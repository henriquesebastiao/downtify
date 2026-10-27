"""What Downtify's folders hold besides library songs.

The library listing only sees audio files. This walks the folders
Downtify writes to - the downloads folder, slskd's folder and the
dedicated lyrics folder - once, and sorts every file into a kind
(:data:`KINDS`), so the library usage page can say what else takes room
and what is safe to clean up:

* *leftovers* - temporary files an interrupted download, conversion or
  library upgrade left behind (:func:`is_temporary`), only once they are
  older than :data:`LEFTOVER_MIN_AGE` (a younger one may be in use);
* *orphans* - sidecars whose song is gone: an ``.lrc`` with no audio
  file of the same name beside it (or, in the lyrics folder, no library
  song at its path) and an album ``cover.jpg`` in a folder with no audio
  file and no playlist left.

Nothing is deleted. ``GET /api/library/usage/scan`` (``downtify/api.py``)
runs it in a thread and keeps the result for a few minutes.
"""

from __future__ import annotations

import os
import re
import time
from collections.abc import Collection, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .library_catalog import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    PODCASTS_DIRNAME,
    UPGRADE_STAGING_MARKER,
)
from .library_cleanup import ALBUM_COVER_FILENAME

#: Every kind a file is sorted into.
KINDS = (
    'audio',
    'podcasts',
    'lyrics',
    'images',
    'playlists',
    'metadata',
    'temporary',
    'other',
)
#: A temporary file younger than this may still be written to.
LEFTOVER_MIN_AGE = 3600.0
#: How many leftovers / orphans are listed by name (biggest first).
EXAMPLES = 50
#: Saved artist photos, banners and profiles (``.metadata/...``).
METADATA_DIRNAME = '.metadata'

PLAYLIST_EXTENSIONS = frozenset({'.m3u', '.m3u8'})
#: yt-dlp's partial downloads and fragments (``.part``, ``.part-Frag3``),
#: its resume notes (``.ytdl``), ffmpeg's ``name.temp.mp3`` while it
#: converts, and the ``.tmp`` of atomic writes.
_TEMPORARY = re.compile(
    r'(\.part(-frag\d+)?|\.ytdl|\.tmp|\.temp(\.\w{1,5})?)$', re.IGNORECASE
)


def is_temporary(name: str) -> bool:
    """Whether *name* is a file only ever meant to exist for a while."""

    return UPGRADE_STAGING_MARKER in name or bool(_TEMPORARY.search(name))


@dataclass(frozen=True)
class Folder:
    """One folder to walk: ``id`` names it, ``skip`` are folders inside
    it walked on their own (or not at all)."""

    id: str
    path: Path
    skip: tuple[Path, ...] = ()


@dataclass
class _File:
    rel: str
    name: str
    size: int
    mtime: float


@dataclass
class _Tally:
    files: int = 0
    bytes: int = 0
    kinds: dict[str, list[int]] = field(
        default_factory=lambda: {kind: [0, 0] for kind in KINDS}
    )

    def add(self, kind: str, size: int) -> None:
        self.files += 1
        self.bytes += size
        self.kinds[kind][0] += 1
        self.kinds[kind][1] += size


def _walk(
    root: Path, skip: Collection[Path]
) -> Iterator[tuple[str, list[_File]]]:
    """``(folder relative to root, [_File])`` for every folder under
    *root*, symlinks not followed."""

    pending = [root]
    while pending:
        current = pending.pop()
        files: list[_File] = []
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        rel_dir = '' if current == root else current.relative_to(root)
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    path = Path(entry.path)
                    if path not in skip:
                        pending.append(path)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                stat = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            rel = f'{rel_dir}/{entry.name}' if rel_dir else entry.name
            files.append(
                _File(
                    str(rel).replace('\\', '/'),
                    entry.name,
                    stat.st_size,
                    stat.st_mtime,
                )
            )
        yield str(rel_dir).replace('\\', '/'), files


def _suffix(name: str) -> str:
    return os.path.splitext(name)[1].lower()


def _stem(name: str) -> str:
    return os.path.splitext(name)[0]


def _kind(folder_rel: str, item: _File, is_downloads: bool) -> str:
    if is_temporary(item.name):
        return 'temporary'
    top = folder_rel.split('/', 1)[0]
    if is_downloads and top == PODCASTS_DIRNAME:
        return 'podcasts'
    if top == METADATA_DIRNAME:
        return 'metadata'
    suffix = _suffix(item.name)
    if suffix in AUDIO_EXTENSIONS:
        return 'audio'
    if suffix == '.lrc':
        return 'lyrics'
    if suffix in IMAGE_EXTENSIONS:
        return 'images'
    if suffix in PLAYLIST_EXTENSIONS:
        return 'playlists'
    return 'other'


@dataclass
class _Found:
    files: int = 0
    bytes: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)
    items: list[dict[str, Any]] = field(default_factory=list)

    def add(self, folder: str, item: _File, kind: str) -> None:
        self.files += 1
        self.bytes += item.size
        self.by_kind[kind] = self.by_kind.get(kind, 0) + 1
        self.items.append({
            'folder': folder,
            'file': item.rel,
            'bytes': item.size,
            'kind': kind,
            'modified': int(item.mtime),
        })

    def report(self) -> dict[str, Any]:
        largest = sorted(
            self.items, key=lambda i: (-i['bytes'], i['folder'], i['file'])
        )
        return {
            'files': self.files,
            'bytes': self.bytes,
            'by_kind': dict(sorted(self.by_kind.items())),
            'examples': largest[:EXAMPLES],
        }


def _orphans_in(
    folder_rel: str,
    files: list[_File],
    library_stems: Optional[Collection[str]],
) -> list[tuple[_File, str]]:
    """The sidecars in one folder whose song is gone.

    In the lyrics folder (*library_stems* given) an ``.lrc`` belongs to
    the library song at its own path; elsewhere, to the audio beside it.
    """

    stems = {
        _stem(item.name)
        for item in files
        if _suffix(item.name) in AUDIO_EXTENSIONS
        and not is_temporary(item.name)
    }
    playlists = any(_suffix(i.name) in PLAYLIST_EXTENSIONS for i in files)
    found: list[tuple[_File, str]] = []
    for item in files:
        suffix = _suffix(item.name)
        if suffix == '.lrc':
            if library_stems is not None:
                if _stem(item.rel) not in library_stems:
                    found.append((item, 'lyrics'))
            elif _stem(item.name) not in stems:
                found.append((item, 'lyrics'))
        elif (
            library_stems is None
            and item.name == ALBUM_COVER_FILENAME
            and not stems
            and not playlists
            and folder_rel
        ):
            found.append((item, 'cover'))
    return found


def scan_folders(
    folders: list[Folder],
    *,
    lyrics: Optional[Folder] = None,
    library_stems: Collection[str] = (),
    now: Optional[float] = None,
) -> dict[str, Any]:
    """Walk *folders* (and the *lyrics* folder, whose ``.lrc`` files
    belong to the library songs at *library_stems* - their library
    paths without the extension).

    ``folders`` lists what each holds (``{id, path, files, bytes,
    kinds: {kind: {files, bytes}}}``); ``leftovers`` and ``orphans``
    count what could go, biggest first.
    """

    moment = time.time() if now is None else now
    leftovers = _Found()
    orphans = _Found()
    report: list[dict[str, Any]] = []
    stems = set(library_stems)
    walks = [(folder, None) for folder in folders]
    if lyrics is not None:
        walks.append((lyrics, stems))
    started = time.monotonic()
    for folder, owned in walks:
        tally = _Tally()
        is_downloads = folder.id == 'downloads'
        for folder_rel, files in _walk(folder.path, folder.skip):
            for item in files:
                kind = _kind(folder_rel, item, is_downloads)
                tally.add(kind, item.size)
                if kind == 'temporary' and (
                    moment - item.mtime >= LEFTOVER_MIN_AGE
                ):
                    leftovers.add(folder.id, item, 'temporary')
            in_podcasts = (
                is_downloads
                and folder_rel.split('/', 1)[0] == PODCASTS_DIRNAME
            )
            if folder_rel.split('/', 1)[0] == METADATA_DIRNAME or in_podcasts:
                continue
            for item, kind in _orphans_in(folder_rel, files, owned):
                orphans.add(folder.id, item, kind)
        report.append({
            'id': folder.id,
            'path': str(folder.path),
            'files': tally.files,
            'bytes': tally.bytes,
            'kinds': {
                kind: {'files': files, 'bytes': size}
                for kind, (files, size) in tally.kinds.items()
                if files
            },
        })
    return {
        'folders': report,
        'leftovers': leftovers.report(),
        'orphans': orphans.report(),
        'seconds': round(time.monotonic() - started, 2),
    }


def _resolved(path: Optional[Path]) -> Optional[Path]:
    if path is None:
        return None
    try:
        resolved = path.resolve()
    except OSError:
        return None
    return resolved if resolved.is_dir() else None


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def plan_folders(
    download_dir: Path,
    slskd_dir: Optional[Path],
    lyrics_dir: Optional[Path],
) -> tuple[list[Folder], Optional[Folder]]:
    """``(folders, lyrics folder)`` to walk: each folder once, one inside
    another walked on its own, and the lyrics folder only when it holds
    none of the others (``.lrc`` files beside the songs are found
    walking the songs' folders)."""

    downloads = _resolved(download_dir)
    if downloads is None:
        return [], None
    roots = {'downloads': downloads}
    slskd = _resolved(slskd_dir)
    if slskd is not None and slskd != downloads:
        roots['slskd'] = slskd
    lyrics = _resolved(lyrics_dir)
    if lyrics is not None and not any(
        _inside(root, lyrics) for root in roots.values()
    ):
        roots['lyrics'] = lyrics
    folders = {
        key: Folder(
            key,
            path,
            tuple(
                other
                for name, other in roots.items()
                if name != key and other != path and _inside(other, path)
            ),
        )
        for key, path in roots.items()
    }
    lyrics_folder = folders.pop('lyrics', None)
    return list(folders.values()), lyrics_folder
