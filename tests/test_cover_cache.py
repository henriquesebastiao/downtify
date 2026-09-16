"""Tests for optional cover art disk cache."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from mutagen.id3 import APIC, ID3

from downtify.cover_cache import CoverArtCache


def _write_mp3_with_cover(path: Path, cover: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\x00' * 128)
    tags = ID3()
    tags.add(
        APIC(
            encoding=3,
            mime='image/jpeg',
            type=3,
            desc='Cover',
            data=cover,
        )
    )
    tags.save(str(path), v2_version=3)


def test_cover_cache_lookup_after_store(tmp_path: Path) -> None:
    track = tmp_path / 'Artist - Song.mp3'
    cover_bytes = b'fake-jpeg-data'
    _write_mp3_with_cover(track, cover_bytes)

    cache = CoverArtCache(tmp_path / 'covers')
    cache.store('Artist - Song.mp3', track, cover_bytes, 'image/jpeg')

    with patch('downtify.cover_art.extract_cover_art') as extract:
        hit = cache.lookup('Artist - Song.mp3', track)
        extract.assert_not_called()

    assert hit is not None
    assert hit[0] == cover_bytes
    assert hit[1] == 'image/jpeg'


def test_cover_cache_refresh_invalidates_on_change(tmp_path: Path) -> None:
    track = tmp_path / 't.mp3'
    _write_mp3_with_cover(track, b'old')
    cache = CoverArtCache(tmp_path / 'covers')
    cache.refresh('t.mp3', track)

    time.sleep(0.05)
    _write_mp3_with_cover(track, b'newcoverbytes')
    cache.refresh('t.mp3', track)
    hit = cache.lookup('t.mp3', track)
    assert hit is not None
    assert hit[0] == b'newcoverbytes'
