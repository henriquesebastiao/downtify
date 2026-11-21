from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
import pytest

from downtify.db.config import DbConfig, Dialect
from downtify.db.core import Database, as_database
from downtify.db.errors import (
    IntegrityError,
    SerializationRetry,
    UndefinedTable,
)

_TEST_URL_ENV = 'TEST_DATABASE_URL'


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


@pytest.fixture(params=['sqlite', 'postgres'])
def db(request, tmp_path: Path):
    if request.param == 'sqlite':
        database = Database.sqlite(tmp_path / 'test.db')
    else:
        url, schema = request.getfixturevalue('pg_schema')
        database = Database.postgres(url, search_path=schema, max_size=4)
    try:
        yield database
    finally:
        database.close()


def _script(database: Database, sql: str) -> None:
    with database.connect() as conn:
        conn.executescript(sql)


def _create_people(database: Database) -> None:
    _script(
        database,
        'CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT NOT NULL);',
    )


def _insert_person(conn, person_id: int, name: str) -> None:
    conn.execute(
        'insert into people (id, name) values (?, ?)', (person_id, name)
    )


def _insert_then_raise(database: Database) -> None:
    with database.connect() as conn:
        _insert_person(conn, 1, 'gone')
        raise RuntimeError('boom')


def _nested_insert_then_outer_raise(database: Database) -> None:
    with database.connect() as outer:
        with database.connect():
            pass
        _insert_person(outer, 1, 'outer')
        raise RuntimeError('outer failed')


def _duplicate_insert(database: Database) -> None:
    with database.connect() as conn:
        _insert_person(conn, 1, 'a')
        _insert_person(conn, 1, 'b')


def _missing_table_select(database: Database) -> None:
    with database.connect() as conn:
        conn.execute('select * from no_such_table')


def _names(database: Database) -> list[str]:
    with database.connect() as conn:
        rows = conn.execute('select name from people order by id').fetchall()
    return [row[0] for row in rows]


def test_execute_fetch_with_names_and_indexes(db: Database) -> None:
    _create_people(db)
    with db.connect() as conn:
        conn.execute('insert into people (id, name) values (?, ?)', (1, 'ann'))
        row = conn.execute(
            'select id, name from people where id = ?', (1,)
        ).fetchone()
        assert row['name'] == 'ann'
        assert row[0] == 1
        assert row[1] == 'ann'


def test_fetchall_fetchmany_and_iteration(db: Database) -> None:
    _create_people(db)
    with db.connect() as conn:
        conn.executemany(
            'insert into people (id, name) values (?, ?)',
            [(1, 'a'), (2, 'b'), (3, 'c')],
        )
        cursor = conn.execute('select name from people order by id')
        assert [row[0] for row in cursor.fetchmany(2)] == ['a', 'b']
        assert [row[0] for row in cursor] == ['c']

        rows = conn.execute('select name from people order by id').fetchall()
        assert [row['name'] for row in rows] == ['a', 'b', 'c']


def test_like_literal_with_params(db: Database) -> None:
    _create_people(db)
    with db.connect() as conn:
        conn.executemany(
            'insert into people (id, name) values (?, ?)',
            [(1, 'alice'), (2, 'bob'), (3, 'al%x')],
        )
        rows = conn.execute(
            "select name from people where name like 'a%' and id > ? "
            'order by id',
            (0,),
        ).fetchall()
    assert [row[0] for row in rows] == ['alice', 'al%x']


def test_rowcount_and_lastrowid(db: Database) -> None:
    _create_people(db)
    with db.connect() as conn:
        cursor = conn.execute(
            'insert into people (id, name) values (?, ?)', (7, 'x')
        )
        assert cursor.rowcount == 1
        if db.dialect is Dialect.SQLITE:
            assert cursor.lastrowid == 7
        else:
            assert cursor.lastrowid is None


def test_executemany_inserts_all_rows(db: Database) -> None:
    _create_people(db)
    with db.connect() as conn:
        cursor = conn.executemany(
            'insert into people (id, name) values (?, ?)',
            [(1, 'a'), (2, 'b')],
        )
        assert cursor.rowcount == 2
    assert _names(db) == ['a', 'b']


def test_executescript_creates_tables(db: Database) -> None:
    _script(
        db,
        """
        CREATE TABLE first_t (id INTEGER PRIMARY KEY);
        CREATE TABLE second_t (id INTEGER PRIMARY KEY, label TEXT);
        """,
    )
    with db.connect() as conn:
        conn.execute(
            'insert into second_t (id, label) values (?, ?)', (1, 'z')
        )
        assert conn.execute('select count(*) from first_t').fetchone()[0] == 0
        assert conn.execute('select label from second_t').fetchone()[0] == 'z'


def test_commit_on_success(db: Database) -> None:
    _create_people(db)
    with db.connect() as conn:
        conn.execute(
            'insert into people (id, name) values (?, ?)', (1, 'kept')
        )
    assert _names(db) == ['kept']


def test_rollback_on_exception(db: Database) -> None:
    _create_people(db)
    with pytest.raises(RuntimeError):
        _insert_then_raise(db)
    assert _names(db) == []


def test_nested_connect_reuses_connection(db: Database) -> None:
    _create_people(db)
    with db.connect() as outer:
        with db.connect() as inner:
            assert inner is outer
            inner.execute(
                'insert into people (id, name) values (?, ?)', (1, 'inner')
            )
    assert _names(db) == ['inner']


def test_nested_inner_writes_discarded_when_outer_raises(db: Database) -> None:
    _create_people(db)
    with pytest.raises(RuntimeError):
        _nested_insert_then_outer_raise(db)
    assert _names(db) == []


def test_nested_failure_rolls_back_even_if_caught(db: Database) -> None:
    _create_people(db)
    with db.connect() as outer:
        outer.execute(
            'insert into people (id, name) values (?, ?)', (1, 'outer')
        )
        try:
            with db.connect() as inner:
                inner.execute(
                    'insert into people (id, name) values (?, ?)',
                    (2, 'inner'),
                )
                raise RuntimeError('inner failed')
        except RuntimeError:
            pass
    assert _names(db) == []


def test_missing_table_raises_undefined_table(db: Database) -> None:
    with pytest.raises(UndefinedTable):
        _missing_table_select(db)


def test_duplicate_key_raises_integrity_error(db: Database) -> None:
    _create_people(db)
    with pytest.raises(IntegrityError):
        _duplicate_insert(db)


def test_run_retries_serialization_retry_then_succeeds(db: Database) -> None:
    calls: list[int] = []

    def fn(conn):
        calls.append(1)
        if len(calls) < 3:
            raise SerializationRetry('conflict')
        return 'ok'

    assert db.run(fn) == 'ok'
    assert len(calls) == 3


def test_run_reraises_after_retries_exhausted(db: Database) -> None:
    calls: list[int] = []

    def fn(conn):
        calls.append(1)
        raise SerializationRetry('always')

    with pytest.raises(SerializationRetry):
        db.run(fn, retries=3)
    assert len(calls) == 4


def test_run_inside_connect_calls_once(db: Database) -> None:
    calls: list[int] = []

    def fn(conn):
        calls.append(1)
        raise SerializationRetry('conflict')

    with pytest.raises(SerializationRetry):
        with db.connect():
            db.run(fn)
    assert len(calls) == 1


def test_run_threads_increment_counter(db: Database) -> None:
    _script(
        db,
        'CREATE TABLE counter (id INTEGER PRIMARY KEY, n INTEGER NOT NULL);',
    )
    with db.connect() as conn:
        conn.execute('insert into counter (id, n) values (?, ?)', (1, 0))

    def increment(conn):
        conn.execute('update counter set n = n + 1 where id = ?', (1,))

    def worker() -> None:
        for _ in range(5):
            db.run(increment, lock=True)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(worker) for _ in range(8)]
        for future in futures:
            future.result()

    with db.connect() as conn:
        assert conn.execute('select n from counter').fetchone()[0] == 40


def test_postgres_small_pool_all_threads_complete(
    pg_schema: tuple[str, str],
) -> None:
    url, schema = pg_schema
    database = Database.postgres(url, search_path=schema, max_size=2)
    try:
        _script(
            database,
            'CREATE TABLE slots (id INTEGER PRIMARY KEY, n INTEGER);',
        )

        def worker(index: int) -> None:
            def write(conn):
                conn.execute(
                    'insert into slots (id, n) values (?, ?)', (index, index)
                )
                conn.execute('select n from slots where id = ?', (index,))

            database.run(write)

        with ThreadPoolExecutor(max_workers=6) as pool:
            for future in [pool.submit(worker, i) for i in range(6)]:
                future.result()

        with database.connect() as conn:
            count = conn.execute('select count(*) from slots').fetchone()[0]
        assert count == 6
    finally:
        database.close()


def test_transaction_lock_sqlite(db: Database) -> None:
    _create_people(db)
    with db.transaction(lock=True) as conn:
        conn.execute(
            'insert into people (id, name) values (?, ?)', (1, 'locked')
        )
    assert _names(db) == ['locked']


def test_healthcheck(db: Database) -> None:
    assert db.healthcheck() is True


def test_for_group_sqlite(tmp_path: Path) -> None:
    cfg = DbConfig(data_dir=tmp_path)
    database = Database.for_group(cfg, 'library')
    try:
        assert database.dialect is Dialect.SQLITE
        assert database.path == tmp_path / 'downtify_library.db'
        with database.connect() as conn:
            conn.execute('select 1')
        assert database.healthcheck() is True
    finally:
        database.close()


def test_for_group_postgres() -> None:
    url = os.environ.get(_TEST_URL_ENV)
    if not url:
        pytest.skip(f'{_TEST_URL_ENV} not set')
    cfg = DbConfig(url=url, pool_min=1, pool_max=4)
    database = Database.for_group(cfg, 'library')
    try:
        assert database.dialect is Dialect.POSTGRES
        assert database.path is None
        assert database.healthcheck() is True
    finally:
        database.close()


def test_as_database_from_path(tmp_path: Path) -> None:
    database = as_database(tmp_path / 'x.db', 'library')
    assert isinstance(database, Database)
    assert database.dialect is Dialect.SQLITE
    assert database.path == tmp_path / 'x.db'
    assert (tmp_path).is_dir()


def test_as_database_passthrough(tmp_path: Path) -> None:
    database = Database.sqlite(tmp_path / 'y.db')
    assert as_database(database, 'library') is database


def test_total_changes_counts_only_dml(db):
    with db.connect() as conn:
        conn.executescript('create table tc (a integer)')
    with db.connect() as conn:
        conn.executemany('insert into tc values (?)', [(1,), (2,), (3,)])
        conn.execute('select * from tc').fetchall()
        assert conn.total_changes == 3


def test_for_group_passes_search_path_to_postgres(monkeypatch):
    seen = {}

    def fake_postgres(cls, url, **kwargs):
        seen.update(kwargs, url=url)
        return cls(Dialect.POSTGRES, pool=None, pool_key=None)

    monkeypatch.setattr(Database, 'postgres', classmethod(fake_postgres))
    cfg = DbConfig(url='postgresql://h/db', search_path='tenant_a')
    Database.for_group(cfg, 'library')
    assert seen['url'] == 'postgresql://h/db'
    assert seen['search_path'] == 'tenant_a'
