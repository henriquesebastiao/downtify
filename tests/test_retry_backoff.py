"""A watch tries a failing song less often the longer it fails, and all
of them again after an update or a change of sources
(``downtify/retry_backoff.py``)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from downtify import api, retry_backoff, watch_history
from downtify.download_queue import PendingDownload, PendingDownloads
from downtify.monitor import PlaylistMonitorDB
from tests.test_watch_history import (
    TRACK_A,
    TRACK_B,
    _Downloader,
    _song,
    _sweep,
    _watch,
)

NOW = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _never_started_over():
    retry_backoff.set_started_over(None)
    yield
    retry_backoff.set_started_over(None)


def _failing_since(first: timedelta, last: timedelta = timedelta(0)):
    return (NOW - first).isoformat(), (NOW - last).isoformat()


@pytest.mark.parametrize(
    ('failing_for', 'wait'),
    [
        (timedelta(0), timedelta(hours=1)),
        (timedelta(hours=2), timedelta(hours=1)),
        (timedelta(days=4), timedelta(days=1)),
        (timedelta(days=60), timedelta(days=7)),
    ],
)
def test_the_wait_grows_with_how_long_the_song_fails(failing_for, wait):
    first, last = _failing_since(failing_for)
    assert retry_backoff.next_try(first, last) == NOW + wait


def test_a_failure_from_before_the_start_over_is_tried_now():
    first, last = _failing_since(timedelta(days=30), timedelta(hours=2))
    since = NOW - timedelta(hours=1)
    assert retry_backoff.next_try(first, last, since) is None


def test_after_a_start_over_the_wait_counts_from_it():
    # Failing for a month, but again only 20 minutes after the update:
    # it waits as a song that just started failing.
    first, last = _failing_since(timedelta(days=30), timedelta(minutes=10))
    since = NOW - timedelta(minutes=30)
    assert retry_backoff.next_try(first, last, since) == (
        NOW - timedelta(minutes=10) + retry_backoff.MIN_WAIT
    )


def test_waiting_lists_only_songs_not_due_yet():
    rows = [
        {
            'track_id': 'recent',
            'first_failed_at': (NOW - timedelta(minutes=5)).isoformat(),
            'last_failed_at': (NOW - timedelta(minutes=5)).isoformat(),
        },
        {
            'track_id': 'due',
            'first_failed_at': (NOW - timedelta(hours=3)).isoformat(),
            'last_failed_at': (NOW - timedelta(hours=2)).isoformat(),
        },
    ]
    assert set(retry_backoff.waiting(rows, NOW)) == {'recent'}
    with retry_backoff.every_failure():
        assert retry_backoff.waiting(rows, NOW) == {}


def _db_with_failing_watch(tmp_path, monkeypatch):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    _watch(db)
    downloader = _Downloader(tmp_path / 'downloads')
    downloader.failing = {TRACK_A}
    tracks = [_song(TRACK_A, 'Alpha'), _song(TRACK_B, 'Beta')]
    _sweep(monkeypatch, db, downloader, tracks)
    return db, downloader, tracks


def test_a_check_skips_a_song_that_just_failed(tmp_path, monkeypatch):
    db, downloader, tracks = _db_with_failing_watch(tmp_path, monkeypatch)
    [watch] = db.list_playlists()
    tried: list[str] = []
    real = downloader.download

    def _download(song, cb, subdir=None):
        tried.append(song['song_id'])
        return real(song, cb, subdir)

    downloader.download = _download
    downloader.failing = set()

    _sweep(monkeypatch, db, downloader, tracks)
    assert tried == []
    [failure] = db.history.failures(watch.id)
    assert failure['attempts'] == 1

    # Check now tries it anyway.
    with retry_backoff.every_failure():
        _sweep(monkeypatch, db, downloader, tracks)
    assert tried == [TRACK_A]
    assert db.history.failures(watch.id) == []


def test_a_song_is_tried_again_once_its_wait_is_over(tmp_path, monkeypatch):
    db, downloader, tracks = _db_with_failing_watch(tmp_path, monkeypatch)
    [watch] = db.list_playlists()
    later = datetime.now(timezone.utc) + timedelta(hours=1, minutes=1)
    monkeypatch.setattr(watch_history, '_now_iso', later.isoformat)

    class _Later(datetime):
        @classmethod
        def now(cls, tz=None):
            return later

    monkeypatch.setattr(retry_backoff, 'datetime', _Later)
    _sweep(monkeypatch, db, downloader, tracks)

    [failure] = db.history.failures(watch.id)
    assert failure['attempts'] == 2


def test_a_start_over_tries_every_failing_song(tmp_path, monkeypatch):
    db, downloader, tracks = _db_with_failing_watch(tmp_path, monkeypatch)
    [watch] = db.list_playlists()
    retry_backoff.start_over(datetime.now(timezone.utc) + timedelta(seconds=1))

    _sweep(monkeypatch, db, downloader, tracks)

    [failure] = db.history.failures(watch.id)
    assert failure['attempts'] == 2


def test_the_watch_page_says_when_each_song_is_tried(tmp_path, monkeypatch):
    db, _downloader, _tracks = _db_with_failing_watch(tmp_path, monkeypatch)
    [watch] = db.list_playlists()

    [failure] = api._failures_with_next_try(db.history.failures(watch.id))
    assert datetime.fromisoformat(failure['next_try']) > datetime.now(
        timezone.utc
    )

    retry_backoff.start_over(datetime.now(timezone.utc) + timedelta(seconds=1))
    [failure] = api._failures_with_next_try(db.history.failures(watch.id))
    assert failure['next_try'] is None


def _store_with_failed_job(tmp_path):
    store = PendingDownloads(tmp_path / 'library.db')
    store.save_failed(
        PendingDownload(
            song_id='sp1',
            song={'song_id': 'sp1', 'name': 'Track'},
            options={'playlist_name': 'Mix'},
            user_ids=[7],
        ),
        'Error: The page needs to be reloaded.',
    )
    return store


def test_requeue_failed_moves_the_jobs_to_the_queue(tmp_path):
    store = _store_with_failed_job(tmp_path)

    assert store.requeue_failed() == 1

    assert store.failed_rows() == []
    [row] = store.rows()
    assert row.song_id == 'sp1'
    assert row.options == {'playlist_name': 'Mix'}
    assert row.user_ids == [7]
    assert store.requeue_failed() == 0


def _start(monkeypatch, store, fingerprint):
    monkeypatch.setattr(api.state, 'pending_downloads', store)
    monkeypatch.setattr(api.state, 'retry_failed_after_update', False)
    monkeypatch.setattr(retry_backoff, 'fingerprint', lambda: fingerprint)
    return api.load_retry_waits()


def test_an_update_retries_the_failed_downloads_once(tmp_path, monkeypatch):
    store = _store_with_failed_job(tmp_path)
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api.state, 'downloader', None)

    # The first start that keeps the versions has nothing to compare with.
    assert _start(monkeypatch, store, 'v1') is False
    assert retry_backoff.started_over() is None
    assert _start(monkeypatch, store, 'v1') is False

    assert _start(monkeypatch, store, 'v2') is True
    moment = retry_backoff.started_over()
    assert moment is not None
    asyncio.run(api.restore_download_queue())
    assert store.failed_rows() == []
    assert [row.song_id for row in store.rows()] == ['sp1']
    assert api.state.retry_failed_after_update is False

    # The next start (same versions) keeps when the waits started over.
    retry_backoff.set_started_over(None)
    assert _start(monkeypatch, store, 'v2') is False
    assert retry_backoff.started_over() == moment


def test_other_audio_sources_start_the_waits_over(tmp_path, monkeypatch):
    store = PendingDownloads(tmp_path / 'library.db')
    monkeypatch.setattr(api.state, 'pending_downloads', store)
    monkeypatch.setattr(
        api.state, 'settings', {**api.DEFAULT_SETTINGS}, raising=False
    )
    monkeypatch.setattr(api.state, 'downloader', None)
    monkeypatch.setattr(api.state, 'settings_path', None)

    async def _no_log(*_a, **_k):
        return None

    monkeypatch.setattr(api, 'log_activity', _no_log)

    class _Request:
        @staticmethod
        async def json():
            return {'audio_providers': ['youtube', 'youtube-music']}

    asyncio.run(api.update_settings_endpoint(_Request(), client_id=''))

    assert retry_backoff.started_over() is not None
    assert store.state_value('retry_started_over') is not None
