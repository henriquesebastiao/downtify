"""Tests for playlist catalog batch lookups and cleanup."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from downtify.library_catalog import LibraryContext, list_library_entries
from downtify.library_metadata_cache import LibraryMetadataCache
from downtify.library_reconcile import prune_stale_and_backfill
from downtify.playlist_catalog import PlaylistCatalog


def test_playlists_on_list_entries(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    track = download_dir / 'Artist - Song.mp3'
    track.write_bytes(b'audio-data-here')

    db = tmp_path / 'library.db'
    catalog = PlaylistCatalog(db)
    catalog.replace_playlist_tracks(
        'Road Mix',
        [({'song_id': '4uLU6hMCjMI75M1A2tKUQC'}, 'Artist - Song.mp3', track)],
    )

    cache = LibraryMetadataCache(db)
    cache.refresh('Artist - Song.mp3', track)
    ctx = LibraryContext(
        download_dir=download_dir,
        metadata_cache=cache,
        playlist_catalog=catalog,
    )
    entries = list_library_entries(ctx)
    assert len(entries) == 1
    assert entries[0]['playlists'] == ['Road Mix']


def test_backfill_from_monitor_db(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    track = download_dir / 'Artist - Song.mp3'
    track.write_bytes(b'audio')

    monitor_db = tmp_path / 'monitor.db'
    with sqlite3.connect(monitor_db) as conn:
        conn.executescript("""
            CREATE TABLE monitored_playlists (
                id INTEGER PRIMARY KEY,
                spotify_id TEXT NOT NULL,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                interval_minutes INTEGER DEFAULT 60,
                enabled INTEGER DEFAULT 1,
                last_checked TEXT,
                last_track_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE downloaded_tracks (
                id INTEGER PRIMARY KEY,
                playlist_id INTEGER NOT NULL,
                track_spotify_id TEXT NOT NULL,
                downloaded_at TEXT NOT NULL,
                filename TEXT
            );
            INSERT INTO monitored_playlists VALUES (
                1, 'playlist12345678901234567890', 'Old Mix', 'http://x', 60, 1, NULL, 0, 'now'
            );
            INSERT INTO downloaded_tracks VALUES (
                1, 1, '4uLU6hMCjMI75M1A2tKUQC', 'now', 'Artist - Song.mp3'
            );
        """)

    catalog = PlaylistCatalog(tmp_path / 'library.db')
    count = catalog.backfill_from_monitor_db(
        monitor_db, download_dir=download_dir
    )
    assert count == 1
    assert catalog.list_tracks('Old Mix')[0]['filename'] == 'Artist - Song.mp3'


def test_prune_stale_playlist_row(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    db = tmp_path / 'library.db'
    catalog = PlaylistCatalog(db)
    song = {'song_id': '4uLU6hMCjMI75M1A2tKUQC'}
    missing = download_dir / 'gone.mp3'
    catalog.upsert_track('My List', song, 'gone.mp3', missing)

    ctx = LibraryContext(download_dir=download_dir)
    pruned, _backfilled, affected = prune_stale_and_backfill(
        ctx, playlist_catalog=catalog
    )
    assert pruned == 1
    assert 'My List' in affected
    assert catalog.list_tracks('My List') == []
