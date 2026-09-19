"""Tests for playlist cover art downloads (TSK-003 / TSK-004).

Covers the source-dispatch helpers in ``monitor.py``, the gating/error
handling in ``download_playlist_cover``, and the places that
trigger it: a manual playlist download (``api._process_batch`` — the
actual path the frontend hits when a Spotify/YouTube Music playlist
link is pasted), the ``/api/playlist/m3u`` endpoint (not currently
called by the frontend, but kept working for whoever else calls it),
and a Playlist Monitor sweep's final M3U rewrite.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

from downtify import api, monitor
from downtify import downloader as downloader_mod
from downtify.downloader import Downloader
from downtify.monitor import (
    SOURCE_SPOTIFY,
    SOURCE_YOUTUBE_MUSIC,
    download_playlist_cover,
    fetch_playlist_cover_url,
)

PLAYLIST_NAME = 'My Playlist'


# ── fetch_playlist_cover_url ────────────────────────────────────────────────


def test_fetch_playlist_cover_url_dispatches_to_spotify(monkeypatch):
    monkeypatch.setattr(
        monitor.spotify,
        'playlist_cover_url_from_id',
        lambda pid: f'spotify-cover-{pid}',
    )
    assert (
        fetch_playlist_cover_url(SOURCE_SPOTIFY, 'pl1') == 'spotify-cover-pl1'
    )


def test_fetch_playlist_cover_url_dispatches_to_youtube_music(monkeypatch):
    monkeypatch.setattr(
        monitor.providers,
        'playlist_cover_url_from_id',
        lambda pid: f'ytm-cover-{pid}',
    )
    assert (
        fetch_playlist_cover_url(SOURCE_YOUTUBE_MUSIC, 'pl1')
        == 'ytm-cover-pl1'
    )


# ── download_playlist_cover ──────────────────────────────────────


def test_download_playlist_cover_noop_when_setting_disabled(
    monkeypatch, tmp_path
):
    def _boom(*_a, **_kw):
        raise AssertionError('should not resolve a cover when disabled')

    monkeypatch.setattr(monitor, 'fetch_playlist_cover_url', _boom)
    result = download_playlist_cover(
        SOURCE_SPOTIFY,
        'pl1',
        tmp_path / f'{PLAYLIST_NAME}.m3u',
        {'download_cover_art_playlists': False},
    )
    assert result is None


def test_download_playlist_cover_noop_when_setting_absent(
    monkeypatch, tmp_path
):
    # Same as disabled: an older settings.json without the key must not
    # start fetching covers.
    def _boom(*_a, **_kw):
        raise AssertionError('should not resolve a cover when unset')

    monkeypatch.setattr(monitor, 'fetch_playlist_cover_url', _boom)
    result = download_playlist_cover(
        SOURCE_SPOTIFY, 'pl1', tmp_path / f'{PLAYLIST_NAME}.m3u', {}
    )
    assert result is None


def test_download_playlist_cover_swallows_fetch_errors(monkeypatch, tmp_path):
    def _boom(*_a, **_kw):
        raise RuntimeError('network is down')

    monkeypatch.setattr(monitor, 'fetch_playlist_cover_url', _boom)
    result = download_playlist_cover(
        SOURCE_SPOTIFY,
        'pl1',
        tmp_path / f'{PLAYLIST_NAME}.m3u',
        {'download_cover_art_playlists': True},
    )
    assert result is None


def test_download_playlist_cover_noop_when_no_cover_url(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, 'fetch_playlist_cover_url', lambda *_a: '')
    calls = []
    monkeypatch.setattr(
        monitor, 'save_playlist_cover', lambda *a: calls.append(a)
    )
    result = download_playlist_cover(
        SOURCE_SPOTIFY,
        'pl1',
        tmp_path / f'{PLAYLIST_NAME}.m3u',
        {'download_cover_art_playlists': True},
    )
    assert result is None
    assert calls == []


def test_download_playlist_cover_saves_when_enabled(monkeypatch, tmp_path):
    monkeypatch.setattr(
        monitor, 'fetch_playlist_cover_url', lambda *_a: 'https://img/cover'
    )
    m3u_path = tmp_path / f'{PLAYLIST_NAME}.m3u'
    monkeypatch.setattr(
        monitor,
        'save_playlist_cover',
        lambda url, path: path.with_suffix('.jpg'),
    )
    result = download_playlist_cover(
        SOURCE_SPOTIFY,
        'pl1',
        m3u_path,
        {'download_cover_art_playlists': True},
    )
    assert result == m3u_path.with_suffix('.jpg')


# ── monitor.check_playlist integration ──────────────────────────────────────


class _FakeMonitorDB:
    @staticmethod
    def get_track_filenames(playlist_id):
        return {}

    @staticmethod
    def mark_track_downloaded(playlist_id, track_id, filename):
        pass

    @staticmethod
    def update_playlist(playlist_id, **kwargs):
        pass


def _monitored_playlist(url='https://open.spotify.com/playlist/pl123'):
    return monitor.MonitoredPlaylist(
        id=1,
        spotify_id='pl123',
        name=PLAYLIST_NAME,
        url=url,
        interval_minutes=60,
        enabled=True,
        last_checked=None,
        last_track_count=0,
        created_at='2026-01-01T00:00:00+00:00',
    )


def _write_track_file(dl: Downloader, song: dict, subdir: str) -> str:
    parts = dl._format_output_parts(song)
    basename = parts[-1]
    target_dir, prefix = dl._resolve_target_dir(
        dl._effective_subdir(song, subdir)
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / f'{basename}.{dl.audio_format}').write_bytes(b'audio')
    return f'{prefix}{basename}.{dl.audio_format}'


async def _fake_broadcast(_msg):
    return None


def test_check_playlist_downloads_cover_when_enabled(monkeypatch, tmp_path):
    tracks = [{'song_id': 'a', 'name': 'Song A', 'artists': ['Artist A']}]
    dl = Downloader(download_dir=tmp_path, audio_format='mp3')

    monkeypatch.setattr(
        monitor.spotify, 'playlist_tracks_from_id', lambda spotify_id: tracks
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda track_id: {})
    monkeypatch.setattr(
        monitor.spotify,
        'playlist_cover_url_from_id',
        lambda pid: 'https://img/cover',
    )
    monkeypatch.setattr(
        downloader_mod, '_download_cover', lambda url: b'IMG-BYTES'
    )
    monkeypatch.setattr(
        dl,
        'download',
        lambda song, cb, subdir=None: _write_track_file(dl, song, subdir),
    )

    async def _scenario():
        return await monitor.check_playlist(
            _monitored_playlist(),
            _FakeMonitorDB(),
            dl,
            _fake_broadcast,
            asyncio.get_running_loop(),
            settings={
                'generate_m3u': True,
                'download_cover_art_playlists': True,
            },
        )

    downloaded = asyncio.run(_scenario())

    assert downloaded == 1
    cover_path = tmp_path / PLAYLIST_NAME / f'{PLAYLIST_NAME}.jpg'
    assert cover_path.read_bytes() == b'IMG-BYTES'


def test_check_playlist_skips_cover_when_disabled(monkeypatch, tmp_path):
    tracks = [{'song_id': 'a', 'name': 'Song A', 'artists': ['Artist A']}]
    dl = Downloader(download_dir=tmp_path, audio_format='mp3')

    monkeypatch.setattr(
        monitor.spotify, 'playlist_tracks_from_id', lambda spotify_id: tracks
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda track_id: {})

    def _boom(*_a, **_kw):
        raise AssertionError('should not fetch a playlist cover when off')

    monkeypatch.setattr(monitor.spotify, 'playlist_cover_url_from_id', _boom)
    monkeypatch.setattr(
        dl,
        'download',
        lambda song, cb, subdir=None: _write_track_file(dl, song, subdir),
    )

    async def _scenario():
        return await monitor.check_playlist(
            _monitored_playlist(),
            _FakeMonitorDB(),
            dl,
            _fake_broadcast,
            asyncio.get_running_loop(),
            settings={'generate_m3u': True},
        )

    downloaded = asyncio.run(_scenario())

    assert downloaded == 1
    assert not (tmp_path / PLAYLIST_NAME / f'{PLAYLIST_NAME}.jpg').exists()


# ── api._process_batch integration (the real manual-download path) ─────────
#
# This is what the frontend actually hits when a Spotify/YouTube Music
# playlist link is pasted and downloaded — unlike
# ``write_playlist_m3u_endpoint`` below, which nothing currently calls.


def _make_downloader(tmp_path) -> Downloader:
    return Downloader(download_dir=tmp_path, audio_format='mp3')


def test_process_batch_downloads_playlist_cover_when_enabled(
    monkeypatch, tmp_path
):
    songs = [{'song_id': 'a', 'name': 'Song A', 'artists': ['Artist A']}]
    dl = _make_downloader(tmp_path)
    monkeypatch.setattr(api.state, 'downloader', dl)
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api.state, 'download_semaphore', None)
    monkeypatch.setattr(
        api.state, 'settings', {'download_cover_art_playlists': True}
    )
    monkeypatch.setattr(
        api, 'parse_playlist_url', lambda url: (SOURCE_SPOTIFY, 'pl123')
    )
    monkeypatch.setattr(
        api, 'fetch_playlist', lambda source, pid: (PLAYLIST_NAME, songs)
    )
    monkeypatch.setattr(
        monitor.spotify,
        'playlist_cover_url_from_id',
        lambda pid: 'https://img/cover',
    )
    monkeypatch.setattr(
        downloader_mod, '_download_cover', lambda url: b'IMG-BYTES'
    )

    async def fake_run_download(song, song_id, subdir=None, **_kwargs):
        return _write_track_file(dl, song, subdir)

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    asyncio.run(
        api._process_batch(
            songs,
            ['job-a'],
            playlist_url='https://open.spotify.com/playlist/pl123',
            generate_m3u=True,
        )
    )

    cover_path = tmp_path / PLAYLIST_NAME / f'{PLAYLIST_NAME}.jpg'
    assert cover_path.read_bytes() == b'IMG-BYTES'


def test_process_batch_skips_playlist_cover_when_setting_disabled(
    monkeypatch, tmp_path
):
    songs = [{'song_id': 'a', 'name': 'Song A', 'artists': ['Artist A']}]
    dl = _make_downloader(tmp_path)
    monkeypatch.setattr(api.state, 'downloader', dl)
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api.state, 'download_semaphore', None)
    monkeypatch.setattr(api.state, 'settings', {})
    monkeypatch.setattr(
        api, 'parse_playlist_url', lambda url: (SOURCE_SPOTIFY, 'pl123')
    )
    monkeypatch.setattr(
        api, 'fetch_playlist', lambda source, pid: (PLAYLIST_NAME, songs)
    )

    def _boom(*_a, **_kw):
        raise AssertionError('should not fetch a playlist cover when off')

    monkeypatch.setattr(monitor.spotify, 'playlist_cover_url_from_id', _boom)

    async def fake_run_download(song, song_id, subdir=None, **_kwargs):
        return _write_track_file(dl, song, subdir)

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    asyncio.run(
        api._process_batch(
            songs,
            ['job-a'],
            playlist_url='https://open.spotify.com/playlist/pl123',
            generate_m3u=True,
        )
    )

    assert not (tmp_path / PLAYLIST_NAME / f'{PLAYLIST_NAME}.jpg').exists()


def test_process_batch_skips_playlist_cover_without_a_playlist_url(
    monkeypatch, tmp_path
):
    # A CSV library import: no Spotify/YouTube Music playlist to resolve
    # a cover from, even with the setting on.
    songs = [{'song_id': 'a', 'name': 'Song A', 'artists': ['Artist A']}]
    dl = _make_downloader(tmp_path)
    monkeypatch.setattr(api.state, 'downloader', dl)
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api.state, 'download_semaphore', None)
    monkeypatch.setattr(
        api.state, 'settings', {'download_cover_art_playlists': True}
    )

    def _boom(*_a, **_kw):
        raise AssertionError('should not fetch a playlist cover without a URL')

    monkeypatch.setattr(monitor.spotify, 'playlist_cover_url_from_id', _boom)

    async def fake_run_download(song, song_id, subdir=None, **_kwargs):
        return _write_track_file(dl, song, subdir)

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    asyncio.run(
        api._process_batch(
            songs,
            ['job-a'],
            playlist_url='',
            generate_m3u=True,
            playlist_name=PLAYLIST_NAME,
        )
    )

    assert not (tmp_path / PLAYLIST_NAME / f'{PLAYLIST_NAME}.jpg').exists()


def test_process_batch_saves_the_cover_before_the_first_track(
    monkeypatch, tmp_path
):
    # The playlist's folder should already look like the playlist while
    # it fills up, rather than only once the last track lands.
    songs = [
        {'song_id': 'a', 'name': 'Song A', 'artists': ['Artist A']},
        {'song_id': 'b', 'name': 'Song B', 'artists': ['Artist B']},
    ]
    dl = _make_downloader(tmp_path)
    monkeypatch.setattr(api.state, 'downloader', dl)
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api.state, 'download_semaphore', None)
    monkeypatch.setattr(
        api.state, 'settings', {'download_cover_art_playlists': True}
    )
    monkeypatch.setattr(
        api, 'parse_playlist_url', lambda url: (SOURCE_SPOTIFY, 'pl123')
    )
    monkeypatch.setattr(
        api, 'fetch_playlist', lambda source, pid: (PLAYLIST_NAME, songs)
    )
    monkeypatch.setattr(
        monitor.spotify,
        'playlist_cover_url_from_id',
        lambda pid: 'https://img/cover',
    )
    monkeypatch.setattr(
        downloader_mod, '_download_cover', lambda url: b'IMG-BYTES'
    )

    cover_path = tmp_path / PLAYLIST_NAME / f'{PLAYLIST_NAME}.jpg'
    cover_seen: list[bool] = []

    async def fake_run_download(song, song_id, subdir=None, **_kwargs):
        cover_seen.append(cover_path.is_file())
        return _write_track_file(dl, song, subdir)

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    asyncio.run(
        api._process_batch(
            songs,
            ['job-a', 'job-b'],
            playlist_url='https://open.spotify.com/playlist/pl123',
            generate_m3u=True,
        )
    )

    assert cover_seen == [True, True]


def test_check_playlist_saves_the_cover_before_the_first_track(
    monkeypatch, tmp_path
):
    tracks = [{'song_id': 'a', 'name': 'Song A', 'artists': ['Artist A']}]
    dl = Downloader(download_dir=tmp_path, audio_format='mp3')

    monkeypatch.setattr(
        monitor.spotify, 'playlist_tracks_from_id', lambda spotify_id: tracks
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda track_id: {})
    monkeypatch.setattr(
        monitor.spotify,
        'playlist_cover_url_from_id',
        lambda pid: 'https://img/cover',
    )
    monkeypatch.setattr(
        downloader_mod, '_download_cover', lambda url: b'IMG-BYTES'
    )

    cover_path = tmp_path / PLAYLIST_NAME / f'{PLAYLIST_NAME}.jpg'
    cover_seen: list[bool] = []

    def _download(song, cb, subdir=None):
        cover_seen.append(cover_path.is_file())
        return _write_track_file(dl, song, subdir)

    monkeypatch.setattr(dl, 'download', _download)

    async def _scenario():
        return await monitor.check_playlist(
            _monitored_playlist(),
            _FakeMonitorDB(),
            dl,
            _fake_broadcast,
            asyncio.get_running_loop(),
            settings={
                'generate_m3u': True,
                'download_cover_art_playlists': True,
            },
        )

    assert asyncio.run(_scenario()) == 1
    assert cover_seen == [True]


# ── api.write_playlist_m3u_endpoint integration ─────────────────────────────


class _JsonRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def _write_m3u_payload(m3u_track_filename):
    return {
        'playlist_url': 'https://open.spotify.com/playlist/pl123',
        'tracks': [
            {
                'filename': m3u_track_filename,
                'title': 'Song A',
                'artist': 'Artist A',
            }
        ],
    }


def test_write_playlist_m3u_endpoint_downloads_cover_when_enabled(
    monkeypatch, tmp_path
):
    dl = Downloader(download_dir=tmp_path, audio_format='mp3')
    track_dir = tmp_path / PLAYLIST_NAME
    track_dir.mkdir()
    (track_dir / 'Artist A - Song A.mp3').write_bytes(b'\x00')

    monkeypatch.setattr(api.state, 'downloader', dl)
    monkeypatch.setattr(
        api.state, 'settings', {'download_cover_art_playlists': True}
    )
    monkeypatch.setattr(
        api, 'parse_playlist_url', lambda url: (SOURCE_SPOTIFY, 'pl123')
    )
    monkeypatch.setattr(
        api, 'fetch_playlist', lambda source, pid: (PLAYLIST_NAME, [])
    )
    captured = {}

    def _fake_cover(source, playlist_id, m3u_path, settings):
        captured['args'] = (source, playlist_id, m3u_path, settings)

    monkeypatch.setattr(api, 'download_playlist_cover', _fake_cover)

    result = asyncio.run(
        api.write_playlist_m3u_endpoint(
            _JsonRequest(
                _write_m3u_payload(f'{PLAYLIST_NAME}/Artist A - Song A.mp3')
            )
        )
    )

    assert 'args' in captured
    source, playlist_id, m3u_path, settings = captured['args']
    assert (source, playlist_id) == (SOURCE_SPOTIFY, 'pl123')
    assert m3u_path == Path(result['path'])
    assert settings is api.state.settings


def test_write_playlist_m3u_endpoint_skips_cover_when_no_tracks_resolved(
    monkeypatch, tmp_path
):
    dl = Downloader(download_dir=tmp_path, audio_format='mp3')
    monkeypatch.setattr(api.state, 'downloader', dl)
    monkeypatch.setattr(
        api.state, 'settings', {'download_cover_art_playlists': True}
    )
    monkeypatch.setattr(
        api, 'parse_playlist_url', lambda url: (SOURCE_SPOTIFY, 'pl123')
    )
    monkeypatch.setattr(
        api, 'fetch_playlist', lambda source, pid: (PLAYLIST_NAME, [])
    )

    def _boom(*_a, **_kw):
        raise AssertionError('should not attempt a cover download')

    monkeypatch.setattr(api, 'download_playlist_cover', _boom)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            api.write_playlist_m3u_endpoint(
                _JsonRequest(_write_m3u_payload('missing/does-not-exist.mp3'))
            )
        )
    assert exc_info.value.status_code == 400
