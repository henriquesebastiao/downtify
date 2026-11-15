"""One AAC encoder and continuous timestamps across bounded HLS segments."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from datetime import datetime

import numpy as np

from .dj_audio import RATE, AudioError


class HlsEncoder:
    def __init__(self, io, checkpoint):
        self.io, self.checkpoint = io, checkpoint
        self.manifest = io.destination(io.workspace / 'index.m3u8')
        self.diagnostic = tempfile.TemporaryFile()
        self.process = None
        self.frames = 0
        self.origin = None
        try:
            self.process = subprocess.Popen(
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
                    '-f',
                    'hls',
                    '-hls_time',
                    '6',
                    '-hls_list_size',
                    '12',
                    '-hls_delete_threshold',
                    '4',
                    '-hls_allow_cache',
                    '0',
                    '-hls_flags',
                    'delete_segments+temp_file+program_date_time',
                    '-hls_segment_filename',
                    str(io.workspace / 'segment-%08d.ts'),
                    str(self.manifest),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=self.diagnostic,
                bufsize=0,
            )
            os.set_blocking(self.process.stdin.fileno(), False)
        except BaseException:
            self.close()
            raise

    def write(self, audio):
        if (
            audio.ndim != 2
            or audio.shape[1] != 2
            or not 1 <= len(audio) <= RATE
            or not np.all(np.isfinite(audio))
        ):
            raise AudioError('unsafe_hls_block')
        self.io.check_space(0)
        block = memoryview(audio.astype('<f4', copy=False).tobytes())
        stalled = time.monotonic()
        while block:
            self.checkpoint()
            if self.process.poll() is not None:
                raise AudioError('audio_command_failed')
            try:
                size = os.write(self.process.stdin.fileno(), block)
                block = block[size:]
                stalled = time.monotonic()
            except BlockingIOError:
                if time.monotonic() - stalled > 30:
                    raise AudioError('audio_timeout')
                time.sleep(0.01)
        self.frames += len(audio)

    def ready(self):
        ready = self.manifest.is_file() and self.frames >= 18 * RATE
        if ready and self.origin is None:
            text = self.manifest.read_text()
            if '#EXT-X-MEDIA-SEQUENCE:0\n' not in text:
                raise AudioError('hls_origin_missing')
            stamp = next(
                (
                    line.split(':', 1)[1]
                    for line in text.splitlines()
                    if line.startswith('#EXT-X-PROGRAM-DATE-TIME:')
                ),
                None,
            )
            if stamp is None:
                raise AudioError('hls_origin_missing')
            self.origin = datetime.fromisoformat(
                stamp.replace('Z', '+00:00')
            ).timestamp()
        return ready

    def finish(self):
        self.process.stdin.close()
        deadline = time.monotonic() + 60
        while self.process.poll() is None:
            self.checkpoint()
            if time.monotonic() > deadline:
                raise AudioError('audio_timeout')
            time.sleep(0.05)
        if self.process.returncode:
            raise AudioError('audio_command_failed')

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
            if self.process.stdin and not self.process.stdin.closed:
                self.process.stdin.close()
        self.diagnostic.close()
