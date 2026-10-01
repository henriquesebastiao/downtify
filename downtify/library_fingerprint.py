"""Hash of audio filenames in each library folder so ``GET /tracks``
can skip a full scan. Playlist M3U writes are ignored.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional

#: Folders ``library_catalog`` excludes from the audio listing.
_SKIP_DIRNAMES = frozenset({'Podcasts', 'Playlists'})
_AUDIO_SUFFIXES = frozenset({
    '.mp3',
    '.m4a',
    '.flac',
    '.ogg',
    '.wav',
    '.aac',
    '.opus',
})
_STAGING = '.downtify-upgrade'


def library_tree_fingerprint(
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
    extra_dirs: Sequence[Path] = (),
) -> str:
    """Hash of each library folder's path + mtime (not per-file stats)."""

    digest = hashlib.sha256()
    seen: set[str] = set()
    for root, prune_sidecars in _roots(download_dir, slskd_dir, extra_dirs):
        _hash_tree(digest, root, seen, prune_sidecars=prune_sidecars)
    return digest.hexdigest()


def _roots(
    download_dir: Path,
    slskd_dir: Optional[Path],
    extra_dirs: Sequence[Path],
) -> list[tuple[Path, bool]]:
    items: list[tuple[Path, bool]] = [(Path(download_dir), True)]
    if slskd_dir is not None:
        items.append((Path(slskd_dir), False))
    for extra in extra_dirs or ():
        items.append((Path(extra), False))
    return items


def _hash_tree(
    digest: Any,
    root: Path,
    seen: set[str],
    *,
    prune_sidecars: bool,
) -> None:
    try:
        resolved = root.resolve()
    except OSError:
        digest.update(b'?:')
        digest.update(str(root).encode('utf-8', 'replace'))
        digest.update(b'\n')
        return
    key = str(resolved)
    if key in seen:
        return
    seen.add(key)
    try:
        is_dir = resolved.is_dir()
    except OSError:
        is_dir = False
    if not is_dir:
        digest.update(b'missing:')
        digest.update(key.encode('utf-8', 'replace'))
        digest.update(b'\n')
        return
    for dirpath, dirnames, filenames in os.walk(resolved, followlinks=False):
        current = Path(dirpath)
        if prune_sidecars and current == resolved:
            dirnames[:] = [
                name for name in dirnames if name not in _SKIP_DIRNAMES
            ]
        dirnames.sort()
        audio_names = [
            name
            for name in filenames
            if _STAGING not in name
            and Path(name).suffix.lower() in _AUDIO_SUFFIXES
        ]
        audio_names.sort()
        digest.update(dirpath.encode('utf-8', 'replace'))
        digest.update(b'\0')
        digest.update('\n'.join(audio_names).encode('utf-8', 'replace'))
        digest.update(b'\n')


def playlist_listing_fingerprint(download_dir: Path) -> str:
    """Hash of every ``.m3u`` under *download_dir* (name + mtime)."""

    digest = hashlib.sha256()
    base = Path(download_dir)
    try:
        if not base.is_dir():
            return digest.hexdigest()
    except OSError:
        return digest.hexdigest()
    found: list[tuple[str, int]] = []
    for dirpath, _dirnames, filenames in os.walk(base, followlinks=False):
        for name in filenames:
            if not name.lower().endswith('.m3u'):
                continue
            path = os.path.join(dirpath, name)
            try:
                mtime_ns = os.stat(path, follow_symlinks=True).st_mtime_ns
            except OSError:
                mtime_ns = 0
            found.append((path, int(mtime_ns)))
    found.sort()
    for path, mtime_ns in found:
        digest.update(path.encode('utf-8', 'replace'))
        digest.update(b'\0')
        digest.update(str(mtime_ns).encode())
        digest.update(b'\n')
    return digest.hexdigest()
