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
        'unchecked_releases': 0,
        'upcoming': 0,
    }
    first = view['artists'][1]
    assert [r['name'] for r in first['releases']] == ['First', 'Second']
    assert first['missing'] == {'tracks': 4, 'releases': 2, 'unread': 0}
    assert first['checking'] is False
    assert first['unchecked'] == 0
    assert all(r['checked'] for r in first['releases'])


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
        'unchecked_releases': 1,
        'upcoming': 0,
    }
    assert view['artists'][0]['unchecked'] == 1
    assert view['artists'][0]['releases'][0]['checked'] is False


def test_a_release_with_a_count_but_no_tracklist_is_not_checked(
    db, monkeypatch
):
    _library(monkeypatch)
    watch = _artist(db, 'Drake')
    _add_release(db, watch, _release('a1', 'Known'), ['One', 'Two'])
    _add_release(db, watch, _release('a2', 'Counted'), [])
    # The catalogue lists 21 tracks, but nobody read them.
    db.catalogue.set_total(watch.id, 'a2', 21)

    view = wanted_routes.wanted_view(db, [watch])

    entry = view['artists'][0]
    by_name = {r['name']: r for r in entry['releases']}
    assert by_name['Known']['checked'] is True
    assert by_name['Counted']['checked'] is False
    assert by_name['Counted']['total'] == 21
    assert entry['unchecked'] == 1
    assert entry['missing']['tracks'] == 2
    assert entry['missing']['releases'] == 1
    assert view['totals']['tracks'] == 2
    assert view['totals']['releases'] == 1
    assert view['totals']['unchecked'] == 1
    assert view['totals']['unchecked_releases'] == 1


def test_an_artist_with_only_a_counted_unread_release_is_listed(
    db, monkeypatch
):
    _library(monkeypatch)
    watch = _artist(db, 'Drake')
    _add_release(db, watch, _release('a1', 'Counted'), [])
    db.catalogue.set_total(watch.id, 'a1', 21)

    view = wanted_routes.wanted_view(db, [watch])

    assert [a['watch']['name'] for a in view['artists']] == ['Drake']
    assert view['artists'][0]['missing']['tracks'] == 0
    assert view['totals']['tracks'] == 0
    assert view['totals']['unchecked'] == 1


def test_wanted_view_without_a_library_index(db, monkeypatch):
    monkeypatch.setattr(api, '_library_songs', lambda: None)
    watch = _artist(db, 'Drake')
    _add_release(db, watch, _release('a1', 'LP'), ['One', 'Two'])

    view = wanted_routes.wanted_view(db, [watch])

    assert view['totals']['artists'] == 1
    assert view['artists'][0]['releases'][0]['checked'] is True


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
        'totals': {
            'tracks': 0,
            'releases': 0,
            'artists': 0,
            'unchecked': 0,
            'unchecked_releases': 0,
            'upcoming': 0,
        },
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


# ── The jobs: check all, download all ───────────────────────────────────


@pytest.fixture(autouse=True)
def _fresh_job(monkeypatch):
    monkeypatch.setattr(wanted_routes, '_job', {})
    monkeypatch.setattr(api, '_inventories', {})
    monkeypatch.setattr(api.state, 'settings', {})

    # Never the real network: a test that lets the job run patches its own.
    def no_network(*_args, **_kwargs):
        raise AssertionError('the job reached the network')

    monkeypatch.setattr(wanted_routes, 'take_inventory', no_network)
    monkeypatch.setattr(wanted_routes, 'check_watch', no_network)


def _unchecked(db, name, user_id=0):
    """An artist whose catalogue has a release with no tracklist."""

    watch = _artist(db, name, user_id)
    _add_release(db, watch, _release(f'{name}1', 'LP', name))
    return watch


def _gappy(db, name, user_id=0):
    watch = _artist(db, name, user_id)
    _add_release(db, watch, _release(f'{name}1', 'LP', name), ['One', 'Two'])
    return watch


class _Spawned:
    """``spawn_task`` stand-in that keeps the task to await."""

    def __init__(self, monkeypatch):
        self.tasks: list[asyncio.Task] = []
        monkeypatch.setattr(wanted_routes.api, 'spawn_task', self.spawn)

    def spawn(self, coro, *, name=None):
        task = asyncio.get_running_loop().create_task(coro, name=name)
        self.tasks.append(task)
        return task

    async def finish(self):
        await asyncio.gather(*self.tasks)


def _admin():
    return _request(1, 'admin')


def _run(spawned, start, request):
    """Start the job, run its task to the end; the start's result."""

    async def go():
        result = await start(request)
        await spawned.finish()
        return result

    return asyncio.run(go())


def test_check_all_runs_unchecked_artists_one_by_one(db, monkeypatch):
    _library(monkeypatch)
    _unchecked(db, 'Bee')
    _unchecked(db, 'Ace')
    _gappy(db, 'Done')
    calls: list[str] = []
    busy = {'now': False}

    def fake(watch, db_, *, progress=None, stop=None):
        assert not busy['now']
        busy['now'] = True
        calls.append(watch.name)
        assert api._inventories[watch.id]['running'] is True
        assert wanted_routes._job['current'] == watch.name
        busy['now'] = False
        return {'checked': 1, 'failed': 0, 'total': 1}

    monkeypatch.setattr(wanted_routes, 'take_inventory', fake)
    spawned = _Spawned(monkeypatch)

    job = _run(spawned, wanted_routes.check_all, _admin())

    assert job['kind'] == 'check'
    assert calls == ['Ace', 'Bee']
    after = wanted_routes.public_job(wanted_routes._job)
    assert after['running'] is False
    assert after['failed'] == 0  # the fake's asserts held
    assert (after['done'], after['total'], after['current']) == (2, 2, '')
    assert 'cancel' not in after
    assert 'user_id' not in after
    assert all(
        not s['running'] and s['checked'] == 1
        for s in api._inventories.values()
    )


def test_check_all_picks_a_counted_unread_release(db, monkeypatch):
    _library(monkeypatch)
    watch = _artist(db, 'Ace')
    _add_release(db, watch, _release('a1', 'Counted', 'Ace'), [])
    db.catalogue.set_total(watch.id, 'a1', 21)
    _gappy(db, 'Done')
    calls: list[str] = []

    def fake(watch, db_, *, progress=None, stop=None):
        calls.append(watch.name)
        return {'checked': 1, 'failed': 0, 'total': 1}

    monkeypatch.setattr(wanted_routes, 'take_inventory', fake)
    spawned = _Spawned(monkeypatch)

    job = _run(spawned, wanted_routes.check_all, _admin())

    assert calls == ['Ace']
    assert job['total'] == 1


def test_download_all_runs_artists_with_gaps_one_by_one(db, monkeypatch):
    _library(monkeypatch)
    _gappy(db, 'Bee')
    _gappy(db, 'Ace')
    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(wanted_routes, 'check_running', lambda _id: False)
    calls: list[str] = []
    busy = {'now': False}

    async def fake(watch, *args, fill_missing=False):
        assert not busy['now']
        assert fill_missing is True
        busy['now'] = True
        await asyncio.sleep(0)
        calls.append(watch.name)
        busy['now'] = False

    monkeypatch.setattr(wanted_routes, 'check_watch', fake)
    spawned = _Spawned(monkeypatch)

    job = _run(spawned, wanted_routes.download_all, _admin())

    assert job['kind'] == 'download'
    assert calls == ['Ace', 'Bee']
    assert wanted_routes._job['done'] == 2
    assert wanted_routes._job['failed'] == 0


def test_download_all_needs_a_downloader(db, monkeypatch):
    _library(monkeypatch)
    _gappy(db, 'Ace')
    spawned = _Spawned(monkeypatch)

    with pytest.raises(api.HTTPException) as err:
        asyncio.run(wanted_routes.download_all(_admin()))
    assert err.value.status_code == 500
    assert spawned.tasks == []


def test_second_job_is_refused(db, monkeypatch):
    _library(monkeypatch)
    _unchecked(db, 'Ace')
    _Spawned(monkeypatch)

    async def go():
        await wanted_routes.check_all(_admin())
        await wanted_routes.check_all(_admin())

    with pytest.raises(api.HTTPException) as err:
        asyncio.run(go())
    assert err.value.status_code == 409
    assert err.value.detail == {'code': 'wanted_busy'}


def test_stop_finishes_the_current_artist_then_stops(db, monkeypatch):
    _library(monkeypatch)
    _unchecked(db, 'Ace')
    _unchecked(db, 'Bee')
    calls: list[str] = []

    def fake(watch, db_, *, progress=None, stop=None):
        calls.append(watch.name)
        wanted_routes._job['cancel'] = True  # as POST /stop sets it
        assert stop() is True
        return {'checked': 0, 'failed': 0, 'total': 0}

    monkeypatch.setattr(wanted_routes, 'take_inventory', fake)
    spawned = _Spawned(monkeypatch)

    _run(spawned, wanted_routes.check_all, _admin())

    job = wanted_routes._job
    assert calls == ['Ace']
    assert job['failed'] == 0  # the fake's `stop()` assert held
    assert job['stopped'] is True
    assert job['done'] == 1
    assert job['running'] is False


def test_stop_endpoint_cancels_the_running_job(db, monkeypatch):
    _library(monkeypatch)
    _unchecked(db, 'Ace')
    _Spawned(monkeypatch)

    async def go():
        started = await wanted_routes.check_all(_admin())
        stopped = await wanted_routes.stop(_admin())
        return started, stopped

    started, body = asyncio.run(go())
    assert started['stopping'] is False
    assert wanted_routes._job['cancel'] is True
    assert body['stopping'] is True
    assert 'cancel' not in body
    assert 'is_admin' not in body


def test_stopping_is_cleared_when_the_job_ends(db, monkeypatch):
    _library(monkeypatch)
    _unchecked(db, 'Ace')

    def fake(watch, db_, *, progress=None, stop=None):
        wanted_routes._job['cancel'] = True
        wanted_routes._job['stopping'] = True
        return {'checked': 0, 'failed': 0, 'total': 0}

    monkeypatch.setattr(wanted_routes, 'take_inventory', fake)
    spawned = _Spawned(monkeypatch)

    _run(spawned, wanted_routes.check_all, _admin())

    assert wanted_routes._job['stopping'] is False
    assert wanted_routes._job['stopped'] is True


def test_stop_after_the_reread_does_not_start_the_next_artist(db, monkeypatch):
    _library(monkeypatch)
    _unchecked(db, 'Ace')
    calls: list[str] = []
    real = db.get_playlist

    def reread(watch_id):
        wanted_routes._job['cancel'] = True  # Stop lands during the re-read
        return real(watch_id)

    monkeypatch.setattr(db, 'get_playlist', reread)

    def fake(watch, db_, *, progress=None, stop=None):
        calls.append(watch.name)
        return {'checked': 1, 'failed': 0, 'total': 1}

    monkeypatch.setattr(wanted_routes, 'take_inventory', fake)
    spawned = _Spawned(monkeypatch)

    _run(spawned, wanted_routes.check_all, _admin())

    assert calls == []
    assert wanted_routes._job['stopped'] is True
    assert wanted_routes._job['running'] is False


def test_a_database_error_counts_as_failed_and_the_job_goes_on(
    db, monkeypatch
):
    _library(monkeypatch)
    _unchecked(db, 'Ace')
    _unchecked(db, 'Bee')
    calls: list[str] = []
    real = db.get_playlist
    seen = {'n': 0}

    def flaky(watch_id):
        seen['n'] += 1
        if seen['n'] == 1:
            raise RuntimeError('database is locked')
        return real(watch_id)

    monkeypatch.setattr(db, 'get_playlist', flaky)

    def fake(watch, db_, *, progress=None, stop=None):
        calls.append(watch.name)
        return {'checked': 1, 'failed': 0, 'total': 1}

    monkeypatch.setattr(wanted_routes, 'take_inventory', fake)
    spawned = _Spawned(monkeypatch)

    _run(spawned, wanted_routes.check_all, _admin())

    job = wanted_routes._job
    assert calls == ['Bee']
    assert (job['failed'], job['done']) == (1, 2)


def test_shutdown_cancels_the_job_so_the_inventory_stops(db, monkeypatch):
    _library(monkeypatch)
    _unchecked(db, 'Ace')
    gate = asyncio.Event

    async def stuck(_job, _watch, _db):
        await gate().wait()

    monkeypatch.setattr(wanted_routes, '_check_one', stuck)
    spawned = _Spawned(monkeypatch)

    async def go():
        await wanted_routes.check_all(_admin())
        await asyncio.sleep(0.01)
        spawned.tasks[0].cancel()
        with pytest.raises(asyncio.CancelledError):
            await spawned.tasks[0]

    asyncio.run(go())

    assert wanted_routes._job['cancel'] is True
    assert wanted_routes._job['running'] is False


def test_stop_without_a_job_is_quiet(db):
    assert asyncio.run(wanted_routes.stop(_admin())) is None


def test_one_failing_artist_does_not_stop_the_job(db, monkeypatch):
    _library(monkeypatch)
    _unchecked(db, 'Ace')
    _unchecked(db, 'Bee')
    calls: list[str] = []

    def fake(watch, db_, *, progress=None, stop=None):
        calls.append(watch.name)
        if watch.name == 'Ace':
            raise RuntimeError('boom')
        return {'checked': 1, 'failed': 0, 'total': 1}

    monkeypatch.setattr(wanted_routes, 'take_inventory', fake)
    spawned = _Spawned(monkeypatch)

    _run(spawned, wanted_routes.check_all, _admin())

    job = wanted_routes._job
    assert calls == ['Ace', 'Bee']
    assert (job['failed'], job['done']) == (1, 2)


def test_download_all_skips_a_watch_being_checked(db, monkeypatch):
    _library(monkeypatch)
    ace = _gappy(db, 'Ace')
    _gappy(db, 'Bee')
    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(
        wanted_routes, 'check_running', lambda wid: wid == ace.id
    )
    calls: list[str] = []

    async def fake(watch, *args, fill_missing=False):
        calls.append(watch.name)

    monkeypatch.setattr(wanted_routes, 'check_watch', fake)
    spawned = _Spawned(monkeypatch)

    _run(spawned, wanted_routes.download_all, _admin())

    assert calls == ['Bee']
    assert wanted_routes._job['skipped'] == 1


def test_check_all_skips_a_watch_with_its_own_check_running(db, monkeypatch):
    _library(monkeypatch)
    ace = _unchecked(db, 'Ace')
    _unchecked(db, 'Bee')
    api._inventories[ace.id] = {'running': True}
    calls: list[str] = []

    def fake(watch, db_, *, progress=None, stop=None):
        calls.append(watch.name)
        return {'checked': 1, 'failed': 0, 'total': 1}

    monkeypatch.setattr(wanted_routes, 'take_inventory', fake)
    spawned = _Spawned(monkeypatch)

    _run(spawned, wanted_routes.check_all, _admin())

    assert calls == ['Bee']
    assert wanted_routes._job['skipped'] == 1
    assert wanted_routes._job['done'] == 2
    assert api._inventories[ace.id] == {'running': True}  # left alone


def test_job_skips_a_watch_removed_mid_run(db, monkeypatch):
    _library(monkeypatch)
    ace = _unchecked(db, 'Ace')
    bee = _unchecked(db, 'Bee')
    cat = _unchecked(db, 'Cat')
    calls: list[str] = []

    def fake(watch, db_, *, progress=None, stop=None):
        calls.append(watch.name)
        return {'checked': 1, 'failed': 0, 'total': 1}

    monkeypatch.setattr(wanted_routes, 'take_inventory', fake)
    spawned = _Spawned(monkeypatch)

    async def go():
        await wanted_routes.check_all(_admin())
        db.delete_playlist(bee.id)
        db.update_playlist(cat.id, enabled=False)
        await spawned.finish()

    asyncio.run(go())

    assert calls == [ace.name]
    assert wanted_routes._job['skipped'] == 2
    assert wanted_routes._job['done'] == 3


def test_the_job_route_is_light_and_scoped(db, monkeypatch):
    _library(monkeypatch)
    _unchecked(db, 'Ace', user_id=2)
    _Spawned(monkeypatch)
    starter = _request(2, 'user')

    def boom(*_args, **_kwargs):
        raise AssertionError('the job route read the list')

    async def go():
        before = await wanted_routes.wanted_job(starter)
        await wanted_routes.check_all(starter)
        monkeypatch.setattr(wanted_routes, 'wanted_view', boom)
        return (
            before,
            await wanted_routes.wanted_job(starter),
            await wanted_routes.wanted_job(_request(3, 'user')),
            await wanted_routes.wanted_job(_admin()),
        )

    before, mine, other, admin = asyncio.run(go())
    assert before == {'job': None}
    assert mine['job']['kind'] == 'check'
    assert mine['job']['running'] is True
    assert other == {'job': None}
    assert admin['job']['kind'] == 'check'
    json.dumps(mine)


def test_job_hidden_from_other_users(db, monkeypatch):
    _library(monkeypatch)
    _unchecked(db, 'Ace', user_id=2)
    _Spawned(monkeypatch)
    starter = _request(2, 'user')

    async def go():
        await wanted_routes.check_all(starter)
        return (
            await wanted_routes.wanted(starter),
            await wanted_routes.wanted(_request(3, 'user')),
            await wanted_routes.wanted(_admin()),
        )

    mine, other, admin = asyncio.run(go())
    assert mine['job']['kind'] == 'check'
    assert other['job'] is None
    assert admin['job']['kind'] == 'check'
    with pytest.raises(api.HTTPException) as err:
        asyncio.run(wanted_routes.stop(_request(3, 'user')))
    assert err.value.detail == {'code': 'no_job'}


def test_a_user_job_covers_only_their_artists(db, monkeypatch):
    _library(monkeypatch)
    _unchecked(db, 'Mine', user_id=2)
    _unchecked(db, 'Theirs', user_id=3)
    calls: list[str] = []

    def fake(watch, db_, *, progress=None, stop=None):
        calls.append(watch.name)
        return {'checked': 1, 'failed': 0, 'total': 1}

    monkeypatch.setattr(wanted_routes, 'take_inventory', fake)
    spawned = _Spawned(monkeypatch)

    _run(spawned, wanted_routes.check_all, _request(2, 'user'))

    assert calls == ['Mine']


def test_library_only_blocks_the_jobs(db, monkeypatch):
    _library(monkeypatch)
    _unchecked(db, 'Ace')
    monkeypatch.setattr(api.state, 'settings', {'library_only': True})

    with pytest.raises(api.HTTPException) as err:
        asyncio.run(wanted_routes.check_all(_admin()))
    assert err.value.status_code == 409
    assert wanted_routes._job == {}
