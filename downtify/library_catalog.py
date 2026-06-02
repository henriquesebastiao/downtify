"""Unified library listing and safe path resolution for player + UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .library_cache_keys import file_content_key
from .library_metadata import library_entry_for_file
from .library_metadata_cache import LibraryMetadataCache
from .library_paths import library_stored_path, locate_library_file
from .library_paths_cache import (
    get_cached_paths,
)
from .playlist_catalog import PlaylistCatalog
from .track_index import TrackIndex

AUDIO_EXTENSIONS = frozenset({
    '.mp3',
    '.m4a',
    '.flac',
    '.ogg',
    '.wav',
    '.aac',
    '.opus',
})


@dataclass(frozen=True)
class LibraryContext:
    download_dir: Path
    slskd_dir: Optional[Path] = None
    track_index: Optional[TrackIndex] = None
    metadata_cache: Optional[LibraryMetadataCache] = None
    playlist_catalog: Optional[PlaylistCatalog] = None


def library_context_from_state(
    download_dir: Path,
    settings: dict[str, Any],
    track_index: Optional[TrackIndex] = None,
    metadata_cache: Optional[LibraryMetadataCache] = None,
    playlist_catalog: Optional[PlaylistCatalog] = None,
) -> LibraryContext:
    slskd_raw = settings.get('slskd')
    slskd_dir: Optional[Path] = None
    if isinstance(slskd_raw, dict):
        source = str(slskd_raw.get('source_dir') or '').strip()
        if source:
            slskd_dir = Path(source)
    return LibraryContext(
        download_dir=Path(download_dir),
        slskd_dir=slskd_dir,
        track_index=track_index,
        metadata_cache=metadata_cache,
        playlist_catalog=playlist_catalog,
    )


def _is_audio(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS


def resolve_library_file(stored: str, ctx: LibraryContext) -> Optional[Path]:
    """Resolve a library-relative path if it points to an allowed audio file."""

    text = str(stored or '').strip().replace('\\', '/')
    if not text or text.startswith('/'):
        return None
    if '\0' in text:
        return None

    candidate = locate_library_file(text, ctx.download_dir, ctx.slskd_dir)
    if candidate is None or not _is_audio(candidate):
        return None

    allowed_roots = [ctx.download_dir.resolve()]
    if ctx.slskd_dir is not None:
        slskd_resolved = ctx.slskd_dir.resolve()
        if slskd_resolved not in allowed_roots:
            allowed_roots.append(slskd_resolved)

    for root in allowed_roots:
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    return None


def _register_path(
    file_path: Path,
    ctx: LibraryContext,
    by_resolved: dict[str, str],
) -> None:
    if not _is_audio(file_path):
        return
    resolved_key = str(file_path.resolve())
    if resolved_key in by_resolved:
        return
    by_resolved[resolved_key] = library_stored_path(
        file_path, ctx.download_dir, ctx.slskd_dir
    )


def _scan_library_paths(ctx: LibraryContext) -> list[str]:
    """Scan disk for playable paths (uncached)."""

    by_resolved: dict[str, str] = {}

    if ctx.download_dir.is_dir():
        for path in ctx.download_dir.rglob('*'):
            if path.is_file():
                _register_path(path, ctx, by_resolved)

    if ctx.slskd_dir is not None and ctx.slskd_dir.is_dir():
        try:
            same_tree = ctx.slskd_dir.resolve() == ctx.download_dir.resolve()
        except OSError:
            same_tree = False
        if not same_tree:
            for path in ctx.slskd_dir.rglob('*'):
                if path.is_file():
                    _register_path(path, ctx, by_resolved)

    if ctx.track_index is not None:
        for stored in ctx.track_index.list_filenames():
            full = resolve_library_file(stored, ctx)
            if full is not None:
                by_resolved[str(full.resolve())] = library_stored_path(
                    full, ctx.download_dir, ctx.slskd_dir
                )

    return sorted(by_resolved.values())


def list_library_paths(ctx: LibraryContext) -> list[str]:
    """All playable library entries (download_dir + slskd tree + index)."""

    return get_cached_paths(ctx, _scan_library_paths)


def _attach_playlists_to_entries(
    entries: list[dict[str, Any]],
    pairs: list[tuple[str, Path]],
    catalog: PlaylistCatalog,
) -> None:
    content_keys: list[str] = []
    filenames: list[str] = []
    ck_by_file: dict[str, str] = {}
    for stored, full in pairs:
        name = str(stored or '').strip().replace('\\', '/')
        if name:
            filenames.append(name)
        ck = file_content_key(full)
        if ck:
            content_keys.append(ck)
            if name:
                ck_by_file[name] = ck
    by_ck = catalog.playlists_by_content_keys(content_keys)
    by_fn = catalog.playlists_by_filenames(filenames)
    for entry in entries:
        fn = str(entry.get('file') or '').replace('\\', '/')
        names: set[str] = set()
        ck = ck_by_file.get(fn)
        if ck:
            names.update(by_ck.get(ck, []))
        names.update(by_fn.get(fn, []))
        if names:
            entry['playlists'] = sorted(names)


def list_library_entries(ctx: LibraryContext) -> list[dict[str, Any]]:
    """Playable library rows with title/artist from embedded tags."""

    pairs: list[tuple[str, Path]] = []
    for stored in list_library_paths(ctx):
        full = resolve_library_file(stored, ctx)
        if full is not None:
            pairs.append((stored, full))
    cache = ctx.metadata_cache
    if cache is not None:
        entries = cache.get_entries_batch(pairs)
    else:
        entries = [
            library_entry_for_file(stored, full) for stored, full in pairs
        ]
    if ctx.playlist_catalog is not None and entries:
        _attach_playlists_to_entries(entries, pairs, ctx.playlist_catalog)
    return entries
