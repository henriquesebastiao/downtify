"""An artist's Spotify top songs, kept as a JSON file so they aren't
re-fetched on every visit.

Fetching them is slow - the artist embed, one embed per song for its cover
and album, and an overview request for the play counts (see
:func:`downtify.spotify.artist_top_songs_from_id`) - so the first five are
saved to ``Metadata/ArtistTopSongs/<name>.json``, next to the artist's
photo, banner and profile. It is a cache, not user data: machine-written,
never edited by hand, and separate from ``ArtistData/<name>.json`` on
purpose (a bio or social-link save rewrites that whole file, and deleting
it to re-seed an artist shouldn't touch this one).

Only links and text are stored - the covers stay remote URLs, nothing is
downloaded - and nothing that changes per download: whether a song is in
the library or the queue is worked out live by the UI.

A file is *fresh* for :data:`TTL` (7 days: play counts move daily, the
ranking rarely) and only while it belongs to the Spotify artist id asked
about. :func:`ensure_top_songs` is the one entry point: it creates the file
when it is missing or stale and otherwise just reads it, so the artist
page, the profile seeding and - later - the download pipeline can all call
it whenever they need the songs.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from . import spotify
from .downloader import _sanitize

#: How many of the artist's top songs are kept.
TOP_SONGS_LIMIT = 5
#: How long a saved file is trusted before it is fetched again.
TTL = timedelta(days=7)

_DIRNAME = 'Metadata/ArtistTopSongs'

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def path_for(download_dir: Path, name: str) -> Path:
    """The file for *name*'s top songs, whether or not it exists."""

    return Path(download_dir) / _DIRNAME / f'{_sanitize(name)}.json'


def _lock_for(download_dir: Path, name: str) -> threading.Lock:
    """One lock per artist: a background refresh and a request for the
    same artist queue up behind each other instead of fetching twice."""

    key = str(path_for(download_dir, name)).lower()
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def load(download_dir: Path, name: str) -> Optional[dict[str, Any]]:
    """The saved file, or ``None`` when missing, unreadable or malformed."""

    try:
        data = json.loads(
            path_for(download_dir, name).read_text(encoding='utf-8')
        )
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get('songs'), list):
        return None
    return data


def _parse_time(value: Any) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def is_fresh(
    data: Optional[dict[str, Any]],
    spotify_artist_id: str,
    now: Optional[datetime] = None,
) -> bool:
    """Whether *data* can be served as is: it belongs to
    *spotify_artist_id* (a corrected id must not keep serving the old
    artist's songs) and was fetched less than :data:`TTL` ago."""

    if not data or str(data.get('artist_id') or '') != spotify_artist_id:
        return False
    fetched = _parse_time(data.get('fetched_at'))
    if fetched is None:
        return False
    return (now or datetime.now(timezone.utc)) - fetched < TTL


def cached(
    download_dir: Path, name: str, spotify_artist_id: str
) -> tuple[Optional[dict[str, Any]], bool]:
    """``(saved file or None, is it fresh)`` - no network."""

    data = load(download_dir, name)
    return data, is_fresh(data, spotify_artist_id)


def _write(download_dir: Path, name: str, data: dict[str, Any]) -> None:
    """Write atomically (temp file, then rename): a reader never sees a
    half-written file, even with a request racing a background refresh."""

    path = path_for(download_dir, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            Path(tmp).unlink()
        raise


def _fetch(spotify_artist_id: str) -> dict[str, Any]:
    artist_name, cover_url, songs = spotify.artist_top_songs_from_id(
        spotify_artist_id, limit=TOP_SONGS_LIMIT
    )
    return {
        'source': 'spotify',
        'artist_id': spotify_artist_id,
        'name': artist_name,
        'cover_url': cover_url,
        'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'songs': songs,
    }


def ensure_top_songs(
    download_dir: Path, name: str, spotify_artist_id: str
) -> dict[str, Any]:
    """*name*'s top songs: the saved file while it is fresh, otherwise
    fetched from Spotify and saved.

    The single entry point - the artist page, the profile seeding and the
    download pipeline all go through it, so a missing or stale file gets
    (re)created by whoever needs it first. Blocking (seconds when it has
    to fetch): run it off the event loop.

    A failed refresh falls back to the stale file when there is one; with
    nothing saved the error propagates. An empty shelf is returned but not
    saved, so a transient failure isn't trusted for a week.
    """

    if not spotify_artist_id:
        raise ValueError('No Spotify artist id')
    with _lock_for(download_dir, name):
        # Re-read under the lock: whoever held it may just have written it.
        saved = load(download_dir, name)
        if is_fresh(saved, spotify_artist_id):
            return saved  # type: ignore[return-value]
        try:
            data = _fetch(spotify_artist_id)
        except Exception:
            if saved is not None and saved.get('artist_id') == (
                spotify_artist_id
            ):
                logger.opt(exception=True).warning(
                    'Top songs refresh failed for {}; serving the saved file',
                    name,
                )
                return saved
            raise
        if data['songs']:
            _write(download_dir, name, data)
        return data


def refresh_in_background(
    download_dir: Path, name: str, spotify_artist_id: str
) -> bool:
    """Start :func:`ensure_top_songs` on a daemon thread when the file is
    missing or stale and nobody is already fetching it; returns whether a
    thread was started. Never raises and never blocks - for callers (the
    profile seeding) that want the file made without waiting for it."""

    if not spotify_artist_id:
        return False
    _, fresh = cached(download_dir, name, spotify_artist_id)
    if fresh or _lock_for(download_dir, name).locked():
        return False

    def run() -> None:
        try:
            ensure_top_songs(download_dir, name, spotify_artist_id)
        except Exception:
            logger.opt(exception=True).debug(
                'Background top songs fetch failed for {}', name
            )

    threading.Thread(
        target=run, name='downtify-top-songs', daemon=True
    ).start()
    return True
