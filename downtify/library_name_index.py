"""The audio file names in the downloads folder, kept in memory.

Before a download, :meth:`Downloader.find_existing_download` looks for
the song's file name anywhere in the library. Walking the whole folder
for that - twice for every song not at its exact path - is most of the
disk reading a playlist or an artist watch does on a NAS. This keeps
one listing per library folder instead:

* a file Downtify saves is added at once (:func:`note_saved`);
* every name it offers is checked on disk first, so a deleted or moved
  file is never offered;
* a file added by hand (or moved in by another tool) is seen once the
  listing is older than :data:`RECHECK_SECONDS` and read again, the
  same delay ``GET /playlists`` allows for an M3U changed by hand.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Optional

#: Seconds a listing is used before the folder is read again.
RECHECK_SECONDS = 60.0

#: The audio files the downloader counts as a song already downloaded.
AUDIO_EXTENSIONS = frozenset({'mp3', 'flac', 'ogg', 'opus', 'm4a'})


def _now() -> float:
    return time.monotonic()


def _folder_order(rel: str) -> tuple:
    """Sort key that puts *rel* where a sorted ``os.walk`` meets it: a
    folder's own files before its subfolders, each in name order."""

    parts = rel.split('/')
    return tuple((1, part) for part in parts[:-1]) + ((0, parts[-1]),)


class _Listing:
    def __init__(self, built_at: float, names: dict[str, list[str]]):
        self.built_at = built_at
        # base name (casefolded, no extension) -> relative paths, in
        # folder order.
        self.names = names


_LOCK = threading.Lock()
_LISTINGS: dict[str, _Listing] = {}


def _key(root: Path) -> str:
    try:
        return str(Path(root).resolve())
    except OSError:
        return str(root)


def _split(name: str) -> Optional[str]:
    """The casefolded base name of an audio file name, else ``None``."""

    base, dot, ext = name.rpartition('.')
    if not dot or ext.lower() not in AUDIO_EXTENSIONS:
        return None
    return base.casefold()


def _read(root: Path) -> dict[str, list[str]]:
    names: dict[str, list[str]] = {}
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
        rel_folder = Path(folder).relative_to(root).as_posix()
        prefix = '' if rel_folder == '.' else f'{rel_folder}/'
        for name in sorted(files):
            base = _split(name)
            if base is not None:
                names.setdefault(base, []).append(f'{prefix}{name}')
    return names


def _listing(root: Path) -> _Listing:
    """Call with :data:`_LOCK` held: one walk serves every thread waiting
    on it."""

    key = _key(root)
    listing = _LISTINGS.get(key)
    now = _now()
    if listing is None or now - listing.built_at > RECHECK_SECONDS:
        listing = _Listing(now, _read(root))
        _LISTINGS[key] = listing
    return listing


def candidates(root: Path, base: str) -> list[str]:
    """Paths under *root* (relative, ``/``-separated) of audio files whose
    name without extension is *base* (casefolded), in folder order. They
    may since have gone from disk: the caller checks each one."""

    with _LOCK:
        return list(_listing(root).names.get(base, ()))


def note_saved(root: Path, rel: str) -> None:
    """*rel* (relative to *root*) was just written: list it without
    reading the folder again."""

    rel = str(rel or '').replace('\\', '/').strip('/')
    if not rel or any(p.startswith('.') for p in rel.split('/')[:-1]):
        return
    base = _split(rel.rsplit('/', 1)[-1])
    if base is None:
        return
    with _LOCK:
        listing = _LISTINGS.get(_key(root))
        if listing is None:
            return
        paths = listing.names.setdefault(base, [])
        if rel not in paths:
            paths.append(rel)
            paths.sort(key=_folder_order)


def note_gone(root: Path, rel: str) -> None:
    """*rel* is no longer on disk."""

    with _LOCK:
        listing = _LISTINGS.get(_key(root))
        if listing is None:
            return
        base = _split(rel.rsplit('/', 1)[-1])
        paths = listing.names.get(base or '')
        if paths and rel in paths:
            paths.remove(rel)


def forget_all() -> None:
    """Drop every listing (tests; a changed library folder)."""

    with _LOCK:
        _LISTINGS.clear()
