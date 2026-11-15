"""One serial, cancellable analysis process with bounded private JSON messages."""

from __future__ import annotations

import json
import os
import secrets
import select
import signal
import subprocess
import threading
import time

from .dj_audio import AudioError

MAX_INPUT = 16384
MAX_OUTPUT = 2 * 1024**2


class AnalysisProcess:
    def __init__(self, arguments, *, cwd=None, timeout=900):
        self.arguments = list(arguments)
        self.cwd = cwd
        self.timeout = timeout
        self._process = None
        self._lock = threading.Lock()

    def _start(self):
        self._process = subprocess.Popen(
            self.arguments,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=self.cwd,
            bufsize=0,
            start_new_session=True,
        )
        os.set_blocking(self._process.stdin.fileno(), False)
        os.set_blocking(self._process.stdout.fileno(), False)

    def close(self):
        with self._lock:
            self._close()

    def _close(self):
        process, self._process = self._process, None
        if process is None:
            return
        try:
            # The resident owns this group, including its current decoder.
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            # A decoder may ignore TERM even after its parent has exited.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=2)
        finally:
            process.stdin.close()
            process.stdout.close()

    def analyze(self, payload, checkpoint):
        while not self._lock.acquire(timeout=0.05):
            checkpoint()
        try:
            checkpoint()
            if self._process is None or self._process.poll() is not None:
                self._close()
                self._start()
            process = self._process
            nonce = secrets.token_hex(16)
            request = (
                json.dumps({'request_id': nonce, 'payload': payload}).encode()
                + b'\n'
            )
            if len(request) > MAX_INPUT:
                raise AudioError('unexpected_audio_input')
            deadline = time.monotonic() + self.timeout
            self._write(process, request, checkpoint, deadline)
            response = self._read(process, checkpoint, deadline)
            if (
                not isinstance(response, dict)
                or response.get('request_id') != nonce
                or not isinstance(response.get('result'), dict)
            ):
                raise AudioError('analysis_response_invalid')
            checkpoint()
            return response['result']
        except BaseException:
            self._close()
            raise
        finally:
            self._lock.release()

    @staticmethod
    def _check(process, checkpoint, deadline):
        checkpoint()
        if time.monotonic() >= deadline:
            raise AudioError('audio_timeout')
        if process.poll() is not None:
            raise AudioError('audio_command_failed')

    def _write(self, process, content, checkpoint, deadline):
        offset = 0
        while offset < len(content):
            self._check(process, checkpoint, deadline)
            if select.select([], [process.stdin], [], 0.05)[1]:
                try:
                    offset += os.write(
                        process.stdin.fileno(), content[offset:]
                    )
                except BlockingIOError:
                    continue
                except BrokenPipeError as error:
                    raise AudioError('audio_command_failed') from error

    def _read(self, process, checkpoint, deadline):
        content = bytearray()
        while True:
            checkpoint()
            if time.monotonic() >= deadline:
                raise AudioError('audio_timeout')
            if select.select([process.stdout], [], [], 0.05)[0]:
                try:
                    part = os.read(process.stdout.fileno(), 65536)
                except BlockingIOError:
                    continue
                if not part:
                    raise AudioError('audio_command_failed')
                content.extend(part)
                if len(content) > MAX_OUTPUT:
                    raise AudioError('unexpected_audio_output')
                if b'\n' in content:
                    line, remaining = bytes(content).split(b'\n', 1)
                    if remaining.strip():
                        raise AudioError('analysis_response_invalid')
                    try:
                        return json.loads(line)
                    except (ValueError, UnicodeDecodeError) as error:
                        raise AudioError(
                            'analysis_response_invalid'
                        ) from error
            if process.poll() is not None:
                raise AudioError('audio_command_failed')
