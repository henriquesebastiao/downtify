"""Unified library listing and safe path resolution for player + UI."""

from __future__ import annotations

import os
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from .library_cache_keys import file_content_key_from_name_and_size
from .library_metadata import library_entry_for_file
from .library_metadata_cache import LibraryMetadataCache
from .library_paths import (
    ResolvedLibraryRoots,
    library_stored_path,
    locate_library_file,
)
from .library_paths_cache import (
    get_cached_path_pairs,
    get_cached_track_entries,
    listing_lock,
    store_cached_track_entries,
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
    extra_dirs: tuple[Path, ...] = ()
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
    from .external_library import extra_dirs_from_settings  # noqa: PLC0415  # import cycle

    extra_dirs = extra_dirs_from_settings(
        settings, Path(download_dir), slskd_dir
    )
    return LibraryContext(
        download_dir=Path(download_dir),
        slskd_dir=slskd_dir,
        extra_dirs=extra_dirs,
        track_index=track_index,
        metadata_cache=metadata_cache,
        playlist_catalog=playlist_catalog,
    )


#: Marker in the name of the working copy a library upgrade writes
#: before swapping it in (see ``downtify.library_upgrade``). It lives in
#: the library folder for the few seconds a rewrite takes, and must
#: never show up as a track of its own.
UPGRADE_STAGING_MARKER = '.downtify-upgrade'

#: Cap on ``GET /tracks?limit=`` and ``POST /api/library/lookup``.
TRACK_QUERY_LIMIT_MAX = 200
LOOKUP_SONG_MAX = 200

# Same rules as ``frontend/src/lib/library.js`` ``songKey``.
_SAME_SONG_TAG = re.compile(
    r'[([](?:(?:feat|ft|with)\b|[^)\]]*remaster)[^)\]]*[)\]]',
    re.IGNORECASE,
)
_FEAT_TAIL = re.compile(r'\s(feat|ft)\.?\s.*$')
_REMASTER_TAIL = re.compile(r'\s-\s[^-]*remaster[^-]*$')
_ARTIST_SPLIT = re.compile(r',|;| & ')

#: Top-level folder podcast episodes live under (see
#: ``downtify.podcasts``). Excluded from the library scan below, so
#: episodes never show up as tracks, albums or artists, and never reach
#: an Upgrade library run — they have no Spotify track id and no lyrics
#: to look for, and neither module needs to know podcasts exist.
PODCASTS_DIRNAME = 'Podcasts'


#: Sidecar artwork Downtify writes (playlist covers) or that already
#: sits beside downloaded tracks.
IMAGE_EXTENSIONS = frozenset({'.jpg', '.jpeg', '.png', '.webp'})


def _is_audio(path: Path) -> bool:
    if UPGRADE_STAGING_MARKER in path.name:
        return False
    return path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS


def _is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def _resolve_within_library(
    stored: str,
    ctx: LibraryContext,
    accept: Callable[[Path], bool],
) -> Optional[Path]:
    """A library-relative path, confined to the library's own folders."""

    text = str(stored or '').strip().replace('\\', '/')
    if not text or text.startswith('/'):
        return None
    if '\0' in text:
        return None

    candidate = locate_library_file(
        text, ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs
    )
    if candidate is None or not accept(candidate):
        return None

    allowed_roots = [ctx.download_dir.resolve()]
    if ctx.slskd_dir is not None:
        slskd_resolved = ctx.slskd_dir.resolve()
        if slskd_resolved not in allowed_roots:
            allowed_roots.append(slskd_resolved)
    for extra in ctx.extra_dirs:
        try:
            extra_resolved = extra.resolve()
        except OSError:
            extra_resolved = extra
        if extra_resolved not in allowed_roots:
            allowed_roots.append(extra_resolved)

    for root in allowed_roots:
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    return None


def resolve_library_file(stored: str, ctx: LibraryContext) -> Optional[Path]:
    """Resolve a library-relative path if it points to an allowed audio file."""

    return _resolve_within_library(stored, ctx, _is_audio)


def resolve_library_image(stored: str, ctx: LibraryContext) -> Optional[Path]:
    """Resolve a library-relative path to a cover image sitting in the library.

    Same path-traversal confinement as :func:`resolve_library_file`, for
    the sidecar artwork saved next to a playlist's M3U (see
    ``downtify.downloader.save_playlist_cover``).
    """

    return _resolve_within_library(stored, ctx, _is_image)


def _under_podcasts(file_path: Path, download_dir: Path) -> bool:
    try:
        file_path.relative_to(download_dir / PODCASTS_DIRNAME)
    except ValueError:
        return False
    return True


def _register_path(
    file_path: Path,
    ctx: LibraryContext,
    by_resolved: dict[str, str],
    roots: ResolvedLibraryRoots,
) -> None:
    if UPGRADE_STAGING_MARKER in file_path.name:
        return
    if file_path.suffix.lower() not in AUDIO_EXTENSIONS:
        return
    try:
        resolved = file_path.resolve()
    except OSError:
        return
    if _under_podcasts(resolved, ctx.download_dir):
        return
    resolved_key = str(resolved)
    if resolved_key in by_resolved:
        return
    by_resolved[resolved_key] = roots.stored_for(resolved)


def _walk_audio_files(root: Path, *, prune_podcasts: bool = False):
    """Yield audio files under *root* without visiting every other file."""

    try:
        if not root.is_dir():
            return
    except OSError:
        return
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        if prune_podcasts and current == root:
            dirnames[:] = [
                name for name in dirnames if name != PODCASTS_DIRNAME
            ]
        for name in filenames:
            if UPGRADE_STAGING_MARKER in name:
                continue
            suffix = Path(name).suffix.lower()
            if suffix not in AUDIO_EXTENSIONS:
                continue
            yield current / name


def _scan_library_path_pairs(ctx: LibraryContext) -> list[tuple[str, str]]:
    """Scan disk for playable ``(stored, resolved)`` pairs (uncached)."""

    by_resolved: dict[str, str] = {}
    roots = ResolvedLibraryRoots.from_dirs(
        ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs
    )

    for path in _walk_audio_files(ctx.download_dir, prune_podcasts=True):
        _register_path(path, ctx, by_resolved, roots)

    if ctx.slskd_dir is not None and roots.slskd != roots.download:
        for path in _walk_audio_files(ctx.slskd_dir):
            _register_path(path, ctx, by_resolved, roots)

    for extra_resolved, _folder_id in roots.extras:
        if extra_resolved == roots.download:
            continue
        if roots.slskd is not None and extra_resolved == roots.slskd:
            continue
        for path in _walk_audio_files(extra_resolved):
            _register_path(path, ctx, by_resolved, roots)

    if ctx.track_index is not None:
        for stored in ctx.track_index.list_filenames():
            full = resolve_library_file(stored, ctx)
            if full is not None:
                by_resolved[str(full.resolve())] = library_stored_path(
                    full, ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs
                )

    return sorted(
        ((stored, resolved) for resolved, stored in by_resolved.items()),
        key=lambda item: item[0],
    )


def list_library_path_pairs(ctx: LibraryContext) -> list[tuple[str, str]]:
    """Playable library entries as ``(stored key, resolved path)``."""

    return get_cached_path_pairs(ctx, _scan_library_path_pairs)


def list_library_paths(ctx: LibraryContext) -> list[str]:
    """All playable library entries (downloads, slskd, extra folders)."""

    return [stored for stored, _resolved in list_library_path_pairs(ctx)]


def _attach_playlists_to_entries(
    entries: list[dict[str, Any]],
    pairs: list[tuple[str, Path]],
    catalog: PlaylistCatalog,
) -> None:
    content_keys: list[str] = []
    filenames: list[str] = []
    ck_by_file: dict[str, str] = {}
    size_by_file = {
        str(entry.get('file') or '').replace('\\', '/'): int(
            entry.get('size') or 0
        )
        for entry in entries
    }
    for stored, full in pairs:
        name = str(stored or '').strip().replace('\\', '/')
        if name:
            filenames.append(name)
        ck = file_content_key_from_name_and_size(
            full.name, size_by_file.get(name, 0)
        )
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


def _attach_m3u_playlists_to_entries(
    entries: list[dict[str, Any]], ctx: LibraryContext
) -> None:
    from .playlist_listing import list_library_playlists  # noqa: PLC0415  # import cycle

    by_file: dict[str, set[str]] = {}
    for playlist in list_library_playlists(
        ctx.download_dir, ctx.slskd_dir, ctx.extra_dirs
    ):
        name = str(playlist.get('name') or '')
        if not name:
            continue
        for stored in playlist.get('files') or []:
            by_file.setdefault(str(stored), set()).add(name)
    if not by_file:
        return
    for entry in entries:
        extra = by_file.get(str(entry.get('file') or ''))
        if not extra:
            continue
        names = set(entry.get('playlists') or [])
        names.update(extra)
        entry['playlists'] = sorted(names)


def list_library_entries(
    ctx: LibraryContext,
    *,
    fold_extra: bool = True,
) -> list[dict[str, Any]]:
    """Playable library rows with title/artist from embedded tags.

    ``fold_extra`` (default) drops extra-folder duplicates and remaps
    artist names. Sync passes ``False`` so it can log those skips itself.
    """

    with listing_lock():
        if fold_extra:
            cached = get_cached_track_entries(ctx)
            if cached is not None:
                return cached

        path_rows = list_library_path_pairs(ctx)
        pairs: list[tuple[str, Path]] = [
            (stored, Path(resolved)) for stored, resolved in path_rows
        ]
        cache = ctx.metadata_cache
        if cache is not None:
            entries = cache.get_entries_batch(pairs)
        else:
            entries = [
                library_entry_for_file(stored, full) for stored, full in pairs
            ]
        if ctx.playlist_catalog is not None and entries:
            _attach_playlists_to_entries(entries, pairs, ctx.playlist_catalog)
        if entries:
            _attach_m3u_playlists_to_entries(entries, ctx)
        if not fold_extra:
            return entries
        from .external_library import (  # noqa: PLC0415  # import cycle
            finish_library_entries,
        )

        entries = finish_library_entries(entries)
        store_cached_track_entries(ctx, entries, paths=path_rows)
        return entries


def list_entries_for_stored_paths(
    ctx: LibraryContext,
    stored_paths: list[str],
) -> list[dict[str, Any]]:
    """``GET /tracks`` rows for an explicit list of library keys.

    Used when a playlist page only needs its own songs, not the whole
    library. Order follows *stored_paths*.
    """

    pairs: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for stored in stored_paths:
        name = str(stored or '').strip().replace('\\', '/')
        if not name or name in seen:
            continue
        seen.add(name)
        full = resolve_library_file(name, ctx)
        if full is not None:
            pairs.append((name, full))
    cache = ctx.metadata_cache
    if cache is not None:
        by_file = {
            str(row.get('file') or ''): row
            for row in cache.get_entries_batch(pairs)
        }
        return [by_file[name] for name, _full in pairs if name in by_file]
    return [library_entry_for_file(stored, full) for stored, full in pairs]


def fold_text(text: str) -> str:
    """Case- and accent-fold, matching the Library page's filter."""

    nfkd = unicodedata.normalize('NFD', str(text or ''))
    stripped = ''.join(
        char for char in nfkd if unicodedata.category(char) != 'Mn'
    )
    return stripped.casefold()


def song_key(artist: str, title: str) -> str:
    """Loose already-downloaded key; keep in sync with ``songKey`` in JS."""

    def clean(text: str) -> str:
        folded = fold_text(text)
        folded = _SAME_SONG_TAG.sub(' ', folded)
        folded = _FEAT_TAIL.sub(' ', folded)
        folded = _REMASTER_TAIL.sub(' ', folded)
        folded = ''.join(ch if ch.isalnum() else ' ' for ch in folded)
        return ' '.join(folded.split())

    first = _ARTIST_SPLIT.split(str(artist or ''), maxsplit=1)[0].strip()
    return f'{clean(first)}|{clean(title)}'


def album_artist_of(entry: dict[str, Any]) -> str:
    """The name Library grouping uses (album artist, else first artist)."""

    album_artist = str(entry.get('album_artist') or '').strip()
    if album_artist:
        return album_artist
    return str(entry.get('artist') or '').split(';')[0].strip()


def _group_albums(
    entries: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    albums: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        album = str(entry.get('album') or '').strip()
        if not album:
            continue
        artist = album_artist_of(entry)
        key = (artist.casefold(), album.casefold())
        bucket = albums.get(key)
        if bucket is None:
            bucket = {
                'title': album,
                'artist': artist,
                'year': str(entry.get('year') or ''),
                'added': int(entry.get('added') or 0),
                'tracks': [],
            }
            albums[key] = bucket
        bucket['tracks'].append(entry)
        bucket['added'] = max(bucket['added'], int(entry.get('added') or 0))
        if not bucket['year'] and entry.get('year'):
            bucket['year'] = str(entry.get('year') or '')
    return albums


def filter_library_entries(
    entries: list[dict[str, Any]],
    *,
    artist: str = '',
    album: str = '',
    q: str = '',
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Subset of listing rows for ``GET /tracks`` query filters."""

    want_artist = str(artist or '').strip().casefold()
    want_album = str(album or '').strip().casefold()
    words = [word for word in fold_text(q).split() if word]
    cap = min(max(int(limit or 0), 0), TRACK_QUERY_LIMIT_MAX)
    out: list[dict[str, Any]] = []
    for entry in entries:
        if want_artist and album_artist_of(entry).casefold() != want_artist:
            continue
        if want_album:
            tagged = str(entry.get('album') or '').strip().casefold()
            if tagged != want_album:
                continue
        if words:
            haystack = fold_text(
                ' '.join((
                    str(entry.get('title') or ''),
                    str(entry.get('artist') or ''),
                    str(entry.get('album') or ''),
                    str(entry.get('file') or ''),
                ))
            )
            if not all(word in haystack for word in words):
                continue
        out.append(entry)
        if cap and len(out) >= cap:
            break
    return out


def lookup_library_songs(
    ctx: LibraryContext, songs: Sequence[Any]
) -> list[dict[str, Any]]:
    """``GET /tracks`` rows that match search/link songs already downloaded."""

    wanted: list[str] = []
    seen_keys: set[str] = set()
    for raw in songs[:LOOKUP_SONG_MAX]:
        if not isinstance(raw, dict):
            continue
        artist = str(raw.get('artist') or '').strip()
        artists = raw.get('artists')
        if not artist and isinstance(artists, list) and artists:
            artist = str(artists[0] or '').strip()
        title = str(raw.get('title') or raw.get('name') or '').strip()
        key = song_key(artist, title)
        if key == '|' or key in seen_keys:
            continue
        seen_keys.add(key)
        wanted.append(key)
    if not wanted:
        return []
    pending = set(wanted)
    found: list[dict[str, Any]] = []
    found_keys: set[str] = set()
    for entry in list_library_entries(ctx):
        key = song_key(
            str(entry.get('artist') or ''),
            str(entry.get('title') or ''),
        )
        if key not in pending or key in found_keys:
            continue
        found_keys.add(key)
        found.append(entry)
        if len(found_keys) == len(pending):
            break
    return found


def library_album_index(ctx: LibraryContext) -> list[dict[str, Any]]:
    """Albums for the Library grid: counts and a cover file, not every track."""

    grouped = _group_albums(list_library_entries(ctx))
    rows: list[dict[str, Any]] = []
    for bucket in grouped.values():
        tracks = bucket['tracks']
        cover_file = ''
        duration = 0.0
        size = 0
        for track in tracks:
            duration += float(track.get('duration') or 0)
            size += int(track.get('size') or 0)
            if not cover_file and track.get('has_cover'):
                cover_file = str(track.get('file') or '')
        rows.append({
            'title': bucket['title'],
            'artist': bucket['artist'],
            'year': bucket['year'],
            'added': int(bucket['added'] or 0),
            'duration': duration,
            'size': size,
            'track_count': len(tracks),
            'cover_file': cover_file,
        })
    rows.sort(
        key=lambda row: (-int(row['added']), str(row['title']).casefold())
    )
    return rows


def library_artist_index(
    ctx: LibraryContext,
    liked_paths: Optional[set[str]] = None,
) -> list[dict[str, Any]]:
    """Artists for the Library grid and Discover, without every track row."""

    liked = liked_paths or set()
    artists: dict[str, dict[str, Any]] = {}
    for entry in list_library_entries(ctx):
        name = album_artist_of(entry)
        if not name:
            continue
        key = name.casefold()
        bucket = artists.get(key)
        if bucket is None:
            bucket = {
                'name': name,
                'added': 0,
                'duration': 0.0,
                'track_count': 0,
                'liked_count': 0,
                'album_count': 0,
                'cover_file': '',
                '_albums': set(),
            }
            artists[key] = bucket
        bucket['track_count'] += 1
        bucket['duration'] += float(entry.get('duration') or 0)
        bucket['added'] = max(
            int(bucket['added'] or 0), int(entry.get('added') or 0)
        )
        stored = str(entry.get('file') or '').replace('\\', '/')
        if stored in liked:
            bucket['liked_count'] += 1
        if not bucket['cover_file'] and entry.get('has_cover'):
            bucket['cover_file'] = stored
        album = str(entry.get('album') or '').strip()
        if album:
            bucket['_albums'].add(album.casefold())
    rows: list[dict[str, Any]] = []
    for bucket in artists.values():
        album_keys = bucket.pop('_albums')
        bucket['album_count'] = len(album_keys)
        rows.append(bucket)
    rows.sort(key=lambda row: str(row['name']).casefold())
    return rows


def library_home_summary(
    ctx: LibraryContext, *, recent_albums: int = 12
) -> dict[str, Any]:
    """Counts and a short recent-album shelf for the Home page."""

    entries = list_library_entries(ctx)
    albums = _group_albums(entries)
    artists: set[str] = set()
    total_size = 0
    for entry in entries:
        total_size += int(entry.get('size') or 0)
        name = album_artist_of(entry)
        if name:
            artists.add(name.casefold())
    recent = sorted(albums.values(), key=lambda row: -int(row['added']))[
        :recent_albums
    ]
    return {
        'track_count': len(entries),
        'album_count': len(albums),
        'artist_count': len(artists),
        'size': total_size,
        'recent_albums': recent,
    }
