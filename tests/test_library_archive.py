"""Tests for the Library page's "Download selected" ZIP stream."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from downtify import library_archive
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
    assert info.extract_version == 20
    assert info.extra == b''


@pytest.mark.parametrize('size', [1023, 1024, 1025])
def test_stream_library_zip_supports_zip64_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: int
) -> None:
    # Exercise the real ZIP64 boundary without allocating a 2 GiB file.
    monkeypatch.setattr(zipfile, 'ZIP64_LIMIT', 1024)
    name = 'My Playlist/Artist - Long.wav'
    track = tmp_path / 'long.wav'
    content = b'x' * size
    track.write_bytes(content)
    following = tmp_path / 'following.mp3'
    following.write_bytes(b'next track')

    with _zip_from([(name, track), ('following.mp3', following)]) as archive:
        assert archive.namelist() == [name, 'following.mp3']
        assert archive.read(name) == content
        assert archive.getinfo(name).file_size == size
        assert archive.getinfo(name).compress_type == zipfile.ZIP_STORED
        assert archive.getinfo(name).extract_version == 45
        assert archive.read('following.mp3') == b'next track'
        assert archive.testzip() is None


def test_stream_library_zip_streams_zip64_before_reading_next_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(zipfile, 'ZIP64_LIMIT', 1024)
    track = tmp_path / 'long.wav'
    content = b'x' * (1024 * 1024)
    track.write_bytes(content)
    following = tmp_path / 'following.mp3'
    entries = stream_library_zip([
        ('long.wav', track),
        ('following.mp3', following),
    ])

    first = next(entries)
    # This file is created only after the first chunk reaches the client.
    following.write_bytes(b'next track')
    chunks = [first, *entries]

    assert len(chunks) > 1
    assert len(first) < len(content)
    with zipfile.ZipFile(io.BytesIO(b''.join(chunks))) as archive:
        assert archive.read('long.wav') == content
        assert archive.getinfo('long.wav').extract_version == 45
        assert archive.read('following.mp3') == b'next track'
        assert archive.testzip() is None


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


def test_archive_ticket_expires(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(library_archive.time, 'monotonic', lambda: 1000.0)
    store = ArchiveTicketStore(ttl_seconds=60)
    token = store.create([('Artist - Song.mp3', tmp_path / 'x.mp3')])

    monkeypatch.setattr(library_archive.time, 'monotonic', lambda: 1061.0)
    assert store.pop(token) is None


def test_archive_tickets_are_independent(tmp_path: Path) -> None:
    store = ArchiveTicketStore()
    first = store.create([('a.mp3', tmp_path / 'a.mp3')])
    second = store.create([('b.mp3', tmp_path / 'b.mp3')])

    assert first != second
    assert store.pop(second) == [('b.mp3', tmp_path / 'b.mp3')]
    assert store.pop(first) == [('a.mp3', tmp_path / 'a.mp3')]
