"""Tests for api._resolve_artist_top_songs (GET /api/artists/top_songs/url)."""

from __future__ import annotations

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
        'https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg', 2
    )
    assert result['source'] == 'spotify'
    assert result['name'] == 'Test Artist'
    assert result['cover_url'] == 'https://example.test/cover.jpg'
    assert [s['song_id'] for s in result['songs']] == ['t1', 't2']
    assert result['available'] == 3


def test_spotify_artist_resolve_failure_is_502(monkeypatch):
    def _raise(_artist_id):
        raise RuntimeError('embed unreachable')

    monkeypatch.setattr(api.spotify, 'artist_top_songs_from_id', _raise)
    with pytest.raises(HTTPException) as exc:
        api._resolve_artist_top_songs(
            'https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg', 5
        )
    assert exc.value.status_code == 502


def test_youtube_artist_url_uses_preview_when_limit_fits(monkeypatch):
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
        lambda channel_id: [_song('a1'), _song('a2'), _song('a3')],
    )

    def _fail_full(_channel_id):
        raise AssertionError('full shelf fetch should not run')

    monkeypatch.setattr(
        api.providers, 'artist_full_top_songs_from_channel_id', _fail_full
    )
    result = api._resolve_artist_top_songs(
        f'https://music.youtube.com/channel/{CHANNEL_ID}', 2
    )
    assert result['source'] == 'youtube'
    assert result['artist_id'] == CHANNEL_ID
    assert [s['song_id'] for s in result['songs']] == ['a1', 'a2']
    assert result['available'] == 3


def test_youtube_artist_url_fetches_full_shelf_when_limit_exceeds_preview(
    monkeypatch,
):
    monkeypatch.setattr(
        api.providers, 'resolve_artist_channel_id', lambda v: v
    )
    monkeypatch.setattr(
        api.providers,
        'artist_info_from_channel_id',
        lambda channel_id: {'name': 'Test Artist', 'cover_url': ''},
    )
    monkeypatch.setattr(
        api.providers,
        'artist_top_songs_from_channel_id',
        lambda channel_id: [_song('a1'), _song('a2')],
    )
    monkeypatch.setattr(
        api.providers,
        'artist_full_top_songs_from_channel_id',
        lambda channel_id: [
            _song('a1'),
            _song('a2'),
            _song('a3'),
            _song('a4'),
            _song('a5'),
            _song('a6'),
        ],
    )
    result = api._resolve_artist_top_songs(
        f'https://music.youtube.com/channel/{CHANNEL_ID}', 6
    )
    assert [s['song_id'] for s in result['songs']] == [
        'a1',
        'a2',
        'a3',
        'a4',
        'a5',
        'a6',
    ]
    assert result['available'] == 6


def test_youtube_artist_url_keeps_preview_when_full_shelf_empty(monkeypatch):
    monkeypatch.setattr(
        api.providers, 'resolve_artist_channel_id', lambda v: v
    )
    monkeypatch.setattr(
        api.providers,
        'artist_info_from_channel_id',
        lambda channel_id: {'name': 'Test Artist', 'cover_url': ''},
    )
    monkeypatch.setattr(
        api.providers,
        'artist_top_songs_from_channel_id',
        lambda channel_id: [_song('a1'), _song('a2')],
    )
    monkeypatch.setattr(
        api.providers,
        'artist_full_top_songs_from_channel_id',
        lambda channel_id: [],
    )
    result = api._resolve_artist_top_songs(
        f'https://music.youtube.com/channel/{CHANNEL_ID}', 6
    )
    assert [s['song_id'] for s in result['songs']] == ['a1', 'a2']


def test_youtube_artist_handle_resolved_channel_not_found_is_404(
    monkeypatch,
):
    def _raise(_handle):
        raise ValueError('handle not found')

    monkeypatch.setattr(api.providers, 'resolve_artist_channel_id', _raise)
    with pytest.raises(HTTPException) as exc:
        api._resolve_artist_top_songs(
            'https://music.youtube.com/@nobody', 5
        )
    assert exc.value.status_code == 404


def test_non_artist_url_is_400():
    with pytest.raises(HTTPException) as exc:
        api._resolve_artist_top_songs(
            'https://open.spotify.com/track/4vfN00PlILRXy5dcXHQE9M', 5
        )
    assert exc.value.status_code == 400
