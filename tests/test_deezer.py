"""Tests for the Deezer artist-photo search and bio/social/related-artist
helpers (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from downtify.deezer import fetch_artist_full, resolve_artist_id, search_artist


def _mock_response(payload):
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.json = lambda: payload
    return resp


def test_search_artist_maps_picture_xl():
    payload = {
        'data': [
            {
                'name': 'TestArtist',
                'picture_xl': 'https://example.com/xl.jpg',
                'picture_big': 'https://example.com/big.jpg',
                'link': 'https://www.deezer.com/artist/1',
            },
        ],
    }
    with patch(
        'downtify.deezer.httpx.get', return_value=_mock_response(payload)
    ):
        results = search_artist('TestArtist')
    assert results == [
        {
            'source': 'deezer',
            'name': 'TestArtist',
            'image_url': 'https://example.com/xl.jpg',
            'url': 'https://www.deezer.com/artist/1',
        }
    ]


def test_search_artist_falls_back_to_smaller_pictures():
    payload = {
        'data': [
            {
                'name': 'TestArtist',
                'picture_medium': 'https://example.com/medium.jpg',
            },
        ],
    }
    with patch(
        'downtify.deezer.httpx.get', return_value=_mock_response(payload)
    ):
        results = search_artist('TestArtist')
    assert results[0]['image_url'] == 'https://example.com/medium.jpg'


def test_search_artist_skips_rows_without_image():
    payload = {'data': [{'name': 'NoPhotoArtist'}]}
    with patch(
        'downtify.deezer.httpx.get', return_value=_mock_response(payload)
    ):
        assert search_artist('NoPhotoArtist') == []


def test_search_artist_empty_query_returns_empty_without_request():
    with patch('downtify.deezer.httpx.get') as mock_get:
        assert search_artist('   ') == []
    mock_get.assert_not_called()


def test_search_artist_request_failure_returns_empty():
    with patch('downtify.deezer.httpx.get', side_effect=Exception('boom')):
        assert search_artist('TestArtist') == []


# ── resolve_artist_id ────────────────────────────────────────────────────


def test_resolve_artist_id_matches_case_insensitively():
    payload = {
        'data': [
            {'id': 111, 'name': 'Some Other Band'},
            {'id': 35, 'name': 'avril lavigne'},
        ]
    }
    with patch(
        'downtify.deezer.httpx.get', return_value=_mock_response(payload)
    ):
        assert resolve_artist_id('Avril Lavigne') == '35'


def test_resolve_artist_id_no_exact_match_returns_none():
    payload = {'data': [{'id': 111, 'name': 'Someone Else'}]}
    with patch(
        'downtify.deezer.httpx.get', return_value=_mock_response(payload)
    ):
        assert resolve_artist_id('Avril Lavigne') is None


def test_resolve_artist_id_empty_name_returns_none_without_request():
    with patch('downtify.deezer.httpx.get') as mock_get:
        assert resolve_artist_id('   ') is None
    mock_get.assert_not_called()


def test_resolve_artist_id_request_failure_returns_none():
    with patch('downtify.deezer.httpx.get', side_effect=Exception('boom')):
        assert resolve_artist_id('Avril Lavigne') is None


# ── fetch_artist_full ────────────────────────────────────────────────────


def test_fetch_artist_full_parses_bio_social_and_related():
    auth_resp = _mock_response({'jwt': 'token123'})
    graphql_payload = {
        'data': {
            'artist': {
                'bio': {'full': '<p>Hello</p>'},
                'social': {
                    'twitter': 'https://twitter.com/x',
                    'facebook': '',
                    'website': '',
                    'instagram': '',
                },
                'relatedArtists': {
                    'edges': [
                        {'node': {'name': 'Simple Plan'}},
                        {'node': {'name': 'Paramore'}},
                    ]
                },
            }
        },
        'errors': [
            {'message': 'Unlogged token does not allow access to this field'}
        ],
    }
    with (
        patch('downtify.deezer.httpx.get', return_value=auth_resp),
        patch(
            'downtify.deezer.httpx.post',
            return_value=_mock_response(graphql_payload),
        ) as mock_post,
    ):
        result = fetch_artist_full('35', 'pt-BR')
    assert result == {
        'bio_html': '<p>Hello</p>',
        'social': {
            'twitter': 'https://twitter.com/x',
            'facebook': '',
            'website': '',
            'instagram': '',
        },
        'related_artist_names': ['Simple Plan', 'Paramore'],
    }
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs['headers']['Authorization'] == 'Bearer token123'
    assert call_kwargs['headers']['Accept-Language'] == 'pt-BR'
    assert call_kwargs['json']['variables']['artistId'] == '35'


def test_fetch_artist_full_missing_token_raises():
    with patch('downtify.deezer.httpx.get', return_value=_mock_response({})):
        with pytest.raises(ValueError, match='Could not fetch'):
            fetch_artist_full('35', 'en')


def test_fetch_artist_full_request_failure_raises():
    with patch('downtify.deezer.httpx.get', side_effect=Exception('boom')):
        with pytest.raises(ValueError, match='Could not fetch'):
            fetch_artist_full('35', 'en')
