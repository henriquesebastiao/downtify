from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path

import psycopg
import pytest

from downtify.db.migrations.schema.library_a import DDL
from downtify.download_log import DownloadLog
from downtify.download_queue import PendingDownloads
from downtify.external_playlists import ExternalPlaylistImports
from downtify.file_providers import FileProviders
from downtify.hand_replaced import HandReplacedFiles
from downtify.library_listing_store import LibraryListingStore
from downtify.library_metadata_cache import LibraryMetadataCache
from downtify.library_usage import UsageSnapshots
from downtify.loudness import LoudnessAnalyzer
from downtify.navidrome_index import NavidromeIndex
from downtify.playlist_batches import PlaylistBatchStore
from downtify.playlist_catalog import PlaylistCatalog
from downtify.playlist_hidden import PlaylistHiddenSongs
from downtify.playlist_shares import PlaylistShares
from downtify.track_index import TrackIndex

TEST_DATABASE_URL = os.environ.get('TEST_DATABASE_URL')

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason='TEST_DATABASE_URL is not set',
)

# Columns that exist only in Postgres to replace SQLite's implicit rowid.
_EXTRA_PG_COLUMNS = {('playlist_hidden_songs', 'id')}

# Store classes whose constructor takes only a database path.
_STORES = [
    TrackIndex,
    NavidromeIndex,
    LibraryMetadataCache,
    LibraryListingStore,
    PlaylistCatalog,
    PlaylistShares,
    PlaylistHiddenSongs,
    FileProviders,
    HandReplacedFiles,
    DownloadLog,
    UsageSnapshots,
    ExternalPlaylistImports,
    PlaylistBatchStore,
    PendingDownloads,
]


def _build_sqlite_stores(root: Path) -> Path:
    path = root / 'library_a.db'
    for store in _STORES:
        store(path)
    LoudnessAnalyzer(path, lambda: None)
    return path


def _sqlite_columns(path: Path) -> dict[str, set[str]]:
    conn = sqlite3.connect(path)
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        ]
        return {
            table: {
                str(row[1])
                for row in conn.execute(f'PRAGMA table_info("{table}")')
            }
            for table in tables
        }
    finally:
        conn.close()


def test_library_a_ddl_matches_sqlite(tmp_path: Path) -> None:
    expected = _sqlite_columns(_build_sqlite_stores(tmp_path))
    schema = f'sc_{uuid.uuid4().hex[:8]}'

    admin = psycopg.connect(TEST_DATABASE_URL, autocommit=True)
    try:
        admin.execute(f'CREATE SCHEMA "{schema}"')
        try:
            conn = psycopg.connect(
                TEST_DATABASE_URL,
                autocommit=True,
                options=f'-c search_path={schema}',
            )
            try:
                for statement in DDL:
                    conn.execute(statement)
                rows = conn.execute(
                    'SELECT table_name, column_name '
                    'FROM information_schema.columns '
                    'WHERE table_schema = %s',
                    (schema,),
                ).fetchall()
            finally:
                conn.close()
        finally:
            admin.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
    finally:
        admin.close()

    actual: dict[str, set[str]] = {}
    for table, column in rows:
        if (table, column) in _EXTRA_PG_COLUMNS:
            continue
        actual.setdefault(table, set()).add(column)

    assert set(actual) == set(expected)
    for table, columns in expected.items():
        assert actual[table] == columns, table
