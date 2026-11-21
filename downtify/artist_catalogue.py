"""What a watched artist has released, and what the library has of it
(issue #581, phase 2: the catalogue view).

Every sweep of an artist watch lists the artist's discography from its
catalogues (YouTube Music, Deezer, MusicBrainz - ``monitor.
_artist_discography``). :class:`ArtistCatalogue` keeps the last listing
of each release, so the watch's page can show the whole catalogue without
asking the catalogues again, plus two things learnt along the way: how
many tracks a release has (once its tracklist was fetched) and whether it
turned out not to be the artist's own (a guest spot, a bootleg).

It also keeps the user's **choice** per release, like Lidarr's per-album
monitoring: ``on`` downloads it even when its type isn't watched or it
came out before a "new releases only" watch started, ``off`` never
downloads it (what is already there stays), ``''`` follows the watch.

:func:`catalogue_view` puts it together for ``GET
/api/monitor/playlists/{id}/releases``: one row per release - the same
album listed by two catalogues is one row - with its state:

``complete``  every track is in the library
``partly``    some are
``missing``   it is wanted and none are there yet (the next check tries)
``upcoming``  it is wanted but announced, not out yet (``release_date`` is
              in the future): the first check on or after its release
              day downloads it
``skipped``   out before a "new releases only" watch started
``not_watched`` a type or kind the watch doesn't download
``off``       switched off
``not_own``   a guest spot or a bootleg: never downloaded

**What the library has** of a release is counted against its tracklist
(:meth:`ArtistCatalogue.store_tracks`): every track the library holds -
the same artist and title, the same length, as :mod:`downtify.
library_songs` matches them - whoever downloaded it. A sweep keeps the
tracklists of the releases it processes; ``monitor.take_inventory``
reads the others on request ("Check what I have"), downloading nothing.
So an album the user had before the watch started shows as complete,
not just "out before the watch".
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from typing import Any, Callable, ContextManager, Iterable, Optional

from . import musicbrainz
from .db.config import Dialect
from .db.core import Connection
from .file_naming import file_name_key
from .library_catalog import song_key

CHOICES = ('', 'on', 'off')

#: Row order of the states when one release is listed twice: the best
#: news wins.
_STATE_ORDER = (
    'complete',
    'partly',
    'upcoming',
    'missing',
    'skipped',
    'not_watched',
    'off',
    'not_own',
)

#: MusicBrainz's secondary types back to the names settings use.
_KIND_NAMES = {mb: name for name, mb in musicbrainz.KINDS.items()}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _source_of(album_id: str, source: Any) -> str:
    """The catalogue a release came from: its own ``source``, else read
    off its id (``youtube``, as YouTube Music's own rows say)."""

    if source:
        return str(source)
    if album_id.startswith('deezer:'):
        return 'deezer'
    if album_id.startswith('mb:'):
        return 'musicbrainz'
    return 'youtube'


class ArtistCatalogue:
    """The ``artist_catalogue`` table of the monitor database."""

    def __init__(
        self, connect: Callable[[], ContextManager[Connection]]
    ) -> None:
        self._connect = connect
        with self._connect() as conn:
            if getattr(conn, 'dialect', Dialect.SQLITE) is Dialect.SQLITE:
                self._init_sqlite(conn)

    @staticmethod
    def _init_sqlite(conn: Connection) -> None:
        """Create the SQLite-only schema; PostgreSQL migrations own it."""
        conn.execute("""CREATE TABLE IF NOT EXISTS artist_catalogue (
            playlist_id INTEGER NOT NULL,
            album_id TEXT NOT NULL,
            name TEXT NOT NULL,
            release_type TEXT NOT NULL DEFAULT '',
            kinds TEXT NOT NULL DEFAULT '',
            year TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            cover_url TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL DEFAULT '',
            position INTEGER NOT NULL DEFAULT 0,
            track_total INTEGER NOT NULL DEFAULT 0,
            not_own INTEGER NOT NULL DEFAULT 0,
            choice TEXT NOT NULL DEFAULT '',
            listed_at TEXT NOT NULL,
            release_date TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (playlist_id, album_id),
            FOREIGN KEY (playlist_id) REFERENCES monitored_playlists(id)
                ON DELETE CASCADE
        )""")
        columns = {
            r[1] for r in conn.execute('PRAGMA table_info(artist_catalogue)')
        }
        if 'release_date' not in columns:
            conn.execute(
                'ALTER TABLE artist_catalogue ADD COLUMN release_date '
                "TEXT NOT NULL DEFAULT ''"
            )
        # Each release's tracklist, once a sweep or "Check what I
        # have" read it.
        conn.execute("""CREATE TABLE IF NOT EXISTS artist_catalogue_tracks (
            playlist_id INTEGER NOT NULL,
            album_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            name TEXT NOT NULL,
            artists TEXT NOT NULL DEFAULT '[]',
            duration REAL NOT NULL DEFAULT 0,
            PRIMARY KEY (playlist_id, album_id, position),
            FOREIGN KEY (playlist_id) REFERENCES monitored_playlists(id)
                ON DELETE CASCADE
        )""")

    def record(
        self, playlist_id: int, albums: Iterable[dict[str, Any]]
    ) -> None:
        """Keep a sweep's listing (what a release is called, its type,
        cover...). What was learnt about a release and the user's choice
        are kept as they are."""

        now = _now()
        with self._connect() as conn:
            for position, album in enumerate(albums):
                album_id = str(album.get('album_id') or '')
                if not album_id:
                    continue
                conn.execute(
                    """INSERT INTO artist_catalogue
                       (playlist_id, album_id, name, release_type, kinds,
                        year, source, cover_url, url, position, listed_at,
                        release_date)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(playlist_id, album_id) DO UPDATE SET
                         name = excluded.name,
                         release_type = excluded.release_type,
                         kinds = excluded.kinds,
                         year = excluded.year,
                         release_date = excluded.release_date,
                         source = excluded.source,
                         cover_url = excluded.cover_url,
                         url = excluded.url,
                         position = excluded.position,
                         listed_at = excluded.listed_at""",
                    (
                        playlist_id,
                        album_id,
                        str(album.get('name') or album_id),
                        str(album.get('release_type') or ''),
                        ','.join(album.get('kinds') or []),
                        str(album.get('year') or ''),
                        _source_of(album_id, album.get('source')),
                        str(album.get('cover_url') or ''),
                        str(album.get('url') or ''),
                        position,
                        now,
                        release_day(album),
                    ),
                )

    def release_day_arrived(
        self, playlist_id: int, last_checked: Optional[str]
    ) -> bool:
        """Whether one of the watch's announced releases has come out
        since its last check: the day it is due, whatever the interval."""

        if not last_checked:
            return False
        try:
            checked = datetime.fromisoformat(last_checked)
        except ValueError:
            return False
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=timezone.utc)
        since = checked.astimezone().date().isoformat()
        today = date.today().isoformat()
        with self._connect() as conn:
            row = conn.execute(
                'SELECT 1 FROM artist_catalogue WHERE playlist_id = ? '
                'AND length(release_date) = 10 AND release_date > ? '
                'AND release_date <= ? LIMIT 1',
                (playlist_id, since, today),
            ).fetchone()
        return row is not None

    def store_tracks(
        self, playlist_id: int, album_id: str, songs: list[dict[str, Any]]
    ) -> None:
        """Keep a release's tracklist (and its track count)."""

        with self._connect() as conn:
            conn.execute(
                'DELETE FROM artist_catalogue_tracks '
                'WHERE playlist_id = ? AND album_id = ?',
                (playlist_id, album_id),
            )
            conn.executemany(
                'INSERT INTO artist_catalogue_tracks VALUES (?,?,?,?,?,?)',
                [
                    (
                        playlist_id,
                        album_id,
                        position,
                        str(song.get('name') or ''),
                        json.dumps([
                            str(a) for a in song.get('artists') or []
                        ]),
                        float(song.get('duration') or 0),
                    )
                    for position, song in enumerate(songs, start=1)
                ],
            )
            conn.execute(
                'UPDATE artist_catalogue SET track_total = ? '
                'WHERE playlist_id = ? AND album_id = ?',
                (len(songs), playlist_id, album_id),
            )

    def tracks(self, playlist_id: int) -> dict[str, list[dict[str, Any]]]:
        """``{album_id: [{position, name, artists, duration}]}`` for the
        releases whose tracklist is kept."""

        found: dict[str, list[dict[str, Any]]] = {}
        with self._connect() as conn:
            for r in conn.execute(
                'SELECT * FROM artist_catalogue_tracks WHERE playlist_id = ? '
                'ORDER BY album_id, position',
                (playlist_id,),
            ):
                found.setdefault(r['album_id'], []).append({
                    'position': r['position'],
                    'name': r['name'],
                    'artists': json.loads(r['artists'] or '[]'),
                    'duration': r['duration'],
                })
        return found

    def set_total(self, playlist_id: int, album_id: str, total: int) -> None:
        with self._connect() as conn:
            conn.execute(
                'UPDATE artist_catalogue SET track_total = ? '
                'WHERE playlist_id = ? AND album_id = ?',
                (int(total), playlist_id, album_id),
            )

    def set_not_own(self, playlist_id: int, album_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                'UPDATE artist_catalogue SET not_own = 1 '
                'WHERE playlist_id = ? AND album_id = ?',
                (playlist_id, album_id),
            )

    def choices(self, playlist_id: int) -> dict[str, str]:
        """``{album_id: 'on' | 'off'}`` for releases the user switched."""

        with self._connect() as conn:
            return {
                r['album_id']: r['choice']
                for r in conn.execute(
                    'SELECT album_id, choice FROM artist_catalogue '
                    "WHERE playlist_id = ? AND choice != ''",
                    (playlist_id,),
                )
            }

    def set_choice(
        self, playlist_id: int, album_ids: Iterable[str], choice: str
    ) -> int:
        """Switch releases ``on``, ``off`` or back to the watch's rules
        (``''``). Returns how many of *album_ids* the watch lists."""

        if choice not in CHOICES:
            raise ValueError(f'unknown choice {choice!r}')
        changed = 0
        with self._connect() as conn:
            for album_id in album_ids:
                changed += conn.execute(
                    'UPDATE artist_catalogue SET choice = ? '
                    'WHERE playlist_id = ? AND album_id = ?',
                    (choice, playlist_id, str(album_id)),
                ).rowcount
        return changed

    def rows(self, playlist_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return [
                dict(r)
                for r in conn.execute(
                    'SELECT * FROM artist_catalogue WHERE playlist_id = ? '
                    'ORDER BY position, album_id',
                    (playlist_id,),
                )
            ]

    def seen(self, playlist_id: int) -> dict[str, bool]:
        """``{album_id: skipped}`` for the releases a sweep processed
        (``seen_albums``): ``True`` for one recorded without downloading
        it."""

        with self._connect() as conn:
            return {
                r['album_id']: bool(r['skipped'])
                for r in conn.execute(
                    'SELECT album_id, skipped FROM seen_albums '
                    'WHERE playlist_id = ?',
                    (playlist_id,),
                )
            }

    def forget_skipped(
        self, playlist_id: int, album_ids: Iterable[str]
    ) -> int:
        """Drop *album_ids* from the releases a watch skipped, so the next
        check downloads them (the user switched them on)."""

        with self._connect() as conn:
            return sum(
                conn.execute(
                    'DELETE FROM seen_albums WHERE playlist_id = ? '
                    'AND album_id = ? AND skipped = 1',
                    (playlist_id, str(album_id)),
                ).rowcount
                for album_id in album_ids
            )

    def clear(self, playlist_id: int) -> None:
        """Forget the listing - the watch now follows another artist."""

        with self._connect() as conn:
            for table in ('artist_catalogue', 'artist_catalogue_tracks'):
                conn.execute(
                    f'DELETE FROM {table} WHERE playlist_id = ?',  # noqa: S608
                    (playlist_id,),
                )


def release_key(name: str) -> str:
    """A release's name as two catalogues are matched by: without a
    ``(feat. …)`` / ``(with …)`` or remaster tag, which one catalogue
    adds and another leaves out (*Laugh Now Cry Later (feat. Lil Durk)*
    on YouTube Music is Deezer's *Laugh Now Cry Later*)."""

    return song_key('', str(name or '')).split('|', 1)[1] or file_name_key(
        str(name or '')
    )


# ── Announced releases ──────────────────────────────────────────────────

_DATE = re.compile(r'\d{4}(-\d{2}(-\d{2})?)?')


def release_day(album: dict[str, Any]) -> str:
    """A release's date as a catalogue gave it (``YYYY-MM-DD``, or only
    ``YYYY-MM`` / ``YYYY`` for some MusicBrainz groups), ``''`` without
    one."""

    text = str(album.get('release_date') or '').strip()[:10]
    return text if _DATE.fullmatch(text) else ''


def upcoming(album: dict[str, Any], today: Optional[date] = None) -> bool:
    """Whether *album* is announced but not out yet: its date is after
    *today* (a month or a year alone: after this month or year). Out on
    its release day itself."""

    day = release_day(album)
    if not day:
        return False
    now = (today or date.today()).isoformat()
    return day > now[: len(day)]


# ── What the watch downloads ────────────────────────────────────────────


def release_type_of(album: dict[str, Any]) -> str:
    """``album``, ``single`` or ``ep``, like ``monitor.release_type_of``:
    a catalogue's label; anything else counts as an album."""

    label = str(album.get('release_type') or '').strip().lower()
    return label if label in {'single', 'ep'} else 'album'


def watch_kinds(playlist: Any, settings: dict[str, Any]) -> set[str]:
    """The MusicBrainz secondary types a watch lets in: its own choice,
    else the ``artist_watch_musicbrainz_kinds`` setting."""

    own = getattr(playlist, 'musicbrainz_kinds', None)
    if own is not None:
        return musicbrainz.kinds_from_setting([k for k in own.split(',') if k])
    return musicbrainz.kinds_from_setting(
        settings.get('artist_watch_musicbrainz_kinds')
    )


def follows_watch(
    album: dict[str, Any], types: set[str], kinds: set[str]
) -> bool:
    """Whether the watch's own rules download *album*: one of its release
    *types*, and only secondary types it lets in (YouTube Music and
    Deezer releases have none)."""

    return release_type_of(album) in types and all(
        kind in kinds for kind in album.get('kinds') or []
    )


def wanted(
    album: dict[str, Any],
    types: set[str],
    kinds: set[str],
    choices: dict[str, str],
) -> bool:
    """Whether a sweep downloads *album*: the user's choice, else the
    watch's rules."""

    choice = choices.get(str(album.get('album_id') or ''), '')
    if choice:
        return choice == 'on'
    return follows_watch(album, types, kinds)


# ── What the library has ────────────────────────────────────────────────


def library_have(
    tracks: dict[str, list[dict[str, Any]]],
    songs: Any,
    recorded: dict[str, int],
) -> dict[str, int]:
    """How many tracks of each release the library holds: of its kept
    tracklist, those *songs* (a :class:`~downtify.library_songs.
    LibrarySongs`) finds; for a release with none kept, the tracks the
    watch recorded (*recorded*)."""

    have = dict(recorded)
    if songs is None:
        return have
    for album_id, rows in tracks.items():
        have[album_id] = sum(1 for row in rows if songs.find(row))
    return have


def track_list(
    rows: list[dict[str, Any]],
    songs: Any,
    recorded: dict[int, str],
) -> list[dict[str, Any]]:
    """A release's tracklist with the library file holding each track
    (``file``, ``None`` when missing): the one *songs* finds, else the one
    the watch recorded at that position."""

    return [
        {
            **row,
            'file': (songs.find(row) if songs is not None else None)
            or recorded.get(row['position']),
        }
        for row in rows
    ]


# ── The view ────────────────────────────────────────────────────────────


def _state(  # noqa: PLR0911  # one answer per state
    row: dict[str, Any],
    have: int,
    skipped: Optional[bool],
    follows: bool,
    today: Optional[date] = None,
) -> str:
    total = int(row['track_total'] or 0)
    if row['choice'] == 'off':
        return 'off'
    if row['not_own']:
        return 'not_own'
    if have and total and have >= total:
        return 'complete'
    if have:
        return 'partly'
    if skipped is False and total == 0:
        # Processed with nothing to download (an empty release).
        return 'complete'
    coming = not skipped and upcoming(row, today)
    if row['choice'] == 'on':
        return 'upcoming' if coming else 'missing'
    if not follows:
        # A type the watch doesn't download: the lasting reason, even for
        # one that also came out before a "new releases only" watch.
        return 'not_watched'
    if coming:
        return 'upcoming'
    return 'skipped' if skipped else 'missing'


def _downloads(
    row: dict[str, Any], skipped: Optional[bool], follows: bool
) -> bool:
    """Whether the watch downloads a release (its switch): the user's
    choice, else its type and kind - unless it came out before a "new
    releases only" watch. Never a guest spot or a bootleg."""

    if row['not_own']:
        return False
    if row['choice']:
        return row['choice'] == 'on'
    return follows and not skipped


def section_of(release_type: str, kinds: list[str]) -> str:
    """Where a release is listed: ``album``, ``mixtape``, ``ep``,
    ``single``, or ``other`` (live albums, compilations, remixes...)."""

    if 'mixtape' in kinds:
        return 'mixtape'
    if any(kind != 'soundtrack' for kind in kinds):
        return 'other'
    return (
        release_type if release_type in {'album', 'ep', 'single'} else 'album'
    )


def catalogue_view(
    rows: list[dict[str, Any]],
    *,
    have: dict[str, int],
    seen: dict[str, bool],
    types: set[str],
    kinds: set[str],
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    """The watch's releases as the page lists them: one per release (a
    release two catalogues list is merged: same name, same type), each
    ``{id, album_ids, name, release_type, kinds, section, year, sources,
    cover_url, url, release_date, state, have, total, choice, wanted}`` -
    ``wanted``
    being whether the watch downloads it (its switch), ``state`` what
    the library has of it.

    *have* is how many tracks of each release the library holds, *seen*
    whether a processed release was skipped (``True``) or downloaded
    (``False``); *types* and *kinds* are the watch's rules."""

    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        album = {
            'album_id': row['album_id'],
            'release_type': row['release_type'],
            'kinds': [k for k in row['kinds'].split(',') if k],
        }
        release_type = release_type_of(album)
        kind_names = [_KIND_NAMES.get(k, k) for k in album['kinds']]
        follows = follows_watch(album, types, kinds)
        state = _state(
            row,
            have.get(row['album_id'], 0),
            seen.get(row['album_id']),
            follows,
            today,
        )
        downloads = _downloads(row, seen.get(row['album_id']), follows)
        key = (release_key(row['name']) or row['album_id'], release_type)
        entry = merged.get(key)
        if entry is None:
            merged[key] = {
                'id': row['album_id'],
                'album_ids': [row['album_id']],
                'name': row['name'],
                'release_type': release_type,
                'kinds': kind_names,
                'section': section_of(release_type, kind_names),
                'year': row['year'],
                'release_date': release_day(row),
                'sources': [row['source']] if row['source'] else [],
                'cover_url': row['cover_url'],
                'url': row['url'],
                'state': state,
                'have': have.get(row['album_id'], 0),
                'total': int(row['track_total'] or 0),
                'choice': row['choice'],
                'wanted': downloads,
            }
            continue
        entry['album_ids'].append(row['album_id'])
        if row['source'] and row['source'] not in entry['sources']:
            entry['sources'].append(row['source'])
        if _STATE_ORDER.index(state) < _STATE_ORDER.index(entry['state']):
            entry['state'] = state
        entry['have'] = max(entry['have'], have.get(row['album_id'], 0))
        entry['total'] = max(entry['total'], int(row['track_total'] or 0))
        entry['year'] = entry['year'] or row['year']
        entry['release_date'] = max(entry['release_date'], release_day(row))
        entry['cover_url'] = entry['cover_url'] or row['cover_url']
        entry['choice'] = entry['choice'] or row['choice']
        entry['wanted'] = entry['wanted'] or downloads
    return list(merged.values())


def missing(releases: list[dict[str, Any]]) -> dict[str, int]:
    """What "Download missing" would fetch: of the releases the watch
    downloads (``wanted``), how many tracks are missing (``tracks``, in
    ``releases`` releases), plus the releases whose tracklist isn't read
    yet (``unread``: their count is unknown)."""

    found = {'tracks': 0, 'releases': 0, 'unread': 0}
    for release in releases:
        if not release.get('wanted') or release['state'] in {
            'complete',
            'upcoming',
        }:
            continue
        if not release['total']:
            found['unread'] += 1
            continue
        gap = release['total'] - release['have']
        if gap > 0:
            found['tracks'] += gap
            found['releases'] += 1
    return found


def upcoming_releases(
    releases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """The announced releases the watch will download on their release
    day, soonest first."""

    return sorted(
        (
            release
            for release in releases
            if release.get('wanted') and release['state'] == 'upcoming'
        ),
        key=lambda release: release.get('release_date') or '',
    )


def counts(releases: list[dict[str, Any]]) -> dict[str, int]:
    """How many releases are in each state."""

    found = dict.fromkeys(_STATE_ORDER, 0)
    for release in releases:
        found[release['state']] = found.get(release['state'], 0) + 1
    return found


def wanted_releases(releases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The releases "Download missing" would still fetch from: the ones
    the watch downloads (``wanted``) that the library has only partly
    (``partly``) or not at all (``missing``), in the order given."""

    return [
        release
        for release in releases
        if release.get('wanted') and release['state'] in {'partly', 'missing'}
    ]
