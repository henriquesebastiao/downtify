"""Pausing and resuming the download queue, and keeping it across
restarts (``downtify/download_queue.py`` and its use in ``api.py``)."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from downtify import api, monitor
from downtify.auth import ADMIN, CLIENT, ROLE_ADMIN, Principal, classify
from downtify.download_queue import (
    STATE_PAUSED,
    STATE_PAUSING,
    STATE_RUNNING,
    PendingDownload,
    PendingDownloads,
    QueuePause,
    queue_pause,
)


class _Downloader:
    """Blocks in ``download`` until the test lets it finish."""

    def __init__(self) -> None:
        self.started: list[str] = []
        self.release = threading.Event()
        self.overwrite_existing_files = True

    def download(self, song, progress, subdir=None):
        self.started.append(song['song_id'])
        self.release.wait(5)


@pytest.fixture
def queue(monkeypatch, tmp_path):
    """A clean queue, a fake downloader and a saved-queue store."""

    downloader = _Downloader()
    connections = MagicMock()
    connections.broadcast = AsyncMock()
    connections.broadcast_job = AsyncMock()
    store = PendingDownloads(tmp_path / 'library.db')
    monkeypatch.setattr(api.state, 'downloader', downloader)
    monkeypatch.setattr(api.state, 'connections', connections)
    monkeypatch.setattr(api.state, 'download_semaphore', None)
    monkeypatch.setattr(api.state, 'loop', None)
    monkeypatch.setattr(api.state, 'pending_downloads', store)
    monkeypatch.setattr(api.state, 'settings', dict(api.DEFAULT_SETTINGS))
    api.state.download_jobs.clear()
    queue_pause.resume()
    yield downloader, connections, store
    downloader.release.set()
    queue_pause.resume()
    api.state.download_jobs.clear()


def _song(song_id: str) -> dict[str, Any]:
    return {'song_id': song_id, 'name': song_id, 'artists': ['Artist']}


async def _until(check, timeout: float = 5.0) -> None:
    async def _poll() -> None:
        while not check():
            await asyncio.sleep(0.01)

    await asyncio.wait_for(_poll(), timeout)


def _admin_request() -> Request:
    principal = Principal('session', 'admin', '', 1, 'admin', ROLE_ADMIN)
    return Request({
        'type': 'http',
        'headers': [],
        'state': {'principal': principal},
    })


def _states(connections: MagicMock) -> list[str]:
    return [
        call.args[0]['state']
        for call in connections.broadcast.call_args_list
        if call.args and call.args[0].get('type') == 'queue_state'
    ]


# ── the switch ──────────────────────────────────────────────────────────


def test_wait_returns_at_once_while_running():
    pause = QueuePause()

    asyncio.run(asyncio.wait_for(pause.wait(), 1))

    assert pause.state == STATE_RUNNING


def test_wait_holds_until_resumed():
    pause = QueuePause()
    pause.pause()

    async def scenario() -> bool:
        waiter = asyncio.create_task(pause.wait())
        await asyncio.sleep(0.05)
        held = not waiter.done()
        pause.resume()
        await asyncio.wait_for(waiter, 1)
        return held

    assert asyncio.run(scenario()) is True


def test_state_drains_from_pausing_to_paused():
    pause = QueuePause()
    drained = AsyncMock()
    pause.on_drained = drained

    async def scenario() -> list[str]:
        seen = []
        async with pause.running():
            pause.pause()
            seen.append(pause.state)
        seen.append(pause.state)
        return seen

    assert asyncio.run(scenario()) == [STATE_PAUSING, STATE_PAUSED]
    drained.assert_awaited_once()
    assert pause.status() == {
        'paused': True,
        'state': STATE_PAUSED,
        'active': 0,
    }


def test_running_queue_never_announces_a_drain():
    pause = QueuePause()
    drained = AsyncMock()
    pause.on_drained = drained

    async def scenario() -> None:
        async with pause.running():
            pass

    asyncio.run(scenario())

    drained.assert_not_awaited()


# ── the saved queue ─────────────────────────────────────────────────────


def test_saved_rows_keep_queue_order_and_merge_waiters(tmp_path: Path):
    store = PendingDownloads(tmp_path / 'library.db')

    store.add([
        PendingDownload('a', _song('a'), {'playlist_name': 'Mix'}, [1]),
        PendingDownload('b', _song('b'), {}, [2]),
    ])
    # Asked for again by someone else: same place, same options.
    store.add([PendingDownload('a', _song('a'), {'playlist_name': 'X'}, [3])])

    rows = store.rows()
    assert [row.song_id for row in rows] == ['a', 'b']
    assert rows[0].options == {'playlist_name': 'Mix'}
    assert rows[0].user_ids == [1, 3]
    assert rows[0].song == _song('a')


def test_forgotten_and_cleared_rows_are_gone(tmp_path: Path):
    store = PendingDownloads(tmp_path / 'library.db')
    store.add([PendingDownload(sid, _song(sid)) for sid in 'abc'])

    store.forget(['b'])
    assert [row.song_id for row in store.rows()] == ['a', 'c']

    store.clear()
    assert store.rows() == []


def test_pause_switch_is_saved(tmp_path: Path):
    db = tmp_path / 'library.db'
    assert PendingDownloads(db).paused() is False

    PendingDownloads(db).set_paused(True)
    assert PendingDownloads(db).paused() is True

    PendingDownloads(db).set_paused(False)
    assert PendingDownloads(db).paused() is False


# ── downloads under a paused queue ──────────────────────────────────────


def test_paused_queue_starts_nothing_until_resumed(queue):
    downloader, connections, store = queue

    async def scenario() -> None:
        await api.pause_queue()
        song_id = api._register_job(_song('s1'), status='downloading')
        task = asyncio.create_task(api._run_download(_song('s1'), song_id))
        await _until(lambda: bool(store.rows()))
        await asyncio.sleep(0.05)

        assert downloader.started == []
        # A single download registers as downloading; paused, it waits.
        assert api.state.download_jobs[song_id]['status'] == 'queued'

        downloader.release.set()
        await api.resume_queue()
        await asyncio.wait_for(task, 5)

    asyncio.run(scenario())

    assert downloader.started == ['s1']
    assert api.state.download_jobs['s1']['status'] == 'done'
    assert store.rows() == []
    assert _states(connections) == [STATE_PAUSED, STATE_RUNNING]


def test_running_download_finishes_then_queue_reads_paused(queue):
    downloader, connections, _store = queue

    async def scenario() -> list[str]:
        song_id = api._register_job(_song('s1'), status='queued')
        task = asyncio.create_task(api._run_download(_song('s1'), song_id))
        await _until(lambda: downloader.started == ['s1'])

        pausing = await api.pause_queue()
        downloader.release.set()
        await asyncio.wait_for(task, 5)
        return [pausing['state'], api.get_queue_state()['state']]

    assert asyncio.run(scenario()) == [STATE_PAUSING, STATE_PAUSED]
    assert api.state.download_jobs['s1']['status'] == 'done'
    # Pausing, then the frame the last finished download sends.
    assert _states(connections) == [STATE_PAUSING, STATE_PAUSED]


def test_job_removed_while_paused_never_starts(queue):
    downloader, _connections, store = queue

    async def scenario():
        await api.pause_queue()
        song_id = api._register_job(_song('s1'), status='queued')
        task = asyncio.create_task(api._run_download(_song('s1'), song_id))
        await _until(lambda: bool(store.rows()))

        api.remove_queue_item(_admin_request(), song_id='s1')
        assert store.rows() == []

        await api.resume_queue()
        return await asyncio.wait_for(task, 5)

    assert asyncio.run(scenario()) is None
    assert downloader.started == []


def test_shutdown_keeps_the_saved_job(queue):
    _downloader, _connections, store = queue

    async def scenario() -> None:
        await api.pause_queue()
        song_id = api._register_job(_song('s1'), status='queued')
        task = asyncio.create_task(api._run_download(_song('s1'), song_id))
        await _until(lambda: bool(store.rows()))
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())

    assert [row.song_id for row in store.rows()] == ['s1']
    assert store.paused() is True


def test_clearing_the_queue_forgets_saved_jobs(queue):
    _downloader, _connections, store = queue
    store.add([PendingDownload(sid, _song(sid)) for sid in ('a', 'b')])
    for sid in ('a', 'b'):
        api._register_job(_song(sid), status='queued')

    api.clear_queue(_admin_request())

    assert store.rows() == []


# ── after a restart ─────────────────────────────────────────────────────


def test_restart_restores_the_paused_queue(queue, monkeypatch):
    downloader, _connections, store = queue
    queue_pause.resume()
    store.set_paused(True)
    store.add([
        PendingDownload(
            's1',
            _song('s1'),
            {'subdir': 'Mix', 'track_order': 4, 'playlist_name': 'Mix'},
            [7],
        )
    ])
    seen: dict[str, Any] = {}
    real_run = api._run_download

    async def spy(song, song_id, **kwargs):
        seen.update(kwargs)
        return await real_run(song, song_id, **kwargs)

    monkeypatch.setattr(api, '_run_download', spy)
    monkeypatch.setattr(
        api, '_schedule_playlist_refresh_after_download', AsyncMock()
    )

    async def scenario() -> int:
        restored = await api.restore_download_queue()
        await asyncio.sleep(0.05)
        assert queue_pause.state == STATE_PAUSED
        assert downloader.started == []
        assert api.state.download_jobs['s1']['status'] == 'queued'
        assert api.state.download_jobs['s1']['user_ids'] == {7}

        downloader.release.set()
        await api.resume_queue()
        await _until(lambda: not store.rows())
        return restored

    assert asyncio.run(scenario()) == 1
    assert downloader.started == ['s1']
    assert seen['subdir'] == 'Mix'
    assert seen['track_order'] == 4
    assert seen['playlist_name'] == 'Mix'
    assert seen['user_id'] == 7
    # A playlist's rows refresh it once at the end, as a batch does.
    assert seen['refresh_playlists'] is False


def test_library_only_mode_keeps_saved_jobs_for_later(queue, monkeypatch):
    downloader, _connections, store = queue
    store.add([PendingDownload('s1', _song('s1'))])
    monkeypatch.setitem(api.state.settings, 'library_only', True)

    assert asyncio.run(api.restore_download_queue()) == 0
    assert [row.song_id for row in store.rows()] == ['s1']
    assert api.state.download_jobs == {}
    assert downloader.started == []


# ── Playlist Monitor ────────────────────────────────────────────────────


def test_monitor_sweep_waits_while_paused(monkeypatch, tmp_path):
    db = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist('pl1', 'My Playlist', 'url', 60)
    tracks = [{'song_id': 'a', 'name': 'A', 'artists': ['Artist']}]
    monkeypatch.setattr(
        monitor.spotify, 'playlist_tracks_from_id', lambda _sid: tracks
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda _tid: {})
    calls: list[str] = []

    class _Downloader:
        organize_by_artist = False
        organize_by_album = False
        download_dir = tmp_path

        @staticmethod
        def download(song, progress_cb=None, subdir=None):
            calls.append(song['song_id'])
            return f'{song["song_id"]}.mp3'

    async def _broadcast(_msg):
        return None

    async def scenario() -> int:
        queue_pause.pause()
        sweep = asyncio.create_task(
            monitor.check_playlist(
                watch,
                db,
                _Downloader(),
                _broadcast,
                asyncio.get_running_loop(),
                settings={'generate_m3u': False},
            )
        )
        await asyncio.sleep(0.1)
        assert calls == []
        queue_pause.resume()
        return await asyncio.wait_for(sweep, 5)

    try:
        assert asyncio.run(scenario()) == 1
    finally:
        queue_pause.resume()
    assert calls == ['a']


# ── access ──────────────────────────────────────────────────────────────


def test_anyone_reads_the_state_only_admins_switch_it():
    assert classify('GET', '/api/queue/state') == CLIENT
    assert classify('POST', '/api/queue/pause') == ADMIN
    assert classify('POST', '/api/queue/resume') == ADMIN
