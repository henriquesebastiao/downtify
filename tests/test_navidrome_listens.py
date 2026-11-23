"""Navidrome plays and stars in Discover (issue #423). Offline."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from downtify import api, navidrome, navidrome_listens
from downtify.discover import seed_weights
from downtify.navidrome_listens import (
    REFRESH_SECONDS,
    RETRY_SECONDS,
    StoreWithNavidrome,
    navidrome_taste,
    taste_from,
    with_starred,
)

ANSWER = {
    'albums': [
        {
            'artist': 'Mica Ferreira',
            'plays': 30,
            'played': '2026-11-01T10:00:00Z',
        },
        {
            'artist': 'mica ferreira',
            'plays': 12,
            'played': '2026-11-20T10:00:00Z',
        },
        {'artist': 'Tomas Vale', 'plays': 3, 'played': ''},
    ],
    'starred': [
        {'artist': 'Solenne'},
        {'artist': 'Solenne'},
        {'artist': ''},
    ],
}


@pytest.fixture(autouse=True)
def fresh_cache():
    navidrome_listens.forget()
    yield
    navidrome_listens.forget()


class _Client:
    """``getAlbumList2`` / ``getStarred2`` answers, as Subsonic sends them."""

    def __init__(self, pages: list[list[dict[str, Any]]], songs=None):
        self.pages = pages
        self.songs = songs or []
        self.calls: list[tuple[str, Any]] = []

    def _request(self, endpoint, extra=None):
        self.calls.append((endpoint, extra))
        if endpoint == 'getAlbumList2':
            page = extra['offset'] // 500
            albums = self.pages[page] if page < len(self.pages) else []
            return {'albumList2': {'album': albums}}
        return {'starred2': {'song': self.songs}}

    _as_list = staticmethod(navidrome.NavidromeClient._as_list)


def test_played_and_starred_reads_every_page_and_skips_unplayed():
    full = [{'artist': 'A', 'playCount': 1, 'played': 'x'} for _ in range(500)]
    client = _Client(
        [full, [{'artist': 'B', 'playCount': 0}]],
        songs={'artist': 'C', 'title': 'one starred song'},
    )
    answer = navidrome.played_and_starred(client)
    assert len(answer['albums']) == 500
    assert answer['starred'] == [{'artist': 'C'}]
    assert [c[1]['offset'] for c in client.calls[:-1]] == [0, 500]


def test_taste_sums_plays_per_artist_and_counts_stars():
    taste = taste_from(ANSWER)
    by_name = {row['name'].casefold(): row for row in taste['listens']}
    assert by_name['mica ferreira']['plays'] == 42
    assert by_name['mica ferreira']['last_played'] == '2026-11-20T10:00:00Z'
    assert by_name['tomas vale']['plays'] == 3
    assert sum(taste['starred'].values()) == 2


def test_navidrome_plays_and_stars_weigh_the_seeds():
    taste = taste_from(ANSWER)
    library = [
        {'name': 'Mica Ferreira', 'tracks': 5, 'liked': 0},
        {'name': 'Solenne', 'tracks': 5, 'liked': 0},
        {'name': 'Quiet One', 'tracks': 5, 'liked': 0},
    ]

    class _Store:
        @staticmethod
        def listens(_user_id=None):
            return []

    store = StoreWithNavidrome(_Store(), taste['listens'])
    weights = seed_weights(
        with_starred(library, taste['starred']), store.listens(1)
    )
    by_name = {v['name']: v['weight'] for v in weights.values()}
    assert by_name['Mica Ferreira'] > by_name['Solenne'] > by_name['Quiet One']


def test_the_answer_is_cached_and_a_failure_keeps_the_last_one(monkeypatch):
    calls = {'n': 0}

    def answer(_client):
        calls['n'] += 1
        if calls['n'] == 2:
            raise OSError('Navidrome is down')
        return ANSWER

    monkeypatch.setattr(navidrome_listens, 'played_and_starred', answer)
    cfg = {'url': 'http://nd', 'username': 'me'}
    first = navidrome_taste(cfg, lambda _cfg: None, now=0)
    assert navidrome_taste(cfg, lambda _cfg: None, now=10) is first
    assert calls['n'] == 1
    # Stale: asked again, fails, the last answer is kept for a while.
    again = navidrome_taste(cfg, lambda _cfg: None, now=REFRESH_SECONDS + 1)
    assert again == first
    assert calls['n'] == 2
    navidrome_taste(cfg, lambda _cfg: None, now=REFRESH_SECONDS + 2)
    assert calls['n'] == 2
    navidrome_taste(
        cfg, lambda _cfg: None, now=REFRESH_SECONDS + RETRY_SECONDS + 2
    )
    assert calls['n'] == 3


# ── who gets it ──────────────────────────────────────────────────────


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setattr(
        api.state,
        'settings',
        {
            **api.DEFAULT_SETTINGS,
            'discover_navidrome_plays': True,
            'navidrome': {
                'enabled': True,
                'url': 'http://nd',
                'username': 'me',
                'password': 'secret',
            },
        },
    )
    monkeypatch.setattr(
        api, 'navidrome_taste', lambda _cfg, _client: taste_from(ANSWER)
    )
    admin = SimpleNamespace(admin=True)
    monkeypatch.setattr(api, 'request_is_admin', lambda r: r.admin)
    return SimpleNamespace(admin=admin, user=SimpleNamespace(admin=False))


LIBRARY = [{'name': 'Solenne', 'tracks': 2, 'liked': 1}]


class _Store:
    @staticmethod
    def listens(_user_id=None):
        return [{'name': 'Own', 'plays': 1, 'last_played': ''}]


def test_an_admins_discover_gets_navidromes_plays(server):
    store, library = api._discover_inputs(server.admin, _Store(), LIBRARY)
    assert library == [{'name': 'Solenne', 'tracks': 2, 'liked': 3}]
    names = [row['name'] for row in store.listens(1)]
    assert names[0] == 'Own'
    assert 'Mica Ferreira' in names


def test_a_users_discover_does_not(server):
    store = _Store()
    assert api._discover_inputs(server.user, store, LIBRARY) == (
        store,
        LIBRARY,
    )


def test_nothing_changes_with_the_setting_off(server):
    api.state.settings['discover_navidrome_plays'] = False
    store = _Store()
    assert api._discover_inputs(server.admin, store, LIBRARY) == (
        store,
        LIBRARY,
    )


def test_it_is_off_by_default():
    assert api.DEFAULT_SETTINGS['discover_navidrome_plays'] is False
