"""M3U8 discovery, cache refresh and playlist maintenance. Offline."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from loguru import logger

from downtify import m3u, manual_playlists
from downtify.library_catalog import LibraryContext
from downtify.library_delete import remove_playlist_shell
from downtify.library_paths import library_stored_path
from downtify.library_paths_cache import invalidate_library_paths_cache
from downtify.playlist_listing import list_library_playlists


@pytest.fixture(autouse=True)
def _clear_listing_cache() -> Iterator[None]:
    invalidate_library_paths_cache()
    yield
    invalidate_library_paths_cache()


@pytest.mark.parametrize('suffix', ['.m3u8', '.M3U8', '.M3u8'])
@pytest.mark.parametrize('encoding', ['utf-8', 'utf-8-sig'])
def test_m3u8_discovery_keeps_order_roots_and_original_files(
    tmp_path: Path, suffix: str, encoding: str
) -> None:
    download = tmp_path / 'downloads'
    directory = download / 'Playlists'
    directory.mkdir(parents=True)
    slskd = tmp_path / 'slskd'
    slskd.mkdir()
    extra = tmp_path / 'collection'
    extra.mkdir()
    audio = [
        download / 'caf\u00e9.mp3',
        slskd / 'soulseek.flac',
        extra / '\u6771\u4eac.mp3',
    ]
    for path in audio:
        path.write_bytes(b'audio')
    ordered = [audio[2], audio[0], audio[1], audio[0]]
    outside = tmp_path / 'outside.mp3'
    outside.write_bytes(b'outside')
    path = directory / f'Mix{suffix}'
    body = '#EXTM3U\n' + '\n'.join(
        os.path.relpath(track, directory) for track in [*ordered, outside]
    )
    path.write_bytes((body + '\n').encode(encoding))
    before = path.read_bytes()
    path.with_suffix('.jpg').write_bytes(b'cover')
    (directory / 'Notes.txt').write_text('not a playlist', encoding='utf-8')

    found = list_library_playlists(download, slskd, (extra,))

    assert len(found) == 1
    assert found[0]['name'] == 'Mix'
    assert found[0]['files'] == [
        library_stored_path(track, download, slskd, (extra,))
        for track in ordered
    ]
    assert found[0]['count'] == 4
    assert found[0]['cover'] == 'Playlists/Mix.jpg'
    assert not found[0]['manual']
    assert m3u.find_m3u_for_name(download, 'mIx') == path
    assert m3u.iter_m3u_files(download) == [path]
    assert path.read_bytes() == before
    assert all(track.read_bytes() == b'audio' for track in audio)
    assert outside.read_bytes() == b'outside'


def test_m3u_lookup_keeps_existing_precedence_and_ignores_backups(
    tmp_path: Path,
) -> None:
    standard = tmp_path / 'Mix.m3u'
    utf8 = tmp_path / 'Mix.m3u8'
    backup = tmp_path / 'Mix.m3u8.bak'
    for path in (standard, utf8, backup):
        path.write_bytes(b'#EXTM3U\n')

    assert m3u.iter_m3u_files(tmp_path) == [standard, utf8]
    assert m3u.find_m3u_for_name(tmp_path, 'Mix') == standard


def test_m3u8_discovery_skips_invalid_utf8_without_legacy_fallback(
    tmp_path: Path,
) -> None:
    (tmp_path / 'song.mp3').write_bytes(b'audio')
    good = tmp_path / 'Good.m3u8'
    good.write_bytes(b'#EXTM3U\nsong.mp3\n')
    legacy = tmp_path / 'Legacy.m3u'
    legacy.write_bytes(b'#EXTM3U\n#EXTINF:1,Caf\xe9\nsong.mp3\n')
    invalid = tmp_path / 'Invalid.M3U8'
    invalid.write_bytes(b'#EXTM3U\n#EXTINF:1,Caf\xe9\nsong.mp3\n')
    before = invalid.read_bytes()
    logged: list[str] = []
    sink = logger.add(lambda message: logged.append(str(message)))
    try:
        found = list_library_playlists(tmp_path)
    finally:
        logger.remove(sink)

    assert [row['name'] for row in found] == ['Good', 'Legacy']
    assert any(str(invalid) in message for message in logged)
    assert invalid.read_bytes() == before


def test_m3u8_listing_cache_detects_creation_edit_and_removal(
    tmp_path: Path,
) -> None:
    for name in ('one.mp3', 'two.mp3'):
        (tmp_path / name).write_bytes(b'audio')
    (tmp_path / 'Original.m3u').write_bytes(b'#EXTM3U\none.mp3\n')
    assert [row['name'] for row in list_library_playlists(tmp_path)] == [
        'Original'
    ]
    added = tmp_path / 'Added.m3u8'
    added.write_bytes(b'#EXTM3U\none.mp3\n')
    found = list_library_playlists(tmp_path)
    assert [(row['name'], row['files']) for row in found] == [
        ('Added', ['one.mp3']),
        ('Original', ['one.mp3']),
    ]
    previous = added.stat()
    added.write_bytes(b'#EXTM3U\ntwo.mp3\n')
    os.utime(
        added,
        ns=(previous.st_atime_ns, previous.st_mtime_ns + 1_000_000_000),
    )

    found = list_library_playlists(tmp_path)

    assert found[0]['files'] == ['two.mp3']
    added.unlink()
    assert [row['name'] for row in list_library_playlists(tmp_path)] == [
        'Original'
    ]


def test_existing_m3u8_name_blocks_duplicate_playlist_creation(
    tmp_path: Path,
) -> None:
    path = tmp_path / 'Mix.m3u8'
    body = f'#EXTM3U\n{m3u.MANUAL_M3U_MARKER}\n'.encode()
    path.write_bytes(body)
    ctx = LibraryContext(download_dir=tmp_path)

    with pytest.raises(manual_playlists.ManualPlaylistError) as caught:
        manual_playlists.create_manual_playlist(ctx, 'mix')

    assert caught.value.status_code == 409
    assert path.read_bytes() == body
    assert not (tmp_path / 'Playlists' / 'mix.m3u').exists()


def test_m3u8_detach_edit_prune_and_drop_keep_audio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        manual_playlists, 'refresh_manual_playlist_cover', lambda *args: None
    )
    for name in ('one.mp3', 'two.mp3'):
        (tmp_path / name).write_bytes(b'audio')
    path = tmp_path / 'Mix.m3u8'
    path.write_bytes(b'#EXTM3U\n#EXTINF:1,One\none.mp3\n')
    ctx = LibraryContext(download_dir=tmp_path)

    detached = manual_playlists.detach_imported_playlist(ctx, 'Mix')

    assert detached['files'] == ['one.mp3']
    assert m3u.is_manual_m3u(path)
    edited = manual_playlists.edit_manual_playlist(ctx, 'Mix', add=['two.mp3'])
    assert edited['files'] == ['one.mp3', 'two.mp3']
    assert manual_playlists.prune_files_from_manual_playlists(
        ctx, ['one.mp3']
    ) == ['Mix']
    assert m3u.read_m3u_tracks(path, tmp_path) == ['two.mp3']
    dropped = manual_playlists.drop_manual_playlist(ctx, 'Mix')
    assert dropped['deleted_count'] == 0
    assert not path.exists()
    assert all(
        (tmp_path / name).read_bytes() == b'audio'
        for name in ('one.mp3', 'two.mp3')
    )


@pytest.mark.parametrize('suffix', ['.m3u', '.m3u8', '.M3U8', '.M3u8'])
@pytest.mark.parametrize('organized', [False, True])
def test_m3u8_shell_removal_keeps_audio_and_other_playlists(
    tmp_path: Path, suffix: str, organized: bool
) -> None:
    directory = tmp_path / ('Playlists' if organized else 'Mix')
    directory.mkdir()
    path = directory / f'Mix{suffix}'
    path.write_bytes(b'#EXTM3U\nsong.mp3\n')
    audio = directory / 'song.mp3'
    audio.write_bytes(b'audio')
    cover = path.with_suffix('.jpg')
    cover.write_bytes(b'cover')
    other = directory / 'Other.m3u8'
    other.write_bytes(b'#EXTM3U\nsong.mp3\n')

    result = remove_playlist_shell(
        'Mix', tmp_path, organize_by_artist=organized
    )

    assert result == {'m3u_removed': 1, 'cover_removed': True}
    assert not path.exists()
    assert not cover.exists()
    assert audio.read_bytes() == b'audio'
    assert other.read_bytes() == b'#EXTM3U\nsong.mp3\n'


def test_organized_shell_removal_does_not_scan_playlist_audio_folder(
    tmp_path: Path,
) -> None:
    directory = tmp_path / 'Mix'
    directory.mkdir()
    path = directory / 'Mix.m3u8'
    path.write_bytes(b'#EXTM3U\nsong.mp3\n')

    result = remove_playlist_shell('Mix', tmp_path, organize_by_artist=True)

    assert result == {'m3u_removed': 0, 'cover_removed': False}
    assert path.is_file()
