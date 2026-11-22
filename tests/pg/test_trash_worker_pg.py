"""Trash worker CLI: admin recheck and argument handling on both backends."""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

import psycopg
import pytest

from downtify import trash_worker
from downtify.db import runtime
from downtify.db.core import Database
from downtify.users import UserStore

_TEST_URL_ENV = 'TEST_DATABASE_URL'
_PASSWORD = 'a long enough test password'


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('DATABASE_DIR', raising=False)
    monkeypatch.delenv('DB_SEARCH_PATH', raising=False)
    yield
    runtime.shutdown()


@pytest.fixture
def pg_schema(monkeypatch):
    url = os.environ.get(_TEST_URL_ENV)
    if not url:
        pytest.skip(f'{_TEST_URL_ENV} not set')
    schema = f'tw_{uuid.uuid4().hex[:8]}'
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


def _accounts(db) -> tuple[int, int]:
    store = UserStore(db)
    admin = store.create('boss', _PASSWORD, role='admin')
    plain = store.create('plain', _PASSWORD, role='user')
    return admin['id'], plain['id']


def test_authorizer_on_database(backend_db) -> None:
    admin_id, user_id = _accounts(backend_db)
    authorized = trash_worker.make_authorizer(backend_db)
    assert authorized(admin_id) is True
    assert authorized(user_id) is False
    assert authorized(999_999) is False


def test_authorizer_on_sqlite_file(tmp_path) -> None:
    path = tmp_path / 'auth.db'
    admin_id, user_id = _accounts(Database.sqlite(path))
    authorized = trash_worker.make_authorizer(path)
    assert authorized(admin_id) is True
    assert authorized(user_id) is False
    assert authorized(999_999) is False


def test_authorizer_on_runtime_target(pg_schema) -> None:
    db = runtime.db_target('auth', Path('/unused'))
    assert isinstance(db, Database)
    admin_id, user_id = _accounts(db)
    authorized = trash_worker.make_authorizer(db)
    assert authorized(admin_id) is True
    assert authorized(user_id) is False
    assert authorized(admin_id) is True


def _config(tmp_path: Path) -> Path:
    music = tmp_path / 'music'
    music.mkdir(exist_ok=True)
    config = tmp_path / 'roots.json'
    config.write_text(
        json.dumps({
            'version': 1,
            'worker': 'external',
            'roots': {'music': {'path': str(music)}},
        })
    )
    return config


def test_postgres_main_ignores_file_args(
    pg_schema, tmp_path, monkeypatch, capsys
) -> None:
    config = _config(tmp_path)
    missing = tmp_path / 'missing.db'
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'trash_worker',
            '--config',
            str(config),
            '--database',
            str(missing),
            '--auth-database',
            str(missing),
            '--data-dir',
            str(tmp_path),
        ],
    )
    trash_worker.main()
    out = json.loads(capsys.readouterr().out)
    assert out == {'processed': 0, 'succeeded': 0, 'failed': 0}


def test_postgres_main_without_file_args(
    pg_schema, tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        sys,
        'argv',
        ['trash_worker', '--config', str(_config(tmp_path))],
    )
    trash_worker.main()
    out = json.loads(capsys.readouterr().out)
    assert out == {'processed': 0, 'succeeded': 0, 'failed': 0}


def test_sqlite_main_still_requires_file_args(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        sys,
        'argv',
        ['trash_worker', '--config', str(_config(tmp_path))],
    )
    with pytest.raises(SystemExit) as excinfo:
        trash_worker.main()
    assert excinfo.value.code == 2
    assert '--database, --auth-database' in capsys.readouterr().err
