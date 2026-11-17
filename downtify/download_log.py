"""How every download ended, for the library usage page.

The queue only keeps its jobs until they are cleared, and a Playlist
Monitor sweep keeps none at all, so neither can say how many downloads
finished, were skipped or failed last month. :class:`DownloadLog` keeps
one small row per attempt in ``downtify_library.db`` - when, how it
ended (``OUTCOME_*``), which provider fetched the audio and how big the
file was - for :data:`RETENTION_DAYS`.

Rows come from ``Downloader.on_outcome`` (every download, from the queue
or a monitor sweep alike: fetched, already in the library, or failed)
and from the queue's own "already in library" check, which ends a job
before the downloader is asked (see ``api.record_download_outcome``).
``GET /api/library/usage`` (``downtify/library_usage.py``) sums them up.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from .db.config import Dialect
from .db.core import Database, as_database

#: A new file was downloaded and tagged.
OUTCOME_COMPLETED = 'completed'
#: The song was already in the library; nothing was downloaded.
OUTCOME_SKIPPED = 'skipped'
#: The download failed (no match, too long, a provider error...).
OUTCOME_FAILED = 'failed'

OUTCOMES = (OUTCOME_COMPLETED, OUTCOME_SKIPPED, OUTCOME_FAILED)

#: Long enough for the longest period the usage page shows (a year).
RETENTION_DAYS = 400


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DownloadLog:
    """One row per download attempt, oldest dropped after a while."""

    def __init__(self, path_or_db: str | Path | Database) -> None:
        self.db = as_database(path_or_db, 'library')
        if isinstance(path_or_db, Database):
            self._path = str(self.db.path) if self.db.path else None
        else:
            self._path = str(path_or_db)
        if self.db.dialect is Dialect.SQLITE:
            self._init_db()

    def _init_db(self) -> None:
        # On PostgreSQL the library_a migration already created the table.
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    at TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    provider TEXT NOT NULL DEFAULT '',
                    bytes INTEGER NOT NULL DEFAULT 0,
                    filename TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_download_log_at '
                'ON download_log (at)'
            )

    def _connect(self):
        return self.db.connect()

    def record(
        self,
        outcome: str,
        *,
        provider: str = '',
        size: int = 0,
        filename: str = '',
        at: Optional[datetime] = None,
    ) -> None:
        """Note how one download ended; an unknown *outcome* is ignored."""

        if outcome not in OUTCOMES:
            return
        with self._connect() as conn:
            conn.execute(
                'INSERT INTO download_log (at, outcome, provider, bytes, '
                'filename) VALUES (?, ?, ?, ?, ?)',
                (
                    (at or _now()).isoformat(),
                    outcome,
                    str(provider or '')[:32],
                    max(0, int(size or 0)),
                    str(filename or '')[:1000],
                ),
            )

    def since(self, moment: datetime) -> list[dict[str, Any]]:
        """Every row from *moment* on, oldest first."""

        with self._connect() as conn:
            rows = conn.execute(
                'SELECT at, outcome, provider, bytes FROM download_log '
                'WHERE at >= ? ORDER BY at',
                (moment.isoformat(),),
            ).fetchall()
        return [
            {
                'at': row[0],
                'outcome': row[1],
                'provider': row[2],
                'bytes': int(row[3]),
            }
            for row in rows
        ]

    def first_at(self) -> Optional[str]:
        """When the oldest row still kept was written, if any."""

        with self._connect() as conn:
            row = conn.execute('SELECT MIN(at) FROM download_log').fetchone()
        return row[0] if row and row[0] else None

    def prune(self, days: int = RETENTION_DAYS) -> int:
        cutoff = (_now() - timedelta(days=days)).isoformat()
        with self._connect() as conn:
            deleted = conn.execute(
                'DELETE FROM download_log WHERE at < ?', (cutoff,)
            ).rowcount
            conn.commit()
        return deleted
