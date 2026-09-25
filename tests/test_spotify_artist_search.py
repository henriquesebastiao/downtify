"""Tests for downtify.spotify.search_artist_by_name - Spotify's artist
lookup by name through the web player's ``searchSuggestions`` query."""

from __future__ import annotations

import json
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from downtify import spotify

_EMBED = {
    'props': {
        'pageProps': {
            'state': {
                'settings': {
                    'session': {
                        'accessToken': 'tok-1',
                        'accessTokenExpirationTimestampMs': str(
                            int((time.time() + 3600) * 1000)
                        ),
                    }
                }
            }
        }
    }
}


def _artist_row(name: str, artist_id: str) -> dict:
    return {
        '__typename': 'TopResultHit',
        'item': {
            '__typename': 'ArtistResponseWrapper',
            'data': {
                '__typename': 'Artist',
                'profile': {'name': name},
                'uri': f'spotify:artist:{artist_id}',
            },
        },
    }


def _other_row(kind: str) -> dict:
    return {
        '__typename': 'TopResultHit',
        'item': {
            '__typename': kind,
            'data': {'name': 'Linkin Park', 'uri': 'spotify:x:nope'},
        },
    }


def _response(rows: list[dict]) -> httpx.Response:
    body = {'data': {'searchV2': {'topResultsV2': {'itemsV2': rows}}}}
    return httpx.Response(
        200, json=body, request=httpx.Request('GET', 'https://x.test/')
    )


@pytest.fixture(autouse=True)
def _fresh_token(monkeypatch):
    monkeypatch.setattr(spotify, '_token_cache', None)
    monkeypatch.setattr(spotify, '_fetch_embed_json', lambda kind, sid: _EMBED)


def _patch_get(monkeypatch, rows, seen=None):
    def fake_get(url, **kwargs):
        if seen is not None:
            seen.append((url, kwargs))
        return _response(rows)

    monkeypatch.setattr(spotify.httpx, 'get', fake_get)


def test_finds_the_exact_name_match_and_returns_its_id(monkeypatch):
    _patch_get(
        monkeypatch,
        [
            _other_row('TrackResponseWrapper'),
            _artist_row('Linkin Park Tribute', 'wrong'),
            _artist_row('Linkin Park', '6XyY86QOPPrYVGvF9ch6wz'),
        ],
    )
    assert spotify.search_artist_by_name(' linkin park ') == {
        'id': '6XyY86QOPPrYVGvF9ch6wz',
        'name': 'Linkin Park',
    }


def test_never_returns_a_near_match(monkeypatch):
    _patch_get(monkeypatch, [_artist_row('Linkin Park Tribute', 'wrong')])
    assert spotify.search_artist_by_name('Linkin Park') is None


def test_non_artist_rows_with_the_same_name_are_ignored(monkeypatch):
    _patch_get(
        monkeypatch,
        [
            _other_row('AlbumResponseWrapper'),
            _other_row('TrackResponseWrapper'),
        ],
    )
    assert spotify.search_artist_by_name('Linkin Park') is None


def test_first_exact_match_wins_for_a_namesake(monkeypatch):
    _patch_get(
        monkeypatch,
        [_artist_row('Nobody', 'first'), _artist_row('Nobody', 'second')],
    )
    assert spotify.search_artist_by_name('Nobody')['id'] == 'first'


def test_sends_the_persisted_query_with_a_wide_result_window(monkeypatch):
    seen: list = []
    _patch_get(monkeypatch, [], seen)
    spotify.search_artist_by_name('Simple Plan')
    url, kwargs = seen[0]
    assert urlparse(url).path.endswith('/pathfinder/v1/query')
    params = kwargs['params']
    assert params['operationName'] == 'searchSuggestions'
    variables = json.loads(params['variables'])
    assert variables['query'] == 'Simple Plan'
    assert variables['numberOfTopResults'] == 20
    persisted = json.loads(params['extensions'])['persistedQuery']
    assert persisted['sha256Hash'] == spotify._SEARCH_SUGGESTIONS_HASH
    assert kwargs['headers']['Authorization'] == 'Bearer tok-1'


def test_blank_name_makes_no_request(monkeypatch):
    def boom(*a, **k):
        raise AssertionError('no request expected')

    monkeypatch.setattr(spotify.httpx, 'get', boom)
    monkeypatch.setattr(spotify, '_fetch_embed_json', boom)
    assert spotify.search_artist_by_name('   ') is None


def test_http_failure_is_none_not_an_exception(monkeypatch):
    def fail(*a, **k):
        raise httpx.ConnectError('down')

    monkeypatch.setattr(spotify.httpx, 'get', fail)
    assert spotify.search_artist_by_name('Linkin Park') is None


def test_persisted_query_error_payload_is_none(monkeypatch):
    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={'errors': [{'message': 'PersistedQueryNotFound'}]},
            request=httpx.Request('GET', url),
        )

    monkeypatch.setattr(spotify.httpx, 'get', fake_get)
    assert spotify.search_artist_by_name('Linkin Park') is None


def test_token_failure_is_none(monkeypatch):
    def fail(kind, sid):
        raise httpx.ConnectError('down')

    monkeypatch.setattr(spotify, '_fetch_embed_json', fail)
    assert spotify.search_artist_by_name('Linkin Park') is None


def test_token_is_cached_across_searches(monkeypatch):
    embed_calls: list = []

    def fetch(kind, sid):
        embed_calls.append(sid)
        return _EMBED

    monkeypatch.setattr(spotify, '_fetch_embed_json', fetch)
    _patch_get(monkeypatch, [])
    spotify.search_artist_by_name('A')
    spotify.search_artist_by_name('B')
    assert len(embed_calls) == 1


def test_expired_token_is_fetched_again(monkeypatch):
    embed_calls: list = []

    def fetch(kind, sid):
        embed_calls.append(sid)
        return _EMBED

    monkeypatch.setattr(spotify, '_fetch_embed_json', fetch)
    _patch_get(monkeypatch, [])
    spotify.search_artist_by_name('A')
    token, _ = spotify._token_cache
    monkeypatch.setattr(spotify, '_token_cache', (token, time.time() - 1))
    spotify.search_artist_by_name('B')
    assert len(embed_calls) == 2


def test_query_string_is_sent_url_safe(monkeypatch):
    """The params go through httpx, so a name with symbols round-trips."""

    seen: list = []
    _patch_get(monkeypatch, [], seen)
    spotify.search_artist_by_name('Panic! At The Disco')
    request = httpx.Request('GET', seen[0][0], params=seen[0][1]['params'])
    sent = parse_qs(request.url.query.decode())
    assert json.loads(sent['variables'][0])['query'] == 'Panic! At The Disco'


# ── names as the disk keeps them ───────────────────────────────────────


def test_a_name_the_disk_shortened_still_finds_the_artist(monkeypatch):
    """A track with no artist tag is named after its file: 'ACDC'."""

    _patch_get(monkeypatch, [_artist_row('AC/DC', '711MCceyCBcFnzjGY4Q7Un')])
    assert spotify.search_artist_by_name('ACDC') == {
        'id': '711MCceyCBcFnzjGY4Q7Un',
        'name': 'AC/DC',
    }


def test_the_spotify_spelling_finds_a_shortened_row(monkeypatch):
    _patch_get(monkeypatch, [_artist_row('ACDC', 'x')])
    assert spotify.search_artist_by_name('AC/DC')['id'] == 'x'


def test_a_different_artist_is_still_not_matched(monkeypatch):
    _patch_get(monkeypatch, [_artist_row('AC/DC Tribute', 'wrong')])
    assert spotify.search_artist_by_name('ACDC') is None


@pytest.mark.parametrize('name', ['???', '///', '...'])
def test_a_name_with_nothing_left_makes_no_request(monkeypatch, name):
    def boom(*a, **k):
        raise AssertionError('no request expected')

    monkeypatch.setattr(spotify.httpx, 'get', boom)
    monkeypatch.setattr(spotify, '_fetch_embed_json', boom)
    assert spotify.search_artist_by_name(name) is None
