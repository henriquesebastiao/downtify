"""Why slskd wasn't used: the reasons downloads fell through to another
source.

With slskd first in the source order, every song it can't serve is
fetched by the next source (YouTube Music, YouTube...) or fails. The
downloader carries the reason slskd gave up (``song['slskd_miss']``, see
``slskd_provider.take_miss``) to ``Downloader.on_outcome``, and
``api.record_download_outcome`` keeps one row here per such download:
when, why, what was used instead (``fallback``, ``''`` when nothing was
found anywhere) and the song. ``GET /api/slskd/misses`` counts them by
reason; ``DELETE /api/slskd/misses`` starts the count over, so the effect
of a settings change shows on its own.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .db.config import Dialect
from .db.core import Database, as_database

#: Like the download log: long enough for a year's view.
RETENTION_DAYS = 400
#: How many recent songs the summary lists.
RECENT = 50


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SlskdMisses:
    """The ``slskd_misses`` table of ``downtify_library.db``."""

    def __init__(self, path_or_db: str | Path | Database) -> None:
        self.db = as_database(path_or_db, 'library')
        if self.db.dialect is Dialect.SQLITE:
            self._init_db()

    def _init_db(self) -> None:
        # On PostgreSQL migration 0004 created it.
        with self.db.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS slskd_misses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    at TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    detail TEXT NOT NULL DEFAULT '',
                    fallback TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    artist TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_slskd_misses_at '
                'ON slskd_misses (at)'
            )

    def record(
        self,
        reason: str,
        *,
        detail: str = '',
        fallback: str = '',
        title: str = '',
        artist: str = '',
    ) -> None:
        with self.db.connect() as conn:
            conn.execute(
                'INSERT INTO slskd_misses '
                '(at, reason, detail, fallback, title, artist) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (
                    _now().isoformat(),
                    str(reason or 'unknown')[:40],
                    str(detail or '')[:200],
                    str(fallback or '')[:40],
                    str(title or '')[:200],
                    str(artist or '')[:200],
                ),
            )

    def summary(self) -> dict[str, Any]:
        """``{total, since, reasons: [{reason, count}], fallbacks:
        {source: count}, recent: [...]}``, most frequent reason first."""

        with self.db.connect() as conn:
            rows = [
                dict(r)
                for r in conn.execute(
                    'SELECT at, reason, detail, fallback, title, artist '
                    'FROM slskd_misses ORDER BY id DESC'
                )
            ]
        reasons = Counter(row['reason'] for row in rows)
        fallbacks = Counter(row['fallback'] or 'none' for row in rows)
        return {
            'total': len(rows),
            'since': rows[-1]['at'] if rows else None,
            'reasons': [
                {'reason': reason, 'count': count}
                for reason, count in reasons.most_common()
            ],
            'fallbacks': dict(fallbacks.most_common()),
            'recent': rows[:RECENT],
        }

    def reset(self) -> int:
        """Start over: forget every recorded reason."""

        with self.db.connect() as conn:
            return conn.execute('DELETE FROM slskd_misses').rowcount

    def prune(self, days: int = RETENTION_DAYS) -> int:
        cutoff = (_now() - timedelta(days=days)).isoformat()
        with self.db.connect() as conn:
            return conn.execute(
                'DELETE FROM slskd_misses WHERE at < ?', (cutoff,)
            ).rowcount
