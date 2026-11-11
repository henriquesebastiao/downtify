"""Validated, staged edits of embedded library metadata."""

from __future__ import annotations

import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile
from mutagen.id3 import ID3, TCMP, TXXX
from mutagen.mp4 import MP4

from .lyrics import can_mutate_audio

_FIELDS = {
    'title': 'title',
    'artist': 'artist',
    'album': 'album',
    'album_artist': 'albumartist',
    'track_number': 'tracknumber',
    'release_date': 'date',
    'genre': 'genre',
}
_lock = threading.RLock()


def validate_changes(changes: Any) -> dict[str, Any]:
    if not isinstance(changes, dict) or not changes:
        raise ValueError('Provide at least one metadata field')
    unknown = set(changes) - set(_FIELDS) - {'explicit', 'compilation'}
    if unknown:
        raise ValueError(
            'Unknown metadata fields: ' + ', '.join(sorted(unknown))
        )
    result = {}
    for field, raw_value in changes.items():
        value = raw_value
        if field in {'explicit', 'compilation'}:
            if value is not None and not isinstance(value, bool):
                raise ValueError(f'{field} must be a boolean or null')
        elif field == 'track_number':
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 1 <= value <= 9999
            ):
                raise ValueError(
                    'track_number must be an integer between 1 and 9999, or null'
                )
        elif value is not None:
            if (
                not isinstance(value, str)
                or len(value) > 1000
                or '\x00' in value
            ):
                raise ValueError(f'Invalid {field}')
            value = value.strip() or None
        result[field] = value
    return result


def edit_file(path: Path, changes: dict[str, Any]) -> None:
    """Copy and retag a file before atomically replacing it, preserving other tags."""
    with _lock:
        if not can_mutate_audio(path):
            raise PermissionError('Audio file is read-only')
        before = path.stat()
        fd, temp = tempfile.mkstemp(
            prefix='.downtify-tags-', suffix=path.suffix, dir=path.parent
        )
        os.close(fd)
        staged = Path(temp)
        try:
            shutil.copy2(path, staged)
            audio = MutagenFile(str(staged), easy=True)
            if audio is None:
                raise ValueError('Unsupported audio format')
            if audio.tags is None:
                audio.add_tags()
            for field, value in changes.items():
                if field in {'explicit', 'compilation'}:
                    continue
                key = _FIELDS[field]
                if value is None:
                    if key in audio:
                        del audio[key]
                else:
                    audio[key] = str(value)
            audio.save()
            # The multi-artist tag takes precedence over the artist tag when
            # read. Remove it when editing artist so the two cannot disagree.
            if (
                'artist' in changes
                or 'explicit' in changes
                or 'compilation' in changes
            ):
                _write_special(staged, changes)
            current = path.stat()
            if (current.st_ino, current.st_size, current.st_mtime_ns) != (
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
            ):
                raise ValueError(
                    'File changed while editing; reload and try again'
                )
            os.replace(staged, path)
        finally:
            staged.unlink(missing_ok=True)


def _write_special(path: Path, changes: dict[str, Any]) -> None:
    if path.suffix.lower() == '.mp3':
        tags = ID3(str(path))
        if 'artist' in changes:
            tags.delall('TXXX:ARTISTS')
        if 'explicit' in changes:
            tags.delall('TXXX:ITUNESADVISORY')
            if changes['explicit'] is not None:
                tags.add(
                    TXXX(
                        encoding=3,
                        desc='ITUNESADVISORY',
                        text=['1' if changes['explicit'] else '2'],
                    )
                )
        if 'compilation' in changes:
            tags.delall('TCMP')
            if changes['compilation'] is not None:
                tags.add(
                    TCMP(
                        encoding=3,
                        text=['1' if changes['compilation'] else '0'],
                    )
                )
        tags.save(v2_version=4)
    elif path.suffix.lower() in {'.m4a', '.mp4'}:
        audio = MP4(str(path))
        if 'artist' in changes:
            audio.pop('----:com.apple.iTunes:ARTISTS', None)
        if 'explicit' in changes:
            audio.pop('rtng', None)
            if changes['explicit'] is not None:
                audio['rtng'] = [1 if changes['explicit'] else 2]
        if 'compilation' in changes:
            audio.pop('cpil', None)
            if changes['compilation'] is not None:
                audio['cpil'] = changes['compilation']
        audio.save()
    else:
        audio = MutagenFile(str(path))
        if audio is None or audio.tags is None:
            raise ValueError('Unsupported audio format')
        if 'artist' in changes:
            audio.tags.pop('artists', None)
        for field, key in (
            ('explicit', 'ITUNESADVISORY'),
            ('compilation', 'compilation'),
        ):
            if field in changes:
                audio.tags.pop(key, None)
                if changes[field] is not None:
                    audio.tags[key] = '1' if changes[field] else '0'
        audio.save()
