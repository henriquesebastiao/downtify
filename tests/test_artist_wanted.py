"""The Wanted list (wanted_routes.wanted_view, GET /api/monitor/wanted):
what the artist watches still miss, across artists.

All offline: the library is faked, the catalogues are written straight
into a real monitor database.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from starlette.requests import Request

from downtify import api, artist_catalogue, monitor, wanted_routes
from downtify.auth import Principal
from downtify.library_songs import LibrarySongs
from downtify.monitor import KIND_PLAYLIST, PlaylistMonitorDB


def _row(state: str, *, wanted: bool = True, name: str = 'R') -> dict:
    return {'id': name, 'name': name, 'state': state, 'wanted': wanted}


def _songs(*titles: str, artist: str = 'Drake') -> list[dict]:
    return [
        {
            'file': f'{artist}/{artist} - {title}.mp3',
            'artist': artist,
            'title': title,
            'duration': 200,
        }
        for title in titles
    ]


def _track(title: str, artist: str = 'Drake') -> dict:
    return {'name': title, 'artists': [artist], 'duration': 200}


def _release(album_id: str, name: str, artist: str = 'Drake') -> dict:
    return {
        'album_id': album_id,
        'name': name,
        'artist': artist,
        'year': '2016',
        'source': 'deezer',
        'release_type': 'Album',
    }


def _add_release(db, watch, row: dict, titles=()):
    """A catalogue row for *watch*, with a tracklist (none when
    *titles* is empty: not read yet)."""

    db.catalogue.record(watch.id, [row])
    if titles:
        db.catalogue.store_tracks(
            watch.id,
            row['album_id'],
            [_track(t, row['artist']) for t in titles],
        )


@pytest.fixture
def db(monkeypatch, tmp_path):
    store = PlaylistMonitorDB(tmp_path / 'monitor.db')
    monkeypatch.setattr(api.state, 'monitor_db', store)
    monkeypatch.setattr(api.state, 'downloader', None)
    return store


def _library(monkeypatch, *rows):
    monkeypatch.setattr(
        api, '_library_songs', lambda: LibrarySongs(list(rows))
    )


def _artist(db, name, user_id=0):
    return db.add_playlist(
        f'UC{name}',
        name,
        f'https://x/{name}',
        60,
        monitor.KIND_ARTIST,
        user_id=user_id,
    )


def _request(user_id: int, role: str) -> Request:
    principal = Principal('session', 'client', '', user_id, 'u', role)
    return Request({
        'type': 'http',
        'method': 'GET',
        'headers': [],
        'state': {'principal': principal},
    })


# ── The pure part ───────────────────────────────────────────────────────


def test_wanted_releases_keeps_partly_and_missing_only():
    rows = [
        _row('complete', name='a'),
        _row('partly', name='b'),
        _row('skipped', name='c'),
        _row('off', name='d'),
        _row('not_watched', name='e'),
        _row('not_own', name='f'),
        _row('missing', name='g'),
        _row('missing', wanted=False, name='h'),
        _row('partly', wanted=False, name='i'),
    ]

    kept = artist_catalogue.wanted_releases(rows)

    assert [r['name'] for r in kept] == ['b', 'g']


# ── The view ────────────────────────────────────────────────────────────


def test_wanted_view_groups_by_artist_with_totals(db, monkeypatch):
    _library(monkeypatch, *_songs('One'), *_songs('Solo', artist='Adele'))
    zed = _artist(db, 'zed')
    adele = _artist(db, 'Adele')
    # Zed: one album with 1 of 3 tracks (2 missing), one with none (2).
    _add_release(
        db, zed, _release('a1', 'First', 'Drake'), ['One', 'Two', 'Three']
    )
    _add_release(db, zed, _release('a2', 'Second', 'Drake'), ['X', 'Y'])
    # Adele: 1 of 2 (1 missing).
    _add_release(
        db, adele, _release('b1', 'Solo LP', 'Adele'), ['Solo', 'Other']
    )

    view = wanted_routes.wanted_view(db, [zed, adele])

    assert [a['watch']['name'] for a in view['artists']] == ['Adele', 'zed']
    assert view['totals'] == {
        'tracks': 5,
        'releases': 3,
        'artists': 2,
        'unchecked': 0,
    }
    first = view['artists'][1]
    assert [r['name'] for r in first['releases']] == ['First', 'Second']
    assert first['missing'] == {'tracks': 4, 'releases': 2, 'unread': 0}
    assert first['checking'] is False


def test_unchecked_artist_is_listed_and_counted(db, monkeypatch):
    _library(monkeypatch)
    watch = _artist(db, 'Drake')
    _add_release(db, watch, _release('a1', 'Unread'), [])

    view = wanted_routes.wanted_view(db, [watch])

    assert [a['watch']['name'] for a in view['artists']] == ['Drake']
    assert view['artists'][0]['missing']['unread'] == 1
    assert view['totals'] == {
        'tracks': 0,
        'releases': 0,
        'artists': 1,
        'unchecked': 1,
    }


def test_complete_artist_is_left_out(db, monkeypatch):
    _library(monkeypatch, *_songs('One', 'Two'))
    watch = _artist(db, 'Drake')
    _add_release(db, watch, _release('a1', 'Done'), ['One', 'Two'])

    view = wanted_routes.wanted_view(db, [watch])

    assert view['artists'] == []
    assert view['totals']['artists'] == 0


def test_no_artist_watches_is_empty(db):
    assert wanted_routes.wanted_view(db, []) == {
        'artists': [],
        'totals': {'tracks': 0, 'releases': 0, 'artists': 0, 'unchecked': 0},
    }


def test_paused_and_playlist_watches_are_left_out(db):
    active = _artist(db, 'Active')
    paused = _artist(db, 'Paused')
    db.update_playlist(paused.id, enabled=False)
    db.add_playlist('PL1', 'A playlist', 'https://x/pl', 60, KIND_PLAYLIST)

    watches = wanted_routes.scoped_artist_watches(db, _request(1, 'admin'))

    assert [w.id for w in watches] == [active.id]


def test_user_sees_only_own_watches(db):
    mine = _artist(db, 'Mine', user_id=2)
    _artist(db, 'Theirs', user_id=3)

    own = wanted_routes.scoped_artist_watches(db, _request(2, 'user'))
    everyone = wanted_routes.scoped_artist_watches(db, _request(1, 'admin'))

    assert [w.id for w in own] == [mine.id]
    assert len(everyone) == 2


def test_library_index_is_built_once(db, monkeypatch):
    built: list[int] = []

    def songs() -> Any:
        built.append(1)
        return LibrarySongs([])

    monkeypatch.setattr(api, '_library_songs', songs)
    watches = [_artist(db, n) for n in ('A', 'B', 'C')]
    for watch in watches:
        _add_release(db, watch, _release('r1', 'LP'), ['One', 'Two'])

    view = wanted_routes.wanted_view(db, watches)

    assert len(built) == 1
    assert view['totals']['artists'] == 3


def test_the_route_returns_the_view_and_no_job(db, monkeypatch):
    _library(monkeypatch)
    watch = _artist(db, 'Drake')
    _add_release(db, watch, _release('a1', 'LP'), ['One'])

    body = asyncio.run(wanted_routes.wanted(_request(1, 'admin')))

    assert body['job'] is None
    assert body['totals']['tracks'] == 1
    json.dumps(body)
