"""Tests for cover art extraction."""

from __future__ import annotations

from pathlib import Path

from mutagen.id3 import APIC, ID3

from downtify.cover_art import extract_cover_art, extract_folder_cover


def test_extract_folder_cover_reads_cover_jpg(tmp_path: Path) -> None:
    track = tmp_path / 'release' / '01-track.mp3'
    track.parent.mkdir(parents=True)
    track.write_bytes(b'\x00')
    (track.parent / 'cover.jpg').write_bytes(b'folder-cover')

    data, mime = extract_folder_cover(track)
    assert data == b'folder-cover'
    assert mime == 'image/jpeg'


def test_extract_cover_art_prefers_embedded(tmp_path: Path) -> None:
    track = tmp_path / 't.mp3'
    track.write_bytes(b'\x00' * 64)
    tags = ID3()
    tags.add(
        APIC(
            encoding=3,
            mime='image/jpeg',
            type=3,
            desc='',
            data=b'embedded',
        )
    )
    tags.save(str(track), v2_version=3)
    (track.parent / 'cover.jpg').write_bytes(b'folder')

    data, _mime = extract_cover_art(track)
    assert data == b'embedded'
