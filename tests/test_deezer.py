"""Tests for the Deezer artist-photo search helper (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from downtify.deezer import search_artist


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
