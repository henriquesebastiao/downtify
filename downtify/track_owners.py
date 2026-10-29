"""Who put each library file on the server.

A ``user`` only sees the tracks they asked to download; an ``admin``
sees everything (see :mod:`downtify.users`). Files are never duplicated:
when two users download the same track it lands on disk once (the
existing dedup in :func:`downtify.track_index.resolve_existing_download`
already guarantees that) and every downloader gets an ownership row
here, keyed by the file's content key (basename + size, stable across
folder moves - see :mod:`downtify.library_cache_keys`).

The key changes when a file is rewritten in place (a re-download with
different bytes, a tags/artwork upgrade, an audio replace). Rows heal
themselves: every record carries the file's library path, so recording
an owner re-points stale rows at the same path to the fresh key, and
:func:`TrackOwners.rekey` does the same for flows that rewrite files
without downloading.

Files with no owners at all are pre-feature, monitor, reconcile or
externally added files: admins see them, users don't. Removing the last
owner is done only through the delete endpoints, which also take the
file off disk then - nothing is ever garbage-collected behind anyone's
back.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Collection

from .sqlite_utils import connect_sqlite


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TrackOwners:
    """``(content_key, user_id)`` rows in ``downtify_library.db``."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS track_owners (
                    content_key TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    added_at TEXT NOT NULL,
                    stored_path TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (content_key, user_id)
                )
            """)
            columns = {
                row[1]
                for row in conn.execute('PRAGMA table_info(track_owners)')
            }
            if 'stored_path' not in columns:
                conn.execute(
                    'ALTER TABLE track_owners ADD COLUMN stored_path TEXT '
                    "NOT NULL DEFAULT ''"
                )
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_track_owners_user
                ON track_owners (user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_track_owners_path
                ON track_owners (stored_path)
            """)

    @staticmethod
    def _norm_path(stored_path: str) -> str:
        return str(stored_path or '').strip().replace('\\', '/')

    def add(
        self, content_key: str, user_id: int, stored_path: str = ''
    ) -> bool:
        """Record *user_id* as an owner. ``True`` when it is new.

        Stale rows at the same path (the file was rewritten since) are
        re-pointed at the fresh key along the way, so an upgrade or a
        re-download never orphans anyone's ownership.
        """

        key = str(content_key or '').strip()
        if not key or not user_id:
            return False
        path = self._norm_path(stored_path)
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO track_owners
                   (content_key, user_id, added_at, stored_path)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(content_key, user_id) DO NOTHING""",
                (key, int(user_id), _now_iso(), path),
            )
            new = cur.rowcount > 0
            if path:
                conn.execute(
                    'UPDATE track_owners SET stored_path = ? '
                    'WHERE content_key = ? AND user_id = ?',
                    (path, key, int(user_id)),
                )
                self._heal_path(conn, path, key)
            return new

    @staticmethod
    def _heal_path(conn: sqlite3.Connection, path: str, key: str) -> None:
        """Re-point rows at *path* whose key went stale, dropping the
        exact duplicates left behind."""

        conn.execute(
            'UPDATE OR IGNORE track_owners SET content_key = ?, '
            'stored_path = ? WHERE stored_path = ? AND content_key != ?',
            (key, path, path, key),
        )
        conn.execute(
            'DELETE FROM track_owners WHERE stored_path = ? '
            'AND content_key != ?',
            (path, key),
        )

    def rekey(self, old_key: str, new_key: str, stored_path: str = '') -> int:
        """Point rows at a rewritten file (upgrade/replace in place).

        Returns how many rows moved. Exact duplicates left behind (the
        same user already owned the fresh key) are dropped.
        """

        old = str(old_key or '').strip()
        new = str(new_key or '').strip()
        if not old or not new or old == new:
            return 0
        path = self._norm_path(stored_path)
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                'UPDATE OR IGNORE track_owners SET content_key = ?, '
                'stored_path = COALESCE(NULLIF(?, ?), stored_path) '
                'WHERE content_key = ?',
                (new, path, '', old),
            )
            moved = cur.rowcount
            conn.execute(
                'DELETE FROM track_owners WHERE content_key = ?', (old,)
            )
            return moved

    def remove(self, content_key: str, user_id: int) -> int:
        """Drop one owner's row; how many owners remain for the file."""

        key = str(content_key or '').strip()
        if not key or not user_id:
            return self.count(key)
        with self._lock, self._connect() as conn:
            conn.execute(
                'DELETE FROM track_owners WHERE content_key = ? '
                'AND user_id = ?',
                (key, int(user_id)),
            )
            row = conn.execute(
                'SELECT COUNT(*) AS n FROM track_owners WHERE content_key = ?',
                (key,),
            ).fetchone()
            return int(row['n'])

    def drop_file(self, content_key: str) -> None:
        """Forget every owner (the file itself is already gone)."""

        key = str(content_key or '').strip()
        if not key:
            return
        with self._lock, self._connect() as conn:
            conn.execute(
                'DELETE FROM track_owners WHERE content_key = ?', (key,)
            )

    def count(self, content_key: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT COUNT(*) AS n FROM track_owners WHERE content_key = ?',
                (str(content_key or '').strip(),),
            ).fetchone()
        return int(row['n'])

    def is_empty(self) -> bool:
        """Whether no ownership was recorded yet (first start)."""

        with self._connect() as conn:
            row = conn.execute('SELECT 1 FROM track_owners LIMIT 1').fetchone()
        return row is None

    def owners(self, content_key: str) -> list[int]:
        """Every owner's user id, oldest first."""

        with self._connect() as conn:
            rows = conn.execute(
                'SELECT user_id FROM track_owners WHERE content_key = ? '
                'ORDER BY added_at, rowid',
                (str(content_key or '').strip(),),
            ).fetchall()
        return [int(row['user_id']) for row in rows]

    def owned_keys(self, user_id: int) -> set[str]:
        """Every content key *user_id* owns."""

        with self._connect() as conn:
            rows = conn.execute(
                'SELECT content_key FROM track_owners WHERE user_id = ?',
                (int(user_id),),
            ).fetchall()
        return {str(row['content_key']) for row in rows}

    def count_by_user(self) -> dict[int, int]:
        """How many ownership rows each account has (download history)."""

        with self._connect() as conn:
            rows = conn.execute(
                'SELECT user_id, COUNT(*) AS n FROM track_owners '
                'GROUP BY user_id'
            ).fetchall()
        return {int(row['user_id']): int(row['n']) for row in rows}

    def remove_user(self, user_id: int) -> int:
        """Drop every row of a deleted account; how many went."""

        with self._lock, self._connect() as conn:
            cur = conn.execute(
                'DELETE FROM track_owners WHERE user_id = ?',
                (int(user_id),),
            )
            return cur.rowcount

    def owned_subset(
        self, content_keys: Collection[str], user_id: int
    ) -> set[str]:
        """Which of *content_keys* *user_id* owns (one query, chunked)."""

        wanted = [str(k or '').strip() for k in content_keys if k]
        if not wanted or not user_id:
            return set()
        found: set[str] = set()
        with self._connect() as conn:
            for start in range(0, len(wanted), 500):
                chunk = wanted[start : start + 500]
                marks = ','.join('?' * len(chunk))
                for row in conn.execute(
                    'SELECT content_key FROM track_owners '
                    f'WHERE user_id = ? AND content_key IN ({marks})',
                    (int(user_id), *chunk),
                ).fetchall():
                    found.add(str(row['content_key']))
        return found
