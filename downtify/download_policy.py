"""Persistent, reversible exclusions and cumulative download attempt budgets."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
import time
import unicodedata
from typing import Any, Callable


class DownloadPolicyBlocked(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _normalize(value: Any) -> str:
    text = unicodedata.normalize('NFKC', str(value or '')).casefold()
    # Collaborator suffixes do not change the selected version, but keep
    # every other version qualifier (live, remix, radio edit, etc.).
    text = re.sub(
        r'\s*[\[(]\s*(?:feat\.?|ft\.?|featuring)\s+[^\])]+[\])]\s*$', '', text
    )
    return ' '.join(re.sub(r'[^\w]+', ' ', text).split())


def recording(song: dict[str, Any]) -> dict[str, Any]:
    raw_id = str(song.get('song_id') or song.get('spotify_id') or '').strip()
    # Never persist a URL, query string or a token as a track identity.
    track_id = raw_id if re.fullmatch(r'[A-Za-z0-9_:-]{1,100}', raw_id) else ''
    artists = song.get('artists')
    if isinstance(artists, list) and artists:
        artist = artists[0]
    else:
        artist = str(song.get('artist') or '').split(';', 1)[0]
    try:
        duration = max(0, min(86400, int(float(song.get('duration') or 0))))
    except (ValueError, TypeError, OverflowError):
        duration = 0
    return {
        'track_id': track_id,
        'title': str(song.get('name') or song.get('title') or '')[:500],
        'artist': str(artist or '')[:300],
        'album': str(song.get('album_name') or song.get('album') or '')[:500],
        'duration': duration,
    }


def _fallback_key(row: dict[str, Any]) -> str:
    title, artist, album = (
        _normalize(row[k]) for k in ('title', 'artist', 'album')
    )
    if not title or not artist or not album or not row['duration']:
        return ''
    data = json.dumps(
        [title, artist, album, row['duration']], ensure_ascii=True
    )
    return 'metadata:' + hashlib.sha256(data.encode()).hexdigest()


class DownloadPolicy:
    """Tracks only actual attempt time, never waiting between watch checks."""

    def __init__(
        self, connect: Callable, *, clock: Callable[[], float] = time.monotonic
    ):
        self._connect = connect
        self.clock = clock
        self._lock = threading.RLock()
        self._active: set[str] = set()
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS download_policy (
                id TEXT PRIMARY KEY, track_id TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL, artist TEXT NOT NULL, album TEXT NOT NULL,
                duration INTEGER NOT NULL, title_key TEXT NOT NULL,
                artist_key TEXT NOT NULL, album_key TEXT NOT NULL,
                fallback_key TEXT NOT NULL, elapsed REAL NOT NULL DEFAULT 0,
                blocked INTEGER NOT NULL DEFAULT 0, reason TEXT NOT NULL DEFAULT '',
                requested_by INTEGER NOT NULL DEFAULT 0, updated REAL NOT NULL
            )""")
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_policy_track ON download_policy(track_id)'
            )
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_policy_match ON download_policy(title_key,artist_key)'
            )

    @staticmethod
    def _find(conn, item: dict[str, Any]):
        if item['track_id']:
            row = conn.execute(
                'SELECT * FROM download_policy WHERE track_id=?',
                (item['track_id'],),
            ).fetchone()
            if row is not None:
                return row
        if not item['duration']:
            return None
        title, artist, album = (
            _normalize(item[k]) for k in ('title', 'artist', 'album')
        )
        if not title or not artist:
            return None
        rows = conn.execute(
            """SELECT * FROM download_policy WHERE title_key=? AND artist_key=?
            AND duration>0 AND abs(duration-?)<=3""",
            (title, artist, item['duration']),
        ).fetchall()
        # Manually excluding a named version may span releases; automatic
        # budget accounting also requires the same album to avoid merging
        # ambiguous recordings. Never guess between multiple matches.
        rows = [
            row
            for row in rows
            if row['reason'] == 'manual'
            or (album and row['album_key'] == album)
        ]
        return rows[0] if len(rows) == 1 else None

    def _get_or_create(self, conn, item: dict[str, Any]):
        row = self._find(conn, item)
        if row is not None:
            return row
        fallback = _fallback_key(item)
        if not item['track_id'] and not fallback:
            raise ValueError('identity_uncertain')
        ident = secrets.token_hex(16)
        conn.execute(
            """INSERT INTO download_policy
            (id,track_id,title,artist,album,duration,title_key,artist_key,album_key,fallback_key,updated)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                ident,
                item['track_id'],
                item['title'],
                item['artist'],
                item['album'],
                item['duration'],
                _normalize(item['title']),
                _normalize(item['artist']),
                _normalize(item['album']),
                fallback,
                time.time(),
            ),
        )
        return conn.execute(
            'SELECT * FROM download_policy WHERE id=?', (ident,)
        ).fetchone()

    def blocked(self, song: dict[str, Any]) -> bool:
        with self._connect() as conn:
            row = self._find(conn, recording(song))
            return bool(row and row['blocked'])

    def suppress(
        self, song: dict[str, Any], *, user_id: int
    ) -> dict[str, Any]:
        item = recording(song)
        with self._lock, self._connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = self._get_or_create(conn, item)
            conn.execute(
                "UPDATE download_policy SET blocked=1,reason='manual',requested_by=?,updated=? WHERE id=?",
                (user_id, time.time(), row['id']),
            )
            return {'id': row['id'], 'reason': 'manual'}

    def resume(self, ident: str) -> None:
        with self._lock, self._connect() as conn:
            if ident in self._active:
                raise ValueError('attempt_still_stopping')
            changed = conn.execute(
                "UPDATE download_policy SET blocked=0,reason='',elapsed=0,updated=? WHERE id=?",
                (time.time(), ident),
            ).rowcount
            if not changed:
                raise ValueError('item_not_found')

    def exclusions(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("""SELECT id,title,artist,album,duration,elapsed,reason,updated
                FROM download_policy WHERE blocked=1 ORDER BY updated DESC LIMIT 1000""").fetchall()
            return [dict(row) for row in rows]

    def begin(self, song: dict[str, Any], limit_seconds: int):
        item = recording(song)
        with self._lock, self._connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = self._get_or_create(conn, item)
            ident = row['id']
            if row['blocked']:
                raise DownloadPolicyBlocked('download_excluded')
            if ident in self._active:
                raise DownloadPolicyBlocked('download_already_active')
            self._active.add(ident)
            return Attempt(
                self, ident, float(row['elapsed']), max(0, limit_seconds)
            )

    def _checkpoint(self, ident: str, elapsed: float, limit: int) -> bool:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                'SELECT blocked,reason,elapsed FROM download_policy WHERE id=?',
                (ident,),
            ).fetchone()
            if row is None:
                return True
            total = max(float(row['elapsed']), elapsed)
            blocked = bool(row['blocked']) or bool(limit and total >= limit)
            reason = row['reason'] or ('timeout' if blocked else '')
            conn.execute(
                'UPDATE download_policy SET elapsed=?,blocked=?,reason=?,updated=? WHERE id=?',
                (total, int(blocked), reason, time.time(), ident),
            )
            return blocked

    def succeeded(self, song: dict[str, Any]) -> None:
        with self._lock, self._connect() as conn:
            row = self._find(conn, recording(song))
            if row is not None and not row['blocked']:
                conn.execute(
                    'UPDATE download_policy SET elapsed=0,updated=? WHERE id=?',
                    (time.time(), row['id']),
                )

    def _finish(self, attempt, successful: bool) -> None:
        with self._lock:
            try:
                blocked = self._checkpoint(
                    attempt.ident, attempt.elapsed(), attempt.limit
                )
                if successful and not blocked:
                    with self._connect() as conn:
                        conn.execute(
                            'UPDATE download_policy SET elapsed=0,updated=? WHERE id=?',
                            (time.time(), attempt.ident),
                        )
            finally:
                self._active.discard(attempt.ident)


class Attempt:
    def __init__(
        self, policy: DownloadPolicy, ident: str, base: float, limit: int
    ):
        self.policy, self.ident, self.base, self.limit = (
            policy,
            ident,
            base,
            limit,
        )
        self.start = policy.clock()
        self.last_checkpoint = self.start - 10

    def elapsed(self) -> float:
        return self.base + max(0.0, self.policy.clock() - self.start)

    def check(self, *, force: bool = False) -> None:
        now = self.policy.clock()
        if not force and now - self.last_checkpoint < 2:
            return
        self.last_checkpoint = now
        if self.policy._checkpoint(self.ident, self.elapsed(), self.limit):
            raise DownloadPolicyBlocked('download_excluded')

    def finish(self, *, successful: bool) -> None:
        self.policy._finish(self, successful)
