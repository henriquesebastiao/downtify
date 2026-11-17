"""Unified database exceptions for the SQLite and PostgreSQL backends.

The classes also subclass the matching ``sqlite3`` exceptions so existing
code that catches ``sqlite3.OperationalError`` or ``sqlite3.IntegrityError``
keeps working on the SQLite backend.
"""

from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Iterator

import psycopg


class DatabaseError(Exception):
    """Base class for all translated database errors."""


class OperationalError(DatabaseError, sqlite3.OperationalError):
    """Operational failure (connection, lock, runtime error)."""


class IntegrityError(DatabaseError, sqlite3.IntegrityError):
    """Constraint violation."""


class ProgrammingError(DatabaseError, sqlite3.ProgrammingError):
    """API misuse, e.g. using a connection after its block has ended."""


class UndefinedTable(OperationalError):
    """A referenced table does not exist."""


class SerializationRetry(OperationalError):
    """The whole transaction is safe to retry.

    Covers PostgreSQL deadlocks and serialization failures and the SQLite
    'database is locked' condition.
    """


_RETRY_SQLSTATES = frozenset({'40001', '40P01'})


def _translate_sqlite(exc: sqlite3.Error, msg: str) -> DatabaseError:
    if isinstance(exc, sqlite3.IntegrityError):
        return IntegrityError(msg)
    if isinstance(exc, sqlite3.OperationalError):
        if msg.startswith('no such table'):
            return UndefinedTable(msg)
        if 'database is locked' in msg or 'database table is locked' in msg:
            return SerializationRetry(msg)
        return OperationalError(msg)
    if isinstance(exc, sqlite3.ProgrammingError):
        return ProgrammingError(msg)
    return DatabaseError(msg)


def _translate_psycopg(exc: psycopg.Error, msg: str) -> DatabaseError:
    sqlstate = getattr(exc, 'sqlstate', None)
    if sqlstate in _RETRY_SQLSTATES:
        return SerializationRetry(msg)
    if sqlstate == '42P01':
        return UndefinedTable(msg)
    if (sqlstate or '').startswith('23') or isinstance(
        exc, psycopg.IntegrityError
    ):
        return IntegrityError(msg)
    if isinstance(exc, psycopg.OperationalError):
        return OperationalError(msg)
    if isinstance(exc, psycopg.ProgrammingError):
        return ProgrammingError(msg)
    return DatabaseError(msg)


def translate(exc: BaseException) -> DatabaseError | None:
    """Map a backend exception to a ``DatabaseError``.

    Returns None if ``exc`` is not a database error, ``exc`` itself if it
    is already a ``DatabaseError``, otherwise a new translated exception
    with the same message.
    """
    if isinstance(exc, DatabaseError):
        return exc
    msg = str(exc)
    if isinstance(exc, sqlite3.Error):
        return _translate_sqlite(exc, msg)
    if isinstance(exc, psycopg.Error):
        return _translate_psycopg(exc, msg)
    return None


@contextlib.contextmanager
def wrap_errors() -> Iterator[None]:
    """Re-raise backend database errors as translated ``DatabaseError``s.

    The translated exception is chained to the original with ``from``.
    Non-database exceptions propagate unchanged.
    """
    try:
        yield
    except BaseException as exc:
        translated = translate(exc)
        if translated is None or translated is exc:
            raise
        raise translated from exc
