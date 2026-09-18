"""Tests for library file and playlist deletion."""

from __future__ import annotations

from pathlib import Path

from downtify.library_catalog import LibraryContext, PlaylistCatalog
from downtify.library_delete import (
    TagMismatchDeleteContext,
    delete_if_spotify_tag_mismatch,
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


def test_delete_library_file_removes_leftovers_like_delete_endpoint(
    tmp_path: Path,
) -> None:
    # Same cleanup as DELETE /delete: the .lrc sidecar goes, and so does
    # the folder once nothing is left in it (never the downloads root).
    download_dir = tmp_path / 'downloads'
    pl_dir = download_dir / 'My Playlist'
    pl_dir.mkdir(parents=True)
    track = pl_dir / 'Artist - Song.mp3'
    track.write_bytes(b'audio')
    (pl_dir / 'Artist - Song.lrc').write_text('lyrics', encoding='utf-8')

    ctx = LibraryContext(download_dir=download_dir)
    result = delete_library_file('My Playlist/Artist - Song.mp3', ctx)

    assert result.get('deleted') is True
    assert not pl_dir.exists()
    assert download_dir.is_dir()


def test_delete_library_file_prunes_slskd_folders_within_slskd_root(
    tmp_path: Path,
) -> None:
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    slskd_dir = tmp_path / 'slskd'
    user_dir = slskd_dir / 'user' / 'Album'
    user_dir.mkdir(parents=True)
    track = user_dir / 'Artist - Song.flac'
    track.write_bytes(b'audio')

    ctx = LibraryContext(download_dir=download_dir, slskd_dir=slskd_dir)
    result = delete_library_file('slskd/user/Album/Artist - Song.flac', ctx)

    assert result.get('deleted') is True
    assert not (slskd_dir / 'user').exists()
    assert slskd_dir.is_dir()


def test_delete_if_spotify_tag_mismatch(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    pl_dir = download_dir / 'My Playlist'
    pl_dir.mkdir(parents=True)
    wrong = pl_dir / 'Noizy - 100 Kile.mp3'
    wrong.write_bytes(b'audio')

    db = tmp_path / 'lib.db'
    catalog = PlaylistCatalog(db)
    catalog.ensure_playlist('My Playlist')
    catalog.upsert_track(
        'My Playlist',
        {
            'song_id': '4uLU6hMCjMI75M1A2tKUQC',
            'name': '100 Kile',
            'artists': ['Noizy'],
        },
        'My Playlist/Noizy - 100 Kile.mp3',
        wrong,
    )

    ctx = LibraryContext(download_dir=download_dir, playlist_catalog=catalog)
    song = {
        'spotify_name': '100 Kile',
        'spotify_artists': ['Noizy'],
        'name': '100',
        'artists': ['Ledri Vula', 'Lyrical Son', 'Singi'],
        'filename': 'My Playlist/Noizy - 100 Kile.mp3',
        'library_from_tags': True,
    }
    del_ctx = TagMismatchDeleteContext(ctx=ctx, playlist_catalog=catalog)
    assert delete_if_spotify_tag_mismatch(
        song, del_ctx, playlist_name='My Playlist'
    )
    assert not wrong.is_file()
    assert catalog.list_tracks('My Playlist') == []


def test_delete_playlist_from_library(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    pl_dir = download_dir / 'My Playlist'
    pl_dir.mkdir(parents=True)
    t1 = pl_dir / 'A - One.mp3'
    t2 = pl_dir / 'B - Two.mp3'
    t1.write_bytes(b'1')
    t2.write_bytes(b'2')
    (pl_dir / 'My Playlist.m3u').write_text('#EXTM3U\n', encoding='utf-8')
    cover = pl_dir / 'My Playlist.jpg'
    cover.write_bytes(b'cover-bytes')

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
    assert not cover.is_file()
    assert catalog.list_tracks('My Playlist') == []
    # Folder is gone too: tracks, the M3U and the cover art were its
    # only contents.
    assert not pl_dir.exists()


def test_delete_playlist_removes_cover_from_playlists_dir_when_organized(
    tmp_path: Path,
) -> None:
    # With organize-by-artist on, tracks live in artist folders but the
    # M3U (and its cover, saved alongside it — see
    # downloader.save_playlist_cover) goes to the legacy Playlists/ dir.
    download_dir = tmp_path / 'downloads'
    artist_dir = download_dir / 'A'
    artist_dir.mkdir(parents=True)
    track = artist_dir / 'A - One.mp3'
    track.write_bytes(b'1')

    playlists_dir = download_dir / 'Playlists'
    playlists_dir.mkdir()
    (playlists_dir / 'My Playlist.m3u').write_text(
        '#EXTM3U\n', encoding='utf-8'
    )
    cover = playlists_dir / 'My Playlist.jpg'
    cover.write_bytes(b'cover-bytes')

    db = tmp_path / 'lib.db'
    catalog = PlaylistCatalog(db)
    catalog.ensure_playlist('My Playlist')
    catalog.upsert_track(
        'My Playlist',
        {'song_id': '4uLU6hMCjMI75M1A2tKUQC'},
        'A/A - One.mp3',
        track,
    )

    state = _DeleteState(catalog, TrackIndex(db))
    settings = {'organize_by_artist': True, 'generate_m3u': False}
    result = delete_playlist_from_library(
        'My Playlist',
        download_dir,
        settings,
        state,
    )

    assert result.get('ok') is True
    assert not cover.is_file()
    assert not (playlists_dir / 'My Playlist.m3u').is_file()
    # The cover was the last thing in Playlists/, so it's pruned too.
    assert not playlists_dir.exists()


def test_delete_playlist_spares_same_named_album_folder_when_organized_by_album(
    tmp_path: Path,
) -> None:
    # With organize-by-album on, a folder named like the playlist is an
    # album's folder, not the playlist's: only the playlist's own tracks
    # (from the catalog) may be deleted.
    download_dir = tmp_path / 'downloads'
    album_dir = download_dir / 'Summer'
    album_dir.mkdir(parents=True)
    playlist_track = album_dir / 'A - In Playlist.mp3'
    album_only = album_dir / 'B - Album Only.mp3'
    playlist_track.write_bytes(b'1')
    album_only.write_bytes(b'2')

    db = tmp_path / 'lib.db'
    catalog = PlaylistCatalog(db)
    catalog.ensure_playlist('Summer')
    catalog.upsert_track(
        'Summer',
        {'song_id': '4uLU6hMCjMI75M1A2tKUQC'},
        'Summer/A - In Playlist.mp3',
        playlist_track,
    )

    result = delete_playlist_from_library(
        'Summer',
        download_dir,
        {'organize_by_album': True, 'generate_m3u': False},
        _DeleteState(catalog, TrackIndex(db)),
    )

    assert result.get('ok') is True
    assert not playlist_track.is_file()
    assert album_only.is_file()
