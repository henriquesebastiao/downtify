"""Unreadable playlists must not break Library discovery. Offline."""

from __future__ import annotations

from pathlib import Path

import pytest
from loguru import logger

from downtify import m3u
from downtify.library_paths_cache import invalidate_library_paths_cache
from downtify.playlist_listing import list_library_playlists
from downtify.playlist_mosaic import (
    EXPLICIT_COVER_MARKER,
    has_explicit_cover,
    keep_explicit_cover,
)


@pytest.mark.parametrize(
    'unreadable',
    [
        b'#EXTM3U\n#EXTDOWNTIFY:manual\n#bad\x81\nsong.mp3\n',
        '#EXTM3U\nsong.mp3\n'.encode('utf-16-le'),
    ],
)
def test_mixed_library_skips_unreadable_playlists(
    tmp_path: Path, unreadable: bytes
) -> None:
    bodies = {
        'Unicode.m3u': '#EXTM3U\n#EXTINF:1,東京 🎵\n東京.mp3\n'.encode(),
        'Legacy.m3u': (
            b'#EXTM3U\r\n#EXTINF:196,Beyonc\xe9\r\nBeyonc\xe9.mp3\r\n'
        ),
        'Broken.m3u': unreadable,
        'Empty.m3u': f'#EXTM3U\n{m3u.MANUAL_M3U_MARKER}\n'.encode(),
    }
    for name, body in bodies.items():
        (tmp_path / name).write_bytes(body)
    for name in ('東京.mp3', 'Beyoncé.mp3', 'song.mp3'):
        (tmp_path / name).write_bytes(b'audio')
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    logged: list[str] = []
    sink = logger.add(lambda message: logged.append(str(message)))
    invalidate_library_paths_cache()
    try:
        found = list_library_playlists(tmp_path)
    finally:
        logger.remove(sink)
        invalidate_library_paths_cache()

    assert [(row['name'], row['files']) for row in found] == [
        ('Empty', []),
        ('Legacy', ['Beyoncé.mp3']),
        ('Unicode', ['東京.mp3']),
    ]
    assert found[0]['manual']
    assert any(
        str(tmp_path / 'Broken.m3u') in message and 'UTF-8' in message
        for message in logged
    )
    assert {
        path.name: path.read_bytes() for path in tmp_path.iterdir()
    } == before


def test_legacy_manual_playlist_with_explicit_cover(tmp_path: Path) -> None:
    path = tmp_path / 'Beyoncé.m3u'
    body = (
        f'#EXTM3U\r\n{m3u.MANUAL_M3U_MARKER}\r\n'
        f'{EXPLICIT_COVER_MARKER}\r\n#EXTINF:196,Beyoncé\r\nBeyoncé.mp3\r\n'
    ).encode('cp1252')
    path.write_bytes(body)
    path.with_suffix('.jpg').write_bytes(b'cover')
    (tmp_path / 'Beyoncé.mp3').write_bytes(b'audio')
    invalidate_library_paths_cache()
    try:
        found = list_library_playlists(tmp_path)
    finally:
        invalidate_library_paths_cache()

    assert has_explicit_cover(path)
    keep_explicit_cover(path)
    assert len(found) == 1
    assert found[0]['files'] == ['Beyoncé.mp3']
    assert found[0]['manual']
    assert found[0]['explicit_cover']
    assert path.read_bytes() == body


def test_library_skips_playlist_that_cannot_be_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = tmp_path / 'Denied.m3u'
    bad.write_text('#EXTM3U\nsong.mp3\n', encoding='utf-8')
    (tmp_path / 'Good.m3u').write_bytes(b'#EXTM3U\nsong.mp3\n')
    (tmp_path / 'song.mp3').write_bytes(b'audio')
    read_bytes = Path.read_bytes

    def guarded_read(path: Path) -> bytes:
        if path == bad:
            raise PermissionError('Access denied')
        return read_bytes(path)

    monkeypatch.setattr(Path, 'read_bytes', guarded_read)
    invalidate_library_paths_cache()
    try:
        found = list_library_playlists(tmp_path)
    finally:
        invalidate_library_paths_cache()

    assert [row['name'] for row in found] == ['Good']
