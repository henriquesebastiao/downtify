"""The names playlists had on their service when last fetched.

A watch's check reads a playlist's songs, and the same response carries
the playlist's current name. Fetching only the songs keeps that name
here, so the check can notice the playlist was renamed on its service
(see ``downtify.monitor.follow_source_name``) without asking the service
a second time.
"""

from __future__ import annotations

import threading
from collections import OrderedDict

# Enough for every watch of a large library; the oldest go first.
_LIMIT = 5000

_lock = threading.Lock()
_names: OrderedDict[tuple[str, str], str] = OrderedDict()


def remember(service: str, playlist_id: str, name: object) -> None:
    """Note *name* as playlist *playlist_id*'s current name on *service*.

    Nothing is kept for an empty name, or one that is just the id (what
    the fetchers fall back to when the service gave no name).
    """

    clean = str(name or '').strip()
    pid = str(playlist_id or '').strip()
    if not clean or not pid or clean == pid:
        return
    key = (service, pid)
    with _lock:
        _names[key] = clean
        _names.move_to_end(key)
        while len(_names) > _LIMIT:
            _names.popitem(last=False)


def seen(service: str, playlist_id: str) -> str:
    """The name last noted for the playlist, ``''`` when none."""

    with _lock:
        return _names.get((service, str(playlist_id or '').strip()), '')


def forget_all() -> None:
    """Drop every noted name (tests)."""

    with _lock:
        _names.clear()
