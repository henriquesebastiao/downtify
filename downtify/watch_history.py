"""What each Playlist Monitor watch added to the library, and failed to.

``downloaded_tracks`` (see :mod:`downtify.monitor`) only says which
tracks a watch holds right now. This keeps the history behind it, in the
same database:

* ``watch_events`` - one row each time a watch adds a track: when, the
  file, which provider fetched it, whether the watch downloaded it or
  found it already in the library (``OUTCOME_*``) and whether it came
  with the watch's first check (its backfill). Rows name the watch as it
  was then (id, target key, name, owner) and outlive it - deleting or
  retargeting a watch keeps them - so a song's origin can be told later.
* ``watch_failures`` - the tracks a watch keeps failing to download,
  until one succeeds, the track leaves the playlist or the watch is
  retargeted.

:mod:`downtify.watch_stats` turns both into provenance and statistics.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Callable, Optional

#: How a track got into a watch: the watch fetched new audio for it, or
#: the song was already in the library (a file the track index knew, or
#: one already at the expected path) and was only linked. ``unknown``:
#: recorded before outcomes were kept.
OUTCOME_DOWNLOADED = 'downloaded'
OUTCOME_LINKED = 'linked'
OUTCOME_UNKNOWN = 'unknown'

_EVENT_COLUMNS = (
    'playlist_id, watch_key, watch_name, user_id, track_id, outcome, '
    'filename, provider, initial, happened_at'
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _marks(values: list[Any]) -> str:
    return ','.join('?' * len(values))


class WatchHistoryStore:
    """``watch_events`` and ``watch_failures``, beside the watches."""

    def __init__(self, connect: Callable[[], sqlite3.Connection]) -> None:
        self._connect = connect
        with self._connect() as conn:
            had_events = (
                conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' "
                    "AND name = 'watch_events'"
                ).fetchone()
                is not None
            )
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS watch_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER NOT NULL,
                    watch_key TEXT NOT NULL,
                    watch_name TEXT NOT NULL,
                    user_id INTEGER NOT NULL DEFAULT 0,
                    track_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    filename TEXT,
                    provider TEXT NOT NULL DEFAULT '',
                    initial INTEGER NOT NULL DEFAULT 0,
                    happened_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_watch_events_watch
                    ON watch_events (playlist_id, happened_at);
                CREATE INDEX IF NOT EXISTS idx_watch_events_track
                    ON watch_events (track_id);
                CREATE INDEX IF NOT EXISTS idx_watch_events_file
                    ON watch_events (filename);
                CREATE TABLE IF NOT EXISTS watch_failures (
                    playlist_id INTEGER NOT NULL,
                    track_id TEXT NOT NULL,
                    name TEXT NOT NULL DEFAULT '',
                    artists TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT '',
                    attempts INTEGER NOT NULL DEFAULT 1,
                    first_failed_at TEXT NOT NULL,
                    last_failed_at TEXT NOT NULL,
                    PRIMARY KEY (playlist_id, track_id),
                    FOREIGN KEY (playlist_id)
                        REFERENCES monitored_playlists(id) ON DELETE CASCADE
                );
            """)
            if not had_events:
                _backfill(conn)

    def record_added(
        self,
        playlist_id: int,
        track_id: str,
        filename: Optional[str],
        *,
        outcome: str,
        provider: str = '',
        initial: bool = False,
    ) -> None:
        """Log that the watch added *track_id* (and clear its failure)."""

        with self._connect() as conn:
            conn.execute(
                f"""INSERT INTO watch_events ({_EVENT_COLUMNS})
                   SELECT id, spotify_id, name, user_id, ?, ?, ?, ?, ?, ?
                   FROM monitored_playlists WHERE id = ?""",
                (
                    track_id,
                    outcome,
                    filename,
                    str(provider or ''),
                    int(initial),
                    _now_iso(),
                    playlist_id,
                ),
            )
            conn.execute(
                'DELETE FROM watch_failures '
                'WHERE playlist_id = ? AND track_id = ?',
                (playlist_id, track_id),
            )

    def rename_file(self, track_id: str, filename: str) -> None:
        """Point the events of *track_id* at the file now holding it."""

        with self._connect() as conn:
            conn.execute(
                """UPDATE watch_events SET filename = ?
                   WHERE track_id = ?
                   AND (filename IS NULL OR filename != ?)""",
                (filename, track_id, filename),
            )

    def events(
        self,
        *,
        playlist_id: Optional[int] = None,
        filename: Optional[str] = None,
        track_ids: Optional[set[str]] = None,
    ) -> list[dict[str, Any]]:
        """Events, oldest first: every one, one watch's (*playlist_id*),
        or those about *filename* or any of *track_ids*."""

        query = f'SELECT {_EVENT_COLUMNS} FROM watch_events'
        params: list[Any] = []
        if playlist_id is not None:
            query += ' WHERE playlist_id = ?'
            params = [int(playlist_id)]
        elif filename is not None or track_ids:
            clauses = []
            if filename is not None:
                clauses.append('filename = ?')
                params.append(filename)
            ids = sorted(track_ids or ())
            if ids:
                clauses.append(f'track_id IN ({_marks(ids)})')
                params.extend(ids)
            query += f' WHERE {" OR ".join(clauses)}'
        with self._connect() as conn:
            rows = conn.execute(
                f'{query} ORDER BY happened_at, id', params
            ).fetchall()
            return [dict(r) for r in rows]

    def holdings(
        self, filename: str, track_ids: Optional[set[str]] = None
    ) -> list[dict[str, Any]]:
        """The ``downloaded_tracks`` rows (every watch) holding the file
        *filename*, or any of *track_ids*: who holds the song now."""

        ids = sorted(track_ids or ())
        clauses = ['filename = ?']
        params: list[Any] = [filename]
        if ids:
            clauses.append(f'track_spotify_id IN ({_marks(ids)})')
            params.extend(ids)
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT playlist_id, track_spotify_id, filename, '
                'downloaded_at FROM downloaded_tracks '
                f'WHERE {" OR ".join(clauses)}',
                params,
            ).fetchall()
            return [dict(r) for r in rows]

    def record_failure(
        self, playlist_id: int, song: dict[str, Any], error: str = ''
    ) -> None:
        """Remember that the watch could not download *song* this time."""

        tid = str(song.get('song_id') or '').strip()
        if not tid:
            return
        now = _now_iso()
        artists = song.get('artists') or []
        if isinstance(artists, str):
            artists = [artists]
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO watch_failures
                   (playlist_id, track_id, name, artists, error, attempts,
                    first_failed_at, last_failed_at)
                   VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                   ON CONFLICT(playlist_id, track_id) DO UPDATE SET
                   name = excluded.name, artists = excluded.artists,
                   error = excluded.error, attempts = attempts + 1,
                   last_failed_at = excluded.last_failed_at""",
                (
                    playlist_id,
                    tid,
                    str(song.get('name') or ''),
                    ', '.join(str(a) for a in artists if a),
                    str(error or '')[:500],
                    now,
                    now,
                ),
            )

    def forget_failures_except(
        self, playlist_id: int, track_ids: set[str]
    ) -> int:
        """Drop the failures of tracks no longer in the playlist."""

        with self._connect() as conn:
            stale = [
                (playlist_id, row['track_id'])
                for row in conn.execute(
                    'SELECT track_id FROM watch_failures '
                    'WHERE playlist_id = ?',
                    (playlist_id,),
                )
                if row['track_id'] not in track_ids
            ]
            conn.executemany(
                'DELETE FROM watch_failures '
                'WHERE playlist_id = ? AND track_id = ?',
                stale,
            )
        return len(stale)

    def failures(self, playlist_id: int) -> list[dict[str, Any]]:
        """The tracks the watch keeps failing to download, latest first."""

        with self._connect() as conn:
            rows = conn.execute(
                """SELECT track_id, name, artists, error, attempts,
                          first_failed_at, last_failed_at
                   FROM watch_failures WHERE playlist_id = ?
                   ORDER BY last_failed_at DESC""",
                (playlist_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def failure_counts(self) -> dict[int, int]:
        """``{watch id: tracks failing}``."""

        with self._connect() as conn:
            rows = conn.execute(
                'SELECT playlist_id, COUNT(*) AS n FROM watch_failures '
                'GROUP BY playlist_id'
            ).fetchall()
            return {int(r['playlist_id']): int(r['n']) for r in rows}


def _backfill(conn: sqlite3.Connection) -> None:
    """Once, when the table is new: the tracks watches recorded before
    events were kept become events of unknown outcome. Those from a
    watch's first day are taken for its first check's backfill."""

    conn.execute(
        f"""INSERT INTO watch_events ({_EVENT_COLUMNS})
           SELECT dt.playlist_id, p.spotify_id, p.name, p.user_id,
                  dt.track_spotify_id, '{OUTCOME_UNKNOWN}', dt.filename, '',
                  COALESCE(julianday(dt.downloaded_at)
                           <= julianday(p.created_at) + 1, 0),
                  dt.downloaded_at
           FROM downloaded_tracks dt
           JOIN monitored_playlists p ON p.id = dt.playlist_id
           ORDER BY dt.downloaded_at, dt.id"""
    )
