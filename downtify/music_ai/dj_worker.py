"""Optional local DJ companion. Models run in cancellable child processes."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path

from .dj_audio import AudioError, AudioIO, run_audio
from .dj_background import BackgroundDeferred
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


def analysis_source(function):
    source = inspect.getsource(function)
    if function is analyze_child:
        # Preserve pre-formatting profile identities for this exact import gap.
        # Every other byte (including analysis logic and model pins) is hashed.
        source = source.replace(
            '    from beat_this.inference import Audio2Beats\n\n'
            '    from .dj_evidence import profile_from_signal\n',
            '    from beat_this.inference import Audio2Beats\n'
            '    from .dj_evidence import profile_from_signal\n',
            1,
        )
    return source.encode()


def analysis_identity():
    # Fingerprint the analysis pipeline, independent of rendering and controls.
    # Model pins and audio-analysis changes still invalidate derived profiles.
    content = json.dumps(PINS, sort_keys=True).encode()
    content += Path(__file__).with_name('dj_evidence.py').read_bytes()
    from .dj_analysis import AnalysisEngine

    content += inspect.getsource(AnalysisEngine).encode()
    for function in (
        validate_models,
        analyze_child,
        AudioIO.original,
        AudioIO.probe,
        AudioIO.analyze,
        AudioIO.loudness,
        run_audio,
    ):
        content += analysis_source(function)
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
        'dj_analysis',
        'analysis_process',
        'dj_evidence',
        'dj_mix',
        'dj_audio',
        'dj_store',
        'dj_background',
        'dj_worker',
        'dj_live',
        'dj_live_plan',
        'dj_preparation',
        'dj_prepared_deck',
        'dj_pcm_stream',
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
    from .dj_analysis import AnalysisEngine

    payload = json.loads(sys.stdin.buffer.read(16385))
    result = AnalysisEngine(options).analyze(payload)
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
        self.compute_ticket = None
        self._analysis_process = None

    def close(self):
        if self._analysis_process is not None:
            self._analysis_process.close()

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
                'interactive_trial_ready': ready,
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
                'analysis_model': self.analysis,
                'seen': time.time(),
                'simultaneous_sessions': 1,
                'weekly_protocol': 1,
                'cache_bytes': self.cache_bytes,
            },
        )

    def checkpoint(self):
        return retry_busy(self._checkpoint, seconds=8)

    def _checkpoint(self):
        if self.compute_ticket is not None and not self.compute_ticket.renew():
            if self.job.get('background'):
                raise BackgroundDeferred('background_waiting')
            raise PermissionError('compute_slot_lost')
        clock = time.monotonic()
        if clock - self.checked < 0.25:
            return
        if self.job.get('background'):
            from .compute_budget import pressure_high
            from .dj_background import allowed, blocked

            with self.database.connect() as db:
                if not allowed(
                    db, self.job['owner'], self.job, now=time.time()
                ):
                    raise PermissionError('weekly_invalidated')
                if blocked(db) or pressure_high():
                    raise BackgroundDeferred('background_waiting')
        if (
            self.job.get('trial')
            and not self.database.effective(self.job['owner'])['dj_trial']
        ):
            raise PermissionError('dj_trial_disabled')
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

    def analysis_result(self, track, source, io, checkpoint):
        checkpoint()
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
        from .analysis_process import AnalysisProcess

        if self._analysis_process is None:
            arguments = [
                sys.executable,
                '-m',
                'downtify.music_ai.dj_worker',
                'analyze-stream',
                '--models',
                str(self.models),
                '--cache',
                str(self.cache),
                '--cache-bytes',
                str(self.cache_bytes),
                '--min-free',
                str(self.min_free),
            ]
            for root in self.roots:
                arguments += ['--root', str(root)]
            self._analysis_process = AnalysisProcess(
                arguments, cwd=Path(__file__).resolve().parents[2]
            )
        result = self._analysis_process.analyze(
            {
                'id': track,
                'path': str(original),
                'artist': source.get('artist', ''),
                'source_version': audio['source_version'],
                'snapshot': 'snapshot' in source,
                'workspace': io.workspace.name,
                'analysis_model': self.analysis,
            },
            checkpoint,
        )
        checkpoint()
        io.original(audio['path'], audio['source_version'])
        result['source_version'] = source['source_version']
        return result

    def analyze(self, track, source, io, generation, *, checkpoint=None):
        checkpoint = checkpoint or self.checkpoint
        result = self.analysis_result(track, source, io, checkpoint)
        checkpoint()
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

    def prepare_deck(
        self,
        track,
        io,
        *,
        source=None,
        checkpoint=None,
        slot=None,
        report=True,
    ):
        """Freeze and analyze only a deck entering the short playback window."""
        checkpoint = checkpoint or self.checkpoint
        checkpoint()
        source = self.job['sources'][track] if source is None else source
        if 'snapshot' in source:
            io.allow_snapshot(
                source['snapshot']['path'],
                source['snapshot']['source_version'],
            )
        if 'snapshot' not in source:
            if report:
                self.publish(phase='snapshot')
            occupied = {Path(value).name for value in io.snapshots}
            if slot is None:
                slot = next(
                    index
                    for index in range(40)
                    if f'source-{index}.audio' not in occupied
                    and not (io.workspace / f'source-{index}.audio').exists()
                )
            source['snapshot'] = io.freeze(
                source['path'], source['source_version'], slot, checkpoint
            )
        return self.analyze(
            track,
            source,
            io,
            self.database.metadata('analysis_generation', 0),
            checkpoint=checkpoint,
        )

    def release_decks(self, io, keep):
        for track, source in self.job['sources'].items():
            snapshot = source.get('snapshot')
            if track in keep or snapshot is None:
                continue
            path = Path(snapshot['path'])
            if (
                path.parent.resolve() == io.workspace.resolve()
                and not path.is_symlink()
            ):
                path.unlink(missing_ok=True)
                io.snapshots.pop(str(path), None)
                source.pop('snapshot')

    def yield_compute(self):
        if self.compute_ticket is not None:
            retry_busy(self.compute_ticket.release, seconds=3)
            self.compute_ticket = None

    def require_compute(self):
        from .compute_budget import acquire

        while self.compute_ticket is None:
            self.checkpoint()
            self.compute_ticket = acquire(self.database, 'dj')
            if self.compute_ticket is None:
                time.sleep(0.25)

    def try_require_compute(self):
        """Live transport stays responsive while another compute job yields."""
        from .compute_budget import acquire

        self.checkpoint()
        if self.compute_ticket is None:
            self.compute_ticket = acquire(self.database, 'dj')
        return self.compute_ticket is not None

    def prepared(self, io):
        started = time.monotonic()
        results = self.analyzed_sources(io)
        profiles = [Profile(**item['profile']) for item in results.values()]
        ordered = order_tracks(
            profiles, self.job['theme'], limit=len(profiles)
        )
        if self.job.get('seed_id'):
            ordered = sorted(
                ordered, key=lambda profile: profile.id != self.job['seed_id']
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
                **(
                    {'asset_workspace': io.workspace.name}
                    if self.job.get('background')
                    else {}
                ),
            },
        )
        if not published:
            target.unlink(missing_ok=True)
            raise PermissionError('dj_session_stopped')
        self._committed_workspace = io.workspace
        # Prepared readiness is the render itself: the client can play the file.
        from .dj_readiness import record as record_readiness

        record_readiness(self.dj.database, 'prepared', elapsed)

    def discard_workspace(self, io):
        if io is None or io.workspace == getattr(
            self, '_committed_workspace', None
        ):
            return
        directory = io.workspace
        if (
            directory != io.cache
            and not directory.is_symlink()
            and directory.resolve().is_relative_to(io.cache)
            and directory.exists()
        ):
            shutil.rmtree(directory)

    def defer_background(self, io):
        try:
            retry_busy(
                lambda: self.dj.defer_background(
                    self.job['id'], self.job['lease_token']
                ),
                seconds=8,
            )
        finally:
            try:
                from .compute_budget import pressure_high

                if (
                    self.database.metadata('native_busy', False)
                    or self.database.metadata('analysis_paused', False)
                    or pressure_high()
                ):
                    self.close()
            finally:
                self.discard_workspace(io)

    def step(self):
        self.capabilities()
        if self.cache.is_symlink():
            raise AudioError('unsafe_cache_entry')
        # The single renderer performs deletion only between jobs, after any
        # cancelled decoder/encoder has been reaped. No original path is used.
        for identity in self.dj.deletion_requests():
            if len(identity) != 32 or any(
                value not in '0123456789abcdef' for value in identity
            ):
                continue
            name = self.dj.workspace(identity)
            if (
                not isinstance(name, str)
                or len(name) != 32
                or any(value not in '0123456789abcdef' for value in name)
            ):
                continue
            directory = self.cache / name
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
            flags = self.database.preferences(-1)
            if not any(
                flags[key] for key in ('dj_prepared', 'dj_interactive')
            ) or self.database.metadata('analysis_paused', False):
                self.close()
            return False
        self.job, self.stage = job, 'preparing'
        self._committed_workspace = None
        self.checked = self.renewed = 0
        io = None
        ticket = None
        try:
            from .compute_budget import acquire

            while ticket is None:
                self.checkpoint()
                ticket = acquire(
                    self.database,
                    'dj-background' if job.get('background') else 'dj',
                )
                if ticket is None:
                    time.sleep(0.25)
            self.compute_ticket = ticket
            io = AudioIO(
                self.cache,
                self.roots,
                budget=self.cache_bytes,
                min_free=self.min_free,
                workspace=job.get('render_workspace', job['id'])
                if job.get('background')
                else job['id'],
            )
            from .dj_assets import Assets

            assets = Assets(
                self.database, budget=self.cache_bytes, min_free=self.min_free
            )
            io.reclaim = lambda requested: assets.reserve(
                requested, self.checkpoint
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

                if (
                    not job.get('validation')
                    and not job.get('trial')
                    and not validated(
                        saved_proof(
                            self.database, self.engine, runtime_identity()
                        ),
                        self.engine,
                        runtime_identity(),
                    )
                ):
                    raise AudioError('interactive_not_validated')
                first = list(dict.fromkeys(job['ids'][:2]))
                results = {
                    track: self.prepare_deck(track, io) for track in first
                }
                renderer = LiveRenderer(self, io, results)
                if (
                    job.get('validation')
                    and not job.get('continuous')
                    and renderer.plan.rows[-1]['end'] < 3700
                ):
                    raise AudioError('validation_set_too_short')
                renderer.render()
        except BackgroundDeferred:
            self.defer_background(io)
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
            if (
                job.get('background')
                and isinstance(error, PermissionError)
                and str(error)
                in {
                    'weekly_invalidated',
                    'dj_session_stopped',
                    'compute_slot_lost',
                }
            ):
                self.defer_background(io)
                return True
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
            # Only this attempt's private workspace can be removed.
            self.discard_workspace(io)
        finally:
            if io is not None:
                io.release_snapshots()
            self.job = None
            if self.compute_ticket is not None:
                retry_busy(self.compute_ticket.release, seconds=3)
            elif ticket is not None:
                retry_busy(ticket.release, seconds=3)
            self.compute_ticket = None
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
    parser.add_argument(
        'action', choices=('work', 'analyze', 'analyze-stream', 'preanalyze')
    )
    parser.add_argument('--database', type=Path)
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--workspace')
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--root', type=Path, action='append', required=True)
    parser.add_argument('--cache-bytes', type=int, default=5 * 1024**3)
    parser.add_argument('--min-free', type=int, default=2 * 1024**3)
    parser.add_argument('--once', action='store_true')
    options = parser.parse_args()
    if options.action == 'analyze-stream':
        from .dj_analysis import serve

        serve(options)
        return
    if options.action == 'analyze':
        analyze_child(options)
        return
    if options.database is None:
        parser.error('--database is required')
    worker_class = DjWorker
    if options.action == 'preanalyze':
        from .rhythm_worker import RhythmWorker

        worker_class = RhythmWorker
    worker = retry_busy(
        lambda: worker_class(
            Store(options.database),
            options.models,
            options.root,
            cache_bytes=options.cache_bytes,
            min_free=options.min_free,
        ),
        seconds=30,
    )
    try:
        while True:
            worked = worker.run_cycle()
            if options.once:
                break
            if not worked:
                time.sleep(3)
    finally:
        worker.close()


if __name__ == '__main__':
    main()
