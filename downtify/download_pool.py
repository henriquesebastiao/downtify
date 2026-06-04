"""Global parallel download limiter shared across batch jobs."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Optional


class DownloadParallelLimiter:
    """Counting limiter for concurrent downloads (works across batch tasks)."""

    def __init__(self, limit: int = 3) -> None:
        self._limit = max(1, min(8, int(limit)))
        self._active = 0
        self._waiters: deque[asyncio.Future[None]] = deque()
        self._mutex = asyncio.Lock()

    @property
    def limit(self) -> int:
        return self._limit

    async def acquire(self) -> None:
        async with self._mutex:
            if self._active < self._limit:
                self._active += 1
                return
            loop = asyncio.get_running_loop()
            fut: asyncio.Future[None] = loop.create_future()
            self._waiters.append(fut)
        await fut

    async def release(self) -> None:
        async with self._mutex:
            if self._waiters:
                waiter = self._waiters.popleft()
                if not waiter.done():
                    waiter.set_result(None)
                return
            if self._active > 0:
                self._active -= 1

    async def apply_limit(self, limit: int) -> None:
        """Update the cap and grant slots to waiters when the limit increases."""

        async with self._mutex:
            self._limit = max(1, min(8, int(limit)))
            while self._active < self._limit and self._waiters:
                waiter = self._waiters.popleft()
                if not waiter.done():
                    waiter.set_result(None)
                self._active += 1  # grant slot to a waiter that was blocked

    async def __aenter__(self) -> DownloadParallelLimiter:
        await self.acquire()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.release()


def limiter_from_settings(settings: dict) -> DownloadParallelLimiter:
    try:
        count = int(settings.get('max_parallel_downloads') or 3)
    except (TypeError, ValueError):
        count = 3
    return DownloadParallelLimiter(count)
