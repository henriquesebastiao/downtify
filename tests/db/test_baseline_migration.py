from __future__ import annotations

import os
import uuid

import psycopg
import pytest

from downtify.db.core import Database
from downtify.db.migrations.runner import run_migrations

_TEST_URL_ENV = 'TEST_DATABASE_URL'

_EXPECTED_TABLES = (
    'users',
    'activity',
    'audio_hashes',
    'monitored_playlists',
    'library_tracks',
    'playlist_tracks',
    'liked_tracks',
    'library_trash',
    'sync_tracks',
    'podcast_shows',
)


@pytest.fixture
def pg_schema():
    url = os.environ.get(_TEST_URL_ENV)
    if not url:
        pytest.skip(f'{_TEST_URL_ENV} not set')
    schema = f'sc_{uuid.uuid4().hex[:8]}'
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(f'create schema {schema}')
    try:
        yield url, schema
    finally:
        with psycopg.connect(url, autocommit=True) as admin:
            admin.execute(f'drop schema if exists {schema} cascade')


def test_baseline_applies_all_tables(pg_schema):
    url, schema = pg_schema
    db = Database.postgres(url, search_path=schema, max_size=4)
    assert run_migrations(db) == [1]

    with db.connect() as conn:
        for table in _EXPECTED_TABLES:
            row = conn.execute(
                'select to_regclass(?) is not null', (table,)
            ).fetchone()
            assert row[0], f'missing table {table}'
        seq = conn.execute("select nextval('library_sync_seq')").fetchone()
        assert seq[0] is not None


def test_baseline_is_idempotent_on_rerun(pg_schema):
    url, schema = pg_schema
    db = Database.postgres(url, search_path=schema, max_size=4)
    assert run_migrations(db) == [1]
    assert run_migrations(db) == []
