"""Pausing the download queue, and keeping it across restarts.

:data:`queue_pause` is the process-wide switch (``POST
/api/queue/pause|resume``): while it is paused no download starts - a
waiting job stays where it is, holding its slot if it has one - and the
downloads already running finish normally. The queue reads as
``pausing`` until the last of them ends, then ``paused``. Playlist
Monitor sweeps wait at the same switch before every track.

:class:`PendingDownloads` is the sqlite copy of the jobs that haven't
finished yet, plus the switch itself, so a restart (or an update) picks
the queue back up where it stopped - still paused when it was.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import sqlite3
from collections.abc import AsyncIterator, Awaitable, Callable, Collection
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from .sqlite_utils import connect_sqlite

STATE_RUNNING = 'running'
STATE_PAUSING = 'pausing'
STATE_PAUSED = 'paused'

#: Keeps every ``IN (...)`` under SQLite's bound-parameter limit.
_CHUNK = 500


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


class PendingDownloads:
    """SQLite copy of the unfinished download jobs, in queue order."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path)

    def _init_db(self) -> None:
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
        with self._connect() as conn:
            for row in rows:
                users = sorted({int(uid) for uid in row.user_ids if uid})
                saved = conn.execute(
                    'SELECT user_ids FROM pending_downloads WHERE song_id = ?',
                    (row.song_id,),
                ).fetchone()
                if saved is None:
                    conn.execute(
                        'INSERT INTO pending_downloads '
                        '(song_id, song, options, user_ids) '
                        'VALUES (?, ?, ?, ?)',
                        (
                            row.song_id,
                            json.dumps(row.song, default=str),
                            json.dumps(row.options, default=str),
                            json.dumps(users),
                        ),
                    )
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
        for song_id, song, options, user_ids in found:
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

    def paused(self) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM download_queue_state WHERE key = 'paused'"
            ).fetchone()
        return bool(row) and row[0] == '1'

    def set_paused(self, value: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                'INSERT INTO download_queue_state (key, value) '
                "VALUES ('paused', ?) "
                'ON CONFLICT(key) DO UPDATE SET value = excluded.value',
                ('1' if value else '0',),
            )


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
