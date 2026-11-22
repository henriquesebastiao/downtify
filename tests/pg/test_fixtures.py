from __future__ import annotations

from tests.db.helpers import execute, query


def test_query_execute_round_trip(backend_db) -> None:
    execute(
        backend_db,
        'create table fx_scratch (id integer primary key, name text not null)',
    )
    assert (
        execute(
            backend_db,
            'insert into fx_scratch (id, name) values (?, ?)',
            1,
            'ann',
        )
        == 1
    )
    execute(
        backend_db,
        'insert into fx_scratch (id, name) values (?, ?)',
        2,
        'bob',
    )
    rows = query(
        backend_db,
        'select id, name from fx_scratch where id >= ? order by id',
        1,
    )
    assert [tuple(row) for row in rows] == [(1, 'ann'), (2, 'bob')]

    assert (
        execute(
            backend_db,
            'update fx_scratch set name = ? where id = ?',
            'cy',
            2,
        )
        == 1
    )
    rows = query(backend_db, 'select name from fx_scratch where id = ?', 2)
    assert [tuple(row) for row in rows] == [('cy',)]


def test_pg_db_is_migrated_and_empty(pg_db) -> None:
    assert query(pg_db, 'select count(*) from users')[0][0] == 0
    exists = query(pg_db, "select to_regclass('library_tracks') is not null")
    assert exists[0][0] is True
