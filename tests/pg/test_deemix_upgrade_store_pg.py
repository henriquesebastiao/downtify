"""AudioReplacementStore on both backends: receipts, aliases and relink."""

from __future__ import annotations

from typing import Any

import pytest

from downtify.db.config import Dialect
from downtify.db.errors import IntegrityError
from downtify.deemix_upgrade_store import (
    AudioReplacementStore,
    replacement_for_id,
)
from downtify.library_sync import LibrarySync
from downtify.library_visibility import LibraryVisibility
from downtify.likes import LikedTracks
from downtify.navidrome_index import NavidromeIndex
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex
from downtify.track_owners import TrackOwners
from tests.db.helpers import execute, query


def _receipt(**overrides: Any) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        'old_file': 'old.mp3',
        'run_id': 1,
        'new_file': 'Catalog/new.mp3',
        'old_key': 'old-key',
        'new_key': 'new-key',
        'old_sha': 'a' * 8,
        'new_sha': 'b' * 8,
        'new_metadata': {
            'file': 'Catalog/new.mp3',
            'title': 'Song',
            'artist': 'Artist',
            'album': 'Album',
            'duration': 173,
        },
        'catalog': {'id': 42, 'duration': 173},
        'delete_original': 1,
    }
    receipt.update(overrides)
    return receipt


@pytest.fixture
def store(backend_db) -> AudioReplacementStore:
    # On SQLite the other stores create their own tables; on PostgreSQL
    # the migrations already did, so these constructors only verify them.
    for cls in (
        TrackIndex,
        PlaylistCatalog,
        LikedTracks,
        TrackOwners,
        LibraryVisibility,
        LibrarySync,
        NavidromeIndex,
    ):
        cls(backend_db)
    return AudioReplacementStore(backend_db)


def _seed_references(store: AudioReplacementStore) -> None:
    """Old-path references in every table the relink rewrites."""
    execute(
        store.db,
        'INSERT INTO library_tracks (spotify_track_id, filename, content_key, '
        'registered_at) VALUES (?, ?, ?, ?)',
        'spotify-1',
        'old.mp3',
        'old-key',
        'now',
    )
    execute(
        store.db,
        'INSERT INTO playlists (name, updated_at) VALUES (?, ?)',
        'manual',
        'now',
    )
    execute(
        store.db,
        'INSERT INTO playlist_tracks (playlist_name, track_spotify_id, '
        'content_key, filename, track_order) VALUES (?, ?, ?, ?, ?)',
        'manual',
        'spotify-1',
        'old-key',
        'old.mp3',
        3,
    )
    execute(
        store.db,
        'INSERT INTO navidrome_tracks (content_key, filename, '
        'navidrome_song_id, spotify_track_id, resolved_at) '
        'VALUES (?, ?, ?, ?, ?)',
        'old-key',
        'old.mp3',
        'nd-1',
        'spotify-1',
        'now',
    )
    execute(
        store.db,
        'INSERT INTO sync_tracks (track_id, path, content_key, seq) '
        'VALUES (?, ?, ?, ?)',
        'tid-1',
        'old.mp3',
        'old-key',
        1,
    )
    for user in (1, 2):
        execute(
            store.db,
            'INSERT INTO track_owners (content_key, user_id, added_at, '
            'stored_path) VALUES (?, ?, ?, ?)',
            'old-key',
            user,
            'now',
            'old.mp3',
        )
        execute(
            store.db,
            'INSERT INTO liked_tracks (stored_path, user_id, content_key, '
            'title, artist, duration, liked_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            'old.mp3',
            user,
            'old-key',
            'Old',
            'Artist',
            190,
            'now',
        )
    execute(
        store.db,
        'INSERT INTO hidden_library_items (kind, item_key, item_path, label, '
        'detail, hidden_at) VALUES (?, ?, ?, ?, ?, ?)',
        'track',
        'old-key',
        'old.mp3',
        'hidden',
        'reason',
        'now',
    )


def _rows(store: AudioReplacementStore, sql: str) -> list[tuple]:
    return [tuple(row) for row in query(store.db, sql)]


def test_constructor_accepts_path_and_database(backend_db, tmp_path) -> None:
    by_db = AudioReplacementStore(backend_db)
    assert by_db.db is backend_db
    if backend_db.dialect is Dialect.SQLITE:
        assert by_db.path == str(backend_db.path)
        by_path = AudioReplacementStore(tmp_path / 'lib.db')
        assert by_path.path == str(tmp_path / 'lib.db')
    else:
        assert by_db.path is None


def test_save_get_and_reuse_round_trip(store) -> None:
    store.save_prepared(_receipt(delete_original=True))

    got = store.get('old.mp3')
    assert got is not None
    assert got['new_file'] == 'Catalog/new.mp3'
    assert got['new_metadata']['title'] == 'Song'
    assert got['catalog'] == {'id': 42, 'duration': 173}
    assert got['delete_original'] == 1
    assert got['state'] == 'prepared'
    assert not got['detail']
    assert got['source_deleted'] == 0
    assert got['updated_at']
    assert store.get('missing.mp3') is None

    store.reuse('old.mp3', 7, False)
    again = store.get('old.mp3')
    assert again is not None
    assert again['run_id'] == 7
    assert again['delete_original'] == 0


def test_save_prepared_never_replaces_a_receipt(store) -> None:
    store.save_prepared(_receipt())

    with pytest.raises(IntegrityError):
        store.save_prepared(_receipt(new_file='Catalog/other.mp3'))
    assert store.get('old.mp3')['new_file'] == 'Catalog/new.mp3'


def test_for_run_orders_bytewise_and_filters_by_run(store) -> None:
    store.save_prepared(_receipt(old_file='a.mp3', run_id=1))
    store.save_prepared(_receipt(old_file='B.mp3', run_id=1))
    store.save_prepared(_receipt(old_file='c.mp3', run_id=2))

    assert [r['old_file'] for r in store.for_run(1)] == ['B.mp3', 'a.mp3']
    assert store.for_run(9) == []


def test_mark_summary_and_path_alias(store) -> None:
    for name in ('a.mp3', 'b.mp3', 'c.mp3', 'd.mp3'):
        store.save_prepared(_receipt(old_file=name, new_file=f'new-{name}'))

    assert store.summary(1) == {
        'prepared': 4,
        'linked': 0,
        'removed': 0,
        'retained': 0,
        'blocked': 0,
    }
    assert store.path_alias('a.mp3') is None

    store.mark('a.mp3', 'linked')
    store.mark('b.mp3', 'complete')
    store.mark('c.mp3', 'blocked', 'x' * 300)
    store.mark('d.mp3', 'complete', deleted=True)
    # A deleted flag is sticky: a later non-deleted mark keeps it.
    store.mark('d.mp3', 'complete', deleted=False)

    assert store.summary(1) == {
        'prepared': 0,
        'linked': 1,
        'removed': 1,
        'retained': 1,
        'blocked': 1,
    }
    assert store.path_alias('a.mp3') == 'new-a.mp3'
    assert store.path_alias('c.mp3') is None
    detail = store.get('c.mp3')['detail']
    assert len(detail) == 200
    assert store.get('d.mp3')['source_deleted'] == 1


def test_relink_rewrites_every_reference_consistently(store) -> None:
    store.save_prepared(_receipt())
    _seed_references(store)

    store.relink(store.for_run(1))
    store.assert_relinked(store.for_run(1))

    assert _rows(
        store,
        'SELECT spotify_track_id, filename, content_key FROM library_tracks',
    ) == [('spotify-1', 'Catalog/new.mp3', 'new-key')]
    assert _rows(
        store,
        'SELECT playlist_name, filename, content_key, track_order '
        'FROM playlist_tracks',
    ) == [('manual', 'Catalog/new.mp3', 'new-key', 3)]
    assert _rows(store, 'SELECT content_key FROM navidrome_tracks') == []
    assert _rows(
        store,
        'SELECT user_id, stored_path, content_key, title, artist, duration '
        'FROM liked_tracks ORDER BY user_id',
    ) == [
        (1, 'Catalog/new.mp3', 'new-key', 'Song', 'Artist', 173.0),
        (2, 'Catalog/new.mp3', 'new-key', 'Song', 'Artist', 173.0),
    ]
    assert _rows(
        store,
        'SELECT user_id, content_key, stored_path FROM track_owners '
        'ORDER BY user_id',
    ) == [(1, 'new-key', 'Catalog/new.mp3'), (2, 'new-key', 'Catalog/new.mp3')]
    assert _rows(
        store,
        'SELECT kind, item_key, item_path, label FROM hidden_library_items',
    ) == [('track', 'new-key', 'Catalog/new.mp3', 'hidden')]
    assert _rows(
        store, 'SELECT track_id, old_file FROM library_audio_sync_aliases'
    ) == [('tid-1', 'old.mp3')]
    assert store.get('old.mp3')['state'] == 'linked'
    assert store.path_alias('old.mp3') == 'Catalog/new.mp3'

    with store.connect() as conn:
        resolved = replacement_for_id(conn, 'tid-1')
    assert resolved is not None
    assert resolved['title'] == 'Song'


def test_relink_twice_is_harmless(store) -> None:
    store.save_prepared(_receipt())
    _seed_references(store)

    store.relink(store.for_run(1))
    store.relink(store.for_run(1))

    assert _rows(
        store, 'SELECT user_id FROM track_owners ORDER BY user_id'
    ) == [
        (1,),
        (2,),
    ]
    assert _rows(
        store, 'SELECT user_id FROM liked_tracks ORDER BY user_id'
    ) == [
        (1,),
        (2,),
    ]


def test_relink_merges_existing_new_owner_and_like(store) -> None:
    store.save_prepared(_receipt())
    _seed_references(store)
    # User 1 already owns and likes the new recording.
    execute(
        store.db,
        'INSERT INTO track_owners (content_key, user_id, added_at, '
        'stored_path) VALUES (?, ?, ?, ?)',
        'new-key',
        1,
        'earlier',
        'Catalog/new.mp3',
    )
    execute(
        store.db,
        'INSERT INTO liked_tracks (stored_path, user_id, content_key, '
        'title, artist, duration, liked_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
        'Catalog/new.mp3',
        1,
        'new-key',
        'Song',
        'Artist',
        173,
        'zzz-later',
    )

    store.relink(store.for_run(1))

    assert _rows(
        store,
        'SELECT user_id, stored_path FROM track_owners ORDER BY user_id',
    ) == [(1, 'Catalog/new.mp3'), (2, 'Catalog/new.mp3')]
    likes = _rows(
        store,
        'SELECT user_id, liked_at FROM liked_tracks ORDER BY user_id',
    )
    # The earlier like time wins over the later one.
    assert likes == [(1, 'now'), (2, 'now')]


def test_relink_without_receipts_is_a_noop(store) -> None:
    _seed_references(store)
    store.relink([])
    assert _rows(store, 'SELECT filename FROM library_tracks') == [
        ('old.mp3',)
    ]


def test_failed_relink_leaves_every_reference_unchanged(store) -> None:
    _seed_references(store)
    bad = _receipt(new_file=None)

    with pytest.raises(IntegrityError):
        store.relink([bad])

    assert _rows(store, 'SELECT filename FROM library_tracks') == [
        ('old.mp3',)
    ]
    assert _rows(
        store, 'SELECT user_id FROM track_owners ORDER BY user_id'
    ) == [
        (1,),
        (2,),
    ]


def test_assert_relinked_blocks_remaining_old_references(store) -> None:
    store.save_prepared(_receipt())
    _seed_references(store)

    with pytest.raises(ValueError, match='cleanup blocked'):
        store.assert_relinked(store.for_run(1))


def test_replacement_for_id_is_none_until_relinked(store) -> None:
    store.save_prepared(_receipt())
    with store.connect() as conn:
        assert replacement_for_id(conn, 'tid-1') is None
    _seed_references(store)
    store.relink(store.for_run(1))
    with store.connect() as conn:
        found = replacement_for_id(conn, 'tid-1')
        assert found is not None
        assert found['file'] == 'Catalog/new.mp3'
        assert replacement_for_id(conn, 'unknown') is None
