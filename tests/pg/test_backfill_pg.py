"""Startup backfills read the monitor history from its own Database.

The monitor, track index and playlist catalog share one ``backend_db``
here, so the same results must come out on SQLite and PostgreSQL.
"""

from __future__ import annotations

from pathlib import Path

from downtify.monitor import PlaylistMonitorDB
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex

PLAYLIST = 'playlist12345678901234567890'
TID_A = '4uLU6hMCjMI75M1A2tKUQC'
TID_B = '1x00000000000000000000'
TID_C = '2y00000000000000000000'


def _audio(directory: Path, name: str) -> None:
    (directory / name).write_bytes(b'audio')


def test_backfills_import_from_the_monitor_database(
    backend_db, tmp_path: Path
) -> None:
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    _audio(download_dir, 'Artist - Song.mp3')
    _audio(download_dir, 'Artist - Other.mp3')

    monitor = PlaylistMonitorDB(backend_db)
    watch = monitor.add_playlist(PLAYLIST, 'Old Mix', 'http://x')
    monitor.mark_track_downloaded(watch.id, TID_A, 'Artist - Song.mp3')
    monitor.mark_track_downloaded(watch.id, TID_B, 'Artist - Other.mp3')
    # No filename: the backfills must skip it.
    monitor.mark_track_downloaded(watch.id, TID_C)

    index = TrackIndex(backend_db)
    assert index.backfill_from_monitor_db(backend_db) == 2
    assert index.lookup(TID_A) == 'Artist - Song.mp3'
    assert index.lookup(TID_B) == 'Artist - Other.mp3'
    assert index.lookup(TID_C) is None
    # Second run: nothing new to import.
    assert index.backfill_from_monitor_db(backend_db) == 0

    catalog = PlaylistCatalog(backend_db)
    assert (
        catalog.backfill_from_monitor_db(backend_db, download_dir=download_dir)
        == 2
    )
    assert catalog.list_playlist_names() == ['Old Mix']
    filenames = sorted(
        row['filename'] for row in catalog.list_tracks('Old Mix')
    )
    assert filenames == ['Artist - Other.mp3', 'Artist - Song.mp3']
    # Run again: membership rows are replaced, not duplicated.
    catalog.backfill_from_monitor_db(backend_db, download_dir=download_dir)
    assert len(catalog.list_tracks('Old Mix')) == 2
    assert catalog.spotify_id_for_playlist('Old Mix') == PLAYLIST
