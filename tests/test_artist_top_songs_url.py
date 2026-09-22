"""Tests for api._resolve_artist_top_songs (GET /api/artists/top_songs/url)."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from downtify import api

CHANNEL_ID = 'UCAjidy3vxRkgGVNIFqZMl_Q'


def _song(song_id):
    return {'song_id': song_id, 'name': song_id, 'source': 'youtube'}


def test_spotify_artist_url_resolves_top_songs(monkeypatch):
    monkeypatch.setattr(
        api.spotify,
        'artist_top_songs_from_id',
        lambda artist_id: (
            'Test Artist',
            'https://example.test/cover.jpg',
            [_song('t1'), _song('t2'), _song('t3')],
        ),
    )
    result = api._resolve_artist_top_songs(
        'https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg'
    )
    assert result['source'] == 'spotify'
    assert result['name'] == 'Test Artist'
    assert result['cover_url'] == 'https://example.test/cover.jpg'
    assert [s['song_id'] for s in result['songs']] == ['t1', 't2', 't3']


def test_spotify_artist_resolve_failure_is_502(monkeypatch):
    def _raise(_artist_id):
        raise RuntimeError('embed unreachable')

    monkeypatch.setattr(api.spotify, 'artist_top_songs_from_id', _raise)
    with pytest.raises(HTTPException) as exc:
        api._resolve_artist_top_songs(
            'https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg'
        )
    assert exc.value.status_code == 502


def _patch_youtube_artist(monkeypatch, preview, full):
    monkeypatch.setattr(
        api.providers, 'resolve_artist_channel_id', lambda v: v
    )
    monkeypatch.setattr(
        api.providers,
        'artist_info_from_channel_id',
        lambda channel_id: {
            'name': 'Test Artist',
            'cover_url': 'https://example.test/artist.jpg',
        },
    )
    monkeypatch.setattr(
        api.providers,
        'artist_top_songs_from_channel_id',
        lambda channel_id: preview,
    )
    monkeypatch.setattr(
        api.providers,
        'artist_full_top_songs_from_channel_id',
        lambda channel_id: full,
    )


def test_youtube_artist_url_returns_the_full_shelf(monkeypatch):
    _patch_youtube_artist(
        monkeypatch,
        preview=[_song('a1'), _song('a2')],
        full=[_song(f'a{i}') for i in range(1, 8)],
    )
    result = api._resolve_artist_top_songs(
        f'https://music.youtube.com/channel/{CHANNEL_ID}'
    )
    assert result['source'] == 'youtube'
    assert result['artist_id'] == CHANNEL_ID
    assert result['name'] == 'Test Artist'
    assert result['cover_url'] == 'https://example.test/artist.jpg'
    assert [s['song_id'] for s in result['songs']] == [
        f'a{i}' for i in range(1, 8)
    ]


def test_youtube_artist_url_caps_the_full_shelf(monkeypatch):
    total = api.YOUTUBE_TOP_SONGS_LIMIT + 20
    _patch_youtube_artist(
        monkeypatch,
        preview=[_song('a1')],
        full=[_song(f'a{i}') for i in range(1, total + 1)],
    )
    result = api._resolve_artist_top_songs(
        f'https://music.youtube.com/channel/{CHANNEL_ID}'
    )
    assert len(result['songs']) == api.YOUTUBE_TOP_SONGS_LIMIT
    assert result['songs'][0]['song_id'] == 'a1'


def test_youtube_artist_url_keeps_preview_when_full_shelf_empty(monkeypatch):
    _patch_youtube_artist(
        monkeypatch, preview=[_song('a1'), _song('a2')], full=[]
    )
    result = api._resolve_artist_top_songs(
        f'https://music.youtube.com/channel/{CHANNEL_ID}'
    )
    assert [s['song_id'] for s in result['songs']] == ['a1', 'a2']


def test_youtube_artist_handle_resolved_channel_not_found_is_404(
    monkeypatch,
):
    def _raise(_handle):
        raise ValueError('handle not found')

    monkeypatch.setattr(api.providers, 'resolve_artist_channel_id', _raise)
    with pytest.raises(HTTPException) as exc:
        api._resolve_artist_top_songs('https://music.youtube.com/@nobody')
    assert exc.value.status_code == 404


def test_non_artist_url_is_400():
    with pytest.raises(HTTPException) as exc:
        api._resolve_artist_top_songs(
            'https://open.spotify.com/track/4vfN00PlILRXy5dcXHQE9M'
        )
    assert exc.value.status_code == 400


def test_url_resolve_spotify_artist_lists_the_releases(monkeypatch):
    releases = [{'album_id': 'AAA', 'name': 'Test Album'}]
    monkeypatch.setattr(
        api.spotify,
        'artist_page_from_id',
        lambda artist_id: (
            'Test Artist',
            'https://example.test/cover.jpg',
            releases,
        ),
    )
    result = api.url_resolve_endpoint(
        'https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg'
    )
    assert result['kind'] == 'artist'
    assert result['name'] == 'Test Artist'
    assert result['cover_url'] == 'https://example.test/cover.jpg'
    assert result['tracks'] == []
    assert result['albums'] == releases


class _FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def test_batch_endpoint_passes_explicit_playlist_name_and_cover(monkeypatch):
    captured = {}

    async def fake_submit(songs, playlist_url, **kwargs):
        captured.update(songs=songs, playlist_url=playlist_url, **kwargs)
        return {'job_ids': ['j1'], 'count': 1}

    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(api, '_submit_playlist_batch', fake_submit)
    payload = {
        'songs': [_song('a1')],
        'playlist_name': 'Top Songs of Test Artist',
        'cover_url': 'https://example.test/artist.jpg',
        'generate_m3u': False,
    }
    result = asyncio.run(api.download_batch_endpoint(_FakeRequest(payload)))
    assert result['count'] == 1
    assert not captured['playlist_url']
    assert captured['playlist_name'] == 'Top Songs of Test Artist'
    assert captured['cover_url'] == 'https://example.test/artist.jpg'
    assert captured['generate_m3u'] is False
