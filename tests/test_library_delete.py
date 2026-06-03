"""Tests for library file and playlist deletion."""

from __future__ import annotations

from pathlib import Path

from downtify.library_catalog import LibraryContext, PlaylistCatalog
from downtify.library_delete import (
    delete_library_file,
    delete_playlist_from_library,
)
from downtify.track_index import TrackIndex


class _DeleteState:
    cover_cache = None
    metadata_cache = None
    track_index = None
    navidrome_index = None

    def __init__(self, catalog: PlaylistCatalog, index: TrackIndex) -> None:
        self.playlist_catalog = catalog
        self.track_index = index


def test_delete_library_file(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    track = download_dir / 'Artist - Song.mp3'
    track.parent.mkdir(parents=True)
    track.write_bytes(b'audio')

    ctx = LibraryContext(download_dir=download_dir)
    result = delete_library_file('Artist - Song.mp3', ctx)
    assert result.get('deleted') is True
    assert not track.is_file()


def test_delete_playlist_from_library(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    pl_dir = download_dir / 'My Playlist'
    pl_dir.mkdir(parents=True)
    t1 = pl_dir / 'A - One.mp3'
    t2 = pl_dir / 'B - Two.mp3'
    t1.write_bytes(b'1')
    t2.write_bytes(b'2')

    db = tmp_path / 'lib.db'
    catalog = PlaylistCatalog(db)
    catalog.ensure_playlist('My Playlist')
    catalog.upsert_track(
        'My Playlist',
        {'song_id': '4uLU6hMCjMI75M1A2tKUQC'},
        'My Playlist/A - One.mp3',
        t1,
    )
    catalog.upsert_track(
        'My Playlist',
        {'song_id': '1Je8F2j4RrcXdon8X0JPB'},
        'My Playlist/B - Two.mp3',
        t2,
    )

    state = _DeleteState(catalog, TrackIndex(db))
    settings = {'organize_by_artist': False, 'generate_m3u': False}
    result = delete_playlist_from_library(
        'My Playlist',
        download_dir,
        settings,
        state,
    )
    assert result.get('ok') is True
    assert result['deleted_count'] == 2
    assert not t1.is_file()
    assert not t2.is_file()
    assert catalog.list_tracks('My Playlist') == []
