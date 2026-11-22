"""Watched playlists show their picture on the Monitor page
(``GET /api/monitor/playlists/{id}/cover``)."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from downtify import api, monitor
from tests.test_monitor_edit import _Req

COVER = 'https://image-cdn-ak.spotifycdn.com/image/ab67706c0000da84cover'


class _Downloader:
    organize_by_artist = True
    organize_by_album = False

    def __init__(self, root):
        self.download_dir = root


@pytest.fixture
def setup(monkeypatch, tmp_path):
    db = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    playlist = db.add_playlist(
        '37i9dQZF1E37hYdaily', 'Daily Mix 4', 'url', 1440
    )
    artist = db.add_playlist(
        'UCdrake', 'Drake', 'url', 1440, monitor.KIND_ARTIST
    )
    downloader = _Downloader(tmp_path / 'music')
    monkeypatch.setattr(api.state, 'monitor_db', db)
    monkeypatch.setattr(api.state, 'downloader', downloader)
    monkeypatch.setattr(monitor, '_watch_cover_urls', {})
    lookups: list[tuple[str, str]] = []

    def fake_lookup(source, playlist_id):
        lookups.append((source, playlist_id))
        return COVER

    monkeypatch.setattr(monitor, 'fetch_playlist_cover_url', fake_lookup)
    return playlist, artist, downloader, lookups


def _cover(watch_id):
    return asyncio.run(api.monitor_playlist_cover(watch_id, _Req({})))


def test_the_saved_cover_beside_the_m3u_is_served(setup):
    playlist, _artist, downloader, lookups = setup
    saved = downloader.download_dir / 'Playlists' / 'Daily Mix 4.jpg'
    saved.parent.mkdir(parents=True)
    saved.write_bytes(b'\xff\xd8jpeg')

    response = _cover(playlist.id)

    assert isinstance(response, FileResponse)
    assert response.path == saved
    assert lookups == []


def test_without_a_saved_cover_it_points_at_the_services_one(setup):
    playlist, _artist, _downloader, lookups = setup

    first = _cover(playlist.id)
    second = _cover(playlist.id)

    assert isinstance(first, RedirectResponse)
    assert first.headers['location'] == COVER
    assert second.headers['location'] == COVER
    # Looked up once, then remembered.
    assert lookups == [('spotify', '37i9dQZF1E37hYdaily')]


def test_no_cover_anywhere_is_a_404_and_is_remembered(setup, monkeypatch):
    playlist, _artist, _downloader, _lookups = setup
    calls = []

    def nothing(source, playlist_id):
        calls.append(playlist_id)
        raise RuntimeError('Spotify did not answer')

    monkeypatch.setattr(monitor, 'fetch_playlist_cover_url', nothing)

    for _ in range(2):
        with pytest.raises(HTTPException) as err:
            _cover(playlist.id)
        assert err.value.status_code == 404
    assert calls == ['37i9dQZF1E37hYdaily']


def test_a_found_cover_is_looked_up_again_after_a_day(setup, monkeypatch):
    playlist, _artist, _downloader, lookups = setup
    clock = [1000.0]
    monkeypatch.setattr(monitor, 'monotonic', lambda: clock[0])

    _cover(playlist.id)
    clock[0] += monitor.WATCH_COVER_TTL_SECONDS - 1
    _cover(playlist.id)
    clock[0] += 2
    _cover(playlist.id)

    assert len(lookups) == 2


def test_only_https_addresses_are_followed(setup, monkeypatch):
    playlist, _artist, _downloader, _lookups = setup
    monkeypatch.setattr(
        monitor, 'fetch_playlist_cover_url', lambda *a: 'javascript:alert(1)'
    )

    with pytest.raises(HTTPException) as err:
        _cover(playlist.id)
    assert err.value.status_code == 404


def test_an_artist_or_unknown_watch_has_no_playlist_cover(setup):
    _playlist, artist, _downloader, lookups = setup

    for watch_id in (artist.id, 9999):
        with pytest.raises(HTTPException) as err:
            _cover(watch_id)
        assert err.value.status_code == 404
    assert lookups == []
