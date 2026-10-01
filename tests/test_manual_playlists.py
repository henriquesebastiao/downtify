"""User-created playlists in the Library, stored as marked M3U files."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from mutagen.id3 import APIC, ID3, TIT2, TPE1

from downtify.library_catalog import LibraryContext
from downtify.library_paths import library_stored_path
from downtify.likes import LIKED_PLAYLIST_NAME
from downtify.m3u import MANUAL_M3U_MARKER, is_manual_m3u, write_m3u
from downtify.manual_playlists import (
    ManualPlaylistError,
    create_manual_playlist,
    drop_manual_playlist,
    edit_manual_playlist,
    prune_files_from_manual_playlists,
    rename_manual_playlist,
)
from downtify.playlist_listing import list_library_playlists
from downtify.playlist_mosaic import _filter_complex, unique_cover_images

_JPEG = bytes.fromhex(
    'ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707'
    '070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c'
    '1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100'
    'ffc4001f0000010501010101010100000000000000000102030405060708090a0bff'
    'c400b5100002010303020403050504040000017d01020300041105122131410613'
    '516107227114328191a1082342b1c11552d1f02433627282090a161718191a2526'
    '2728292a3435363738393a434445464748494a535455565758595a636465666768'
    '696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7'
    'a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3'
    'e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda0008010100003f00fbd3ffd9'
)


def _jpeg(tag: bytes) -> bytes:
    comment = b'\xff\xfe' + (len(tag) + 2).to_bytes(2, 'big') + tag
    return b'\xff\xd8' + comment + _JPEG[2:]


def _mp3(
    path: Path, *, title: str, artist: str, cover: bytes | None = None
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tags = ID3()
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text=artist))
    if cover:
        tags.add(
            APIC(encoding=3, mime='image/jpeg', type=3, desc='', data=cover)
        )
    tags.save(str(path), v2_version=3)


def test_create_empty_manual_playlist(tmp_path):
    download = tmp_path / 'downloads'
    download.mkdir()
    ctx = LibraryContext(download_dir=download)
    result = create_manual_playlist(ctx, 'Late night')
    path = download / 'Playlists' / 'Late night.m3u'
    assert result['manual'] is True
    assert result['count'] == 0
    assert path.is_file()
    assert is_manual_m3u(path)
    assert MANUAL_M3U_MARKER in path.read_text(encoding='utf-8')
    listed = list_library_playlists(download)
    assert listed[0]['name'] == 'Late night'
    assert listed[0]['manual'] is True
    assert listed[0]['files'] == []
    assert listed[0]['added'] > 0


def test_add_downloaded_and_extra_tracks(tmp_path):
    download = tmp_path / 'downloads'
    extra = tmp_path / 'ripped'
    download.mkdir()
    native = download / 'Song.mp3'
    imported = extra / 'Other.mp3'
    _mp3(native, title='Harbor Lights', artist='Kenji Aoki')
    _mp3(imported, title='Undertow', artist='Kenji Aoki')
    ctx = LibraryContext(download_dir=download, extra_dirs=(extra,))
    create_manual_playlist(ctx, 'Mix')
    stored_extra = library_stored_path(imported, download, extra_dirs=(extra,))
    edited = edit_manual_playlist(ctx, 'Mix', add=['Song.mp3', stored_extra])
    assert edited['count'] == 2
    assert 'Song.mp3' in edited['files']
    assert stored_extra in edited['files']
    listed = list_library_playlists(download, extra_dirs=(extra,))
    mix = next(item for item in listed if item['name'] == 'Mix')
    assert mix['files'] == edited['files']


def test_cannot_edit_imported_playlist(tmp_path):
    download = tmp_path / 'downloads'
    track = download / 'Song.mp3'
    _mp3(track, title='Harbor Lights', artist='Kenji Aoki')
    write_m3u(download, 'Spotify Hits', [{'filename': 'Song.mp3'}])
    ctx = LibraryContext(download_dir=download)
    with pytest.raises(ManualPlaylistError) as caught:
        edit_manual_playlist(ctx, 'Spotify Hits', add=['Song.mp3'])
    assert caught.value.status_code == 403


def test_drop_manual_keeps_audio(tmp_path):
    download = tmp_path / 'downloads'
    track = download / 'Song.mp3'
    _mp3(track, title='Harbor Lights', artist='Kenji Aoki')
    ctx = LibraryContext(download_dir=download)
    create_manual_playlist(ctx, 'Mix')
    edit_manual_playlist(ctx, 'Mix', add=['Song.mp3'])
    result = drop_manual_playlist(ctx, 'Mix')
    assert result['deleted_count'] == 0
    assert track.is_file()
    assert not (download / 'Playlists' / 'Mix.m3u').exists()
    assert not (download / 'Playlists' / 'Mix.jpg').exists()


def test_prune_missing_file_from_manual_playlist(tmp_path):
    download = tmp_path / 'downloads'
    keep = download / 'Keep.mp3'
    gone = download / 'Gone.mp3'
    _mp3(keep, title='Keep', artist='A')
    _mp3(gone, title='Gone', artist='A')
    ctx = LibraryContext(download_dir=download)
    create_manual_playlist(ctx, 'Mix')
    edit_manual_playlist(ctx, 'Mix', add=['Keep.mp3', 'Gone.mp3'])
    gone.unlink()
    affected = prune_files_from_manual_playlists(ctx, ['Gone.mp3'])
    assert affected == ['Mix']
    listed = list_library_playlists(download)
    mix = next(item for item in listed if item['name'] == 'Mix')
    assert mix['files'] == ['Keep.mp3']


def test_reserved_liked_name_rejected(tmp_path):
    download = tmp_path / 'downloads'
    download.mkdir()
    ctx = LibraryContext(download_dir=download)
    assert LIKED_PLAYLIST_NAME.casefold() == 'downtify liked songs'
    with pytest.raises(ManualPlaylistError) as caught:
        create_manual_playlist(ctx, LIKED_PLAYLIST_NAME)
    assert caught.value.status_code == 409


def test_mosaic_filter_matches_spotify_layouts():
    two = _filter_complex(2)
    three = _filter_complex(3)
    four = _filter_complex(4)
    assert 'hstack' in two
    assert 'vstack' in three
    assert 'hstack' in three
    assert four.count('hstack') == 2
    assert 'vstack' in four


def test_manual_playlist_cover_uses_distinct_track_art(tmp_path):
    download = tmp_path / 'downloads'
    one = download / 'One.mp3'
    two = download / 'Two.mp3'
    same = download / 'Same.mp3'
    _mp3(one, title='One', artist='A', cover=_jpeg(b'one'))
    _mp3(two, title='Two', artist='B', cover=_jpeg(b'two'))
    _mp3(same, title='Same', artist='A', cover=_jpeg(b'one'))
    ctx = LibraryContext(download_dir=download)
    create_manual_playlist(ctx, 'Mix')
    edit_manual_playlist(ctx, 'Mix', add=['One.mp3', 'Same.mp3', 'Two.mp3'])
    images = unique_cover_images(ctx, ['One.mp3', 'Same.mp3', 'Two.mp3'])
    assert len(images) == 2
    jpg = download / 'Playlists' / 'Mix.jpg'
    if shutil.which('ffmpeg'):
        assert jpg.is_file()
        assert jpg.stat().st_size > 0
    edit_manual_playlist(ctx, 'Mix', remove=['One.mp3', 'Same.mp3', 'Two.mp3'])
    assert not jpg.exists()


def test_rename_manual_playlist_keeps_tracks(tmp_path):
    download = tmp_path / 'downloads'
    track = download / 'Song.mp3'
    _mp3(track, title='Harbor Lights', artist='Kenji Aoki')
    ctx = LibraryContext(download_dir=download)
    create_manual_playlist(ctx, 'tesdte')
    edit_manual_playlist(ctx, 'tesdte', add=['Song.mp3'])
    result = rename_manual_playlist(ctx, 'tesdte', 'Late night')
    assert result['name'] == 'Late night'
    assert result['previous'] == 'tesdte'
    assert result['files'] == ['Song.mp3']
    assert not (download / 'Playlists' / 'tesdte.m3u').exists()
    dest = download / 'Playlists' / 'Late night.m3u'
    assert dest.is_file()
    assert is_manual_m3u(dest)
    listed = list_library_playlists(download)
    mix = next(item for item in listed if item['name'] == 'Late night')
    assert mix['files'] == ['Song.mp3']
    assert track.is_file()


def test_cannot_rename_imported_playlist(tmp_path):
    download = tmp_path / 'downloads'
    track = download / 'Song.mp3'
    _mp3(track, title='Harbor Lights', artist='Kenji Aoki')
    write_m3u(download, 'Spotify Hits', [{'filename': 'Song.mp3'}])
    ctx = LibraryContext(download_dir=download)
    with pytest.raises(ManualPlaylistError) as caught:
        rename_manual_playlist(ctx, 'Spotify Hits', 'New name')
    assert caught.value.status_code == 403


def test_rename_rejects_taken_name(tmp_path):
    download = tmp_path / 'downloads'
    download.mkdir()
    ctx = LibraryContext(download_dir=download)
    create_manual_playlist(ctx, 'Alpha')
    create_manual_playlist(ctx, 'Beta')
    with pytest.raises(ManualPlaylistError) as caught:
        rename_manual_playlist(ctx, 'Alpha', 'Beta')
    assert caught.value.status_code == 409
