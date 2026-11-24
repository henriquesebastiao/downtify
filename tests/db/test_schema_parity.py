"""The single Postgres baseline covers every table the server's SQLite files.

Builds every store the server opens at startup on SQLite files named like
production, applies ``0001_baseline`` to a fresh Postgres schema, and checks
that each SQLite table exists there with all of its columns. Runs only when
``TEST_DATABASE_URL`` points at a PostgreSQL server.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg import sql

from downtify.activity import ActivityLog
from downtify.auth import AuthStore
from downtify.compilation import CompilationMarks
from downtify.db.core import Database
from downtify.db.migrations.runner import run_migrations
from downtify.deemix_upgrade_store import AudioReplacementStore
from downtify.discover import DiscoverStore
from downtify.doctor_audio import AudioHashCache
from downtify.download_log import DownloadLog
from downtify.download_queue import PendingDownloads
from downtify.download_sources import DownloadSources
from downtify.duplicate_merge import KeptApart
from downtify.external_playlists import ExternalPlaylistImports
from downtify.file_providers import FileProviders
from downtify.hand_replaced import HandReplacedFiles
from downtify.library_listing_store import LibraryListingStore
from downtify.library_metadata_cache import LibraryMetadataCache
from downtify.library_sync import LibrarySync
from downtify.library_trash import LibraryTrash, TrashRoot
from downtify.library_upgrade_db import LibraryUpgradeDB
from downtify.library_usage import UsageSnapshots
from downtify.library_visibility import LibraryVisibility
from downtify.likes import LikedTracks
from downtify.loudness import LoudnessAnalyzer
from downtify.lyrics_cache import LyricsLookupCache
from downtify.monitor import PlaylistMonitorDB
from downtify.music_video import MusicVideos
from downtify.navidrome_index import NavidromeIndex
from downtify.playlist_batches import PlaylistBatchStore
from downtify.playlist_catalog import ManualPlaylistOwners, PlaylistCatalog
from downtify.playlist_hidden import PlaylistHiddenSongs
from downtify.playlist_shares import PlaylistShares
from downtify.playlist_spotify_cache import PlaylistSpotifyCache
from downtify.podcasts import PodcastStore
from downtify.slskd_misses import SlskdMisses
from downtify.storage_quota import StorageQuotas
from downtify.track_index import TrackIndex
from downtify.track_owners import TrackOwners
from downtify.traffic import TrafficCounters

_URL_ENV = 'TEST_DATABASE_URL'
_MIGRATION_TABLE = 'schema_migrations'

# Columns that exist only in Postgres, standing in for SQLite's rowid.
_ROWID_COLUMN = 'id'

# Stores whose constructor takes only the library database path. They all
# share downtify_library.db, as in main.py:_open_library_stores.
_LIBRARY_STORES: tuple[Callable[[Path], Any], ...] = (
    TrackIndex,
    NavidromeIndex,
    LibraryMetadataCache,
    LibraryListingStore,
    PlaylistCatalog,
    ManualPlaylistOwners,
    PlaylistShares,
    PlaylistHiddenSongs,
    FileProviders,
    HandReplacedFiles,
    DownloadSources,
    DownloadLog,
    SlskdMisses,
    UsageSnapshots,
    ExternalPlaylistImports,
    PlaylistBatchStore,
    PendingDownloads,
    PlaylistSpotifyCache,
    LyricsLookupCache,
    LikedTracks,
    TrackOwners,
    StorageQuotas,
    MusicVideos,
    LibraryVisibility,
    CompilationMarks,
    PodcastStore,
    LibrarySync,
    DiscoverStore,
    LibraryUpgradeDB,
    AudioReplacementStore,
)


def _build_sqlite(root: Path) -> dict[str, Path]:
    """Open every store the server builds, on files named as in production.

    Returns the six SQLite files keyed by their path relative to the data
    directory.
    """

    data = root / 'data'
    doctor = data / 'doctor'
    downloads = root / 'downloads'
    doctor.mkdir(parents=True)
    downloads.mkdir()
    library = data / 'downtify_library.db'
    monitor = data / 'downtify_monitor.db'
    auth = data / 'downtify_auth.db'
    activity = data / 'downtify_activity.db'
    audio = doctor / 'audio_hashes.db'
    kept = doctor / 'duplicates.db'

    for store in _LIBRARY_STORES:
        store(library)
    LoudnessAnalyzer(library, lambda: None)
    TrafficCounters(library)
    # Only built when the operator turns the music trash on, but its tables
    # belong to the baseline all the same.
    LibraryTrash(library, {'downloads': TrashRoot(downloads)})
    PlaylistMonitorDB(monitor)
    AuthStore(auth, data / '.auth_secret')
    ActivityLog(activity)
    AudioHashCache(audio)
    KeptApart(kept)

    return {
        'downtify_library.db': library,
        'downtify_monitor.db': monitor,
        'downtify_auth.db': auth,
        'downtify_activity.db': activity,
        'doctor/audio_hashes.db': audio,
        'doctor/duplicates.db': kept,
    }


def _sqlite_tables(path: Path) -> dict[str, set[str]]:
    """Every user table in *path* with its column names."""

    with closing(sqlite3.connect(path)) as conn:
        names = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND substr(name, 1, 7) <> 'sqlite_'"
            )
        ]
        return {
            name: {
                str(row[1])
                for row in conn.execute(f'PRAGMA table_info("{name}")')
            }
            for name in names
        }


def _pg_tables(db: Database, schema: str) -> dict[str, set[str]]:
    """Every table in *schema* with its columns, minus the migration log."""

    with db.connect() as conn:
        rows = conn.execute(
            'select table_name, column_name '
            'from information_schema.columns '
            'where table_schema = ?',
            (schema,),
        ).fetchall()
    tables: dict[str, set[str]] = {}
    for table, column in rows:
        if table == _MIGRATION_TABLE:
            continue
        tables.setdefault(table, set()).add(column)
    return tables


@pytest.mark.skipif(
    not os.environ.get(_URL_ENV),
    reason=f'{_URL_ENV} not set',
)
def test_baseline_covers_every_sqlite_table(tmp_path: Path) -> None:
    url = os.environ[_URL_ENV]
    sqlite_files = {
        name: _sqlite_tables(path)
        for name, path in _build_sqlite(tmp_path).items()
    }
    sqlite_union = {
        table for tables in sqlite_files.values() for table in tables
    }

    schema = f'sc_{uuid.uuid4().hex[:8]}'
    with closing(psycopg.connect(url, autocommit=True)) as admin:
        admin.execute(
            sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema))
        )
    try:
        db = Database.postgres(url, search_path=schema, max_size=4)
        try:
            run_migrations(db)
            pg_tables = _pg_tables(db, schema)
        finally:
            db.close()
    finally:
        with closing(psycopg.connect(url, autocommit=True)) as admin:
            admin.execute(
                sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(
                    sql.Identifier(schema)
                )
            )

    # (1) Every SQLite table, from any of the six files, exists in Postgres.
    missing = sorted(sqlite_union - set(pg_tables))
    assert not missing, f'SQLite tables missing from baseline: {missing}'

    # (2) Per file, each SQLite table's columns are in Postgres, and the only
    # extra Postgres column is the rowid stand-in ``id``.
    problems: list[str] = []
    for file_name, tables in sorted(sqlite_files.items()):
        for table, columns in sorted(tables.items()):
            pg_columns = pg_tables[table]
            absent = sorted(columns - pg_columns)
            if absent:
                problems.append(f'{file_name}:{table} lacks columns {absent}')
            extra = sorted(pg_columns - columns - {_ROWID_COLUMN})
            if extra:
                problems.append(
                    f'{file_name}:{table} has extra Postgres columns {extra}'
                )
    assert not problems, '\n'.join(problems)

    # (3) No Postgres table exists that no SQLite store creates.
    stray = sorted(set(pg_tables) - sqlite_union)
    assert not stray, f'Postgres tables no SQLite store creates: {stray}'
