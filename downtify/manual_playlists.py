"""Playlists the user builds in the Library, stored as marked M3U files.

Downloaded Spotify/YouTube playlists stay read-only here. These ones
live under ``Playlists/`` with ``#EXTDOWNTIFY:manual`` so they can be
edited, and so deleting them never removes the audio files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from loguru import logger

from . import m3u
from .library_catalog import LibraryContext, resolve_library_file
from .library_paths_cache import invalidate_library_paths_cache
from .playlist_mosaic import refresh_manual_playlist_cover

MAX_PLAYLIST_NAME_LEN = 120
MAX_TRACKS_PER_EDIT = 500


class ManualPlaylistError(ValueError):
    """User-facing failure (duplicate name, not manual, missing file)."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _ctx_dirs(
    ctx: LibraryContext,
) -> tuple[Path, Optional[Path], tuple[Path, ...]]:
    return ctx.download_dir, ctx.slskd_dir, tuple(ctx.extra_dirs or ())


def _entries_for(files: list[str]) -> list[dict[str, str]]:
    return [{'filename': name} for name in files]


def _write(ctx: LibraryContext, files: list[str], path: Path) -> Path:
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


def edit_manual_playlist(
    ctx: LibraryContext,
    name: str,
    *,
    add: Optional[list[str]] = None,
    remove: Optional[list[str]] = None,
) -> dict[str, Any]:
    path = m3u.find_m3u_for_name(ctx.download_dir, name)
    if path is None:
        raise ManualPlaylistError(
            f'Playlist {name!r} was not found', status_code=404
        )
    _require_manual(path, path.stem)
    current = _read_files(ctx, path)
    seen = set(current)
    drop = {
        str(item or '').strip().replace('\\', '/')
        for item in (remove or [])
        if str(item or '').strip()
    }
    files = [item for item in current if item not in drop]
    added = 0
    for raw in add or []:
        stored = str(raw or '').strip().replace('\\', '/')
        if not stored or stored in seen or stored in drop:
            continue
        if len(files) >= MAX_TRACKS_PER_EDIT and stored not in seen:
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
        'removed': len(drop & set(current)),
    }


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
    written = _write(ctx, files, dest)
    if written.resolve() != path.resolve():
        old_cover = path.with_suffix('.jpg')
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
