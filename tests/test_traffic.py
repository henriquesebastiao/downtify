"""Traffic counters add in memory and save in the background.

The middleware counts every response on the event loop; a database
write there stalled every request (and waited on any other writer of
the shared library database).
"""

from __future__ import annotations

import asyncio
import sqlite3

import pytest

from downtify import traffic as traffic_mod
from downtify.traffic import (
    DIRECTION_IN,
    DIRECTION_OUT,
    TrafficCounters,
    traffic_flush_loop,
)


def _saved(path) -> list[tuple[int, str, int]]:
    conn = sqlite3.connect(str(path))
    try:
        return conn.execute(
            'SELECT user_id, direction, total_bytes FROM traffic_counters '
            'ORDER BY user_id, direction'
        ).fetchall()
    finally:
        conn.close()


def test_add_does_not_touch_the_database(tmp_path, monkeypatch):
    counters = TrafficCounters(tmp_path / 'lib.db')

    def no_db():
        raise AssertionError('add() opened the database')

    monkeypatch.setattr(counters, '_connect', no_db)
    counters.add(5, DIRECTION_OUT, 1000)


def test_pending_bytes_show_in_totals_and_flush_saves_them(tmp_path):
    path = tmp_path / 'lib.db'
    counters = TrafficCounters(path)
    counters.add(5, DIRECTION_OUT, 1000)
    counters.add(5, DIRECTION_OUT, 24)
    counters.add(7, DIRECTION_IN, 10)

    assert _saved(path) == []
    assert counters.totals() == {
        5: {'in': 0, 'out': 1024},
        7: {'in': 10, 'out': 0},
    }

    counters.flush()
    assert _saved(path) == [(5, 'out', 1024), (7, 'in', 10)]

    counters.add(5, DIRECTION_OUT, 1)
    assert counters.totals()[5] == {'in': 0, 'out': 1025}
    counters.flush()
    assert _saved(path) == [(5, 'out', 1025), (7, 'in', 10)]


def test_a_failed_flush_keeps_the_bytes(tmp_path, monkeypatch):
    counters = TrafficCounters(tmp_path / 'lib.db')
    counters.add(5, DIRECTION_OUT, 100)

    def broken():
        raise sqlite3.OperationalError('database is locked')

    monkeypatch.setattr(counters, '_connect', broken)
    with pytest.raises(sqlite3.OperationalError):
        counters.flush()
    monkeypatch.undo()

    counters.add(5, DIRECTION_OUT, 1)
    counters.flush()
    assert counters.totals() == {5: {'in': 0, 'out': 101}}


def test_remove_user_drops_pending_bytes_too(tmp_path):
    counters = TrafficCounters(tmp_path / 'lib.db')
    counters.add(5, DIRECTION_OUT, 100)
    counters.flush()
    counters.add(5, DIRECTION_IN, 7)
    counters.add(6, DIRECTION_IN, 3)

    counters.remove_user(5)
    counters.flush()

    assert counters.totals() == {6: {'in': 3, 'out': 0}}


def test_flush_loop_saves_in_the_background(tmp_path, monkeypatch):
    path = tmp_path / 'lib.db'
    counters = TrafficCounters(path)
    counters.add(5, DIRECTION_OUT, 42)
    real_sleep = asyncio.sleep
    calls = 0

    async def fast_sleep(_seconds):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise asyncio.CancelledError
        await real_sleep(0)

    monkeypatch.setattr(traffic_mod.asyncio, 'sleep', fast_sleep)

    async def run():
        with pytest.raises(asyncio.CancelledError):
            await traffic_flush_loop(lambda: counters)

    asyncio.run(run())
    assert _saved(path) == [(5, 'out', 42)]
