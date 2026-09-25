"""Tests for the Apple Music artist bio/origin helpers (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from downtify import apple_music
from downtify.apple_music import (
    fetch_artist_full,
    resolve_artist_id,
    resolve_artist_slug_id,
)


@pytest.fixture(autouse=True)
def _reset_token_cache():
    apple_music._token_cache['token'] = ''
    apple_music._token_cache['exp'] = 0.0
    yield
    apple_music._token_cache['token'] = ''
    apple_music._token_cache['exp'] = 0.0


def _mock_response(payload=None, text=''):
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    if payload is not None:
        resp.json = lambda: payload
    resp.text = text
    return resp


# ── resolve_artist_id ────────────────────────────────────────────────────


def test_resolve_artist_id_matches_case_insensitively():
    payload = {
        'results': [
            {'artistId': 111, 'artistName': 'Some Other Band'},
            {'artistId': 42102393, 'artistName': 'evanescence'},
        ]
    }
    with patch(
        'downtify.apple_music.httpx.get', return_value=_mock_response(payload)
    ):
        assert resolve_artist_id('Evanescence') == '42102393'


def test_resolve_artist_id_no_exact_match_returns_none():
    payload = {'results': [{'artistId': 111, 'artistName': 'Someone Else'}]}
    with patch(
        'downtify.apple_music.httpx.get', return_value=_mock_response(payload)
    ):
        assert resolve_artist_id('Evanescence') is None


def test_resolve_artist_id_empty_name_returns_none_without_request():
    with patch('downtify.apple_music.httpx.get') as mock_get:
        assert resolve_artist_id('   ') is None
    mock_get.assert_not_called()


def test_resolve_artist_id_request_failure_returns_none():
    with patch(
        'downtify.apple_music.httpx.get', side_effect=Exception('boom')
    ):
        assert resolve_artist_id('Evanescence') is None


# ── resolve_artist_slug_id ─────────────────────────────────────────────────


def test_resolve_artist_slug_id_extracts_slug_from_artist_link():
    payload = {
        'results': [
            {
                'artistId': 75950796,
                'artistName': 'Paramore',
                'artistLinkUrl': (
                    'https://music.apple.com/us/artist/paramore/75950796?uo=4'
                ),
            }
        ]
    }
    with patch(
        'downtify.apple_music.httpx.get', return_value=_mock_response(payload)
    ):
        assert resolve_artist_slug_id('Paramore') == 'paramore/75950796'


def test_resolve_artist_slug_id_no_exact_match_returns_none():
    payload = {'results': [{'artistName': 'Someone Else'}]}
    with patch(
        'downtify.apple_music.httpx.get', return_value=_mock_response(payload)
    ):
        assert resolve_artist_slug_id('Paramore') is None


def test_resolve_artist_slug_id_rejects_non_music_link():
    # entity=musicArtist can still return a same-named author/book result.
    payload = {
        'results': [
            {
                'artistName': 'Paramore',
                'artistLinkUrl': (
                    'https://books.apple.com/us/author/paramore/id123?uo=4'
                ),
            }
        ]
    }
    with patch(
        'downtify.apple_music.httpx.get', return_value=_mock_response(payload)
    ):
        assert resolve_artist_slug_id('Paramore') is None


def test_resolve_artist_slug_id_missing_link_returns_none():
    payload = {'results': [{'artistName': 'Paramore'}]}
    with patch(
        'downtify.apple_music.httpx.get', return_value=_mock_response(payload)
    ):
        assert resolve_artist_slug_id('Paramore') is None


def test_resolve_artist_slug_id_empty_name_returns_none_without_request():
    with patch('downtify.apple_music.httpx.get') as mock_get:
        assert resolve_artist_slug_id('   ') is None
    mock_get.assert_not_called()


# ── token scraping / caching ──────────────────────────────────────────────

_JWT_HEADER = apple_music._TOKEN_HEADER
_FAKE_TOKEN = f'{_JWT_HEADER}.eyJleHAiOjk5OTk5OTk5OTl9.sig'


def test_scrape_web_token_extracts_token_from_bundle():
    browse_html = '<script src="/assets/index~abc123.js"></script>'
    bundle_js = f'const t="{_FAKE_TOKEN}";'
    with patch(
        'downtify.apple_music.httpx.get',
        side_effect=[
            _mock_response(text=browse_html),
            _mock_response(text=bundle_js),
        ],
    ):
        assert apple_music._scrape_web_token() == _FAKE_TOKEN


def test_scrape_web_token_missing_bundle_link_raises():
    with patch(
        'downtify.apple_music.httpx.get',
        return_value=_mock_response(text='<html></html>'),
    ):
        with pytest.raises(ValueError, match='bundle'):
            apple_music._scrape_web_token()


def test_scrape_web_token_missing_token_in_bundle_raises():
    browse_html = '<script src="/assets/index~abc123.js"></script>'
    with patch(
        'downtify.apple_music.httpx.get',
        side_effect=[
            _mock_response(text=browse_html),
            _mock_response(text='no token here'),
        ],
    ):
        with pytest.raises(ValueError, match='token'):
            apple_music._scrape_web_token()


def test_current_token_reuses_cached_token_until_near_expiry():
    with patch(
        'downtify.apple_music._scrape_web_token', return_value=_FAKE_TOKEN
    ) as mock_scrape:
        first = apple_music._current_token()
        second = apple_music._current_token()
    assert first == second == _FAKE_TOKEN
    mock_scrape.assert_called_once()


def test_current_token_rescrapes_once_past_expiry():
    apple_music._token_cache['token'] = 'stale'
    apple_music._token_cache['exp'] = 0.0
    with patch(
        'downtify.apple_music._scrape_web_token', return_value=_FAKE_TOKEN
    ) as mock_scrape:
        assert apple_music._current_token() == _FAKE_TOKEN
    mock_scrape.assert_called_once()


# ── fetch_artist_full ────────────────────────────────────────────────────


def _catalog_payload(**overrides):
    attrs = {
        'artistBio': '<p>Hello <em>world</em></p>',
        'origin': 'Little Rock, AR, United States',
        'bornOrFormed': '1995',
        'isGroup': True,
        'genreNames': ['Hard rock'],
        'hero': [{'content': [{'artwork': {'bgColor': '2c2622'}}]}],
        'url': 'https://music.apple.com/us/artist/evanescence/42102393',
    }
    attrs.update(overrides)
    return {'data': [{'id': '42102393', 'attributes': attrs}]}


def test_fetch_artist_full_parses_all_fields():
    with (
        patch('downtify.apple_music._current_token', return_value='tok123'),
        patch(
            'downtify.apple_music.httpx.get',
            return_value=_mock_response(_catalog_payload()),
        ) as mock_get,
    ):
        result = fetch_artist_full('42102393', 'pt-BR')
    assert result == {
        'bio_html': '<p>Hello <em>world</em></p>',
        'origin': 'Little Rock, AR, United States',
        'born_or_formed': '1995',
        'is_group': True,
        'genre': 'Hard rock',
        'banner_bg_color': '2c2622',
        'applemusic_id': 'evanescence/42102393',
    }
    call_kwargs = mock_get.call_args.kwargs
    assert call_kwargs['headers']['Authorization'] == 'Bearer tok123'
    # pt-BR maps to the 'br' storefront - see _STOREFRONT_LANG.
    assert '/catalog/br/artists/42102393' in str(mock_get.call_args.args[0])
    assert call_kwargs['params']['l'] == 'pt-BR'


def test_fetch_artist_full_unknown_lang_falls_back_to_us():
    with (
        patch('downtify.apple_music._current_token', return_value='tok123'),
        patch(
            'downtify.apple_music.httpx.get',
            return_value=_mock_response(_catalog_payload()),
        ) as mock_get,
    ):
        fetch_artist_full('42102393', 'xx-XX')
    assert '/catalog/us/artists/42102393' in str(mock_get.call_args.args[0])
    assert mock_get.call_args.kwargs['params']['l'] == 'en-US'


def test_fetch_artist_full_missing_hero_gives_empty_bg_color():
    with (
        patch('downtify.apple_music._current_token', return_value='tok123'),
        patch(
            'downtify.apple_music.httpx.get',
            return_value=_mock_response(_catalog_payload(hero=[])),
        ),
    ):
        result = fetch_artist_full('42102393', 'en')
    assert not result['banner_bg_color']


def test_fetch_artist_full_missing_url_gives_empty_applemusic_id():
    with (
        patch('downtify.apple_music._current_token', return_value='tok123'),
        patch(
            'downtify.apple_music.httpx.get',
            return_value=_mock_response(_catalog_payload(url='')),
        ),
    ):
        result = fetch_artist_full('42102393', 'en')
    assert not result['applemusic_id']


def test_fetch_artist_full_empty_bio_stays_empty():
    with (
        patch('downtify.apple_music._current_token', return_value='tok123'),
        patch(
            'downtify.apple_music.httpx.get',
            return_value=_mock_response(_catalog_payload(artistBio='')),
        ),
    ):
        result = fetch_artist_full('42102393', 'hu')
    assert not result['bio_html']
    # Non-bio fields (origin/bornOrFormed/isGroup) aren't per-language,
    # so they're still populated even without a translated bio.
    assert result['origin'] == 'Little Rock, AR, United States'


def test_fetch_artist_full_token_failure_raises():
    with patch(
        'downtify.apple_music._current_token',
        side_effect=ValueError('no token'),
    ):
        with pytest.raises(ValueError, match='Could not fetch'):
            fetch_artist_full('42102393', 'en')


def test_fetch_artist_full_request_failure_raises():
    with (
        patch('downtify.apple_music._current_token', return_value='tok123'),
        patch('downtify.apple_music.httpx.get', side_effect=Exception('boom')),
    ):
        with pytest.raises(ValueError, match='Could not fetch'):
            fetch_artist_full('42102393', 'en')


def test_fetch_artist_full_genre_is_the_first_genre_name():
    payload = _catalog_payload(genreNames=['Alternativo', 'Rock'])
    with (
        patch('downtify.apple_music._current_token', return_value='tok'),
        patch(
            'downtify.apple_music.httpx.get',
            return_value=_mock_response(payload),
        ),
    ):
        assert fetch_artist_full('1', 'pt-BR')['genre'] == 'Alternativo'


@pytest.mark.parametrize('genres', [[], None, [None, 5]])
def test_fetch_artist_full_genre_is_empty_without_usable_names(genres):
    payload = _catalog_payload(genreNames=genres)
    with (
        patch('downtify.apple_music._current_token', return_value='tok'),
        patch(
            'downtify.apple_music.httpx.get',
            return_value=_mock_response(payload),
        ),
    ):
        assert not fetch_artist_full('1', 'en')['genre']


# ── names as the disk keeps them ───────────────────────────────────────


def test_resolve_artist_id_finds_the_artist_by_the_name_the_disk_kept():
    payload = {
        'results': [
            {
                'artistId': 5040714,
                'artistName': 'AC/DC',
                'artistLinkUrl': 'https://music.apple.com/us/artist/ac-dc/5040714',
            }
        ]
    }
    with patch(
        'downtify.apple_music.httpx.get', return_value=_mock_response(payload)
    ):
        assert resolve_artist_id('ACDC') == '5040714'
        assert resolve_artist_slug_id('ACDC') == 'ac-dc/5040714'


def test_resolve_artist_id_does_not_match_a_different_artist_by_disk_name():
    payload = {'results': [{'artistId': 1, 'artistName': 'AC/DC Tribute'}]}
    with patch(
        'downtify.apple_music.httpx.get', return_value=_mock_response(payload)
    ):
        assert resolve_artist_id('ACDC') is None


def test_resolve_artist_id_with_nothing_left_of_the_name_makes_no_request():
    with patch('downtify.apple_music.httpx.get') as get:
        assert resolve_artist_id('???') is None
    get.assert_not_called()
