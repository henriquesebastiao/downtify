"""TrackOwners on both backends: the same results on SQLite and PostgreSQL."""

from __future__ import annotations

from downtify.db.config import Dialect
from downtify.track_owners import TrackOwners
from tests.db.helpers import query


def test_constructor_accepts_path_and_database(backend_db, tmp_path) -> None:
    by_db = TrackOwners(backend_db)
    assert by_db.db is backend_db
    assert by_db.is_empty() is True
    if backend_db.dialect is Dialect.SQLITE:
        assert by_db._path == str(backend_db.path)
        by_path = TrackOwners(tmp_path / 'lib.db')
        assert by_path.db.dialect is Dialect.SQLITE
        assert by_path._path == str(tmp_path / 'lib.db')
    else:
        assert by_db._path is None


def test_add_records_new_owners_and_ignores_repeats(backend_db) -> None:
    owners = TrackOwners(backend_db)

    assert owners.add('key-a', 1, 'Artist/a.mp3') is True
    assert owners.add('key-a', 1, 'Artist/a.mp3') is False
    assert owners.add('key-a', 2) is True
    assert owners.owners('key-a') == [1, 2]
    assert owners.count('key-a') == 2


def test_add_ignores_empty_key_or_user(backend_db) -> None:
    owners = TrackOwners(backend_db)

    assert owners.add('', 1) is False
    assert owners.add('   ', 1) is False
    assert owners.add('key-b', 0) is False
    assert owners.is_empty() is True


def test_add_normalises_key_and_path(backend_db) -> None:
    owners = TrackOwners(backend_db)

    assert owners.add('  key-c  ', 3, '  A\\B\\c.mp3  ') is True
    rows = query(
        backend_db,
        'SELECT content_key, stored_path FROM track_owners',
    )
    assert [tuple(r) for r in rows] == [('key-c', 'A/B/c.mp3')]


def test_add_heals_stale_rows_at_the_same_path(backend_db) -> None:
    owners = TrackOwners(backend_db)
    owners.add('old-key', 1, 'Music/song.mp3')
    owners.add('old-key', 2, 'Music/song.mp3')

    owners.add('new-key', 1, 'Music/song.mp3')

    assert owners.count('old-key') == 0
    # Healed rows keep their original added_at, so user 2 sorts first.
    assert owners.owners('new-key') == [2, 1]


def test_add_heal_drops_exact_duplicates(backend_db) -> None:
    owners = TrackOwners(backend_db)
    owners.add('old-key', 1, 'Music/dup.mp3')
    owners.add('new-key', 1)
    owners.add('old-key', 2, 'Music/dup.mp3')

    owners.add('new-key', 2, 'Music/dup.mp3')

    assert owners.count('old-key') == 0
    assert owners.owners('new-key') == [1, 2]
    assert owners.count('new-key') == 2


def test_rekey_moves_rows_and_path(backend_db) -> None:
    owners = TrackOwners(backend_db)
    owners.add('k1', 1, 'a.mp3')
    owners.add('k1', 2, 'a.mp3')

    assert owners.rekey('k1', 'k2', 'b.mp3') == 2
    assert owners.count('k1') == 0
    assert owners.owners('k2') == [1, 2]
    rows = query(
        backend_db,
        'SELECT DISTINCT stored_path FROM track_owners WHERE content_key=?',
        'k2',
    )
    assert [tuple(r) for r in rows] == [('b.mp3',)]


def test_rekey_without_path_keeps_stored_path(backend_db) -> None:
    owners = TrackOwners(backend_db)
    owners.add('k1', 1, 'keep.mp3')

    assert owners.rekey('k1', 'k2') == 1
    rows = query(
        backend_db,
        'SELECT stored_path FROM track_owners WHERE content_key=?',
        'k2',
    )
    assert [tuple(r) for r in rows] == [('keep.mp3',)]


def test_rekey_drops_duplicates_and_ignores_no_op(backend_db) -> None:
    owners = TrackOwners(backend_db)
    owners.add('k1', 1)
    owners.add('k2', 1)
    owners.add('k1', 2)

    assert owners.rekey('k1', 'k2') == 1
    assert owners.count('k1') == 0
    assert owners.owners('k2') == [1, 2]
    assert owners.rekey('k2', 'k2') == 0
    assert owners.rekey('', 'k2') == 0
    assert owners.rekey('k2', '') == 0


def test_remove_returns_remaining_owner_count(backend_db) -> None:
    owners = TrackOwners(backend_db)
    owners.add('k', 1)
    owners.add('k', 2)

    assert owners.remove('k', 1) == 1
    assert owners.remove('k', 2) == 0
    assert owners.remove('k', 0) == 0
    assert owners.remove('', 5) == 0


def test_drop_file_forgets_every_owner(backend_db) -> None:
    owners = TrackOwners(backend_db)
    owners.add('gone', 1)
    owners.add('gone', 2)
    owners.add('kept', 1)

    owners.drop_file('gone')
    owners.drop_file('')

    assert owners.count('gone') == 0
    assert owners.owners('kept') == [1]


def test_is_empty_flips_after_first_add(backend_db) -> None:
    owners = TrackOwners(backend_db)
    assert owners.is_empty() is True
    owners.add('k', 1)
    assert owners.is_empty() is False


def test_owners_are_listed_oldest_first(backend_db) -> None:
    owners = TrackOwners(backend_db)
    for user in (5, 3, 9):
        owners.add('k', user)

    assert owners.owners('k') == [5, 3, 9]
    assert owners.owners('missing') == []


def test_owned_keys_and_count_by_user(backend_db) -> None:
    owners = TrackOwners(backend_db)
    owners.add('a', 1)
    owners.add('b', 1)
    owners.add('b', 2)

    assert owners.owned_keys(1) == {'a', 'b'}
    assert owners.owned_keys(2) == {'b'}
    assert owners.owned_keys(3) == set()
    assert owners.count_by_user() == {1: 2, 2: 1}


def test_remove_user_drops_all_their_rows(backend_db) -> None:
    owners = TrackOwners(backend_db)
    owners.add('a', 1)
    owners.add('b', 1)
    owners.add('b', 2)

    assert owners.remove_user(1) == 2
    assert owners.remove_user(1) == 0
    assert owners.count_by_user() == {2: 1}


def test_owned_subset_chunks_and_filters(backend_db) -> None:
    owners = TrackOwners(backend_db)
    owners.add('x', 1)
    owners.add('y', 1)
    owners.add('z', 2)
    many = [f'pad-{i}' for i in range(1200)] + ['x', 'z', '']

    assert owners.owned_subset(['x', 'y', 'z'], 1) == {'x', 'y'}
    assert owners.owned_subset(many, 1) == {'x'}
    assert owners.owned_subset([], 1) == set()
    assert owners.owned_subset(['x'], 0) == set()
