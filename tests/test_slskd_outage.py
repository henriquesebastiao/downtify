"""slskd cut off from Soulseek: say so, and pause the queue after a run of
songs it couldn't search for (downtify/slskd_outage.py)."""

from __future__ import annotations

import asyncio

import pytest

from downtify import api, notifications, slskd_outage, slskd_provider
from downtify.download_log import OUTCOME_COMPLETED
from downtify.download_queue import queue_pause
from downtify.slskd_outage import OutageWatch

SONG = {'name': 'Light', 'artists': ['Tom Jung'], 'duration': 200}


# -- the watch ----------------------------------------------------------


def test_trips_once_at_the_threshold():
    watch = OutageWatch()
    assert [watch.note('offline', 3) for _ in range(5)] == [
        False,
        False,
        True,
        False,
        False,
    ]
    assert watch.streak == 5


def test_a_real_search_starts_the_count_over():
    watch = OutageWatch()
    watch.note('search_failed', 3)
    watch.note('search_failed', 3)
    # slskd searched and found nothing: it is working.
    assert watch.note('no_match', 3) is False
    assert watch.streak == 0
    assert watch.note('unreachable', 3) is False
    assert watch.note('unreachable', 3) is False
    assert watch.note('unreachable', 3) is True


def test_reset_lets_a_later_outage_trip_again():
    watch = OutageWatch()
    assert watch.note('offline', 1) is True
    assert watch.note('offline', 1) is False
    watch.reset()
    assert watch.note('offline', 1) is True


def test_zero_never_pauses():
    watch = OutageWatch()
    assert not any(watch.note('offline', 0) for _ in range(100))


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        (None, 25),
        ('', 25),
        (0, 0),
        ('0', 0),
        ('40', 40),
        (-3, 0),
        (5000, 1000),
        ('x', 25),
    ],
)
def test_pause_after_setting(raw, expected):
    settings = {} if raw is None else {'outage_pause_after': raw}
    assert slskd_outage.pause_after(settings) == expected


def test_settings_keep_zero():
    def saved(value):
        settings = {'slskd': {'outage_pause_after': value}}
        return api._effective_slskd_settings(settings)['outage_pause_after']

    assert saved(0) == 0
    assert saved(None) == 25


# -- the provider -------------------------------------------------------


class _Offline:
    base_url = 'https://slskd.example'
    searched = False

    @staticmethod
    def configured() -> bool:
        return True

    @staticmethod
    def can_connect() -> bool:
        return True

    @staticmethod
    def server_state():
        # What slskd 0.26 reports once it lost the Soulseek server.
        return {
            'state': 'Disconnected',
            'isConnected': False,
            'isLoggedIn': False,
        }

    def start_search(self, query):  # pragma: no cover - must not run
        self.searched = True


def test_offline_slskd_is_a_miss_without_searching(monkeypatch):
    fake = _Offline()
    monkeypatch.setattr(slskd_provider, 'SlskdClient', lambda s: fake)
    found = slskd_provider.download_from_slskd(
        dict(SONG), {'enabled': True, 'base_url': fake.base_url}
    )
    assert found is None
    assert fake.searched is False
    assert slskd_provider.take_miss() == {
        'reason': 'offline',
        'detail': 'Disconnected',
    }


class _Response:
    def __init__(self, payload):
        self.content = b'x'
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_client_reads_the_login_state(monkeypatch):
    client = slskd_provider.SlskdClient({
        'base_url': 'http://s',
        'api_key': 'k',
    })
    payload = {'server': {'state': 'Connected, LoggedIn', 'isLoggedIn': True}}
    monkeypatch.setattr(
        client.session, 'request', lambda *a, **k: _Response(payload)
    )
    assert client.logged_in() is True
    payload['server'] = {'state': 'Disconnected', 'isLoggedIn': False}
    assert client.logged_in() is False
    payload.pop('server')
    assert client.logged_in() is None


# -- the API: pause, notify, resume ------------------------------------


@pytest.fixture
def outage(monkeypatch):
    watch = OutageWatch()
    monkeypatch.setattr(slskd_outage, 'watch', watch)
    monkeypatch.setattr(slskd_outage, 'CHECK_SECONDS', 0)
    monkeypatch.setattr(
        api.state,
        'settings',
        {
            **api.state.settings,
            'slskd': {'enabled': True, 'outage_pause_after': 3},
        },
    )
    monkeypatch.setattr(api.state, 'pending_downloads', None)
    sent = []
    monkeypatch.setattr(notifications, 'emit', lambda *args: sent.append(args))
    queue_pause.resume()
    yield watch, sent
    queue_pause.resume()


def _miss(reason):
    return {
        **SONG,
        'download_provider': 'youtube-music',
        'slskd_miss': {'reason': reason, 'detail': ''},
    }


def test_pauses_after_a_run_and_resumes_when_slskd_is_back(
    outage, monkeypatch
):
    watch, sent = outage
    back = iter([False, True])
    monkeypatch.setattr(api, '_slskd_is_back', lambda s: next(back))

    async def run():
        api.state.loop = asyncio.get_running_loop()
        for _ in range(3):
            await asyncio.to_thread(
                api._note_slskd_outage, _miss('offline'), OUTCOME_COMPLETED
            )
        for _ in range(50):
            await asyncio.sleep(0)
            if queue_pause.paused:
                break
        assert queue_pause.paused
        assert watch.paused_by_outage
        for _ in range(200):
            await asyncio.sleep(0)
            if not queue_pause.paused:
                break

    asyncio.run(run())
    assert not queue_pause.paused
    assert [s[:2] for s in sent] == [
        ('slskd_outage', 'downloads paused'),
        ('slskd_outage', 'downloads resumed'),
    ]
    assert '3 songs in a row' in sent[0][2]


def test_a_slskd_download_resets_the_run(outage):
    watch, _sent = outage
    api._note_slskd_outage(_miss('offline'), OUTCOME_COMPLETED)
    api._note_slskd_outage(_miss('offline'), OUTCOME_COMPLETED)
    api._note_slskd_outage(
        {**SONG, 'download_provider': 'slskd'}, OUTCOME_COMPLETED
    )
    assert watch.streak == 0


def test_resuming_by_hand_ends_the_watch(outage):
    watch, _sent = outage
    watch.paused_by_outage = True
    asyncio.run(api.resume_queue())
    assert watch.paused_by_outage is False


# -- notifications ------------------------------------------------------


def test_new_event_reaches_channels_saved_before_it():
    saved = {'channels': {'discord': {'events': ['download_failed']}}}
    events = notifications.effective(saved)['channels']['discord']['events']
    assert events == [
        'download_failed',
        'slskd_outage',
        'ytdlp',
        'youtube_cookies',
        'watch_failing',
    ]


def test_an_unticked_event_stays_off():
    saved = {
        'channels': {
            'discord': {
                'events': ['download_failed'],
                'known_events': list(notifications.EVENTS),
            }
        }
    }
    events = notifications.effective(saved)['channels']['discord']['events']
    assert events == ['download_failed']
