"""Pausing the download queue, and keeping it across restarts.

:data:`queue_pause` is the process-wide switch (``POST
/api/queue/pause|resume``): while it is paused no download starts - a
waiting job stays where it is, holding its slot if it has one - and the
downloads already running finish normally. The queue reads as
``pausing`` until the last of them ends, then ``paused``. Playlist
Monitor sweeps wait at the same switch before every track.

:class:`PendingDownloads` is the database copy of the jobs that haven't
finished yet, plus the switch itself, so a restart (or an update) picks
the queue back up where it stopped - still paused when it was. It also
keeps the jobs that failed (with why), so the queue's Failed tab and its
**Retry failed** survive a restart too (issue #678): they come back as
failed, never run on their own, and leave the copy once retried,
removed or cleared.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Collection
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from .db.config import Dialect
from .db.core import Connection, Database, as_database

STATE_RUNNING = 'running'
STATE_PAUSING = 'pausing'
STATE_PAUSED = 'paused'

#: Keeps every ``IN (...)`` under SQLite's bound-parameter limit.
_CHUNK = 500
#: Failed jobs kept across restarts; the oldest go first past this.
FAILED_LIMIT = 2000


def _release(waiter: asyncio.Future[None]) -> None:
    if not waiter.done():
        waiter.set_result(None)


class QueuePause:
    """Hold new downloads while paused; count the ones still running."""

    def __init__(self) -> None:
        self._paused = False
        self._active = 0
        self._waiters: list[asyncio.Future[None]] = []
        #: Awaited when the last running download of a paused queue ends
        #: (the API broadcasts the new state from it).
        self.on_drained: Optional[Callable[[], Awaitable[Any]]] = None

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def active(self) -> int:
        return self._active

    @property
    def state(self) -> str:
        if not self._paused:
            return STATE_RUNNING
        return STATE_PAUSING if self._active else STATE_PAUSED

    def status(self) -> dict[str, Any]:
        return {
            'paused': self._paused,
            'state': self.state,
            'active': self._active,
        }

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False
        waiters, self._waiters = self._waiters, []
        for waiter in waiters:
            # A waiter may belong to a loop that already closed (tests).
            with contextlib.suppress(RuntimeError):
                waiter.get_loop().call_soon_threadsafe(_release, waiter)

    async def wait(self) -> None:
        """Return once the queue runs - at once when it isn't paused."""

        while self._paused:
            waiter = asyncio.get_running_loop().create_future()
            self._waiters.append(waiter)
            try:
                await waiter
            finally:
                with contextlib.suppress(ValueError):
                    self._waiters.remove(waiter)

    @contextlib.asynccontextmanager
    async def running(self) -> AsyncIterator[None]:
        """Count one download as running for as long as the block lasts."""

        await self.wait()
        self._active += 1
        try:
            yield
        finally:
            self._active -= 1
            if self._paused and not self._active and self.on_drained:
                try:
                    await self.on_drained()
                except Exception:
                    logger.opt(exception=True).debug(
                        'Could not announce the paused queue'
                    )


queue_pause = QueuePause()


@dataclass
class PendingDownload:
    """One saved job: what ``_run_download`` needs to run it again."""

    song_id: str
    song: dict[str, Any]
    #: ``subdir``, ``delay_seconds``, ``playlist_name``,
    #: ``spotify_playlist_id`` and ``track_order``.
    options: dict[str, Any] = field(default_factory=dict)
    user_ids: list[int] = field(default_factory=list)


@dataclass
class FailedDownload(PendingDownload):
    """One saved failed job, and why it failed."""

    message: str = ''


class PendingDownloads:
    """Database copy of the unfinished download jobs, in queue order."""

    def __init__(self, path_or_db: str | Path | Database) -> None:
        self.db = as_database(path_or_db, 'library')
        if isinstance(path_or_db, (str, Path)):
            self._path: Optional[str] = str(path_or_db)
        else:
            self._path = str(self.db.path) if self.db.path else None
        self._init_db()

    def _connect(self) -> Any:
        return self.db.connect()

    def _init_db(self) -> None:
        # PostgreSQL gets its schema from the library migrations.
        if self.db.dialect is not Dialect.SQLITE:
            return
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_downloads (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    song_id TEXT NOT NULL UNIQUE,
                    song TEXT NOT NULL,
                    options TEXT NOT NULL DEFAULT '{}',
                    user_ids TEXT NOT NULL DEFAULT '[]'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS failed_downloads (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    song_id TEXT NOT NULL UNIQUE,
                    song TEXT NOT NULL,
                    options TEXT NOT NULL DEFAULT '{}',
                    user_ids TEXT NOT NULL DEFAULT '[]',
                    message TEXT NOT NULL DEFAULT '',
                    failed_at TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_queue_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

    def add(self, rows: Collection[PendingDownload]) -> None:
        """Save *rows* at the end of the queue.

        A job already saved keeps its place (and its options); only the
        accounts waiting on it are merged in.
        """

        if not rows:
            return
        with self.db.transaction(lock=True) as conn:
            for row in rows:
                users = sorted({int(uid) for uid in row.user_ids if uid})
                inserted = conn.execute(
                    'INSERT INTO pending_downloads '
                    '(song_id, song, options, user_ids) '
                    'VALUES (?, ?, ?, ?) '
                    'ON CONFLICT (song_id) DO NOTHING',
                    (
                        row.song_id,
                        json.dumps(row.song, default=str),
                        json.dumps(row.options, default=str),
                        json.dumps(users),
                    ),
                ).rowcount
                if inserted:
                    continue
                saved = conn.execute(
                    'SELECT user_ids FROM pending_downloads '
                    'WHERE song_id = ?' + _row_lock(conn),
                    (row.song_id,),
                ).fetchone()
                if saved is None:
                    continue
                merged = sorted(set(_user_ids(saved[0])) | set(users))
                conn.execute(
                    'UPDATE pending_downloads SET user_ids = ? '
                    'WHERE song_id = ?',
                    (json.dumps(merged), row.song_id),
                )

    def forget(self, song_ids: Collection[str]) -> None:
        ids = list(dict.fromkeys(str(sid) for sid in song_ids if sid))
        if not ids:
            return
        with self._connect() as conn:
            for start in range(0, len(ids), _CHUNK):
                chunk = ids[start : start + _CHUNK]
                marks = ','.join('?' * len(chunk))
                conn.execute(
                    f'DELETE FROM pending_downloads WHERE song_id IN ({marks})',
                    chunk,
                )

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute('DELETE FROM pending_downloads')

    def rows(self) -> list[PendingDownload]:
        """Every saved job, first queued first (unreadable rows skipped)."""

        with self._connect() as conn:
            found = conn.execute(
                'SELECT song_id, song, options, user_ids '
                'FROM pending_downloads ORDER BY seq'
            ).fetchall()
        rows: list[PendingDownload] = []
        for raw in found:
            song_id, song, options, user_ids = tuple(raw)
            try:
                song_dict = json.loads(song)
                options_dict = json.loads(options or '{}')
            except ValueError:
                logger.warning(
                    'Skipping unreadable saved download {}', song_id
                )
                continue
            if not isinstance(song_dict, dict):
                continue
            rows.append(
                PendingDownload(
                    song_id=str(song_id),
                    song=song_dict,
                    options=options_dict
                    if isinstance(options_dict, dict)
                    else {},
                    user_ids=_user_ids(user_ids),
                )
            )
        return rows

    # Failed jobs (issue #678)

    def save_failed(self, row: PendingDownload, message: str) -> None:
        """Keep *row* as failed with *message*, at the end of the list
        (a job failing again moves there); the accounts on it merge."""

        users = sorted({int(uid) for uid in row.user_ids if uid})
        with self.db.transaction(lock=True) as conn:
            saved = conn.execute(
                'SELECT user_ids FROM failed_downloads '
                'WHERE song_id = ?' + _row_lock(conn),
                (row.song_id,),
            ).fetchone()
            if saved is not None:
                users = sorted(set(_user_ids(saved[0])) | set(users))
                conn.execute(
                    'DELETE FROM failed_downloads WHERE song_id = ?',
                    (row.song_id,),
                )
            conn.execute(
                'INSERT INTO failed_downloads '
                '(song_id, song, options, user_ids, message, failed_at) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (
                    row.song_id,
                    json.dumps(row.song, default=str),
                    json.dumps(row.options, default=str),
                    json.dumps(users),
                    str(message or '')[:2000],
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.execute(
                'DELETE FROM failed_downloads WHERE seq NOT IN ('
                'SELECT seq FROM failed_downloads ORDER BY seq DESC '
                'LIMIT ?)',
                (FAILED_LIMIT,),
            )

    def forget_failed(self, song_ids: Collection[str]) -> None:
        ids = list(dict.fromkeys(str(sid) for sid in song_ids if sid))
        if not ids:
            return
        with self._connect() as conn:
            for start in range(0, len(ids), _CHUNK):
                chunk = ids[start : start + _CHUNK]
                marks = ','.join('?' * len(chunk))
                conn.execute(
                    f'DELETE FROM failed_downloads WHERE song_id IN ({marks})',
                    chunk,
                )

    def clear_failed(self) -> None:
        with self._connect() as conn:
            conn.execute('DELETE FROM failed_downloads')

    def failed_rows(self) -> list[FailedDownload]:
        """Every saved failed job, oldest failure first."""

        with self._connect() as conn:
            found = conn.execute(
                'SELECT song_id, song, options, user_ids, message '
                'FROM failed_downloads ORDER BY seq'
            ).fetchall()
        rows: list[FailedDownload] = []
        for raw in found:
            song_id, song, options, user_ids, message = tuple(raw)
            try:
                song_dict = json.loads(song)
                options_dict = json.loads(options or '{}')
            except ValueError:
                logger.warning(
                    'Skipping unreadable failed download {}', song_id
                )
                continue
            if not isinstance(song_dict, dict):
                continue
            rows.append(
                FailedDownload(
                    song_id=str(song_id),
                    song=song_dict,
                    options=options_dict
                    if isinstance(options_dict, dict)
                    else {},
                    user_ids=_user_ids(user_ids),
                    message=str(message or ''),
                )
            )
        return rows

    def paused(self) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM download_queue_state WHERE key = 'paused'"
            ).fetchone()
        return bool(row) and tuple(row)[0] == '1'

    def set_paused(self, value: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                'INSERT INTO download_queue_state (key, value) '
                "VALUES ('paused', ?) "
                'ON CONFLICT(key) DO UPDATE SET value = excluded.value',
                ('1' if value else '0',),
            )


def _row_lock(conn: Connection) -> str:
    """Row lock for read-modify-write on PostgreSQL (SQLite has none)."""
    return ' FOR UPDATE' if conn.dialect is Dialect.POSTGRES else ''


def _user_ids(raw: Any) -> list[int]:
    try:
        values = json.loads(raw or '[]')
    except (TypeError, ValueError):
        return []
    if not isinstance(values, list):
        return []
    found: set[int] = set()
    for value in values:
        try:
            uid = int(value)
        except (TypeError, ValueError):
            continue
        if uid:
            found.add(uid)
    return sorted(found)
