"""Validate an on-disk track against a monitored release, not only its ID."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .file_naming import file_name_key
from .library_metadata import read_audio_metadata
from .track_tag_match import (
    duration_tolerances_from_settings,
    media_duration_matches_song,
)


def matches_release(
    path: Path,
    song: dict[str, Any],
    slskd_settings: Optional[dict[str, Any]] = None,
) -> bool:
    """Compare release tags and duration without modifying the file.

    The title, album, first artist and track number must agree. The
    length is held to the same allowance the download itself was
    (*slskd_settings*' duration tolerance, 10 s / 15 % by default, see
    :func:`~downtify.track_tag_match.media_duration_matches_song`): a
    catalogue's length is often a few seconds off the audio it lists, and
    a stricter check here would refuse the very file just downloaded.
    """
    if not path.is_file() or path.is_symlink():
        return False
    actual = read_audio_metadata(path)
    length = float(actual.get('duration') or 0)
    if length <= 0:
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
    if not song.get('duration'):
        return True
    tolerance = duration_tolerances_from_settings(slskd_settings)
    return media_duration_matches_song(
        song,
        max(1, round(length)),
        tolerance_seconds=tolerance['seconds'],
        tolerance_percent=tolerance['percent'],
    )
