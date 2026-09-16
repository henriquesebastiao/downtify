"""Tests for the Library page's "Download selected" ZIP stream."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from downtify.library_archive import (
    ArchiveTicketStore,
    archive_filename,
    stream_library_zip,
)


def _zip_from(entries: list[tuple[str, Path]]) -> zipfile.ZipFile:
    data = b''.join(stream_library_zip(entries))
    return zipfile.ZipFile(io.BytesIO(data))


def test_stream_library_zip_keeps_paths_and_contents(tmp_path: Path) -> None:
    flat = tmp_path / 'Artist - Song.mp3'
    flat.write_bytes(b'flat audio')
    nested = tmp_path / 'My Playlist' / 'Artist - Other.mp3'
    nested.parent.mkdir()
    nested.write_bytes(b'nested audio')

    archive = _zip_from([
        ('Artist - Song.mp3', flat),
        ('My Playlist/Artist - Other.mp3', nested),
    ])

    # Folders survive the round trip, so an extracted selection looks
    # like the library it came from.
    assert archive.namelist() == [
        'Artist - Song.mp3',
        'My Playlist/Artist - Other.mp3',
    ]
    assert archive.read('My Playlist/Artist - Other.mp3') == b'nested audio'
    assert archive.testzip() is None


def test_stream_library_zip_stores_without_compressing(tmp_path: Path) -> None:
    track = tmp_path / 'Artist - Song.flac'
    track.write_bytes(b'\x00' * 4096)

    archive = _zip_from([('Artist - Song.flac', track)])

    info = archive.getinfo('Artist - Song.flac')
    assert info.compress_type == zipfile.ZIP_STORED
    assert info.file_size == 4096


def test_stream_library_zip_yields_chunks_before_finishing(
    tmp_path: Path,
) -> None:
    # The response is streamed: a large file must not be buffered whole
    # before the first byte reaches the client.
    big = tmp_path / 'Artist - Long.wav'
    big.write_bytes(b'x' * (1024 * 1024))

    chunks = list(stream_library_zip([('Artist - Long.wav', big)]))

    assert len(chunks) > 1
    assert zipfile.ZipFile(io.BytesIO(b''.join(chunks))).testzip() is None


def test_stream_library_zip_skips_missing_files(tmp_path: Path) -> None:
    present = tmp_path / 'Artist - Song.mp3'
    present.write_bytes(b'audio')
    gone = tmp_path / 'Artist - Deleted.mp3'

    archive = _zip_from([
        ('Artist - Deleted.mp3', gone),
        ('Artist - Song.mp3', present),
    ])

    # A file deleted between selecting and downloading must not break
    # the archive for the rest of the selection.
    assert archive.namelist() == ['Artist - Song.mp3']


def test_archive_filename_is_timestamped() -> None:
    moment = datetime(2026, 9, 15, 20, 58, 1, tzinfo=timezone.utc)
    assert archive_filename(moment) == 'downtify-library-20260915-205801.zip'


def test_archive_ticket_is_single_use(tmp_path: Path) -> None:
    store = ArchiveTicketStore()
    entries = [('Artist - Song.mp3', tmp_path / 'Artist - Song.mp3')]

    token = store.create(entries)

    assert store.pop(token) == entries
    assert store.pop(token) is None


def test_archive_ticket_expires(tmp_path: Path) -> None:
    store = ArchiveTicketStore(ttl_seconds=0)
    token = store.create([('Artist - Song.mp3', tmp_path / 'x.mp3')])

    assert store.pop(token) is None


def test_archive_tickets_are_independent(tmp_path: Path) -> None:
    store = ArchiveTicketStore()
    first = store.create([('a.mp3', tmp_path / 'a.mp3')])
    second = store.create([('b.mp3', tmp_path / 'b.mp3')])

    assert first != second
    assert store.pop(second) == [('b.mp3', tmp_path / 'b.mp3')]
    assert store.pop(first) == [('a.mp3', tmp_path / 'a.mp3')]
