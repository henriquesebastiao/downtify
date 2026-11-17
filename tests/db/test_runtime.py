from __future__ import annotations

import os
import uuid
from pathlib import Path

import psycopg
import pytest

from downtify.db import runtime
from downtify.db.core import Database

_TEST_URL_ENV = 'TEST_DATABASE_URL'


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('DB_SEARCH_PATH', raising=False)
    yield
    runtime.shutdown()


@pytest.fixture
def pg_schema(monkeypatch):
    url = os.environ.get(_TEST_URL_ENV)
    if not url:
        pytest.skip(f'{_TEST_URL_ENV} not set')
    schema = f'rt_{uuid.uuid4().hex[:8]}'
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(f'create schema {schema}')
    monkeypatch.setenv('DATABASE_URL', url)
    monkeypatch.setenv('DB_SEARCH_PATH', schema)
    try:
        yield schema
    finally:
        runtime.shutdown()
        with psycopg.connect(url, autocommit=True) as admin:
            admin.execute(f'drop schema if exists {schema} cascade')


def test_sqlite_returns_group_path(tmp_path):
    target = runtime.db_target('library', data_dir=tmp_path)
    assert target == tmp_path / 'downtify_library.db'
    assert isinstance(target, Path)


def test_sqlite_doctor_group_path(tmp_path):
    target = runtime.db_target('doctor_hashes', data_dir=tmp_path)
    assert target == tmp_path / 'doctor' / 'audio_hashes.db'


def test_sqlite_uses_database_dir_when_no_override(monkeypatch, tmp_path):
    monkeypatch.setenv('DATABASE_DIR', str(tmp_path))
    assert runtime.db_target('auth') == tmp_path / 'downtify_auth.db'


def test_healthcheck_none_on_sqlite(monkeypatch):
    assert runtime.healthcheck() is None


def test_postgres_returns_database_and_migrates_once(pg_schema, monkeypatch):
    calls = []
    real = runtime.run_migrations

    def counting(db, *args, **kwargs):
        calls.append(db)
        return real(db, *args, **kwargs)

    monkeypatch.setattr(runtime, 'run_migrations', counting)
    first = runtime.db_target('library', data_dir=Path('/unused'))
    second = runtime.db_target('monitor', data_dir=Path('/unused'))
    assert isinstance(first, Database)
    assert isinstance(second, Database)
    assert len(calls) == 1
    assert runtime.healthcheck() is True


def test_postgres_tables_created_in_search_path(pg_schema):
    db = runtime.db_target('library')
    with psycopg.connect(os.environ[_TEST_URL_ENV]) as conn:
        names = {
            row[0]
            for row in conn.execute(
                'select table_name from information_schema.tables '
                'where table_schema = %s',
                (pg_schema,),
            ).fetchall()
        }
    assert 'schema_migrations' in names
    assert isinstance(db, Database)


def test_shutdown_closes_pools(pg_schema):
    db = runtime.db_target('library')
    assert db._pool is not None
    assert not db._pool.closed
    runtime.shutdown()
    assert db._pool.closed


def test_shutdown_then_target_migrates_again(pg_schema, monkeypatch):
    calls = []
    real = runtime.run_migrations

    def counting(db, *args, **kwargs):
        calls.append(db)
        return real(db, *args, **kwargs)

    monkeypatch.setattr(runtime, 'run_migrations', counting)
    runtime.db_target('library')
    runtime.shutdown()
    runtime.db_target('library')
    assert len(calls) == 2
