"""Tests for library path reconciliation."""

from __future__ import annotations

from pathlib import Path

from downtify.library_catalog import LibraryContext
from downtify.library_reconcile import (
    build_disk_content_index,
    reconcile_library_paths,
)
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex


def test_reconcile_updates_stale_path(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    data = b'x' * 100
    old = download_dir / 'Playlist' / 'Artist - Song.mp3'
    new = download_dir / 'Artist' / 'Artist - Song.mp3'
    old.parent.mkdir(parents=True)
    new.parent.mkdir(parents=True)
    old.write_bytes(data)
    new.write_bytes(data)

    library_db = tmp_path / 'library.db'
    index = TrackIndex(library_db)
    index.register(
        '4uLU6hMCjMI75M1A2tKUQC', 'Playlist/Artist - Song.mp3', full_path=old
    )

    catalog = PlaylistCatalog(library_db)
    catalog.replace_playlist_tracks(
        'My List',
        [
            (
                {'song_id': '4uLU6hMCjMI75M1A2tKUQC'},
                'Playlist/Artist - Song.mp3',
                old,
            )
        ],
    )

    ctx = LibraryContext(download_dir=download_dir)
    old.unlink()
    count, affected = reconcile_library_paths(
        ctx, track_index=index, playlist_catalog=catalog
    )
    assert count >= 1
    assert 'My List' in affected
    assert index.lookup('4uLU6hMCjMI75M1A2tKUQC') == 'Artist/Artist - Song.mp3'
    assert (
        catalog.list_tracks('My List')[0]['filename']
        == 'Artist/Artist - Song.mp3'
    )


def test_build_disk_content_index(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    track = download_dir / 'a.mp3'
    track.parent.mkdir(parents=True)
    track.write_bytes(b'xyz')
    ctx = LibraryContext(download_dir=download_dir)
    index = build_disk_content_index(ctx)
    assert len(index) == 1
    assert list(index.values())[0] == 'a.mp3'
