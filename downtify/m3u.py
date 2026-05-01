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
from typing import Iterable, Optional

from loguru import logger

_PLAYLIST_NAME_ALLOWED = re.compile(r'[^A-Za-z0-9 _-]+')


def sanitize_playlist_name(name: str) -> str:
    """Strip filesystem-unsafe characters from a playlist name.

    Keeps alphanumerics, spaces, hyphens and underscores; drops the rest.
    Returns ``'playlist'`` if nothing is left after sanitising so we
    never produce an empty filename.
    """

    if not name:
        return 'playlist'
    cleaned = _PLAYLIST_NAME_ALLOWED.sub('', name).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned or 'playlist'


def build_m3u_content(
    entries: Iterable[dict],
    *,
    download_dir: Path,
    m3u_dir: Optional[Path] = None,
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
        path = (download_dir / filename).resolve()
        if not path.exists():
            logger.warning('Skipping missing track in M3U: {}', path)
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


def write_m3u(
    download_dir: Path,
    playlist_name: str,
    entries: Iterable[dict],
    *,
    playlist_subdir: Optional[str] = None,
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

    safe_name = sanitize_playlist_name(playlist_name)
    if playlist_subdir:
        target_dir = Path(download_dir) / playlist_subdir
    else:
        target_dir = Path(download_dir) / 'Playlists'
    target_dir.mkdir(parents=True, exist_ok=True)

    content, kept = build_m3u_content(
        list(entries),
        download_dir=Path(download_dir),
        m3u_dir=target_dir,
    )
    if kept == 0:
        logger.warning(
            'Refusing to write empty M3U for playlist {!r}', playlist_name
        )
        return None, 0

    target = target_dir / f'{safe_name}.m3u'
    # UTF-8, no BOM, LF line endings — encoding='utf-8' on text mode
    # gives us no BOM, and we built the content with '\n' already.
    target.write_text(content, encoding='utf-8', newline='\n')
    logger.info('Wrote M3U: {} with {} tracks', target, kept)
    return target, kept
