"""Tests for the Deezer artist-photo search and bio/social/related-artist
helpers (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from downtify.deezer import (
    exact_artist_picture,
    fetch_artist_full,
    resolve_artist_id,
    search_artist,
)


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


# ── placeholder pictures and namesakes (the "Survivor" case) ───────────

_CDN = 'https://cdn-images.dzcdn.net/images/artist'
_EMPTY_HASH = 'd41d8cd98f00b204e9800998ecf8427e'


def _row(artist_id, name, fans, picture_hash):
    """A search row shaped like the real API's, all four sizes included."""

    return {
        'id': artist_id,
        'name': name,
        'nb_fan': fans,
        'link': f'https://www.deezer.com/artist/{artist_id}',
        'picture_small': f'{_CDN}/{picture_hash}/56x56-000000-80-0-0.jpg',
        'picture_medium': f'{_CDN}/{picture_hash}/250x250-000000-80-0-0.jpg',
        'picture_big': f'{_CDN}/{picture_hash}/500x500-000000-80-0-0.jpg',
        'picture_xl': f'{_CDN}/{picture_hash}/1000x1000-000000-80-0-0.jpg',
    }


# Real shape of Deezer's answer for "Survivor": an unknown namesake with
# only the placeholder listed BEFORE the real band.
_SURVIVOR = [
    _row(12593709, 'Survivor', 34, _EMPTY_HASH),
    _row(39, 'Survivor', 261382, '120fb04f94eca09d46b10bc661eb3044'),
    _row(288356791, 'Survivor', 2, '598a59731b3352ecd083f197911c9193'),
]


def _serve(rows):
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.json.return_value = {'data': rows}
    return patch('downtify.deezer.httpx.get', return_value=resp)


def test_resolve_artist_id_prefers_the_most_popular_namesake():
    with _serve(_SURVIVOR):
        assert resolve_artist_id('Survivor') == '39'


def test_resolve_artist_id_a_missing_fan_count_counts_as_zero():
    rows = [
        {**_row(1, 'Band', 0, 'a' * 32), 'nb_fan': None},
        _row(2, 'Band', 5, 'b' * 32),
    ]
    with _serve(rows):
        assert resolve_artist_id('Band') == '2'


def test_resolve_artist_id_ties_keep_the_first_result():
    rows = [_row(1, 'Band', 9, 'a' * 32), _row(2, 'Band', 9, 'b' * 32)]
    with _serve(rows):
        assert resolve_artist_id('Band') == '1'


def test_exact_artist_picture_picks_the_real_band_not_the_placeholder():
    with _serve(_SURVIVOR):
        url = exact_artist_picture('Survivor')
    assert (
        url
        == f'{_CDN}/120fb04f94eca09d46b10bc661eb3044/250x250-000000-80-0-0.jpg'
    )


def test_exact_artist_picture_is_none_when_the_artist_only_has_a_placeholder():
    with _serve([_row(12593709, 'Survivor', 34, _EMPTY_HASH)]):
        assert exact_artist_picture('Survivor') is None


def test_exact_artist_picture_never_swaps_in_a_lesser_namesakes_face():
    # The most popular "Band" has no photo; a fanless namesake does. The
    # namesake's face must not be shown under the real artist's name.
    rows = [
        _row(1, 'Band', 100000, _EMPTY_HASH),
        _row(2, 'Band', 3, 'c' * 32),
    ]
    with _serve(rows):
        assert exact_artist_picture('Band') is None


def test_exact_artist_picture_placeholder_is_recognised_at_any_size():
    row = _row(1, 'Band', 10, _EMPTY_HASH)
    row['picture_xl'] = ''
    row['picture_big'] = ''
    with _serve([row]):
        assert exact_artist_picture('Band') is None


def test_search_artist_leaves_out_placeholder_only_artists():
    with _serve(_SURVIVOR):
        results = search_artist('Survivor')
    assert [r['url'] for r in results] == [
        'https://www.deezer.com/artist/39',
        'https://www.deezer.com/artist/288356791',
    ]
    assert all(_EMPTY_HASH not in r['image_url'] for r in results)
