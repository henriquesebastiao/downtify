"""Validate an on-disk track against a monitored release, not only its ID."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .file_naming import file_name_key
from .library_metadata import read_audio_metadata


def matches_release(path: Path, song: dict[str, Any]) -> bool:
    """Compare release tags and duration without modifying the file."""
    if not path.is_file() or path.is_symlink():
        return False
    actual = read_audio_metadata(path)
    if float(actual.get('duration') or 0) <= 0:
        return False
    for wanted, found in (
        (song.get('name'), actual.get('title')),
        (song.get('album_name'), actual.get('album')),
    ):
        if not wanted or file_name_key(wanted) != file_name_key(found or ''):
            return False
    artists = song.get('artists') or []
    if artists:
        found = {file_name_key(a) for a in actual.get('artists') or []}
        if file_name_key(artists[0]) not in found:
            return False
    number = int(song.get('track_number') or 0)
    if number and int(actual.get('track_number') or 0) != number:
        return False
    duration = float(song.get('duration') or 0)
    if duration and abs(float(actual.get('duration') or 0) - duration) > 3:
        return False
    return True
