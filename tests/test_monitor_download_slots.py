"""A watch's downloads share the "Parallel downloads" limit with every
other download (issue #548)."""

from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

import pytest

from downtify import monitor


@pytest.fixture(autouse=True)
def _restore_slots():
    yield
    monitor.share_download_slots(lambda: None)


class _Downloader:
    """Counts downloads running at once."""

    def __init__(self) -> None:
        self.running = 0
        self.most = 0
        self._lock = threading.Lock()

    def download(self, song, progress, subdir=None):
        with self._lock:
            self.running += 1
            self.most = max(self.most, self.running)
        threading.Event().wait(0.05)
        with self._lock:
            self.running -= 1
        return f'{song["song_id"]}.mp3'


class _DB:
    def mark_track_downloaded(self, *args, **kwargs):
        pass


def _fetch(song_id, downloader, broadcast, loop):
    return monitor._fetch_watch_track(
        {'song_id': song_id, 'name': song_id},
        SimpleNamespace(id=1, name='Watch'),
        _DB(),
        downloader,
        broadcast,
        loop,
        subdir='',
        initial=False,
    )


@pytest.mark.parametrize('limit', [1, 2])
def test_checks_never_run_more_downloads_than_the_limit(limit):
    async def run():
        sem = asyncio.Semaphore(limit)
        monitor.share_download_slots(lambda: sem)
        sent = []

        async def broadcast(message):
            sent.append(message)

        loop = asyncio.get_running_loop()
        downloader = _Downloader()
        # Five watches checked at once, as when many are added together.
        await asyncio.gather(
            *(_fetch(f's{i}', downloader, broadcast, loop) for i in range(5))
        )
        return downloader.most, sent

    most, sent = asyncio.run(run())

    assert most == limit
    waiting = [m for m in sent if m.get('status') == 'queued']
    assert waiting  # songs that waited for a slot showed as queued
    assert all(m['playlist_name'] == 'Watch' for m in waiting)


def test_a_free_slot_starts_at_once_without_a_waiting_message():
    async def run():
        sem = asyncio.Semaphore(3)
        monitor.share_download_slots(lambda: sem)
        sent = []

        async def broadcast(message):
            sent.append(message)

        await _fetch(
            's1', _Downloader(), broadcast, asyncio.get_running_loop()
        )
        return sent

    assert asyncio.run(run()) == []


def test_without_a_limit_downloads_are_not_held():
    async def run():
        async def broadcast(message):
            pass

        downloader = _Downloader()
        loop = asyncio.get_running_loop()
        await asyncio.gather(
            *(_fetch(f's{i}', downloader, broadcast, loop) for i in range(3))
        )
        return downloader.most

    assert asyncio.run(run()) >= 1


def test_a_limit_changed_in_settings_is_picked_up():
    """The limit is read on every download: Settings replaces the
    semaphore when Parallel downloads changes."""

    holder = {'sem': None}
    monitor.share_download_slots(lambda: holder['sem'])

    async def run():
        holder['sem'] = asyncio.Semaphore(1)
        async with holder['sem']:
            entered = asyncio.Event()

            async def broadcast(message):
                pass

            async def inside():
                async with monitor._download_slot({}, 'W', broadcast):
                    entered.set()

            task = asyncio.create_task(inside())
            await asyncio.sleep(0.01)
            blocked = not entered.is_set()
        await task
        return blocked, entered.is_set()

    assert asyncio.run(run()) == (True, True)
