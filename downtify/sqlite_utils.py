"""Shared SQLite connection tuning."""

from __future__ import annotations

import sqlite3

_BUSY_TIMEOUT_MS = 30_000


def connect_sqlite(
    path: str,
    *,
    row_factory: bool = False,
) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    if row_factory:
        conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute(f'PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}')
    return conn
