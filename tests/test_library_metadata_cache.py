"""Tests for library metadata SQLite cache."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from mutagen.id3 import ID3, TIT2, TPE1

from downtify.library_catalog import LibraryContext, list_library_entries
from downtify.library_metadata_cache import LibraryMetadataCache
from downtify.sqlite_utils import connect_sqlite


def _write_tagged_mp3(path: Path, title: str, artist: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tags = ID3()
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text=artist))
    tags.save(str(path), v2_version=3)


def test_cache_hit_skips_mutagen(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    track = download_dir / 'Artist - Song.mp3'
    _write_tagged_mp3(track, 'Cached Title', 'Cached Artist')

    cache = LibraryMetadataCache(tmp_path / 'library.db')
    cache.refresh('Artist - Song.mp3', track)

    ctx = LibraryContext(download_dir=download_dir, metadata_cache=cache)
    with patch('downtify.library_metadata.read_audio_metadata') as read_meta:
        entries = list_library_entries(ctx)
        read_meta.assert_not_called()

    assert len(entries) == 1
    assert entries[0]['title'] == 'Cached Title'
    assert entries[0]['artist'] == 'Cached Artist'


def test_cache_invalidates_when_file_changes(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    track = download_dir / 't.mp3'
    _write_tagged_mp3(track, 'Old', 'Old Artist')

    cache = LibraryMetadataCache(tmp_path / 'library.db')
    cache.refresh('t.mp3', track)

    time.sleep(0.05)
    _write_tagged_mp3(track, 'New', 'New Artist')
    entry = cache.get_entry('t.mp3', track)
    assert entry['title'] == 'New'
    assert entry['artist'] == 'New Artist'


def test_refresh_stored_path_resolves_under_slskd(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    slskd_dir = tmp_path / 'slskd'
    download_dir.mkdir()
    track = slskd_dir / 'peer' / 'x.mp3'
    _write_tagged_mp3(track, 'Slskd Title', 'Slskd Artist')

    cache = LibraryMetadataCache(tmp_path / 'library.db')
    cache.refresh_stored_path(
        'slskd/peer/x.mp3', download_dir=download_dir, slskd_dir=slskd_dir
    )
    row = cache._fetch_by_filename('slskd/peer/x.mp3')
    assert row is not None
    assert row[2] == 'Slskd Title'


def test_metadata_cache_survives_path_change(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    old_path = download_dir / 'Playlist' / 'Artist - Track.mp3'
    _write_tagged_mp3(old_path, 'Title', 'Artist')

    cache = LibraryMetadataCache(tmp_path / 'library.db')
    cache.refresh('Playlist/Artist - Track.mp3', old_path)

    new_path = download_dir / 'Artist' / 'Artist - Track.mp3'
    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_path.write_bytes(old_path.read_bytes())

    entry = cache.get_entry('Artist/Artist - Track.mp3', new_path)
    assert entry['title'] == 'Title'
    assert entry['artist'] == 'Artist'


def test_has_cover_column_migration_keeps_cached_mtime(tmp_path: Path) -> None:
    db_path = tmp_path / 'library.db'
    with connect_sqlite(str(db_path), row_factory=True) as conn:
        conn.execute("""
            CREATE TABLE library_metadata (
                content_key TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                artist TEXT NOT NULL DEFAULT '',
                album TEXT NOT NULL DEFAULT '',
                file_mtime_ns INTEGER NOT NULL,
                file_size INTEGER NOT NULL,
                cached_at TEXT NOT NULL
            )
        """)
        conn.execute(
            """INSERT INTO library_metadata
               (content_key, filename, title, artist, album,
                file_mtime_ns, file_size, cached_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ('ck1', 't.mp3', 'Title', 'Artist', '', 123456, 100, 'now'),
        )

    cache = LibraryMetadataCache(db_path)
    with cache._connect() as conn:
        row = conn.execute(
            'SELECT file_mtime_ns, has_cover FROM library_metadata WHERE content_key = ?',
            ('ck1',),
        ).fetchone()
    assert int(row['file_mtime_ns']) == 123456
    assert int(row['has_cover']) == 0
