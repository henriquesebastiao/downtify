"""Personal rankings, stable pages and explicit artist identity resolution."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from downtify import api
from downtify.artist_suggestions import artist_candidates, artist_suggestions
from downtify.auth import Principal

NOW = datetime(2026, 10, 25, tzinfo=timezone.utc)
CHANNEL = 'UC' + 'a' * 22
OTHER = 'UC' + 'b' * 22


def listen(name, plays, days=0):
    return {
        'name': name,
        'plays': plays,
        'last_played': (NOW - timedelta(days=days)).isoformat(),
    }


def rank(library=(), listens=(), watches=(), **kw):
    return artist_suggestions(library, listens, watches, now=NOW, **kw)


def test_listening_uses_recency_without_library_bias():
    out = rank(
        [{'name': 'Old', 'track_count': 500}],
        [listen('Old', 100, 180), listen('Recent', 10)],
    )
    assert [r['name'] for r in out['listening']['items']] == ['Recent', 'Old']
    assert out['listening']['items'][0]['track_count'] == 0
    assert out['half_life_days'] == 45


def test_half_life_and_future_clock_are_bounded():
    rows = rank(listens=[listen('A', 20, 45), listen('B', 10, -5)])[
        'listening'
    ]['items']
    assert [r['score'] for r in rows] == [10, 10]


def test_library_tracks_then_albums_then_name():
    out = rank([
        {'name': 'Z', 'track_count': 10, 'album_count': 2},
        {'name': 'A', 'track_count': 10, 'album_count': 2},
        {'name': 'B', 'track_count': 10, 'album_count': 3},
        {'name': 'C', 'track_count': 11, 'album_count': 1},
    ])
    assert [r['name'] for r in out['library']['items']] == ['C', 'B', 'A', 'Z']


def test_paused_watches_excluded_but_playlists_do_not_hide_artists():
    watches = [
        SimpleNamespace(name='A', kind='artist', enabled=False),
        SimpleNamespace(name='B', kind='playlist'),
    ]
    out = rank(listens=[listen('a', 5), listen('B', 2)], watches=watches)
    assert [r['name'] for r in out['listening']['items']] == ['B']


def test_independent_pagination_and_empty_state():
    listens = [listen(str(n), 50 - n) for n in range(45)]
    out = rank(listens=listens, listening_offset=20, limit=20)
    assert len(out['listening']['items']) == 20
    assert out['listening']['next_offset'] == 40
    assert out['library'] == {'items': [], 'total': 0, 'next_offset': None}
    assert (
        rank(listens=listens, listening_offset=40)['listening']['next_offset']
        is None
    )


def test_invalid_history_and_names_are_not_suggested():
    out = rank(
        listens=[
            listen('', 2),
            listen('A', 0),
            {'name': 'B', 'plays': 3, 'last_played': 'invalid'},
        ]
    )
    assert out['listening']['total'] == 0


def test_ambiguous_exact_names_require_explicit_choice():
    rows = [
        {'name': 'Same', 'artist_id': CHANNEL},
        {'name': 'Same', 'artist_id': OTHER},
    ]
    assert artist_candidates('Same', rows)['url'] is None
    assert len(artist_candidates('Same', rows)['candidates']) == 2
    assert artist_candidates('Same', rows[:1])['url'].endswith(CHANNEL)


def test_no_first_result_fallback_or_unsafe_channel():
    assert (
        artist_candidates('Wanted', [{'name': 'Other', 'artist_id': CHANNEL}])[
            'url'
        ]
        is None
    )
    assert (
        artist_candidates(
            'Wanted', [{'name': 'Wanted', 'artist_id': '../bad'}]
        )['candidates']
        == []
    )


def request(uid=7, admin=False):
    principal = Principal(
        'device', 'client', '', uid, 'owner', 'admin' if admin else 'user'
    )
    return Request({
        'type': 'http',
        'state': {'principal': principal},
        'headers': [],
    })


@pytest.mark.parametrize('admin', [False, True])
def test_endpoint_always_scopes_history_and_watches_to_current_user(
    monkeypatch, admin
):
    calls = []
    monkeypatch.setattr(
        api,
        '_require_discover',
        lambda: SimpleNamespace(
            listens=lambda uid: (
                calls.append(('listens', uid)) or [listen('Own', 3)]
            )
        ),
    )
    monkeypatch.setattr(
        api,
        '_require_monitor_db',
        lambda: SimpleNamespace(
            list_playlists=lambda uid: calls.append(('watches', uid)) or []
        ),
    )
    monkeypatch.setattr(api, 'library_context', lambda: 'context')
    monkeypatch.setattr(api, 'allowed_entry_keys', lambda req: {'visible'})
    monkeypatch.setattr(api, 'admin_hidden_rules', lambda req: None)
    monkeypatch.setattr(
        api,
        'library_artist_index',
        lambda ctx, **kw: (
            calls.append(('visibility', kw['allowed_keys'])) or []
        ),
    )
    out = api.monitor_artist_suggestions(request(admin=admin), 0, 0, 20)
    assert out['listening']['items'][0]['name'] == 'Own'
    assert calls == [
        ('visibility', {'visible'}),
        ('listens', 7),
        ('watches', 7),
    ]


def test_unauthenticated_requests_fail_before_reading_any_data():
    with pytest.raises(HTTPException) as err:
        api.monitor_artist_suggestions(None, 0, 0, 20)
    assert err.value.status_code == 401


def test_resolution_does_not_create_a_watch(monkeypatch):
    monkeypatch.setattr(
        api.providers,
        'search_artists',
        lambda name, limit: [{'name': name, 'artist_id': CHANNEL}],
    )
    monkeypatch.setattr(
        api,
        '_require_monitor_db',
        lambda: pytest.fail('GET must not create a watch'),
    )
    assert api.resolve_monitor_artist_suggestion(request(), 'Artist')[
        'url'
    ].endswith(CHANNEL)
