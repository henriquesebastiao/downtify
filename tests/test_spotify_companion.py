"""The Spotify companion (downtify/spotify_companion.py and its routes)."""

from __future__ import annotations

import asyncio
import io
import json
import random
import re
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from downtify import (
    api,
    monitor,
    notifications,
    spotify,
    spotify_companion,
    spotify_companion_routes,
)
from downtify.auth import ADMIN, CLIENT, classify
from downtify.spotify_companion import (
    AWAY,
    OTHER_ACCOUNT,
    READY,
    SIGNED_OUT,
    CompanionWaiting,
    Store,
    UnknownJob,
    Watch,
)

UTC = timezone.utc
SAD = '37i9dQZF1EVKuMoAJjoTIw'
DAILY = '37i9dQZF1E37jO8SiMT0yy'
WEEKLY_ID = '37i9dQZEVXcJZyENOWUFo7'
MINE = {'id': 'me123', 'name': 'Shivpatel'}
# A Wednesday, inside the default evening slot (18:00-23:00 UTC here).
EVENING = datetime(2026, 11, 25, 19, 0, tzinfo=UTC)


def _store(tmp_path, **config):
    store = Store(tmp_path / 'companion', tz=UTC, rng=random.Random(1))
    store.set_config({'enabled': True, **config})
    return store


def _watch(watch_id, playlist_id=SAD, name='Sad Mix', last=None, minutes=1440):
    return Watch(
        id=watch_id,
        playlist_id=playlist_id,
        name=name,
        interval_minutes=minutes,
        last_checked=last.isoformat() if last else None,
    )


def _ready(store, now, account=MINE):
    return store.report(now, {'status': READY, 'account': account})


def _first_job(store, now, watches):
    """Ask until a job comes, moving the clock by each wait."""

    for _ in range(50):
        answer = store.plan(now, watches)
        if 'job' in answer:
            return now, answer['job']
        now += timedelta(seconds=answer['wait_seconds'])
        _ready(store, now)
    raise AssertionError('no job came')


TRACK_ITEM = {
    'itemV2': {
        '__typename': 'TrackResponseWrapper',
        'data': {
            'uri': 'spotify:track:4uLU6hMCjMI75M1A2tKUQC',
            'name': 'making the bed',
            'artists': {'items': [{'profile': {'name': 'Olivia Rodrigo'}}]},
            'albumOfTrack': {
                'name': 'GUTS',
                'date': {'isoString': '2023-09-08T00:00:00Z'},
            },
            'trackDuration': {'totalMilliseconds': 198000},
        },
    }
}


# ── Mixes ───────────────────────────────────────────────────────────


def test_personal_mixes_are_recognised_by_their_id():
    assert spotify_companion.is_personal_mix(SAD)
    assert spotify_companion.is_personal_mix(WEEKLY_ID)
    # Editorial and "This Is" playlists are the same for everyone.
    assert not spotify_companion.is_personal_mix('37i9dQZF1DXcBWIGoYBM5M')
    assert not spotify_companion.is_personal_mix('37i9dQZF1DZ06evO2YqUuI')
    assert not spotify_companion.is_personal_mix('')


def test_kinds():
    kind = spotify_companion.kind_of
    assert kind(DAILY, 'Daily Mix 3') == 'daily'
    assert kind(WEEKLY_ID, 'Discover Weekly') == 'weekly'
    assert kind(SAD, 'Release Radar') == 'weekly'
    assert kind(SAD, 'Sad Mix') == 'mixes'


def test_bad_slots_are_dropped_and_values_clamped():
    config = spotify_companion.effective({
        'enabled': True,
        'slots': [
            {
                'name': 'ok',
                'days': [0, 9],
                'start': '7:30',
                'end': '08:00',
                'seats': 9999,
                'kinds': ['daily', 'x'],
            },
            {
                'name': 'no days',
                'days': [],
                'start': '01:00',
                'end': '02:00',
                'kinds': ['daily'],
            },
            {
                'name': 'empty',
                'days': [1],
                'start': '01:00',
                'end': '01:00',
                'kinds': ['daily'],
            },
            'junk',
        ],
        'min_gap_seconds': 1,
    })
    assert len(config['slots']) == 1
    slot = config['slots'][0]
    assert slot['days'] == [0]
    assert slot['start'] == '07:30'
    assert slot['seats'] == spotify_companion.MAX_SEATS
    assert slot['kinds'] == ['daily']
    assert config['min_gap_seconds'] == 20


def test_off_by_default(tmp_path):
    store = Store(tmp_path)
    assert store.enabled is False
    assert store.plan(EVENING, [_watch(1)])['reason'] == 'off'


# ── Holding the mixes ───────────────────────────────────────────────


def test_nothing_is_read_until_the_companion_is_signed_in(tmp_path):
    store = _store(tmp_path)
    assert store.plan(EVENING, [_watch(1)])['reason'] == 'never_connected'
    store.report(EVENING, {'status': SIGNED_OUT})
    assert store.plan(EVENING, [_watch(1)])['reason'] == SIGNED_OUT
    # "ready" without an account is a signed-out web player.
    store.report(EVENING, {'status': READY})
    assert store.health(EVENING)['status'] == SIGNED_OUT


def test_another_account_puts_everything_on_hold(tmp_path):
    store = _store(tmp_path)
    _ready(store, EVENING)
    notices = _ready(store, EVENING, {'id': 'aidon', 'name': 'Aidon'})
    assert store.plan(EVENING, [_watch(1)])['reason'] == OTHER_ACCOUNT
    assert len(notices) == 1
    assert 'Aidon' in notices[0][1]
    assert 'Shivpatel' in notices[0][1]

    store.accept_account()
    assert store.health(EVENING)['status'] == READY
    assert [title for title, _ in store.tick(EVENING)] == ['back']
    assert store.state['account']['name'] == 'Aidon'


def test_signed_out_and_back_notify_once_each(tmp_path):
    store = _store(tmp_path)
    assert _ready(store, EVENING) == []
    notices = store.report(EVENING, {'status': SIGNED_OUT})
    assert [title for title, _ in notices] == ['signed out of Spotify']
    assert store.report(EVENING, {'status': SIGNED_OUT}) == []
    back = _ready(store, EVENING + timedelta(minutes=1))
    assert [title for title, _ in back] == ['back']


def test_going_quiet_waits_then_tells_you(tmp_path):
    store = _store(tmp_path, away_alert_hours=2)
    _ready(store, EVENING)
    later = EVENING + timedelta(minutes=10)
    assert store.health(later)['status'] == AWAY
    assert store.tick(later) == []  # not yet worth a message
    notices = store.tick(EVENING + timedelta(hours=2, minutes=1))
    assert [title for title, _ in notices] == ['not heard from']
    assert store.tick(EVENING + timedelta(hours=3)) == []


def test_turning_it_off_says_nothing(tmp_path):
    store = _store(tmp_path)
    store.report(EVENING, {'status': SIGNED_OUT})
    store.set_config({'enabled': False})
    assert store.tick(EVENING) == []


# ── Slots, seats and spacing ────────────────────────────────────────


def test_reads_wait_for_a_slot(tmp_path):
    store = _store(tmp_path)
    morning_early = datetime(2026, 11, 25, 6, 0, tzinfo=UTC)
    _ready(store, morning_early)
    answer = store.plan(morning_early, [_watch(1)])
    assert answer['reason'] == 'between_slots'
    # Three hours to the morning slot, asked again within the hour.
    assert answer['wait_seconds'] == 3600


def test_a_slot_can_run_past_midnight(tmp_path):
    store = _store(
        tmp_path,
        slots=[
            {
                'name': 'Night',
                'days': [2],
                'start': '23:00',
                'end': '02:00',
                'seats': 5,
                'kinds': ['mixes'],
            }
        ],
    )
    # Thursday 01:00 is still Wednesday's night slot.
    late = datetime(2026, 11, 26, 1, 0, tzinfo=UTC)
    windows = spotify_companion.open_windows(store.config['slots'], late)
    assert [w[3] for w in windows] == ['slot1@2026-11-25']


def test_the_first_read_starts_a_little_after_the_slot_opens(tmp_path):
    store = _store(tmp_path)
    opening = datetime(2026, 11, 25, 18, 0, tzinfo=UTC)
    _ready(store, opening)
    answer = store.plan(opening, [_watch(1)])
    assert answer.get('reason') == 'slot_opening'
    assert answer['wait_seconds'] > 0


def test_one_read_at_a_time_then_a_spread_gap(tmp_path):
    store = _store(tmp_path, min_gap_seconds=60)
    watches = [
        _watch(i, f'{spotify_companion.MIX_PREFIX}{i:012d}', f'Mix {i}')
        for i in range(1, 6)
    ]
    _ready(store, EVENING)
    now, job = _first_job(store, EVENING, watches)
    assert store.plan(now, watches)['reason'] == 'busy'

    store.finish(now, job['id'], tracks=[], name='Mix')
    answer = store.plan(now, watches)
    assert answer['reason'] == 'gap'
    # About (time left in the slot) / (reads left), with jitter: 4 mixes
    # over ~4 hours is close to an hour apart, capped at 30 minutes.
    assert 60 <= answer['wait_seconds'] <= spotify_companion.MAX_GAP_SECONDS


def test_seats_limit_reads_per_slot(tmp_path):
    store = _store(
        tmp_path,
        min_gap_seconds=20,
        slots=[
            {
                'name': 'Short',
                'days': list(range(7)),
                'start': '18:00',
                'end': '23:00',
                'seats': 2,
                'kinds': ['mixes'],
            }
        ],
    )
    watches = [
        _watch(i, f'{spotify_companion.MIX_PREFIX}{i:012d}', f'Mix {i}')
        for i in range(1, 6)
    ]
    now = EVENING
    _ready(store, now)
    read = []
    for _ in range(2):
        now, job = _first_job(store, now, watches)
        store.finish(now, job['id'], tracks=[], name=job['name'])
        read.append(job['watch_id'])
    assert len(set(read)) == 2
    now += timedelta(hours=1)
    _ready(store, now)
    assert store.plan(now, watches)['reason'] == 'nothing_due'


def test_a_slot_takes_only_its_kinds(tmp_path):
    store = _store(
        tmp_path,
        slots=[
            {
                'name': 'Dailies',
                'days': list(range(7)),
                'start': '18:00',
                'end': '23:00',
                'seats': 9,
                'kinds': ['daily'],
            }
        ],
    )
    _ready(store, EVENING)
    watches = [_watch(1, SAD, 'Sad Mix'), _watch(2, DAILY, 'Daily Mix 1')]
    _now, job = _first_job(store, EVENING, watches)
    assert job['watch_id'] == 2


def test_most_overdue_first_and_recent_reads_wait(tmp_path):
    store = _store(tmp_path)
    _ready(store, EVENING)
    watches = [
        _watch(1, SAD, 'Sad Mix', last=EVENING - timedelta(days=2)),
        _watch(2, DAILY, 'Daily Mix 1', last=EVENING - timedelta(days=5)),
        _watch(
            3,
            f'{spotify_companion.MIX_PREFIX}abc',
            'Chill Mix',
            last=EVENING - timedelta(hours=2),
        ),
    ]
    _now, job = _first_job(store, EVENING, watches)
    assert job['watch_id'] == 2


def test_weekly_playlists_wait_for_spotifys_refresh(tmp_path):
    # Read Monday afternoon: Discover Weekly is due again next Monday.
    monday = datetime(2026, 11, 23, 15, 0, tzinfo=UTC)
    watch = _watch(1, WEEKLY_ID, 'Discover Weekly', last=monday, minutes=60)
    due = spotify_companion.due_at(watch, monday, UTC)
    assert due == datetime(2026, 11, 30, 6, 0, tzinfo=UTC)
    # Release Radar read Thursday: due Friday morning.
    thursday = datetime(2026, 11, 26, 20, 0, tzinfo=UTC)
    radar = _watch(2, WEEKLY_ID, 'Release Radar', last=thursday)
    assert spotify_companion.due_at(radar, thursday, UTC) == datetime(
        2026, 11, 27, 6, 0, tzinfo=UTC
    )


def test_check_now_jumps_the_queue_even_between_slots(tmp_path):
    store = _store(tmp_path)
    noon = datetime(2026, 11, 25, 14, 0, tzinfo=UTC)
    _ready(store, noon)
    watches = [_watch(1, last=noon - timedelta(hours=1))]
    store.request(1)
    answer = store.plan(noon, watches)
    assert answer['job']['watch_id'] == 1
    store.finish(noon, answer['job']['id'], tracks=[], name='Sad Mix')
    # Still a gap after it.
    store.request(1)
    assert store.plan(noon, watches)['reason'] == 'gap'


def test_slow_down_pauses_reads_for_an_hour(tmp_path):
    store = _store(tmp_path)
    _ready(store, EVENING)
    now, job = _first_job(
        store, EVENING, [_watch(1), _watch(2, DAILY, 'Daily Mix 1')]
    )
    store.finish(now, job['id'], error='rate_limited')
    _ready(store, now + timedelta(minutes=30))
    answer = store.plan(
        now + timedelta(minutes=30), [_watch(2, DAILY, 'Daily Mix 1')]
    )
    assert answer['reason'] == 'gap'
    assert answer['wait_seconds'] >= 29 * 60


def test_an_unanswered_read_is_given_up(tmp_path):
    store = _store(tmp_path)
    _ready(store, EVENING)
    now, job = _first_job(store, EVENING, [_watch(1)])
    later = now + spotify_companion.JOB_TIMEOUT + timedelta(minutes=1)
    _ready(store, later)
    store.tick(later)
    assert store.state['in_flight'] is None
    assert store.state['errors']['1']['error']
    with pytest.raises(UnknownJob):
        store.finish(later, job['id'], tracks=[])


# ── Songs ───────────────────────────────────────────────────────────


def test_a_read_is_kept_and_survives_a_restart(tmp_path):
    store = _store(tmp_path)
    _ready(store, EVENING)
    now, job = _first_job(store, EVENING, [_watch(1)])
    song = {'song_id': 'x', 'name': 'making the bed'}
    store.finish(now, job['id'], tracks=[song], name='Sad Mix')

    again = Store(tmp_path / 'companion', tz=UTC)
    assert again.snapshot(SAD) == ('Sad Mix', [song])
    assert again.enabled is True
    assert again.state['account'] == MINE


def test_spotify_reads_your_version_never_the_signed_out_one(
    tmp_path, monkeypatch
):
    def signed_out(*args):
        raise AssertionError('read Spotify signed out')

    monkeypatch.setattr(spotify, '_fetch_embed_json', signed_out)
    store = _store(tmp_path)
    monkeypatch.setattr(spotify_companion, '_current', store)

    with pytest.raises(CompanionWaiting):
        spotify.playlist_tracks_from_id(SAD)
    _ready(store, EVENING)
    now, job = _first_job(store, EVENING, [_watch(1)])
    store.finish(now, job['id'], tracks=[{'song_id': 'x'}], name='Sad Mix')
    assert spotify.playlist_tracks_from_id(SAD) == [{'song_id': 'x'}]
    assert spotify.playlist_info_and_tracks(SAD) == (
        'Sad Mix',
        [{'song_id': 'x'}],
    )

    # Other playlists, and everything with the companion off, read as before.
    calls = []
    monkeypatch.setattr(
        spotify, '_fetch_embed_json', lambda kind, pid: calls.append(pid) or {}
    )
    monkeypatch.setattr(spotify, '_entity_from', lambda payload: {})
    spotify.playlist_tracks_from_id('37i9dQZF1DXcBWIGoYBM5M')
    store.set_config({'enabled': False})
    spotify.playlist_tracks_from_id(SAD)
    assert calls == ['37i9dQZF1DXcBWIGoYBM5M', SAD]


def test_graphql_items_become_songs():
    songs = spotify.tracks_from_graphql_items([
        TRACK_ITEM,
        {'itemV2': {}},
        'junk',
    ])
    assert [s['name'] for s in songs] == ['making the bed']
    assert songs[0]['artist'] == 'Olivia Rodrigo'
    assert spotify.tracks_from_graphql_items(None) == []


def test_a_new_watch_asks_the_companion_for_a_read(tmp_path, monkeypatch):
    store = _store(tmp_path)
    monkeypatch.setattr(spotify_companion, '_current', store)
    playlist = monitor.MonitoredPlaylist(
        id=9,
        spotify_id=SAD,
        name='Sad Mix',
        url=f'https://open.spotify.com/playlist/{SAD}',
        interval_minutes=1440,
        enabled=True,
        last_checked=None,
        last_track_count=0,
        created_at='',
    )

    class DB:
        @staticmethod
        def update_playlist(*args, **kwargs):
            raise AssertionError('marked as checked')

    count = asyncio.run(
        monitor.check_playlist(playlist, DB(), None, print, None)
    )
    assert count == 0
    assert store.state['requests'] == [9]


def test_adding_a_mix_reads_only_its_public_name(tmp_path, monkeypatch):
    store = _store(tmp_path)
    monkeypatch.setattr(spotify_companion, '_current', store)
    monkeypatch.setattr(
        spotify, '_fetch_embed_json', lambda kind, pid: {'name': 'Sad Mix'}
    )
    monkeypatch.setattr(spotify, '_entity_from', lambda payload: payload)
    kind, key, name = asyncio.run(
        api._resolve_watch_target(f'https://open.spotify.com/playlist/{SAD}')
    )
    assert (kind, key, name) == ('playlist', SAD, 'Sad Mix')


def test_the_monitor_leaves_companion_mixes_alone(tmp_path, monkeypatch):
    def playlist(spotify_id):
        return monitor.MonitoredPlaylist(
            id=1,
            spotify_id=spotify_id,
            name='x',
            url=f'https://open.spotify.com/playlist/{spotify_id}',
            interval_minutes=60,
            enabled=True,
            last_checked=None,
            last_track_count=0,
            created_at='',
        )

    store = _store(tmp_path)
    monkeypatch.setattr(spotify_companion, '_current', store)
    assert monitor.companion_reads(playlist(SAD))
    assert not monitor.companion_reads(playlist('37i9dQZF1DXcBWIGoYBM5M'))
    store.set_config({'enabled': False})
    assert not monitor.companion_reads(playlist(SAD))


def test_the_event_can_be_chosen_and_is_on_by_default():
    assert 'spotify_companion' in notifications.EVENTS
    channel = notifications.effective({})['channels']['ntfy']
    assert 'spotify_companion' in channel['events']
    message = notifications.batch_message(
        'spotify_companion', [('signed out of Spotify', 'Sign in again')]
    )
    assert message.title == 'Spotify companion: signed out of Spotify'
    assert message.level == 'warning'


# ── Routes ──────────────────────────────────────────────────────────


def test_route_rules():
    assert classify('POST', '/api/companion/poll') == CLIENT
    assert classify('POST', '/api/companion/result') == CLIENT
    assert classify('GET', '/api/companion/watches') == CLIENT
    assert classify('GET', '/api/companion') == ADMIN
    assert classify('PUT', '/api/companion') == ADMIN
    assert classify('POST', '/api/companion/extension') == ADMIN
    assert classify('POST', '/api/companion/account') == ADMIN


class FakeDB:
    def __init__(self, playlists):
        self.playlists = {p.id: p for p in playlists}

    def list_playlists(self):
        return list(self.playlists.values())

    def get_playlist(self, playlist_id):
        return self.playlists.get(playlist_id)


@pytest.fixture
def routes(tmp_path, monkeypatch):
    sad = monitor.MonitoredPlaylist(
        id=4,
        spotify_id=SAD,
        name='Sad Mix',
        url=f'https://open.spotify.com/playlist/{SAD}',
        interval_minutes=1440,
        enabled=True,
        last_checked=None,
        last_track_count=0,
        created_at='',
    )
    other = monitor.MonitoredPlaylist(
        id=5,
        spotify_id='37i9dQZF1DXcBWIGoYBM5M',
        name='Editorial',
        url='https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M',
        interval_minutes=60,
        enabled=True,
        last_checked=None,
        last_track_count=0,
        created_at='',
    )
    store = _store(tmp_path)
    store.request(4)  # so the first poll gets a job at any hour
    monkeypatch.setattr(spotify_companion, '_current', store)
    monkeypatch.setattr(api.state, 'monitor_db', FakeDB([sad, other]))
    checks = []
    monkeypatch.setattr(
        spotify_companion_routes, '_start_check', lambda p: checks.append(p.id)
    )
    sent = []
    monkeypatch.setattr(notifications, 'emit', lambda *args: sent.append(args))
    app = FastAPI()
    app.include_router(spotify_companion_routes.router)
    with TestClient(app) as client:
        client.store = store
        client.checks = checks
        client.sent = sent
        yield client


def test_poll_read_and_check(routes):
    answer = routes.post(
        '/api/companion/poll',
        json={'status': READY, 'account': MINE, 'version': '1.0.0'},
    ).json()
    job = answer['job']
    assert job['playlist_id'] == SAD
    assert job['hash'] == spotify._GRAPHQL_HASH

    done = routes.post(
        '/api/companion/result',
        json={'job_id': job['id'], 'name': 'Sad Mix', 'items': [TRACK_ITEM]},
    ).json()
    assert done == {'ok': True, 'songs': 1}
    assert routes.checks == [4]
    name, tracks = routes.store.snapshot(SAD)
    assert tracks[0]['name'] == 'making the bed'

    # The same job twice is refused.
    again = routes.post(
        '/api/companion/result', json={'job_id': job['id'], 'items': []}
    )
    assert again.status_code == 409

    status = routes.get('/api/companion').json()
    assert status['health']['account'] == MINE
    assert status['mixes'] == 1
    assert status['watches']['4']['name'] == 'Sad Mix'
    badges = routes.get('/api/companion/watches').json()
    assert list(badges['watches']) == ['4']


def test_an_empty_answer_is_a_failed_read(routes):
    job = routes.post(
        '/api/companion/poll', json={'status': READY, 'account': MINE}
    ).json()['job']
    done = routes.post(
        '/api/companion/result', json={'job_id': job['id'], 'items': []}
    ).json()
    assert done['ok'] is False
    assert routes.checks == []
    assert routes.store.snapshot(SAD) is None


def test_a_signed_out_read_holds_and_notifies(routes):
    job = routes.post(
        '/api/companion/poll', json={'status': READY, 'account': MINE}
    ).json()['job']
    done = routes.post(
        '/api/companion/result',
        json={'job_id': job['id'], 'error': 'signed_out'},
    ).json()
    assert done['ok'] is False
    assert routes.checks == []
    assert routes.sent[-1][0] == 'spotify_companion'
    assert routes.store.health(datetime.now(UTC))['status'] == SIGNED_OUT


def test_settings_round_trip(routes):
    body = routes.put(
        '/api/companion', json={'min_gap_seconds': 90, 'slots': []}
    ).json()
    assert body['config']['min_gap_seconds'] == 90
    assert body['config']['slots'] == []


def test_the_extension_download_carries_the_key(routes, monkeypatch):
    async def new_device(info, user, ip, extra):
        assert info['platform'] == 'spotify-companion'
        return {'token': 'dtfy_1_secret', 'device': {'id': 1}}

    class Users:
        @staticmethod
        def get(user_id):
            return {'id': user_id}

    class Auth:
        users = Users()

    monkeypatch.setattr(spotify_companion_routes.auth_routes, '_store', Auth)
    monkeypatch.setattr(
        spotify_companion_routes.auth_routes,
        '_me',
        lambda request: type('Me', (), {'user_id': 1})(),
    )
    monkeypatch.setattr(
        spotify_companion_routes.auth_routes, '_new_device', new_device
    )
    monkeypatch.setattr(
        spotify_companion_routes.auth_routes, '_ip', lambda r: ''
    )

    response = routes.post('/api/companion/extension')
    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = archive.namelist()
    assert 'manifest.json' in names
    config = json.loads(archive.read('config.json'))
    assert config == {
        'downtify_url': 'http://testserver',
        'key': 'dtfy_1_secret',
    }


def test_check_now_queues_a_companion_read(tmp_path, monkeypatch):
    store = _store(tmp_path)
    monkeypatch.setattr(spotify_companion, '_current', store)
    playlist = monitor.MonitoredPlaylist(
        id=4,
        spotify_id=SAD,
        name='Sad Mix',
        url=f'https://open.spotify.com/playlist/{SAD}',
        interval_minutes=1440,
        enabled=True,
        last_checked=None,
        last_track_count=0,
        created_at='',
    )
    monkeypatch.setattr(api, '_require_monitor_db', object)
    monkeypatch.setattr(
        api, '_monitor_watch_for_request', lambda pid, request: playlist
    )
    monkeypatch.setattr(api.state, 'downloader', object())
    answer = asyncio.run(api.manual_check_playlist(4, None))
    assert answer == {'status': 'companion_queued', 'id': 4}
    assert store.state['requests'] == [4]


# ── Setting up with an AI agent ─────────────────────────────────────


def _fake_accounts(monkeypatch):
    made = []

    async def new_device(info, user, ip, extra):
        made.append(info['device_name'])
        return {'token': f'dtfy_9_secret{len(made)}', 'device': {'id': 9}}

    class Users:
        @staticmethod
        def get(user_id):
            return {'id': user_id}

    class Auth:
        users = Users()

    routes_auth = spotify_companion_routes.auth_routes
    monkeypatch.setattr(routes_auth, '_store', Auth)
    monkeypatch.setattr(
        routes_auth, '_me', lambda request: type('Me', (), {'user_id': 1})()
    )
    monkeypatch.setattr(routes_auth, '_new_device', new_device)
    monkeypatch.setattr(routes_auth, '_ip', lambda r: '')
    return made


def test_agent_setup_link_route_rules():
    token = 'A' * 32
    assert classify('POST', '/api/companion/agent') == ADMIN
    assert classify('GET', f'/api/companion/agent/{token}/extension.zip') == (
        'public'
    )
    assert classify('GET', f'/api/companion/agent/{token}/status') == 'public'
    # Anything else under it stays an admin's.
    assert classify('GET', '/api/companion/agent/short/status') == ADMIN
    assert classify('DELETE', f'/api/companion/agent/{token}/status') == ADMIN


def test_an_agent_can_fetch_set_up_and_check(routes, monkeypatch):
    made = _fake_accounts(monkeypatch)
    answer = routes.post('/api/companion/agent', json={}).json()
    text = answer['instructions']
    assert 'Never type, ask for, store or copy my Spotify password' in text
    links = re.findall(
        r'http://testserver/api/companion/agent/[^"?\s`]+', text
    )
    zip_url = next(u for u in links if u.endswith('extension.zip'))
    status_url = next(u for u in links if u.endswith('/status'))

    first = zipfile.ZipFile(io.BytesIO(routes.get(zip_url).content))
    config = json.loads(first.read('config.json'))
    assert config['downtify_url'] == 'http://testserver'
    manifest = json.loads(first.read('manifest.json'))
    # Allowed to reach Downtify with nobody clicking Save.
    assert 'http://testserver/*' in manifest['host_permissions']

    # Another address (from inside a container); the same key.
    second = zipfile.ZipFile(
        io.BytesIO(
            routes.get(
                zip_url, params={'address': 'http://192.168.1.20:8000/x'}
            ).content
        )
    )
    again = json.loads(second.read('config.json'))
    assert again == {
        'downtify_url': 'http://192.168.1.20:8000',
        'key': config['key'],
    }
    assert (
        'http://192.168.1.20:8000/*'
        in json.loads(second.read('manifest.json'))['host_permissions']
    )
    assert made == ['Spotify companion (AI setup)']

    status = routes.get(status_url).json()
    assert status['status'] == 'never_connected'
    assert set(status) == {
        'status',
        'message',
        'last_check_in',
        'extension_version',
        'personal_mixes',
        'read_today',
    }
    routes.post('/api/companion/poll', json={'status': READY, 'account': MINE})
    status = routes.get(status_url).json()
    assert status['status'] == READY
    assert 'Shivpatel' not in json.dumps(status)


def test_an_old_setup_link_stops_working(routes, monkeypatch):
    _fake_accounts(monkeypatch)
    text = routes.post('/api/companion/agent', json={}).json()['instructions']
    status_url = re.search(
        r'http://testserver/api/companion/agent/\S+/status', text
    ).group(0)
    later = datetime.now(UTC) + timedelta(hours=25)
    monkeypatch.setattr(spotify_companion_routes, '_now', lambda: later)
    response = routes.get(status_url)
    assert response.status_code == 404
    assert 'expired' in response.json()['detail']


def test_the_download_for_people_also_needs_no_save(routes, monkeypatch):
    _fake_accounts(monkeypatch)
    archive = zipfile.ZipFile(
        io.BytesIO(routes.post('/api/companion/extension').content)
    )
    manifest = json.loads(archive.read('manifest.json'))
    assert 'http://testserver/*' in manifest['host_permissions']
