"""Cancellation must not hide a still-running stream download thread."""

from __future__ import annotations

import asyncio
import gc
import threading
from pathlib import Path
from typing import Any

import pytest

from downtify import api, stream

VIDEOS = ('dQw4w9WgXcQ', 'abcdefghijk', '12345678901')
AUDIO = b'complete cached audio'


class _ControlledFetch:
    def __init__(self, cache: stream.StreamCache) -> None:
        self.cache = cache
        self.loop = asyncio.get_running_loop()
        self.started = {video: asyncio.Event() for video in VIDEOS}
        self.finished = {video: asyncio.Event() for video in VIDEOS}
        self.release = {video: threading.Event() for video in VIDEOS}
        self.calls: list[str] = []
        self.active = 0
        self.peak = 0
        self.fail = False
        self.lock = threading.Lock()

    def __call__(self, video_id: str, cookies_file: str = '') -> None:
        with self.lock:
            self.calls.append(video_id)
            self.active += 1
            self.peak = max(self.peak, self.active)
        self.loop.call_soon_threadsafe(self.started[video_id].set)
        try:
            if not self.release[video_id].wait(timeout=10):
                raise AssertionError('test did not release the download')
            if self.fail:
                raise ValueError('YouTube did not answer')
            (self.cache._dir / f'{video_id}.m4a').write_bytes(AUDIO)
        finally:
            with self.lock:
                self.active -= 1
            self.loop.call_soon_threadsafe(self.finished[video_id].set)

    async def wait_started(self, *videos: str) -> None:
        await asyncio.wait_for(
            asyncio.gather(*(self.started[video].wait() for video in videos)),
            timeout=10,
        )

    async def cleanup(self, *requests: asyncio.Task[Any]) -> None:
        for release in self.release.values():
            release.set()
        jobs = [job.task for job in self.cache._jobs.values()]
        await asyncio.gather(*requests, *jobs, return_exceptions=True)
        await asyncio.wait_for(
            asyncio.gather(
                *(self.finished[video].wait() for video in set(self.calls))
            ),
            timeout=10,
        )


def _cache(tmp_path: Path) -> stream.StreamCache:
    return stream.StreamCache(tmp_path / 'streams', max_concurrent=1)


async def _request(
    cache: stream.StreamCache, video: str
) -> asyncio.Task[Path]:
    task = asyncio.create_task(cache.get(video, max_seconds=0))
    # Let get register its waiter; no wall-clock delay is needed.
    await asyncio.sleep(0)
    return task


async def _cancel(task: asyncio.Task[Any]) -> None:
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0)


@pytest.mark.parametrize('capacity', [1, 2, 3])
def test_cancelled_downloads_keep_their_slots_until_the_threads_finish(
    tmp_path: Path, capacity: int
) -> None:
    async def scenario() -> None:
        cache = stream.StreamCache(
            tmp_path / 'streams', max_concurrent=capacity
        )
        fetch = _ControlledFetch(cache)
        cache._fetch = fetch
        requests = [
            await _request(cache, video) for video in VIDEOS[:capacity]
        ]
        try:
            await fetch.wait_started(*VIDEOS[:capacity])
            for request in requests:
                await _cancel(request)

            assert cache.running == capacity
            assert len(cache._jobs) == capacity
            assert fetch.active == capacity
        finally:
            await fetch.cleanup(*requests)
        assert cache.running == 0
        assert cache._jobs == {}

    asyncio.run(scenario())


def test_another_video_waits_for_a_cancelled_download_to_finish(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        cache = _cache(tmp_path)
        fetch = _ControlledFetch(cache)
        cache._fetch = fetch
        first = await _request(cache, VIDEOS[0])
        second: asyncio.Task[Path] | None = None
        try:
            await fetch.wait_started(VIDEOS[0])
            await _cancel(first)
            second = await _request(cache, VIDEOS[1])

            assert VIDEOS[0] in cache._jobs
            assert not fetch.started[VIDEOS[1]].is_set()
            fetch.release[VIDEOS[0]].set()
            await fetch.wait_started(VIDEOS[1])
            assert fetch.finished[VIDEOS[0]].is_set()
            fetch.release[VIDEOS[1]].set()
            assert (await second).read_bytes() == AUDIO
            assert fetch.peak == 1
        finally:
            await fetch.cleanup(first, *((second,) if second else ()))

    asyncio.run(scenario())


def test_replay_shares_a_download_after_its_only_waiter_was_cancelled(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        cache = _cache(tmp_path)
        fetch = _ControlledFetch(cache)
        cache._fetch = fetch
        first = await _request(cache, VIDEOS[0])
        replays: list[asyncio.Task[Path]] = []
        try:
            await fetch.wait_started(VIDEOS[0])
            job = cache._jobs[VIDEOS[0]]
            await _cancel(first)
            replays = [await _request(cache, VIDEOS[0]) for _ in range(3)]

            assert cache._jobs[VIDEOS[0]] is job
            assert job.waiters == len(replays)
            fetch.release[VIDEOS[0]].set()
            paths = await asyncio.gather(*replays)
            assert all(path.read_bytes() == AUDIO for path in paths)
            assert len(set(paths)) == 1
            assert fetch.calls == [VIDEOS[0]]
            assert job.waiters == 0
        finally:
            await fetch.cleanup(first, *replays)

    asyncio.run(scenario())


def test_cancelling_one_waiter_does_not_cancel_the_other(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        cache = _cache(tmp_path)
        fetch = _ControlledFetch(cache)
        cache._fetch = fetch
        first = await _request(cache, VIDEOS[0])
        second = await _request(cache, VIDEOS[0])
        try:
            await fetch.wait_started(VIDEOS[0])
            job = cache._jobs[VIDEOS[0]]
            await _cancel(first)

            assert not job.task.done()
            assert job.waiters == 1
            fetch.release[VIDEOS[0]].set()
            assert (await second).read_bytes() == AUDIO
            assert fetch.calls == [VIDEOS[0]]
            assert job.waiters == 0
        finally:
            await fetch.cleanup(first, second)

    asyncio.run(scenario())


def test_a_cancelled_queued_download_is_removed_and_can_be_retried(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        cache = _cache(tmp_path)
        fetch = _ControlledFetch(cache)
        cache._fetch = fetch
        first = await _request(cache, VIDEOS[0])
        queued: asyncio.Task[Path] | None = None
        try:
            await fetch.wait_started(VIDEOS[0])
            queued = await _request(cache, VIDEOS[1])
            await _cancel(queued)
            await asyncio.sleep(0)

            assert VIDEOS[1] not in cache._jobs
            assert not fetch.started[VIDEOS[1]].is_set()
            fetch.release[VIDEOS[0]].set()
            assert (await first).read_bytes() == AUDIO
            assert fetch.calls == [VIDEOS[0]]
            fetch.release[VIDEOS[1]].set()
            assert (
                await cache.get(VIDEOS[1], max_seconds=0)
            ).read_bytes() == AUDIO
            assert fetch.calls == [VIDEOS[0], VIDEOS[1]]
        finally:
            await fetch.cleanup(first, *((queued,) if queued else ()))

    asyncio.run(scenario())


def test_immediate_retry_does_not_join_a_cancelling_queued_job(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        cache = _cache(tmp_path)
        fetch = _ControlledFetch(cache)
        cache._fetch = fetch
        first = await _request(cache, VIDEOS[0])
        queued: asyncio.Task[Path] | None = None
        replay: asyncio.Task[Path] | None = None
        try:
            await fetch.wait_started(VIDEOS[0])
            queued = await _request(cache, VIDEOS[1])
            old_job = cache._jobs[VIDEOS[1]]
            queued.cancel()
            # Schedule the new caller before the old job's done callback.
            replay = asyncio.create_task(cache.get(VIDEOS[1], max_seconds=0))
            with pytest.raises(asyncio.CancelledError):
                await queued
            await asyncio.sleep(0)

            assert cache._jobs[VIDEOS[1]] is not old_job
            for release in fetch.release.values():
                release.set()
            assert (await first).read_bytes() == AUDIO
            assert (await replay).read_bytes() == AUDIO
            assert fetch.calls == [VIDEOS[0], VIDEOS[1]]
            assert fetch.peak == 1
        finally:
            requests = [task for task in (first, queued, replay) if task]
            await fetch.cleanup(*requests)

    asyncio.run(scenario())


@pytest.mark.parametrize('fails', [False, True])
def test_finished_downloads_clear_waiters_and_allow_retry(
    tmp_path: Path, fails: bool
) -> None:
    async def scenario() -> None:
        cache = _cache(tmp_path)
        fetch = _ControlledFetch(cache)
        fetch.fail = fails
        cache._fetch = fetch
        requests = [await _request(cache, VIDEOS[0]) for _ in range(2)]
        try:
            await fetch.wait_started(VIDEOS[0])
            job = cache._jobs[VIDEOS[0]]
            fetch.release[VIDEOS[0]].set()
            results = await asyncio.gather(*requests, return_exceptions=True)

            if fails:
                assert all(
                    isinstance(result, ValueError) for result in results
                )
            else:
                assert all(isinstance(result, Path) for result in results)
            assert job.waiters == 0
            assert cache._jobs == {}
            assert cache.running == 0
            fetch.fail = False
            assert (
                await cache.get(VIDEOS[0], max_seconds=0)
            ).read_bytes() == AUDIO
            assert len(fetch.calls) == (2 if fails else 1)
        finally:
            await fetch.cleanup(*requests)

    asyncio.run(scenario())


def test_an_abandoned_failure_is_observed_and_does_not_block_retry(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        cache = _cache(tmp_path)
        fetch = _ControlledFetch(cache)
        fetch.fail = True
        cache._fetch = fetch
        request = await _request(cache, VIDEOS[0])
        loop = asyncio.get_running_loop()
        errors: list[dict[str, Any]] = []
        loop.set_exception_handler(
            lambda _loop, context: errors.append(context)
        )
        try:
            await fetch.wait_started(VIDEOS[0])
            job = cache._jobs[VIDEOS[0]]
            completed = asyncio.Event()
            job.task.add_done_callback(lambda _task: completed.set())
            await _cancel(request)
            fetch.release[VIDEOS[0]].set()
            await asyncio.wait_for(completed.wait(), timeout=10)
            await asyncio.wait_for(
                fetch.finished[VIDEOS[0]].wait(), timeout=10
            )
            await asyncio.sleep(0)
            del request, job
            gc.collect()
            await asyncio.sleep(0)

            assert errors == []
            assert cache._jobs == {}
            assert cache.running == 0
            fetch.fail = False
            assert (
                await cache.get(VIDEOS[0], max_seconds=0)
            ).read_bytes() == AUDIO
        finally:
            loop.set_exception_handler(None)
            await fetch.cleanup()

    asyncio.run(scenario())


def test_cancelling_prefetch_preserves_its_download_for_playback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api.state, 'settings', {'library_only': False})
    monkeypatch.setattr(api.state, 'background_tasks', set())

    async def scenario() -> None:
        cache = _cache(tmp_path)
        fetch = _ControlledFetch(cache)
        cache._fetch = fetch
        prefetch = api.spawn_task(
            api._prefetch_stream_video(cache, VIDEOS[0], '', 0),
            name=f'stream-prefetch-{VIDEOS[0]}',
        )
        playback: asyncio.Task[Path] | None = None
        try:
            await fetch.wait_started(VIDEOS[0])
            job = cache._jobs[VIDEOS[0]]
            await _cancel(prefetch)
            assert prefetch not in api.state.background_tasks
            assert cache._jobs[VIDEOS[0]] is job
            playback = await _request(cache, VIDEOS[0])
            fetch.release[VIDEOS[0]].set()
            assert (await playback).read_bytes() == AUDIO
            assert fetch.calls == [VIDEOS[0]]
        finally:
            await fetch.cleanup(prefetch, *((playback,) if playback else ()))

    asyncio.run(scenario())
