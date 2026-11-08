"""Connections must close when their ``with`` block ends.

On Python 3.11+ an unclosed ``sqlite3`` connection lingers until the
cyclic GC runs, holding its file descriptors; a loop of short lookups
(e.g. ``GET /api/playlists/batches`` on a large playlist) then exhausts
the process's descriptor limit.
"""

from __future__ import annotations

import gc
import sqlite3

import pytest

from downtify.monitor import PlaylistMonitorDB
from downtify.sqlite_utils import connect_sqlite


def test_with_block_commits_then_closes(tmp_path):
    path = str(tmp_path / 'db.sqlite')
    with connect_sqlite(path) as conn:
        conn.execute('CREATE TABLE t (x INTEGER)')
        conn.execute('INSERT INTO t VALUES (1)')

    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute('SELECT 1')
    with connect_sqlite(path) as other:
        assert other.execute('SELECT x FROM t').fetchall() == [(1,)]


def _insert_then_fail(path: str, used: list[sqlite3.Connection]) -> None:
    with connect_sqlite(path) as conn:
        used.append(conn)
        conn.execute('INSERT INTO t VALUES (1)')
        raise RuntimeError('boom')


def test_with_block_rolls_back_then_closes_on_error(tmp_path):
    path = str(tmp_path / 'db.sqlite')
    with connect_sqlite(path) as conn:
        conn.execute('CREATE TABLE t (x INTEGER)')

    used: list[sqlite3.Connection] = []
    with pytest.raises(RuntimeError):
        _insert_then_fail(path, used)

    with pytest.raises(sqlite3.ProgrammingError):
        used[0].execute('SELECT 1')
    with connect_sqlite(path) as other:
        assert other.execute('SELECT x FROM t').fetchall() == []


def test_row_factory_still_applies(tmp_path):
    with connect_sqlite(str(tmp_path / 'db.sqlite'), row_factory=True) as c:
        row = c.execute('SELECT 1 AS one').fetchone()
        assert row['one'] == 1


def test_many_lookups_leave_no_open_connection(tmp_path):
    path = str(tmp_path / 'db.sqlite')
    with connect_sqlite(path) as conn:
        conn.execute('CREATE TABLE t (x INTEGER)')

    opened: list[sqlite3.Connection] = []
    gc.disable()
    try:
        for _ in range(200):
            with connect_sqlite(path) as conn:
                conn.execute('SELECT COUNT(*) FROM t').fetchone()
            opened.append(conn)
        still_open = 0
        for conn in opened:
            try:
                conn.execute('SELECT 1')
                still_open += 1
            except sqlite3.ProgrammingError:
                pass
    finally:
        gc.enable()
    assert still_open == 0


def test_playlist_monitor_db_connections_close(tmp_path):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    with db._connect() as conn:
        conn.execute('SELECT 1')

    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute('SELECT 1')
