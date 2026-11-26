"""A watch downloads as many songs at once as "Parallel downloads" allows
(monitor._side_by_side), not one after another.

Before, each watch held one slot however many were free: three artist
watches with Parallel downloads at 8 ran three songs. All offline - the
providers and the downloader are faked.
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest

from downtify import monitor
from tests.test_artist_watch_duplicates import (
    CHANNEL_ID,
    _album,
    _FakeDownloader,
    _patch,
    _track,
)


@pytest.fixture(autouse=True)
def _restore_slots():
    yield
    monitor.share_download_slots(lambda: None)


class _Counting(_FakeDownloader):
    """The duplicates test's downloader, counting downloads at once."""

    def __init__(self, root):
        super().__init__(root)
        self.running = 0
        self.most = 0
        self._lock = threading.Lock()

    def download(self, song, progress_cb=None, subdir=None):
        with self._lock:
            self.running += 1
            self.most = max(self.most, self.running)
        try:
            threading.Event().wait(0.05)
            return super().download(song, progress_cb, subdir)
        finally:
            with self._lock:
                self.running -= 1


def _singles(count):
    albums = [_album(f'MPREb_s{i}', f'Single {i}') for i in range(count)]
    tracks = {
        a['album_id']: [
            _track(f's{i}', f'Single {i}', a['name'], 1, duration=200)
        ]
        for i, a in enumerate(albums)
    }
    return albums, tracks


def _check_artist(tmp_path, downloader, settings, limit):
    db = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist(
        CHANNEL_ID, 'Drake', 'url', 60, monitor.KIND_ARTIST
    )

    async def scenario():
        if limit:
            sem = asyncio.Semaphore(limit)
            monitor.share_download_slots(lambda: sem)

        async def broadcast(_message):
            return None

        return await monitor.check_artist(
            watch,
            db,
            downloader,
            broadcast,
            asyncio.get_running_loop(),
            settings=settings,
            library=monitor.LibraryStores(listing=list),
        )

    return asyncio.run(scenario()), db, watch


def test_an_artist_watch_fills_every_free_slot(monkeypatch, tmp_path):
    albums, tracks = _singles(6)
    _patch(monkeypatch, albums, tracks)
    downloader = _Counting(tmp_path)

    downloaded, db, watch = _check_artist(
        tmp_path, downloader, {'max_parallel_downloads': 3}, limit=3
    )

    assert downloaded == 6
    assert downloader.most == 3
    # Every release is remembered once its songs are in.
    assert db.get_seen_album_ids(watch.id) == {a['album_id'] for a in albums}


def test_the_shared_limit_still_wins_over_the_setting(monkeypatch, tmp_path):
    """Other downloads hold slots too: the semaphore is the real bound."""

    albums, tracks = _singles(5)
    _patch(monkeypatch, albums, tracks)
    downloader = _Counting(tmp_path)

    _check_artist(tmp_path, downloader, {'max_parallel_downloads': 8}, limit=2)

    assert downloader.most == 2


def test_without_a_shared_limit_a_watch_goes_one_at_a_time(
    monkeypatch, tmp_path
):
    albums, tracks = _singles(3)
    _patch(monkeypatch, albums, tracks)
    downloader = _Counting(tmp_path)

    downloaded, _db, _watch = _check_artist(
        tmp_path, downloader, {'max_parallel_downloads': 8}, limit=None
    )

    assert downloaded == 3
    assert downloader.most == 1


def test_a_song_on_an_album_and_its_deluxe_downloads_once(
    monkeypatch, tmp_path
):
    """The two copies run side by side but wait for each other, so the
    second finds the first one's file instead of downloading again."""

    albums = [_album('MPREb_a', 'Album'), _album('MPREb_d', 'Album (Deluxe)')]
    tracks = {
        'MPREb_a': [_track('t1', 'Song', 'Album', 1, duration=200)],
        'MPREb_d': [
            _track('t1d', 'Song', 'Album (Deluxe)', 1, duration=200),
            _track('t2', 'Bonus', 'Album (Deluxe)', 2, duration=180),
        ],
    }
    _patch(monkeypatch, albums, tracks)
    downloader = _Counting(tmp_path)

    _check_artist(tmp_path, downloader, {'max_parallel_downloads': 4}, limit=4)

    assert sorted(downloader.calls) == ['t1', 't2']


def test_a_release_with_a_failed_song_is_tried_again(monkeypatch, tmp_path):
    albums = [_album('MPREb_a', 'Album'), _album('MPREb_b', 'Other')]
    tracks = {
        'MPREb_a': [
            _track('ok', 'Fine', 'Album', 1, duration=200),
            _track('bad', 'Broken', 'Album', 2, duration=200),
        ],
        'MPREb_b': [_track('b1', 'Else', 'Other', 1, duration=200)],
    }
    _patch(monkeypatch, albums, tracks)

    class _Failing(_Counting):
        def download(self, song, progress_cb=None, subdir=None):
            if song['song_id'] == 'bad':
                raise RuntimeError('no source')
            return super().download(song, progress_cb, subdir)

    downloader = _Failing(tmp_path)
    _downloaded, db, watch = _check_artist(
        tmp_path, downloader, {'max_parallel_downloads': 3}, limit=3
    )

    assert db.get_seen_album_ids(watch.id) == {'MPREb_b'}


# ── playlist watches ────────────────────────────────────────────────────


class _PlaylistDB:
    def __init__(self):
        self.marked = []

    @staticmethod
    def get_track_filenames(playlist_id):
        return {}

    def mark_track_downloaded(self, playlist_id, track_id, filename, **_kw):
        self.marked.append(track_id)

    def update_playlist(self, playlist_id, **kwargs):
        pass


def test_a_playlist_watch_fills_every_free_slot(monkeypatch, tmp_path):
    tracks = [{'song_id': f'p{i}', 'name': f'P{i}'} for i in range(6)]
    monkeypatch.setattr(
        monitor.spotify, 'playlist_tracks_from_id', lambda _id: tracks
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda _id: {})

    class _Downloader:
        download_dir = Path(tmp_path)
        organize_by_artist = False
        organize_by_album = False
        running = 0
        most = 0
        lock = threading.Lock()

        def download(self, song, cb, subdir=None):
            with self.lock:
                self.running += 1
                self.most = max(self.most, self.running)
            threading.Event().wait(0.05)
            with self.lock:
                self.running -= 1
            return f'{song["song_id"]}.mp3'

    downloader = _Downloader()
    db = _PlaylistDB()
    playlist = monitor.MonitoredPlaylist(
        id=1,
        spotify_id='pl123',
        name='Mix',
        url='https://open.spotify.com/playlist/pl123',
        interval_minutes=60,
        enabled=True,
        last_checked=None,
        last_track_count=0,
        created_at='2026-01-01T00:00:00+00:00',
    )

    async def scenario():
        sem = asyncio.Semaphore(4)
        monitor.share_download_slots(lambda: sem)

        async def broadcast(_message):
            return None

        return await monitor.check_playlist(
            playlist,
            db,
            downloader,
            broadcast,
            asyncio.get_running_loop(),
            settings={'max_parallel_downloads': 4, 'generate_m3u': False},
        )

    assert asyncio.run(scenario()) == 6
    assert downloader.most == 4
    assert sorted(db.marked) == sorted(t['song_id'] for t in tracks)
