"""One continuous decoder with bounded stereo read-ahead and explicit ownership."""

from __future__ import annotations

import os
import select
import signal
import subprocess
import threading
import time
from collections import deque

import numpy as np

from .dj_audio import FRAME_BYTES, RATE, AudioError


class ProgressivePcm:
    """Array-like logical deck; unread or expired frames are never silence."""

    ndim = 2

    def __init__(self, command, frames, validate, *, ahead=24 * RATE):
        if (
            type(frames) is not int
            or frames <= 0
            or not RATE <= ahead <= 30 * RATE
        ):
            raise ValueError('Invalid progressive audio bounds')
        self.shape = (frames, 2)
        self.ahead = ahead
        self._validate = validate
        self._condition = threading.Condition()
        self._stop = threading.Event()
        self._chunks = deque()
        self._produced = self._consumed = 0
        self._error = None
        self._done = False
        self._closed = False
        self._termination_lock = threading.Lock()
        self._terminated = False
        self._process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        os.set_blocking(self._process.stdout.fileno(), False)
        self._thread = threading.Thread(
            target=self._pump,
            name='dj-progressive-pcm',
            daemon=True,
        )
        self._thread.start()

    def __len__(self):
        return self.shape[0]

    @property
    def idle(self):
        with self._condition:
            self._check()
            return self._done or self._produced >= min(
                len(self), self._consumed + self.ahead
            )

    @property
    def buffered_frames(self):
        with self._condition:
            return sum(len(chunk) for _, chunk in self._chunks)

    def _check(self):
        if self._error is not None:
            raise self._error
        if self._closed:
            raise AudioError('decoded_deck_closed')

    def ready(self, left, right):
        with self._condition:
            self._check()
            first = self._chunks[0][0] if self._chunks else self._produced
            if left < first:
                raise AudioError('decoded_range_expired')
            return 0 <= left <= right <= self._produced

    def warm(self, checkpoint):
        target = min(len(self), self.ahead)
        while True:
            checkpoint()
            with self._condition:
                self._check()
                if self._produced >= target:
                    return self
                if self._done:
                    raise AudioError('decoded_length_mismatch')
                self._condition.wait(0.05)

    def __getitem__(self, span):
        if not isinstance(span, slice) or span.step not in {None, 1}:
            raise ValueError('Only contiguous stereo slices are supported')
        left = 0 if span.start is None else span.start
        right = len(self) if span.stop is None else span.stop
        with self._condition:
            if not self.ready(left, right):
                raise AudioError('decoded_range_not_ready')
            pieces = [
                chunk[max(0, left - start) : min(len(chunk), right - start)]
                for start, chunk in self._chunks
                if start < right and start + len(chunk) > left
            ]
            audio = (
                np.concatenate(pieces)
                if pieces
                else np.empty((0, 2), dtype='<f4')
            )
            if len(audio) != right - left:
                raise AudioError('decoded_length_mismatch')
            self._consumed = max(self._consumed, right)
            # Keep one second behind the cursor for bounded diagnostic rereads.
            while (
                self._chunks
                and self._chunks[0][0] + len(self._chunks[0][1])
                <= self._consumed - RATE
            ):
                self._chunks.popleft()
            self._condition.notify_all()
            return audio

    def _append(self, data):
        chunk = np.frombuffer(data, dtype='<f4').reshape(-1, 2)
        if not np.all(np.isfinite(chunk)):
            raise AudioError('invalid_decoded_samples')
        with self._condition:
            self._chunks.append((self._produced, chunk))
            self._produced += len(chunk)
            self._condition.notify_all()

    def _pump(self):
        pending = b''
        overflow = 0
        progress_at = time.monotonic()
        verified_at = 0
        try:
            while not self._stop.is_set():
                with self._condition:
                    limit = min(len(self), self._consumed + self.ahead)
                    if self._produced >= limit and self._produced < len(self):
                        self._condition.wait(0.05)
                        progress_at = time.monotonic()
                        continue
                    capacity = min(
                        65536, (limit - self._produced) * FRAME_BYTES
                    )
                    # At the logical end, drain only the tolerated codec tail.
                    if self._produced == len(self):
                        capacity = max(1, (2048 - overflow) * FRAME_BYTES + 1)
                if self._produced - verified_at >= RATE or verified_at == 0:
                    self._validate()
                    verified_at = self._produced
                readable, _, _ = select.select(
                    [self._process.stdout], [], [], 0.05
                )
                if not readable:
                    if time.monotonic() - progress_at > 30:
                        raise AudioError('audio_command_timeout')
                    continue
                try:
                    data = os.read(self._process.stdout.fileno(), capacity)
                except BlockingIOError:
                    continue
                if not data:
                    if pending:
                        raise AudioError('decoded_length_mismatch')
                    if self._process.wait(timeout=2) != 0:
                        raise AudioError('audio_command_failed')
                    missing = len(self) - self._produced
                    if not 0 <= missing <= 2048:
                        raise AudioError('decoded_length_mismatch')
                    self._validate()
                    if missing:
                        self._append(bytes(missing * FRAME_BYTES))
                    return
                progress_at = time.monotonic()
                pending += data
                aligned = len(pending) // FRAME_BYTES * FRAME_BYTES
                if not aligned:
                    continue
                chunk, pending = pending[:aligned], pending[aligned:]
                available = len(self) - self._produced
                usable = min(available, len(chunk) // FRAME_BYTES)
                if usable:
                    self._append(chunk[: usable * FRAME_BYTES])
                overflow += len(chunk) // FRAME_BYTES - usable
                if overflow > 2048:
                    raise AudioError('decoded_length_mismatch')
        except BaseException as error:
            with self._condition:
                self._error = error
        finally:
            self._terminate()
            with self._condition:
                self._done = True
                self._condition.notify_all()

    def _terminate(self):
        with self._termination_lock:
            if self._terminated:
                return
            try:
                os.killpg(self._process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            # Also terminate descendants if the group leader has already exited.
            try:
                os.killpg(self._process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self._process.wait(timeout=2)
            self._terminated = True

    def close(self):
        with self._condition:
            if self._closed:
                return
            self._closed = True
            self._stop.set()
            self._condition.notify_all()
        self._terminate()
        self._thread.join(timeout=5)
        self._process.stdout.close()
        with self._condition:
            self._chunks.clear()
        if self._thread.is_alive():
            raise AudioError('decoded_deck_cleanup_failed')
