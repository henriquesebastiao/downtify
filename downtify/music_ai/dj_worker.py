"""Optional local DJ companion. Models run in cancellable child processes."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import math
import shutil
import sqlite3
import sys
import time
from pathlib import Path

from .dj_audio import AudioError, AudioIO, run_audio
from .dj_plan import Profile, order_tracks, timeline
from .dj_store import DjStore
from .sqlite_busy import is_busy, retry_busy
from .store import Store

PINS = {
    'small0': '6074be2c4d490c5f6101fcc374a1ec72ae93456e23bb6019783b849f5dc7d47b',
    'final0': '8c328b45f59d8dd3dff219253ff6a8d6482be57d0133a29140e2febbf8eb8331',
}


def identity(names):
    content = json.dumps(PINS, sort_keys=True).encode()
    for name in names:
        content += Path(__file__).with_name(name + '.py').read_bytes()
    return hashlib.sha256(content).hexdigest()


def analysis_identity():
    # Fingerprint the analysis pipeline, independent of rendering and controls.
    # Model pins and audio-analysis changes still invalidate derived profiles.
    content = json.dumps(PINS, sort_keys=True).encode()
    content += Path(__file__).with_name('dj_evidence.py').read_bytes()
    for function in (
        validate_models,
        analyze_child,
        AudioIO.original,
        AudioIO.probe,
        AudioIO.analyze,
        AudioIO.loudness,
        run_audio,
    ):
        content += inspect.getsource(function).encode()
    for package in (
        'torch',
        'torchaudio',
        'numpy',
        'scipy',
        'soxr',
        'beat-this',
    ):
        try:
            version = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            version = 'unavailable'
        content += f'{package}:{version}'.encode()
    return 'beat-this:' + hashlib.sha256(content).hexdigest()


def engine_identity():
    return 'dj:' + identity((
        'dj_plan',
        'dj_evidence',
        'dj_mix',
        'dj_audio',
        'dj_store',
        'dj_worker',
        'dj_live',
        'dj_live_plan',
        'dj_hls',
        'dj_validation',
    ))


def validate_models(models):
    models = Path(models)
    for name, digest in PINS.items():
        path = models / (name + '.ckpt')
        if path.is_symlink():
            raise AudioError('dj_models_unavailable')
        with path.open('rb') as source:
            if hashlib.file_digest(source, 'sha256').hexdigest() != digest:
                raise AudioError('dj_models_unavailable')


def analyze_child(options):
    import torch
    from beat_this.inference import Audio2Beats

    from .dj_evidence import profile_from_signal

    validate_models(options.models)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    payload = json.loads(sys.stdin.buffer.read(16385))
    io = AudioIO(
        options.cache,
        options.root,
        budget=options.cache_bytes,
        min_free=options.min_free,
        workspace=options.workspace,
    )
    if payload.get('snapshot'):
        io.allow_snapshot(payload['path'], payload['source_version'])
    chosen = ['small0']

    def positions(values, duration):
        if any(
            not math.isfinite(value)
            or value < -0.05
            or value > duration + 0.05
            for value in values
        ):
            raise AudioError('invalid_beat_positions')
        # A model's final spectrogram frame can coincide with the audio end.
        return [float(value) for value in values if 0 <= value < duration]

    def tracker(signal, rate):
        with torch.inference_mode():
            small = Audio2Beats(
                str(options.models / 'small0.ckpt'), device='cpu', dbn=False
            )
            beats, bars = small(signal, rate)
            beats, bars = (
                positions(beats, len(signal) / rate),
                positions(bars, len(signal) / rate),
            )
            evidence = profile_from_signal(
                payload['id'], signal, rate, beats, bars
            )
            if 0.2 <= evidence.confidence < 0.75:
                large = Audio2Beats(
                    str(options.models / 'final0.ckpt'),
                    device='cpu',
                    dbn=False,
                )
                other_beats, other_bars = large(signal, rate)
                other_beats = positions(other_beats, len(signal) / rate)
                other_bars = positions(other_bars, len(signal) / rate)
                other = profile_from_signal(
                    payload['id'], signal, rate, other_beats, other_bars
                )
                if other.confidence > evidence.confidence + 0.05:
                    beats, bars, chosen[0] = other_beats, other_bars, 'final0'
            return beats, bars

    result = io.analyze(
        payload['id'],
        payload['path'],
        tracker,
        lambda: None,
        artist=payload.get('artist', ''),
        expected=payload['source_version'],
    )
    result['beat_model'] = chosen[0]
    print(json.dumps(result))


class DjWorker:
    def __init__(
        self,
        database,
        models,
        roots,
        *,
        cache_bytes=5 * 1024**3,
        min_free=2 * 1024**3,
    ):
        self.database = database
        self.dj = DjStore(database)
        self.models, self.roots = (
            Path(models).resolve(),
            [Path(root).resolve() for root in roots],
        )
        self.cache = database.path.resolve().parent / 'dj'
        self.cache_bytes, self.min_free = cache_bytes, min_free
        self.analysis, self.engine = analysis_identity(), engine_identity()
        self.job = None
        self.stage = 'preparing'
        self.checked = self.renewed = 0.0
        self.models_validated = False

    def capabilities(self):
        from .dj_validation import runtime_identity, saved_proof, validated

        flags = self.database.preferences(-1)
        active = any(flags[key] for key in ('dj_prepared', 'dj_interactive'))
        paused = self.database.metadata('analysis_paused', False)
        ready = active and not paused
        if ready and not self.models_validated:
            validate_models(self.models)
            self.models_validated = True
        self.database.set_metadata(
            'dj',
            {
                'ready': ready,
                'prepared_ready': ready,
                'queue_supported': True,
                'continuous_supported': True,
                'interactive_ready': ready
                and validated(
                    saved_proof(
                        self.database, self.engine, runtime_identity()
                    ),
                    self.engine,
                    runtime_identity(),
                ),
                'state': 'paused'
                if paused
                else 'ready'
                if ready
                else 'disabled',
                'engine': self.engine,
                'seen': time.time(),
                'simultaneous_sessions': 1,
                'cache_bytes': self.cache_bytes,
            },
        )

    def checkpoint(self):
        return retry_busy(self._checkpoint, seconds=8)

    def _checkpoint(self):
        clock = time.monotonic()
        if clock - self.checked < 0.25:
            return
        if not self.dj.alive(self.job['id'], self.job['lease_token']):
            raise PermissionError('dj_session_stopped')
        if clock - self.renewed >= 5:
            if not self.dj.publish(
                self.job['id'], self.job['lease_token'], self.stage
            ):
                raise PermissionError('dj_session_stopped')
            self.renewed = clock
            self.capabilities()
        self.checked = clock

    def publish(self, **changes):
        if not retry_busy(
            lambda: self.dj.publish(
                self.job['id'], self.job['lease_token'], self.stage, changes
            ),
            seconds=8,
        ):
            raise PermissionError('dj_session_stopped')

    def analyze(self, track, source, io, generation):
        audio = source.get('snapshot', source)
        original, _ = io.original(audio['path'], audio['source_version'])
        cached = self.dj.profile(
            track,
            self.analysis,
            source['fingerprint'],
            source['source_version'],
        )
        if cached:
            return cached
        arguments = [
            sys.executable,
            '-m',
            'downtify.music_ai.dj_worker',
            'analyze',
            '--models',
            str(self.models),
            '--cache',
            str(self.cache),
            '--workspace',
            self.job['id'],
            '--cache-bytes',
            str(self.cache_bytes),
            '--min-free',
            str(self.min_free),
        ]
        for root in self.roots:
            arguments += ['--root', str(root)]
        payload = {
            'id': track,
            'path': str(original),
            'artist': source.get('artist', ''),
            'source_version': audio['source_version'],
            'snapshot': 'snapshot' in source,
        }
        output, _ = run_audio(
            arguments,
            self.checkpoint,
            timeout=900,
            input_data=json.dumps(payload).encode(),
            max_output=2 * 1024**2,
            cwd=Path(__file__).resolve().parents[2],
        )
        result = json.loads(output)
        io.original(audio['path'], audio['source_version'])
        result['source_version'] = source['source_version']
        if not self.dj.put_profile(
            track,
            self.analysis,
            source['fingerprint'],
            source['source_version'],
            result,
            generation=generation,
            session=self.job['id'],
            token=self.job['lease_token'],
        ):
            raise PermissionError('dj_session_stopped')
        return result

    def analyzed_sources(self, io):
        generation = self.database.metadata('analysis_generation', 0)
        results = {}
        for index, track in enumerate(self.job['ids']):
            self.checkpoint()
            self.publish(
                phase='analysis', progress=0.5 * index / len(self.job['ids'])
            )
            results[track] = self.analyze(
                track, self.job['sources'][track], io, generation
            )
        return results

    def prepared(self, io):
        started = time.monotonic()
        results = self.analyzed_sources(io)
        profiles = [Profile(**item['profile']) for item in results.values()]
        ordered = order_tracks(
            profiles, self.job['theme'], limit=len(profiles)
        )
        rows = timeline(ordered)
        self.stage = 'rendering'
        self.publish(
            phase='mixing',
            progress=0.5,
            timeline=rows,
            duration=rows[-1]['end'],
        )
        render_started = time.monotonic()

        def decode(index, row):
            track = row['id']
            source = self.job['sources'][track]
            result = io.decode(
                source['path'],
                row,
                results[track]['loudness'],
                io.workspace / f'decoded-{index}.pcm',
                self.checkpoint,
                expected=source['source_version'],
            )
            self.publish(
                phase='mixing', progress=0.5 + 0.35 * (index + 1) / len(rows)
            )
            return result

        target = io.prepared(
            rows, decode, io.workspace / 'set.m4a', self.checkpoint
        )
        for row in rows:
            source = self.job['sources'][row['id']]
            io.original(source['path'], source['source_version'])
        elapsed, render_time = (
            time.monotonic() - started,
            time.monotonic() - render_started,
        )
        self.checkpoint()
        published = self.dj.publish(
            self.job['id'],
            self.job['lease_token'],
            'ready',
            {
                'phase': 'ready',
                'progress': 1.0,
                'duration': rows[-1]['end'],
                'timeline': rows,
                'preparation_seconds': elapsed,
                'render_speed': rows[-1]['end'] / max(0.001, render_time),
                'engine': self.engine,
                'output_bytes': target.stat().st_size,
            },
        )
        if not published:
            target.unlink(missing_ok=True)
            raise PermissionError('dj_session_stopped')

    def step(self):
        self.capabilities()
        # The single renderer performs deletion only between jobs, after any
        # cancelled decoder/encoder has been reaped. No original path is used.
        for identity in self.dj.deletion_requests():
            if len(identity) != 32 or any(
                value not in '0123456789abcdef' for value in identity
            ):
                continue
            directory = self.cache / identity
            if directory.is_symlink() or (
                directory.exists()
                and not directory.resolve().is_relative_to(
                    self.cache.resolve()
                )
            ):
                continue
            if directory.exists():
                shutil.rmtree(directory)
            self.dj.deleted(identity)
        job = self.dj.claim()
        if job is None:
            return False
        self.job, self.stage = job, 'preparing'
        self.checked = self.renewed = 0
        io = None
        try:
            io = AudioIO(
                self.cache,
                self.roots,
                budget=self.cache_bytes,
                min_free=self.min_free,
                workspace=job['id'],
            )
            if job['mode'] == 'prepared':
                self.prepared(io)
            else:
                from .dj_live import LiveRenderer
                from .dj_validation import (
                    runtime_identity,
                    saved_proof,
                    validated,
                )

                if not job.get('validation') and not validated(
                    saved_proof(
                        self.database, self.engine, runtime_identity()
                    ),
                    self.engine,
                    runtime_identity(),
                ):
                    raise AudioError('interactive_not_validated')
                for index, source in enumerate(job['sources'].values()):
                    self.publish(phase='snapshot', progress=0.0)
                    source['snapshot'] = io.freeze(
                        source['path'],
                        source['source_version'],
                        index,
                        self.checkpoint,
                    )
                results = self.analyzed_sources(io)
                renderer = LiveRenderer(self, io, results)
                if (
                    job.get('validation')
                    and not job.get('continuous')
                    and renderer.plan.rows[-1]['end'] < 3700
                ):
                    raise AudioError('validation_set_too_short')
                renderer.render()
        except (
            OSError,
            ValueError,
            KeyError,
            RuntimeError,
            sqlite3.OperationalError,
        ) as error:
            if isinstance(error, sqlite3.OperationalError) and not is_busy(
                error
            ):
                raise
            code = (
                str(error)
                if isinstance(error, AudioError)
                else 'dj_render_unavailable'
            )
            if isinstance(error, sqlite3.OperationalError):
                code = 'dj_database_busy'
            if isinstance(error, PermissionError):
                code = 'dj_session_stopped'
            try:
                self.dj.publish(
                    job['id'],
                    job['lease_token'],
                    'failed',
                    {'phase': 'failed', 'error': code},
                )
            except sqlite3.OperationalError as pending:
                if not is_busy(pending):
                    raise
                # The lease expires without accepting any late output.
            # Only this opaque session's private workspace can be removed.
            if io is not None:
                directory = io.workspace
                if (
                    directory != io.cache
                    and not directory.is_symlink()
                    and directory.resolve().is_relative_to(io.cache)
                ):
                    shutil.rmtree(directory)
        finally:
            if io is not None:
                io.release_snapshots()
            self.job = None
        return True

    def run_cycle(self):
        try:
            return self.step()
        except sqlite3.OperationalError as error:
            if not is_busy(error):
                raise
            return False
        except (OSError, ValueError, RuntimeError):
            try:
                self.database.set_metadata(
                    'dj',
                    {
                        'ready': False,
                        'state': 'unavailable',
                        'seen': time.time(),
                    },
                )
            except sqlite3.OperationalError as error:
                if not is_busy(error):
                    raise
            return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('work', 'analyze'))
    parser.add_argument('--database', type=Path)
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--workspace')
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--root', type=Path, action='append', required=True)
    parser.add_argument('--cache-bytes', type=int, default=5 * 1024**3)
    parser.add_argument('--min-free', type=int, default=2 * 1024**3)
    parser.add_argument('--once', action='store_true')
    options = parser.parse_args()
    if options.action == 'analyze':
        analyze_child(options)
        return
    if options.database is None:
        parser.error('--database is required')
    worker = retry_busy(
        lambda: DjWorker(
            Store(options.database),
            options.models,
            options.root,
            cache_bytes=options.cache_bytes,
            min_free=options.min_free,
        ),
        seconds=30,
    )
    while True:
        worked = worker.run_cycle()
        if options.once:
            break
        if not worked:
            time.sleep(3)


if __name__ == '__main__':
    main()
