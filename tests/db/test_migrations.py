from __future__ import annotations

import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import psycopg
import pytest

from downtify.db.core import Database
from downtify.db.migrations.runner import (
    applied_versions,
    discover,
    run_migrations,
)

_TEST_URL_ENV = 'TEST_DATABASE_URL'

_MIGRATION_A = """
def up(conn):
    conn.execute('create table t_a (id integer primary key)')
"""

_MIGRATION_B = """
def up(conn):
    conn.execute('create table t_b (id integer primary key)')
"""

_MIGRATION_B_RAISES = """
def up(conn):
    conn.execute('create table t_b (id integer primary key)')
    raise RuntimeError('boom')
"""


@pytest.fixture
def pg_schema():
    url = os.environ.get(_TEST_URL_ENV)
    if not url:
        pytest.skip(f'{_TEST_URL_ENV} not set')
    schema = f'sc_{uuid.uuid4().hex[:8]}'
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(f'create schema {schema}')
    try:
        yield url, schema
    finally:
        with psycopg.connect(url, autocommit=True) as admin:
            admin.execute(f'drop schema if exists {schema} cascade')


@pytest.fixture
def pg_db(pg_schema):
    url, schema = pg_schema
    database = Database.postgres(url, search_path=schema, max_size=8)
    try:
        yield database
    finally:
        database.close()


@pytest.fixture
def pkg_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Write a throw-away package of migration modules; return its name."""
    monkeypatch.syspath_prepend(str(tmp_path))

    def make(files: dict[str, str]) -> str:
        name = f'mig_{uuid.uuid4().hex}'
        pkg_dir = tmp_path / name
        pkg_dir.mkdir()
        (pkg_dir / '__init__.py').write_text('')
        for filename, source in files.items():
            (pkg_dir / filename).write_text(source)
        return name

    return make


def _table_exists(database: Database, table: str) -> bool:
    with database.connect() as conn:
        row = conn.execute(
            f"select to_regclass('{table}') is not null"
        ).fetchone()
    return bool(row[0])


def test_discover_sorts_by_version(pkg_factory) -> None:
    pkg = pkg_factory({'0002_b.py': _MIGRATION_B, '0001_a.py': _MIGRATION_A})
    migrations = discover(pkg)
    assert [m.version for m in migrations] == [1, 2]
    assert [m.name for m in migrations] == ['0001_a', '0002_b']
    assert all(callable(m.up) for m in migrations)


def test_discover_ignores_non_matching_modules(pkg_factory) -> None:
    pkg = pkg_factory({
        '0001_a.py': _MIGRATION_A,
        '0002_b.py': _MIGRATION_B,
        'helper.py': 'raise RuntimeError("must not be imported")\n',
        '0003_Bad.py': 'raise RuntimeError("must not be imported")\n',
        '0004-dash.py': 'raise RuntimeError("must not be imported")\n',
        '12_short.py': 'raise RuntimeError("must not be imported")\n',
    })
    migrations = discover(pkg)
    assert [m.version for m in migrations] == [1, 2]
    for ignored in ('helper', '0003_Bad', '0004-dash', '12_short'):
        assert f'{pkg}.{ignored}' not in sys.modules


def test_discover_rejects_duplicate_versions(pkg_factory) -> None:
    pkg = pkg_factory({'0001_a.py': _MIGRATION_A, '0001_b.py': _MIGRATION_B})
    with pytest.raises(RuntimeError, match='0001'):
        discover(pkg)


def test_discover_requires_up(pkg_factory) -> None:
    pkg = pkg_factory({'0001_a.py': 'x = 1\n'})
    with pytest.raises(RuntimeError, match='0001_a'):
        discover(pkg)


def test_sqlite_is_noop_and_creates_nothing(
    pkg_factory, tmp_path: Path
) -> None:
    pkg = pkg_factory({'0001_a.py': _MIGRATION_A, '0002_b.py': _MIGRATION_B})
    database = Database.sqlite(tmp_path / 'store.db')
    try:
        assert run_migrations(database, package=pkg) == []
        assert applied_versions(database) == []
        with database.connect() as conn:
            tables = conn.execute(
                "select name from sqlite_master where type = 'table'"
            ).fetchall()
        assert tables == []
    finally:
        database.close()


def test_postgres_applies_in_order_and_records(
    pg_db: Database, pkg_factory
) -> None:
    pkg = pkg_factory({'0002_b.py': _MIGRATION_B, '0001_a.py': _MIGRATION_A})
    assert applied_versions(pg_db) == []
    assert run_migrations(pg_db, package=pkg) == [1, 2]
    assert applied_versions(pg_db) == [1, 2]
    assert _table_exists(pg_db, 't_a')
    assert _table_exists(pg_db, 't_b')


def test_postgres_second_run_applies_nothing(
    pg_db: Database, pkg_factory
) -> None:
    pkg = pkg_factory({'0001_a.py': _MIGRATION_A, '0002_b.py': _MIGRATION_B})
    assert run_migrations(pg_db, package=pkg) == [1, 2]
    assert run_migrations(pg_db, package=pkg) == []
    assert applied_versions(pg_db) == [1, 2]


def test_postgres_failure_rolls_back_whole_run(
    pg_db: Database, pkg_factory
) -> None:
    pkg = pkg_factory({
        '0001_a.py': _MIGRATION_A,
        '0002_b.py': _MIGRATION_B_RAISES,
    })
    with pytest.raises(RuntimeError, match='boom'):
        run_migrations(pg_db, package=pkg)
    assert applied_versions(pg_db) == []
    assert not _table_exists(pg_db, 't_a')
    assert not _table_exists(pg_db, 't_b')


def test_postgres_concurrent_runs_apply_each_version_once(
    pg_db: Database, pkg_factory
) -> None:
    pkg = pkg_factory({'0001_a.py': _MIGRATION_A, '0002_b.py': _MIGRATION_B})
    workers = 4
    barrier = Barrier(workers)

    def start() -> list[int]:
        barrier.wait()
        return run_migrations(pg_db, package=pkg)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(start) for _ in range(workers)]
        results = [future.result() for future in futures]

    applied = sorted(version for result in results for version in result)
    assert applied == [1, 2]
    assert applied_versions(pg_db) == [1, 2]
