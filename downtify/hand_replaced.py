"""Files whose audio an admin replaced by hand, kept from being overwritten.

**Replace audio** (a version picked on YouTube, a SoundCloud link, or an
audio file uploaded from the admin's own computer) puts the right audio
in a library file. With **Download again if the file exists** on, the
next download of the same song - from another monitored playlist, an
artist watch, a playlist download - would write over it with whatever
the automatic match finds, which is how a wrong version comes back
(issue #582).

So each replacement is remembered here, by library path, and the
downloader leaves those files alone: a download that would land on one
counts as "already downloaded" instead (see
``Downloader._hand_replaced_at``). Library upgrade's audio replacement
skips them too. The admin can lift it from the Replace audio dialog.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

from .sqlite_utils import connect_sqlite

#: Where the new audio came from.
SOURCES = ('youtube', 'soundcloud', 'file')


def _key(file: str) -> str:
    return str(file or '').replace('\\', '/').strip('/')


class HandReplacedFiles:
    """Library files (as stored: relative to the downloads folder, or
    ``slskd/...``) whose audio was replaced by hand."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hand_replaced_files (
                    file TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    replaced_at REAL NOT NULL
                )
            """)

    def _connect(self):
        return connect_sqlite(self._path, row_factory=True)

    def mark(self, file: str, source: str) -> None:
        """Remember that *file*'s audio was just replaced from *source*."""

        if source not in SOURCES:
            raise ValueError(f'unknown source {source!r}')
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO hand_replaced_files (file, source, replaced_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(file) DO UPDATE SET
                     source = excluded.source,
                     replaced_at = excluded.replaced_at""",
                (_key(file), source, time.time()),
            )

    def get(self, file: str) -> Optional[dict[str, Any]]:
        """``{file, source, replaced_at}`` for a protected file, else
        ``None``."""

        with self._connect() as conn:
            row = conn.execute(
                'SELECT file, source, replaced_at FROM hand_replaced_files '
                'WHERE file = ?',
                (_key(file),),
            ).fetchone()
        return dict(row) if row else None

    def protected(self, file: str) -> bool:
        return self.get(file) is not None

    def forget(self, file: str) -> bool:
        """Let downloads overwrite *file* again. Whether it was kept."""

        with self._connect() as conn:
            cursor = conn.execute(
                'DELETE FROM hand_replaced_files WHERE file = ?',
                (_key(file),),
            )
        return cursor.rowcount > 0

    def rename(self, old: str, new: str) -> None:
        """*old* is now *new* (a merge or a move kept the replacement)."""

        with self._connect() as conn:
            conn.execute(
                'UPDATE OR REPLACE hand_replaced_files SET file = ? '
                'WHERE file = ?',
                (_key(new), _key(old)),
            )

    def count(self) -> int:
        with self._connect() as conn:
            return int(
                conn.execute(
                    'SELECT COUNT(*) FROM hand_replaced_files'
                ).fetchone()[0]
            )
