"""PlaylistBatchStore on both backends (SQLite file, migrated PostgreSQL)."""

from __future__ import annotations

import pytest

from downtify.playlist_batches import PlaylistBatchStore, ensure_batch_records
from tests.db.helpers import query

SID = 'playlist12345678901234567890'
URL = f'https://open.spotify.com/playlist/{SID}'


def _owner(db, batch_id):
    return query(
        db, 'SELECT user_id FROM playlist_batches WHERE id = ?', batch_id
    )[0][0]


def _ids(db, sql, *params):
    return [row[0] for row in query(db, sql, *params)]


def test_start_update_finish_and_mark_complete(backend_db):
    store = PlaylistBatchStore(backend_db)
    first = store.start_batch(SID, '  Mix  ', URL, 5, user_id=7)
    second = store.start_batch(SID, '', URL, -3)

    assert isinstance(first, int)
    assert isinstance(second, int)
    assert second > first
    row = store.get_batch(first)
    assert row['playlist_name'] == 'Mix'
    assert row['expected_count'] == 5
    assert row['status'] == 'in_progress'
    assert row['finished_at'] is None
    # Blank name falls back to the playlist id; negatives clamp to 0.
    assert store.get_batch(second)['playlist_name'] == SID
    assert store.get_batch(second)['expected_count'] == 0

    store.update_batch_name(first, '  Renamed  ')
    store.update_batch_name(first, '   ')
    assert store.get_batch(first)['playlist_name'] == 'Renamed'

    store.finish_batch(first, 3, -2, status=' INCOMPLETE ')
    row = store.get_batch(first)
    assert row['status'] == 'incomplete'
    assert row['succeeded_count'] == 3
    assert row['failed_count'] == 0
    assert row['finished_at'] is not None

    store.mark_complete(first)
    row = store.get_batch(first)
    assert row['status'] == 'complete'
    finished = row['finished_at']
    store.mark_complete(first)
    assert store.get_batch(first)['finished_at'] == finished

    assert store.get_batch(999999) is None


def test_invalid_input_is_rejected(backend_db):
    store = PlaylistBatchStore(backend_db)
    with pytest.raises(ValueError, match='required'):
        store.start_batch('', 'x', URL, 1)
    with pytest.raises(ValueError, match='required'):
        store.start_batch(SID, 'x', '  ', 1)
    batch_id = store.start_batch(SID, 'x', URL, 1)
    with pytest.raises(ValueError, match='invalid batch status'):
        store.finish_batch(batch_id, 1, 0, status='running')


def test_list_open_and_latest_per_playlist(backend_db):
    store = PlaylistBatchStore(backend_db)
    old = store.start_batch(SID, 'A', URL, 2, user_id=1)
    store.finish_batch(old, 2, 0, status='complete')
    new = store.start_batch(SID, 'A', URL, 2, user_id=1)
    other = store.start_batch('other', 'B', URL, 1, user_id=2)
    store.finish_batch(other, 0, 1, status='incomplete')

    open_ids = sorted(b['id'] for b in store.list_open_batches())
    assert open_ids == sorted([new, other])

    latest = {b['id'] for b in store.list_latest_batches()}
    assert latest == {new, other}

    only_user_two = store.list_latest_batches(user_id=2)
    assert [b['id'] for b in only_user_two] == [other]
    assert only_user_two[0]['status'] == 'incomplete'
    assert only_user_two[0]['failed_count'] == 1
    assert store.list_open_batches(user_id=1)[0]['id'] == new
    assert store.list_open_batches(user_id=99) == []


def test_reassign_legacy_only_touches_user_zero(backend_db):
    store = PlaylistBatchStore(backend_db)
    legacy = store.start_batch(SID, 'L', URL, 1)
    owned = store.start_batch('other', 'O', URL, 1, user_id=5)

    assert store.reassign_legacy(0) == 0
    assert store.reassign_legacy(9) == 1
    assert _owner(backend_db, legacy) == 9
    assert _owner(backend_db, owned) == 5
    assert store.reassign_legacy(9) == 0


def test_delete_for_spotify_playlist(backend_db):
    store = PlaylistBatchStore(backend_db)
    store.start_batch(SID, 'A', URL, 1, user_id=1)
    store.start_batch(SID, 'A', URL, 1, user_id=2)
    keep = store.start_batch('other', 'B', URL, 1, user_id=1)

    assert store.delete_for_spotify_playlist('  ') == 0
    assert store.delete_for_spotify_playlist(SID, user_id=1) == 1
    assert store.delete_for_spotify_playlist(SID) == 1
    assert store.delete_for_spotify_playlist(SID) == 0
    assert _ids(backend_db, 'SELECT id FROM playlist_batches') == [keep]


def test_ensure_batch_records_creates_missing_rows(backend_db):
    store = PlaylistBatchStore(backend_db)
    existing = store.start_batch(SID, 'Mine', URL, 4)
    playlists = [
        {'spotify_id': SID, 'name': 'Skip me', 'track_count': 9},
        {'spotify_id': 'new1', 'name': '', 'track_count': 0},
        {'spotify_id': '', 'name': 'no id'},
        {
            'spotify_id': 'new2',
            'name': 'Two',
            'url': 'https://x/2',
            'expected': 3,
        },
    ]

    assert ensure_batch_records(store, playlists) == 2
    assert ensure_batch_records(store, playlists) == 0

    latest = {b['spotify_playlist_id']: b for b in store.list_latest_batches()}
    assert latest[SID]['id'] == existing
    assert latest['new1']['playlist_name'] == 'new1'
    assert latest['new1']['expected_count'] == 1
    assert latest['new1']['status'] == 'incomplete'
    assert latest['new1']['playlist_url'].endswith('/new1')
    assert latest['new2']['expected_count'] == 3
    assert latest['new2']['playlist_url'] == 'https://x/2'
