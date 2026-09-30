"""Discover's Deezer-first albums and playlists, and Spotify's picks matched
back to Deezer (no network - Deezer and Spotify are stubbed)."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from downtify import api, deezer
from downtify.discover import (
    MATCH_TTL_FOUND,
    MATCH_TTL_MISSING,
    RELATED_TTL,
    album_key,
    deezer_collections,
    pick_deezer_collections,
    spotify_collections,
)
from tests.test_discover import (
    NOW,
    _album,
    _artist,
    _Body,
    _Deezer,
    _playlist,
    _search_for_artist,
    _store,
)


def _release(aid, name, kind='Album', fans=0, artist_id='a1'):
    return {
        'album_id': aid,
        'name': name,
        'artist': '',
        'artist_id': artist_id,
        'cover_url': f'https://img/{aid}',
        'year': '2001',
        'release_type': kind,
        'fans': fans,
        'url': f'https://www.deezer.com/album/{aid}',
    }


def _hundred(name, pid='p1'):
    return {
        'playlist_id': pid,
        'name': f'100% {name}',
        'owner': deezer.EDITORIAL_OWNER,
        'cover_url': '',
        'url': f'https://www.deezer.com/playlist/{pid}',
    }


# ── pick_deezer_collections (pure) ────────────────────────────────────


def test_a_full_album_beats_a_more_popular_single():
    picked = pick_deezer_collections(
        [{'name': 'New', 'because': ['X']}],
        [],
        {
            'new': [
                _release('s', 'Hit Single', 'Single', fans=900),
                _release('a2', 'Second', fans=50),
                _release('a1', 'First', fans=300),
            ]
        },
        {},
        set(),
        set(),
    )
    [album] = picked['albums']
    assert album['name'] == 'First'
    assert album['source'] == 'deezer'
    assert album['deezer_album_id'] == 'a1'
    assert album['key'] == album_key('New', 'First')
    assert album['reason'] == 'similar'
    assert album['because'] == ['X']


def test_a_single_is_suggested_when_there_is_no_album():
    picked = pick_deezer_collections(
        [{'name': 'New'}],
        [],
        {'new': [_release('s', 'Only Single', 'Single', fans=5)]},
        {},
        set(),
        set(),
    )
    assert [a['name'] for a in picked['albums']] == ['Only Single']


def test_owned_albums_are_skipped_and_seeds_get_two_each():
    picked = pick_deezer_collections(
        [],
        ['Mine'],
        {
            'mine': [
                _release('1', 'Owned', fans=999),
                _release('2', 'Second', fans=500),
                _release('3', 'Third', fans=400),
                _release('4', 'Fourth', fans=300),
            ]
        },
        {},
        {album_key('Mine', 'Owned (Deluxe Edition)')},
        set(),
    )
    more = picked['more_albums']
    assert [a['name'] for a in more] == ['Second', 'Third']
    assert all(a['reason'] == 'more_from' for a in more)
    assert all(a['because'] == ['Mine'] for a in more)


def test_hundred_playlists_skip_the_downloaded_ones():
    picked = pick_deezer_collections(
        [{'name': 'New'}, {'name': 'Other'}],
        [],
        {},
        {'new': _hundred('New', 'p1'), 'other': _hundred('Other', 'p2')},
        set(),
        {'100% other'},
    )
    [playlist] = picked['playlists']
    assert playlist['name'] == '100% New'
    assert playlist['source'] == 'deezer'
    assert playlist['reason'] == 'essentials'
    assert playlist['url'] == 'https://www.deezer.com/playlist/p1'


# ── deezer_collections (cache and failures) ───────────────────────────


class _DeezerShelves:
    """Stand-ins for the discography and "100%" playlist lookups."""

    def __init__(self, albums=None, playlists=None, failing=()):
        self.albums = albums or {}
        self.playlists = playlists or {}
        self.failing = set(failing)
        self.album_calls: list[str] = []
        self.playlist_calls: list[str] = []

    def fetch_albums(self, deezer_id: str):
        self.album_calls.append(deezer_id)
        if deezer_id in self.failing:
            raise ValueError('Deezer refused the request')
        return self.albums.get(deezer_id, [])

    def fetch_playlist(self, name: str):
        self.playlist_calls.append(name)
        if name in self.failing:
            raise ValueError('Deezer refused the request')
        return self.playlists.get(name)


def _deezer_kw(related: _Deezer, shelves: _DeezerShelves, **kw):
    return {
        'lookup_id': related.lookup_id,
        'fetch_related': related.fetch_related,
        'fetch_albums': shelves.fetch_albums,
        'fetch_playlist': shelves.fetch_playlist,
        'now': kw.pop('now', NOW),
        **kw,
    }


def test_deezer_collections_end_to_end_and_cached(tmp_path):
    store = _store(tmp_path)
    related = _Deezer({'Mine': [_artist('New', deezer_id='d-new')]})
    shelves = _DeezerShelves(
        albums={
            'id-Mine': [_release('m1', 'Mine Album', fans=10)],
            'd-new': [_release('n1', 'New Album', fans=10)],
        },
        playlists={'New': _hundred('New')},
    )
    library = [{'name': 'Mine', 'tracks': 3}]

    first = deezer_collections(store, library, **_deezer_kw(related, shelves))
    second = deezer_collections(store, library, **_deezer_kw(related, shelves))

    assert [a['name'] for a in first['albums']] == ['New Album']
    assert [a['name'] for a in first['more_albums']] == ['Mine Album']
    assert [p['name'] for p in first['playlists']] == ['100% New']
    assert first['partial'] is False
    assert second == first
    # The seed's Deezer id came from its related-artists cache; everything
    # was asked once, the second call answered from the cache.
    assert sorted(shelves.album_calls) == ['d-new', 'id-Mine']
    assert shelves.playlist_calls == ['New']


def test_no_hundred_playlist_is_remembered(tmp_path):
    store = _store(tmp_path)
    related = _Deezer({'Mine': [_artist('New')]})
    shelves = _DeezerShelves()
    library = [{'name': 'Mine', 'tracks': 3}]

    deezer_collections(store, library, **_deezer_kw(related, shelves))
    deezer_collections(store, library, **_deezer_kw(related, shelves))

    assert shelves.playlist_calls == ['New']


def test_a_deezer_failure_is_partial_and_never_cached(tmp_path):
    store = _store(tmp_path)
    related = _Deezer({'Mine': [_artist('New', deezer_id='d-new')]})
    shelves = _DeezerShelves(failing={'d-new', 'New'})
    library = [{'name': 'Mine', 'tracks': 3}]

    first = deezer_collections(store, library, **_deezer_kw(related, shelves))
    deezer_collections(store, library, **_deezer_kw(related, shelves))

    assert first['partial'] is True
    assert first['albums'] == []
    assert shelves.album_calls.count('d-new') == 2
    assert shelves.playlist_calls == ['New', 'New']
    assert store.cached_deezer('new', 'albums') is None


def test_a_stale_discography_is_used_when_deezer_fails(tmp_path):
    store = _store(tmp_path)
    related = _Deezer({'Mine': [_artist('New', deezer_id='d-new')]})
    library = [{'name': 'Mine', 'tracks': 3}]
    store.save_deezer(
        'new',
        'albums',
        [_release('n1', 'Old Answer')],
        when=NOW - RELATED_TTL - timedelta(days=1),
    )
    shelves = _DeezerShelves(failing={'d-new'})

    picked = deezer_collections(store, library, **_deezer_kw(related, shelves))

    assert [a['name'] for a in picked['albums']] == ['Old Answer']
    assert picked['partial'] is True


# ── spotify_collections (matching to Deezer) ──────────────────────────


class _Finder:
    """A stand-in for ``deezer.search_albums_by``."""

    def __init__(self, rows=None, failing=False):
        self.rows = rows or {}
        self.failing = failing
        self.calls: list[tuple[str, str]] = []

    def __call__(self, artist: str, title: str):
        self.calls.append((artist, title))
        if self.failing:
            raise ValueError('Deezer refused the request')
        return self.rows.get(title, [])


def _match_row(aid, name, artist):
    row = _release(aid, name, artist_id=f'art-{aid}')
    row['artist'] = artist
    return row


def _spotify_setup(tmp_path):
    store = _store(tmp_path)
    related = _Deezer({'Mine': [_artist('New')]})
    searches = {
        'Mine': _search_for_artist(
            'Mine',
            [_album('m1', 'Mine Classic', 'Mine')],
            [_playlist('radio1', 'Mine Radio')],
        ),
        'New': _search_for_artist(
            'New',
            [_album('n1', 'New Record (Remastered)', 'New')],
            [_playlist('this1', 'This Is New')],
        ),
    }
    return store, related, searches


def _spotify_kw(related, searches, finder, **kw):
    return {
        'lookup_id': related.lookup_id,
        'fetch_related': related.fetch_related,
        'search': lambda name: searches[name],
        'find_album': finder,
        'now': kw.pop('now', NOW),
        **kw,
    }


def test_spotify_albums_matched_to_deezer_or_kept_as_spotify(tmp_path):
    store, related, searches = _spotify_setup(tmp_path)
    finder = _Finder({
        'New Record (Remastered)': [_match_row('dz1', 'New Record', 'New')]
    })
    library = [{'name': 'Mine', 'tracks': 3}]

    picked = spotify_collections(
        store, library, **_spotify_kw(related, searches, finder)
    )

    [matched] = picked['albums']
    assert matched['source'] == 'deezer'
    assert matched['deezer_album_id'] == 'dz1'
    assert matched['deezer_artist_id'] == 'art-dz1'
    assert matched['url'] == 'https://www.deezer.com/album/dz1'
    [unmatched] = picked['more_albums']
    assert unmatched['source'] == 'spotify'
    assert unmatched['url'] == 'https://open.spotify.com/album/m1'
    assert unmatched['key'] == album_key('Mine', 'Mine Classic')
    # Only "This Is": Spotify's Radio mixes aren't offered.
    assert [p['name'] for p in picked['playlists']] == ['This Is New']
    assert picked['playlists'][0]['source'] == 'spotify'
    assert picked['partial'] is False


def test_albums_already_shown_are_not_matched(tmp_path):
    store, related, searches = _spotify_setup(tmp_path)
    finder = _Finder()
    library = [{'name': 'Mine', 'tracks': 3}]

    picked = spotify_collections(
        store,
        library,
        shown=[
            album_key('New', 'New Record'),
            album_key('Mine', 'Mine Classic'),
        ],
        **_spotify_kw(related, searches, finder),
    )

    assert picked['albums'] == []
    assert picked['more_albums'] == []
    assert finder.calls == []


def test_matches_are_cached_found_longer_than_missing(tmp_path):
    store, related, searches = _spotify_setup(tmp_path)
    finder = _Finder({
        'New Record (Remastered)': [_match_row('dz1', 'New Record', 'New')]
    })
    library = [{'name': 'Mine', 'tracks': 3}]

    spotify_collections(
        store, library, **_spotify_kw(related, searches, finder)
    )
    assert len(finder.calls) == 2

    # Within both lifetimes: nothing asked again.
    later = NOW + MATCH_TTL_MISSING - timedelta(hours=1)
    spotify_collections(
        store, library, **_spotify_kw(related, searches, finder, now=later)
    )
    assert len(finder.calls) == 2

    # Past the "missing" lifetime only the unmatched album is asked again.
    later = NOW + MATCH_TTL_MISSING + timedelta(hours=1)
    assert later < NOW + MATCH_TTL_FOUND
    spotify_collections(
        store, library, **_spotify_kw(related, searches, finder, now=later)
    )
    assert finder.calls[2:] == [('Mine', 'Mine Classic')]


def test_a_match_failure_shows_the_spotify_album_and_isnt_cached(tmp_path):
    store, related, searches = _spotify_setup(tmp_path)
    finder = _Finder(failing=True)
    library = [{'name': 'Mine', 'tracks': 3}]

    picked = spotify_collections(
        store, library, **_spotify_kw(related, searches, finder)
    )

    assert picked['partial'] is True
    assert {a['source'] for a in picked['albums'] + picked['more_albums']} == {
        'spotify'
    }
    assert store.cached_album_match('n1') is None


def test_a_different_album_by_the_same_name_is_not_a_match(tmp_path):
    store, related, searches = _spotify_setup(tmp_path)
    finder = _Finder({
        'New Record (Remastered)': [
            _match_row('x', 'New Record', 'Someone Else'),
            _match_row('y', 'New Record Live', 'New'),
        ]
    })
    library = [{'name': 'Mine', 'tracks': 3}]

    picked = spotify_collections(
        store, library, **_spotify_kw(related, searches, finder)
    )

    assert picked['albums'][0]['source'] == 'spotify'


# ── Deezer lookups ────────────────────────────────────────────────────


def _response(payload):
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.json = lambda: payload
    return resp


@pytest.fixture(autouse=True)
def _no_throttle(monkeypatch):
    monkeypatch.setattr(deezer, '_throttle', lambda: None)


def _playlist_row(pid, title, owner):
    return {
        'id': pid,
        'title': title,
        'link': f'https://www.deezer.com/playlist/{pid}',
        'picture_xl': f'https://img/{pid}',
        'user': {'name': owner},
    }


def test_editorial_playlist_is_only_the_editors_exact_one():
    payload = {
        'data': [
            _playlist_row(1, '100% Radiohead', 'Some Fan'),
            _playlist_row(
                2, '100% Radiohead & Friends', deezer.EDITORIAL_OWNER
            ),
            _playlist_row(3, '100% Radiohead', deezer.EDITORIAL_OWNER),
        ]
    }
    with patch('downtify.deezer.httpx.get', return_value=_response(payload)):
        playlist = deezer.editorial_playlist('Radiohead')
    assert playlist['playlist_id'] == '3'
    assert playlist['owner'] == deezer.EDITORIAL_OWNER
    assert playlist['url'] == 'https://www.deezer.com/playlist/3'


def test_editorial_playlist_none_and_failure_differ():
    with patch(
        'downtify.deezer.httpx.get', return_value=_response({'data': []})
    ):
        assert deezer.editorial_playlist('Nobody') is None
    with patch(
        'downtify.deezer.httpx.get',
        return_value=_response({'error': {'code': 4}}),
    ):
        with pytest.raises(ValueError, match='Deezer refused'):
            deezer.editorial_playlist('Nobody')


def test_search_albums_by_falls_back_to_a_plain_search():
    album = {
        'id': 7,
        'title': 'Discovery',
        'artist': {'id': 27, 'name': 'Daft Punk'},
        'record_type': 'album',
    }
    calls: list[dict[str, Any]] = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return _response({'data': [album] if len(calls) == 2 else []})

    with patch('downtify.deezer.httpx.get', side_effect=fake_get):
        rows = deezer.search_albums_by('Daft Punk', 'Discovery')
    assert calls[0]['q'] == 'artist:"Daft Punk" album:"Discovery"'
    assert calls[1]['q'] == 'Daft Punk Discovery'
    assert rows[0]['album_id'] == '7'
    assert rows[0]['artist'] == 'Daft Punk'


def test_search_albums_by_falls_back_when_no_row_is_by_the_artist():
    # Deezer's field search answers with other artists' albums rather than
    # nothing (seen live for Blur's "Blur").
    others = {
        'id': 1,
        'title': 'Four Classic Albums',
        'artist': {'id': 5, 'name': 'Milt Jackson'},
    }
    blur = {'id': 2, 'title': 'Blur', 'artist': {'id': 9, 'name': 'Blur'}}
    answers = [{'data': [others]}, {'data': [blur]}]
    with patch(
        'downtify.deezer.httpx.get',
        side_effect=[_response(answer) for answer in answers],
    ):
        rows = deezer.search_albums_by('Blur', 'Blur')
    assert [row['album_id'] for row in rows] == ['2']


def test_search_albums_by_stops_at_the_field_search_when_it_finds_the_artist():
    album = {'id': 7, 'title': 'Blur', 'artist': {'id': 9, 'name': 'Blur'}}
    with patch(
        'downtify.deezer.httpx.get', return_value=_response({'data': [album]})
    ) as get:
        rows = deezer.search_albums_by('Blur', 'Blur')
    assert get.call_count == 1
    assert rows[0]['album_id'] == '7'


def test_artist_discography_follows_pages():
    pages = [
        {
            'data': [{'id': 1, 'title': 'A', 'fans': 5}],
            'next': 'https://api.deezer.com/artist/9/albums?index=100',
        },
        {'data': [{'id': 2, 'title': 'B', 'fans': 7}]},
    ]
    with patch(
        'downtify.deezer.httpx.get',
        side_effect=[_response(page) for page in pages],
    ):
        rows = deezer.artist_discography('9')
    assert [(r['album_id'], r['fans'], r['artist_id']) for r in rows] == [
        ('1', 5, '9'),
        ('2', 7, '9'),
    ]


# ── endpoints ─────────────────────────────────────────────────────────


@pytest.fixture
def discover_state(monkeypatch, tmp_path):
    store = _store(tmp_path)
    monkeypatch.setattr(api.state, 'discover', store)
    return store


def test_deezer_endpoint_validates_and_passes_lists(
    discover_state, monkeypatch
):
    seen: dict[str, Any] = {}

    def fake(store, library, albums, names):
        seen.update(library=library, albums=albums, names=names)
        return {'albums': []}

    monkeypatch.setattr(api, 'deezer_collections', fake)
    with pytest.raises(HTTPException):
        asyncio.run(api.discover_deezer_collections_endpoint(_Body({})))
    asyncio.run(
        api.discover_deezer_collections_endpoint(
            _Body({
                'library': [],
                'albums': [{'artist': 'A', 'title': 'T'}],
                'playlist_names': 'nope',
            })
        )
    )
    assert seen == {
        'library': [],
        'albums': [{'artist': 'A', 'title': 'T'}],
        'names': [],
    }


def test_spotify_endpoint_passes_what_is_shown(discover_state, monkeypatch):
    seen: dict[str, Any] = {}

    def fake(store, library, albums, ids, shown):
        seen.update(ids=ids, shown=shown)
        return {'albums': []}

    monkeypatch.setattr(api, 'spotify_collections', fake)
    asyncio.run(
        api.discover_spotify_collections_endpoint(
            _Body({'library': [], 'playlist_ids': ['s1'], 'shown': ['k']})
        )
    )
    assert seen == {'ids': ['s1'], 'shown': ['k']}
