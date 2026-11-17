"""Backend-neutral database access for SQLite and PostgreSQL.

``Database`` hands out ``Connection`` objects. Each connection exposes the
same small API on both backends: ``?`` placeholders (translated for
PostgreSQL), rows that support both index and column-name access, and
errors translated to the classes in ``downtify.db.errors``.
"""

from __future__ import annotations

import contextlib
import random
import threading
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path
from typing import Any, TypeVar

from psycopg_pool import ConnectionPool

from downtify.db.config import DbConfig, Dialect
from downtify.db.errors import DatabaseError, SerializationRetry, wrap_errors
from downtify.db.rows import pg_row_factory
from downtify.db.sql import to_pyformat
from downtify.sqlite_utils import connect_sqlite

T = TypeVar('T')

_POOLS: dict[tuple[str, str | None], ConnectionPool] = {}
_POOLS_LOCK = threading.Lock()


class Cursor:
    """Thin wrapper over a driver cursor with translated errors."""

    def __init__(self, raw: Any, dialect: Dialect) -> None:
        self._raw = raw
        self._dialect = dialect

    @property
    def rowcount(self) -> int:
        return self._raw.rowcount

    @property
    def lastrowid(self) -> int | None:
        """SQLite's last inserted row id; always None on PostgreSQL."""
        if self._dialect is Dialect.SQLITE:
            return self._raw.lastrowid
        return None

    @property
    def description(self) -> Any:
        return self._raw.description

    def fetchone(self) -> Any:
        with wrap_errors():
            return self._raw.fetchone()

    def fetchall(self) -> list[Any]:
        with wrap_errors():
            return self._raw.fetchall()

    def fetchmany(self, size: int) -> list[Any]:
        with wrap_errors():
            return self._raw.fetchmany(size)

    def __iter__(self) -> Iterator[Any]:
        while True:
            row = self.fetchone()
            if row is None:
                return
            yield row

    def close(self) -> None:
        with wrap_errors():
            self._raw.close()


class Connection:
    """A single database connection, usable on either backend."""

    def __init__(self, dialect: Dialect, raw: Any) -> None:
        self.dialect = dialect
        self.raw = raw
        self._postgres_changes = 0

    @property
    def total_changes(self) -> int:
        if self.dialect is Dialect.SQLITE:
            return self.raw.total_changes
        return self._postgres_changes

    def _count(self, sql: str, raw_cursor: Any) -> None:
        # Only meaningful on PostgreSQL; SQLite reports its own total, which
        # counts rows changed by INSERT/UPDATE/DELETE only (not SELECT).
        if self.dialect is not Dialect.POSTGRES or raw_cursor.rowcount <= 0:
            return
        if sql.lstrip()[:6].upper() in {'INSERT', 'UPDATE', 'DELETE'}:
            self._postgres_changes += raw_cursor.rowcount

    def execute(self, sql: str, params: Iterable[Any] = ()) -> Cursor:
        values = tuple(params)
        with wrap_errors():
            if self.dialect is Dialect.POSTGRES:
                raw_cursor = self.raw.execute(to_pyformat(sql), values)
            else:
                raw_cursor = self.raw.execute(sql, values)
            self._count(sql, raw_cursor)
        return Cursor(raw_cursor, self.dialect)

    def executemany(self, sql: str, seq: Iterable[Sequence[Any]]) -> Cursor:
        with wrap_errors():
            if self.dialect is Dialect.POSTGRES:
                raw_cursor = self.raw.cursor()
                raw_cursor.executemany(
                    to_pyformat(sql), [tuple(row) for row in seq]
                )
            else:
                raw_cursor = self.raw.executemany(sql, seq)
            self._count(sql, raw_cursor)
        return Cursor(raw_cursor, self.dialect)

    def executescript(self, sql: str) -> None:
        # No parameters: the SQL must not be pyformat-translated.
        with wrap_errors():
            if self.dialect is Dialect.POSTGRES:
                self.raw.execute(sql)
            else:
                self.raw.executescript(sql)

    def commit(self) -> None:
        with wrap_errors():
            self.raw.commit()

    def rollback(self) -> None:
        with wrap_errors():
            self.raw.rollback()


class _ThreadState(threading.local):
    """Per-thread bookkeeping for one ``Database``'s connect() nesting."""

    depth: int = 0
    conn: Connection | None = None
    failed: bool = False


class Database:
    """Opens connections to one SQLite file or one PostgreSQL pool."""

    def __init__(
        self,
        dialect: Dialect,
        *,
        path: Path | None = None,
        pool: ConnectionPool | None = None,
        pool_key: tuple[str, str | None] | None = None,
    ) -> None:
        self.dialect = dialect
        self.path = path
        self._pool = pool
        self._pool_key = pool_key
        self._local = _ThreadState()

    @classmethod
    def sqlite(cls, path: str | Path) -> Database:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return cls(Dialect.SQLITE, path=file_path)

    @classmethod
    def postgres(
        cls,
        url: str,
        *,
        min_size: int = 2,
        max_size: int = 20,
        timeout: float = 10.0,
        search_path: str | None = None,
    ) -> Database:
        key = (url, search_path)
        with _POOLS_LOCK:
            pool = _POOLS.get(key)
            if pool is None:
                kwargs: dict[str, Any] = {'row_factory': pg_row_factory}
                # UTC session time zone: naive ISO timestamps then compare
                # like SQLite's (UTC) julianday().
                options = '-c timezone=UTC'
                if search_path:
                    options += f' -c search_path={search_path}'
                kwargs['options'] = options
                pool = ConnectionPool(
                    url,
                    min_size=min_size,
                    max_size=max_size,
                    timeout=timeout,
                    kwargs=kwargs,
                    open=True,
                )
                _POOLS[key] = pool
        return cls(Dialect.POSTGRES, pool=pool, pool_key=key)

    @classmethod
    def for_group(cls, cfg: DbConfig, group: str) -> Database:
        if cfg.dialect is Dialect.SQLITE:
            return cls.sqlite(cfg.sqlite_path(group))
        assert cfg.url is not None
        return cls.postgres(
            cfg.url,
            min_size=cfg.pool_min,
            max_size=cfg.pool_max,
            timeout=cfg.pool_timeout,
            search_path=cfg.search_path,
        )

    def _acquire(self) -> Connection:
        if self.dialect is Dialect.SQLITE:
            with wrap_errors():
                raw = connect_sqlite(str(self.path), row_factory=True)
        else:
            assert self._pool is not None
            with wrap_errors():
                raw = self._pool.getconn()
        return Connection(self.dialect, raw)

    def _release(self, conn: Connection) -> None:
        if self.dialect is Dialect.SQLITE:
            conn.raw.close()
        else:
            assert self._pool is not None
            self._pool.putconn(conn.raw)

    @contextlib.contextmanager
    def _session(self, *, lock: bool) -> Iterator[Connection]:
        state = self._local
        if state.depth:
            # Nested on this thread: reuse the open connection.
            assert state.conn is not None
            state.depth += 1
            try:
                yield state.conn
            except BaseException:
                state.failed = True
                raise
            finally:
                state.depth -= 1
            return

        conn = self._acquire()
        state.conn, state.depth, state.failed = conn, 1, False
        commit = False
        try:
            if lock and self.dialect is Dialect.SQLITE:
                conn.execute('BEGIN IMMEDIATE')
            yield conn
            commit = not state.failed
        finally:
            state.conn, state.depth, state.failed = None, 0, False
            try:
                if commit:
                    conn.commit()
                else:
                    # Keep the original exception if rollback also fails.
                    with contextlib.suppress(DatabaseError):
                        conn.rollback()
            finally:
                self._release(conn)

    def connect(self) -> contextlib.AbstractContextManager[Connection]:
        """Yield a connection; re-entrant per thread.

        Only the outermost block commits or rolls back and releases the
        connection.
        """
        return self._session(lock=False)

    def transaction(
        self, *, lock: bool = False
    ) -> contextlib.AbstractContextManager[Connection]:
        """Like ``connect()``; on SQLite, ``lock=True`` takes a write lock
        up front with ``BEGIN IMMEDIATE`` when opening a new connection.
        """
        return self._session(lock=lock)

    def run(
        self,
        fn: Callable[[Connection], T],
        *,
        lock: bool = False,
        retries: int = 3,
    ) -> T:
        """Run ``fn(conn)`` in a transaction, retrying on serialization
        failures. Inside an open ``connect()`` it runs once without retry.
        """
        if self._local.depth:
            assert self._local.conn is not None
            return fn(self._local.conn)
        attempt = 0
        while True:
            try:
                with self.transaction(lock=lock) as conn:
                    return fn(conn)
            except SerializationRetry:
                if attempt >= retries:
                    raise
                time.sleep(0.05 * 2**attempt + random.uniform(0, 0.05))
                attempt += 1

    def healthcheck(self) -> bool:
        try:
            with self.connect() as conn:
                conn.execute('select 1').fetchone()
        except Exception:
            return False
        return True

    def close(self) -> None:
        if self._pool is None or self._pool_key is None:
            return
        with _POOLS_LOCK:
            if _POOLS.get(self._pool_key) is self._pool:
                del _POOLS[self._pool_key]
        self._pool.close()


def as_database(obj: Database | str | Path, group: str) -> Database:
    """Return ``obj`` if it is a Database, else open it as a SQLite path.

    ``group`` is accepted for symmetry with ``Database.for_group``.
    """
    if isinstance(obj, Database):
        return obj
    return Database.sqlite(obj)
