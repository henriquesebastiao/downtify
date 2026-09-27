"""The downloaded playlists, as ``GET /playlists`` lists them (and, by
track id, ``GET /api/v1/playlists``)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from . import m3u
from .library_paths import library_stored_path
from .likes import is_liked_playlist


def list_library_playlists(
    download_dir: Path, slskd_dir: Optional[Path]
) -> list[dict[str, Any]]:
    """Every playlist on disk, from the ``.m3u`` files Downtify writes for
    playlist/album downloads and Playlist Monitor sweeps (see
    ``downtify/m3u.py``).

    Each M3U file on disk is one playlist, regardless of whether
    *Organize by artist/album* put its tracks in a per-playlist folder or
    scattered them into artist/album folders — the M3U is the one place
    that still records "these tracks belong together, in this order"
    either way. Single tracks and albums downloaded without an M3U
    aren't playlists and don't show up here. The liked songs playlist
    comes first, then the rest by name.
    """

    base = Path(download_dir).resolve()
    if not base.exists():
        return []
    playlists: list[dict[str, Any]] = []
    for m3u_path in sorted(base.rglob('*.m3u')):
        tracks = m3u.read_m3u_tracks(m3u_path, base, slskd_dir)
        if not tracks:
            continue
        # The sidecar artwork save_playlist_cover writes beside the M3U,
        # when the playlist has one of its own.
        cover = m3u_path.with_suffix('.jpg')
        playlists.append({
            'name': m3u_path.stem,
            'files': tracks,
            'count': len(tracks),
            'cover': (
                library_stored_path(cover, base, slskd_dir)
                if cover.is_file()
                else ''
            ),
            # The playlist of hearted songs, not a downloaded one.
            'liked': is_liked_playlist(m3u_path.stem),
        })
    playlists.sort(key=lambda p: (not p['liked'], p['name'].casefold()))
    return playlists
