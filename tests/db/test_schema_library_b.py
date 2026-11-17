from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path

import psycopg
import pytest

from downtify.compilation import CompilationMarks
from downtify.db.migrations.schema.library_b import DDL
from downtify.deemix_upgrade_store import AudioReplacementStore
from downtify.discover import DiscoverStore
from downtify.library_sync import LibrarySync
from downtify.library_trash import LibraryTrash, TrashRoot
from downtify.library_upgrade_db import LibraryUpgradeDB
from downtify.library_visibility import LibraryVisibility
from downtify.likes import LikedTracks
from downtify.lyrics_cache import LyricsLookupCache
from downtify.playlist_spotify_cache import PlaylistSpotifyCache
from downtify.podcasts import PodcastStore
from downtify.track_owners import TrackOwners

# Columns SQLite gets from the rowid, which the stores order by. The Postgres
# DDL carries them as an extra identity column.
ROWID_COLUMNS = {
    'liked_tracks': {'id'},
    'track_owners': {'id'},
    'hidden_library_items': {'id'},
}


def _sqlite_stores(root: Path) -> Path:
    """Instantiate every library store on SQLite files under ``root``."""
    db = root / 'library.db'
    for store in (
        PlaylistSpotifyCache,
        LyricsLookupCache,
        LikedTracks,
        TrackOwners,
        LibraryVisibility,
        CompilationMarks,
        PodcastStore,
        LibrarySync,
        DiscoverStore,
        LibraryUpgradeDB,
        AudioReplacementStore,
    ):
        store(db)
    LibraryTrash(db, {'main': TrashRoot(root / 'trash', '', '')})
    return db


def _sqlite_columns(db: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    conn = sqlite3.connect(db)
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        ]
        for table in tables:
            cols = conn.execute(f'PRAGMA table_info({table})').fetchall()
            result[table] = {row[1] for row in cols}
    finally:
        conn.close()
    return result


@pytest.mark.skipif(
    not os.environ.get('TEST_DATABASE_URL'),
    reason='TEST_DATABASE_URL not set',
)
def test_library_b_ddl_matches_sqlite(tmp_path: Path) -> None:
    url = os.environ['TEST_DATABASE_URL']
    expected = _sqlite_columns(_sqlite_stores(tmp_path))
    schema = f'sc_{uuid.uuid4().hex[:8]}'

    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(f'CREATE SCHEMA {schema}')
    try:
        with psycopg.connect(
            url,
            autocommit=True,
            options=f'-c search_path={schema}',
        ) as conn:
            for statement in DDL:
                conn.execute(statement)

            rows = conn.execute(
                'SELECT table_name, column_name '
                'FROM information_schema.columns '
                'WHERE table_schema = %s',
                (schema,),
            ).fetchall()
            actual: dict[str, set[str]] = {}
            for table, column in rows:
                actual.setdefault(table, set()).add(column)

            assert set(actual) == set(expected)
            for table, columns in expected.items():
                extra = ROWID_COLUMNS.get(table, set())
                assert actual[table] - extra == columns, table
                assert extra <= actual[table], table

            value = conn.execute(
                "SELECT nextval('library_sync_seq')"
            ).fetchone()
            assert value is not None
    finally:
        with psycopg.connect(url, autocommit=True) as admin:
            admin.execute(f'DROP SCHEMA IF EXISTS {schema} CASCADE')
