from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import closing
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

from downtify.activity import ActivityLog
from downtify.auth import AuthStore
from downtify.db.migrations.schema import activity, auth, doctor
from downtify.doctor_audio import AudioHashCache
from downtify.duplicate_merge import KeptApart
from downtify.traffic import TrafficCounters

requires_pg = pytest.mark.skipif(
    not os.environ.get('TEST_DATABASE_URL'),
    reason='TEST_DATABASE_URL not set',
)


def _build_sqlite(tmp_path: Path) -> list[Path]:
    """Run every SQLite store once so its final schema exists on disk."""

    paths = [
        tmp_path / 'auth.db',
        tmp_path / 'activity.db',
        tmp_path / 'library.db',
        tmp_path / 'audio.db',
        tmp_path / 'kept.db',
    ]
    AuthStore(paths[0], tmp_path / 'secret.key')
    ActivityLog(paths[1])
    TrafficCounters(paths[2])
    AudioHashCache(paths[3])
    KeptApart(paths[4])
    return paths


def _sqlite_schema(tmp_path: Path) -> tuple[dict[str, set[str]], set[str]]:
    tables: dict[str, set[str]] = {}
    indexes: set[str] = set()
    for path in _build_sqlite(tmp_path):
        with closing(sqlite3.connect(path)) as conn:
            names = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            for (table,) in names:
                info = conn.execute(f'PRAGMA table_info({table})').fetchall()
                tables[table] = {row[1] for row in info}
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' "
                'AND sql IS NOT NULL'
            ).fetchall()
            indexes.update(name for (name,) in rows)
    return tables, indexes


@requires_pg
def test_schema_matches_sqlite(tmp_path: Path) -> None:
    url = os.environ['TEST_DATABASE_URL']
    sqlite_tables, sqlite_indexes = _sqlite_schema(tmp_path)
    schema = f'sc_{uuid.uuid4().hex[:8]}'
    ddl = auth.DDL + activity.DDL + doctor.DDL

    with closing(psycopg.connect(url, autocommit=True)) as admin:
        admin.execute(
            sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema))
        )
        try:
            with closing(
                psycopg.connect(
                    url,
                    autocommit=True,
                    options=f'-c search_path={schema}',
                )
            ) as conn:
                for statement in ddl:
                    conn.execute(statement)
                columns = conn.execute(
                    'SELECT table_name, column_name '
                    'FROM information_schema.columns '
                    'WHERE table_schema = %s',
                    (schema,),
                ).fetchall()
                index_rows = conn.execute(
                    'SELECT indexname FROM pg_indexes WHERE schemaname = %s',
                    (schema,),
                ).fetchall()
        finally:
            admin.execute(
                sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(
                    sql.Identifier(schema)
                )
            )

    pg_tables: dict[str, set[str]] = {}
    for table, column in columns:
        pg_tables.setdefault(table, set()).add(column)
    pg_indexes = {name for (name,) in index_rows}

    assert set(pg_tables) == set(sqlite_tables)
    for table, expected in sqlite_tables.items():
        assert pg_tables[table] == expected, table
    assert sqlite_indexes <= pg_indexes
