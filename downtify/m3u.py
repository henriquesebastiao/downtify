"""Build and write Jellyfin-compatible ``.m3u`` playlist files.

The Spotify embed flow gives us the playlist name and an ordered list of
tracks; the downloader gives us the final on-disk filename of every
track that succeeds. Combining the two produces an ``EXTM3U`` file that
Jellyfin (and any other media server that consumes M3U) can pick up so
the playlist appears as a single unit instead of a pile of loose tracks.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, Optional, Sequence

from loguru import logger

from .library_paths import (
    EXTERNAL_LIBRARY_PREFIX,
    SLSKD_LIBRARY_PREFIX,
    ResolvedLibraryRoots,
    locate_library_file,
)

# Only characters that are genuinely illegal in FAT/NTFS/ext filenames are
# dropped. Everything else — including accented and non-Latin letters such
# as "ö" (Sólrún) or "é" (Renata Béranger) — is preserved so folder names
# match the original artist/album/playlist titles.
_PLAYLIST_NAME_INVALID = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
#: Marks an M3U the user built in the Library, so it can be edited
#: without touching downloaded Spotify/YouTube playlists.
MANUAL_M3U_MARKER = '#EXTDOWNTIFY:manual'


def is_manual_m3u(m3u_path: Path) -> bool:
    """True when *m3u_path* was written as a Library-created playlist."""

    try:
        head = m3u_path.read_text(encoding='utf-8')[:2048]
    except OSError:
        return False
    return any(
        line.strip() == MANUAL_M3U_MARKER for line in head.splitlines()[:12]
    )


def iter_m3u_files(download_dir: Path) -> list[Path]:
    """Every ``.m3u`` under *download_dir*, sorted by path."""

    base = Path(download_dir)
    found: list[Path] = []
    try:
        if not base.is_dir():
            return []
    except OSError:
        return []
    for dirpath, _dirnames, filenames in os.walk(base, followlinks=False):
        current = Path(dirpath)
        for name in filenames:
            if name.lower().endswith('.m3u'):
                found.append(current / name)
    found.sort()
    return found


def find_m3u_for_name(
    download_dir: Path, playlist_name: str
) -> Optional[Path]:
    """The M3U whose stem matches *playlist_name* (case-insensitive)."""

    want = str(playlist_name or '').strip().casefold()
    if not want:
        return None
    for path in iter_m3u_files(download_dir):
        if path.stem.casefold() == want:
            return path
    return None


def sanitize_playlist_name(name: str) -> str:
    """Strip filesystem-unsafe characters from a playlist name.

    Removes only characters that are illegal in filenames on common
    filesystems while keeping Unicode letters, digits and punctuation
    intact. Collapses runs of whitespace and trims leading/trailing dots
    and spaces. Returns ``'playlist'`` if nothing is left after
    sanitising so we never produce an empty filename.
    """

    if not name:
        return 'playlist'
    cleaned = _PLAYLIST_NAME_INVALID.sub('', name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().strip('.').strip()
    return cleaned or 'playlist'


def build_m3u_content(
    entries: Iterable[dict],
    *,
    download_dir: Path,
    m3u_dir: Optional[Path] = None,
    slskd_dir: Optional[Path] = None,
    extra_dirs: Optional[Sequence[Path]] = None,
) -> tuple[str, int]:
    """Render the body of a ``.m3u`` file.

    Each entry is a dict with at least ``filename`` and optionally
    ``title``, ``artist`` and ``duration``. Entries whose file does not
    exist on disk are skipped (and logged).

    Track paths are written **relative to the M3U file's directory** so
    the same file works whether it's read from inside the Downtify
    container (``/downloads/...``) or from another consumer that mounts
    the same library at a different root (Jellyfin under
    ``/nas/music/...``, etc). ``m3u_dir`` defaults to
    ``download_dir/Playlists`` to match :func:`write_m3u`.

    Returns ``(content, kept_count)`` so the caller can both write the
    file and report how many tracks ended up in it.
    """

    if m3u_dir is None:
        m3u_dir = download_dir / 'Playlists'
    lines: list[str] = ['#EXTM3U']
    kept = 0
    for entry in entries:
        filename = (entry or {}).get('filename')
        if not filename:
            continue
        # Also finds ``slskd/...`` files left in place under the slskd
        # folder, outside download_dir.
        path = locate_library_file(
            filename, download_dir, slskd_dir, extra_dirs
        )
        if path is None:
            logger.warning('Skipping missing track in M3U: {}', filename)
            continue
        title = (entry.get('title') or '').strip()
        artist = (entry.get('artist') or '').strip()
        duration = entry.get('duration')
        try:
            duration_int = int(duration) if duration is not None else -1
        except (TypeError, ValueError):
            duration_int = -1
        if title or artist:
            label = ' - '.join(p for p in (artist, title) if p)
            lines.append(f'#EXTINF:{duration_int},{label}')
        lines.append(os.path.relpath(path, start=m3u_dir))
        kept += 1
    # Standard M3U uses LF line endings.
    return '\n'.join(lines) + '\n', kept


def read_m3u_tracks(
    m3u_path: Path,
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
    extra_dirs: Optional[Sequence[Path]] = None,
    *,
    keep_missing: bool = False,
) -> list[str]:
    """Return the tracks listed in *m3u_path*, as paths relative to
    *download_dir* (the same shape ``/list`` returns), in file order.

    Inverts the relative-path scheme :func:`build_m3u_content` writes:
    each non-comment line is relative to the M3U's own directory, not to
    *download_dir* (absolute lines are accepted too). Tracks under
    *slskd_dir* — slskd downloads left in place — come back with the
    virtual ``slskd/`` prefix. Lines that don't resolve to an existing
    file under either root are skipped — self-healing when a track was
    deleted or a line is otherwise stale, and a hard guard against a
    malicious or malformed M3U escaping the library via ``../``.
    """

    download_dir = Path(download_dir).resolve()
    slskd_root = Path(slskd_dir).resolve() if slskd_dir else None
    m3u_dir = m3u_path.resolve().parent
    extras = ResolvedLibraryRoots.from_dirs(
        download_dir, slskd_dir, extra_dirs
    ).extras
    try:
        lines = m3u_path.read_text(encoding='utf-8').splitlines()
    except OSError:
        return []

    tracks: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        try:
            resolved = (m3u_dir / line).resolve()
        except OSError:
            continue
        stored = _stored_library_path(
            resolved, download_dir, slskd_root, extras
        )
        if not stored:
            continue
        if resolved.is_file() or keep_missing:
            tracks.append(stored)
    return tracks


def _stored_library_path(
    resolved: Path,
    download_dir: Path,
    slskd_root: Optional[Path],
    extras: Sequence[tuple[Path, str]],
) -> str:
    if resolved.is_relative_to(download_dir):
        return resolved.relative_to(download_dir).as_posix()
    if slskd_root is not None and resolved.is_relative_to(slskd_root):
        rel = resolved.relative_to(slskd_root).as_posix()
        return f'{SLSKD_LIBRARY_PREFIX}{rel}'
    return _extra_stored_path(resolved, extras)


def _extra_stored_path(
    resolved: Path, extras: Sequence[tuple[Path, str]]
) -> str:
    for extra_root, folder_id in extras:
        try:
            rel = resolved.relative_to(extra_root).as_posix()
        except ValueError:
            continue
        return f'{EXTERNAL_LIBRARY_PREFIX}{folder_id}/{rel}'
    return ''


def m3u_path_for(
    download_dir: Path,
    playlist_name: str,
    *,
    playlist_subdir: Optional[str] = None,
) -> Path:
    """Where :func:`write_m3u` would put this playlist's M3U.

    Resolving the path without writing anything lets the playlist's
    cover art be saved beside it before the first track is downloaded —
    see ``downtify.monitor.download_playlist_cover``.
    """

    if playlist_subdir:
        target_dir = Path(download_dir) / playlist_subdir
    else:
        target_dir = Path(download_dir) / 'Playlists'
    return target_dir / f'{sanitize_playlist_name(playlist_name)}.m3u'


def write_m3u(
    download_dir: Path,
    playlist_name: str,
    entries: Iterable[dict],
    *,
    playlist_subdir: Optional[str] = None,
    slskd_dir: Optional[Path] = None,
    extra_dirs: Optional[Sequence[Path]] = None,
    manual: bool = False,
    allow_empty: bool = False,
) -> tuple[Optional[Path], int]:
    """Write an M3U for ``playlist_name``.

    When ``playlist_subdir`` is given the M3U is placed inside that
    per-playlist folder (``download_dir/<playlist_subdir>/<safe>.m3u``)
    so the directory is fully self-contained — handy for browsing on a
    NAS or playing folders directly on Sonos. Otherwise the legacy
    ``download_dir/Playlists/<safe>.m3u`` location is used.

    Returns ``(path, kept)``. ``path`` is ``None`` and ``kept`` is ``0``
    when no track survived the existence check; nothing is written in
    that case.
    """

    target = m3u_path_for(
        download_dir, playlist_name, playlist_subdir=playlist_subdir
    )
    target_dir = target.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    content, kept = build_m3u_content(
        list(entries),
        download_dir=Path(download_dir),
        m3u_dir=target_dir,
        slskd_dir=slskd_dir,
        extra_dirs=extra_dirs,
    )
    if manual:
        lines = content.splitlines()
        if lines[:1] == ['#EXTM3U'] and MANUAL_M3U_MARKER not in lines[:4]:
            lines.insert(1, MANUAL_M3U_MARKER)
            content = '\n'.join(lines) + '\n'
    if kept == 0 and not allow_empty:
        logger.warning(
            'Refusing to write empty M3U for playlist {!r}', playlist_name
        )
        return None, 0

    # UTF-8, no BOM, LF line endings — encoding='utf-8' on text mode
    # gives us no BOM, and we built the content with '\n' already.
    target.write_text(content, encoding='utf-8', newline='\n')
    logger.info('Wrote M3U: {} with {} tracks', target, kept)
    return target, kept
