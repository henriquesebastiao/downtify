"""TrafficCounters on both backends (SQLite file, migrated PostgreSQL)."""

from __future__ import annotations

import pytest

from downtify.traffic import DIRECTION_IN, DIRECTION_OUT, TrafficCounters
from tests.db.helpers import query


def _saved(db) -> list[tuple[int, str, int]]:
    return [
        tuple(row)
        for row in query(
            db,
            'SELECT user_id, direction, total_bytes FROM traffic_counters '
            'ORDER BY user_id, direction',
        )
    ]


def test_add_and_totals_include_pending_bytes(backend_db):
    counters = TrafficCounters(backend_db)
    counters.add(5, DIRECTION_OUT, 1000)
    counters.add(5, DIRECTION_OUT, 24)
    counters.add(7, DIRECTION_IN, 10)
    counters.add(0, DIRECTION_IN, 99)  # nobody: ignored
    counters.add(7, 'sideways', 99)  # bad direction: ignored

    assert counters.totals() == {
        5: {'in': 0, 'out': 1024},
        7: {'in': 10, 'out': 0},
    }
    assert _saved(backend_db) == []


def test_flush_upserts_and_accumulates_across_flushes(backend_db):
    counters = TrafficCounters(backend_db)
    counters.add(5, DIRECTION_OUT, 1024)
    counters.add(7, DIRECTION_IN, 10)
    counters.flush()
    assert _saved(backend_db) == [(5, 'out', 1024), (7, 'in', 10)]

    counters.add(5, DIRECTION_OUT, 1)
    counters.flush()
    assert _saved(backend_db) == [(5, 'out', 1025), (7, 'in', 10)]
    assert counters.totals() == {
        5: {'in': 0, 'out': 1025},
        7: {'in': 10, 'out': 0},
    }


def test_flush_with_nothing_pending_is_a_no_op(backend_db):
    counters = TrafficCounters(backend_db)
    counters.flush()
    assert _saved(backend_db) == []


def test_a_failed_flush_keeps_the_bytes(backend_db, monkeypatch):
    counters = TrafficCounters(backend_db)
    counters.add(5, DIRECTION_OUT, 100)

    def broken():
        raise RuntimeError('database is locked')

    monkeypatch.setattr(counters, '_connect', broken)
    with pytest.raises(RuntimeError):
        counters.flush()
    monkeypatch.undo()

    counters.add(5, DIRECTION_OUT, 1)
    counters.flush()
    assert counters.totals() == {5: {'in': 0, 'out': 101}}
    assert _saved(backend_db) == [(5, 'out', 101)]


def test_remove_user_drops_saved_and_pending_rows(backend_db):
    counters = TrafficCounters(backend_db)
    counters.add(5, DIRECTION_OUT, 100)
    counters.flush()
    counters.add(5, DIRECTION_IN, 7)
    counters.add(6, DIRECTION_IN, 3)

    counters.remove_user(5)
    counters.flush()

    assert counters.totals() == {6: {'in': 3, 'out': 0}}
    assert _saved(backend_db) == [(6, 'in', 3)]
