"""One cancellable preparation slot, with results owned by the caller."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Event
from typing import Any


@dataclass(frozen=True)
class PreparationResult:
    key: Any
    value: Any
    error: BaseException | None
    cancelled: bool


class SinglePreparation:
    """Owner-thread API; work receives only a cooperative cancellation check.

    A completed task still occupies the slot until poll returns its result.
    close joins the worker but leaves that result available for disposal.
    """

    def __init__(self):
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix='dj-preparation'
        )
        self._future = None
        self._cancelled = None
        self._key = None
        self._closed = False

    @property
    def busy(self):
        return self._future is not None

    def submit(self, key, work):
        if self._closed or self.busy:
            return False
        cancelled = Event()

        def checkpoint():
            if cancelled.is_set():
                raise PermissionError('dj_preparation_cancelled')

        def run():
            checkpoint()
            return work(checkpoint)

        future = self._executor.submit(run)
        self._key, self._cancelled, self._future = key, cancelled, future
        return True

    def poll(self):
        future = self._future
        if future is None or not future.done():
            return None
        value, error = None, None
        try:
            value = future.result()
        except BaseException as failure:
            error = failure
        result = PreparationResult(
            self._key, value, error, self._cancelled.is_set()
        )
        self._future = self._cancelled = self._key = None
        return result

    def cancel(self):
        if self._future is not None:
            self._cancelled.set()
            self._future.cancel()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.cancel()
        self._executor.shutdown(wait=True, cancel_futures=True)
