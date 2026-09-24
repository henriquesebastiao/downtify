"""Tests for artist photo/banner storage (downtify/artist_profile.py) and
the ``/api/artists/art*`` endpoints in downtify/api.py."""

from __future__ import annotations

import asyncio
import base64
import json
import os
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


@pytest.fixture(autouse=True)
def _no_spotify_name_search(monkeypatch):
    """Nothing here may reach Spotify's real search; a test that wants a
    match overrides this."""

    monkeypatch.setattr(
        artist_profile.spotify, 'search_artist_by_name', lambda name: None
    )
    # ...nor may the ensure endpoint start its background top songs fetch.
    monkeypatch.setattr(
        api.artist_top_songs, 'refresh_in_background', lambda *args: False
    )


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
    version = artist_profile.image_version_for(
        app_state, 'Avril Lavigne', artist_profile.KIND_PHOTO
    )
    assert version
    assert result == {
        'Avril Lavigne': {
            'photo_url': '/downloads/Metadata/ArtistImage/Avril Lavigne.jpg',
            'photo_version': version,
            'banner_url': None,
            'banner_version': None,
        },
        'Nobody': {
            'photo_url': None,
            'photo_version': None,
            'banner_url': None,
            'banner_version': None,
        },
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
        'origin': '',
        'born_or_formed': '',
        'genre': '',
        'is_group': None,
        'banner_bg_color': '',
        'platforms_id': {
            'spotify': '',
            'youtubemusic': '',
            'deezer': '',
            'applemusic': '',
        },
        'social': {
            'twitter': '',
            'facebook': '',
            'website': '',
            'instagram': '',
            'youtube': '',
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


# ── _format_bio_text ──────────────────────────────────────────────────


def test_format_bio_text_keeps_a_single_block_as_is():
    assert (
        artist_profile._format_bio_text('Just one paragraph.')
        == 'Just one paragraph.'
    )


def test_format_bio_text_keeps_blank_line_separated_paragraphs():
    assert artist_profile._format_bio_text('First.\n\nSecond.') == (
        'First.\n\nSecond.'
    )


def test_format_bio_text_turns_each_bullet_into_its_own_paragraph():
    text = 'Intro paragraph.\n\n• One\n• Two \n• Three'
    assert artist_profile._format_bio_text(text) == (
        'Intro paragraph.\n\nOne\n\nTwo\n\nThree'
    )


def test_format_bio_text_apple_music_shape_one_paragraph_per_bullet():
    # As Apple sends it: a lead paragraph, then bullets split by a single
    # "\n" (some with a trailing space) and italics as <i> tags.
    raw = 'Lead.\n\n• First <i>Origin</i>. \n• Second.\n• Third.'
    paragraphs = artist_profile._format_bio_text(raw).split('\n\n')
    assert paragraphs == ['Lead.', 'First Origin.', 'Second.', 'Third.']


def test_format_bio_text_bullet_without_a_blank_line_before_it():
    assert artist_profile._format_bio_text('Intro.\n• One\n• Two') == (
        'Intro.\n\nOne\n\nTwo'
    )


def test_format_bio_text_keeps_single_line_breaks_outside_bullets():
    assert artist_profile._format_bio_text('Line one\nLine two') == (
        'Line one\nLine two'
    )


def test_format_bio_text_continuation_line_stays_with_its_bullet():
    assert artist_profile._format_bio_text('• One\ncontinued\n• Two') == (
        'One\ncontinued\n\nTwo'
    )


def test_format_bio_text_turns_deezer_html_paragraphs_into_blank_lines():
    assert artist_profile._format_bio_text(
        '<p>Hello <em>there</em></p><p>World</p>'
    ) == ('Hello there\n\nWorld')


def test_format_bio_text_leaves_no_html_tags():
    assert artist_profile._format_bio_text('A <script>x</script> B') == 'A x B'


def test_format_bio_text_is_idempotent():
    once = artist_profile._format_bio_text('<p>Intro.</p>\n• One\n• Two')
    assert artist_profile._format_bio_text(once) == once


def test_normalize_stored_bio_upgrades_legacy_html_list():
    legacy = '<p>Intro.</p><ul><li>One</li><li>Two</li></ul>'
    assert artist_profile._normalize_stored_bio(legacy) == (
        'Intro.\n\nOne\n\nTwo'
    )


def test_normalize_stored_bio_upgrades_legacy_bullet_text():
    legacy = 'Intro.\n\n• One\n• Two'
    assert artist_profile._normalize_stored_bio(legacy) == (
        'Intro.\n\nOne\n\nTwo'
    )


def test_normalize_stored_bio_leaves_plain_text_alone():
    assert artist_profile._normalize_stored_bio('Plain.\n\nText.') == (
        'Plain.\n\nText.'
    )


def test_format_bio_text_empty_input_returns_empty_string():
    assert not artist_profile._format_bio_text('')
    assert not artist_profile._format_bio_text('   ')


_APPLE_FULL = {
    'bio_html': '<p>Hello <em>world</em></p>',
    'origin': 'Little Rock, AR, United States',
    'born_or_formed': '1995',
    'is_group': True,
    'genre': 'Hard rock',
    'banner_bg_color': '2c2622',
    'applemusic_id': 'evanescence/42102393',
}
_APPLE_FULL_NO_BIO = {**_APPLE_FULL, 'bio_html': ''}
_DEEZER_FULL = {
    'bio_html': '<p>Hello</p>',
    'social': {
        'twitter': 'https://twitter.com/x',
        'facebook': '',
        'website': '',
        'instagram': '',
    },
    'related_artist_names': ['Simple Plan', 'Paramore'],
}
_DEEZER_FULL_NO_BIO = {**_DEEZER_FULL, 'bio_html': ''}


def test_fetch_bio_apple_primary_sets_bio_and_metadata(tmp_path):
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value='42102393',
        ) as mock_resolve_apple,
        patch(
            'downtify.artist_profile.apple_music.fetch_artist_full',
            return_value=_APPLE_FULL,
        ) as mock_fetch_apple,
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL_NO_BIO,
        ),
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Evanescence', 'en')
    mock_resolve_apple.assert_called_once_with('Evanescence')
    mock_fetch_apple.assert_called_once_with('42102393', 'en')
    assert profile['bio'] == 'Hello world'
    assert profile['origin'] == 'Little Rock, AR, United States'
    assert profile['born_or_formed'] == '1995'
    assert profile['is_group'] is True
    assert profile['genre'] == 'Hard rock'
    assert profile['banner_bg_color'] == '2c2622'
    assert profile['platforms_id']['applemusic'] == 'evanescence/42102393'
    # Deezer still contributes social/related artists even though Apple
    # already supplied the bio text - they're not mutually exclusive.
    assert profile['social']['twitter'] == 'https://twitter.com/x'
    assert profile['related_artists'] == ['Simple Plan', 'Paramore']
    assert profile['platforms_id']['deezer'] == '35'
    reloaded = artist_profile.load_profile(tmp_path, 'Evanescence')
    assert reloaded['bio'] == 'Hello world'


def test_fetch_bio_reuses_cached_apple_id(tmp_path):
    existing = artist_profile.load_profile(tmp_path, 'Evanescence')
    existing['platforms_id']['applemusic'] = 'evanescence/42102393'
    artist_profile._save_profile(tmp_path, 'Evanescence', existing)
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id'
        ) as mock_resolve_apple,
        patch(
            'downtify.artist_profile.apple_music.fetch_artist_full',
            return_value=_APPLE_FULL,
        ) as mock_fetch_apple,
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
    ):
        artist_profile.fetch_bio(tmp_path, 'Evanescence', 'en')
    mock_resolve_apple.assert_not_called()
    mock_fetch_apple.assert_called_once_with('42102393', 'en')


def test_fetch_bio_preserves_manually_set_social_fields(tmp_path):
    # 'youtube' has no Deezer equivalent (see downtify/deezer.py's fixed
    # four-field 'social' shape) - a re-fetch must not wipe it.
    artist_profile.save_social(
        tmp_path, 'Evanescence', {'youtube': 'https://youtube.com/x'}
    )
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL,
        ),
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Evanescence', 'en')
    assert profile['social']['twitter'] == 'https://twitter.com/x'
    assert profile['social']['youtube'] == 'https://youtube.com/x'


def test_fetch_bio_reuses_cached_deezer_id(tmp_path):
    existing = artist_profile.load_profile(tmp_path, 'Evanescence')
    existing['platforms_id']['deezer'] = '35'
    artist_profile._save_profile(tmp_path, 'Evanescence', existing)
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id'
        ) as mock_resolve,
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL_NO_BIO,
        ) as mock_fetch,
    ):
        artist_profile.fetch_bio(tmp_path, 'Evanescence', 'en')
    mock_resolve.assert_not_called()
    mock_fetch.assert_called_once_with('35', 'en')


def test_fetch_bio_raises_when_artist_not_found_on_either_source(tmp_path):
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
    ):
        with pytest.raises(ValueError, match='No matching artist'):
            artist_profile.fetch_bio(tmp_path, 'Some Unknown Band', 'en')


def test_fetch_bio_falls_back_to_deezer_when_apple_bio_is_empty(tmp_path):
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value='42102393',
        ),
        patch(
            'downtify.artist_profile.apple_music.fetch_artist_full',
            return_value=_APPLE_FULL_NO_BIO,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL,
        ),
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Evanescence', 'hu')
    assert profile['bio'] == 'Hello'
    # Apple's own (non-per-language) fields are still kept even though
    # its bio was empty for this language.
    assert profile['origin'] == 'Little Rock, AR, United States'
    assert profile['social']['twitter'] == 'https://twitter.com/x'


def test_fetch_bio_apple_bio_wins_over_deezer_when_both_have_one(tmp_path):
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value='42102393',
        ),
        patch(
            'downtify.artist_profile.apple_music.fetch_artist_full',
            return_value=_APPLE_FULL,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL,
        ),
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Evanescence', 'en')
    assert profile['bio'] == 'Hello world'


def test_fetch_bio_apple_request_failure_falls_through_to_deezer(tmp_path):
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value='42102393',
        ),
        patch(
            'downtify.artist_profile.apple_music.fetch_artist_full',
            side_effect=ValueError(
                'Could not fetch artist info from Apple Music'
            ),
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL,
        ),
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Evanescence', 'en')
    assert profile['bio'] == 'Hello'
    assert not profile['origin']


def test_fetch_bio_keeps_partial_data_when_neither_source_has_bio_text(
    tmp_path,
):
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value='42102393',
        ),
        patch(
            'downtify.artist_profile.apple_music.fetch_artist_full',
            return_value=_APPLE_FULL_NO_BIO,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL_NO_BIO,
        ),
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Evanescence', 'en')
    assert not profile['bio']
    assert profile['origin'] == 'Little Rock, AR, United States'
    assert profile['social']['twitter'] == 'https://twitter.com/x'
    assert profile['related_artists'] == ['Simple Plan', 'Paramore']


def test_fetch_bio_merges_spotify_related_artists_with_deezers(tmp_path):
    existing = artist_profile.load_profile(tmp_path, 'Evanescence')
    existing['platforms_id']['spotify'] = 'spotify123'
    artist_profile._save_profile(tmp_path, 'Evanescence', existing)
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL,
        ),
        patch(
            'downtify.artist_profile.spotify.related_artist_names_from_id',
            return_value=['Paramore', 'Linkin Park'],
        ) as mock_spotify_related,
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Evanescence', 'en')
    mock_spotify_related.assert_called_once_with('spotify123')
    # Deezer's own two names, plus Spotify's new one - 'Paramore' isn't
    # duplicated since Deezer already had it (case-insensitively).
    assert profile['related_artists'] == [
        'Simple Plan',
        'Paramore',
        'Linkin Park',
    ]


def test_fetch_bio_skips_spotify_related_artists_when_spotify_has_no_match(
    tmp_path,
):
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL,
        ),
        patch(
            'downtify.artist_profile.spotify.related_artist_names_from_id'
        ) as mock_spotify_related,
    ):
        artist_profile.fetch_bio(tmp_path, 'Evanescence', 'en')
    mock_spotify_related.assert_not_called()


def test_fetch_bio_spotify_related_artists_failure_is_non_fatal(tmp_path):
    existing = artist_profile.load_profile(tmp_path, 'Evanescence')
    existing['platforms_id']['spotify'] = 'spotify123'
    artist_profile._save_profile(tmp_path, 'Evanescence', existing)
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL,
        ),
        patch(
            'downtify.artist_profile.spotify.related_artist_names_from_id',
            side_effect=Exception('boom'),
        ),
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Evanescence', 'en')
    assert profile['related_artists'] == ['Simple Plan', 'Paramore']


# ── _merge_names ──────────────────────────────────────────────────────────


def test_merge_names_appends_new_names_only():
    assert artist_profile._merge_names(
        ['Simple Plan', 'Paramore'], ['paramore', 'Linkin Park']
    ) == ['Simple Plan', 'Paramore', 'Linkin Park']


def test_merge_names_empty_inputs():
    assert artist_profile._merge_names([], []) == []
    assert artist_profile._merge_names(['A'], []) == ['A']
    assert artist_profile._merge_names([], ['A']) == ['A']


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
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
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
            'downtify.api.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
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


# ── manual bio/social edits (save_bio, save_social) ──────────────────────


def test_save_bio_sets_bio_text(tmp_path):
    profile = artist_profile.save_bio(tmp_path, 'Avril Lavigne', 'My own bio.')
    assert profile['bio'] == 'My own bio.'
    reloaded = artist_profile.load_profile(tmp_path, 'Avril Lavigne')
    assert reloaded['bio'] == 'My own bio.'


def test_save_bio_strips_whitespace(tmp_path):
    profile = artist_profile.save_bio(tmp_path, 'Avril Lavigne', '  padded  ')
    assert profile['bio'] == 'padded'


def test_save_bio_overwrites_a_fetched_bio_but_keeps_the_rest(tmp_path):
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value={
                'bio_html': '<p>Fetched</p>',
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

    profile = artist_profile.save_bio(tmp_path, 'Avril Lavigne', 'My own bio.')
    assert profile['bio'] == 'My own bio.'
    assert profile['social']['twitter'] == 'https://twitter.com/x'
    assert profile['related_artists'] == ['Simple Plan']
    assert profile['platforms_id']['deezer'] == '35'


def test_save_social_sets_all_five_fields(tmp_path):
    profile = artist_profile.save_social(
        tmp_path,
        'Avril Lavigne',
        {
            'twitter': 'https://twitter.com/x',
            'facebook': 'https://facebook.com/x',
            'website': 'https://example.com',
            'instagram': 'https://instagram.com/x',
            'youtube': 'https://youtube.com/x',
        },
    )
    assert profile['social'] == {
        'twitter': 'https://twitter.com/x',
        'facebook': 'https://facebook.com/x',
        'website': 'https://example.com',
        'instagram': 'https://instagram.com/x',
        'youtube': 'https://youtube.com/x',
    }
    reloaded = artist_profile.load_profile(tmp_path, 'Avril Lavigne')
    assert reloaded['social']['website'] == 'https://example.com'


def test_save_social_missing_keys_become_empty_strings(tmp_path):
    artist_profile.save_social(
        tmp_path, 'Avril Lavigne', {'twitter': 'https://twitter.com/x'}
    )
    profile = artist_profile.save_social(
        tmp_path, 'Avril Lavigne', {'facebook': 'https://facebook.com/x'}
    )
    # The second call's payload didn't include twitter, so it's cleared -
    # the editor always submits its full form, this isn't a partial merge.
    assert profile['social'] == {
        'twitter': '',
        'facebook': 'https://facebook.com/x',
        'website': '',
        'instagram': '',
        'youtube': '',
    }


def test_save_social_ignores_unknown_keys(tmp_path):
    profile = artist_profile.save_social(
        tmp_path,
        'Avril Lavigne',
        {'twitter': 'https://twitter.com/x', 'tiktok': 'x'},
    )
    assert 'tiktok' not in profile['social']


def test_artist_profile_bio_set_endpoint_saves_manual_text(app_state):
    request = _JsonRequest({'name': 'Avril Lavigne', 'bio': 'Manual bio.'})
    result = asyncio.run(api.artist_profile_bio_set_endpoint(request))
    assert result['bio'] == 'Manual bio.'
    assert api.artist_profile_endpoint(name='Avril Lavigne')['bio'] == (
        'Manual bio.'
    )


def test_artist_profile_bio_set_endpoint_rejects_blank_name(app_state):
    request = _JsonRequest({'name': '  ', 'bio': 'x'})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.artist_profile_bio_set_endpoint(request))
    assert exc.value.status_code == 400


def test_artist_profile_social_set_endpoint_saves_links(app_state):
    request = _JsonRequest({
        'name': 'Avril Lavigne',
        'social': {'twitter': 'https://twitter.com/x'},
    })
    result = asyncio.run(api.artist_profile_social_set_endpoint(request))
    assert result['social']['twitter'] == 'https://twitter.com/x'
    assert not result['social']['facebook']


def test_artist_profile_social_set_endpoint_rejects_blank_name(app_state):
    request = _JsonRequest({'name': '  ', 'social': {}})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.artist_profile_social_set_endpoint(request))
    assert exc.value.status_code == 400


def test_artist_profile_social_set_endpoint_non_dict_social_becomes_empty(
    app_state,
):
    request = _JsonRequest({'name': 'Avril Lavigne', 'social': 'not-a-dict'})
    result = asyncio.run(api.artist_profile_social_set_endpoint(request))
    assert result['social'] == {
        'twitter': '',
        'facebook': '',
        'website': '',
        'instagram': '',
        'youtube': '',
    }


# ── resolve_platform_ids ──────────────────────────────────────────────────


def test_resolve_platform_ids_returns_every_match():
    with (
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.providers.resolve_artist_id',
            return_value='UCxxx',
        ),
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_slug_id',
            return_value='avril-lavigne/459885',
        ),
    ):
        assert artist_profile.resolve_platform_ids('Avril Lavigne') == {
            'deezer': '35',
            'youtubemusic': 'UCxxx',
            'applemusic': 'avril-lavigne/459885',
        }


def test_resolve_platform_ids_omits_platforms_with_no_match():
    with (
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.providers.resolve_artist_id',
            return_value='UCxxx',
        ),
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_slug_id',
            return_value=None,
        ),
    ):
        assert artist_profile.resolve_platform_ids('Some Band') == {
            'youtubemusic': 'UCxxx',
        }


def test_resolve_platform_ids_empty_dict_when_nothing_matches():
    with (
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.providers.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_slug_id',
            return_value=None,
        ),
    ):
        assert artist_profile.resolve_platform_ids('Unknown') == {}


# ── ensure_profile ─────────────────────────────────────────────────────────


_BOTH_KINDS = (artist_profile.KIND_PHOTO, artist_profile.KIND_BANNER)


def _fake_track_index(spotify_track_id='track123'):
    index = MagicMock()
    index.spotify_id_for_filename.return_value = spotify_track_id
    return index


def test_ensure_profile_noop_when_file_already_exists(tmp_path):
    artist_profile.save_bio(tmp_path, 'Avril Lavigne', 'Existing bio.')
    with (
        patch(
            'downtify.artist_profile.spotify.primary_artist_id_from_track_id'
        ) as mock_spotify,
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id'
        ) as mock_apple,
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id'
        ) as mock_deezer,
        patch(
            'downtify.artist_profile.providers.resolve_artist_id'
        ) as mock_ytm,
    ):
        profile = artist_profile.ensure_profile(
            tmp_path,
            'Avril Lavigne',
            ['Avril Lavigne/song.mp3'],
            'en',
            track_index=_fake_track_index(),
        )
    mock_spotify.assert_not_called()
    mock_apple.assert_not_called()
    mock_deezer.assert_not_called()
    mock_ytm.assert_not_called()
    assert profile['bio'] == 'Existing bio.'


def test_ensure_profile_seeds_photo_and_banner_from_spotify(tmp_path):
    with (
        patch(
            'downtify.artist_profile.spotify.primary_artist_id_from_track_id',
            return_value='artist123',
        ),
        patch(
            'downtify.artist_profile.spotify.artist_image_url_from_id',
            return_value='https://img/photo.jpg',
        ),
        patch(
            'downtify.artist_profile.spotify.artist_banner_url_from_id',
            return_value='https://img/banner.jpg',
        ),
        patch(
            'downtify.artist_profile.spotify.related_artist_names_from_id',
            return_value=[],
        ),
        patch('downtify.artist_profile.fetch_and_save_image') as mock_save,
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_slug_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.providers.resolve_artist_id',
            return_value=None,
        ),
    ):
        profile = artist_profile.ensure_profile(
            tmp_path,
            'New Artist',
            ['New Artist/song.mp3'],
            'en',
            track_index=_fake_track_index(),
            image_kinds=_BOTH_KINDS,
        )
    calls = {c.args[2]: c for c in mock_save.call_args_list}
    assert calls[artist_profile.KIND_PHOTO].args[3] == 'https://img/photo.jpg'
    assert calls[artist_profile.KIND_PHOTO].kwargs['source'] == 'spotify'
    assert (
        calls[artist_profile.KIND_BANNER].args[3] == 'https://img/banner.jpg'
    )
    assert calls[artist_profile.KIND_BANNER].kwargs['source'] == 'spotify'
    # The resolved id is cached, not just used transiently for images.
    assert profile['platforms_id']['spotify'] == 'artist123'


def test_ensure_profile_falls_back_to_youtube_when_spotify_has_nothing(
    tmp_path,
):
    with (
        patch(
            'downtify.artist_profile.spotify.primary_artist_id_from_track_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.providers.search_artists',
            return_value=[
                {'name': 'new artist', 'cover_url': 'https://img/yt.jpg'}
            ],
        ),
        patch('downtify.artist_profile.fetch_and_save_image') as mock_save,
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_slug_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.providers.resolve_artist_id',
            return_value=None,
        ),
    ):
        artist_profile.ensure_profile(
            tmp_path,
            'New Artist',
            ['New Artist/song.mp3'],
            'en',
            track_index=_fake_track_index(),
            image_kinds=_BOTH_KINDS,
        )
    assert mock_save.call_count == 2
    for c in mock_save.call_args_list:
        assert c.args[3] == 'https://img/yt.jpg'
        assert c.kwargs['source'] == 'youtube'


def test_ensure_profile_fills_bio_and_platform_ids(tmp_path):
    with (
        patch(
            'downtify.artist_profile.spotify.primary_artist_id_from_track_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.providers.search_artists',
            return_value=[],
        ),
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value='42102393',
        ),
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_slug_id',
            return_value='evanescence/42102393',
        ),
        patch(
            'downtify.artist_profile.apple_music.fetch_artist_full',
            return_value=_APPLE_FULL,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL_NO_BIO,
        ),
        patch(
            'downtify.artist_profile.providers.resolve_artist_id',
            return_value='UCxxx',
        ),
    ):
        profile = artist_profile.ensure_profile(
            tmp_path, 'Evanescence', [], 'en', track_index=_fake_track_index()
        )
    assert profile['bio'] == 'Hello world'
    assert profile['platforms_id']['applemusic'] == 'evanescence/42102393'
    assert profile['platforms_id']['deezer'] == '35'
    assert profile['platforms_id']['youtubemusic'] == 'UCxxx'


def test_ensure_profile_persists_even_when_nothing_found(tmp_path):
    with (
        patch(
            'downtify.artist_profile.spotify.primary_artist_id_from_track_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.providers.search_artists',
            return_value=[],
        ),
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_slug_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.providers.resolve_artist_id',
            return_value=None,
        ),
    ):
        profile = artist_profile.ensure_profile(
            tmp_path,
            'Unknown Band',
            [],
            'en',
            track_index=_fake_track_index(),
        )
    assert not profile['bio']
    assert artist_profile._profile_path_for(tmp_path, 'Unknown Band').is_file()


def test_ensure_profile_without_track_index_or_match_seeds_nothing(tmp_path):
    with (
        patch('downtify.artist_profile.fetch_and_save_image') as mock_save,
        patch(
            'downtify.artist_profile.providers.search_artists',
            return_value=[],
        ),
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_slug_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.providers.resolve_artist_id',
            return_value=None,
        ),
    ):
        artist_profile.ensure_profile(tmp_path, 'Nobody', [], 'en')
    mock_save.assert_not_called()


def test_artist_profile_ensure_endpoint_seeds_and_returns_profile(app_state):
    with (
        patch(
            'downtify.api.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.api.artist_profile.apple_music.resolve_artist_slug_id',
            return_value=None,
        ),
        patch(
            'downtify.api.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.api.artist_profile.providers.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.api.artist_profile.providers.search_artists',
            return_value=[],
        ),
    ):
        request = _JsonRequest({'name': 'Avril Lavigne', 'lang': 'en'})
        result = asyncio.run(api.artist_profile_ensure_endpoint(request))
    assert result['name'] == 'Avril Lavigne'
    assert artist_profile._profile_path_for(
        app_state, 'Avril Lavigne'
    ).is_file()


def test_artist_profile_ensure_endpoint_rejects_blank_name(app_state):
    request = _JsonRequest({'name': '  '})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.artist_profile_ensure_endpoint(request))
    assert exc.value.status_code == 400


# ── /api/artists/photo-proxy (display-only) ────────────────────────────


def test_photo_proxy_endpoint_relays_deezer_photo_without_saving(
    app_state, monkeypatch
):
    monkeypatch.setattr(
        api.artist_photo_proxy,
        'fetch_proxied_photo',
        lambda name: (b'jpegbytes', 'image/jpeg'),
    )
    resp = api.artist_photo_proxy_endpoint(name='Paramore')
    assert resp.body == b'jpegbytes'
    assert resp.media_type == 'image/jpeg'
    assert resp.headers['cache-control'] == 'public, max-age=10800'
    assert resp.headers['etag']
    # Display only: nothing lands under the library's Metadata folder.
    assert not (app_state / 'Metadata').exists()


def test_photo_proxy_endpoint_miss_is_a_cacheable_404(app_state, monkeypatch):
    monkeypatch.setattr(
        api.artist_photo_proxy, 'fetch_proxied_photo', lambda name: None
    )
    resp = api.artist_photo_proxy_endpoint(name='Nobody')
    assert resp.status_code == 404
    assert resp.headers['cache-control'] == 'public, max-age=10800'


def test_photo_proxy_endpoint_prefers_saved_photo(app_state, monkeypatch):
    artist_profile.save_image(
        app_state, 'Avril Lavigne', artist_profile.KIND_PHOTO, _TINY_PNG
    )

    def boom(name):
        raise AssertionError('Deezer must not be asked')

    monkeypatch.setattr(api.artist_photo_proxy, 'fetch_proxied_photo', boom)
    resp = api.artist_photo_proxy_endpoint(name='Avril Lavigne')
    assert resp.path.name == 'Avril Lavigne.jpg'
    assert resp.headers['cache-control'] == 'no-cache'


# ── Spotify artist id by name ──────────────────────────────────────────


def _no_other_platforms():
    """Patches that make every non-Spotify name lookup come up empty."""

    return (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_slug_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.providers.resolve_artist_id',
            return_value=None,
        ),
    )


def test_resolve_platform_ids_includes_spotify_by_name(monkeypatch):
    monkeypatch.setattr(
        artist_profile.spotify,
        'search_artist_by_name',
        lambda name: {'id': 'sp123', 'name': name},
    )
    a, b, c, d = _no_other_platforms()
    with a, b, c, d:
        assert artist_profile.resolve_platform_ids('Linkin Park') == {
            'spotify': 'sp123'
        }


def test_resolve_platform_ids_skips_platforms_already_known(monkeypatch):
    def boom(name):
        raise AssertionError('must not search a platform that is known')

    monkeypatch.setattr(artist_profile.spotify, 'search_artist_by_name', boom)
    with (
        patch('downtify.artist_profile.deezer.resolve_artist_id') as dz,
        patch('downtify.artist_profile.providers.resolve_artist_id') as yt,
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_slug_id'
        ) as am,
    ):
        known = {
            'spotify': 'sp1',
            'deezer': '92',
            'youtubemusic': 'UCx',
            'applemusic': 'linkin-park/148662',
        }
        assert artist_profile.resolve_platform_ids('X', known=known) == {}
    dz.assert_not_called()
    yt.assert_not_called()
    am.assert_not_called()


def test_spotify_search_failure_never_breaks_platform_lookup(monkeypatch):
    def boom(name):
        raise RuntimeError('spotify down')

    monkeypatch.setattr(artist_profile.spotify, 'search_artist_by_name', boom)
    a, b, c, d = _no_other_platforms()
    with a, b, c, d:
        assert artist_profile.resolve_platform_ids('Linkin Park') == {}


def test_resolve_spotify_artist_id_prefers_the_track_over_the_name(
    monkeypatch,
):
    monkeypatch.setattr(
        artist_profile.spotify,
        'primary_artist_id_from_track_id',
        lambda track_id: 'from_track',
    )

    def boom(name):
        raise AssertionError('name search must not run')

    monkeypatch.setattr(artist_profile.spotify, 'search_artist_by_name', boom)
    assert (
        artist_profile.resolve_spotify_artist_id(
            ['A/song.mp3'], _fake_track_index(), 'A'
        )
        == 'from_track'
    )


def test_resolve_spotify_artist_id_falls_back_to_the_name(monkeypatch):
    monkeypatch.setattr(
        artist_profile.spotify,
        'search_artist_by_name',
        lambda name: {'id': 'by_name', 'name': name},
    )
    index = MagicMock()
    index.spotify_id_for_filename.return_value = None
    assert (
        artist_profile.resolve_spotify_artist_id(['A/song.mp3'], index, 'A')
        == 'by_name'
    )
    # No track index at all, only a name.
    assert artist_profile.resolve_spotify_artist_id([], None, 'A') == 'by_name'


def test_resolve_spotify_artist_id_without_name_or_track_is_none():
    assert artist_profile.resolve_spotify_artist_id([], None) is None
    assert artist_profile.resolve_spotify_artist_id([], None, '  ') is None


def test_fetch_bio_resolves_and_caches_spotify_id_by_name(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        artist_profile.spotify,
        'search_artist_by_name',
        lambda name: {'id': 'sp123', 'name': name},
    )
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL,
        ),
        patch(
            'downtify.artist_profile.spotify.related_artist_names_from_id',
            return_value=['Spotify Related'],
        ) as related,
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Linkin Park', 'en')
    related.assert_called_once_with('sp123')
    assert profile['platforms_id']['spotify'] == 'sp123'
    assert 'Spotify Related' in profile['related_artists']
    saved = artist_profile.load_profile(tmp_path, 'Linkin Park')
    assert saved['platforms_id']['spotify'] == 'sp123'


def test_fetch_bio_never_replaces_a_cached_spotify_id(tmp_path, monkeypatch):
    def boom(name):
        raise AssertionError('name search must not run')

    monkeypatch.setattr(artist_profile.spotify, 'search_artist_by_name', boom)
    existing = artist_profile.load_profile(tmp_path, 'Linkin Park')
    existing['platforms_id']['spotify'] = 'from_track'
    artist_profile._save_profile(tmp_path, 'Linkin Park', existing)
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL,
        ),
        patch(
            'downtify.artist_profile.spotify.related_artist_names_from_id',
            return_value=[],
        ),
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Linkin Park', 'en')
    assert profile['platforms_id']['spotify'] == 'from_track'


def test_ensure_profile_without_a_spotify_track_uses_the_name_search(
    tmp_path, monkeypatch
):
    """The Linkin Park case: tracks not downloaded from Spotify, so no
    track id - the artist is found by name, its photo/banner come from
    Spotify (not the YouTube Music fallback) and the id is saved."""

    monkeypatch.setattr(
        artist_profile.spotify,
        'search_artist_by_name',
        lambda name: {'id': 'lp123', 'name': name},
    )
    a, b, c, d = _no_other_platforms()
    with (
        a,
        b,
        c,
        d,
        patch(
            'downtify.artist_profile.spotify.artist_image_url_from_id',
            return_value='https://img/photo.jpg',
        ),
        patch(
            'downtify.artist_profile.spotify.artist_banner_url_from_id',
            return_value='https://img/banner.jpg',
        ),
        patch(
            'downtify.artist_profile.spotify.related_artist_names_from_id',
            return_value=[],
        ),
        patch('downtify.artist_profile.providers.search_artists') as ytm,
        patch('downtify.artist_profile.fetch_and_save_image') as mock_save,
    ):
        index = MagicMock()
        index.spotify_id_for_filename.return_value = None
        profile = artist_profile.ensure_profile(
            tmp_path,
            'Linkin Park',
            ['Linkin Park/What I have Done.mp3'],
            'en',
            track_index=index,
            image_kinds=_BOTH_KINDS,
        )
    ytm.assert_not_called()
    sources = {c.args[2]: c.kwargs['source'] for c in mock_save.call_args_list}
    assert sources == {
        artist_profile.KIND_PHOTO: 'spotify',
        artist_profile.KIND_BANNER: 'spotify',
    }
    assert profile['platforms_id']['spotify'] == 'lp123'


def test_ensure_profile_keeps_the_track_derived_spotify_id(
    tmp_path, monkeypatch
):
    calls = []

    def search(name):
        calls.append(name)
        return {'id': 'namesake', 'name': name}

    monkeypatch.setattr(
        artist_profile.spotify, 'search_artist_by_name', search
    )
    a, b, c, d = _no_other_platforms()
    with (
        a,
        b,
        c,
        d,
        patch(
            'downtify.artist_profile.spotify.primary_artist_id_from_track_id',
            return_value='from_track',
        ),
        patch(
            'downtify.artist_profile.spotify.artist_image_url_from_id',
            return_value='',
        ),
        patch(
            'downtify.artist_profile.spotify.artist_banner_url_from_id',
            return_value='',
        ),
        patch(
            'downtify.artist_profile.spotify.related_artist_names_from_id',
            return_value=[],
        ),
        patch(
            'downtify.artist_profile.providers.search_artists',
            return_value=[],
        ),
    ):
        profile = artist_profile.ensure_profile(
            tmp_path,
            'Same Name',
            ['Same Name/song.mp3'],
            'en',
            track_index=_fake_track_index(),
        )
    assert profile['platforms_id']['spotify'] == 'from_track'
    assert calls == []


# ── /api/artists/art/spotify_candidate by name ─────────────────────────


def test_spotify_candidate_endpoint_resolves_by_name_without_a_file(
    app_state,
):
    with (
        patch(
            'downtify.api.spotify.search_artist_by_name',
            return_value={'id': 'lp123', 'name': 'Linkin Park'},
        ),
        patch(
            'downtify.api.spotify.artist_banner_url_from_id',
            return_value='https://spotify/banner.jpg',
        ) as banner,
        patch(
            'downtify.api.spotify.artist_name_from_id',
            return_value='Linkin Park',
        ),
    ):
        result = api.artist_art_spotify_candidate_endpoint(
            file='', kind=artist_profile.KIND_BANNER, name='Linkin Park'
        )
    banner.assert_called_once_with('lp123')
    assert result == {
        'source': 'spotify',
        'name': 'Linkin Park',
        'image_url': 'https://spotify/banner.jpg',
    }


def test_spotify_candidate_endpoint_name_without_a_match_is_empty(app_state):
    with patch(
        'downtify.api.spotify.search_artist_by_name', return_value=None
    ):
        assert (
            api.artist_art_spotify_candidate_endpoint(
                file='', kind=artist_profile.KIND_PHOTO, name='Nobody'
            )
            == {}
        )


def test_spotify_candidate_endpoint_track_wins_over_the_name(
    app_state, tmp_path
):
    track_index = TrackIndex(tmp_path / 'lib.db')
    api.state.track_index = track_index
    (app_state / 'Artist - Song.mp3').write_bytes(b'audio')
    track_index.register('a' * 22, 'Artist - Song.mp3')

    def boom(name):
        raise AssertionError('name search must not run')

    with (
        patch(
            'downtify.api.spotify.primary_artist_id_from_track_id',
            return_value='from_track',
        ),
        patch('downtify.api.spotify.search_artist_by_name', boom),
        patch(
            'downtify.api.spotify.artist_image_url_from_id',
            return_value='https://spotify/img.jpg',
        ) as image,
        patch('downtify.api.spotify.artist_name_from_id', return_value='A'),
    ):
        result = api.artist_art_spotify_candidate_endpoint(
            file='Artist - Song.mp3',
            kind=artist_profile.KIND_PHOTO,
            name='Artist',
        )
    image.assert_called_once_with('from_track')
    assert result['image_url'] == 'https://spotify/img.jpg'


def test_spotify_candidate_endpoint_uses_name_when_track_is_not_spotify(
    app_state, tmp_path
):
    track_index = TrackIndex(tmp_path / 'lib.db')
    api.state.track_index = track_index
    (app_state / 'Artist - Song.mp3').write_bytes(b'audio')
    with (
        patch(
            'downtify.api.spotify.search_artist_by_name',
            return_value={'id': 'by_name', 'name': 'Artist'},
        ),
        patch(
            'downtify.api.spotify.artist_image_url_from_id',
            return_value='https://spotify/img.jpg',
        ) as image,
        patch('downtify.api.spotify.artist_name_from_id', return_value='A'),
    ):
        result = api.artist_art_spotify_candidate_endpoint(
            file='Artist - Song.mp3',
            kind=artist_profile.KIND_PHOTO,
            name='Artist',
        )
    image.assert_called_once_with('by_name')
    assert result['source'] == 'spotify'


# ── platforms_id 'itunes' -> 'applemusic' rename ───────────────────────


def _write_profile_json(tmp_path, name, platforms_id):
    path = artist_profile._profile_path_for(tmp_path, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({'name': name, 'platforms_id': platforms_id}),
        encoding='utf-8',
    )


def test_load_profile_reads_a_legacy_itunes_key_as_applemusic(tmp_path):
    _write_profile_json(
        tmp_path,
        'Evanescence',
        {'deezer': '98', 'itunes': 'evanescence/42102393'},
    )
    ids = artist_profile.load_profile(tmp_path, 'Evanescence')['platforms_id']
    assert ids['applemusic'] == 'evanescence/42102393'
    assert 'itunes' not in ids
    assert ids['deezer'] == '98'


def test_load_profile_prefers_an_existing_applemusic_over_legacy(tmp_path):
    _write_profile_json(
        tmp_path,
        'Evanescence',
        {'itunes': 'old/1', 'applemusic': 'evanescence/42102393'},
    )
    ids = artist_profile.load_profile(tmp_path, 'Evanescence')['platforms_id']
    assert ids['applemusic'] == 'evanescence/42102393'
    assert 'itunes' not in ids


def test_a_legacy_file_is_rewritten_with_the_new_key_on_save(tmp_path):
    _write_profile_json(
        tmp_path, 'Evanescence', {'itunes': 'evanescence/42102393'}
    )
    profile = artist_profile.load_profile(tmp_path, 'Evanescence')
    artist_profile._save_profile(tmp_path, 'Evanescence', profile)
    raw = json.loads(
        artist_profile._profile_path_for(tmp_path, 'Evanescence').read_text(
            encoding='utf-8'
        )
    )
    assert raw['platforms_id']['applemusic'] == 'evanescence/42102393'
    assert 'itunes' not in raw['platforms_id']


def test_fetch_bio_reuses_a_legacy_itunes_id_without_searching(tmp_path):
    _write_profile_json(
        tmp_path, 'Evanescence', {'itunes': 'evanescence/42102393'}
    )
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id'
        ) as search,
        patch(
            'downtify.artist_profile.apple_music.fetch_artist_full',
            return_value=_APPLE_FULL,
        ) as fetch,
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
    ):
        artist_profile.fetch_bio(tmp_path, 'Evanescence', 'en')
    search.assert_not_called()
    fetch.assert_called_once_with('42102393', 'en')


# ── ensure honours the artist-image settings ───────────────────────────


def _ensure_with_kinds(tmp_path, image_kinds=None):
    """Run ensure_profile for an artist Spotify resolves, with every
    lookup mocked; returns ``({kind: source}, profile)`` for the images
    it tried to save."""

    kwargs = {} if image_kinds is None else {'image_kinds': image_kinds}
    a, b, c, d = _no_other_platforms()
    with (
        a,
        b,
        c,
        d,
        patch(
            'downtify.artist_profile.spotify.search_artist_by_name',
            return_value={'id': 'sp1', 'name': 'Linkin Park'},
        ),
        patch(
            'downtify.artist_profile.spotify.artist_image_url_from_id',
            return_value='https://img/photo.jpg',
        ),
        patch(
            'downtify.artist_profile.spotify.artist_banner_url_from_id',
            return_value='https://img/banner.jpg',
        ),
        patch(
            'downtify.artist_profile.spotify.related_artist_names_from_id',
            return_value=[],
        ),
        patch(
            'downtify.artist_profile.providers.search_artists',
            return_value=[],
        ) as ytm,
        patch('downtify.artist_profile.fetch_and_save_image') as mock_save,
    ):
        profile = artist_profile.ensure_profile(
            tmp_path, 'Linkin Park', [], 'en', **kwargs
        )
    saved = {c.args[2]: c.kwargs['source'] for c in mock_save.call_args_list}
    return saved, profile, ytm


def test_ensure_profile_saves_no_images_unless_asked(tmp_path):
    saved, profile, ytm = _ensure_with_kinds(tmp_path)
    assert saved == {}
    ytm.assert_not_called()
    # The JSON metadata is not an image: it's written regardless, Spotify
    # id included.
    assert artist_profile._profile_path_for(tmp_path, 'Linkin Park').is_file()
    assert profile['platforms_id']['spotify'] == 'sp1'


def test_ensure_profile_saves_only_the_photo_when_only_it_is_enabled(
    tmp_path,
):
    saved, _, _ = _ensure_with_kinds(tmp_path, (artist_profile.KIND_PHOTO,))
    assert saved == {artist_profile.KIND_PHOTO: 'spotify'}


def test_ensure_profile_saves_only_the_banner_when_only_it_is_enabled(
    tmp_path,
):
    saved, _, _ = _ensure_with_kinds(tmp_path, (artist_profile.KIND_BANNER,))
    assert saved == {artist_profile.KIND_BANNER: 'spotify'}


def test_ensure_profile_youtube_fallback_is_also_gated(tmp_path):
    a, b, c, d = _no_other_platforms()
    with (
        a,
        b,
        c,
        d,
        patch(
            'downtify.artist_profile.providers.search_artists',
            return_value=[{'name': 'Nobody', 'cover_url': 'https://yt/x.jpg'}],
        ),
        patch('downtify.artist_profile.fetch_and_save_image') as mock_save,
    ):
        artist_profile.ensure_profile(tmp_path, 'Nobody', [], 'en')
    mock_save.assert_not_called()


@pytest.mark.parametrize(
    ('settings', 'expected'),
    [
        ({}, ()),
        (
            {
                'download_cover_art_artist': False,
                'download_cover_art_artist_banner': False,
            },
            (),
        ),
        (
            {'download_cover_art_artist': True},
            (artist_profile.KIND_PHOTO,),
        ),
        (
            {'download_cover_art_artist_banner': True},
            (artist_profile.KIND_BANNER,),
        ),
        (
            {
                'download_cover_art_artist': True,
                'download_cover_art_artist_banner': True,
            },
            (artist_profile.KIND_PHOTO, artist_profile.KIND_BANNER),
        ),
    ],
)
def test_image_kinds_follow_the_artist_cover_settings(settings, expected):
    assert api._artist_image_kinds_to_save(settings) == expected


def _ensure_endpoint_saved_kinds(app_state, settings):
    api.state.settings = settings
    a, b, c, d = _no_other_platforms_for_api()
    with (
        a,
        b,
        c,
        d,
        patch(
            'downtify.api.artist_profile.spotify.search_artist_by_name',
            return_value={'id': 'sp1', 'name': 'Linkin Park'},
        ),
        patch(
            'downtify.api.artist_profile.spotify.artist_image_url_from_id',
            return_value='https://img/photo.jpg',
        ),
        patch(
            'downtify.api.artist_profile.spotify.artist_banner_url_from_id',
            return_value='https://img/banner.jpg',
        ),
        patch(
            'downtify.api.artist_profile.spotify.related_artist_names_from_id',
            return_value=[],
        ),
        patch('downtify.api.artist_profile.fetch_and_save_image') as mock_save,
    ):
        request = _JsonRequest({'name': 'Linkin Park', 'lang': 'en'})
        asyncio.run(api.artist_profile_ensure_endpoint(request))
    return {c.args[2] for c in mock_save.call_args_list}


def _no_other_platforms_for_api():
    return (
        patch(
            'downtify.api.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.api.artist_profile.apple_music.resolve_artist_slug_id',
            return_value=None,
        ),
        patch(
            'downtify.api.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.api.artist_profile.providers.resolve_artist_id',
            return_value=None,
        ),
    )


def test_ensure_endpoint_saves_no_images_with_default_settings(app_state):
    assert _ensure_endpoint_saved_kinds(app_state, {}) == set()


def test_ensure_endpoint_saves_the_images_the_settings_enable(app_state):
    saved = _ensure_endpoint_saved_kinds(
        app_state,
        {
            'download_cover_art_artist': True,
            'download_cover_art_artist_banner': True,
        },
    )
    assert saved == {artist_profile.KIND_PHOTO, artist_profile.KIND_BANNER}


def test_ensure_endpoint_banner_setting_alone_saves_only_the_banner(
    app_state,
):
    saved = _ensure_endpoint_saved_kinds(
        app_state, {'download_cover_art_artist_banner': True}
    )
    assert saved == {artist_profile.KIND_BANNER}


# ── fetch_bio(source=...): the user picks whose bio to use ─────────────


def _fetch_bio_with(tmp_path, source, apple_full, deezer_full, name='Avril'):
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value='42102393',
        ),
        patch(
            'downtify.artist_profile.apple_music.fetch_artist_full',
            return_value=apple_full,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=deezer_full,
        ),
    ):
        return artist_profile.fetch_bio(tmp_path, name, 'en', source=source)


def test_fetch_bio_deezer_source_uses_deezers_bio_even_when_apple_has_one(
    tmp_path,
):
    profile = _fetch_bio_with(
        tmp_path, artist_profile.BIO_SOURCE_DEEZER, _APPLE_FULL, _DEEZER_FULL
    )
    assert profile['bio'] == 'Hello'  # Deezer's, not Apple's 'Hello world'
    # Everything else is still fetched the usual way.
    assert profile['origin'] == 'Little Rock, AR, United States'
    assert profile['genre'] == 'Hard rock'
    assert profile['social']['twitter'] == 'https://twitter.com/x'


def test_fetch_bio_applemusic_source_uses_apples_bio_not_deezers(tmp_path):
    profile = _fetch_bio_with(
        tmp_path,
        artist_profile.BIO_SOURCE_APPLE_MUSIC,
        _APPLE_FULL,
        _DEEZER_FULL,
    )
    assert profile['bio'] == 'Hello world'


def test_fetch_bio_applemusic_source_never_falls_back_to_deezer(tmp_path):
    artist_profile.save_bio(tmp_path, 'Avril', 'My own bio.')
    with pytest.raises(ValueError, match='Apple Music has no biography'):
        _fetch_bio_with(
            tmp_path,
            artist_profile.BIO_SOURCE_APPLE_MUSIC,
            _APPLE_FULL_NO_BIO,
            _DEEZER_FULL,
        )
    # Nothing was saved: the current bio survives the failed attempt.
    assert artist_profile.load_profile(tmp_path, 'Avril')['bio'] == (
        'My own bio.'
    )


def test_fetch_bio_deezer_source_without_a_deezer_bio_is_an_error(tmp_path):
    artist_profile.save_bio(tmp_path, 'Avril', 'My own bio.')
    with pytest.raises(ValueError, match='Deezer has no biography'):
        _fetch_bio_with(
            tmp_path,
            artist_profile.BIO_SOURCE_DEEZER,
            _APPLE_FULL,
            _DEEZER_FULL_NO_BIO,
        )
    assert artist_profile.load_profile(tmp_path, 'Avril')['bio'] == (
        'My own bio.'
    )


def test_fetch_bio_explicit_source_replaces_an_existing_bio(tmp_path):
    artist_profile.save_bio(tmp_path, 'Avril', 'My own bio.')
    profile = _fetch_bio_with(
        tmp_path, artist_profile.BIO_SOURCE_DEEZER, _APPLE_FULL, _DEEZER_FULL
    )
    assert profile['bio'] == 'Hello'
    assert artist_profile.load_profile(tmp_path, 'Avril')['bio'] == 'Hello'


def test_fetch_bio_auto_is_unchanged_apple_then_deezer_fallback(tmp_path):
    assert (
        _fetch_bio_with(tmp_path, 'auto', _APPLE_FULL, _DEEZER_FULL)['bio']
        == 'Hello world'
    )
    other = tmp_path / 'other'
    assert (
        _fetch_bio_with(other, 'auto', _APPLE_FULL_NO_BIO, _DEEZER_FULL)['bio']
        == 'Hello'
    )


def test_fetch_bio_rejects_an_unknown_source(tmp_path):
    with pytest.raises(ValueError, match='Unknown bio source'):
        artist_profile.fetch_bio(tmp_path, 'Avril', 'en', source='spotify')


def test_bio_endpoint_passes_the_chosen_source(app_state):
    seen = {}

    def fake_fetch(download_dir, name, lang, source):
        seen.update(name=name, lang=lang, source=source)
        return {'bio': 'x'}

    with patch('downtify.api.artist_profile.fetch_bio', fake_fetch):
        request = _JsonRequest({
            'name': 'Avril',
            'lang': 'pt-BR',
            'source': 'deezer',
        })
        asyncio.run(api.artist_profile_bio_endpoint(request))
    assert seen == {'name': 'Avril', 'lang': 'pt-BR', 'source': 'deezer'}


def test_bio_endpoint_defaults_to_auto_when_no_source_is_sent(app_state):
    seen = {}

    def fake_fetch(download_dir, name, lang, source):
        seen['source'] = source
        return {'bio': 'x'}

    with patch('downtify.api.artist_profile.fetch_bio', fake_fetch):
        asyncio.run(
            api.artist_profile_bio_endpoint(_JsonRequest({'name': 'Avril'}))
        )
    assert seen['source'] == 'auto'


def test_bio_endpoint_turns_a_missing_source_bio_into_a_400(app_state):
    def fake_fetch(*args):
        raise ValueError('Deezer has no biography for this artist')

    with patch('downtify.api.artist_profile.fetch_bio', fake_fetch):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                api.artist_profile_bio_endpoint(
                    _JsonRequest({'name': 'Avril', 'source': 'deezer'})
                )
            )
    assert exc.value.status_code == 400
    assert 'Deezer has no biography' in exc.value.detail


# ── a re-fetch must never wipe social links the user filled in ─────────

_DEEZER_SOCIAL_SPARSE = {
    **_DEEZER_FULL,
    # What Deezer really sends for an artist it only partly knows: the
    # networks it lacks come back as empty strings, not missing keys.
    'social': {
        'twitter': 'https://twitter.com/deezer_twitter',
        'facebook': '',
        'website': '',
        'instagram': '',
    },
}


def _refetch_social(tmp_path, saved_social, deezer_full):
    artist_profile.save_social(tmp_path, 'Evanescence', saved_social)
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value=None,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='98',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=deezer_full,
        ),
    ):
        profile = artist_profile.fetch_bio(tmp_path, 'Evanescence', 'en')
    # What's on disk, not just the returned dict.
    return artist_profile.load_profile(tmp_path, 'Evanescence')['social'], (
        profile['social']
    )


def test_fetch_bio_keeps_links_the_user_added_for_networks_deezer_lacks(
    tmp_path,
):
    on_disk, returned = _refetch_social(
        tmp_path,
        {
            'instagram': 'https://instagram.com/evanescence',
            'facebook': 'https://facebook.com/evanescence',
            'website': 'https://evanescence.com',
            'youtube': 'https://youtube.com/evanescence',
        },
        _DEEZER_SOCIAL_SPARSE,
    )
    for social in (on_disk, returned):
        assert social['instagram'] == 'https://instagram.com/evanescence'
        assert social['facebook'] == 'https://facebook.com/evanescence'
        assert social['website'] == 'https://evanescence.com'
        assert social['youtube'] == 'https://youtube.com/evanescence'
        # ...while Deezer still fills the one that was empty.
        assert social['twitter'] == 'https://twitter.com/deezer_twitter'


def test_fetch_bio_does_not_replace_a_link_that_is_already_there(tmp_path):
    on_disk, _ = _refetch_social(
        tmp_path,
        {'twitter': 'https://twitter.com/my_corrected_handle'},
        _DEEZER_SOCIAL_SPARSE,
    )
    assert on_disk['twitter'] == 'https://twitter.com/my_corrected_handle'


def test_fetch_bio_treats_a_blank_saved_link_as_empty(tmp_path):
    on_disk, _ = _refetch_social(
        tmp_path, {'twitter': '   '}, _DEEZER_SOCIAL_SPARSE
    )
    assert on_disk['twitter'] == 'https://twitter.com/deezer_twitter'


def test_fetch_bio_with_deezer_lacking_every_network_changes_nothing(
    tmp_path,
):
    saved = {
        'twitter': 'https://twitter.com/a',
        'instagram': 'https://instagram.com/a',
    }
    nothing = {
        **_DEEZER_FULL,
        'social': {
            'twitter': '',
            'facebook': '',
            'website': '',
            'instagram': '',
        },
    }
    on_disk, _ = _refetch_social(tmp_path, saved, nothing)
    assert on_disk['twitter'] == saved['twitter']
    assert on_disk['instagram'] == saved['instagram']


def test_fill_empty_social_never_mutates_its_inputs():
    current = {'twitter': '', 'youtube': 'https://y'}
    fetched = {'twitter': 'https://t', 'facebook': ''}
    result = artist_profile._fill_empty_social(current, fetched)
    assert result == {'twitter': 'https://t', 'youtube': 'https://y'}
    assert current == {'twitter': '', 'youtube': 'https://y'}
    assert fetched == {'twitter': 'https://t', 'facebook': ''}


# ── preview_bio: load one service's bio without saving anything ────────


def _preview(tmp_path, source, apple_full=None, deezer_full=None):
    with (
        patch(
            'downtify.artist_profile.apple_music.resolve_artist_id',
            return_value='42102393',
        ),
        patch(
            'downtify.artist_profile.apple_music.fetch_artist_full',
            return_value=apple_full or _APPLE_FULL,
        ),
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=deezer_full or _DEEZER_FULL,
        ),
    ):
        return artist_profile.preview_bio(tmp_path, 'Avril', 'en', source)


def test_preview_bio_applemusic_returns_apples_text(tmp_path):
    assert _preview(tmp_path, 'applemusic') == 'Hello world'


def test_preview_bio_deezer_returns_deezers_text(tmp_path):
    assert _preview(tmp_path, 'deezer') == 'Hello'


def test_preview_bio_writes_nothing_to_disk(tmp_path):
    artist_profile.save_bio(tmp_path, 'Avril', 'My own bio.')
    before = artist_profile._profile_path_for(tmp_path, 'Avril').read_bytes()
    _preview(tmp_path, 'applemusic')
    _preview(tmp_path, 'deezer')
    after = artist_profile._profile_path_for(tmp_path, 'Avril').read_bytes()
    assert after == before
    assert artist_profile.load_profile(tmp_path, 'Avril')['bio'] == (
        'My own bio.'
    )


def test_preview_bio_creates_no_profile_file_for_a_new_artist(tmp_path):
    _preview(tmp_path, 'deezer')
    assert not artist_profile._profile_path_for(tmp_path, 'Avril').exists()
    assert not (tmp_path / 'Metadata').exists()


def test_preview_bio_fetches_nothing_but_the_one_bio(tmp_path):
    with (
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL,
        ),
        patch('downtify.artist_profile.apple_music.fetch_artist_full') as ap,
        patch(
            'downtify.artist_profile.spotify.related_artist_names_from_id'
        ) as sp,
        patch('downtify.artist_profile.spotify.search_artist_by_name') as sn,
    ):
        artist_profile.preview_bio(tmp_path, 'Avril', 'en', 'deezer')
    ap.assert_not_called()
    sp.assert_not_called()
    sn.assert_not_called()


def test_preview_bio_reuses_a_cached_id_without_searching(tmp_path):
    existing = artist_profile.load_profile(tmp_path, 'Avril')
    existing['platforms_id']['deezer'] = '35'
    artist_profile._save_profile(tmp_path, 'Avril', existing)
    with (
        patch('downtify.artist_profile.deezer.resolve_artist_id') as search,
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL,
        ) as fetch,
    ):
        artist_profile.preview_bio(tmp_path, 'Avril', 'en', 'deezer')
    search.assert_not_called()
    fetch.assert_called_once_with('35', 'en')


def test_preview_bio_applemusic_without_a_bio_is_an_error(tmp_path):
    with pytest.raises(ValueError, match='Apple Music has no biography'):
        _preview(tmp_path, 'applemusic', apple_full=_APPLE_FULL_NO_BIO)


def test_preview_bio_deezer_without_a_bio_is_an_error(tmp_path):
    with pytest.raises(ValueError, match='Deezer has no biography'):
        _preview(tmp_path, 'deezer', deezer_full=_DEEZER_FULL_NO_BIO)


def test_preview_bio_with_no_artist_match_is_an_error(tmp_path):
    with (
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value=None,
        ),
        pytest.raises(ValueError, match='Deezer has no biography'),
    ):
        artist_profile.preview_bio(tmp_path, 'Nobody', 'en', 'deezer')


@pytest.mark.parametrize('source', ['', 'auto', 'spotify'])
def test_preview_bio_rejects_other_sources(tmp_path, source):
    with pytest.raises(ValueError, match='Unknown bio source'):
        artist_profile.preview_bio(tmp_path, 'Avril', 'en', source)


def test_bio_preview_endpoint_returns_only_the_text(app_state):
    with patch(
        'downtify.api.artist_profile.preview_bio', return_value='The bio'
    ) as preview:
        request = _JsonRequest({
            'name': 'Avril',
            'lang': 'pt-BR',
            'source': 'deezer',
        })
        result = asyncio.run(api.artist_profile_bio_preview_endpoint(request))
    assert result == {'bio': 'The bio'}
    preview.assert_called_once_with(app_state, 'Avril', 'pt-BR', 'deezer')


def test_bio_preview_endpoint_saves_nothing(app_state):
    with (
        patch(
            'downtify.artist_profile.deezer.resolve_artist_id',
            return_value='35',
        ),
        patch(
            'downtify.artist_profile.deezer.fetch_artist_full',
            return_value=_DEEZER_FULL,
        ),
    ):
        request = _JsonRequest({'name': 'Avril', 'source': 'deezer'})
        result = asyncio.run(api.artist_profile_bio_preview_endpoint(request))
    assert result == {'bio': 'Hello'}
    assert not (app_state / 'Metadata').exists()


def test_bio_preview_endpoint_maps_errors_to_400(app_state):
    with patch(
        'downtify.api.artist_profile.preview_bio',
        side_effect=ValueError('Deezer has no biography for this artist'),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                api.artist_profile_bio_preview_endpoint(
                    _JsonRequest({'name': 'Avril', 'source': 'deezer'})
                )
            )
    assert exc.value.status_code == 400
    assert 'Deezer has no biography' in exc.value.detail


def test_bio_preview_endpoint_rejects_a_blank_name(app_state):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            api.artist_profile_bio_preview_endpoint(
                _JsonRequest({'name': '  ', 'source': 'deezer'})
            )
        )
    assert exc.value.status_code == 400


# ── artists named as the disk keeps them (AC/DC -> ACDC) ───────────────


def test_a_profile_saved_as_ac_dc_is_the_one_read_for_acdc(tmp_path):
    """The files are named after the sanitized name, so the two spellings
    of one artist already share every sidecar."""

    artist_profile.save_bio(tmp_path, 'AC/DC', 'Thunderstruck.')
    assert artist_profile.load_profile(tmp_path, 'ACDC')['bio'] == (
        'Thunderstruck.'
    )
    assert artist_profile._profile_path_for(tmp_path, 'AC/DC') == (
        artist_profile._profile_path_for(tmp_path, 'ACDC')
    )


def test_the_youtube_photo_fallback_matches_the_name_the_disk_kept(tmp_path):
    with (
        patch(
            'downtify.artist_profile.providers.search_artists',
            return_value=[{'name': 'AC/DC', 'cover_url': 'https://yt/x.jpg'}],
        ),
        patch('downtify.artist_profile.fetch_and_save_image') as mock_save,
    ):
        artist_profile._seed_image_from_streams(
            tmp_path, 'ACDC', artist_profile.KIND_PHOTO, None
        )
    assert mock_save.call_count == 1
    assert mock_save.call_args.args[3] == 'https://yt/x.jpg'
    assert mock_save.call_args.kwargs['source'] == 'youtube'


def test_the_youtube_photo_fallback_ignores_a_different_artist(tmp_path):
    with (
        patch(
            'downtify.artist_profile.providers.search_artists',
            return_value=[
                {'name': 'AC/DC Tribute', 'cover_url': 'https://yt/x.jpg'}
            ],
        ),
        patch('downtify.artist_profile.fetch_and_save_image') as mock_save,
    ):
        artist_profile._seed_image_from_streams(
            tmp_path, 'ACDC', artist_profile.KIND_PHOTO, None
        )
    mock_save.assert_not_called()


# ── image versions: a replaced photo must not be served from a browser cache


def test_image_version_is_none_when_there_is_no_file(tmp_path):
    for kind in (artist_profile.KIND_PHOTO, artist_profile.KIND_BANNER):
        assert (
            artist_profile.image_version_for(tmp_path, 'Nobody', kind) is None
        )


def test_image_version_is_the_files_modified_time_in_milliseconds(tmp_path):
    artist_profile.save_image(
        tmp_path, 'Avril Lavigne', artist_profile.KIND_PHOTO, _TINY_PNG
    )
    path = artist_profile.image_path_for(
        tmp_path, 'Avril Lavigne', artist_profile.KIND_PHOTO
    )
    assert artist_profile.image_version_for(
        tmp_path, 'Avril Lavigne', artist_profile.KIND_PHOTO
    ) == int(path.stat().st_mtime * 1000)


def test_replacing_a_photo_changes_its_version_but_not_its_url(tmp_path):
    kind = artist_profile.KIND_PHOTO
    url = artist_profile.save_image(tmp_path, 'Avril Lavigne', kind, _TINY_PNG)
    path = artist_profile.image_path_for(tmp_path, 'Avril Lavigne', kind)
    os.utime(path, (1_600_000_000, 1_600_000_000))
    before = artist_profile.image_version_for(tmp_path, 'Avril Lavigne', kind)
    assert (
        artist_profile.save_image(tmp_path, 'Avril Lavigne', kind, _TINY_PNG)
        == url
    )
    after = artist_profile.image_version_for(tmp_path, 'Avril Lavigne', kind)
    assert before == 1_600_000_000_000
    assert after > before  # the URL alone would have looked unchanged


def test_photo_and_banner_have_their_own_versions(tmp_path):
    artist_profile.save_image(
        tmp_path, 'Avril Lavigne', artist_profile.KIND_PHOTO, _TINY_PNG
    )
    banner = artist_profile.image_path_for(
        tmp_path, 'Avril Lavigne', artist_profile.KIND_BANNER
    )
    assert not banner.exists()
    assert (
        artist_profile.image_version_for(
            tmp_path, 'Avril Lavigne', artist_profile.KIND_BANNER
        )
        is None
    )


def test_art_endpoint_reports_the_versions(app_state):
    artist_profile.save_image(
        app_state, 'Avril Lavigne', artist_profile.KIND_PHOTO, _TINY_PNG
    )
    result = api.artist_art_endpoint(name='Avril Lavigne')
    assert result['photo_version'] == artist_profile.image_version_for(
        app_state, 'Avril Lavigne', artist_profile.KIND_PHOTO
    )
    assert result['banner_version'] is None
    assert result['banner_url'] is None


def test_art_endpoint_version_moves_when_the_photo_is_replaced(app_state):
    kind = artist_profile.KIND_PHOTO
    artist_profile.save_image(app_state, 'Avril Lavigne', kind, _TINY_PNG)
    path = artist_profile.image_path_for(app_state, 'Avril Lavigne', kind)
    os.utime(path, (1_600_000_000, 1_600_000_000))
    first = api.artist_art_endpoint(name='Avril Lavigne')
    artist_profile.save_image(app_state, 'Avril Lavigne', kind, _TINY_PNG)
    second = api.artist_art_endpoint(name='Avril Lavigne')
    assert first['photo_url'] == second['photo_url']
    assert first['photo_version'] != second['photo_version']


# ── current_cover: the tail of the URL the saved image came from ───────


def _fetch_returning_png():
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.content = _TINY_PNG
    return patch('downtify.artist_profile.httpx.get', return_value=resp)


@pytest.mark.parametrize(
    ('url', 'expected'),
    [
        (
            'https://image-cdn-ak.spotifycdn.com/image/ab6761610000e5eb527d',
            '/image/ab6761610000e5eb527d',
        ),
        ('https://cdn.test/a/b.jpg?token=secret#frag', '/a/b.jpg'),
        (
            'https://lh3.googleusercontent.com/uE72em=w600-h600-l90-rj',
            '/uE72em=w600-h600-l90-rj',
        ),
        ('https://cdn.test', ''),
        ('https://cdn.test/', ''),
        ('', ''),
        ('   ', ''),
    ],
)
def test_origin_path_keeps_only_what_names_the_image(url, expected):
    assert artist_profile._origin_path(url) == expected


def test_fetch_and_save_records_the_urls_path_not_the_host_or_query(tmp_path):
    with _fetch_returning_png():
        artist_profile.fetch_and_save_image(
            tmp_path,
            'Linkin Park',
            artist_profile.KIND_PHOTO,
            'https://image-cdn-ak.spotifycdn.com/image/ab67?sig=xyz',
            source='spotify',
        )
    profile = artist_profile.load_profile(tmp_path, 'Linkin Park')
    assert profile['current_cover'] == '/image/ab67'
    assert not profile['current_cover_banner']


def test_the_same_image_from_another_cdn_host_records_the_same_value(tmp_path):
    values = []
    for host in ('image-cdn-ak', 'image-cdn-fa'):
        with _fetch_returning_png():
            artist_profile.fetch_and_save_image(
                tmp_path,
                'Linkin Park',
                artist_profile.KIND_PHOTO,
                f'https://{host}.spotifycdn.com/image/ab67',
                source='spotify',
            )
        values.append(
            artist_profile.load_profile(tmp_path, 'Linkin Park')[
                'current_cover'
            ]
        )
    assert values == ['/image/ab67', '/image/ab67']


def test_photo_and_banner_each_record_their_own_image(tmp_path):
    with _fetch_returning_png():
        artist_profile.fetch_and_save_image(
            tmp_path, 'A', artist_profile.KIND_PHOTO, 'https://c.test/photo'
        )
        artist_profile.fetch_and_save_image(
            tmp_path, 'A', artist_profile.KIND_BANNER, 'https://c.test/banner'
        )
    profile = artist_profile.load_profile(tmp_path, 'A')
    assert profile['current_cover'] == '/photo'
    assert profile['current_cover_banner'] == '/banner'


def test_an_upload_records_upload_and_replaces_a_previous_url(tmp_path):
    with _fetch_returning_png():
        artist_profile.fetch_and_save_image(
            tmp_path,
            'A',
            artist_profile.KIND_PHOTO,
            'https://c.test/old',
            source='deezer',
        )
    artist_profile.save_image(
        tmp_path, 'A', artist_profile.KIND_PHOTO, _TINY_PNG, source='upload'
    )
    assert artist_profile.load_profile(tmp_path, 'A')['current_cover'] == (
        'upload'
    )


def test_saving_with_no_origin_clears_what_described_the_previous_image(
    tmp_path,
):
    with _fetch_returning_png():
        artist_profile.fetch_and_save_image(
            tmp_path, 'A', artist_profile.KIND_PHOTO, 'https://c.test/old'
        )
    assert artist_profile.load_profile(tmp_path, 'A')['current_cover']
    artist_profile.save_image(
        tmp_path, 'A', artist_profile.KIND_PHOTO, _TINY_PNG
    )
    assert not artist_profile.load_profile(tmp_path, 'A')['current_cover']


def test_saving_with_no_origin_creates_no_profile_file(tmp_path):
    artist_profile.save_image(
        tmp_path, 'A', artist_profile.KIND_PHOTO, _TINY_PNG
    )
    assert not artist_profile._profile_path_for(tmp_path, 'A').exists()


def test_a_source_without_a_url_is_recorded_as_given(tmp_path):
    artist_profile.save_image(
        tmp_path, 'A', artist_profile.KIND_PHOTO, _TINY_PNG, source='spotify'
    )
    assert artist_profile.load_profile(tmp_path, 'A')['current_cover'] == (
        'spotify'
    )


def test_the_first_visit_seeding_records_the_seeded_images_path(tmp_path):
    with (
        _fetch_returning_png(),
        patch(
            'downtify.artist_profile.spotify.artist_image_url_from_id',
            return_value='https://image-cdn-ak.spotifycdn.com/image/ab6761photo',
        ),
        patch(
            'downtify.artist_profile.spotify.artist_banner_url_from_id',
            return_value='https://image-cdn-ak.spotifycdn.com/image/ab6761banner',
        ),
    ):
        for kind in (artist_profile.KIND_PHOTO, artist_profile.KIND_BANNER):
            artist_profile._seed_image_from_streams(
                tmp_path, 'Linkin Park', kind, 'sp123'
            )
    profile = artist_profile.load_profile(tmp_path, 'Linkin Park')
    assert profile['current_cover'] == '/image/ab6761photo'
    assert profile['current_cover_banner'] == '/image/ab6761banner'


def test_from_url_endpoint_records_the_path_the_picker_will_match(app_state):
    with _fetch_returning_png():
        request = _JsonRequest({
            'name': 'Linkin Park',
            'kind': 'photo',
            'image_url': 'https://cdn-images.dzcdn.net/images/artist/h4sh/1000x1000-000000-80-0-0.jpg',
            'source': 'deezer',
        })
        asyncio.run(api.artist_art_from_url_endpoint(request))
    profile = artist_profile.load_profile(app_state, 'Linkin Park')
    assert profile['current_cover'] == (
        '/images/artist/h4sh/1000x1000-000000-80-0-0.jpg'
    )
