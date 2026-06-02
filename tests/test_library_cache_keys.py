"""Tests for stable library cache keys."""

from __future__ import annotations

from pathlib import Path

from downtify.library_cache_keys import file_content_key


def test_content_key_same_after_folder_move(tmp_path: Path) -> None:
    data = b'audio-payload'
    old = tmp_path / 'Playlist A' / 'Artist - Song.mp3'
    new = tmp_path / 'Artist' / 'Artist - Song.mp3'
    old.parent.mkdir(parents=True)
    new.parent.mkdir(parents=True)
    old.write_bytes(data)
    new.write_bytes(data)

    assert file_content_key(old) == file_content_key(new)


def test_content_key_changes_when_size_changes(tmp_path: Path) -> None:
    track = tmp_path / 'Song.mp3'
    track.write_bytes(b'short')
    key_a = file_content_key(track)
    track.write_bytes(b'longer-bytes')
    key_b = file_content_key(track)
    assert key_a != key_b
