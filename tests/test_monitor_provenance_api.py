"""``GET /api/monitor/provenance``, ``/stats`` and
``/playlists/{id}/tracks``: who brought a song in, and what each watch
added - a user only sees their own watches by name."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from downtify import api
from downtify.auth import Principal
from downtify.monitor import PlaylistMonitorDB
from downtify.watch_history import OUTCOME_DOWNLOADED, OUTCOME_LINKED

ADMIN_ID, BOB_ID, EVE_ID = 1, 2, 3
MIX = '37i9dQZF1DXcBWIGoYBM5M'
DAILY = '37i9dQZF1DX0XUsuxWHRQd'


def _request(user_id: int, role: str = 'user') -> Request:
    principal = Principal('session', 'user', '', user_id, f'u{user_id}', role)
    return Request({
        'type': 'http',
        'method': 'GET',
        'headers': [],
        'state': {'principal': principal},
    })


ADMIN = _request(ADMIN_ID, 'admin')
BOB = _request(BOB_ID)
EVE = _request(EVE_ID)


@pytest.fixture
def db(monkeypatch, tmp_path):
    store = PlaylistMonitorDB(tmp_path / 'monitor.db')
    monkeypatch.setattr(api.state, 'monitor_db', store)
    monkeypatch.setattr(api.state, 'track_index', None)
    monkeypatch.setattr(api.state, 'file_providers', None)
    monkeypatch.setattr(api.state, 'library_visibility', None)
    monkeypatch.setattr(
        api, '_usernames', lambda: {ADMIN_ID: 'admin', BOB_ID: 'bob'}
    )
    return store


def _watches(db):
    """Bob's mix downloaded the song; Eve's daily mix found it later."""

    mix = db.add_playlist(
        MIX, 'Weekly Mix', f'https://x/{MIX}', user_id=BOB_ID
    )
    daily = db.add_playlist(
        DAILY, 'Daily Mix', f'https://x/{DAILY}', user_id=EVE_ID
    )
    db.mark_track_downloaded(
        mix.id,
        'song',
        'Weekly Mix/Song.mp3',
        outcome=OUTCOME_DOWNLOADED,
        provider='youtube-music',
    )
    db.mark_track_downloaded(
        daily.id, 'song', 'Weekly Mix/Song.mp3', outcome=OUTCOME_LINKED
    )
    db.mark_track_downloaded(
        mix.id, 'other', 'Weekly Mix/Other.mp3', outcome=OUTCOME_DOWNLOADED
    )
    return mix, daily


def _provenance(request, file):
    return asyncio.run(api.monitor_provenance(request, file=file))


def test_an_admin_sees_every_watch_and_its_owner(db):
    mix, daily = _watches(db)

    found = _provenance(ADMIN, 'Weekly Mix/Song.mp3')

    assert found['origin']['watch']['id'] == mix.id
    assert found['origin']['watch']['owner'] == 'bob'
    assert found['origin']['provider'] == 'youtube-music'
    assert found['origin']['estimated'] is False
    assert [(w['id'], w['outcome']) for w in found['watches']] == [
        (mix.id, OUTCOME_DOWNLOADED),
        (daily.id, OUTCOME_LINKED),
    ]
    assert found['others'] == 0


def test_a_user_sees_only_their_own_watches_by_name(db):
    mix, daily = _watches(db)

    found = _provenance(EVE, 'Weekly Mix/Song.mp3')

    # Bob's watch downloaded it: Eve learns when, not whose.
    assert found['origin']['hidden'] is True
    assert 'name' not in found['origin']
    assert [w['id'] for w in found['watches']] == [daily.id]
    assert not found['watches'][0]['owner']
    assert found['others'] == 1


def test_a_deleted_watch_stays_the_origin(db):
    mix, _daily = _watches(db)
    db.delete_playlist(mix.id)

    found = _provenance(BOB, 'Weekly Mix/Song.mp3')

    assert found['origin']['watch'] is None
    assert found['origin']['name'] == 'Weekly Mix'
    assert found['watches'] == []
    assert found['others'] == 1


def test_provenance_needs_a_file(db):
    with pytest.raises(HTTPException) as err:
        _provenance(ADMIN, '  ')
    assert err.value.status_code == 400
    assert _provenance(ADMIN, 'Nobody/Knows.mp3') == {
        'file': 'Nobody/Knows.mp3',
        'origin': None,
        'watches': [],
        'others': 0,
    }


def test_stats_are_scoped_to_the_users_watches(db, monkeypatch):
    mix, daily = _watches(db)
    monkeypatch.setattr(
        api,
        '_watch_file_facts',
        lambda paths: (
            {'Weekly Mix/Song.mp3': 100, 'Weekly Mix/Other.mp3': 40},
            {'Weekly Mix/Song.mp3': 'youtube-music'},
        ),
    )

    everyone = asyncio.run(api.monitor_stats(ADMIN, days=7))
    eve = asyncio.run(api.monitor_stats(EVE, days=7))

    assert {row['id'] for row in everyone['watches']} == {mix.id, daily.id}
    assert everyone['totals']['bytes'] == 140
    [row] = eve['watches']
    assert row['id'] == daily.id
    assert row['storage']['shared_files'] == 1
    assert row['status']['linked'] == 1
    assert row['providers'] == {'youtube-music': 1}
    assert eve['days'] == 7


def test_a_watchs_tracks_with_how_they_got_there(db, monkeypatch):
    mix, _daily = _watches(db)
    db.history.record_failure(mix.id, {'song_id': 'x', 'name': 'Nope'}, 'err')
    on_disk = {'Weekly Mix/Song.mp3', 'Weekly Mix/Other.mp3'}
    db.mark_track_downloaded(
        mix.id, 'gone', 'Weekly Mix/Gone.mp3', outcome=OUTCOME_DOWNLOADED
    )
    monkeypatch.setattr(
        api,
        'list_entries_for_stored_paths',
        lambda ctx, paths: [
            {'file': p, 'title': p, 'size': 1} for p in paths if p in on_disk
        ],
    )

    found = asyncio.run(api.monitor_playlist_tracks(mix.id, BOB))

    assert [t['file'] for t in found['tracks']] == [
        'Weekly Mix/Other.mp3',
        'Weekly Mix/Song.mp3',
    ]
    song = found['tracks'][1]['watch']
    assert song['outcome'] == OUTCOME_DOWNLOADED
    assert song['provider'] == 'youtube-music'
    assert song['shared_with'] == 1
    assert found['missing'] == 1
    assert [f['track_id'] for f in found['failures']] == ['x']

    # Someone else's watch reads as unknown.
    with pytest.raises(HTTPException) as err:
        asyncio.run(api.monitor_playlist_tracks(mix.id, EVE))
    assert err.value.status_code == 404
