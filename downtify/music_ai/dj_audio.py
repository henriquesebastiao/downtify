"""Bounded FFmpeg audio I/O. Originals are always inputs; only the DJ cache is writable."""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .dj_evidence import profile_from_signal
from .dj_mix import StereoMixer
from .worker import signature, source_path

RATE = 48000
FRAME_BYTES = 8  # stereo float32


class AudioError(RuntimeError):
    pass


def run_audio(
    arguments,
    checkpoint,
    *,
    timeout=300,
    input_data=None,
    max_output=16384,
    cwd=None,
):
    """Never expose FFmpeg metadata or source paths in an exception or log."""
    if input_data is not None and len(input_data) > 16384:
        raise AudioError('unexpected_audio_input')
    if not 1 <= max_output <= 2 * 1024**2:
        raise AudioError('unexpected_audio_output_limit')
    checkpoint()
    with (
        tempfile.TemporaryFile() as incoming,
        tempfile.TemporaryFile() as output,
        tempfile.TemporaryFile() as diagnostic,
    ):
        if input_data is not None:
            incoming.write(input_data)
            incoming.seek(0)
        process = subprocess.Popen(
            arguments,
            stdin=incoming if input_data is not None else subprocess.DEVNULL,
            stdout=output,
            stderr=diagnostic,
            cwd=cwd,
        )
        started = time.monotonic()
        try:
            while process.poll() is None:
                checkpoint()
                if time.monotonic() - started > timeout:
                    raise AudioError('audio_timeout')
                time.sleep(0.05)
            if process.returncode:
                raise AudioError('audio_command_failed')
            checkpoint()
            output.seek(0)
            content = output.read(max_output + 1)
            if len(content) > max_output:
                raise AudioError('unexpected_audio_output')
            diagnostic.seek(0, 2)
            diagnostic.seek(max(0, diagnostic.tell() - 16384))
            return content, diagnostic.read()
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)


class AudioIO:
    def __init__(
        self,
        cache,
        roots,
        *,
        budget=5 * 1024**3,
        min_free=2 * 1024**3,
        max_track_seconds=1200,
        workspace=None,
    ):
        cache = Path(cache)
        if cache.is_symlink() or cache.name != 'dj':
            raise ValueError('A private DJ cache directory is required')
        cache.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.cache = cache.resolve(strict=True)
        self.snapshots = {}
        if workspace is not None and not re.fullmatch(
            '[a-f0-9]{32}', workspace
        ):
            raise ValueError('Invalid DJ workspace')
        self.workspace = self.cache / workspace if workspace else self.cache
        if self.workspace.is_symlink():
            raise ValueError('Invalid DJ workspace')
        self.workspace.mkdir(mode=0o700, exist_ok=True)
        self.roots = [Path(root).resolve(strict=True) for root in roots]
        if any(
            self.cache.is_relative_to(root) or root.is_relative_to(self.cache)
            for root in self.roots
        ):
            raise ValueError('DJ cache and original music must be separate')
        if (
            not 16 * 1024**2 <= budget <= 50 * 1024**3
            or min_free < 0
            or not 10 <= max_track_seconds <= 3600
        ):
            raise ValueError('Invalid DJ resource budget')
        self.budget, self.min_free, self.max_track_seconds = (
            budget,
            min_free,
            max_track_seconds,
        )

    def check_space(self, requested):
        used = 0
        for path in self.cache.rglob('*'):
            try:
                if path.is_symlink():
                    raise AudioError('unsafe_cache_entry')
                if path.is_file():
                    used += path.stat().st_size
            except FileNotFoundError:
                # The encoder and one preparation task atomically rotate
                # private temporary files. All other filesystem errors fail.
                continue
        if requested < 0 or used + requested > self.budget:
            raise AudioError('dj_cache_full')
        if shutil.disk_usage(self.cache).free < requested + self.min_free:
            raise AudioError('dj_storage_reserve')

    def destination(self, target):
        path = Path(target)
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(self.cache)
            or path.exists()
        ):
            raise AudioError('unsafe_cache_destination')
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not path.parent.resolve(strict=True).is_relative_to(self.cache):
            raise AudioError('unsafe_cache_destination')
        return path

    def temporary(self, suffix):
        descriptor, filename = tempfile.mkstemp(
            prefix='render-', suffix=suffix, dir=self.workspace
        )
        os.close(descriptor)
        return Path(filename)

    def original(self, value, expected=None):
        candidate = Path(value)
        if str(candidate) in self.snapshots:
            if expected is None:
                expected = self.snapshots[str(candidate)]
            if (
                candidate.is_symlink()
                or not candidate.resolve().is_relative_to(
                    self.workspace.resolve()
                )
            ):
                raise AudioError('unsafe_snapshot_source')
            path = candidate
        else:
            path = source_path(value, self.roots)
        current = list(signature(path))
        if expected is not None and current != list(expected):
            raise AudioError('source_changed')
        return path, current

    def allow_snapshot(self, path, expected):
        path = Path(path)
        if (
            not re.fullmatch(r'source-[0-9]+\.audio', path.name)
            or path.is_symlink()
            or path.parent.resolve() != self.workspace.resolve()
            or not path.is_file()
            or list(signature(path)) != list(expected)
        ):
            raise AudioError('unsafe_snapshot_source')
        self.snapshots[str(path)] = list(expected)

    def freeze(self, value, expected, index, checkpoint):
        if type(index) is not int or not 0 <= index < 40:
            raise AudioError('unsafe_snapshot_destination')
        original, before = self.original(value, expected)
        target = self.destination(self.workspace / f'source-{index}.audio')
        try:
            self.check_space(original.stat().st_size)
            with original.open('rb') as source, target.open('xb') as output:
                while block := source.read(1024**2):
                    checkpoint()
                    self.check_space(len(block))
                    output.write(block)
            self.original(original, before)
            target.chmod(0o400)
            version = list(signature(target))
            self.allow_snapshot(target, version)
            return {'path': str(target), 'source_version': version}
        except BaseException:
            target.unlink(missing_ok=True)
            raise

    def release_snapshots(self):
        for value in self.snapshots:
            path = Path(value)
            if (
                path.parent.resolve() == self.workspace.resolve()
                and not path.is_symlink()
            ):
                path.unlink(missing_ok=True)
        self.snapshots.clear()

    def probe(self, path, checkpoint):
        content, _ = run_audio(
            [
                'ffprobe',
                '-v',
                'error',
                '-protocol_whitelist',
                'file,pipe',
                '-select_streams',
                'a:0',
                '-show_entries',
                'format=duration:stream=codec_type,sample_rate,channels',
                '-of',
                'json',
                str(path),
            ],
            checkpoint,
            timeout=30,
        )
        try:
            data = json.loads(content)
            duration = float(data['format']['duration'])
            audio = data['streams'][0]
        except (ValueError, KeyError, IndexError, TypeError):
            raise AudioError('audio_metadata_unavailable') from None
        if (
            not math.isfinite(duration)
            or not 1 <= duration <= self.max_track_seconds
            or audio.get('codec_type') != 'audio'
        ):
            raise AudioError('unsupported_audio_duration')
        return duration

    def loudness(self, path, checkpoint):
        _, diagnostic = run_audio(
            [
                'ffmpeg',
                '-nostdin',
                '-hide_banner',
                '-nostats',
                '-v',
                'info',
                '-protocol_whitelist',
                'file,pipe',
                '-i',
                str(path),
                '-map',
                '0:a:0',
                '-vn',
                '-sn',
                '-dn',
                '-af',
                'loudnorm=I=-18:TP=-1.5:LRA=11:print_format=json',
                '-f',
                'null',
                '-',
            ],
            checkpoint,
            timeout=300,
        )
        try:
            stats = json.loads(diagnostic[diagnostic.rfind(b'{') :])
            result = {
                key: float(stats[key]) for key in ('input_i', 'input_tp')
            }
        except (ValueError, KeyError, TypeError):
            raise AudioError('loudness_unavailable') from None
        if not all(math.isfinite(value) for value in result.values()):
            raise AudioError('silent_audio')
        return result

    def analyze(
        self, identity, value, tracker, checkpoint, *, artist='', expected=None
    ):
        path, before = self.original(value, expected)
        duration = self.probe(path, checkpoint)
        self.check_space(math.ceil(duration * 44100 * 4))
        mono = self.temporary('.mono.pcm')
        try:
            run_audio(
                [
                    'ffmpeg',
                    '-nostdin',
                    '-hide_banner',
                    '-nostats',
                    '-v',
                    'error',
                    '-xerror',
                    '-protocol_whitelist',
                    'file,pipe',
                    '-i',
                    str(path),
                    '-map',
                    '0:a:0',
                    '-vn',
                    '-sn',
                    '-dn',
                    '-t',
                    str(self.max_track_seconds + 0.1),
                    '-ar',
                    '44100',
                    '-ac',
                    '1',
                    '-f',
                    'f32le',
                    '-y',
                    str(mono),
                ],
                checkpoint,
                timeout=300,
            )
            if mono.stat().st_size >= self.max_track_seconds * 44100 * 4:
                raise AudioError('unsupported_audio_duration')
            signal = np.fromfile(mono, dtype='<f4')
            checkpoint()
            beats, downbeats = tracker(signal, 44100)
            checkpoint()
            profile = profile_from_signal(
                identity, signal, 44100, beats, downbeats, artist=artist
            )
            levels = self.loudness(path, checkpoint)
            self.original(path, before)
            return {
                'profile': asdict(profile),
                'loudness': levels,
                'source_version': before,
            }
        finally:
            mono.unlink(missing_ok=True)

    def decode(self, value, row, levels, target, checkpoint, *, expected=None):
        path, before = self.original(value, expected)
        self.probe(path, checkpoint)
        speed, cue, source_end = row['speed'], row['cue'], row['source_end']
        if (
            not all(math.isfinite(v) for v in (speed, cue, source_end))
            or not 0.96 <= speed <= 1.04
            or not 0 <= cue < source_end <= self.max_track_seconds
        ):
            raise AudioError('unsafe_audio_plan')
        gain = min(24.0, -18 - levels['input_i'], -3 - levels['input_tp'])
        if not math.isfinite(gain):
            raise AudioError('loudness_unavailable')
        frames = round((source_end - cue) / speed * RATE)
        if 'start' in row or 'end' in row:
            start, end = row.get('start'), row.get('end')
            if (
                not isinstance(start, (int, float))
                or not isinstance(end, (int, float))
                or not all(math.isfinite(value) for value in (start, end))
                or not 0 <= start < end
            ):
                raise AudioError('unsafe_audio_plan')
            # Match the mixer's absolute sample grid. Rounding a duration
            # independently can otherwise make a fractional cue one frame short.
            planned = round(end * RATE) - round(start * RATE)
            if abs(planned - frames) > 1:
                raise AudioError('unsafe_audio_plan')
            frames = planned
        self.check_space(frames * FRAME_BYTES)
        target = self.destination(target)
        temporary = self.temporary('.stereo.pcm')
        try:
            run_audio(
                [
                    'ffmpeg',
                    '-nostdin',
                    '-hide_banner',
                    '-nostats',
                    '-v',
                    'error',
                    '-xerror',
                    '-protocol_whitelist',
                    'file,pipe',
                    '-ss',
                    f'{cue:.9f}',
                    '-i',
                    str(path),
                    '-map',
                    '0:a:0',
                    '-vn',
                    '-sn',
                    '-dn',
                    '-map_metadata',
                    '-1',
                    '-af',
                    f'rubberband=tempo={speed:.10f}:pitch=1:channels=together,volume={gain:.8f}dB',
                    '-t',
                    f'{frames / RATE:.9f}',
                    '-ar',
                    str(RATE),
                    '-ac',
                    '2',
                    '-f',
                    'f32le',
                    '-y',
                    str(temporary),
                ],
                checkpoint,
                timeout=300,
            )
            self.original(path, before)
            produced = temporary.stat().st_size // FRAME_BYTES
            if abs(produced - frames) > 2048:
                raise AudioError('decoded_length_mismatch')
            with temporary.open('r+b') as output:
                if produced < frames:
                    output.seek(0, 2)
                    output.write(bytes((frames - produced) * FRAME_BYTES))
                else:
                    output.truncate(frames * FRAME_BYTES)
            checkpoint()
            os.replace(temporary, target)
            return target
        finally:
            temporary.unlink(missing_ok=True)

    def prepared(self, rows, decoded, target, checkpoint):
        # Compressed output only: never allocate a second complete PCM set.
        self.check_space(math.ceil(rows[-1]['end'] * 40000))
        target = self.destination(target)
        encoded = self.temporary('.set.m4a')
        sources, filenames = {}, {}
        process = None
        diagnostic = tempfile.TemporaryFile()

        def load(index, row):
            if index in sources:
                return sources[index]
            filename = Path(
                decoded(index, row) if callable(decoded) else decoded[index]
            )
            if filename.is_symlink() or not filename.resolve(
                strict=True
            ).is_relative_to(self.cache):
                raise AudioError('unsafe_cache_source')
            length = filename.stat().st_size // FRAME_BYTES
            sources[index] = np.memmap(
                filename, mode='r', dtype='<f4', shape=(length, 2)
            )
            filenames[index] = filename
            return sources[index]

        def release(index):
            array = sources.pop(index)
            array._mmap.close()
            if callable(decoded):
                filenames[index].unlink(missing_ok=True)

        try:
            checkpoint()
            process = subprocess.Popen(
                [
                    'ffmpeg',
                    '-nostdin',
                    '-hide_banner',
                    '-nostats',
                    '-v',
                    'error',
                    '-xerror',
                    '-f',
                    'f32le',
                    '-ar',
                    str(RATE),
                    '-ac',
                    '2',
                    '-i',
                    'pipe:0',
                    '-af',
                    'aresample=192000,alimiter=limit=0.84139514:attack=5:release=50:level=false:latency=true,aresample=48000',
                    '-c:a',
                    'aac',
                    '-b:a',
                    '256k',
                    '-movflags',
                    '+faststart',
                    '-f',
                    'ipod',
                    '-y',
                    str(encoded),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=diagnostic,
                bufsize=0,
            )
            descriptor = process.stdin.fileno()
            os.set_blocking(descriptor, False)
            mixer = StereoMixer(rows, load)
            while mixer.position < mixer.total_frames:
                checkpoint()
                block = memoryview(
                    mixer.read(RATE).astype('<f4', copy=False).tobytes()
                )
                stalled = time.monotonic()
                while block:
                    checkpoint()
                    if process.poll() is not None:
                        raise AudioError('audio_command_failed')
                    try:
                        size = os.write(descriptor, block)
                        block = block[size:]
                        stalled = time.monotonic()
                    except BlockingIOError:
                        if time.monotonic() - stalled > 30:
                            raise AudioError('audio_timeout')
                        time.sleep(0.01)
                for index in list(sources):
                    if mixer.bounds[index][1] <= mixer.position:
                        release(index)
                self.check_space(0)
            process.stdin.close()
            deadline = time.monotonic() + 60
            while process.poll() is None:
                checkpoint()
                if time.monotonic() > deadline:
                    raise AudioError('audio_timeout')
                time.sleep(0.05)
            if process.returncode:
                raise AudioError('audio_command_failed')
            checkpoint()
            os.replace(encoded, target)
            return target
        finally:
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=2)
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
            for index in list(sources):
                release(index)
            diagnostic.close()
            encoded.unlink(missing_ok=True)
