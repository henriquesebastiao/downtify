"""The downloaded playlists, as ``GET /playlists`` lists them (and, by
track id, ``GET /api/v1/playlists``)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional

from . import m3u
from .library_paths import library_stored_path
from .library_paths_cache import get_cached_playlists
from .likes import is_liked_playlist


def list_library_playlists(
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
    extra_dirs: Optional[Sequence[Path]] = None,
) -> list[dict[str, Any]]:
    """Every playlist on disk, from the ``.m3u`` files Downtify writes for
    playlist/album downloads and Playlist Monitor sweeps (see
    ``downtify/m3u.py``), plus playlists the user created in the Library.

    Each M3U file on disk is one playlist, regardless of whether
    *Organize by artist/album* put its tracks in a per-playlist folder or
    scattered them into artist/album folders — the M3U is the one place
    that still records "these tracks belong together, in this order"
    either way. Single tracks and albums downloaded without an M3U
    aren't playlists and don't show up here. The liked songs playlist
    comes first, then the rest by name.
    """

    extras = tuple(extra_dirs or ())
    return get_cached_playlists(
        Path(download_dir),
        slskd_dir,
        extras,
        lambda: _scan_library_playlists(Path(download_dir), slskd_dir, extras),
    )


def _known_library_files(
    download_dir: Path,
    slskd_dir: Optional[Path],
    extra_dirs: tuple[Path, ...],
) -> set[str]:
    from .library_catalog import LibraryContext, list_library_paths  # noqa: PLC0415

    ctx = LibraryContext(
        download_dir=download_dir,
        slskd_dir=slskd_dir,
        extra_dirs=extra_dirs,
    )
    return set(list_library_paths(ctx))


def _scan_library_playlists(
    download_dir: Path,
    slskd_dir: Optional[Path],
    extra_dirs: tuple[Path, ...],
) -> list[dict[str, Any]]:
    base = Path(download_dir).resolve()
    if not base.exists():
        return []
    known = _known_library_files(download_dir, slskd_dir, extra_dirs)
    playlists: list[dict[str, Any]] = []
    for m3u_path in m3u.iter_m3u_files(base):
        manual = m3u.is_manual_m3u(m3u_path)
        tracks = [
            stored
            for stored in m3u.read_m3u_tracks(
                m3u_path,
                base,
                slskd_dir,
                extra_dirs,
                keep_missing=True,
            )
            if stored in known
        ]
        if not tracks and not manual:
            continue
        # The sidecar artwork save_playlist_cover writes beside the M3U,
        # when the playlist has one of its own.
        cover = m3u_path.with_suffix('.jpg')
        playlists.append({
            'name': m3u_path.stem,
            'files': tracks,
            'count': len(tracks),
            'added': int(m3u_path.stat().st_mtime),
            'cover': (
                library_stored_path(cover, base, slskd_dir, extra_dirs)
                if cover.is_file()
                else ''
            ),
            # The playlist of hearted songs, not a downloaded one.
            'liked': is_liked_playlist(m3u_path.stem),
            'manual': manual,
        })
    playlists.sort(key=lambda p: (not p['liked'], p['name'].casefold()))
    return playlists
