"""Recognize transient contention without hiding corrupt or missing databases."""

import sqlite3
import time


def is_busy(error):
    code = getattr(error, 'sqlite_errorcode', None)
    if code is not None:
        return (code & 255) in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}
    return isinstance(error, sqlite3.OperationalError) and str(error) in {
        'database is locked',
        'database table is locked',
        'database schema is locked',
    }


def retry_busy(operation, *, seconds=10):
    deadline, delay = time.monotonic() + seconds, 0.05
    while True:
        try:
            return operation()
        except sqlite3.OperationalError as error:
            if not is_busy(error) or time.monotonic() >= deadline:
                raise
            time.sleep(delay)
            delay = min(0.5, delay * 2)
