"""The Postgres monitor DDL matches the SQLite stores it mirrors.

Runs only when ``TEST_DATABASE_URL`` points at a PostgreSQL server.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path

import psycopg
import pytest

from downtify.db.migrations.schema.monitor import DDL
from downtify.monitor import PlaylistMonitorDB

DB_URL = os.environ.get('TEST_DATABASE_URL', '')

TABLES = (
    'monitored_playlists',
    'downloaded_tracks',
    'seen_albums',
    'artist_release_tracks',
    'artist_catalogue',
    'artist_catalogue_tracks',
    'download_policy',
    'watch_events',
    'watch_failures',
)

pytestmark = pytest.mark.skipif(
    not DB_URL, reason='TEST_DATABASE_URL is not set'
)


def _sqlite_columns(path: Path) -> dict[str, set[str]]:
    conn = sqlite3.connect(path)
    try:
        return {
            table: {
                row[1] for row in conn.execute(f'PRAGMA table_info({table})')
            }
            for table in TABLES
        }
    finally:
        conn.close()


@pytest.fixture
def pg_schema():
    schema = f'sc_{uuid.uuid4().hex[:8]}'
    admin = psycopg.connect(DB_URL, autocommit=True)
    try:
        admin.execute(f'CREATE SCHEMA {schema}')
        yield schema
    finally:
        admin.execute(f'DROP SCHEMA IF EXISTS {schema} CASCADE')
        admin.close()


def _pg(schema: str) -> psycopg.Connection:
    return psycopg.connect(
        DB_URL,
        autocommit=True,
        options=f'-c search_path={schema}',
    )


def test_ddl_matches_sqlite_stores(tmp_path: Path, pg_schema: str) -> None:
    sqlite_path = tmp_path / 'monitor.db'
    PlaylistMonitorDB(sqlite_path)
    expected = _sqlite_columns(sqlite_path)

    with _pg(pg_schema) as conn:
        for statement in DDL:
            conn.execute(statement)
        rows = conn.execute(
            """SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = %s""",
            (pg_schema,),
        ).fetchall()

    actual: dict[str, set[str]] = {}
    for table, column in rows:
        actual.setdefault(table, set()).add(column)

    assert set(actual) == set(TABLES)
    for table in TABLES:
        assert actual[table] == expected[table], table


def test_foreign_keys_cascade(pg_schema: str) -> None:
    with _pg(pg_schema) as conn:
        for statement in DDL:
            conn.execute(statement)
        playlist_id = conn.execute(
            """INSERT INTO monitored_playlists
            (spotify_id, name, url, created_at)
            VALUES ('p1', 'Playlist', 'https://example.test/p1', 'now')
            RETURNING id"""
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO downloaded_tracks
            (playlist_id, track_spotify_id, downloaded_at)
            VALUES (%s, 't1', 'now')""",
            (playlist_id,),
        )
        conn.execute(
            """INSERT INTO seen_albums
            (playlist_id, album_id, seen_at)
            VALUES (%s, 'a1', 'now')""",
            (playlist_id,),
        )
        conn.execute(
            """INSERT INTO artist_release_tracks
            (playlist_id, album_id, position, track_id, filename)
            VALUES (%s, 'a1', 0, 't1', 'f.mp3')""",
            (playlist_id,),
        )
        conn.execute(
            """INSERT INTO watch_failures
            (playlist_id, track_id, first_failed_at, last_failed_at)
            VALUES (%s, 't1', 'now', 'now')""",
            (playlist_id,),
        )

        conn.execute(
            'DELETE FROM monitored_playlists WHERE id = %s', (playlist_id,)
        )
        for table in (
            'downloaded_tracks',
            'seen_albums',
            'artist_release_tracks',
            'watch_failures',
        ):
            count = conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
            assert count == 0, table
