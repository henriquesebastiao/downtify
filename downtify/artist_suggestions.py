"""Artists to follow, suggested on the Monitor page's Artists tab.

Two lists, ranked from what the server already keeps - nothing is
searched for while they load:

* **listening**: the user's own listens (``DiscoverStore.listens``),
  each artist's plays faded by how long ago they were last played, with
  Discover's half-life (:data:`downtify.discover.LISTEN_HALF_LIFE_DAYS`);
* **library**: the artists of the library the user can see, by track
  count, then album count.

Artists the user already watches (paused watches too) and compilation
placeholders (``Various Artists``) are left out. Following one is a
separate step: :func:`artist_candidates` picks the YouTube Music artist
an artist watch follows, or leaves the choice to the user.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
from urllib.parse import urlsplit

from .discover import LISTEN_HALF_LIFE_DAYS, artist_key
from .monitor import KIND_ARTIST

#: Album artists of compilations, never an artist to follow.
_PLACEHOLDERS = frozenset(
    artist_key(name)
    for name in (
        'Various Artists',
        'Various Artist',
        'Various',
        'Artistes divers',
        'Unknown',
        'Unknown Artist',
    )
)
#: A YouTube Music artist's channel id; anything else isn't offered.
_CHANNEL_ID = re.compile(r'UC[A-Za-z0-9_-]{22}')
#: Where a YouTube Music artist's photo is served from. A photo from
#: anywhere else is dropped, not shown.
_PHOTO_HOSTS = frozenset({
    'yt3.ggpht.com',
    'yt3.googleusercontent.com',
    'lh3.googleusercontent.com',
})


def _parse_time(value: Any) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _page(
    rows: list[dict[str, Any]], offset: int, limit: int
) -> dict[str, Any]:
    end = offset + limit
    return {
        'items': rows[offset:end],
        'total': len(rows),
        'next_offset': end if end < len(rows) else None,
    }


def artist_suggestions(
    library: Iterable[dict[str, Any]],
    listens: Iterable[dict[str, Any]],
    watches: Iterable[Any],
    *,
    listening_offset: int = 0,
    library_offset: int = 0,
    limit: int = 20,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """One page of each list: ``{listening, library, half_life_days}``.

    *library* is ``library_artist_index`` rows, *listens* the user's
    ``DiscoverStore.listens`` and *watches* their monitor watches - the
    caller scopes all three to the user asking. Each list is ``{items,
    total, next_offset}``; an item is ``{name, track_count,
    album_count}``, and a listening one also has ``plays`` (every listen
    counted), ``score`` (the faded plays it is ranked by) and
    ``last_played``. A listen with no readable time is left out.
    """

    now = now or datetime.now(timezone.utc)
    skip = _PLACEHOLDERS | {
        artist_key(watch.name)
        for watch in watches
        if watch.kind == KIND_ARTIST
    }
    counts: dict[str, dict[str, Any]] = {}
    for row in library:
        name = str(row.get('name') or '').strip()
        key = artist_key(name)
        if not key or key in skip:
            continue
        bucket = counts.setdefault(
            key, {'name': name, 'track_count': 0, 'album_count': 0}
        )
        bucket['track_count'] += max(0, int(row.get('track_count') or 0))
        bucket['album_count'] += max(0, int(row.get('album_count') or 0))
    in_library = sorted(
        (row for row in counts.values() if row['track_count']),
        key=lambda row: (
            -row['track_count'],
            -row['album_count'],
            row['name'].casefold(),
        ),
    )

    played: dict[str, dict[str, Any]] = {}
    for row in listens:
        name = str(row.get('name') or '').strip()
        key = artist_key(name)
        plays = max(0, int(row.get('plays') or 0))
        last = _parse_time(row.get('last_played'))
        if not key or key in skip or not plays or last is None:
            continue
        age_days = max(0.0, (now - last).total_seconds() / 86400)
        bucket = played.get(key)
        if bucket is None:
            known = counts.get(key, {'name': name})
            bucket = played[key] = {
                'name': known['name'],
                'track_count': known.get('track_count', 0),
                'album_count': known.get('album_count', 0),
                'plays': 0,
                'score': 0.0,
                'last_played': last,
            }
        bucket['plays'] += plays
        bucket['score'] += plays * 0.5 ** (age_days / LISTEN_HALF_LIFE_DAYS)
        bucket['last_played'] = max(bucket['last_played'], last)
    listening = sorted(
        played.values(),
        key=lambda row: (-row['score'], row['name'].casefold()),
    )
    for row in listening:
        row['score'] = round(row['score'], 3)
        row['last_played'] = (
            row['last_played'].astimezone(timezone.utc).isoformat()
        )

    return {
        'listening': _page(listening, listening_offset, limit),
        'library': _page(in_library, library_offset, limit),
        'half_life_days': LISTEN_HALF_LIFE_DAYS,
    }


def _photo(row: dict[str, Any]) -> str:
    value = str(row.get('cover_url') or '')
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return ''
    if (
        parsed.scheme == 'https'
        and parsed.hostname in _PHOTO_HOSTS
        and not parsed.username
        and not parsed.password
        and port in {None, 443}
    ):
        return value
    return ''


def artist_candidates(
    name: str, results: Iterable[dict[str, Any]], *, limit: int = 10
) -> dict[str, Any]:
    """The YouTube Music artists to offer for *name*: ``{candidates,
    url}``.

    *results* are ``providers.search_artists`` rows. ``url`` is set only
    when exactly one of them is named *name* (case and the characters a
    file name can't hold ignored, see :func:`artist_key`): that one is
    followed without asking. Otherwise - namesakes, or no exact name - the
    user picks from ``candidates`` (``{name, artist_id, url,
    image_url}``, the ones named *name* first, at most *limit* - a famous
    name easily has twenty namesakes), never the top result on its own.
    Rows without a valid channel id are left out, and the link is built
    from the id, not taken from the row.
    """

    wanted = artist_key(name)
    named: dict[str, dict[str, str]] = {}
    others: dict[str, dict[str, str]] = {}
    for row in results:
        channel = str(row.get('artist_id') or '')
        if not _CHANNEL_ID.fullmatch(channel):
            continue
        if channel in named or channel in others:
            continue
        candidate = {
            'name': str(row.get('name') or '').strip(),
            'artist_id': channel,
            'url': f'https://music.youtube.com/channel/{channel}',
            'image_url': _photo(row),
        }
        if artist_key(candidate['name']) == wanted:
            named[channel] = candidate
        else:
            others[channel] = candidate
    exact = list(named.values())
    return {
        'candidates': [*exact, *others.values()][:limit],
        'url': exact[0]['url'] if len(exact) == 1 else None,
    }
