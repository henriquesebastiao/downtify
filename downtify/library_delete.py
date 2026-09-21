"""Delete library files and playlists (disk, catalog, caches)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from .library_catalog import (
    AUDIO_EXTENSIONS,
    PODCASTS_DIRNAME,
    LibraryContext,
    library_context_from_state,
    resolve_library_file,
)
from .library_cleanup import prune_empty_parent_dirs, remove_track_leftovers
from .library_paths import SLSKD_LIBRARY_PREFIX, library_stored_path
from .library_paths_cache import invalidate_library_paths_cache
from .m3u import sanitize_playlist_name
from .track_tag_match import (
    spotify_aligns_with_file_tags,
    spotify_file_tag_mismatch_label,
)


@dataclass
class TagMismatchDeleteContext:
    """Optional caches/indexes used when removing wrong on-disk audio."""

    ctx: LibraryContext
    cover_cache: Any = None
    metadata_cache: Any = None
    playlist_catalog: Any = None
    track_index: Any = None
    navidrome_index: Any = None


def delete_if_spotify_tag_mismatch(
    song: dict[str, Any],
    del_ctx: TagMismatchDeleteContext,
    *,
    playlist_name: str = '',
) -> bool:
    """Delete a library file whose embedded tags disagree with Spotify.

    Returns ``True`` when the file was removed from disk and catalog.
    """

    if not song.get('library_from_tags'):
        return False
    if spotify_aligns_with_file_tags(song):
        return False

    filename = str(song.get('filename') or '').strip().replace('\\', '/')
    if not filename:
        return False

    label = spotify_file_tag_mismatch_label(song)
    pl_note = f' playlist={playlist_name!r}' if playlist_name else ''
    result = delete_library_file(
        filename,
        del_ctx.ctx,
        cover_cache=del_ctx.cover_cache,
        metadata_cache=del_ctx.metadata_cache,
        playlist_catalog=del_ctx.playlist_catalog,
        track_index=del_ctx.track_index,
        navidrome_index=del_ctx.navidrome_index,
    )
    if result.get('deleted'):
        logger.info(
            'library: deleted wrong file {} ({}){}',
            filename,
            label,
            pl_note,
        )
        return True

    logger.warning(
        'library: tag mismatch but delete failed for {} ({}){} — {}',
        filename,
        label,
        pl_note,
        result.get('error') or 'unknown error',
    )
    return False


def tag_mismatch_delete_context_from_state(
    state: Any,
    *,
    download_dir: Optional[Path] = None,
    settings: Optional[dict[str, Any]] = None,
) -> Optional[TagMismatchDeleteContext]:
    """Build delete context from app ``state`` when a downloader is configured."""

    downloader = getattr(state, 'downloader', None)
    if downloader is None:
        return None
    dl_dir = download_dir or Path(downloader.download_dir)
    cfg = (
        settings
        if isinstance(settings, dict)
        else getattr(state, 'settings', {})
    )
    if not isinstance(cfg, dict):
        cfg = {}
    return TagMismatchDeleteContext(
        ctx=library_context_from_state(
            dl_dir,
            cfg,
            track_index=getattr(state, 'track_index', None),
            metadata_cache=getattr(state, 'metadata_cache', None),
            playlist_catalog=getattr(state, 'playlist_catalog', None),
        ),
        cover_cache=getattr(state, 'cover_cache', None),
        metadata_cache=getattr(state, 'metadata_cache', None),
        playlist_catalog=getattr(state, 'playlist_catalog', None),
        track_index=getattr(state, 'track_index', None),
        navidrome_index=getattr(state, 'navidrome_index', None),
    )


def _log_failed_deletes(
    failed: list[dict[str, str]],
    *,
    context: str,
) -> None:
    for item in failed:
        logger.warning(
            '{}: could not delete {} — {}',
            context,
            item.get('file') or '?',
            item.get('error') or 'unknown error',
        )


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
        logger.warning('Library delete: file not found on disk: {}', file_key)
        return {
            'file': file_key,
            'deleted': False,
            'error': 'File not found',
        }

    try:
        full.unlink()
    except OSError as exc:
        logger.warning(
            'Library delete: could not unlink {}: {}',
            full,
            exc,
        )
        return {'file': file_key, 'deleted': False, 'error': str(exc)}
    # Same leftovers DELETE /delete removes: .lrc sidecar, orphaned
    # cover.jpg, and folders left empty (never the library roots).
    root = (
        ctx.slskd_dir
        if ctx.slskd_dir is not None
        and file_key.startswith(SLSKD_LIBRARY_PREFIX)
        else ctx.download_dir
    )
    remove_track_leftovers(full, root)

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

    if affected_playlists:
        logger.info(
            'Library delete: removed {} (playlists: {})',
            file_key,
            ', '.join(affected_playlists),
        )
    else:
        logger.info(
            'Library delete: removed {} (not linked to a playlist in catalog)',
            file_key,
        )
    return {
        'file': file_key,
        'deleted': True,
        'playlists_affected': affected_playlists,
    }


def delete_library_files(
    stored_paths: list[str],
    ctx: LibraryContext,
    state: Any,
    *,
    log_failures: bool = True,
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
        pl_note = (
            f'; playlists: {", ".join(sorted(affected))}'
            if affected
            else '; no playlist catalog links'
        )
        logger.info(
            'Batch library delete: removed {} file(s){}',
            len(deleted),
            pl_note,
        )
    if failed and log_failures:
        _log_failed_deletes(failed, context='Batch library delete')
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
        logger.debug(
            'Playlist folder scan: directory does not exist: {}',
            directory,
        )
        return {
            'deleted': deleted,
            'failed': failed,
            'playlists_affected': [],
        }
    try:
        podcasts_root = (ctx.download_dir / PODCASTS_DIRNAME).resolve()
        is_podcasts_root = directory.resolve() == podcasts_root
    except OSError:
        is_podcasts_root = False
    if is_podcasts_root:
        # A playlist named "Podcasts" would otherwise sweep every show's
        # episodes at once — playlists and podcast subscriptions are
        # deleted through entirely different paths on purpose.
        logger.warning(
            'Refusing to sweep the Podcasts folder as a playlist folder: {}',
            directory,
        )
        return {
            'deleted': deleted,
            'failed': failed,
            'playlists_affected': [],
        }

    logger.debug('Playlist folder scan: {}', directory)
    # Materialized up front: deleting a track can prune its folder.
    for path in list(directory.rglob('*')):
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


def _remove_playlist_m3u_files(
    download_dir: Path,
    playlist_name: str,
    *,
    organize_by_artist: bool,
) -> int:
    removed = 0
    for m3u_path in _m3u_paths_for_playlist(
        download_dir,
        playlist_name,
        organize_by_artist=organize_by_artist,
    ):
        try:
            if m3u_path.is_file():
                m3u_path.unlink()
                removed += 1
                logger.info('Playlist delete: removed M3U {}', m3u_path)
                prune_empty_parent_dirs(m3u_path.parent, download_dir)
        except OSError as exc:
            logger.warning('Could not remove M3U {}: {}', m3u_path, exc)
    return removed


def _remove_playlist_cover_file(
    download_dir: Path,
    playlist_name: str,
    *,
    organize_by_artist: bool,
) -> bool:
    """Remove the playlist's cover art, if any.

    Saved by ``downloader.save_playlist_cover`` at the same path as the
    playlist's M3U, with a ``.jpg`` suffix instead — see
    ``_m3u_paths_for_playlist`` for the candidate locations. Returns
    whether a file was removed.
    """
    for m3u_path in _m3u_paths_for_playlist(
        download_dir,
        playlist_name,
        organize_by_artist=organize_by_artist,
    ):
        cover_path = m3u_path.with_suffix('.jpg')
        try:
            if cover_path.is_file():
                cover_path.unlink()
                logger.info(
                    'Playlist delete: removed cover art {}', cover_path
                )
                prune_empty_parent_dirs(cover_path.parent, download_dir)
                return True
        except OSError as exc:
            logger.warning(
                'Could not remove cover art {}: {}', cover_path, exc
            )
    return False


def _log_playlist_delete_summary(
    playlist_name: str,
    *,
    catalog_count: int,
    deleted_count: int,
    catalog_deleted: int,
    folder_deleted: int,
    failed_count: int,
    m3u_removed: int,
    cover_removed: bool,
) -> None:
    if deleted_count:
        logger.info(
            'Playlist delete finished for {!r}: {} audio file(s) removed '
            '({} from catalog, {} from folder scan), {} failed, {} M3U '
            'file(s), cover removed={}',
            playlist_name,
            deleted_count,
            catalog_deleted,
            folder_deleted,
            failed_count,
            m3u_removed,
            cover_removed,
        )
        return
    logger.warning(
        'Playlist delete finished for {!r}: no audio files removed from disk '
        '(catalog listed {}, failed {}, M3U removed {}, cover removed={})',
        playlist_name,
        catalog_count,
        failed_count,
        m3u_removed,
        cover_removed,
    )


def _delete_playlist_catalog_tracks(
    playlist_name: str,
    ctx: LibraryContext,
    state: Any,
    catalog: Any,
) -> tuple[list[str], list[str], list[dict[str, str]], set[str], set[str]]:
    filenames = catalog.delete_playlist(playlist_name)
    seen = set(filenames)
    logger.info(
        'Playlist delete: catalog had {} registered track file(s) for {!r}',
        len(filenames),
        playlist_name,
    )
    if not filenames:
        logger.info(
            'Playlist delete: no catalog entries for {!r}; '
            'relying on folder scan and M3U cleanup',
            playlist_name,
        )

    batch = delete_library_files(list(seen), ctx, state, log_failures=False)
    downloaded_from_catalog = list(batch['deleted'])
    failed = list(batch['failed'])
    if filenames:
        logger.info(
            'Playlist delete: removed {}/{} catalog track file(s) for {!r}',
            len(downloaded_from_catalog),
            len(filenames),
            playlist_name,
        )
    _log_failed_deletes(failed, context=f'Playlist delete ({playlist_name!r})')
    affected = set(batch.get('playlists_affected') or [])
    return filenames, downloaded_from_catalog, failed, seen, affected


def _delete_playlist_folder_extras(
    playlist_name: str,
    playlist_dir: Path,
    ctx: LibraryContext,
    state: Any,
    *,
    skip_paths: set[str],
    already_deleted: list[str],
) -> tuple[list[str], list[dict[str, str]], list[str], list[str]]:
    extra = _delete_audio_under_dir(
        playlist_dir,
        ctx,
        state,
        skip_paths=skip_paths,
    )
    extra_deleted = [
        fn for fn in extra['deleted'] if fn not in already_deleted
    ]
    merged = list(already_deleted)
    for fn in extra['deleted']:
        if fn not in merged:
            merged.append(fn)
    if extra_deleted:
        logger.info(
            'Playlist delete: removed {} extra track file(s) from {}',
            len(extra_deleted),
            playlist_dir,
        )
    elif playlist_dir.is_dir():
        logger.info(
            'Playlist delete: no extra audio under {} '
            '(folder exists, nothing beyond catalog list)',
            playlist_dir,
        )
    _log_failed_deletes(
        extra['failed'],
        context=f'Playlist delete folder scan ({playlist_name!r})',
    )
    return (
        merged,
        extra['failed'],
        extra_deleted,
        list(extra.get('playlists_affected') or []),
    )


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

    # With organize-by-artist or -album on, tracks live in artist/album
    # folders, not a per-playlist folder — and a same-named album folder
    # must not be swept as if it were the playlist's.
    organize = bool(
        settings.get('organize_by_artist', False)
        or settings.get('organize_by_album', False)
    )
    safe = sanitize_playlist_name(pl_name)
    logger.info(
        'Deleting playlist {!r} (folder={!r}, organized={})',
        pl_name,
        safe,
        organize,
    )

    ctx = library_context_from_state(
        download_dir,
        settings,
        track_index=state.track_index,
    )
    catalog = state.playlist_catalog
    if catalog is None:
        return {'ok': False, 'error': 'Playlist catalog not available'}

    filenames, downloaded_from_catalog, failed, seen, affected = (
        _delete_playlist_catalog_tracks(pl_name, ctx, state, catalog)
    )
    deleted = list(downloaded_from_catalog)
    extra_deleted: list[str] = []

    if not organize:
        deleted, extra_failed, extra_deleted, extra_affected = (
            _delete_playlist_folder_extras(
                pl_name,
                download_dir / safe,
                ctx,
                state,
                skip_paths=seen,
                already_deleted=downloaded_from_catalog,
            )
        )
        failed.extend(extra_failed)
        for pl_name_affected in extra_affected:
            affected.add(pl_name_affected)
    else:
        logger.info(
            'Playlist delete: skipped folder scan for {!r} '
            '(organize by artist/album enabled)',
            pl_name,
        )

    m3u_removed = _remove_playlist_m3u_files(
        download_dir,
        pl_name,
        organize_by_artist=organize,
    )

    affected.add(pl_name)
    if deleted:
        invalidate_library_paths_cache()

    _log_playlist_delete_summary(
        pl_name,
        catalog_count=len(filenames),
        deleted_count=len(deleted),
        catalog_deleted=len(downloaded_from_catalog),
        folder_deleted=len(extra_deleted),
        failed_count=len(failed),
        m3u_removed=m3u_removed,
        cover_removed=_remove_playlist_cover_file(
            download_dir, pl_name, organize_by_artist=organize
        ),
    )

    return {
        'ok': True,
        'playlist': pl_name,
        'files': deleted,
        'deleted_count': len(deleted),
        'failed_count': len(failed),
        'failed': failed,
        'playlists_affected': sorted(affected),
    }
