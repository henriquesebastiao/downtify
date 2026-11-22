from __future__ import annotations

import os
import pickle
import sqlite3
from dataclasses import dataclass

import psycopg
import pytest

from downtify.db.rows import Row, pg_row_factory


@dataclass
class FakeColumn:
    name: str


class FakeCursor:
    def __init__(self, names: list[str] | None) -> None:
        if names is None:
            self.description = None
        else:
            self.description = [FakeColumn(n) for n in names]


def make(keys=('Id', 'Name', 'name'), values=(1, 'x', 'y')) -> Row:
    return Row(keys, values)


def test_positive_and_negative_index() -> None:
    row = make()
    assert row[0] == 1
    assert row[-1] == 'y'


def test_slice_returns_plain_tuple() -> None:
    row = make()
    assert row[0:2] == (1, 'x')
    assert type(row[0:2]) is tuple


def test_name_lookup_is_case_insensitive_first_match() -> None:
    row = make()
    assert row['id'] == 1
    assert row['ID'] == 1
    assert row['NAME'] == 'x'


def test_unknown_name_raises_index_error() -> None:
    with pytest.raises(IndexError, match='No item with that key'):
        make()['missing']


def test_keys_preserves_original_case() -> None:
    assert make().keys() == ['Id', 'Name', 'name']


def test_len_and_iteration_yield_values() -> None:
    row = make()
    assert len(row) == 3
    assert list(row) == [1, 'x', 'y']


def test_equality_and_hash_match_plain_tuple() -> None:
    row = make()
    assert row == (1, 'x', 'y')
    assert hash(row) == hash((1, 'x', 'y'))
    assert make(('a',), (1,)) == make(('b',), (1,))


def test_dict_conversion() -> None:
    assert dict(make(('a', 'b'), (1, 2))) == {'a': 1, 'b': 2}


def test_get_with_default() -> None:
    row = make()
    assert row.get('name') == 'x'
    assert row.get('nope') is None
    assert row.get('nope', 5) == 5
    assert row.get(0) == 1


def test_key_tuples_share_index_cache() -> None:
    a = make(('a', 'b'), (1, 2))
    b = make(('a', 'b'), (3, 4))
    assert a._index is b._index


def test_pickle_round_trip() -> None:
    row = pickle.loads(pickle.dumps(make()))
    assert isinstance(row, Row)
    assert row['name'] == 'x'
    assert row.keys() == ['Id', 'Name', 'name']


def test_pg_row_factory_builds_rows() -> None:
    cursor = FakeCursor(['a', 'B'])
    make_row = pg_row_factory(cursor)
    row = make_row((1, 'x'))
    assert isinstance(row, Row)
    assert row['b'] == 'x'
    assert row[0] == 1
    assert row.keys() == ['a', 'B']


def test_pg_row_factory_without_description() -> None:
    row = pg_row_factory(FakeCursor(None))(())
    assert len(row) == 0
    assert row.keys() == []


def test_matches_sqlite3_row() -> None:
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    try:
        sq = conn.execute("select 1 as Alpha, 'x' as beta").fetchone()
    finally:
        conn.close()
    ours = Row(['Alpha', 'beta'], (1, 'x'))

    assert ours[0] == sq[0] == 1
    assert ours[-1] == sq[-1] == 'x'
    assert ours['alpha'] == sq['alpha'] == 1
    assert ours['BETA'] == sq['BETA'] == 'x'
    assert ours.keys() == sq.keys() == ['Alpha', 'beta']
    assert len(ours) == len(sq) == 2
    assert list(ours) == list(sq) == [1, 'x']


@pytest.mark.skipif(
    not os.environ.get('TEST_DATABASE_URL'),
    reason='TEST_DATABASE_URL not set',
)
def test_postgres_row_factory() -> None:
    url = os.environ['TEST_DATABASE_URL']
    with psycopg.connect(url, row_factory=pg_row_factory) as conn:
        row = conn.execute("select 1 as a, 'x' as b").fetchone()
    assert row['b'] == 'x'
    assert row[0] == 1
