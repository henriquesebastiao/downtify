"""Pausing downloads before the disk is full (downtify/disk_guard.py)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from downtify import api, disk_guard, notifications, slskd_outage
from downtify.disk_guard import GB, DiskGuard, Low

LIMIT = 5


def _low(gb: float) -> Low:
    return Low('/downloads', int(gb * GB))


def test_min_free_gb():
    assert disk_guard.min_free_gb({}) == disk_guard.DEFAULT_MIN_FREE_GB
    assert disk_guard.min_free_gb({'min_free_space_gb': ''}) == 5
    assert disk_guard.min_free_gb({'min_free_space_gb': 0}) == 0
    assert disk_guard.min_free_gb({'min_free_space_gb': '12'}) == 12
    assert disk_guard.min_free_gb({'min_free_space_gb': -3}) == 0
    assert disk_guard.min_free_gb({'min_free_space_gb': 'x'}) == 5
    assert disk_guard.min_free_gb({'min_free_space_gb': 10**9}) == 10_000


def test_lowest_picks_the_fullest_and_skips_unreadable():
    free = {'/a': 10 * GB, '/b': 2 * GB, '/c': None}
    worst = disk_guard.lowest(
        [Path('/a'), Path('/b'), Path('/c')],
        free=lambda p: free[p.as_posix()],
    )
    assert worst.path.replace('\\', '/') == '/b'
    assert worst.free == 2 * GB
    assert disk_guard.lowest([Path('/c')], free=lambda _p: None) is None


def test_pause_then_resume_with_a_margin():
    g = DiskGuard()
    assert not g.decide(_low(10), LIMIT, queue_paused=False)
    assert g.decide(_low(4), LIMIT, queue_paused=False) == 'pause'
    assert not g.decide(_low(3), LIMIT, queue_paused=True)
    # Just above the limit is not enough to resume.
    assert not g.decide(_low(5.5), LIMIT, queue_paused=True)
    assert g.decide(_low(6.5), LIMIT, queue_paused=True) == 'resume'
    assert not g.decide(_low(6.5), LIMIT, queue_paused=False)


def test_off_never_pauses_and_releases_its_pause():
    g = DiskGuard()
    assert not g.decide(_low(1), 0, queue_paused=False)
    g.decide(_low(1), LIMIT, queue_paused=False)
    assert g.decide(_low(1), 0, queue_paused=True) == 'resume'


def test_already_paused_only_warns_once_and_never_resumes_it():
    g = DiskGuard()
    assert g.decide(_low(1), LIMIT, queue_paused=True) == 'warn'
    assert not g.decide(_low(1), LIMIT, queue_paused=True)
    # Space comes back: the admin's pause is left alone.
    assert not g.decide(_low(20), LIMIT, queue_paused=True)


def test_someone_else_resuming_on_a_full_disk_is_paused_again():
    g = DiskGuard()
    g.decide(_low(1), LIMIT, queue_paused=False)
    assert g.decide(_low(1), LIMIT, queue_paused=False) == 'repause'


def test_an_admin_resuming_takes_over_until_space_came_back():
    g = DiskGuard()
    g.decide(_low(1), LIMIT, queue_paused=False)
    g.admin_took_over()
    assert not g.decide(_low(1), LIMIT, queue_paused=False)
    assert not g.decide(_low(20), LIMIT, queue_paused=False)
    # Back above, then low again: guarded again.
    assert g.decide(_low(1), LIMIT, queue_paused=False) == 'pause'


# -- the queue -------------------------------------------------------------


@pytest.fixture
def wired(monkeypatch):
    g = DiskGuard()
    monkeypatch.setattr(disk_guard, 'guard', g)
    calls = []
    sent = []

    async def set_paused(paused):
        calls.append(paused)
        if paused:
            api.queue_pause.pause()
        else:
            api.queue_pause.resume()
        return {}

    monkeypatch.setattr(api, '_set_queue_paused', set_paused)
    monkeypatch.setattr(
        notifications, 'emit', lambda *a: sent.append(a), raising=True
    )
    monkeypatch.setattr(api.notifications, 'emit', lambda *a: sent.append(a))
    monkeypatch.setattr(api.state, 'settings', {'min_free_space_gb': LIMIT})
    monkeypatch.setattr(api, '_disk_guard_paths', lambda: [Path('/x')])
    free = {'gb': 50.0}
    monkeypatch.setattr(
        disk_guard,
        'lowest',
        lambda _paths: Low('/downloads', int(free['gb'] * GB)),
    )
    monkeypatch.setattr(slskd_outage.watch, 'paused_by_outage', False)
    api.queue_pause.resume()
    yield free, calls, sent
    api.queue_pause.resume()


def test_tick_pauses_says_so_and_resumes(wired):
    free, calls, sent = wired

    assert not asyncio.run(api.disk_guard_tick())
    free['gb'] = 2
    assert asyncio.run(api.disk_guard_tick()) == 'pause'
    assert calls == [True]
    assert sent[-1][0:2] == ('disk_space', 'downloads paused')
    assert '/downloads' in sent[-1][2]
    free['gb'] = 40
    assert asyncio.run(api.disk_guard_tick()) == 'resume'
    assert calls == [True, False]
    assert sent[-1][1] == 'room again'
    assert 'Downloads resumed' in sent[-1][2]


def test_resume_leaves_an_slskd_pause_in_place(wired, monkeypatch):
    free, calls, sent = wired
    free['gb'] = 2
    asyncio.run(api.disk_guard_tick())
    monkeypatch.setattr(slskd_outage.watch, 'paused_by_outage', True)
    free['gb'] = 40

    assert asyncio.run(api.disk_guard_tick()) == 'resume'
    assert calls == [True]
    assert 'wait for slskd' in sent[-1][2]


def test_disk_space_event_reaches_channels_saved_before_it():
    saved = {'channels': {'discord': {'events': ['download_failed']}}}
    events = notifications.effective(saved)['channels']['discord']['events']
    assert 'disk_space' in events
