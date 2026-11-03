from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from starlette.requests import Request

from downtify import api, library_upgrade, monitor, podcasts
from downtify.download_queue import QueuePause, queue_pause


@pytest.fixture(autouse=True)
def unpause():
    queue_pause.resume()
    yield
    queue_pause.resume()


@pytest.mark.asyncio
async def test_global_pause_uses_upgrade_native_pause_and_reports_draining(
    monkeypatch,
):
    runner = Mock()
    runner.busy.return_value = True
    monkeypatch.setattr(api.state, 'upgrade_runner', runner)
    monkeypatch.setattr(api.state, 'pending_downloads', None)

    async def broadcast():
        pass

    monkeypatch.setattr(api, '_broadcast_queue_state', broadcast)
    status = await api._set_queue_paused(True)
    runner.pause.assert_called_once()
    assert status['state'] == 'pausing'
    assert status['active'] == 1
    runner.busy.return_value = False
    assert api._global_queue_status()['state'] == 'paused'
    await api._set_queue_paused(False)
    runner.resume.assert_not_called()


def test_upgrade_cannot_start_during_global_pause():
    queue_pause.pause()
    runner = object.__new__(library_upgrade.LibraryUpgradeRunner)
    with pytest.raises(RuntimeError, match='global queue'):
        runner.start(('audio',))


def test_running_upgrade_is_preserved_paused_after_restart():
    queue_pause.pause()
    runner = object.__new__(library_upgrade.LibraryUpgradeRunner)
    runner.db = Mock()
    runner.db.latest_run.return_value = {
        'id': 7,
        'state': library_upgrade.STATE_RUNNING,
    }
    runner.resume_after_restart()
    runner.db.requeue_running.assert_called_once_with(7)
    runner.db.set_state.assert_called_once_with(
        7, library_upgrade.STATE_PAUSED
    )


@pytest.mark.asyncio
async def test_running_context_cannot_start_a_download_after_pause():
    pause = QueuePause()
    pause.pause()
    entered = asyncio.Event()

    async def download():
        async with pause.running():
            entered.set()

    task = asyncio.create_task(download())
    try:
        await asyncio.sleep(0)
        assert not entered.is_set()
        assert pause.active == 0
        pause.resume()
        await asyncio.wait_for(task, 1)
        assert entered.is_set()
        assert pause.active == 0
    finally:
        pause.resume()
        task.cancel()


@pytest.mark.asyncio
async def test_paused_monitor_sweep_does_not_read_or_check_watches(
    monkeypatch,
):
    read = asyncio.Event()

    async def fake_to_thread(*args, **kwargs):
        read.set()
        return []

    monkeypatch.setattr(monitor.asyncio, 'to_thread', fake_to_thread)
    queue_pause.pause()
    task = asyncio.create_task(
        monitor.monitor_loop(
            SimpleNamespace(list_playlists=Mock()),
            lambda: None,
            Mock(),
            asyncio.get_running_loop(),
        )
    )
    try:
        await asyncio.sleep(0)
        assert not read.is_set()
        queue_pause.resume()
        await asyncio.wait_for(read.wait(), 1)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


def test_queue_state_advertises_global_scope_and_separate_admin_permission(
    monkeypatch,
):
    request = Request({'type': 'http', 'headers': []})
    monkeypatch.setattr(api, 'request_is_admin', lambda _: False)
    status = api.get_queue_state(request)
    assert status['global_pause_supported']
    assert not status['can_control']
    queue_pause.pause()
    assert api.get_queue_state(request)['monitors_paused']
    monkeypatch.setattr(api, 'request_is_admin', lambda _: True)
    assert api.get_queue_state(request)['can_control']


def test_paused_podcast_sync_does_not_fetch_a_feed(monkeypatch, tmp_path):
    fetch = Mock()
    monkeypatch.setattr(podcasts, 'fetch_feed', fetch)
    assert (
        podcasts.sync_show(
            Mock(),
            {'feed_url': 'https://example.test/feed'},
            tmp_path,
            should_continue=lambda: False,
        )
        == 0
    )
    fetch.assert_not_called()


def test_podcast_pause_finishes_current_episode_without_starting_next(
    monkeypatch, tmp_path
):
    feed = SimpleNamespace(
        episodes=[], description='', author='', artwork_url=''
    )
    monkeypatch.setattr(podcasts, 'fetch_feed', lambda _: feed)
    rows = [
        {
            key: ''
            for key in (
                'guid',
                'title',
                'description',
                'published_at',
                'duration_seconds',
                'season_number',
                'episode_number',
                'enclosure_url',
                'enclosure_type',
            )
        }
        for _ in range(2)
    ]
    for i, row in enumerate(rows):
        row['id'] = i + 1
    monkeypatch.setattr(podcasts, 'episode_plan', lambda *args: (rows, []))
    monkeypatch.setattr(podcasts, 'best_cover_bytes', lambda _: None)
    monkeypatch.setattr(podcasts, 'EpisodeInfo', lambda **kwargs: object())
    allowed = [True]

    def download(*args, **kwargs):
        allowed[0] = False
        return 'podcasts/episode.mp3'

    download = Mock(side_effect=download)
    monkeypatch.setattr(podcasts, 'download_episode', download)
    store = Mock()
    show = {
        'id': 1,
        'feed_url': 'https://example.test/feed',
        'name': 'Test',
        'description': '',
        'author': '',
        'artwork_url': '',
        'folder_name': 'Test',
    }
    assert (
        podcasts.sync_show(
            store,
            show,
            tmp_path,
            should_continue=lambda: allowed[0],
        )
        == 1
    )
    download.assert_called_once()
    store.mark_downloaded.assert_called_once_with(1, 'podcasts/episode.mp3')


def test_admin_device_is_not_advertised_as_web_control(monkeypatch):
    request = Request({
        'type': 'http',
        'headers': [],
        'state': {'principal': SimpleNamespace(kind='device')},
    })
    monkeypatch.setattr(api, 'request_is_admin', lambda request: True)
    assert not api.get_queue_state(request)['can_control']
