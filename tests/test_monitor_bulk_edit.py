"""Editing several watches at once (PATCH /api/monitor/playlists)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from downtify import api
from downtify.auth import Principal
from downtify.monitor import KIND_ARTIST, PlaylistMonitorDB


def _request(payload: Any, user_id: int = 1, role: str = 'admin'):
    body = json.dumps(payload).encode()

    async def receive() -> dict[str, Any]:
        return {'type': 'http.request', 'body': body, 'more_body': False}

    principal = Principal('device', 'client', '', user_id, f'u{user_id}', role)
    return Request(
        {
            'type': 'http',
            'method': 'PATCH',
            'headers': [],
            'state': {'principal': principal},
        },
        receive,
    )


def _bulk(payload: Any, **who: Any) -> dict[str, Any]:
    return asyncio.run(api.update_monitor_playlists(_request(payload, **who)))


@pytest.fixture
def db(monkeypatch, tmp_path):
    store = PlaylistMonitorDB(tmp_path / 'monitor.db')
    monkeypatch.setattr(api.state, 'monitor_db', store)
    monkeypatch.setattr(api.state, 'downloader', None)
    return store


def _watches(db, count=3, user_id=0):
    return [
        db.add_playlist(
            f'pl{user_id}x{n}',
            f'Playlist {n}',
            f'https://open.spotify.com/playlist/pl{user_id}x{n}',
            1440,
            user_id=user_id,
        )
        for n in range(count)
    ]


def test_changes_the_interval_of_every_watch_named(db):
    a, b, c = _watches(db)
    out = _bulk({'ids': [a.id, b.id], 'interval_minutes': 4320})
    assert sorted(w['id'] for w in out['updated']) == [a.id, b.id]
    assert all(w['interval_minutes'] == 4320 for w in out['updated'])
    assert out['missing'] == []
    assert db.get_playlist(a.id).interval_minutes == 4320
    assert db.get_playlist(b.id).interval_minutes == 4320
    assert db.get_playlist(c.id).interval_minutes == 1440


def test_pauses_and_resumes(db):
    a, b, _ = _watches(db)
    _bulk({'ids': [a.id, b.id], 'enabled': False})
    assert not db.get_playlist(a.id).enabled
    assert not db.get_playlist(b.id).enabled
    _bulk({'ids': [a.id], 'enabled': True})
    assert db.get_playlist(a.id).enabled
    assert not db.get_playlist(b.id).enabled


def test_interval_and_enabled_together_keep_everything_else(db):
    (a,) = _watches(db, 1)
    db.update_playlist(a.id, last_checked='2026-01-01T00:00:00')
    out = _bulk({'ids': [a.id], 'interval_minutes': 10080, 'enabled': False})
    watch = out['updated'][0]
    assert watch['interval_minutes'] == 10080
    assert watch['enabled'] is False
    assert watch['name'] == 'Playlist 0'
    assert watch['last_checked'] == '2026-01-01T00:00:00'


def test_artist_watches_too(db):
    artist = db.add_playlist(
        'UCabc',
        'Some Artist',
        'https://music.youtube.com/channel/UCabc',
        1440,
        kind=KIND_ARTIST,
    )
    out = _bulk({'ids': [artist.id], 'interval_minutes': 4320})
    assert out['updated'][0]['interval_minutes'] == 4320


def test_unknown_ids_are_listed_as_missing(db):
    (a,) = _watches(db, 1)
    out = _bulk({'ids': [a.id, 9999], 'enabled': False})
    assert [w['id'] for w in out['updated']] == [a.id]
    assert out['missing'] == [9999]


def test_repeated_ids_count_once(db):
    (a,) = _watches(db, 1)
    out = _bulk({'ids': [a.id, a.id, str(a.id)], 'enabled': False})
    assert [w['id'] for w in out['updated']] == [a.id]


def test_a_user_only_changes_their_own_watches(db):
    (mine,) = _watches(db, 1, user_id=2)
    (theirs,) = _watches(db, 1, user_id=3)
    out = _bulk(
        {'ids': [mine.id, theirs.id], 'interval_minutes': 4320},
        user_id=2,
        role='user',
    )
    assert [w['id'] for w in out['updated']] == [mine.id]
    assert out['missing'] == [theirs.id]
    assert db.get_playlist(theirs.id).interval_minutes == 1440


@pytest.mark.parametrize(
    'payload',
    [
        {'interval_minutes': 60},
        {'ids': [], 'interval_minutes': 60},
        {'ids': 'all', 'interval_minutes': 60},
        {'ids': ['x'], 'interval_minutes': 60},
        {'ids': [1]},
        {'ids': [1], 'interval_minutes': 0},
        {'ids': [1], 'interval_minutes': 'soon'},
        {'ids': list(range(api.MONITOR_BULK_LIMIT + 1)), 'enabled': True},
    ],
)
def test_bad_requests_are_400_and_change_nothing(db, payload):
    (a,) = _watches(db, 1)
    with pytest.raises(HTTPException) as err:
        _bulk(payload)
    assert err.value.status_code == 400
    assert db.get_playlist(a.id).interval_minutes == 1440
    assert db.get_playlist(a.id).enabled
