"""Tests for link resolution: _resolve_url and /api/url/resolve."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from downtify import api


def test_resolve_url_artist_channel_returns_albums(monkeypatch):
    monkeypatch.setattr(
        api.providers,
        'artist_albums_from_channel_id',
        lambda channel_id: [{'album_id': f'{channel_id}-album'}],
    )
    result = api._resolve_url(
        'https://music.youtube.com/channel/UCAjidy3vxRkgGVNIFqZMl_Q'
    )
    assert result == [{'album_id': 'UCAjidy3vxRkgGVNIFqZMl_Q-album'}]


# ── /api/url/resolve ──────────────────────────────────────────────────

_PLAYLIST = 'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M'
_ALBUM = 'https://open.spotify.com/album/2dZMT4gpOWtIYtvdSLT4pr'
_TRACK = 'https://open.spotify.com/track/0DiWol3AO6WpXZgp0goxAV'
_CHANNEL = 'https://music.youtube.com/channel/UCAjidy3vxRkgGVNIFqZMl_Q'

_SONG = {
    'song_id': 't1',
    'name': 'Harbor Lights',
    'artists': ['Kenji Aoki', 'Guest'],
    'album_name': 'Glass Harbor',
    'cover_url': 'https://i.scdn.co/cover.jpg',
    'year': '2025',
}


def test_url_resolve_names_a_spotify_playlist(monkeypatch):
    monkeypatch.setattr(
        api.spotify,
        'playlist_info_and_tracks',
        lambda sid: ('Weekend Coastline', [_SONG]),
    )

    result = api.url_resolve_endpoint(_PLAYLIST)

    assert result['kind'] == 'playlist'
    assert result['name'] == 'Weekend Coastline'
    assert result['tracks'] == [_SONG]
    # Track covers aren't the playlist's cover, so none is claimed.
    assert not result['cover_url']
    assert result['albums'] == []


def test_url_resolve_takes_album_details_from_its_tracks(monkeypatch):
    monkeypatch.setattr(
        api.spotify, 'album_tracks_from_id', lambda sid: [_SONG, _SONG]
    )

    result = api.url_resolve_endpoint(_ALBUM)

    assert result['kind'] == 'album'
    assert result['name'] == 'Glass Harbor'
    assert result['subtitle'] == 'Kenji Aoki, Guest'
    assert result['cover_url'] == 'https://i.scdn.co/cover.jpg'
    assert result['year'] == '2025'
    assert len(result['tracks']) == 2


def test_url_resolve_wraps_a_single_track(monkeypatch):
    monkeypatch.setattr(api.spotify, 'track_from_id', lambda sid: _SONG)

    result = api.url_resolve_endpoint(_TRACK)

    assert result['kind'] == 'track'
    assert result['name'] == 'Harbor Lights'
    assert result['tracks'] == [_SONG]


def test_url_resolve_lists_an_artists_releases(monkeypatch):
    monkeypatch.setattr(
        api.providers, 'resolve_artist_channel_id', lambda yid: yid
    )
    monkeypatch.setattr(
        api.providers,
        'artist_info_from_channel_id',
        lambda cid: {'name': 'Kenji Aoki', 'cover_url': 'c.jpg'},
    )
    monkeypatch.setattr(
        api.providers,
        'artist_albums_from_channel_id',
        lambda cid: [{'album_id': 'a1'}],
    )

    result = api.url_resolve_endpoint(_CHANNEL)

    assert result['kind'] == 'artist'
    assert result['name'] == 'Kenji Aoki'
    assert result['albums'] == [{'album_id': 'a1'}]
    assert result['tracks'] == []


def test_url_resolve_rejects_unknown_links():
    with pytest.raises(HTTPException) as info:
        api.url_resolve_endpoint('https://example.com/music')
    assert info.value.status_code == 400


def test_url_resolve_reports_upstream_failures_as_bad_gateway(monkeypatch):
    def _boom(sid):
        raise RuntimeError('embed down')

    monkeypatch.setattr(api.spotify, 'track_from_id', _boom)

    with pytest.raises(HTTPException) as info:
        api.url_resolve_endpoint(_TRACK)
    assert info.value.status_code == 502
