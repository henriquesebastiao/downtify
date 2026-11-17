from __future__ import annotations

import argparse
import os
import sys
import uuid

import psycopg
import pytest
from loguru import logger

import main
from downtify.activity import ActivityLog
from downtify.db import runtime

_TEST_URL_ENV = 'TEST_DATABASE_URL'


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('DB_SEARCH_PATH', raising=False)
    yield
    runtime.shutdown()


@pytest.fixture
def captured_logs():
    records: list[str] = []
    sink_id = logger.add(
        lambda message: records.append(str(message)), level='DEBUG'
    )
    yield records
    logger.remove(sink_id)


def _namespace(**overrides) -> argparse.Namespace:
    values = {'from_sqlite': '', 'to': '', 'force': False}
    values.update(overrides)
    return argparse.Namespace(**values)


def test_db_migrate_without_url_exits_1_and_hides_nothing(
    monkeypatch, tmp_path, captured_logs
):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    status = main._db_migrate(_namespace(from_sqlite=str(tmp_path), to=''))
    assert status == 1
    text = '\n'.join(captured_logs)
    assert 'DATABASE_URL' in text
    assert 'secret' not in text


def test_db_migrate_parser_reads_flags(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'main.py',
            'db-migrate',
            '--from-sqlite',
            str(tmp_path),
            '--to',
            'postgresql://u:secret@localhost:1/db',
            '--force',
        ],
    )
    args = main._parse_args()
    assert args.mode == 'db-migrate'
    assert args.from_sqlite == str(tmp_path)
    assert args.to == 'postgresql://u:secret@localhost:1/db'
    assert args.force is True


def _pg_schema(monkeypatch):
    url = os.environ.get(_TEST_URL_ENV)
    if not url:
        pytest.skip(f'{_TEST_URL_ENV} not set')
    schema = f'mig_{uuid.uuid4().hex[:8]}'
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(f'create schema {schema}')
    monkeypatch.setenv('DB_SEARCH_PATH', schema)
    return url, schema


def _drop_schema(url, schema):
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(f'drop schema if exists {schema} cascade')


def _count_activity(url, schema) -> int:
    with psycopg.connect(url) as conn:
        conn.execute(f'set search_path to {schema}')
        row = conn.execute('select count(*) from activity').fetchone()
        return int(row[0])


def _sqlite_install(tmp_path):
    ActivityLog(tmp_path / 'downtify_activity.db').record(
        'test', summary='one entry'
    )


def test_db_migrate_end_to_end(monkeypatch, tmp_path, capsys):
    url, schema = _pg_schema(monkeypatch)
    try:
        _sqlite_install(tmp_path)
        monkeypatch.setattr(
            sys,
            'argv',
            [
                'main.py',
                'db-migrate',
                '--from-sqlite',
                str(tmp_path),
                '--to',
                url,
            ],
        )
        args = main._parse_args()
        assert main._db_migrate(args) == 0
        assert (tmp_path / 'MIGRATED_TO_POSTGRES').exists()
        assert _count_activity(url, schema) == 1
        assert 'activity' in capsys.readouterr().out

        assert main._db_migrate(args) == 1
        assert _count_activity(url, schema) == 1

        forced = _namespace(from_sqlite=str(tmp_path), to=url, force=True)
        assert main._db_migrate(forced) == 0
        assert _count_activity(url, schema) == 1
    finally:
        runtime.shutdown()
        _drop_schema(url, schema)


def test_startup_warning_when_marker_and_sqlite_mode(
    monkeypatch, tmp_path, captured_logs
):
    monkeypatch.setenv('DATABASE_DIR', str(tmp_path))
    (tmp_path / 'MIGRATED_TO_POSTGRES').write_text('x')
    main._warn_if_migrated_to_sqlite()
    text = '\n'.join(captured_logs)
    assert 'migrated to PostgreSQL' in text
    assert 'DATABASE_URL' in text


def test_no_startup_warning_without_marker(
    monkeypatch, tmp_path, captured_logs
):
    monkeypatch.setenv('DATABASE_DIR', str(tmp_path))
    main._warn_if_migrated_to_sqlite()
    assert not captured_logs
