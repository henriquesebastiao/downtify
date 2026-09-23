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


def test_spotify_candidate_endpoint_banner_kind_uses_banner_lookup(
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
            'downtify.api.spotify.artist_banner_url_from_id',
            return_value='https://spotify/banner.jpg',
        ) as mock_banner,
        patch('downtify.api.spotify.artist_image_url_from_id') as mock_photo,
        patch(
            'downtify.api.spotify.artist_name_from_id',
            return_value='Avril Lavigne',
        ),
    ):
        result = api.artist_art_spotify_candidate_endpoint(
            file='Artist - Song.mp3', kind='banner'
        )
    assert result == {
        'source': 'spotify',
        'name': 'Avril Lavigne',
        'image_url': 'https://spotify/banner.jpg',
    }
    mock_banner.assert_called_once_with('artist123')
    mock_photo.assert_not_called()


def test_spotify_candidate_endpoint_banner_kind_empty_when_no_banner(
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
            'downtify.api.spotify.artist_banner_url_from_id',
            return_value='',
        ),
    ):
        result = api.artist_art_spotify_candidate_endpoint(
            file='Artist - Song.mp3', kind='banner'
        )
    assert result == {}


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


# ── profile data: bio, social links, related artists, platform ids ──────


def test_load_profile_returns_blank_skeleton_when_missing(tmp_path):
    assert artist_profile.load_profile(tmp_path, 'Nobody') == {
        'name': 'Nobody',
        'bio': '',
        'platforms_id': {'deezer': ''},
        'social': {
            'twitter': '',
            'facebook': '',
            'website': '',
            'instagram': '',
        },
        'related_artists': [],
        'current_cover': '',
        'current_cover_banner': '',
    }


def test_save_image_with_source_updates_current_cover(tmp_path):
    artist_profile.save_image(
        tmp_path,
        'Avril Lavigne',
        artist_profile.KIND_PHOTO,
        _TINY_PNG,
        source='deezer',
    )
    profile = artist_profile.load_profile(tmp_path, 'Avril Lavigne')
    assert profile['current_cover'] == 'deezer'
    assert not profile['current_cover_banner']


def test_save_image_without_source_does_not_touch_profile(tmp_path):
    artist_profile.save_image(
        tmp_path, 'Avril Lavigne', artist_profile.KIND_PHOTO, _TINY_PNG
    )
    profile = artist_profile.load_profile(tmp_path, 'Avril Lavigne')
    assert not profile['current_cover']


def test_delete_image_clears_current_cover(tmp_path):
    artist_profile.save_image(
        tmp_path,
        'Avril Lavigne',
        artist_profile.KIND_BANNER,
        _TINY_PNG,
        source='upload',
    )
    artist_profile.delete_image(
        tmp_path, 'Avril Lavigne', artist_profile.KIND_BANNER
    )
    profile = artist_profile.load_profile(tmp_path, 'Avril Lavigne')
    assert not profile['current_cover_banner']


def test_fetch_bio_resolves_id_fetches_and_saves(tmp_path):
    with (
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ) as mock_resolve,
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value={
                'bio_html': '<p>Hello <em>world</em></p>',
                'social': {
                    'twitter': 'https://twitter.com/x',
                    'facebook': '',
                    'website': '',
                    'instagram': '',
                },
                'related_artist_names': ['Simple Plan', 'Paramore'],
            },
        ) as mock_fetch,
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Avril Lavigne', 'en')
    mock_resolve.assert_called_once_with('Avril Lavigne')
    mock_fetch.assert_called_once_with('35', 'en')
    assert profile['bio'] == 'Hello world'
    assert profile['platforms_id']['deezer'] == '35'
    assert profile['social']['twitter'] == 'https://twitter.com/x'
    assert profile['related_artists'] == ['Simple Plan', 'Paramore']
    reloaded = artist_profile.load_profile(tmp_path, 'Avril Lavigne')
    assert reloaded['bio'] == 'Hello world'


def test_fetch_bio_reuses_cached_deezer_id(tmp_path):
    existing = artist_profile.load_profile(tmp_path, 'Avril Lavigne')
    existing['platforms_id'] = {'deezer': '35'}
    artist_profile._save_profile(tmp_path, 'Avril Lavigne', existing)
    with (
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id'
        ) as mock_resolve,
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value={
                'bio_html': '',
                'social': {
                    'twitter': '',
                    'facebook': '',
                    'website': '',
                    'instagram': '',
                },
                'related_artist_names': [],
            },
        ) as mock_fetch,
    ):
        artist_profile.fetch_bio(tmp_path, 'Avril Lavigne', 'en')
    mock_resolve.assert_not_called()
    mock_fetch.assert_called_once_with('35', 'en')


def test_fetch_bio_raises_when_artist_not_found_on_either_source(tmp_path):
    with (
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.providers.resolve_artist_id_by_name',
            return_value=None,
        ),
    ):
        with pytest.raises(ValueError, match='No matching artist'):
            artist_profile.fetch_bio(tmp_path, 'Some Unknown Band', 'en')


def test_fetch_bio_falls_back_to_youtube_when_deezer_has_no_match(tmp_path):
    with (
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.providers.resolve_artist_id_by_name',
            return_value='UCxxx',
        ) as mock_resolve_yt,
        patch(
            'downtify.artist_profile.providers.artist_bio_from_channel_id',
            return_value='A great band from YouTube Music.',
        ) as mock_yt_bio,
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Some Band', 'en')
    mock_resolve_yt.assert_called_once_with('Some Band')
    mock_yt_bio.assert_called_once_with('UCxxx', 'en')
    assert profile['bio'] == 'A great band from YouTube Music.'
    # Only Deezer brings social/related artists.
    assert not profile['platforms_id']['deezer']
    assert profile['social'] == {
        'twitter': '',
        'facebook': '',
        'website': '',
        'instagram': '',
    }
    assert profile['related_artists'] == []


def test_fetch_bio_falls_back_to_youtube_when_deezer_bio_is_empty(tmp_path):
    with (
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value={
                'bio_html': '',
                'social': {
                    'twitter': 'https://twitter.com/x',
                    'facebook': '',
                    'website': '',
                    'instagram': '',
                },
                'related_artist_names': ['Simple Plan'],
            },
        ),
        patch(
            'downtify.artist_profile.providers.resolve_artist_id_by_name',
            return_value='UCxxx',
        ),
        patch(
            'downtify.artist_profile.providers.artist_bio_from_channel_id',
            return_value='Bio from YouTube Music.',
        ),
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Avril Lavigne', 'en')
    assert profile['bio'] == 'Bio from YouTube Music.'
    # Deezer's social/related are kept even though its bio was empty.
    assert profile['platforms_id']['deezer'] == '35'
    assert profile['social']['twitter'] == 'https://twitter.com/x'
    assert profile['related_artists'] == ['Simple Plan']


def test_fetch_bio_falls_back_to_youtube_when_deezer_request_fails(tmp_path):
    with (
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            side_effect=ValueError('Could not fetch artist info from Deezer'),
        ),
        patch(
            'downtify.artist_profile.providers.resolve_artist_id_by_name',
            return_value='UCxxx',
        ),
        patch(
            'downtify.artist_profile.providers.artist_bio_from_channel_id',
            return_value='Bio from YouTube Music.',
        ),
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Avril Lavigne', 'en')
    assert profile['bio'] == 'Bio from YouTube Music.'


def test_fetch_bio_keeps_deezer_data_when_neither_source_has_bio_text(
    tmp_path,
):
    with (
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value={
                'bio_html': '',
                'social': {
                    'twitter': 'https://twitter.com/x',
                    'facebook': '',
                    'website': '',
                    'instagram': '',
                },
                'related_artist_names': ['Simple Plan'],
            },
        ),
        patch(
            'downtify.artist_profile.providers.resolve_artist_id_by_name',
            return_value=None,
        ),
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Avril Lavigne', 'en')
    assert not profile['bio']
    assert profile['social']['twitter'] == 'https://twitter.com/x'
    assert profile['related_artists'] == ['Simple Plan']


def test_artist_profile_endpoint_returns_blank_skeleton(app_state):
    result = api.artist_profile_endpoint(name='Nobody')
    assert not result['bio']
    assert result['related_artists'] == []


def test_artist_profile_bio_endpoint_saves_and_returns(app_state):
    request = _JsonRequest({'name': 'Avril Lavigne', 'lang': 'pt-BR'})
    with patch(
        'downtify.api.artist_profile.fetch_bio',
        return_value={'bio': 'Ola', 'name': 'Avril Lavigne'},
    ) as mock_fetch:
        result = asyncio.run(api.artist_profile_bio_endpoint(request))
    assert result == {'bio': 'Ola', 'name': 'Avril Lavigne'}
    mock_fetch.assert_called_once()


def test_artist_profile_bio_endpoint_rejects_blank_name(app_state):
    request = _JsonRequest({'name': '  ', 'lang': 'en'})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.artist_profile_bio_endpoint(request))
    assert exc.value.status_code == 400


def test_artist_profile_bio_endpoint_propagates_value_error(app_state):
    request = _JsonRequest({'name': 'Unknown', 'lang': 'en'})
    with patch(
        'downtify.api.artist_profile.fetch_bio',
        side_effect=ValueError('No matching artist found on Deezer'),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(api.artist_profile_bio_endpoint(request))
    assert exc.value.status_code == 400


def test_remove_bio_clears_only_bio_keeps_everything_else(tmp_path):
    with (
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value={
                'bio_html': '<p>Hello</p>',
                'social': {
                    'twitter': 'https://twitter.com/x',
                    'facebook': '',
                    'website': '',
                    'instagram': '',
                },
                'related_artist_names': ['Simple Plan'],
            },
        ),
    ):
        artist_profile.fetch_bio(tmp_path, 'Avril Lavigne', 'en')

    profile = artist_profile.remove_bio(tmp_path, 'Avril Lavigne')
    assert not profile['bio']
    assert profile['social']['twitter'] == 'https://twitter.com/x'
    assert profile['related_artists'] == ['Simple Plan']
    assert profile['platforms_id']['deezer'] == '35'

    reloaded = artist_profile.load_profile(tmp_path, 'Avril Lavigne')
    assert not reloaded['bio']
    assert reloaded['social']['twitter'] == 'https://twitter.com/x'
    assert reloaded['related_artists'] == ['Simple Plan']
    assert reloaded['platforms_id']['deezer'] == '35'


def test_remove_bio_on_untouched_artist_returns_blank_skeleton(tmp_path):
    profile = artist_profile.remove_bio(tmp_path, 'Nobody')
    assert profile == artist_profile.load_profile(tmp_path, 'Nobody')


def test_artist_profile_bio_delete_endpoint_clears_saved_bio(app_state):
    with (
        patch(
            'downtify.api.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.api.artist_profile.deezer.fetch_artist_full',
            return_value={
                'bio_html': 'Hello',
                'social': {'twitter': '', 'facebook': '', 'website': ''},
                'related_artist_names': [],
            },
        ),
    ):
        asyncio.run(
            api.artist_profile_bio_endpoint(
                _JsonRequest({'name': 'Avril Lavigne', 'lang': 'en'})
            )
        )
    result = api.artist_profile_bio_delete_endpoint(name='Avril Lavigne')
    assert not result['bio']
    assert not api.artist_profile_endpoint(name='Avril Lavigne')['bio']
