"""ArtistReleaseStore on both backends (SQLite file, migrated PostgreSQL)."""

from __future__ import annotations

from datetime import datetime

from downtify.artist_release_store import ArtistReleaseStore
from downtify.db.config import Dialect
from downtify.db.dialect import insert_returning_id
from tests.db.helpers import execute, query


def _prepare(db) -> int:
    """Create the parent tables on SQLite (Postgres is migrated) and insert
    one monitored playlist. The SQLite seen_albums table lacks
    ``last_attempt`` so the store's ALTER path runs."""
    with db.connect() as conn:
        if conn.dialect is Dialect.SQLITE:
            conn.execute(
                'CREATE TABLE monitored_playlists (id INTEGER PRIMARY KEY,'
                ' spotify_id TEXT, name TEXT, url TEXT, created_at TEXT)'
            )
            conn.execute(
                'CREATE TABLE seen_albums (id INTEGER PRIMARY KEY'
                ' AUTOINCREMENT, playlist_id INTEGER NOT NULL,'
                ' album_id TEXT NOT NULL, name TEXT,'
                ' seen_at TEXT NOT NULL,'
                ' skipped INTEGER NOT NULL DEFAULT 0,'
                ' UNIQUE (playlist_id, album_id))'
            )
        return insert_returning_id(
            conn,
            'INSERT INTO monitored_playlists'
            ' (spotify_id, name, url, created_at) VALUES (?,?,?,?)',
            ('pl1', 'Playlist', 'https://example.test/pl1', '2020-01-01'),
        )


def _seen(db, playlist_id, album_id, skipped=0, last_attempt=None) -> None:
    execute(
        db,
        'INSERT INTO seen_albums (playlist_id, album_id, seen_at, skipped,'
        ' last_attempt) VALUES (?,?,?,?,?)',
        playlist_id,
        album_id,
        '2020-01-01',
        skipped,
        last_attempt,
    )


def test_tracks_empty_when_nothing_recorded(backend_db) -> None:
    pl = _prepare(backend_db)
    store = ArtistReleaseStore(backend_db.connect)
    assert store.tracks(pl, 'alb1') == {}


def test_record_inserts_and_upserts(backend_db) -> None:
    pl = _prepare(backend_db)
    store = ArtistReleaseStore(backend_db.connect)
    store.record(pl, 'alb1', 1, 'trk1', 'one.mp3')
    store.record(pl, 'alb1', 2, 'trk2', 'two.mp3')
    assert store.tracks(pl, 'alb1') == {
        (1, 'trk1'): 'one.mp3',
        (2, 'trk2'): 'two.mp3',
    }
    store.record(pl, 'alb1', 1, 'trk1', 'renamed.mp3')
    assert store.tracks(pl, 'alb1') == {
        (1, 'trk1'): 'renamed.mp3',
        (2, 'trk2'): 'two.mp3',
    }


def test_tracks_scoped_to_playlist_and_album(backend_db) -> None:
    pl = _prepare(backend_db)
    store = ArtistReleaseStore(backend_db.connect)
    store.record(pl, 'alb1', 1, 'trk1', 'one.mp3')
    store.record(pl, 'alb2', 1, 'trk9', 'nine.mp3')
    assert store.tracks(pl, 'alb1') == {(1, 'trk1'): 'one.mp3'}
    assert store.tracks(pl, 'alb2') == {(1, 'trk9'): 'nine.mp3'}
    assert store.tracks(pl + 1000, 'alb1') == {}


def test_next_release_none_when_no_candidates(backend_db) -> None:
    pl = _prepare(backend_db)
    store = ArtistReleaseStore(backend_db.connect)
    assert store.next_release(pl) is None
    _seen(backend_db, pl, 'skipped', skipped=1)
    assert store.next_release(pl) is None


def test_next_release_orders_null_attempts_first(backend_db) -> None:
    pl = _prepare(backend_db)
    store = ArtistReleaseStore(backend_db.connect)
    _seen(backend_db, pl, 'A')
    _seen(backend_db, pl, 'B', last_attempt='2020-01-01T00:00:00+00:00')
    _seen(backend_db, pl, 'C')
    _seen(backend_db, pl, 'D', skipped=1)

    assert store.next_release(pl) == 'A'
    store.attempt(pl, 'A')
    assert store.next_release(pl) == 'C'
    store.attempt(pl, 'C')
    assert store.next_release(pl) == 'B'
    store.attempt(pl, 'B')
    assert store.next_release(pl) in {'A', 'C'}


def test_attempt_stamps_last_attempt(backend_db) -> None:
    pl = _prepare(backend_db)
    store = ArtistReleaseStore(backend_db.connect)
    _seen(backend_db, pl, 'A')
    store.attempt(pl, 'A')
    rows = query(
        backend_db,
        'SELECT last_attempt FROM seen_albums WHERE playlist_id=?'
        ' AND album_id=?',
        pl,
        'A',
    )
    stamp = rows[0][0]
    assert stamp is not None
    datetime.fromisoformat(stamp)


def test_attempt_unknown_album_is_noop(backend_db) -> None:
    pl = _prepare(backend_db)
    store = ArtistReleaseStore(backend_db.connect)
    store.attempt(pl, 'missing')
    assert store.next_release(pl) is None


def test_constructor_is_idempotent(backend_db) -> None:
    pl = _prepare(backend_db)
    store = ArtistReleaseStore(backend_db.connect)
    store.record(pl, 'alb1', 1, 'trk1', 'one.mp3')
    again = ArtistReleaseStore(backend_db.connect)
    assert again.tracks(pl, 'alb1') == {(1, 'trk1'): 'one.mp3'}
