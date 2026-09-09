"""Tests for the DOWNTIFY_MONITOR_SYNC_TIME sibling feature: an optional
delay between consecutive downloads in a batch (playlist / album / batch
endpoint) and in Playlist Monitor auto-download sweeps.

Coverage focuses on two things that are easy to get subtly wrong:
  * the delay must never fire after the *last* item in a run (nothing to
    wait for), and single-item runs must not delay at all;
  * the delay setting must reach the right call sites with the right
    value.
"""

from __future__ import annotations

import asyncio

from downtify import api, monitor

# ── _run_download ────────────────────────────────────────────────────────────


class _StubDownloader:
    def __init__(self, *, fail=False):
        self.fail = fail

    def download(self, song, progress_cb, subdir=None):
        if self.fail:
            raise RuntimeError('network error')
        return f'{song["song_id"]}.mp3'


def _prepare_run_download(monkeypatch, *, fail=False):
    monkeypatch.setitem(api.state.download_jobs, 'abc', {'status': 'queued'})
    monkeypatch.setattr(api.state, 'downloader', _StubDownloader(fail=fail))
    monkeypatch.setattr(api.state, 'download_semaphore', None)

    async def fake_broadcast(_msg):
        return None

    monkeypatch.setattr(api.state.connections, 'broadcast', fake_broadcast)

    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(api.asyncio, 'sleep', fake_sleep)
    return sleeps


def test_run_download_sleeps_for_requested_delay(monkeypatch):
    sleeps = _prepare_run_download(monkeypatch)
    song = {'song_id': 'abc'}
    filename = asyncio.run(api._run_download(song, 'abc', delay_seconds=42))
    assert filename == 'abc.mp3'
    assert sleeps == [42]


def test_run_download_does_not_sleep_when_delay_is_zero(monkeypatch):
    sleeps = _prepare_run_download(monkeypatch)
    song = {'song_id': 'abc'}
    asyncio.run(api._run_download(song, 'abc', delay_seconds=0))
    assert sleeps == []


def test_run_download_does_not_sleep_on_failure(monkeypatch):
    sleeps = _prepare_run_download(monkeypatch, fail=True)
    song = {'song_id': 'abc'}
    try:
        asyncio.run(api._run_download(song, 'abc', delay_seconds=42))
    except RuntimeError:
        pass
    assert sleeps == []


# ── _process_batch ───────────────────────────────────────────────────────────


def test_process_batch_skips_delay_for_single_song(monkeypatch):
    monkeypatch.setitem(api.state.settings, 'download_delay_seconds', 30)
    captured = []

    async def fake_run_download(song, song_id, subdir=None, delay_seconds=0):
        captured.append(delay_seconds)
        return f'{song["song_id"]}.mp3'

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    asyncio.run(
        api._process_batch(
            [{'song_id': 'a'}], ['job-a'], playlist_url='', generate_m3u=False
        )
    )
    assert captured == [0]


def test_process_batch_applies_delay_for_multiple_songs(monkeypatch):
    monkeypatch.setitem(api.state.settings, 'download_delay_seconds', 30)
    captured = []

    async def fake_run_download(song, song_id, subdir=None, delay_seconds=0):
        captured.append(delay_seconds)
        return f'{song["song_id"]}.mp3'

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    asyncio.run(
        api._process_batch(
            [{'song_id': 'a'}, {'song_id': 'b'}],
            ['job-a', 'job-b'],
            playlist_url='',
            generate_m3u=False,
        )
    )
    assert captured == [30, 30]


# ── download_album_endpoint ─────────────────────────────────────────────────


def test_download_album_endpoint_skips_delay_for_single_track(monkeypatch):
    monkeypatch.setitem(api.state.settings, 'download_delay_seconds', 15)
    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(
        api,
        '_songs_for_album_download',
        lambda url: [{'song_id': 'only'}],
    )

    captured = []

    async def fake_run_download(song, job_id, subdir=None, delay_seconds=0):
        captured.append(delay_seconds)
        return f'{song["song_id"]}.mp3'

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    asyncio.run(api.download_album_endpoint(url='https://example.com/album'))
    assert captured == [0]


def test_download_album_endpoint_applies_delay_for_multiple_tracks(
    monkeypatch,
):
    monkeypatch.setitem(api.state.settings, 'download_delay_seconds', 15)
    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(
        api,
        '_songs_for_album_download',
        lambda url: [{'song_id': 'a'}, {'song_id': 'b'}],
    )

    captured = []

    async def fake_run_download(song, job_id, subdir=None, delay_seconds=0):
        captured.append(delay_seconds)
        return f'{song["song_id"]}.mp3'

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    asyncio.run(api.download_album_endpoint(url='https://example.com/album'))
    assert captured == [15, 15]


# ── monitor.check_playlist ───────────────────────────────────────────────────


def _playlist():
    return monitor.MonitoredPlaylist(
        id=1,
        spotify_id='pl123',
        name='Test Playlist',
        url='https://open.spotify.com/playlist/pl123',
        interval_minutes=60,
        enabled=True,
        last_checked=None,
        last_track_count=0,
        created_at='2026-01-01T00:00:00+00:00',
    )


class _FakeMonitorDB:
    def __init__(self):
        self.filenames = {}

    def get_track_filenames(self, playlist_id):
        return self.filenames

    def mark_track_downloaded(self, playlist_id, track_id, filename):
        pass

    def update_playlist(self, playlist_id, **kwargs):
        pass


def test_check_playlist_skips_delay_after_last_track(monkeypatch):
    tracks = [
        {'song_id': 'a', 'name': 'A'},
        {'song_id': 'b', 'name': 'B'},
        {'song_id': 'c', 'name': 'C'},
    ]

    monkeypatch.setattr(
        monitor.spotify,
        'playlist_tracks_from_id',
        lambda spotify_id: tracks,
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda track_id: {})

    class _Downloader:
        download_dir = __import__('pathlib').Path('/tmp')
        organize_by_artist = False
        organize_by_album = False

        @staticmethod
        def download(song, cb, subdir=None):
            return f'{song["song_id"]}.mp3'

    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(monitor.asyncio, 'sleep', fake_sleep)

    async def fake_broadcast(_msg):
        return None

    loop = asyncio.new_event_loop()
    try:
        downloaded = loop.run_until_complete(
            monitor.check_playlist(
                _playlist(),
                _FakeMonitorDB(),
                _Downloader(),
                fake_broadcast,
                loop,
                settings={'download_delay_seconds': 10, 'generate_m3u': False},
            )
        )
    finally:
        loop.close()

    assert downloaded == 3
    # 3 tracks -> 2 delays (never after the last one)
    assert sleeps == [10, 10]


def test_check_playlist_no_delay_when_setting_is_zero(monkeypatch):
    tracks = [
        {'song_id': 'a', 'name': 'A'},
        {'song_id': 'b', 'name': 'B'},
    ]

    monkeypatch.setattr(
        monitor.spotify,
        'playlist_tracks_from_id',
        lambda spotify_id: tracks,
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda track_id: {})

    class _Downloader:
        download_dir = __import__('pathlib').Path('/tmp')
        organize_by_artist = False
        organize_by_album = False

        @staticmethod
        def download(song, cb, subdir=None):
            return f'{song["song_id"]}.mp3'

    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(monitor.asyncio, 'sleep', fake_sleep)

    async def fake_broadcast(_msg):
        return None

    loop = asyncio.new_event_loop()
    try:
        downloaded = loop.run_until_complete(
            monitor.check_playlist(
                _playlist(),
                _FakeMonitorDB(),
                _Downloader(),
                fake_broadcast,
                loop,
                settings={'download_delay_seconds': 0, 'generate_m3u': False},
            )
        )
    finally:
        loop.close()

    assert downloaded == 2
    assert sleeps == []
