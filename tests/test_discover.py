"""Discover: suggested artists from the library, listens and the block
list (no network - Deezer is stubbed)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from downtify import api
from downtify.deezer import find_track_preview, related_artists
from downtify.discover import (
    RELATED_TTL,
    DiscoverStore,
    album_key,
    artist_key,
    collections,
    pick_collections,
    pick_seeds,
    rank_candidates,
    recommendations,
    seed_weights,
)
from downtify.file_naming import title_key

NOW = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)


class _Body:
    def __init__(self, payload: Any = None):
        self._payload = payload

    async def json(self) -> Any:
        return self._payload


def _store(tmp_path: Path) -> DiscoverStore:
    return DiscoverStore(tmp_path / 'lib.db')


def _artist(name: str, fans: int = 0, deezer_id: str = '') -> dict[str, Any]:
    return {
        'deezer_id': deezer_id or name.lower(),
        'name': name,
        'picture_url': f'https://img/{name}.jpg',
        'fans': fans,
    }


class _Deezer:
    """A stand-in for Deezer: ``related`` by seed name, counting calls."""

    def __init__(
        self,
        related: dict[str, list[dict[str, Any]]],
        *,
        failing: frozenset[str] = frozenset(),
    ):
        self.related = related
        self.failing = failing
        self.lookups: list[str] = []
        self.fetches: list[str] = []

    def lookup_id(self, name: str) -> Optional[str]:
        self.lookups.append(name)
        if name in self.failing:
            raise ValueError('Deezer refused the request')
        return f'id-{name}' if name in self.related else None

    def fetch_related(self, deezer_id: str, limit: int):
        self.fetches.append(deezer_id)
        return self.related[deezer_id.removeprefix('id-')][:limit]


def _recommend(store, library, deezer, **kw):
    return recommendations(
        store,
        library,
        lookup_id=deezer.lookup_id,
        fetch_related=deezer.fetch_related,
        now=kw.pop('now', NOW),
        **kw,
    )


# ── keys and weights ──────────────────────────────────────────────────


def test_artist_key_matches_names_as_the_disk_keeps_them():
    assert artist_key('AC/DC') == artist_key('acdc')
    assert artist_key('  Daft   Punk ') == artist_key('daft punk')
    assert not artist_key('???')


def test_listening_outweighs_liking_which_outweighs_owning():
    library = [
        {'name': 'Owned', 'tracks': 10},
        {'name': 'Liked', 'tracks': 10, 'liked': 5},
        {'name': 'Played', 'tracks': 10, 'liked': 5},
    ]
    listens = [{'name': 'Played', 'plays': 5, 'last_played': NOW.isoformat()}]
    weights = seed_weights(library, listens, NOW)

    assert (
        weights['played']['weight']
        > weights['liked']['weight']
        > weights['owned']['weight']
        > 0
    )


def test_a_listen_fades_with_time():
    library = [{'name': 'A', 'tracks': 1}, {'name': 'B', 'tracks': 1}]
    listens = [
        {'name': 'A', 'plays': 10, 'last_played': NOW.isoformat()},
        {
            'name': 'B',
            'plays': 10,
            'last_played': (NOW - timedelta(days=365)).isoformat(),
        },
    ]
    weights = seed_weights(library, listens, NOW)

    assert weights['a']['weight'] > weights['b']['weight']


def test_only_library_artists_are_seeds():
    listens = [{'name': 'Gone', 'plays': 50, 'last_played': NOW.isoformat()}]

    weights = seed_weights([{'name': 'Here', 'tracks': 3}], listens, NOW)

    assert set(weights) == {'here'}


def test_a_big_discography_doesnt_drown_everything_else():
    library = [
        {'name': 'Prolific', 'tracks': 400},
        {'name': 'Favourite', 'tracks': 12, 'liked': 12},
    ]
    listens = [
        {'name': 'Favourite', 'plays': 30, 'last_played': NOW.isoformat()}
    ]

    seeds = pick_seeds(seed_weights(library, listens, NOW))

    assert [name for _key, name, _weight in seeds] == ['Favourite', 'Prolific']


def test_pick_seeds_keeps_the_heaviest():
    weights = {
        f'a{i}': {'name': f'A{i}', 'weight': float(i)} for i in range(20)
    }

    seeds = pick_seeds(weights, limit=3)

    assert [name for _key, name, _weight in seeds] == ['A19', 'A18', 'A17']


# ── ranking ───────────────────────────────────────────────────────────


def test_an_artist_several_seeds_suggest_ranks_first():
    seeds = [('x', 'X', 2.0), ('y', 'Y', 2.0)]
    related = {
        'x': [_artist('Solo'), _artist('Shared')],
        'y': [_artist('Other'), _artist('Shared')],
    }

    ranked = rank_candidates(seeds, related, exclude=set())

    assert ranked[0]['name'] == 'Shared'
    assert set(ranked[0]['because']) == {'X', 'Y'}


def test_library_blocked_and_seed_artists_are_never_suggested():
    seeds = [('x', 'X', 1.0), ('y', 'Y', 1.0)]
    related = {
        'x': [_artist('Y'), _artist('Owned'), _artist('Blocked')],
        'y': [_artist('New')],
    }

    ranked = rank_candidates(
        seeds, related, exclude={'owned', artist_key('BLOCKED')}
    )

    assert [r['name'] for r in ranked] == ['New']


def test_higher_on_deezers_list_scores_higher():
    ranked = rank_candidates(
        [('x', 'X', 1.0)],
        {'x': [_artist('First'), _artist('Second')]},
        exclude=set(),
    )

    assert [r['name'] for r in ranked] == ['First', 'Second']
    assert ranked[0]['score'] > ranked[1]['score']


def test_because_names_the_biggest_contributor_first():
    seeds = [('x', 'Light', 0.5), ('y', 'Heavy', 5.0)]
    related = {'x': [_artist('Z')], 'y': [_artist('Z')]}

    ranked = rank_candidates(seeds, related, exclude=set())

    assert ranked[0]['because'] == ['Heavy', 'Light']
    assert set(ranked[0]) == {
        'name',
        'deezer_id',
        'picture_url',
        'fans',
        'score',
        'because',
    }


def test_rank_respects_the_limit():
    related = {'x': [_artist(f'A{i}') for i in range(10)]}

    assert len(rank_candidates([('x', 'X', 1)], related, set(), limit=4)) == 4


# ── the store ─────────────────────────────────────────────────────────


def test_listens_add_up_under_one_artist(tmp_path):
    store = _store(tmp_path)
    store.record_listen('Daft Punk', when=NOW - timedelta(days=1))
    row = store.record_listen('daft punk', when=NOW)

    assert row == {
        'name': 'daft punk',
        'plays': 2,
        'last_played': NOW.isoformat(),
    }
    assert store.listens() == [row]
    assert store.record_listen('   ') is None


def test_clearing_listens_forgets_them(tmp_path):
    store = _store(tmp_path)
    store.record_listen('A')
    store.record_listen('B')

    assert store.clear_listens() == 2
    assert store.listens() == []


def test_block_list_round_trip(tmp_path):
    store = _store(tmp_path)

    assert store.block('AC/DC')['name'] == 'AC/DC'
    store.block('ACDC')  # the same artist: a no-op
    assert [row['name'] for row in store.blocked()] == ['AC/DC']
    assert store.blocked_keys() == {artist_key('acdc')}

    assert store.unblock('acdc') is True
    assert store.unblock('acdc') is False
    assert store.blocked() == []
    assert store.block('') is None


def test_related_cache_round_trip(tmp_path):
    store = _store(tmp_path)
    store.save_related('x', '42', [_artist('A')], when=NOW)

    cached = store.cached_related('x')

    assert cached == {
        'deezer_id': '42',
        'related': [_artist('A')],
        'fetched_at': NOW,
    }
    assert store.cached_related('missing') is None


# ── recommendations ───────────────────────────────────────────────────


def test_recommendations_end_to_end(tmp_path):
    store = _store(tmp_path)
    store.block('Blocked')
    deezer = _Deezer({
        'X': [_artist('Shared'), _artist('Blocked'), _artist('Y')],
        'Y': [_artist('Shared'), _artist('Only Y')],
    })
    library = [
        {'name': 'X', 'tracks': 5, 'liked': 1},
        {'name': 'Y', 'tracks': 5},
    ]

    result = _recommend(store, library, deezer)

    assert [a['name'] for a in result['artists']] == ['Shared', 'Only Y']
    assert result['seeds'] == ['X', 'Y']
    assert result['partial'] is False


def test_an_empty_library_suggests_nothing_without_asking_deezer(tmp_path):
    deezer = _Deezer({})

    result = _recommend(_store(tmp_path), [], deezer)

    assert result == {'artists': [], 'seeds': [], 'partial': False}
    assert deezer.lookups == []


def test_a_fresh_cache_isnt_asked_again(tmp_path):
    store = _store(tmp_path)
    deezer = _Deezer({'X': [_artist('A')]})
    library = [{'name': 'X', 'tracks': 1}]

    _recommend(store, library, deezer)
    _recommend(store, library, deezer, now=NOW + timedelta(days=1))

    assert deezer.lookups == ['X']
    assert deezer.fetches == ['id-X']


def test_a_stale_cache_is_refetched_reusing_the_saved_id(tmp_path):
    store = _store(tmp_path)
    deezer = _Deezer({'X': [_artist('A')]})
    library = [{'name': 'X', 'tracks': 1}]

    _recommend(store, library, deezer)
    deezer.related['X'] = [_artist('B')]
    later = NOW + RELATED_TTL + timedelta(hours=1)
    result = _recommend(store, library, deezer, now=later)

    assert deezer.lookups == ['X']  # the id came from the cache
    assert [a['name'] for a in result['artists']] == ['B']


def test_an_artist_deezer_doesnt_know_is_remembered(tmp_path):
    store = _store(tmp_path)
    deezer = _Deezer({})
    library = [{'name': 'Unknown', 'tracks': 1}]

    _recommend(store, library, deezer)
    _recommend(store, library, deezer, now=NOW + timedelta(days=1))

    assert deezer.lookups == ['Unknown']


def test_a_deezer_failure_is_partial_and_never_cached(tmp_path):
    store = _store(tmp_path)
    deezer = _Deezer(
        {'X': [_artist('A')], 'Y': [_artist('B')]}, failing=frozenset({'Y'})
    )
    library = [{'name': 'X', 'tracks': 2}, {'name': 'Y', 'tracks': 1}]

    result = _recommend(store, library, deezer)

    assert [a['name'] for a in result['artists']] == ['A']
    assert result['partial'] is True
    assert store.cached_related('y') is None


def test_a_failure_falls_back_to_the_stale_answer(tmp_path):
    store = _store(tmp_path)
    store.save_related('x', '', [_artist('Old')], when=NOW - RELATED_TTL * 2)
    deezer = _Deezer({}, failing=frozenset({'X'}))

    result = _recommend(store, [{'name': 'X', 'tracks': 1}], deezer)

    assert [a['name'] for a in result['artists']] == ['Old']
    assert result['partial'] is True


# ── Deezer's related-artists call ─────────────────────────────────────


def _response(payload):
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.json = lambda: payload
    return resp


def test_related_artists_maps_rows_and_drops_placeholder_photos():
    payload = {
        'data': [
            {
                'id': 664,
                'name': 'Jeff Buckley',
                'picture_big': 'https://cdn/big.jpg',
                'nb_fan': 327642,
            },
            {
                'id': 7,
                'name': 'Faceless',
                'picture_big': (
                    'https://cdn/images/artist/'
                    'd41d8cd98f00b204e9800998ecf8427e/500x500.jpg'
                ),
            },
            {'name': 'No id'},
        ]
    }
    with patch(
        'downtify.deezer.httpx.get', return_value=_response(payload)
    ) as get:
        rows = related_artists('399', limit=5)

    assert get.call_args.args[0] == 'https://api.deezer.com/artist/399/related'
    assert get.call_args.kwargs['params'] == {'limit': 5}
    assert rows == [
        {
            'deezer_id': '664',
            'name': 'Jeff Buckley',
            'picture_url': 'https://cdn/big.jpg',
            'fans': 327642,
        },
        {'deezer_id': '7', 'name': 'Faceless', 'picture_url': '', 'fans': 0},
    ]


def test_related_artists_rate_limit_is_an_error_not_an_empty_list():
    payload = {'error': {'code': 4, 'message': 'Quota limit exceeded'}}
    with (
        patch('downtify.deezer.httpx.get', return_value=_response(payload)),
        pytest.raises(ValueError, match='refused'),
    ):
        related_artists('399')


def test_related_artists_unreachable_is_an_error():
    with (
        patch('downtify.deezer.httpx.get', side_effect=OSError('down')),
        pytest.raises(ValueError, match='reach'),
    ):
        related_artists('399')


# ── endpoints ─────────────────────────────────────────────────────────


@pytest.fixture
def discover_state(monkeypatch, tmp_path):
    store = _store(tmp_path)
    monkeypatch.setattr(api.state, 'discover', store)
    return store


def test_listen_endpoint_counts_and_rejects_blank(discover_state):
    row = asyncio.run(api.record_listen_endpoint(_Body({'artist': 'Air'})))

    assert row['plays'] == 1
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.record_listen_endpoint(_Body({'artist': ' '})))
    assert exc.value.status_code == 400


def test_clear_listens_endpoint(discover_state):
    discover_state.record_listen('Air')

    assert asyncio.run(api.clear_listens_endpoint()) == {'cleared': 1}


def test_block_endpoints_round_trip(discover_state):
    asyncio.run(api.block_artist_endpoint(_Body({'name': 'Air'})))

    assert [
        r['name'] for r in asyncio.run(api.blocked_artists_endpoint())
    ] == ['Air']
    assert asyncio.run(api.unblock_artist_endpoint('air')) == {
        'name': 'air',
        'removed': True,
    }
    with pytest.raises(HTTPException):
        asyncio.run(api.block_artist_endpoint(_Body({})))


def test_discover_endpoint_needs_a_library_list(discover_state):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.discover_endpoint(_Body({'library': 'nope'})))
    assert exc.value.status_code == 400


def test_discover_endpoint_ranks_the_posted_library(
    discover_state, monkeypatch
):
    fake = _Deezer({'X': [_artist('New')]})
    monkeypatch.setattr(
        api,
        'recommendations',
        lambda store, library: recommendations(
            store,
            library,
            lookup_id=fake.lookup_id,
            fetch_related=fake.fetch_related,
        ),
    )

    result = asyncio.run(
        api.discover_endpoint(
            _Body({'library': [{'name': 'X', 'tracks': 3}, 'junk']})
        )
    )

    assert [a['name'] for a in result['artists']] == ['New']


# ── titles ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ('title', 'key'),
    [
        ('Dummy (Deluxe Edition)', 'dummy'),
        ('Roads - Live', 'roads'),
        ('Glory Box [Remastered] (2011)', 'glory box'),
        ('(Untitled)', '(untitled)'),
        ('AC/DC Song', 'acdc song'),
    ],
)
def test_title_key_ignores_edition_suffixes(title, key):
    assert title_key(title) == key


def test_album_key_matches_across_services():
    assert album_key('Portishead', 'Dummy (Deluxe)') == album_key(
        'portishead', 'Dummy'
    )


# ── Deezer preview clips ──────────────────────────────────────────────


def _track_row(title, artist, duration, preview):
    return {
        'title': title,
        'title_short': title.split(' (')[0],
        'artist': {'name': artist},
        'duration': duration,
        'preview': preview,
    }


_DZ = 'https://cdnt-preview.dzcdn.net/api/1/'


def test_find_track_preview_picks_the_same_song_closest_in_length():
    payload = {
        'data': [
            _track_row('Roads (Live)', 'Portishead', 350, _DZ + 'live'),
            _track_row('Roads', 'Cover Band', 305, _DZ + 'cover'),
            _track_row('Roads', 'Portishead', 303, _DZ + 'studio'),
            _track_row('Roads', 'Portishead', 300, 'http://x/insecure'),
        ]
    }
    with patch(
        'downtify.deezer.httpx.get', return_value=_response(payload)
    ) as get:
        url = find_track_preview('Portishead', 'Roads', 305)

    assert url == _DZ + 'studio'
    assert get.call_args.kwargs['params']['q'] == 'Portishead Roads'


def test_find_track_preview_never_plays_another_song():
    payload = {'data': [_track_row('Other', 'Portishead', 300, _DZ + 'x')]}
    with patch('downtify.deezer.httpx.get', return_value=_response(payload)):
        assert not find_track_preview('Portishead', 'Roads')
    assert not find_track_preview('', 'Roads')


def test_find_track_preview_failure_is_an_error():
    payload = {'error': {'code': 4}}
    with (
        patch('downtify.deezer.httpx.get', return_value=_response(payload)),
        pytest.raises(ValueError, match='refused'),
    ):
        find_track_preview('Portishead', 'Roads')


def test_preview_endpoint(monkeypatch):
    monkeypatch.setattr(
        api.deezer, 'find_track_preview', lambda a, t, d: f'{_DZ}{a}-{t}-{d}'
    )
    assert asyncio.run(api.song_preview_endpoint('A', 'T', 3.0)) == {
        'preview_url': f'{_DZ}A-T-3.0'
    }

    def down(*_args):
        raise ValueError('Could not reach Deezer')

    monkeypatch.setattr(api.deezer, 'find_track_preview', down)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.song_preview_endpoint('A', 'T', None))
    assert exc.value.status_code == 503


# ── albums and playlists ──────────────────────────────────────────────


def _album(aid, name, artist, kind='ALBUM', year='1994'):
    return {
        'id': aid,
        'name': name,
        'artists': [artist],
        'year': year,
        'cover_url': f'https://img/{aid}',
        'type': kind,
    }


def _playlist(pid, name, owner='Spotify'):
    return {'id': pid, 'name': name, 'owner': owner, 'cover_url': ''}


def _search_for_artist(name, albums=(), playlists=()):
    return {
        'artists': [{'id': f'art-{name}', 'name': name, 'image_url': ''}],
        'albums': list(albums),
        'playlists': list(playlists),
    }


def test_pick_collections_end_to_end():
    searches = {
        'seed': _search_for_artist(
            'Seed',
            [
                _album('s1', 'Owned (Deluxe)', 'Seed'),
                _album('s2', 'Second', 'Seed'),
                _album('s3', 'Third', 'Seed'),
                _album('s4', 'Fourth', 'Seed'),
            ],
            [
                _playlist('p-this', 'This Is Seed'),
                _playlist('p-radio', 'Seed Radio'),
            ],
        ),
        'new one': _search_for_artist(
            'New One',
            [
                _album('n0', 'Guest Spot', 'Someone Else'),
                _album('n1', 'Single', 'New One', kind='SINGLE'),
                _album('n2', 'Debut', 'New One'),
            ],
            [
                _playlist('fan', 'This Is New One', owner='A Fan'),
                _playlist('p-new', 'This Is New One'),
            ],
        ),
    }
    picked = pick_collections(
        [{'name': 'New One', 'because': ['Seed']}],
        ['Seed'],
        searches,
        owned_albums={album_key('Seed', 'Owned')},
        owned_playlists=set(),
    )

    assert [
        (a['name'], a['reason'], a['because']) for a in picked['albums']
    ] == [('Debut', 'similar', ['Seed'])]
    assert picked['albums'][0]['url'] == 'https://open.spotify.com/album/n2'
    assert [a['name'] for a in picked['more_albums']] == ['Second', 'Third']
    assert [(p['spotify_id'], p['reason']) for p in picked['playlists']] == [
        ('p-radio', 'radio'),
        ('p-new', 'this_is'),
    ]
    assert picked['artist_urls'] == {
        'New One': 'https://open.spotify.com/artist/art-New One'
    }


def test_an_artist_named_radio_something_isnt_a_radio_mix():
    searches = {
        'radiohead': _search_for_artist(
            'Radiohead', playlists=[_playlist('this', 'This Is Radiohead')]
        )
    }
    picked = pick_collections([], ['Radiohead'], searches, set(), set())

    assert picked['playlists'] == []


def test_downloaded_playlists_are_left_out():
    searches = {
        'seed': _search_for_artist(
            'Seed', playlists=[_playlist('p-radio', 'Seed Radio')]
        )
    }
    picked = pick_collections([], ['Seed'], searches, set(), {'p-radio'})

    assert picked['playlists'] == []


def test_collections_caches_searches_and_reports_failures(tmp_path):
    store = _store(tmp_path)
    deezer = _Deezer({'X': [_artist('New')]})
    calls: list[str] = []

    def search(name):
        calls.append(name)
        if name == 'New':
            raise ValueError('Spotify search failed')
        return _search_for_artist(name, [_album('x2', 'Other', 'X')])

    kw = {
        'lookup_id': deezer.lookup_id,
        'fetch_related': deezer.fetch_related,
        'search': search,
        'now': NOW,
    }
    library = [{'name': 'X', 'tracks': 2}]

    first = collections(
        store, library, [{'artist': 'X', 'title': 'Mine'}], **kw
    )
    second = collections(store, library, **kw)

    assert [a['name'] for a in first['more_albums']] == ['Other']
    assert first['partial'] is True
    assert sorted(calls) == ['New', 'New', 'X']  # X cached, New retried
    assert store.cached_search('new') is None
    assert second['partial'] is True


def test_collections_endpoint_validates_and_passes_owned(
    discover_state, monkeypatch
):
    seen = {}

    def fake(store, library, albums, playlist_ids):
        seen.update(library=library, albums=albums, ids=playlist_ids)
        return {'albums': []}

    monkeypatch.setattr(api, 'collections', fake)
    with pytest.raises(HTTPException):
        asyncio.run(api.discover_collections_endpoint(_Body({})))
    asyncio.run(
        api.discover_collections_endpoint(
            _Body({
                'library': [],
                'albums': [{'artist': 'A', 'title': 'T'}],
                'playlist_ids': 'nope',
            })
        )
    )
    assert seen == {
        'library': [],
        'albums': [{'artist': 'A', 'title': 'T'}],
        'ids': [],
    }
