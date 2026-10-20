"""Shared SQLite connection tuning."""

from __future__ import annotations

import sqlite3
from types import TracebackType
from typing import Optional

_BUSY_TIMEOUT_MS = 30_000


class ClosingConnection(sqlite3.Connection):
    """A connection that closes itself when its ``with`` block ends.

    ``with conn:`` on a plain connection only commits or rolls back. On
    Python 3.11+ the connection then lingers - file descriptors for the
    database, ``-wal`` and ``-shm`` files included - until the cyclic GC
    gets to it, so a loop of short lookups can exhaust the process's
    descriptor limit (``OSError: [Errno 24]``).
    """

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> bool:
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


def connect_sqlite(
    path: str,
    *,
    row_factory: bool = False,
) -> sqlite3.Connection:
    conn = sqlite3.connect(
        path, check_same_thread=False, factory=ClosingConnection
    )
    if row_factory:
        conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute(f'PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}')
    return conn
