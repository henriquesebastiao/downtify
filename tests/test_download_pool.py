"""Tests for the global download parallel limiter."""

from __future__ import annotations

import asyncio

import pytest

from downtify.download_pool import DownloadParallelLimiter


async def _hold(limiter: DownloadParallelLimiter, delay: float) -> None:
    async with limiter:
        await asyncio.sleep(delay)


@pytest.mark.asyncio
async def test_limiter_caps_concurrent_tasks() -> None:
    limiter = DownloadParallelLimiter(3)
    active = 0
    peak = 0
    lock = asyncio.Lock()

    async def worker(delay: float) -> None:
        nonlocal active, peak
        async with limiter:
            async with lock:
                active += 1
                peak = max(peak, active)
            await asyncio.sleep(delay)
            async with lock:
                active -= 1

    await asyncio.gather(*[worker(0.05) for _ in range(8)])
    assert peak == 3


@pytest.mark.asyncio
async def test_apply_limit_can_raise_cap_for_waiters() -> None:
    limiter = DownloadParallelLimiter(2)
    started: asyncio.Event = asyncio.Event()
    gate: asyncio.Event = asyncio.Event()

    async def blocker() -> None:
        async with limiter:
            started.set()
            await gate.wait()

    t1 = asyncio.create_task(blocker())
    t2 = asyncio.create_task(blocker())
    await started.wait()
    t3 = asyncio.create_task(blocker())
    await asyncio.sleep(0.01)

    await limiter.apply_limit(3)
    gate.set()
    await asyncio.gather(t1, t2, t3)
