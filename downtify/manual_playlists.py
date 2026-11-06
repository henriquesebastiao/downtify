"""Playlists the user builds in the Library, stored as marked M3U files.

Downloaded Spotify/YouTube playlists stay read-only here. These ones
live under ``Playlists/`` with ``#EXTDOWNTIFY:manual`` so they can be
edited, and so deleting them never removes the audio files.
"""

from __future__ import annotations

import functools
import threading
from collections import Counter
from collections.abc import Collection, Iterable
from pathlib import Path
from shutil import copyfile
from typing import Any, Callable, Optional, ParamSpec, TypeVar

from loguru import logger

from . import m3u
from .library_catalog import LibraryContext, resolve_library_file
from .library_paths_cache import invalidate_library_paths_cache
from .playlist_mosaic import (
    EXPLICIT_COVER_MARKER,
    has_explicit_cover,
    keep_explicit_cover,
    normalize_uploaded_cover,
    refresh_manual_playlist_cover,
)

MAX_PLAYLIST_NAME_LEN = 120
# Keep edits bounded, while supporting large imported playlists.
MAX_TRACKS_PER_EDIT = 10_000

_P = ParamSpec('_P')
_R = TypeVar('_R')
_WRITE_LOCK = threading.RLock()


def _serialized(func: Callable[_P, _R]) -> Callable[_P, _R]:
    """Run *func* alone among this module's M3U rewrites: the owner and
    the editors of a shared playlist read, change and write it back at
    the same time, and the last write would drop the other's songs."""

    @functools.wraps(func)
    def run(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        with _WRITE_LOCK:
            return func(*args, **kwargs)

    return run


class ManualPlaylistError(ValueError):
    """User-facing failure (duplicate name, not manual, missing file)."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _ctx_dirs(
    ctx: LibraryContext,
) -> tuple[Path, Optional[Path], tuple[Path, ...]]:
    return ctx.download_dir, ctx.slskd_dir, tuple(ctx.extra_dirs or ())


def _clean_path(raw: object) -> str:
    return str(raw or '').strip().replace('\\', '/')


def _occurrence_indexes(
    files: list[str], entries: Iterable[tuple[str, int]]
) -> set[int]:
    """Where in *files* each ``(file, occurrence)`` sits: the
    *occurrence*-th copy (from 0) of a song the playlist repeats."""

    wanted: dict[str, set[int]] = {}
    for raw, occurrence in entries:
        stored = _clean_path(raw)
        if stored and occurrence >= 0:
            wanted.setdefault(stored, set()).add(occurrence)
    seen: Counter[str] = Counter()
    indexes: set[int] = set()
    for index, item in enumerate(files):
        if seen[item] in wanted.get(item, ()):
            indexes.add(index)
        seen[item] += 1
    return indexes


def _entries_for(files: list[str]) -> list[dict[str, str]]:
    return [{'filename': name} for name in files]


def _write(ctx: LibraryContext, files: list[str], path: Path) -> Path:
    explicit_cover = has_explicit_cover(path)
    content, _kept = m3u.build_m3u_content(
        _entries_for(files),
        download_dir=ctx.download_dir,
        m3u_dir=path.parent,
        slskd_dir=ctx.slskd_dir,
        extra_dirs=tuple(ctx.extra_dirs or ()),
    )
    lines = content.splitlines()
    if lines[:1] == ['#EXTM3U'] and m3u.MANUAL_M3U_MARKER not in lines[:4]:
        lines.insert(1, m3u.MANUAL_M3U_MARKER)
        if explicit_cover:
            lines.insert(2, EXPLICIT_COVER_MARKER)
        content = '\n'.join(lines) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8', newline='\n')
    refresh_manual_playlist_cover(ctx, path, files)
    invalidate_library_paths_cache()
    return path


def _read_files(ctx: LibraryContext, path: Path) -> list[str]:
    download_dir, slskd_dir, extra_dirs = _ctx_dirs(ctx)
    return m3u.read_m3u_tracks(
        path, download_dir, slskd_dir, extra_dirs, keep_missing=True
    )


def _require_manual(path: Path, name: str) -> None:
    if not m3u.is_manual_m3u(path):
        raise ManualPlaylistError(
            f'Playlist {name!r} is imported and cannot be edited',
            status_code=403,
        )


@_serialized
def save_manual_playlist_cover(
    ctx: LibraryContext,
    name: str,
    data: bytes,
    content_type: str,
) -> Path:
    """Replace a manual playlist's generated cover with uploaded art."""

    path = m3u.find_m3u_for_name(ctx.download_dir, name)
    if path is None:
        raise ManualPlaylistError(
            f'Playlist {name!r} was not found', status_code=404
        )
    _require_manual(path, path.stem)
    cover = path.with_suffix('.jpg')
    cover.write_bytes(normalize_uploaded_cover(data, content_type))
    keep_explicit_cover(path)
    invalidate_library_paths_cache()
    return cover


@_serialized
def remove_manual_playlist_cover(ctx: LibraryContext, name: str) -> None:
    """Remove custom art and restore the manual playlist's track mosaic."""

    path = m3u.find_m3u_for_name(ctx.download_dir, name)
    if path is None:
        raise ManualPlaylistError(
            f'Playlist {name!r} was not found', status_code=404
        )
    _require_manual(path, path.stem)
    path.with_suffix('.jpg').unlink(missing_ok=True)
    text = m3u.read_m3u_text(path)
    if text is not None:
        lines = [
            line
            for line in text.splitlines()
            if line.strip() != EXPLICIT_COVER_MARKER
        ]
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    refresh_manual_playlist_cover(ctx, path, _read_files(ctx, path))
    invalidate_library_paths_cache()


def existing_playlist_names(download_dir: Path) -> set[str]:
    return {path.stem.casefold() for path in m3u.iter_m3u_files(download_dir)}


def _validated_name(raw: str) -> str:
    text = str(raw or '').strip()
    if not text or len(text) > MAX_PLAYLIST_NAME_LEN:
        raise ManualPlaylistError('Enter a playlist name')
    # Same rule as likes.is_liked_playlist, inlined to avoid
    # manual_playlists → likes → library_reconcile → library_delete.
    if text.casefold() == 'downtify liked songs':
        raise ManualPlaylistError(
            'That name is reserved for liked songs', status_code=409
        )
    return m3u.sanitize_playlist_name(text)


def create_manual_playlist(ctx: LibraryContext, name: str) -> dict[str, Any]:
    safe = _validated_name(name)
    if safe.casefold() in existing_playlist_names(ctx.download_dir):
        raise ManualPlaylistError(
            f'A playlist named {safe!r} already exists', status_code=409
        )
    path = m3u.m3u_path_for(ctx.download_dir, safe)
    written = _write(ctx, [], path)
    logger.info('Created manual playlist {!r} at {}', safe, written)
    return {
        'name': written.stem,
        'manual': True,
        'files': [],
        'count': 0,
    }


@_serialized
def edit_manual_playlist(
    ctx: LibraryContext,
    name: str,
    *,
    add: Optional[list[str]] = None,
    remove: Optional[list[str]] = None,
    remove_entries: Optional[list[tuple[str, int]]] = None,
    allow_duplicates: bool = False,
) -> dict[str, Any]:
    """Add songs at the end and take songs out.

    *remove* takes every copy of a song; *remove_entries* one copy each,
    as ``(file, occurrence)``. A song the playlist already has is only
    added again with *allow_duplicates*: otherwise it is listed in
    ``already`` so the caller can ask.
    """

    path = m3u.find_m3u_for_name(ctx.download_dir, name)
    if path is None:
        raise ManualPlaylistError(
            f'Playlist {name!r} was not found', status_code=404
        )
    _require_manual(path, path.stem)
    current = _read_files(ctx, path)
    present = set(current)
    drop = {_clean_path(item) for item in (remove or []) if _clean_path(item)}
    dropped_at = _occurrence_indexes(current, remove_entries or [])
    files = [
        item
        for index, item in enumerate(current)
        if item not in drop and index not in dropped_at
    ]
    removed = len(current) - len(files)
    seen = set(files)
    added = 0
    already: list[str] = []
    for raw in add or []:
        stored = _clean_path(raw)
        if not stored or stored in drop:
            continue
        if stored in seen and not allow_duplicates:
            if stored in present and stored not in already:
                already.append(stored)
            continue
        if len(files) >= MAX_TRACKS_PER_EDIT:
            raise ManualPlaylistError(
                f'Playlists can hold at most {MAX_TRACKS_PER_EDIT} tracks'
            )
        if resolve_library_file(stored, ctx) is None:
            raise ManualPlaylistError(f'Track not in the library: {stored}')
        files.append(stored)
        seen.add(stored)
        added += 1
    written = _write(ctx, files, path)
    kept = _read_files(ctx, written)
    return {
        'name': written.stem,
        'manual': True,
        'files': kept,
        'count': len(kept),
        'added': added,
        'removed': removed,
        'already': already,
    }


@_serialized
def reorder_manual_playlist(
    ctx: LibraryContext,
    name: str,
    order: list[str],
    *,
    visible: Optional[Collection[str]] = None,
) -> dict[str, Any]:
    """Put the playlist's songs in *order*.

    *order* is every song the caller sees, repeats included, in its new
    place. Anything else means the playlist changed since they loaded it
    (another editor added or removed a song): ``409``, so nobody's edit
    is lost. Songs outside *visible* - hidden from the caller - keep the
    places they had.
    """

    path = m3u.find_m3u_for_name(ctx.download_dir, name)
    if path is None:
        raise ManualPlaylistError(
            f'Playlist {name!r} was not found', status_code=404
        )
    _require_manual(path, path.stem)
    current = _read_files(ctx, path)
    wanted = [_clean_path(item) for item in order if _clean_path(item)]
    slots = [
        index
        for index, item in enumerate(current)
        if visible is None or item in visible
    ]
    if Counter(current[index] for index in slots) != Counter(wanted):
        raise ManualPlaylistError(
            'The playlist changed meanwhile: reload it and try again',
            status_code=409,
        )
    files = list(current)
    for index, item in zip(slots, wanted, strict=True):
        files[index] = item
    written = _write(ctx, files, path)
    kept = _read_files(ctx, written)
    logger.info('Reordered manual playlist {!r}', written.stem)
    return {
        'name': written.stem,
        'manual': True,
        'files': kept,
        'count': len(kept),
    }


def detach_imported_playlist(ctx: LibraryContext, name: str) -> dict[str, Any]:
    """Turn an imported playlist into a Library one (tracks kept).

    Only the M3U changes: it gets the manual marker, so it can be edited
    and no longer counts as downloaded from a link. Its artwork stays
    until the first edit. Unlinking it from its source (catalog row,
    watch) is the caller's job.
    """

    path = m3u.find_m3u_for_name(ctx.download_dir, name)
    if path is None:
        raise ManualPlaylistError(
            f'Playlist {name!r} was not found', status_code=404
        )
    if m3u.is_manual_m3u(path):
        raise ManualPlaylistError(
            f'Playlist {path.stem!r} can already be edited', status_code=409
        )
    text = m3u.read_m3u_text(path)
    if text is None:
        raise ManualPlaylistError(f'Could not read {path.name}')
    lines = text.splitlines()
    if lines[:1] != ['#EXTM3U']:
        lines.insert(0, '#EXTM3U')
    lines.insert(1, m3u.MANUAL_M3U_MARKER)
    try:
        path.write_text(
            '\n'.join(lines) + '\n', encoding='utf-8', newline='\n'
        )
    except OSError as exc:
        raise ManualPlaylistError(f'Could not write {path.name}') from exc
    invalidate_library_paths_cache()
    kept = _read_files(ctx, path)
    logger.info('Detached playlist {!r} from its source', path.stem)
    return {
        'name': path.stem,
        'manual': True,
        'files': kept,
        'count': len(kept),
    }


def copy_playlist(
    ctx: LibraryContext, files: list[str], new_name: str
) -> dict[str, Any]:
    """Save *files* as a new Library playlist called *new_name*."""

    safe = _validated_name(new_name)
    if safe.casefold() in existing_playlist_names(ctx.download_dir):
        raise ManualPlaylistError(
            f'A playlist named {safe!r} already exists', status_code=409
        )
    path = m3u.m3u_path_for(ctx.download_dir, safe)
    # In order, a song the original repeats included.
    cleaned = [_clean_path(item) for item in files if _clean_path(item)]
    written = _write(ctx, cleaned, path)
    kept = _read_files(ctx, written)
    logger.info('Saved a copy of a playlist as {!r}', written.stem)
    return {
        'name': written.stem,
        'manual': True,
        'files': kept,
        'count': len(kept),
    }


@_serialized
def rename_manual_playlist(
    ctx: LibraryContext, name: str, new_name: str
) -> dict[str, Any]:
    """Rename a Library-created playlist. Audio files stay where they are."""

    path = m3u.find_m3u_for_name(ctx.download_dir, name)
    if path is None:
        raise ManualPlaylistError(
            f'Playlist {name!r} was not found', status_code=404
        )
    _require_manual(path, path.stem)
    safe = _validated_name(new_name)
    dest = path.with_name(f'{safe}.m3u')
    if dest.resolve() != path.resolve():
        taken = existing_playlist_names(ctx.download_dir)
        if (
            safe.casefold() in taken
            and path.stem.casefold() != safe.casefold()
        ):
            raise ManualPlaylistError(
                f'A playlist named {safe!r} already exists', status_code=409
            )
        if dest.exists() and dest.resolve() != path.resolve():
            raise ManualPlaylistError(
                f'A playlist named {safe!r} already exists', status_code=409
            )
    files = _read_files(ctx, path)
    explicit_cover = has_explicit_cover(path)
    written = _write(ctx, files, dest)
    if written.resolve() != path.resolve():
        old_cover = path.with_suffix('.jpg')
        if explicit_cover:
            copyfile(old_cover, written.with_suffix('.jpg'))
            keep_explicit_cover(written)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise ManualPlaylistError(f'Could not remove {path.name}') from exc
        if old_cover.resolve() != written.with_suffix('.jpg').resolve():
            try:
                old_cover.unlink(missing_ok=True)
            except OSError:
                logger.opt(exception=True).warning(
                    'Could not remove playlist cover {}', old_cover
                )
    logger.info(
        'Renamed manual playlist {!r} to {!r}', path.stem, written.stem
    )
    kept = _read_files(ctx, written)
    return {
        'name': written.stem,
        'previous': path.stem,
        'manual': True,
        'files': kept,
        'count': len(kept),
    }


@_serialized
def drop_manual_playlist(ctx: LibraryContext, name: str) -> dict[str, Any]:
    """Remove the M3U only — audio files stay on disk."""

    path = m3u.find_m3u_for_name(ctx.download_dir, name)
    if path is None:
        raise ManualPlaylistError(
            f'Playlist {name!r} was not found', status_code=404
        )
    _require_manual(path, path.stem)
    cover = path.with_suffix('.jpg')
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        raise ManualPlaylistError(f'Could not remove {path.name}') from exc
    try:
        cover.unlink(missing_ok=True)
    except OSError:
        logger.opt(exception=True).warning(
            'Could not remove playlist cover {}', cover
        )
    logger.info('Removed manual playlist {!r} (audio kept)', path.stem)
    invalidate_library_paths_cache()
    return {
        'ok': True,
        'playlist': path.stem,
        'files': [],
        'deleted_count': 0,
        'failed_count': 0,
        'failed': [],
        'playlists_affected': [],
        'manual': True,
    }


@_serialized
def prune_files_from_manual_playlists(
    ctx: LibraryContext, filenames: list[str]
) -> list[str]:
    """Drop *filenames* from every manual M3U. Returns playlist names."""

    gone = {
        str(item or '').strip().replace('\\', '/')
        for item in filenames
        if str(item or '').strip()
    }
    if not gone:
        return []
    affected: list[str] = []
    for path in m3u.iter_m3u_files(ctx.download_dir):
        if not m3u.is_manual_m3u(path):
            continue
        files = _read_files(ctx, path)
        kept = [item for item in files if item not in gone]
        if len(kept) == len(files):
            continue
        _write(ctx, kept, path)
        affected.append(path.stem)
    return affected
