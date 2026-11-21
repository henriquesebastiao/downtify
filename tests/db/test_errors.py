from __future__ import annotations

import sqlite3

import psycopg
import psycopg.errors
import pytest

from downtify.db import errors


def test_hierarchy() -> None:
    assert issubclass(errors.DatabaseError, Exception)
    assert issubclass(errors.OperationalError, errors.DatabaseError)
    assert issubclass(errors.OperationalError, sqlite3.OperationalError)
    assert issubclass(errors.IntegrityError, errors.DatabaseError)
    assert issubclass(errors.IntegrityError, sqlite3.IntegrityError)
    assert issubclass(errors.UndefinedTable, errors.OperationalError)
    assert issubclass(errors.SerializationRetry, errors.OperationalError)


def test_isinstance_checks() -> None:
    assert isinstance(errors.IntegrityError('x'), sqlite3.IntegrityError)
    assert isinstance(errors.UndefinedTable('x'), sqlite3.OperationalError)
    assert isinstance(errors.SerializationRetry('x'), sqlite3.OperationalError)
    assert isinstance(errors.IntegrityError('x'), errors.DatabaseError)


@pytest.mark.parametrize(
    ('exc', 'expected'),
    [
        (sqlite3.IntegrityError('UNIQUE failed'), errors.IntegrityError),
        (sqlite3.OperationalError('no such table: x'), errors.UndefinedTable),
        (
            sqlite3.OperationalError('database is locked'),
            errors.SerializationRetry,
        ),
        (
            sqlite3.OperationalError('database table is locked: t'),
            errors.SerializationRetry,
        ),
        (sqlite3.OperationalError('disk I/O error'), errors.OperationalError),
        (sqlite3.ProgrammingError('bad'), errors.ProgrammingError),
        (
            psycopg.errors.SerializationFailure('x'),
            errors.SerializationRetry,
        ),
        (psycopg.errors.DeadlockDetected('x'), errors.SerializationRetry),
        (psycopg.errors.UndefinedTable('x'), errors.UndefinedTable),
        (psycopg.errors.UniqueViolation('x'), errors.IntegrityError),
        (psycopg.OperationalError('x'), errors.OperationalError),
        (psycopg.ProgrammingError('x'), errors.ProgrammingError),
    ],
)
def test_translate_mapping(exc: BaseException, expected: type) -> None:
    result = errors.translate(exc)
    assert type(result) is expected
    assert str(result) == str(exc)
    assert result is not exc


def test_translate_non_database_error_returns_none() -> None:
    assert errors.translate(ValueError()) is None


def test_translate_already_translated_passes_through() -> None:
    exc = errors.UndefinedTable('x')
    assert errors.translate(exc) is exc


def test_wrap_errors_translates_and_chains() -> None:
    original = sqlite3.IntegrityError('boom')
    with pytest.raises(errors.IntegrityError) as info:
        with errors.wrap_errors():
            raise original
    assert info.value.__cause__ is original
    assert str(info.value) == 'boom'


def test_wrap_errors_lets_non_db_exceptions_through() -> None:
    with pytest.raises(ValueError, match='nope'):
        with errors.wrap_errors():
            raise ValueError('nope')


def test_wrap_errors_reraises_already_translated_unchanged() -> None:
    original = errors.IntegrityError('boom')
    with pytest.raises(errors.IntegrityError) as info:
        with errors.wrap_errors():
            raise original
    assert info.value is original
    assert info.value.__cause__ is None


def test_sqlite_round_trip_missing_table() -> None:
    conn = sqlite3.connect(':memory:')
    try:
        with pytest.raises(errors.UndefinedTable):
            with errors.wrap_errors():
                conn.execute('select * from missing')
    finally:
        conn.close()


def test_programming_errors_keep_the_sqlite3_class():
    out = errors.translate(sqlite3.ProgrammingError('closed'))
    assert isinstance(out, errors.ProgrammingError)
    assert isinstance(out, sqlite3.ProgrammingError)
    out = errors.translate(psycopg.ProgrammingError('syntax'))
    assert isinstance(out, errors.ProgrammingError)
