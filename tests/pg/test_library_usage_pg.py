"""UsageSnapshots on both backends: the same results on SQLite and PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from downtify.library_usage import UsageSnapshots

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)


def test_record_keeps_one_reading_a_day(backend_db) -> None:
    store = UsageSnapshots(backend_db)
    store.record({'files': 1, 'bytes': 10}, NOW - timedelta(days=9))
    store.record({'files': 2, 'bytes': 20}, NOW - timedelta(days=2))
    store.record({'files': 3, 'bytes': 30}, NOW - timedelta(hours=1))
    store.record(
        {
            'files': 4,
            'bytes': 40,
            'working_files': 1,
            'working_bytes': 7,
            'by_provider': [{'name': 'slskd', 'files': 4}],
            'by_location': [],
        },
        NOW,
    )

    rows = store.since('2026-10-24')

    # The reading before the period still stands for its first days.
    assert [(r['day'], r['bytes']) for r in rows] == [
        ('2026-10-18', 10),
        ('2026-10-25', 20),
        ('2026-10-27', 40),
    ]
    assert rows[-1]['working_files'] == 1
    assert rows[-1]['working_bytes'] == 7
    assert set(rows[-1].keys()) == {
        'day',
        'files',
        'bytes',
        'working_files',
        'working_bytes',
    }


def test_since_without_rows_is_empty(backend_db) -> None:
    store = UsageSnapshots(backend_db)
    assert store.since('2026-10-24') == []


def test_since_returns_only_the_last_reading_before(backend_db) -> None:
    store = UsageSnapshots(backend_db)
    store.record({'files': 1, 'bytes': 10}, NOW - timedelta(days=5))
    store.record({'files': 2, 'bytes': 20}, NOW - timedelta(days=3))

    rows = store.since('2026-10-25')

    assert [(r['day'], r['bytes']) for r in rows] == [('2026-10-24', 20)]


def test_second_store_on_same_database_sees_rows(backend_db) -> None:
    UsageSnapshots(backend_db).record({'files': 5, 'bytes': 50}, NOW)

    # Re-opening (the constructor runs its startup logic again) keeps data.
    rows = UsageSnapshots(backend_db).since('2026-10-27')

    assert [(r['day'], r['files'], r['bytes']) for r in rows] == [
        ('2026-10-27', 5, 50)
    ]
