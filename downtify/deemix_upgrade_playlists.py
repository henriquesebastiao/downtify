"""Publish replacement M3U paths before any old audio can be removed."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Callable


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


def playlist_files(roots: list[Path]) -> list[Path]:
    """One walk per batch, never follow directory symlinks."""
    found: set[Path] = set()
    for root in roots:
        for directory, _, names in os.walk(root, followlinks=False):
            for name in names:
                if Path(name).suffix.lower() in {'.m3u', '.m3u8'}:
                    found.add(Path(directory, name))
    return sorted(found)


def rewrite_playlists(
    roots: list[Path],
    writable_root: Path,
    mapping: dict[Path, tuple[Path, float]],
    *,
    stopped: Callable[[], bool],
) -> None:
    """Keep comments, ordering and manual-playlist markers; fail closed.

    A partly published batch is safe to repeat: original audio still
    exists, and an already rewritten line no longer matches the map.
    Read-only playlists referring to originals block the entire batch.
    """
    root = writable_root.resolve()
    changes: list[tuple[Path, bytes, str]] = []
    for playlist in playlist_files(roots):
        if stopped():
            raise InterruptedError('Replacement paused before publication')
        original = playlist.read_bytes()
        lines = original.decode('utf-8-sig').splitlines(keepends=True)
        changed = False
        for index, line in enumerate(lines):
            value = line.strip()
            if not value or value.startswith('#'):
                continue
            target = mapping.get((playlist.parent / value).resolve())
            if target is None:
                continue
            if not playlist.resolve().is_relative_to(root):
                raise ValueError(
                    'An external playlist still uses the original'
                )
            new_path, duration = target
            ending = '\r\n' if line.endswith('\r\n') else '\n'
            lines[index] = (
                os.path.relpath(new_path, playlist.parent).replace('\\', '/')
                + ending
            )
            if index and lines[index - 1].startswith('#EXTINF:'):
                _, comma, label = lines[index - 1].partition(',')
                if comma:
                    lines[index - 1] = f'#EXTINF:{round(duration)},{label}'
            changed = True
        if changed:
            changes.append((
                playlist,
                ''.join(lines).encode('utf-8'),
                hashlib.sha256(original).hexdigest(),
            ))
    for playlist, content, expected in changes:
        if stopped():
            raise InterruptedError('Replacement paused before publication')
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=playlist.parent, prefix='.audio-relink-', delete=False
            ) as output:
                temporary = Path(output.name)
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            os.chmod(temporary, playlist.stat().st_mode & 0o777)
            if digest(playlist) != expected:
                raise ValueError(
                    'Playlist changed during replacement; original audio retained'
                )
            os.replace(temporary, playlist)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
