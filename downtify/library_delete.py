"""Delete library files and playlists (disk, catalog, caches)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from .library_catalog import (
    AUDIO_EXTENSIONS,
    LibraryContext,
    library_context_from_state,
    resolve_library_file,
)
from .library_paths import library_stored_path
from .library_paths_cache import invalidate_library_paths_cache
from .m3u import sanitize_playlist_name


def delete_library_file(
    stored_path: str,
    ctx: LibraryContext,
    *,
    cover_cache: Any = None,
    metadata_cache: Any = None,
    playlist_catalog: Any = None,
    track_index: Any = None,
    navidrome_index: Any = None,
    invalidate_paths: bool = True,
) -> dict[str, Any]:
    """Remove one library file and catalog rows. Does not refresh playlists."""

    file_key = str(stored_path or '').strip().replace('\\', '/')
    if not file_key:
        return {'file': stored_path, 'deleted': False, 'error': 'Empty path'}

    full = resolve_library_file(file_key, ctx)
    if full is None:
        return {
            'file': file_key,
            'deleted': False,
            'error': 'File not found',
        }

    try:
        full.unlink()
    except OSError as exc:
        return {'file': file_key, 'deleted': False, 'error': str(exc)}

    affected_playlists: list[str] = []
    if cover_cache is not None:
        cover_cache.forget(file_key, full_path=full)
    if metadata_cache is not None:
        metadata_cache.forget(file_key, full_path=full)
    if playlist_catalog is not None:
        affected_playlists = playlist_catalog.remove_tracks_for_filename(
            file_key
        )
    if track_index is not None:
        track_index.remove_by_filename(file_key)
    if navidrome_index is not None:
        navidrome_index.forget_filename(file_key, full_path=full)

    if invalidate_paths:
        invalidate_library_paths_cache()
    return {
        'file': file_key,
        'deleted': True,
        'playlists_affected': affected_playlists,
    }


def delete_library_files(
    stored_paths: list[str],
    ctx: LibraryContext,
    state: Any,
) -> dict[str, Any]:
    """Delete many files; return per-file results and union of affected playlists."""

    seen: set[str] = set()
    deleted: list[str] = []
    failed: list[dict[str, str]] = []
    affected: set[str] = set()

    for raw in stored_paths:
        key = str(raw or '').strip().replace('\\', '/')
        if not key or key in seen:
            continue
        seen.add(key)
        result = delete_library_file(
            key,
            ctx,
            cover_cache=state.cover_cache,
            metadata_cache=state.metadata_cache,
            playlist_catalog=state.playlist_catalog,
            track_index=state.track_index,
            navidrome_index=state.navidrome_index,
            invalidate_paths=False,
        )
        if result.get('deleted'):
            deleted.append(key)
            for pl in result.get('playlists_affected') or []:
                affected.add(str(pl))
        else:
            failed.append({
                'file': key,
                'error': str(result.get('error') or 'Delete failed'),
            })

    if deleted:
        invalidate_library_paths_cache()
    return {
        'deleted': deleted,
        'failed': failed,
        'deleted_count': len(deleted),
        'failed_count': len(failed),
        'playlists_affected': sorted(affected),
    }


def _m3u_paths_for_playlist(
    download_dir: Path,
    playlist_name: str,
    *,
    organize_by_artist: bool,
) -> list[Path]:
    safe = sanitize_playlist_name(playlist_name)
    paths = [
        download_dir / 'Playlists' / f'{safe}.m3u',
        download_dir / safe / f'{safe}.m3u',
    ]
    if organize_by_artist:
        return [paths[0]]
    return paths


def _delete_audio_under_dir(
    directory: Path,
    ctx: LibraryContext,
    state: Any,
    *,
    skip_paths: set[str],
) -> dict[str, Any]:
    """Delete audio files under *directory* not already in *skip_paths*."""

    deleted: list[str] = []
    failed: list[dict[str, str]] = []
    affected: set[str] = set()

    if not directory.is_dir():
        return {
            'deleted': deleted,
            'failed': failed,
            'playlists_affected': [],
        }

    for path in directory.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        stored = library_stored_path(path, ctx.download_dir, ctx.slskd_dir)
        if stored in skip_paths:
            continue
        result = delete_library_file(
            stored,
            ctx,
            cover_cache=state.cover_cache,
            metadata_cache=state.metadata_cache,
            playlist_catalog=state.playlist_catalog,
            track_index=state.track_index,
            navidrome_index=state.navidrome_index,
            invalidate_paths=False,
        )
        if result.get('deleted'):
            deleted.append(stored)
            skip_paths.add(stored)
            for pl in result.get('playlists_affected') or []:
                affected.add(str(pl))
        else:
            failed.append({
                'file': stored,
                'error': str(result.get('error') or 'Delete failed'),
            })

    return {
        'deleted': deleted,
        'failed': failed,
        'playlists_affected': sorted(affected),
    }


def delete_playlist_from_library(
    playlist_name: str,
    download_dir: Path,
    settings: dict[str, Any],
    state: Any,
) -> dict[str, Any]:
    """Delete all tracks for a playlist, remove M3U, drop catalog entry."""

    pl_name = str(playlist_name or '').strip()
    if not pl_name:
        return {'ok': False, 'error': 'Empty playlist name'}

    ctx = library_context_from_state(
        download_dir,
        settings,
        track_index=state.track_index,
    )
    catalog = state.playlist_catalog
    if catalog is None:
        return {'ok': False, 'error': 'Playlist catalog not available'}

    filenames = catalog.delete_playlist(pl_name)
    seen = set(filenames)
    batch = delete_library_files(list(seen), ctx, state)
    deleted = list(batch['deleted'])
    failed = list(batch['failed'])
    affected = set(batch.get('playlists_affected') or [])

    organize = bool(settings.get('organize_by_artist', False))
    if not organize:
        safe = sanitize_playlist_name(pl_name)
        extra = _delete_audio_under_dir(
            download_dir / safe,
            ctx,
            state,
            skip_paths=seen,
        )
        for fn in extra['deleted']:
            if fn not in deleted:
                deleted.append(fn)
        failed.extend(extra['failed'])
        for pl in extra.get('playlists_affected') or []:
            affected.add(pl)

    for m3u_path in _m3u_paths_for_playlist(
        download_dir, pl_name, organize_by_artist=organize
    ):
        try:
            if m3u_path.is_file():
                m3u_path.unlink()
                logger.info('Removed M3U: {}', m3u_path)
        except OSError as exc:
            logger.warning('Could not remove M3U {}: {}', m3u_path, exc)

    affected.add(pl_name)
    if deleted:
        invalidate_library_paths_cache()
    return {
        'ok': True,
        'playlist': pl_name,
        'files': deleted,
        'deleted_count': len(deleted),
        'failed_count': len(failed),
        'failed': failed,
        'playlists_affected': sorted(affected),
    }
