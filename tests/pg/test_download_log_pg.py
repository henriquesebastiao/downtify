"""DownloadLog on both backends (SQLite file, migrated PostgreSQL)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from downtify.download_log import (
    OUTCOME_COMPLETED,
    OUTCOME_FAILED,
    OUTCOME_SKIPPED,
    RETENTION_DAYS,
    DownloadLog,
)
from tests.db.helpers import query

NOW = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)


def _rows(db) -> list[tuple]:
    return [
        tuple(row)
        for row in query(
            db, 'SELECT outcome, provider, bytes, filename FROM download_log'
        )
    ]


def test_records_and_reads_back_rows_in_time_order(backend_db):
    log = DownloadLog(backend_db)
    log.record(
        OUTCOME_COMPLETED,
        provider='youtube',
        size=1234,
        filename='a.mp3',
        at=NOW,
    )
    log.record(OUTCOME_SKIPPED, at=NOW - timedelta(hours=1))
    log.record(OUTCOME_FAILED, provider='yt', at=NOW + timedelta(hours=1))

    rows = log.since(NOW - timedelta(days=1))

    assert [r['outcome'] for r in rows] == [
        OUTCOME_SKIPPED,
        OUTCOME_COMPLETED,
        OUTCOME_FAILED,
    ]
    assert rows[1] == {
        'at': NOW.isoformat(),
        'outcome': OUTCOME_COMPLETED,
        'provider': 'youtube',
        'bytes': 1234,
    }
    assert all(isinstance(r['bytes'], int) for r in rows)


def test_since_filters_by_moment(backend_db):
    log = DownloadLog(backend_db)
    log.record(OUTCOME_COMPLETED, at=NOW - timedelta(days=5))
    log.record(OUTCOME_COMPLETED, at=NOW)

    rows = log.since(NOW - timedelta(days=1))

    assert [r['at'] for r in rows] == [NOW.isoformat()]


def test_unknown_outcome_is_ignored_and_fields_are_clipped(backend_db):
    log = DownloadLog(backend_db)
    log.record('bogus', at=NOW)
    log.record(
        OUTCOME_COMPLETED,
        provider='p' * 40,
        size=-5,
        filename='f' * 1200,
        at=NOW,
    )

    rows = _rows(backend_db)

    assert rows == [(OUTCOME_COMPLETED, 'p' * 32, 0, 'f' * 1000)]


def test_first_at_reports_the_oldest_row_or_none(backend_db):
    log = DownloadLog(backend_db)
    assert log.first_at() is None

    log.record(OUTCOME_COMPLETED, at=NOW)
    log.record(OUTCOME_FAILED, at=NOW - timedelta(days=2))

    assert log.first_at() == (NOW - timedelta(days=2)).isoformat()


def test_prune_drops_rows_older_than_retention(backend_db):
    log = DownloadLog(backend_db)
    old = NOW - timedelta(days=RETENTION_DAYS + 5)
    log.record(OUTCOME_COMPLETED, at=old)
    log.record(OUTCOME_SKIPPED, at=NOW)

    deleted = log.prune()

    assert deleted == 1
    assert [r[0] for r in _rows(backend_db)] == [OUTCOME_SKIPPED]


def test_the_id_column_is_generated_on_both_backends(backend_db):
    log = DownloadLog(backend_db)
    log.record(OUTCOME_COMPLETED, at=NOW)
    log.record(OUTCOME_COMPLETED, at=NOW)

    ids = [row[0] for row in query(backend_db, 'SELECT id FROM download_log')]

    assert len(set(ids)) == 2
