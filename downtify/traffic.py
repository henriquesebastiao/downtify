"""Per-user traffic accounting (Settings → Users summary).

Two directions, counted separately:

* ``in`` — bytes fetched from upstream: finished library downloads and
  stream-cache fetches. A dedup hit fetches nothing and counts nothing.
* ``out`` — bytes served to clients, counted by an ASGI middleware that
  sums response bodies per signed-in user (audio, covers, archives, API
  answers alike; WebSocket frames never pass through it).

Counters, not events: one row per ``(user_id, direction)``, updated in
place. The Users summary reads them; deleting an account drops its
rows with everything else.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, MutableMapping

from .sqlite_utils import connect_sqlite

DIRECTION_IN = 'in'
DIRECTION_OUT = 'out'
DIRECTIONS = (DIRECTION_IN, DIRECTION_OUT)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TrafficCounters:
    """``(user_id, direction)`` byte counters in ``downtify_library.db``."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traffic_counters (
                    user_id INTEGER NOT NULL,
                    direction TEXT NOT NULL,
                    total_bytes INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, direction)
                )
            """)

    def add(self, user_id: int, direction: str, nbytes: int) -> None:
        """Add *nbytes* to a counter. Ignores junk (nobody, bad direction,
        nothing)."""

        uid = int(user_id or 0)
        try:
            count = int(nbytes)
        except (TypeError, ValueError):
            return
        if not uid or direction not in DIRECTIONS or count <= 0:
            return
        with self._lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO traffic_counters
                   (user_id, direction, total_bytes, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id, direction) DO UPDATE SET
                   total_bytes = total_bytes + excluded.total_bytes,
                   updated_at = excluded.updated_at""",
                (uid, direction, count, _now_iso()),
            )

    def totals(self) -> dict[int, dict[str, int]]:
        """``{user_id: {'in': bytes, 'out': bytes}}``."""

        with self._connect() as conn:
            rows = conn.execute(
                'SELECT user_id, direction, total_bytes FROM traffic_counters'
            ).fetchall()
        result: dict[int, dict[str, int]] = {}
        for row in rows:
            entry = result.setdefault(int(row['user_id']), {'in': 0, 'out': 0})
            if str(row['direction']) in DIRECTIONS:
                entry[str(row['direction'])] = int(row['total_bytes'] or 0)
        return result

    def remove_user(self, user_id: int) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                'DELETE FROM traffic_counters WHERE user_id = ?',
                (int(user_id),),
            )


class TrafficMiddleware:
    """Count served bytes per signed-in user.

    Runs inside the auth middleware (which puts the principal in the
    scope), summing ``http.response.body`` chunks and filing one counter
    update when the response is done. Failures to count never fail the
    response itself.
    """

    def __init__(
        self,
        app: Callable[..., Awaitable[None]],
        get_counters: Callable[[], Any],
    ) -> None:
        self._app = app
        self._get_counters = get_counters

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: Callable[..., Awaitable[Any]],
        send: Callable[..., Awaitable[None]],
    ) -> None:
        if scope.get('type') != 'http':
            await self._app(scope, receive, send)
            return
        principal = (scope.get('state') or {}).get('principal')
        user_id = int(getattr(principal, 'user_id', 0) or 0)
        if not user_id:
            await self._app(scope, receive, send)
            return
        total = 0

        async def counting_send(message: MutableMapping[str, Any]) -> None:
            nonlocal total
            if message.get('type') == 'http.response.body':
                body = message.get('body', b'')
                total += len(body) if isinstance(body, bytes) else 0
            await send(message)

        try:
            await self._app(scope, receive, counting_send)
        finally:
            if total > 0:
                try:
                    counters = self._get_counters()
                    if counters is not None:
                        counters.add(user_id, DIRECTION_OUT, total)
                except Exception:
                    pass
