"""Navidrome plays and stars in Discover (issue #423).

People who listen through a Navidrome client rarely play anything in
Downtify itself, so Discover - which weighs each library artist by how
often it was played and liked here (:func:`downtify.discover.seed_weights`)
- knew only what they owned. With **Use Navidrome plays in Discover** on
(``discover_navidrome_plays``), the plays and starred songs of the
Navidrome account Downtify signs in with count too.

Subsonic only tells an account's own plays, and that account is
whoever's login is in Settings, so they count for admins' Discover only:
another user's suggestions are never built from someone else's
listening.

Plays come per album (``getAlbumList2`` *frequent*), summed per album
artist with the latest play as ``last_played``; stars per song
(``getStarred2``), added to the artist's liked count. Both are fetched at
most every :data:`REFRESH_SECONDS` and kept in memory; a failure keeps
the last answer (or none), never breaks Discover.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

from loguru import logger

from .discover import artist_key
from .navidrome import played_and_starred

#: How long one answer from Navidrome is used before asking again.
REFRESH_SECONDS = 6 * 3600
#: How long to wait before asking again after a failure.
RETRY_SECONDS = 600

_lock = threading.Lock()
_cache: dict[str, Any] = {'key': None, 'at': 0.0, 'taste': None}


def taste_from(answer: dict[str, Any]) -> dict[str, Any]:
    """``{listens, starred}`` from :func:`downtify.navidrome.played_and_starred`:
    ``listens`` rows like :meth:`DiscoverStore.listens` (``{name, plays,
    last_played}``, one per artist), ``starred`` ``{artist key: count}``."""

    plays: dict[str, dict[str, Any]] = {}
    for album in answer.get('albums') or []:
        name = str(album.get('artist') or '').strip()
        key = artist_key(name)
        if not key:
            continue
        row = plays.setdefault(
            key, {'name': name, 'plays': 0, 'last_played': ''}
        )
        row['plays'] += max(0, int(album.get('plays') or 0))
        row['last_played'] = max(
            row['last_played'], str(album.get('played') or '')
        )
    starred: dict[str, int] = {}
    for song in answer.get('starred') or []:
        key = artist_key(str(song.get('artist') or ''))
        if key:
            starred[key] = starred.get(key, 0) + 1
    return {'listens': list(plays.values()), 'starred': starred}


def navidrome_taste(
    cfg: dict[str, Any],
    client_for: Callable[[dict[str, Any]], Any],
    *,
    now: Optional[float] = None,
) -> Optional[dict[str, Any]]:
    """The account's taste (:func:`taste_from`), cached; ``None`` when it
    can't be read and never was."""

    now = time.monotonic() if now is None else now
    key = (cfg.get('url'), cfg.get('username'))
    with _lock:
        fresh = _cache['key'] == key and now < _cache['at']
        if fresh:
            return _cache['taste']
        kept = _cache['taste'] if _cache['key'] == key else None
    try:
        taste = taste_from(played_and_starred(client_for(cfg)))
        wait = REFRESH_SECONDS
    except Exception:
        logger.opt(exception=True).warning(
            'Discover: could not read plays from Navidrome'
        )
        taste, wait = kept, RETRY_SECONDS
    with _lock:
        _cache.update(key=key, at=now + wait, taste=taste)
    return taste


def forget() -> None:
    """Drop the cached answer (tests, or the settings changed)."""

    with _lock:
        _cache.update(key=None, at=0.0, taste=None)


class StoreWithNavidrome:
    """A :class:`DiscoverStore` whose ``listens`` also has Navidrome's
    plays: what :func:`downtify.discover.recommendations` and the
    collections read, without them knowing about Navidrome."""

    def __init__(self, store: Any, listens: list[dict[str, Any]]) -> None:
        self._store = store
        self._listens = listens

    def listens(self, user_id: Optional[int] = None) -> list[dict[str, Any]]:
        return [*self._store.listens(user_id), *self._listens]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._store, name)


def with_starred(
    library: list[Any], starred: dict[str, int]
) -> list[dict[str, Any]]:
    """*library* (``{name, tracks, liked}`` per artist) with each artist's
    Navidrome stars added to ``liked``."""

    out: list[dict[str, Any]] = []
    for artist in library:
        if not isinstance(artist, dict):
            continue
        extra = starred.get(artist_key(str(artist.get('name') or '')), 0)
        liked = int(artist.get('liked') or 0) + extra
        out.append({**artist, 'liked': liked} if extra else artist)
    return out
