"""Discover: artists the user doesn't have yet, suggested from the ones
they do.

Where the suggestions come from
-------------------------------

Each *seed* is an artist already in the library. How much a seed counts
is its :func:`seed_weights`: how many of its tracks are in the library,
how many of those are liked, and how often (and how recently) the user
actually listened to it - the player reports a listen once a track has
played long enough (see :meth:`DiscoverStore.record_listen`). The
heaviest seeds are then looked up on Deezer, whose public, keyless
``/artist/{id}/related`` answers "fans of this artist also like" (see
:func:`downtify.deezer.related_artists`), and every related artist gets
points from each seed that suggests it (:func:`rank_candidates`). An
artist several of the user's favourites point to beats one only a single
seed mentions.

Last.fm, which other tools use for this, needs an API key; Spotify's own
"Fans also like" needs a Spotify id per seed, and the embed pages this
project relies on (no Web API credentials) only hand that out per track.
Deezer needs neither.

What is never suggested: an artist already in the library, and an artist
on the user's block list (:meth:`DiscoverStore.block`) - "Not interested"
on a suggestion, or a name typed in by hand.

Albums and playlists
--------------------

:func:`collections` builds on the artists above, with the web player's
own search (anonymous, like everything else here - see
:func:`downtify.spotify.search`), one search per artist name:

* **Albums for you** - the top album of each of the best suggested
  artists.
* **More from your artists** - the most popular albums of the user's own
  heaviest artists that aren't in the library yet.
* **Playlists** - Spotify's own "<artist> Radio" mixes for the user's
  heaviest artists (similar music around an artist they already love),
  then its "This Is <artist>" for the best suggested ones.

Every result is a Spotify album or playlist, so opening one lands on the
same page a pasted link does, with the tracks' preview clips. Albums
already in the library and playlists already downloaded are left out.

What is stored
--------------

Four tables in ``downtify_library.db``: the listen counts, the block
list, a per-seed cache of Deezer's answer (the seed's Deezer id and its
related artists) and a per-artist cache of the Spotify search, both
trusted for :data:`RELATED_TTL` so opening the page again doesn't cost a
round of requests - Deezer allows about 50 per 5 seconds, and a cold page
is two per seed.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from . import deezer, spotify
from .file_naming import file_name_key, title_key
from .sqlite_utils import connect_sqlite

#: How long a seed's related artists are trusted before asking Deezer again.
RELATED_TTL = timedelta(days=7)
#: How many of the heaviest library artists are looked up.
MAX_SEEDS = 15
#: How many related artists are asked for per seed.
RELATED_PER_SEED = 20
#: How many suggestions are returned, at most.
RESULT_LIMIT = 48
#: Listening to an artist counts half as much after this many days.
LISTEN_HALF_LIFE_DAYS = 45
#: Deezer requests in flight at once (it rate-limits at ~50 per 5 s).
_WORKERS = 4
#: For Deezer lookups that go through its throttle (discographies,
#: playlists, album matches): more at once is safe, the throttle keeps the
#: overall rate under Deezer's limit.
_THROTTLED_WORKERS = 8
#: How many of the best suggested artists get an album / playlist.
COLLECTION_SUGGESTED = 12
#: How many of the heaviest library artists get albums / a radio mix.
COLLECTION_SEEDS = 6
#: Albums not in the library, at most, per library artist.
MORE_FROM_PER_SEED = 2
#: Spotify's own account, the owner of its editorial playlists.
SPOTIFY_OWNER = 'spotify'
#: How long a Spotify album's Deezer match is trusted: an album found on
#: Deezer stays the same album, one missing may be added any week.
MATCH_TTL_FOUND = timedelta(days=30)
MATCH_TTL_MISSING = RELATED_TTL
#: The per-artist Deezer cache's parts, by name -> column prefix (a fixed
#: list: the name ends up in the SQL).
_DEEZER_PARTS = {'albums': 'albums', 'playlist': 'playlist'}

#: A seed's related artists, best match first (see ``deezer.related_artists``).
Related = list[dict[str, Any]]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def artist_key(name: str) -> str:
    """The key two names of the same artist share: case, spaces and the
    characters a file name can't hold are ignored, so ``AC/DC`` in a tag
    and ``ACDC`` on Deezer are the same artist (see
    :func:`downtify.file_naming.file_name_key`)."""

    return file_name_key(str(name or ''))


def _parse_time(value: Any) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


# ── Ranking (pure) ───────────────────────────────────────────────────────


def seed_weights(
    library: Iterable[dict[str, Any]],
    listens: Iterable[dict[str, Any]],
    now: Optional[datetime] = None,
) -> dict[str, dict[str, Any]]:
    """How much each library artist says about the user's taste.

    *library* is ``{name, tracks, liked}`` per artist in the library;
    *listens* the rows of :meth:`DiscoverStore.listens`. The weight grows
    with each signal but flattens out (``log1p``), so a 400-track
    discography doesn't drown everything else, and listening counts most,
    liking next, owning least. A listen fades with the time since the
    artist was last played (:data:`LISTEN_HALF_LIFE_DAYS`).

    Only artists in *library* can be seeds - a listen to an artist whose
    tracks have since been deleted doesn't count. Returns ``{key: {name,
    weight}}``, keyed by :func:`artist_key`; artists with no weight at all
    are left out.
    """

    now = now or _now()
    plays: dict[str, float] = {}
    for row in listens:
        key = artist_key(row.get('name'))
        if not key:
            continue
        last = _parse_time(row.get('last_played'))
        age_days = (
            max(0.0, (now - last).total_seconds() / 86400) if last else 0
        )
        fade = 0.5 ** (age_days / LISTEN_HALF_LIFE_DAYS)
        plays[key] = (
            plays.get(key, 0.0) + max(0, int(row.get('plays') or 0)) * fade
        )

    weights: dict[str, dict[str, Any]] = {}
    for artist in library:
        name = str(artist.get('name') or '').strip()
        key = artist_key(name)
        if not key:
            continue
        tracks = max(0, int(artist.get('tracks') or 0))
        liked = max(0, int(artist.get('liked') or 0))
        weight = (
            math.log1p(tracks)
            + 1.5 * math.log1p(liked)
            + 2.0 * math.log1p(plays.get(key, 0.0))
        )
        if weight <= 0:
            continue
        entry = weights.setdefault(key, {'name': name, 'weight': 0.0})
        entry['weight'] += weight
    return weights


def pick_seeds(
    weights: dict[str, dict[str, Any]], limit: int = MAX_SEEDS
) -> list[tuple[str, str, float]]:
    """The *limit* heaviest seeds as ``(key, name, weight)``, heaviest
    first (ties by name, so the pick is stable)."""

    ranked = sorted(
        weights.items(),
        key=lambda item: (-item[1]['weight'], item[1]['name'].casefold()),
    )
    return [(key, v['name'], v['weight']) for key, v in ranked[:limit]]


def rank_candidates(
    seeds: list[tuple[str, str, float]],
    related: dict[str, Related],
    exclude: set[str],
    limit: int = RESULT_LIMIT,
) -> list[dict[str, Any]]:
    """Every related artist, scored by the seeds that suggest it.

    A seed gives a related artist its own weight, less the further down
    Deezer's list it sits; an artist several seeds suggest adds up all of
    theirs. Keys in *exclude* (the library, the block list) are never
    suggested, and neither is a seed itself.

    Each result is ``{name, deezer_id, picture_url, fans, score,
    because}`` - ``because`` the names of up to three seeds that suggested
    it, the biggest contributor first. Best first; ties go to the artist
    with more fans.
    """

    seed_keys = {key for key, _name, _weight in seeds}
    found: dict[str, dict[str, Any]] = {}
    for seed_key, seed_name, weight in seeds:
        for position, artist in enumerate(related.get(seed_key) or []):
            key = artist_key(artist.get('name'))
            if not key or key in exclude or key in seed_keys:
                continue
            points = weight / (1 + 0.15 * position)
            entry = found.get(key)
            if entry is None:
                entry = found[key] = {
                    'name': artist['name'],
                    'deezer_id': str(artist.get('deezer_id') or ''),
                    'picture_url': str(artist.get('picture_url') or ''),
                    'fans': int(artist.get('fans') or 0),
                    'score': 0.0,
                    '_by': {},
                }
            entry['score'] += points
            entry['_by'][seed_name] = entry['_by'].get(seed_name, 0) + points

    ranked = sorted(
        found.values(),
        key=lambda e: (-e['score'], -e['fans'], e['name'].casefold()),
    )[:limit]
    for entry in ranked:
        by = entry.pop('_by')
        entry['because'] = sorted(by, key=lambda n: -by[n])[:3]
        entry['score'] = round(entry['score'], 3)
    return ranked


# ── Storage ──────────────────────────────────────────────────────────────


class DiscoverStore:
    """Listen counts, the block list, and the related-artists cache."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self):
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discover_listens (
                    artist_key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    plays INTEGER NOT NULL DEFAULT 0,
                    last_played TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discover_plays (
                    play_id TEXT PRIMARY KEY,
                    recorded_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discover_blocked (
                    artist_key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    blocked_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discover_search (
                    artist_key TEXT PRIMARY KEY,
                    results_json TEXT NOT NULL DEFAULT '{}',
                    fetched_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discover_related (
                    artist_key TEXT PRIMARY KEY,
                    deezer_id TEXT NOT NULL DEFAULT '',
                    related_json TEXT NOT NULL DEFAULT '[]',
                    fetched_at TEXT NOT NULL
                )
            """)
            # An artist's Deezer discography and editorial "100%"
            # playlist, each fetched (and trusted) on its own.
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discover_deezer (
                    artist_key TEXT PRIMARY KEY,
                    albums_json TEXT,
                    albums_at TEXT,
                    playlist_json TEXT,
                    playlist_at TEXT
                )
            """)
            # A Spotify album's match on Deezer - '' ids when Deezer has
            # no such album.
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discover_album_map (
                    spotify_id TEXT PRIMARY KEY,
                    deezer_album_id TEXT NOT NULL DEFAULT '',
                    deezer_artist_id TEXT NOT NULL DEFAULT '',
                    cover_url TEXT NOT NULL DEFAULT '',
                    fetched_at TEXT NOT NULL
                )
            """)

    # Listens

    def record_listen(
        self,
        name: str,
        when: Optional[datetime] = None,
        play_id: str = '',
    ) -> Optional[dict[str, Any]]:
        """Count one listen to *name*. ``None`` for a name with no key.

        *when* is when it was played - an app that was offline reports
        its plays later; a late report never moves ``last_played`` back.
        A *play_id* is counted once: the same play reported twice (a
        retry after a lost answer) doesn't add up.
        """

        name = str(name or '').strip()
        key = artist_key(name)
        if not key:
            return None
        stamp = (when or _now()).isoformat()
        with self._connect() as conn:
            fresh = True
            if play_id:
                cur = conn.execute(
                    'INSERT INTO discover_plays (play_id, recorded_at) '
                    'VALUES (?, ?) ON CONFLICT(play_id) DO NOTHING',
                    (play_id[:64], _now().isoformat()),
                )
                fresh = cur.rowcount > 0
            if fresh:
                conn.execute(
                    """INSERT INTO discover_listens
                       (artist_key, name, plays, last_played)
                       VALUES (?, ?, 1, ?)
                       ON CONFLICT(artist_key) DO UPDATE SET
                         name = excluded.name,
                         plays = plays + 1,
                         last_played = MAX(last_played, excluded.last_played)""",
                    (key, name, stamp),
                )
            row = conn.execute(
                'SELECT name, plays, last_played FROM discover_listens '
                'WHERE artist_key = ?',
                (key,),
            ).fetchone()
        return dict(row)

    def listens(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT name, plays, last_played FROM discover_listens '
                'ORDER BY plays DESC, name'
            ).fetchall()
        return [dict(row) for row in rows]

    def clear_listens(self) -> int:
        with self._connect() as conn:
            return conn.execute('DELETE FROM discover_listens').rowcount

    # Block list

    def block(self, name: str) -> Optional[dict[str, Any]]:
        """Never suggest *name* again. ``None`` for a name with no key."""

        name = str(name or '').strip()
        key = artist_key(name)
        if not key:
            return None
        stamp = _now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO discover_blocked (artist_key, name, blocked_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(artist_key) DO NOTHING""",
                (key, name, stamp),
            )
            row = conn.execute(
                'SELECT name, blocked_at FROM discover_blocked '
                'WHERE artist_key = ?',
                (key,),
            ).fetchone()
        return dict(row)

    def unblock(self, name: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                'DELETE FROM discover_blocked WHERE artist_key = ?',
                (artist_key(name),),
            )
            return cur.rowcount > 0

    def blocked(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT name, blocked_at FROM discover_blocked '
                'ORDER BY blocked_at DESC, name'
            ).fetchall()
        return [dict(row) for row in rows]

    def blocked_keys(self) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT artist_key FROM discover_blocked'
            ).fetchall()
        return {row['artist_key'] for row in rows}

    # Related-artists cache

    def cached_related(self, key: str) -> Optional[dict[str, Any]]:
        """``{deezer_id, related, fetched_at}`` for a seed, or ``None``."""

        with self._connect() as conn:
            row = conn.execute(
                'SELECT deezer_id, related_json, fetched_at '
                'FROM discover_related WHERE artist_key = ?',
                (key,),
            ).fetchone()
        if row is None:
            return None
        try:
            related = json.loads(row['related_json'])
        except ValueError:
            related = []
        return {
            'deezer_id': row['deezer_id'],
            'related': related if isinstance(related, list) else [],
            'fetched_at': _parse_time(row['fetched_at']),
        }

    def save_related(
        self,
        key: str,
        deezer_id: str,
        related: Related,
        when: Optional[datetime] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO discover_related
                   (artist_key, deezer_id, related_json, fetched_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(artist_key) DO UPDATE SET
                     deezer_id = excluded.deezer_id,
                     related_json = excluded.related_json,
                     fetched_at = excluded.fetched_at""",
                (
                    key,
                    deezer_id or '',
                    json.dumps(related),
                    (when or _now()).isoformat(),
                ),
            )

    # Spotify search cache

    def cached_search(self, key: str) -> Optional[dict[str, Any]]:
        """``{results, fetched_at}`` for an artist's search, or ``None``."""

        with self._connect() as conn:
            row = conn.execute(
                'SELECT results_json, fetched_at FROM discover_search '
                'WHERE artist_key = ?',
                (key,),
            ).fetchone()
        if row is None:
            return None
        try:
            results = json.loads(row['results_json'])
        except ValueError:
            results = {}
        return {
            'results': results if isinstance(results, dict) else {},
            'fetched_at': _parse_time(row['fetched_at']),
        }

    def save_search(
        self,
        key: str,
        results: dict[str, Any],
        when: Optional[datetime] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO discover_search
                   (artist_key, results_json, fetched_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(artist_key) DO UPDATE SET
                     results_json = excluded.results_json,
                     fetched_at = excluded.fetched_at""",
                (key, json.dumps(results), (when or _now()).isoformat()),
            )

    # Deezer discography / editorial playlist cache

    def cached_deezer(self, key: str, part: str) -> Optional[dict[str, Any]]:
        """``{value, fetched_at}`` for an artist's Deezer *part*
        (``'albums'`` or ``'playlist'``), or ``None`` if never fetched."""

        column = _DEEZER_PARTS[part]
        with self._connect() as conn:
            row = conn.execute(
                f'SELECT {column}_json AS value, {column}_at AS fetched_at '
                'FROM discover_deezer WHERE artist_key = ?',
                (key,),
            ).fetchone()
        if row is None or row['fetched_at'] is None:
            return None
        try:
            value = json.loads(row['value'] or 'null')
        except ValueError:
            value = None
        return {'value': value, 'fetched_at': _parse_time(row['fetched_at'])}

    def save_deezer(
        self,
        key: str,
        part: str,
        value: Any,
        when: Optional[datetime] = None,
    ) -> None:
        column = _DEEZER_PARTS[part]
        with self._connect() as conn:
            conn.execute(
                f"""INSERT INTO discover_deezer
                    (artist_key, {column}_json, {column}_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(artist_key) DO UPDATE SET
                      {column}_json = excluded.{column}_json,
                      {column}_at = excluded.{column}_at""",
                (key, json.dumps(value), (when or _now()).isoformat()),
            )

    # Spotify -> Deezer album matches

    def cached_album_match(self, spotify_id: str) -> Optional[dict[str, Any]]:
        """``{deezer_album_id, deezer_artist_id, cover_url, fetched_at}``
        for a Spotify album, or ``None`` if never matched."""

        with self._connect() as conn:
            row = conn.execute(
                'SELECT deezer_album_id, deezer_artist_id, cover_url, '
                'fetched_at FROM discover_album_map WHERE spotify_id = ?',
                (spotify_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            'deezer_album_id': row['deezer_album_id'],
            'deezer_artist_id': row['deezer_artist_id'],
            'cover_url': row['cover_url'],
            'fetched_at': _parse_time(row['fetched_at']),
        }

    def save_album_match(
        self,
        spotify_id: str,
        match: Optional[dict[str, Any]],
        when: Optional[datetime] = None,
    ) -> None:
        """Remember *spotify_id*'s Deezer album (*match*, a
        :func:`downtify.deezer.search_albums_by` row), or - ``None`` -
        that Deezer has none."""

        match = match or {}
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO discover_album_map
                   (spotify_id, deezer_album_id, deezer_artist_id,
                    cover_url, fetched_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(spotify_id) DO UPDATE SET
                     deezer_album_id = excluded.deezer_album_id,
                     deezer_artist_id = excluded.deezer_artist_id,
                     cover_url = excluded.cover_url,
                     fetched_at = excluded.fetched_at""",
                (
                    spotify_id,
                    str(match.get('album_id') or ''),
                    str(match.get('artist_id') or ''),
                    str(match.get('cover_url') or ''),
                    (when or _now()).isoformat(),
                ),
            )


# ── Albums and playlists (pure) ──────────────────────────────────────────


def album_key(artist: str, title: str) -> str:
    """The key an album is known by across services: its artist's
    :func:`artist_key` and its :func:`~downtify.file_naming.title_key`, so
    ``Dummy (Deluxe Edition)`` on Spotify is the ``Dummy`` on disk."""

    return f'{artist_key(artist)}|{title_key(title)}'


def _album_item(
    album: dict[str, Any], artist: str, reason: str, because: list[str]
) -> dict[str, Any]:
    return {
        'name': album['name'],
        'artist': artist,
        'year': album.get('year') or '',
        'cover_url': album.get('cover_url') or '',
        'spotify_id': album['id'],
        'url': f'https://open.spotify.com/album/{album["id"]}',
        'reason': reason,
        'because': because,
    }


def _playlist_item(
    playlist: dict[str, Any], artist: str, reason: str
) -> dict[str, Any]:
    return {
        'name': playlist['name'],
        'owner': playlist.get('owner') or '',
        'cover_url': playlist.get('cover_url') or '',
        'spotify_id': playlist['id'],
        'url': f'https://open.spotify.com/playlist/{playlist["id"]}',
        'reason': reason,
        'artist': artist,
    }


def _albums_by(results: dict[str, Any], name: str) -> list[dict[str, Any]]:
    """The albums in an artist's search *results* that are theirs (first
    credited artist), full albums before singles/EPs, otherwise in
    Spotify's (popularity) order."""

    key = artist_key(name)
    own = [
        album
        for album in results.get('albums') or []
        if album.get('artists') and artist_key(album['artists'][0]) == key
    ]
    return sorted(own, key=lambda a: a.get('type') != 'ALBUM')


def _editorial_playlist(
    results: dict[str, Any], name: str, *, radio: bool
) -> Optional[dict[str, Any]]:
    """Spotify's own "<name> Radio" (*radio*) or "This Is <name>" playlist
    in an artist's search *results*, or ``None``."""

    key = artist_key(name)
    for playlist in results.get('playlists') or []:
        if artist_key(playlist.get('owner')) != SPOTIFY_OWNER:
            continue
        title = artist_key(playlist.get('name'))
        if key not in title:
            continue
        # What's left once the artist's own name is out: "Radiohead" must
        # not make "This Is Radiohead" a radio mix.
        rest = title.replace(key, ' ')
        if radio and 'radio' in rest.split():
            return playlist
        if not radio and 'this is' in rest:
            return playlist
    return None


def pick_collections(
    suggested: list[dict[str, Any]],
    seeds: list[str],
    searches: dict[str, dict[str, Any]],
    owned_albums: set[str],
    owned_playlists: set[str],
) -> dict[str, Any]:
    """Albums and playlists from each artist's Spotify *searches* (keyed
    by :func:`artist_key`).

    *suggested* are :func:`rank_candidates` results (best first), *seeds*
    the user's heaviest library artists. Returns ``{albums, more_albums,
    playlists, artist_urls}``:

    * ``albums``: each suggested artist's top album not in
      *owned_albums* (keys from :func:`album_key`), ``reason: 'similar'``.
    * ``more_albums``: up to :data:`MORE_FROM_PER_SEED` albums per seed
      not in *owned_albums*, ``reason: 'more_from'``.
    * ``playlists``: the seeds' "<artist> Radio", then the suggested
      artists' "This Is <artist>" (``reason: 'radio'`` / ``'this_is'``),
      leaving out ids in *owned_playlists*.
    * ``artist_urls``: ``{name: Spotify artist URL}`` for every suggested
      artist the search found by exact name.
    """

    albums: list[dict[str, Any]] = []
    more: list[dict[str, Any]] = []
    radios: list[dict[str, Any]] = []
    this_is: list[dict[str, Any]] = []
    artist_urls: dict[str, str] = {}
    seen_albums: set[str] = set(owned_albums)
    seen_playlists: set[str] = set(owned_playlists)

    def take_album(album, artist, reason, because, into) -> bool:
        key = album_key(artist, album['name'])
        if key in seen_albums:
            return False
        seen_albums.add(key)
        into.append(_album_item(album, artist, reason, because))
        return True

    def take_playlist(playlist, artist, reason, into) -> None:
        if playlist is None or playlist['id'] in seen_playlists:
            return
        seen_playlists.add(playlist['id'])
        into.append(_playlist_item(playlist, artist, reason))

    for seed in seeds:
        results = searches.get(artist_key(seed)) or {}
        taken = 0
        for album in _albums_by(results, seed):
            if taken >= MORE_FROM_PER_SEED:
                break
            if take_album(album, seed, 'more_from', [seed], more):
                taken += 1
        take_playlist(
            _editorial_playlist(results, seed, radio=True),
            seed,
            'radio',
            radios,
        )

    for artist in suggested:
        name = artist['name']
        results = searches.get(artist_key(name)) or {}
        for found in results.get('artists') or []:
            if artist_key(found.get('name')) == artist_key(name):
                artist_urls[name] = (
                    f'https://open.spotify.com/artist/{found["id"]}'
                )
                break
        for album in _albums_by(results, name):
            if take_album(
                album, name, 'similar', artist.get('because') or [], albums
            ):
                break
        take_playlist(
            _editorial_playlist(results, name, radio=False),
            name,
            'this_is',
            this_is,
        )

    return {
        'albums': albums,
        'more_albums': more,
        'playlists': radios + this_is,
        'artist_urls': artist_urls,
    }


# ── Putting it together ──────────────────────────────────────────────────


def _related_for_seed(
    store: DiscoverStore,
    key: str,
    name: str,
    *,
    lookup_id: Callable[[str], Optional[str]],
    fetch_related: Callable[[str, int], Related],
    now: datetime,
) -> tuple[Related, bool]:
    """A seed's related artists, from the cache while fresh, else Deezer.

    Returns ``(related, failed)``. When Deezer can't be asked (down, rate
    limited), a stale cached answer is used if there is one, and nothing
    is saved - "couldn't find out" is never remembered as "none". A seed
    Deezer doesn't know at all *is* remembered (with no id and no related
    artists), so it isn't searched for again until the cache runs out.
    """

    cached = store.cached_related(key)
    if (
        cached is not None
        and cached['fetched_at'] is not None
        and now - cached['fetched_at'] < RELATED_TTL
    ):
        return cached['related'], False

    stale = cached['related'] if cached is not None else []
    try:
        deezer_id = (cached or {}).get('deezer_id') or lookup_id(name)
        if not deezer_id:
            store.save_related(key, '', [], when=now)
            return [], False
        related = fetch_related(deezer_id, RELATED_PER_SEED)
    except ValueError:
        return stale, True
    store.save_related(key, deezer_id, related, when=now)
    return related, False


def recommendations(
    store: DiscoverStore,
    library: list[dict[str, Any]],
    *,
    limit: int = RESULT_LIMIT,
    lookup_id: Callable[[str], Optional[str]] = deezer.lookup_artist_id,
    fetch_related: Callable[[str, int], Related] = deezer.related_artists,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Suggested artists for a library.

    *library* is ``{name, tracks, liked}`` per library artist (what the
    Library page already groups - see ``frontend/src/lib/library.js``).
    Returns ``{artists, seeds, partial}``: the ranked suggestions (see
    :func:`rank_candidates`), the names of the seeds they came from, and
    whether Deezer failed for any seed - the list is then built from what
    could be fetched (plus stale cache), not an error.
    """

    now = now or _now()
    library = [a for a in library if isinstance(a, dict)]
    seeds = pick_seeds(seed_weights(library, store.listens(), now))
    if not seeds:
        return {'artists': [], 'seeds': [], 'partial': False}

    def fetch(seed: tuple[str, str, float]) -> tuple[str, Related, bool]:
        key, name, _weight = seed
        try:
            related, failed = _related_for_seed(
                store,
                key,
                name,
                lookup_id=lookup_id,
                fetch_related=fetch_related,
                now=now,
            )
        except Exception:
            logger.opt(exception=True).warning(
                'Discover: related artists failed for {!r}', name
            )
            return key, [], True
        return key, related, failed

    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        results = list(pool.map(fetch, seeds))

    related = {key: rows for key, rows, _failed in results}
    exclude = {artist_key(a.get('name')) for a in library}
    exclude |= store.blocked_keys()
    exclude.discard('')
    return {
        'artists': rank_candidates(seeds, related, exclude, limit=limit),
        'seeds': [name for _key, name, _weight in seeds],
        'partial': any(failed for _key, _rows, failed in results),
    }


def _search_for(
    store: DiscoverStore,
    name: str,
    *,
    search: Callable[[str], dict[str, Any]],
    now: datetime,
) -> tuple[dict[str, Any], bool]:
    """An artist's Spotify search, from the cache while fresh. Returns
    ``(results, failed)``; same failure rules as :func:`_related_for_seed`
    - a failed search falls back to a stale answer and is never saved."""

    key = artist_key(name)
    cached = store.cached_search(key)
    if (
        cached is not None
        and cached['fetched_at'] is not None
        and now - cached['fetched_at'] < RELATED_TTL
    ):
        return cached['results'], False
    try:
        results = search(name)
    except ValueError:
        return (cached['results'] if cached else {}), True
    store.save_search(key, results, when=now)
    return results, False


def collections(
    store: DiscoverStore,
    library: list[dict[str, Any]],
    owned_albums: Iterable[dict[str, Any]] = (),
    owned_playlists: Iterable[str] = (),
    *,
    lookup_id: Callable[[str], Optional[str]] = deezer.lookup_artist_id,
    fetch_related: Callable[[str, int], Related] = deezer.related_artists,
    search: Callable[[str], dict[str, Any]] = spotify.search,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Albums and playlists for a library (see :func:`pick_collections`).

    *library* is what :func:`recommendations` takes (its answer comes from
    the same cache, so this costs no extra Deezer requests once the
    artists are shown); *owned_albums* ``{artist, title}`` per library
    album, *owned_playlists* the Spotify ids of downloaded playlists.
    ``partial`` is ``True`` when a search failed for some artist.
    """

    now = now or _now()
    library = [a for a in library if isinstance(a, dict)]
    ranked = recommendations(
        store,
        library,
        lookup_id=lookup_id,
        fetch_related=fetch_related,
        now=now,
    )
    suggested = ranked['artists'][:COLLECTION_SUGGESTED]
    seeds = ranked['seeds'][:COLLECTION_SEEDS]
    names = list(dict.fromkeys([*seeds, *(a['name'] for a in suggested)]))

    def fetch(name: str) -> tuple[str, dict[str, Any], bool]:
        try:
            results, failed = _search_for(store, name, search=search, now=now)
        except Exception:
            logger.opt(exception=True).warning(
                'Discover: Spotify search failed for {!r}', name
            )
            return name, {}, True
        return name, results, failed

    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        results = list(pool.map(fetch, names))

    picked = pick_collections(
        suggested,
        seeds,
        {artist_key(name): found for name, found, _failed in results},
        {
            album_key(a.get('artist'), a.get('title'))
            for a in owned_albums
            if isinstance(a, dict)
        },
        {str(pid) for pid in owned_playlists if pid},
    )
    picked['partial'] = ranked['partial'] or any(
        failed for _name, _found, failed in results
    )
    return picked


# ── Deezer first, then Spotify matched to Deezer ─────────────────────────
#
# The web page's album and playlist shelves. Deezer's own picks come first
# (deezer_collections: quick, and every album opens in the Finder); what
# Spotify picks is added after (spotify_collections), each album matched
# back to Deezer by name when Deezer has it. Playlists aren't matched - a
# "100% <artist>" (Deezer's editors) and a "This Is <artist>" (Spotify's)
# are different lists - so each service keeps its own shelf.
#
# collections() above, Spotify only, is kept as it is: other clients may
# rely on it.


def _release_rank(album: dict[str, Any]) -> tuple[bool, int]:
    """Sort key for an artist's Deezer releases: full albums first (as
    :func:`_albums_by` does on Spotify), then the most fans."""

    kind = str(album.get('release_type') or '').lower()
    return kind != 'album', -int(album.get('fans') or 0)


def _deezer_album_item(
    album: dict[str, Any], artist: str, reason: str, because: list[str]
) -> dict[str, Any]:
    album_id = str(album['album_id'])
    return {
        'name': album['name'],
        'artist': artist,
        'year': album.get('year') or '',
        'cover_url': album.get('cover_url') or '',
        'source': 'deezer',
        'deezer_album_id': album_id,
        'deezer_artist_id': str(album.get('artist_id') or ''),
        'url': album.get('url') or f'https://www.deezer.com/album/{album_id}',
        'key': album_key(artist, album['name']),
        'reason': reason,
        'because': because,
    }


def _deezer_playlist_item(
    playlist: dict[str, Any], artist: str
) -> dict[str, Any]:
    return {
        'name': playlist['name'],
        'owner': playlist.get('owner') or '',
        'cover_url': playlist.get('cover_url') or '',
        'source': 'deezer',
        'deezer_playlist_id': str(playlist['playlist_id']),
        'url': playlist['url'],
        'reason': 'essentials',
        'artist': artist,
    }


def pick_deezer_collections(
    suggested: list[dict[str, Any]],
    seeds: list[str],
    discographies: dict[str, list[dict[str, Any]]],
    playlists: dict[str, Optional[dict[str, Any]]],
    owned_albums: set[str],
    owned_playlists: set[str],
) -> dict[str, Any]:
    """The same shelves as :func:`pick_collections`, from Deezer.

    *discographies* and *playlists* are keyed by :func:`artist_key`: each
    artist's :func:`downtify.deezer.artist_discography` and
    :func:`downtify.deezer.editorial_playlist`. *owned_albums* holds
    :func:`album_key` values, *owned_playlists* the
    :func:`~downtify.file_naming.file_name_key` of every library playlist
    name - a downloaded Deezer playlist keeps its title as its name.
    Returns ``{albums, more_albums, playlists}``:

    * ``albums``: each suggested artist's best album not owned - a full
      album before a single or EP, the most fans first - ``reason:
      'similar'``.
    * ``more_albums``: up to :data:`MORE_FROM_PER_SEED` per seed, same
      order, ``reason: 'more_from'``.
    * ``playlists``: the suggested artists' "100%" playlists,
      ``reason: 'essentials'``.
    """

    albums: list[dict[str, Any]] = []
    more: list[dict[str, Any]] = []
    lists: list[dict[str, Any]] = []
    seen: set[str] = set(owned_albums)

    def take(album, artist, reason, because, into) -> bool:
        key = album_key(artist, album['name'])
        if key in seen:
            return False
        seen.add(key)
        into.append(_deezer_album_item(album, artist, reason, because))
        return True

    for seed in seeds:
        taken = 0
        releases = discographies.get(artist_key(seed)) or []
        for album in sorted(releases, key=_release_rank):
            if taken >= MORE_FROM_PER_SEED:
                break
            if take(album, seed, 'more_from', [seed], more):
                taken += 1

    for artist in suggested:
        name = artist['name']
        because = artist.get('because') or []
        releases = discographies.get(artist_key(name)) or []
        for album in sorted(releases, key=_release_rank):
            if take(album, name, 'similar', because, albums):
                break
        playlist = playlists.get(artist_key(name))
        if playlist and file_name_key(playlist['name']) not in owned_playlists:
            lists.append(_deezer_playlist_item(playlist, name))

    return {'albums': albums, 'more_albums': more, 'playlists': lists}


def _deezer_part(
    store: DiscoverStore,
    key: str,
    part: str,
    fetch: Callable[[], Any],
    *,
    now: datetime,
) -> tuple[Any, bool]:
    """An artist's Deezer *part* from the cache while fresh, else
    *fetch*. ``(value, failed)``, with the same rules as
    :func:`_related_for_seed`: a failure falls back to a stale answer and
    is never saved; "Deezer has none" (``None``) is saved like any answer.
    """

    cached = store.cached_deezer(key, part)
    if (
        cached is not None
        and cached['fetched_at'] is not None
        and now - cached['fetched_at'] < RELATED_TTL
    ):
        return cached['value'], False
    try:
        value = fetch()
    except ValueError:
        return (cached['value'] if cached else None), True
    store.save_deezer(key, part, value, when=now)
    return value, False


def deezer_collections(
    store: DiscoverStore,
    library: list[dict[str, Any]],
    owned_albums: Iterable[dict[str, Any]] = (),
    owned_playlists: Iterable[str] = (),
    *,
    lookup_id: Callable[[str], Optional[str]] = deezer.lookup_artist_id,
    fetch_related: Callable[[str, int], Related] = deezer.related_artists,
    fetch_albums: Callable[
        [str], list[dict[str, Any]]
    ] = deezer.artist_discography,
    fetch_playlist: Callable[
        [str], Optional[dict[str, Any]]
    ] = deezer.editorial_playlist,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Albums and playlists for a library from Deezer alone (see
    :func:`pick_deezer_collections`) - the page's first, quick answer.

    *library* and *owned_albums* are what :func:`collections` takes;
    *owned_playlists* are library playlist names. Built on the same ranked
    artists (cached), so it only asks Deezer for discographies and
    playlists: one each per artist, cached for :data:`RELATED_TTL`.
    ``partial`` is ``True`` when some of those couldn't be fetched.
    """

    now = now or _now()
    library = [a for a in library if isinstance(a, dict)]
    ranked = recommendations(
        store,
        library,
        lookup_id=lookup_id,
        fetch_related=fetch_related,
        now=now,
    )
    suggested = ranked['artists'][:COLLECTION_SUGGESTED]
    seeds = ranked['seeds'][:COLLECTION_SEEDS]

    # A suggestion carries its own Deezer id; a seed's was saved with its
    # related artists.
    names: dict[str, str] = {}
    ids: dict[str, str] = {}
    for seed in seeds:
        key = artist_key(seed)
        names[key] = seed
        ids[key] = (store.cached_related(key) or {}).get('deezer_id') or ''
    for artist in suggested:
        key = artist_key(artist['name'])
        names.setdefault(key, artist['name'])
        ids.setdefault(key, str(artist.get('deezer_id') or ''))

    jobs = [(key, 'albums') for key, deezer_id in ids.items() if deezer_id]
    jobs += [(artist_key(a['name']), 'playlist') for a in suggested]

    def fetcher(key: str, part: str) -> Callable[[], Any]:
        if part == 'albums':
            return lambda: fetch_albums(ids[key])
        return lambda: fetch_playlist(names[key])

    def run(job: tuple[str, str]) -> tuple[str, str, Any, bool]:
        key, part = job
        try:
            value, failed = _deezer_part(
                store, key, part, fetcher(key, part), now=now
            )
        except Exception:
            logger.opt(exception=True).warning(
                'Discover: Deezer {} failed for {!r}', part, names[key]
            )
            return key, part, None, True
        return key, part, value, failed

    with ThreadPoolExecutor(max_workers=_THROTTLED_WORKERS) as pool:
        results = list(pool.map(run, jobs))

    discographies = {
        key: value or [] for key, part, value, _ in results if part == 'albums'
    }
    playlists = {
        key: value for key, part, value, _ in results if part == 'playlist'
    }
    picked = pick_deezer_collections(
        suggested,
        seeds,
        discographies,
        playlists,
        {
            album_key(a.get('artist'), a.get('title'))
            for a in owned_albums
            if isinstance(a, dict)
        },
        {file_name_key(str(name)) for name in owned_playlists if name},
    )
    picked['partial'] = ranked['partial'] or any(
        failed for _key, _part, _value, failed in results
    )
    return picked


def _match_album(
    store: DiscoverStore,
    item: dict[str, Any],
    *,
    find: Callable[[str, str], list[dict[str, Any]]],
    now: datetime,
) -> tuple[Optional[dict[str, Any]], bool]:
    """A Spotify album *item*'s Deezer album, or ``None`` when Deezer has
    none: ``(match, failed)``.

    A row counts only when it's the same album by :func:`album_key` (same
    artist, same title once edition suffixes are dropped) - never "the
    closest". Matches are cached by Spotify id, a found one for
    :data:`MATCH_TTL_FOUND`, a missing one for :data:`MATCH_TTL_MISSING`;
    a failure falls back to a stale match and is never saved.
    """

    spotify_id = str(item['spotify_id'])
    cached = store.cached_album_match(spotify_id)
    if cached is not None and cached['fetched_at'] is not None:
        found = bool(cached['deezer_album_id'])
        ttl = MATCH_TTL_FOUND if found else MATCH_TTL_MISSING
        if now - cached['fetched_at'] < ttl:
            return (cached if found else None), False
    try:
        rows = find(item['artist'], item['name'])
    except ValueError:
        stale = cached if cached and cached['deezer_album_id'] else None
        return stale, True
    wanted = album_key(item['artist'], item['name'])
    row = next(
        (
            row
            for row in rows
            if album_key(row.get('artist'), row.get('name')) == wanted
        ),
        None,
    )
    store.save_album_match(spotify_id, row, when=now)
    if row is None:
        return None, False
    return {
        'deezer_album_id': str(row['album_id']),
        'deezer_artist_id': str(row.get('artist_id') or ''),
        'cover_url': row.get('cover_url') or '',
    }, False


def _matched_album_item(
    item: dict[str, Any], match: Optional[dict[str, Any]]
) -> dict[str, Any]:
    """A Spotify album *item* as Deezer's (opens in the Finder), or as
    Spotify's when Deezer has no match (opens on its Spotify page)."""

    key = album_key(item['artist'], item['name'])
    if match is None:
        return {**item, 'source': 'spotify', 'key': key}
    album_id = match['deezer_album_id']
    return {
        'name': item['name'],
        'artist': item['artist'],
        'year': item.get('year') or '',
        'cover_url': match.get('cover_url') or item.get('cover_url') or '',
        'source': 'deezer',
        'deezer_album_id': album_id,
        'deezer_artist_id': match.get('deezer_artist_id') or '',
        'url': f'https://www.deezer.com/album/{album_id}',
        'key': key,
        'reason': item['reason'],
        'because': item['because'],
    }


def spotify_collections(
    store: DiscoverStore,
    library: list[dict[str, Any]],
    owned_albums: Iterable[dict[str, Any]] = (),
    owned_playlists: Iterable[str] = (),
    shown: Iterable[str] = (),
    *,
    lookup_id: Callable[[str], Optional[str]] = deezer.lookup_artist_id,
    fetch_related: Callable[[str, int], Related] = deezer.related_artists,
    search: Callable[[str], dict[str, Any]] = spotify.search,
    find_album: Callable[
        [str, str], list[dict[str, Any]]
    ] = deezer.search_albums_by,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """What Spotify adds to :func:`deezer_collections` - the page's
    second, slower answer.

    Spotify's own picks (:func:`collections`, its searches cached), less
    the albums already *shown* (their :func:`album_key` values) - so an
    album both services pick costs no match - each matched to Deezer (see
    :func:`_match_album`). *owned_playlists* are Spotify playlist ids, as
    for :func:`collections`. Returns ``{albums, more_albums, playlists,
    partial}``: albums with ``source`` ``'deezer'`` (matched) or
    ``'spotify'`` (no match), and only the "This Is <artist>" playlists -
    Spotify's "Radio" mixes aren't offered here.
    """

    now = now or _now()
    picked = collections(
        store,
        library,
        owned_albums,
        owned_playlists,
        lookup_id=lookup_id,
        fetch_related=fetch_related,
        search=search,
        now=now,
    )
    skip = {str(key) for key in shown if key}
    jobs = [
        (shelf, item)
        for shelf in ('albums', 'more_albums')
        for item in picked[shelf]
        if album_key(item['artist'], item['name']) not in skip
    ]

    def run(job: tuple[str, dict[str, Any]]) -> tuple[str, dict, bool]:
        shelf, item = job
        try:
            match, failed = _match_album(store, item, find=find_album, now=now)
        except Exception:
            logger.opt(exception=True).warning(
                'Discover: matching {!r} to Deezer failed', item['name']
            )
            match, failed = None, True
        return shelf, _matched_album_item(item, match), failed

    with ThreadPoolExecutor(max_workers=_THROTTLED_WORKERS) as pool:
        results = list(pool.map(run, jobs))

    return {
        'albums': [item for shelf, item, _ in results if shelf == 'albums'],
        'more_albums': [
            item for shelf, item, _ in results if shelf == 'more_albums'
        ],
        'playlists': [
            {**playlist, 'source': 'spotify'}
            for playlist in picked['playlists']
            if playlist['reason'] == 'this_is'
        ],
        'partial': picked['partial']
        or any(failed for _shelf, _item, failed in results),
    }
