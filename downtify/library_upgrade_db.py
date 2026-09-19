"""Storage for library upgrade runs, their queue and what was checked.

A library upgrade can take hours, so the queue lives in
``downtify_library.db`` rather than in memory: stopping the container
mid-run and starting it again resumes where it left off. The same
database remembers when each track was last looked at, so a second run
doesn't ask iTunes and Spotify about tracks that were already checked.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from .sqlite_utils import connect_sqlite

# Run states.
STATE_SCANNING = 'scanning'
STATE_READY = 'ready'
STATE_RUNNING = 'running'
STATE_PAUSED = 'paused'
STATE_DONE = 'done'
STATE_CANCELLED = 'cancelled'

#: States a run can still be resumed from after a restart.
LIVE_STATES = (STATE_SCANNING, STATE_READY, STATE_RUNNING, STATE_PAUSED)

# Job states.
JOB_QUEUED = 'queued'
JOB_RUNNING = 'running'
JOB_DONE = 'done'
JOB_SKIPPED = 'skipped'
JOB_FAILED = 'failed'


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_list(raw: Any) -> list[str]:
    try:
        value = json.loads(str(raw or '[]'))
    except ValueError:
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def _json_dict(raw: Any) -> dict[str, Any]:
    try:
        value = json.loads(str(raw or '{}'))
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _run_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        'id': int(row['id']),
        'state': str(row['state']),
        'categories': _json_list(row['categories']),
        'options': _json_dict(row['options']),
        'total_tracks': int(row['total_tracks'] or 0),
        'total_bytes': int(row['total_bytes'] or 0),
        'summary': _json_dict(row['summary']),
        'created_at': str(row['created_at'] or ''),
        'finished_at': str(row['finished_at'] or ''),
    }


def _job_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        'file': str(row['stored_path']),
        'status': str(row['status']),
        'stage': str(row['stage'] or ''),
        'categories': _json_list(row['categories']),
        'size': int(row['size_bytes'] or 0),
        'title': str(row['title'] or ''),
        'artist': str(row['artist'] or ''),
        'detail': str(row['detail'] or ''),
        'changed': _json_list(row['changed']),
        'updated_at': str(row['updated_at'] or ''),
    }


class LibraryUpgradeDB:
    """Runs, their queued tracks, and per-track check history."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS library_upgrade_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    state TEXT NOT NULL,
                    categories TEXT NOT NULL DEFAULT '[]',
                    options TEXT NOT NULL DEFAULT '{}',
                    total_tracks INTEGER NOT NULL DEFAULT 0,
                    total_bytes INTEGER NOT NULL DEFAULT 0,
                    summary TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS library_upgrade_jobs (
                    run_id INTEGER NOT NULL,
                    stored_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL DEFAULT '',
                    categories TEXT NOT NULL DEFAULT '[]',
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    title TEXT NOT NULL DEFAULT '',
                    artist TEXT NOT NULL DEFAULT '',
                    detail TEXT NOT NULL DEFAULT '',
                    changed TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (run_id, stored_path)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_upgrade_jobs_status
                ON library_upgrade_jobs (run_id, status)
            """)
            # One row per track *and category*: repairing artwork says
            # nothing about whether the track's lyrics were ever looked
            # for, so a later run for another category must not treat the
            # track as already handled.
            conn.execute("""
                CREATE TABLE IF NOT EXISTS library_upgrade_checks (
                    stored_path TEXT NOT NULL,
                    category TEXT NOT NULL,
                    checked_at TEXT NOT NULL,
                    app_version TEXT NOT NULL DEFAULT '',
                    artwork_px INTEGER NOT NULL DEFAULT 0,
                    artwork_source TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (stored_path, category)
                )
            """)

    # ── Runs ──────────────────────────────────────────────────────
    def create_run(
        self, categories: list[str], options: dict[str, Any]
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO library_upgrade_runs
                   (state, categories, options, created_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    STATE_SCANNING,
                    json.dumps(list(categories)),
                    json.dumps(dict(options)),
                    _now_iso(),
                ),
            )
            return int(cur.lastrowid or 0)

    def latest_run(self) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM library_upgrade_runs ORDER BY id DESC LIMIT 1'
            ).fetchone()
        return _run_row(row) if row is not None else None

    def get_run(self, run_id: int) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT * FROM library_upgrade_runs WHERE id = ?', (run_id,)
            ).fetchone()
        return _run_row(row) if row is not None else None

    def set_state(self, run_id: int, state: str) -> None:
        finished = _now_iso() if state in {STATE_DONE, STATE_CANCELLED} else ''
        with self._connect() as conn:
            conn.execute(
                """UPDATE library_upgrade_runs
                   SET state = ?, finished_at = ?
                   WHERE id = ?""",
                (state, finished, run_id),
            )

    def set_categories(self, run_id: int, categories: list[str]) -> None:
        with self._connect() as conn:
            conn.execute(
                'UPDATE library_upgrade_runs SET categories = ? WHERE id = ?',
                (json.dumps(list(categories)), run_id),
            )

    def set_summary(self, run_id: int, summary: dict[str, Any]) -> None:
        """Store what the scan found.

        It can't change after the scan, and every progress message
        carries it, so it is computed once here rather than aggregated
        out of tens of thousands of job rows on each broadcast.
        """

        with self._connect() as conn:
            conn.execute(
                'UPDATE library_upgrade_runs SET summary = ? WHERE id = ?',
                (json.dumps(dict(summary)), run_id),
            )

    def set_totals(self, run_id: int, tracks: int, size_bytes: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """UPDATE library_upgrade_runs
                   SET total_tracks = ?, total_bytes = ?
                   WHERE id = ?""",
                (int(tracks), int(size_bytes), run_id),
            )

    # ── Queue ─────────────────────────────────────────────────────
    def add_jobs(self, run_id: int, jobs: Iterable[dict[str, Any]]) -> int:
        rows = [
            (
                run_id,
                str(job['file']),
                JOB_QUEUED,
                json.dumps(list(job.get('categories') or [])),
                int(job.get('size') or 0),
                str(job.get('title') or ''),
                str(job.get('artist') or ''),
                _now_iso(),
            )
            for job in jobs
        ]
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                """INSERT INTO library_upgrade_jobs
                   (run_id, stored_path, status, categories, size_bytes,
                    title, artist, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(run_id, stored_path) DO NOTHING""",
                rows,
            )
        return len(rows)

    def take_next(self, run_id: int) -> Optional[dict[str, Any]]:
        """Claim the next queued track, marking it running."""

        with self._connect() as conn:
            row = conn.execute(
                """SELECT * FROM library_upgrade_jobs
                   WHERE run_id = ? AND status = ?
                   ORDER BY stored_path LIMIT 1""",
                (run_id, JOB_QUEUED),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                """UPDATE library_upgrade_jobs
                   SET status = ?, updated_at = ?
                   WHERE run_id = ? AND stored_path = ?""",
                (JOB_RUNNING, _now_iso(), run_id, row['stored_path']),
            )
        job = _job_row(row)
        job['status'] = JOB_RUNNING
        return job

    def set_stage(self, run_id: int, stored_path: str, stage: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """UPDATE library_upgrade_jobs SET stage = ?, updated_at = ?
                   WHERE run_id = ? AND stored_path = ?""",
                (stage, _now_iso(), run_id, stored_path),
            )

    def finish_job(
        self,
        run_id: int,
        stored_path: str,
        status: str,
        *,
        detail: str = '',
        changed: Optional[list[str]] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """UPDATE library_upgrade_jobs
                   SET status = ?, stage = '', detail = ?, changed = ?,
                       updated_at = ?
                   WHERE run_id = ? AND stored_path = ?""",
                (
                    status,
                    detail[:500],
                    json.dumps(list(changed or [])),
                    _now_iso(),
                    run_id,
                    stored_path,
                ),
            )

    def requeue_running(self, run_id: int) -> int:
        """Put jobs interrupted by a restart back in the queue."""

        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE library_upgrade_jobs
                   SET status = ?, stage = '', updated_at = ?
                   WHERE run_id = ? AND status = ?""",
                (JOB_QUEUED, _now_iso(), run_id, JOB_RUNNING),
            )
            return cur.rowcount

    def counts(self, run_id: int) -> dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT status, COUNT(*) AS n,
                          COALESCE(SUM(size_bytes), 0) AS bytes
                   FROM library_upgrade_jobs WHERE run_id = ?
                   GROUP BY status""",
                (run_id,),
            ).fetchall()
        by_status = {str(row['status']): int(row['n']) for row in rows}
        done_bytes = sum(
            int(row['bytes'])
            for row in rows
            if str(row['status']) in {JOB_DONE, JOB_SKIPPED, JOB_FAILED}
        )
        total = sum(by_status.values())
        finished = (
            by_status.get(JOB_DONE, 0)
            + by_status.get(JOB_SKIPPED, 0)
            + by_status.get(JOB_FAILED, 0)
        )
        return {
            'total': total,
            'queued': by_status.get(JOB_QUEUED, 0),
            'running': by_status.get(JOB_RUNNING, 0),
            'completed': by_status.get(JOB_DONE, 0),
            'skipped': by_status.get(JOB_SKIPPED, 0),
            'failed': by_status.get(JOB_FAILED, 0),
            'finished': finished,
            'processed_bytes': done_bytes,
        }

    def jobs(
        self,
        run_id: int,
        *,
        status: Optional[str] = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        query = 'SELECT * FROM library_upgrade_jobs WHERE run_id = ?'
        params: list[Any] = [run_id]
        if status:
            query += ' AND status = ?'
            params.append(status)
        query += ' ORDER BY updated_at DESC, stored_path LIMIT ?'
        params.append(int(limit))
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_job_row(row) for row in rows]

    def delete_run_jobs(self, run_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                'DELETE FROM library_upgrade_jobs WHERE run_id = ?', (run_id,)
            )

    # ── Per-track check history ───────────────────────────────────
    def record_check(
        self,
        stored_path: str,
        categories: list[str],
        *,
        app_version: str,
        artwork_px: int = 0,
        artwork_source: str = '',
    ) -> None:
        """Remember that these categories were just looked at for a track."""

        rows = [
            (
                stored_path,
                category,
                _now_iso(),
                app_version,
                int(artwork_px),
                artwork_source,
            )
            for category in categories
        ]
        if not rows:
            return
        with self._connect() as conn:
            conn.executemany(
                """INSERT INTO library_upgrade_checks
                   (stored_path, category, checked_at, app_version,
                    artwork_px, artwork_source)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(stored_path, category) DO UPDATE SET
                   checked_at = excluded.checked_at,
                   app_version = excluded.app_version,
                   artwork_px = MAX(excluded.artwork_px,
                                    library_upgrade_checks.artwork_px),
                   artwork_source = excluded.artwork_source""",
                rows,
            )

    def record_checks(
        self,
        entries: Iterable[tuple[str, list[str]]],
        *,
        app_version: str,
    ) -> int:
        """Record many tracks' checks at once.

        The scan uses this for the categories it examined and found
        nothing to do for: looking and finding nothing is a check like
        any other, and writing them one connection per track would cost
        tens of thousands of round-trips on a large library.
        """

        now = _now_iso()
        rows = [
            (path, category, now, app_version)
            for path, categories in entries
            for category in categories
        ]
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                """INSERT INTO library_upgrade_checks
                   (stored_path, category, checked_at, app_version)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(stored_path, category) DO UPDATE SET
                   checked_at = excluded.checked_at,
                   app_version = excluded.app_version""",
                rows,
            )
        return len(rows)

    def checks_for(
        self, paths: list[str]
    ) -> dict[str, dict[str, dict[str, Any]]]:
        """``{stored_path: {category: check}}`` for the paths given."""

        if not paths:
            return {}
        found: dict[str, dict[str, dict[str, Any]]] = {}
        with self._connect() as conn:
            for start in range(0, len(paths), 400):
                chunk = paths[start : start + 400]
                marks = ','.join('?' * len(chunk))
                rows = conn.execute(
                    f"""SELECT * FROM library_upgrade_checks
                        WHERE stored_path IN ({marks})""",  # noqa: S608
                    chunk,
                ).fetchall()
                for row in rows:
                    found.setdefault(str(row['stored_path']), {})[
                        str(row['category'])
                    ] = {
                        'checked_at': str(row['checked_at'] or ''),
                        'app_version': str(row['app_version'] or ''),
                        'artwork_px': int(row['artwork_px'] or 0),
                        'artwork_source': str(row['artwork_source'] or ''),
                    }
        return found

    def forget_checks(self) -> int:
        with self._connect() as conn:
            cur = conn.execute('DELETE FROM library_upgrade_checks')
            return cur.rowcount


def check_is_fresh(
    check: Optional[dict[str, Any]],
    *,
    app_version: str,
    max_age_days: int,
) -> bool:
    """True when this track was checked recently by this Downtify version.

    A newer Downtify may match or tag better than the one that ran
    before, so a check made by another version is never treated as
    fresh — that is what lets an upgraded install re-examine a library
    that an older one already went through.
    """

    if not check or max_age_days <= 0:
        return False
    if str(check.get('app_version') or '') != app_version:
        return False
    try:
        checked = datetime.fromisoformat(str(check.get('checked_at') or ''))
    except ValueError:
        return False
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - checked
    return age < timedelta(days=max_age_days)
