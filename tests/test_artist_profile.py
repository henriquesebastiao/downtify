"""Tests for artist photo/banner storage (downtify/artist_profile.py) and
the ``/api/artists/art*`` endpoints in downtify/api.py."""

from __future__ import annotations

import asyncio
import base64
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from downtify import api, artist_profile
from downtify.downloader import Downloader
from downtify.track_index import TrackIndex

# A real (if tiny) 1x1 PNG, so downtify.image_size.image_dimensions()
# accepts it as valid image data.
_TINY_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQ'
    'UBAScY42YAAAAASUVORK5CYII='
)


class _JsonRequest:
    def __init__(self, payload: Any):
        self._payload = payload

    async def json(self) -> Any:
        return self._payload


class _RawRequest:
    def __init__(self, body: bytes):
        self._body = body

    async def body(self) -> bytes:
        return self._body


@pytest.fixture
def app_state(monkeypatch, tmp_path):
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    monkeypatch.setattr(
        api.state,
        'downloader',
        Downloader(download_dir=downloads, audio_format='mp3'),
    )
    monkeypatch.setattr(api.state, 'settings', {})
    monkeypatch.setattr(api.state, 'track_index', None)
    return downloads


# ── downtify/artist_profile.py ──────────────────────────────────────────


def test_path_for_photo_uses_sanitized_name(tmp_path):
    path = artist_profile.image_path_for(
        tmp_path, 'Avril/Lavigne', artist_profile.KIND_PHOTO
    )
    assert path == tmp_path / 'Metadata/ArtistImage/AvrilLavigne.jpg'


def test_path_for_banner_uses_banner_suffix(tmp_path):
    path = artist_profile.image_path_for(
        tmp_path, 'Avril Lavigne', artist_profile.KIND_BANNER
    )
    assert (
        path
        == tmp_path / 'Metadata/ArtistBannerImage/Avril Lavigne.banner.jpg'
    )


def test_public_url_none_when_missing(tmp_path):
    assert (
        artist_profile.image_url_for(
            tmp_path, 'Nobody', artist_profile.KIND_PHOTO
        )
        is None
    )


def test_save_bytes_then_public_url_roundtrip(tmp_path):
    url = artist_profile.save_image(
        tmp_path, 'Avril Lavigne', artist_profile.KIND_PHOTO, _TINY_PNG
    )
    assert url == '/downloads/Metadata/ArtistImage/Avril Lavigne.jpg'
    assert (
        artist_profile.image_url_for(
            tmp_path, 'Avril Lavigne', artist_profile.KIND_PHOTO
        )
        == url
    )


def test_save_bytes_rejects_non_image_data(tmp_path):
    with pytest.raises(ValueError, match='Not a valid image'):
        artist_profile.save_image(
            tmp_path,
            'Avril Lavigne',
            artist_profile.KIND_PHOTO,
            b'not an image',
        )


def test_save_bytes_rejects_oversized_data(tmp_path, monkeypatch):
    monkeypatch.setattr(artist_profile, 'MAX_IMAGE_BYTES', 10)
    with pytest.raises(ValueError, match='Not a valid image'):
        artist_profile.save_image(
            tmp_path, 'Avril Lavigne', artist_profile.KIND_PHOTO, _TINY_PNG
        )


def test_fetch_and_save_downloads_and_stores(tmp_path):
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.content = _TINY_PNG
    with patch('downtify.artist_profile.httpx.get', return_value=resp):
        url = artist_profile.fetch_and_save_image(
            tmp_path,
            'Avril Lavigne',
            artist_profile.KIND_BANNER,
            'https://example.com/photo.jpg',
        )
    assert (
        url == '/downloads/Metadata/ArtistBannerImage/Avril Lavigne.banner.jpg'
    )


def test_fetch_and_save_empty_url_raises(tmp_path):
    with pytest.raises(ValueError, match='No image URL given'):
        artist_profile.fetch_and_save_image(
            tmp_path, 'Avril Lavigne', artist_profile.KIND_PHOTO, ''
        )


def test_fetch_and_save_request_failure_raises(tmp_path):
    with patch(
        'downtify.artist_profile.httpx.get',
        side_effect=Exception('network down'),
    ):
        with pytest.raises(ValueError, match='Could not fetch'):
            artist_profile.fetch_and_save_image(
                tmp_path,
                'Avril Lavigne',
                artist_profile.KIND_PHOTO,
                'https://example.com/photo.jpg',
            )


# ── endpoints ──────────────────────────────────────────────────────────


def test_artist_art_endpoint_reports_existing_and_missing(app_state):
    artist_profile.save_image(
        app_state, 'Avril Lavigne', artist_profile.KIND_PHOTO, _TINY_PNG
    )
    result = api.artist_art_endpoint(name='Avril Lavigne')
    assert result['photo_url'] == (
        '/downloads/Metadata/ArtistImage/Avril Lavigne.jpg'
    )
    assert result['banner_url'] is None


def test_artist_art_search_endpoint_combines_sources(app_state):
    with (
        patch(
            'downtify.api.providers.search_artists',
            return_value=[
                {'name': 'Avril Lavigne', 'cover_url': 'https://yt/x.jpg'},
                {'name': 'No Cover Here', 'cover_url': ''},
            ],
        ),
        patch(
            'downtify.api.deezer.search_artist',
            return_value=[
                {
                    'source': 'deezer',
                    'name': 'Avril Lavigne',
                    'image_url': 'https://dz/x.jpg',
                    'url': 'https://deezer.com/artist/1',
                }
            ],
        ),
    ):
        results = api.artist_art_search_endpoint(name='Avril Lavigne')
    assert results == [
        {
            'source': 'youtube',
            'name': 'Avril Lavigne',
            'image_url': 'https://yt/x.jpg',
        },
        {
            'source': 'deezer',
            'name': 'Avril Lavigne',
            'image_url': 'https://dz/x.jpg',
            'url': 'https://deezer.com/artist/1',
        },
    ]


def test_artist_art_search_endpoint_empty_query_short_circuits(app_state):
    with patch('downtify.api.providers.search_artists') as mock_search:
        assert api.artist_art_search_endpoint(name='   ') == []
    mock_search.assert_not_called()


def test_bulk_endpoint_reports_each_artist(app_state):
    artist_profile.save_image(
        app_state, 'Avril Lavigne', artist_profile.KIND_PHOTO, _TINY_PNG
    )
    request = _JsonRequest({'names': ['Avril Lavigne', 'Nobody']})
    result = asyncio.run(api.artist_art_bulk_endpoint(request))
    assert result == {
        'Avril Lavigne': {
            'photo_url': '/downloads/Metadata/ArtistImage/Avril Lavigne.jpg',
            'banner_url': None,
        },
        'Nobody': {'photo_url': None, 'banner_url': None},
    }


def test_bulk_endpoint_dedupes_and_skips_blank_names(app_state):
    artist_profile.save_image(
        app_state, 'Avril Lavigne', artist_profile.KIND_PHOTO, _TINY_PNG
    )
    request = _JsonRequest({'names': ['Avril Lavigne', 'Avril Lavigne', '  ']})
    result = asyncio.run(api.artist_art_bulk_endpoint(request))
    assert list(result) == ['Avril Lavigne']


def test_bulk_endpoint_non_list_names_returns_empty(app_state):
    request = _JsonRequest({'names': 'Avril Lavigne'})
    assert asyncio.run(api.artist_art_bulk_endpoint(request)) == {}
    request = _JsonRequest({})
    assert asyncio.run(api.artist_art_bulk_endpoint(request)) == {}


def test_spotify_candidate_endpoint_no_track_index_returns_empty(app_state):
    assert (
        api.artist_art_spotify_candidate_endpoint(file='Artist - Song.mp3')
        == {}
    )


def test_spotify_candidate_endpoint_unknown_file_returns_empty(app_state):
    api.state.track_index = TrackIndex(app_state / 'lib.db')
    assert (
        api.artist_art_spotify_candidate_endpoint(file='../etc/passwd') == {}
    )


def test_spotify_candidate_endpoint_resolves_via_track_index(
    app_state, tmp_path
):
    track_index = TrackIndex(tmp_path / 'lib.db')
    api.state.track_index = track_index
    audio = app_state / 'Artist - Song.mp3'
    audio.write_bytes(b'audio')
    track_id = 'a' * 22
    track_index.register(track_id, 'Artist - Song.mp3')

    with (
        patch(
            'downtify.api.spotify.primary_artist_id_from_track_id',
            return_value='artist123',
        ),
        patch(
            'downtify.api.spotify.artist_image_url_from_id',
            return_value='https://spotify/img.jpg',
        ),
        patch(
            'downtify.api.spotify.artist_name_from_id',
            return_value='Avril Lavigne',
        ),
    ):
        result = api.artist_art_spotify_candidate_endpoint(
            file='Artist - Song.mp3'
        )
    assert result == {
        'source': 'spotify',
        'name': 'Avril Lavigne',
        'image_url': 'https://spotify/img.jpg',
    }


def test_from_url_endpoint_saves_and_returns_url(app_state):
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.content = _TINY_PNG
    request = _JsonRequest({
        'name': 'Avril Lavigne',
        'kind': 'photo',
        'image_url': 'https://example.com/photo.jpg',
    })
    with patch('downtify.artist_profile.httpx.get', return_value=resp):
        result = asyncio.run(api.artist_art_from_url_endpoint(request))
    assert result['url'] == '/downloads/Metadata/ArtistImage/Avril Lavigne.jpg'


def test_from_url_endpoint_rejects_invalid_kind(app_state):
    request = _JsonRequest({
        'name': 'Avril Lavigne',
        'kind': 'poster',
        'image_url': 'https://example.com/photo.jpg',
    })
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.artist_art_from_url_endpoint(request))
    assert exc.value.status_code == 400


def test_upload_endpoint_saves_raw_body(app_state):
    request = _RawRequest(_TINY_PNG)
    result = asyncio.run(
        api.artist_art_upload_endpoint(
            request, name='Avril Lavigne', kind='banner'
        )
    )
    assert result['url'] == (
        '/downloads/Metadata/ArtistBannerImage/Avril Lavigne.banner.jpg'
    )


def test_upload_endpoint_rejects_oversized_body(app_state, monkeypatch):
    monkeypatch.setattr(artist_profile, 'MAX_IMAGE_BYTES', 10)
    request = _RawRequest(_TINY_PNG)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            api.artist_art_upload_endpoint(
                request, name='Avril Lavigne', kind='photo'
            )
        )
    assert exc.value.status_code == 413


def test_delete_removes_an_existing_file(tmp_path):
    artist_profile.save_image(
        tmp_path, 'Avril Lavigne', artist_profile.KIND_PHOTO, _TINY_PNG
    )
    assert artist_profile.delete_image(
        tmp_path, 'Avril Lavigne', artist_profile.KIND_PHOTO
    )
    assert (
        artist_profile.image_url_for(
            tmp_path, 'Avril Lavigne', artist_profile.KIND_PHOTO
        )
        is None
    )


def test_delete_missing_file_returns_false(tmp_path):
    assert not artist_profile.delete_image(
        tmp_path, 'Nobody', artist_profile.KIND_PHOTO
    )


def test_delete_endpoint_removes_saved_banner(app_state):
    artist_profile.save_image(
        app_state, 'Avril Lavigne', artist_profile.KIND_BANNER, _TINY_PNG
    )
    result = api.artist_art_delete_endpoint(
        name='Avril Lavigne', kind='banner'
    )
    assert result == {'removed': True}
    assert api.artist_art_endpoint(name='Avril Lavigne')['banner_url'] is None


def test_delete_endpoint_reports_nothing_to_remove(app_state):
    result = api.artist_art_delete_endpoint(name='Nobody', kind='photo')
    assert result == {'removed': False}


def test_delete_endpoint_rejects_invalid_kind(app_state):
    with pytest.raises(HTTPException) as exc:
        api.artist_art_delete_endpoint(name='Avril Lavigne', kind='poster')
    assert exc.value.status_code == 400
