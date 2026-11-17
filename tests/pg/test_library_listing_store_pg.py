"""LibraryListingStore on both backends: the same results on SQLite and PostgreSQL."""

from __future__ import annotations

from downtify.library_listing_store import LISTING_FORMAT, LibraryListingStore
from downtify.library_metadata_cache import META_VERSION


def _set_columns(store: LibraryListingStore, **columns) -> None:
    sets = ', '.join(f'{name} = ?' for name in columns)
    with store.db.connect() as conn:
        conn.execute(
            f'UPDATE library_listing SET {sets} WHERE cache_key = ?',
            (*columns.values(), 'k1'),
        )
        conn.commit()


def test_load_missing_key_returns_none(backend_db) -> None:
    store = LibraryListingStore(backend_db)
    assert store.load('absent') is None


def test_save_and_load_round_trip(backend_db) -> None:
    store = LibraryListingStore(backend_db)
    paths = [('a/x.mp3', '/music/a/x.mp3'), ('b/ü.flac', '/music/b/ü.flac')]
    playlists = [{'name': 'Mix', 'tracks': [1, 2]}]
    entries = [{'title': 'Roads', 'artist': 'Portishead', 'n': 3}]
    store.save('k1', 'fp-1', paths, playlists, entries)

    loaded = store.load('k1')
    assert loaded == {
        'fingerprint': 'fp-1',
        'paths': paths,
        'playlists': playlists,
        'entries': entries,
    }
    assert all(isinstance(pair, tuple) for pair in loaded['paths'])


def test_save_overwrites_same_key(backend_db) -> None:
    store = LibraryListingStore(backend_db)
    store.save('k1', 'old', [], [], [{'v': 1}])
    store.save('k1', 'new', [('p', 'q')], [], [{'v': 2}])

    loaded = store.load('k1')
    assert loaded['fingerprint'] == 'new'
    assert loaded['paths'] == [('p', 'q')]
    assert loaded['entries'] == [{'v': 2}]


def test_stale_format_or_meta_version_is_ignored(backend_db) -> None:
    store = LibraryListingStore(backend_db)
    store.save('k1', 'fp', [], [], [])

    _set_columns(store, listing_format=LISTING_FORMAT + 1)
    assert store.load('k1') is None

    _set_columns(store, listing_format=LISTING_FORMAT, meta_version=0)
    assert store.load('k1') is None

    _set_columns(store, meta_version=META_VERSION)
    assert store.load('k1') is not None


def test_corrupt_json_is_ignored(backend_db) -> None:
    store = LibraryListingStore(backend_db)
    store.save('k1', 'fp', [], [], [])

    _set_columns(store, entries_json='{"not": "a list"}')
    assert store.load('k1') is None

    _set_columns(store, entries_json='not json')
    assert store.load('k1') is None


def test_clear_removes_all_rows(backend_db) -> None:
    store = LibraryListingStore(backend_db)
    store.save('k1', 'a', [], [], [])
    store.save('k2', 'b', [], [], [])
    store.clear()

    assert store.load('k1') is None
    assert store.load('k2') is None
    store.clear()  # clearing an empty table is a no-op


def test_store_accepts_path_and_database(tmp_path, backend_db) -> None:
    by_path = LibraryListingStore(tmp_path / 'listing.db')
    by_path.save('k1', 'fp', [], [], [{'x': 1}])
    assert by_path.load('k1')['entries'] == [{'x': 1}]
    assert by_path._path == str(tmp_path / 'listing.db')

    by_db = LibraryListingStore(backend_db)
    by_db.save('k1', 'fp', [], [], [])
    assert by_db.load('k1')['fingerprint'] == 'fp'
