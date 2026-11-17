"""TrackIndex on both backends: the same results on SQLite and PostgreSQL."""

from __future__ import annotations

import sqlite3

from downtify.db.config import Dialect
from downtify.track_index import (
    TrackIndex,
    normalize_spotify_track_id,
)

TID_A = '4uLU6hMCjMI75M1A2tKUQC'
TID_B = '1x00000000000000000000'
TID_C = '2y00000000000000000000'


def _count(index: TrackIndex) -> int:
    with index.db.connect() as conn:
        return conn.execute('SELECT COUNT(*) FROM library_tracks').fetchone()[
            0
        ]


def test_normalize_song_forms() -> None:
    assert normalize_spotify_track_id({'song_id': TID_A}) == TID_A
    assert (
        normalize_spotify_track_id({
            'url': f'https://open.spotify.com/track/{TID_A}?si=x'
        })
        == TID_A
    )
    assert normalize_spotify_track_id({'song_id': 'dQw4w9WgXcQ'}) is None
    assert normalize_spotify_track_id({}) is None


def test_register_lookup_and_lookup_song(backend_db) -> None:
    index = TrackIndex(backend_db)
    assert index.lookup(TID_A) is None
    assert index.lookup('not-an-id') is None

    index.register(TID_A, r'Artist\One.mp3')
    assert index.lookup(TID_A) == 'Artist/One.mp3'
    assert index.lookup_song({'song_id': f'spotify:track:{TID_A}'}) == (
        'Artist/One.mp3'
    )
    assert index.lookup_song({'song_id': 'dQw4w9WgXcQ'}) is None

    # Invalid ids and empty names are ignored.
    index.register('bad', 'x.mp3')
    index.register(TID_B, '  ')
    assert _count(index) == 1


def test_register_song_and_register_updates(backend_db, tmp_path) -> None:
    index = TrackIndex(backend_db)
    first = tmp_path / 'first.mp3'
    second = tmp_path / 'second.mp3'
    first.write_bytes(b'same')
    second.write_bytes(b'same')

    index.register_song({'song_id': TID_A}, 'a/first.mp3', full_path=first)
    index.register_song({'song_id': 'nope'}, 'ignored.mp3')
    assert index.lookup(TID_A) == 'a/first.mp3'

    # Re-registering keeps the content key when the new one is absent.
    index.register(TID_A, 'a/second.mp3')
    rows = index.all_rows()
    assert len(rows) == 1
    assert rows[0]['filename'] == 'a/second.mp3'
    assert rows[0]['content_key'] is not None

    index.register(TID_A, 'a/third.mp3', full_path=second)
    assert index.lookup(TID_A) == 'a/third.mp3'


def test_spotify_id_for_filename(backend_db) -> None:
    index = TrackIndex(backend_db)
    index.register(TID_A, 'Dir/Track.flac')
    assert index.spotify_id_for_filename('Dir\\Track.flac') == TID_A
    assert index.spotify_id_for_filename('Dir/Track.flac') == TID_A
    assert index.spotify_id_for_filename('missing.mp3') is None
    assert index.spotify_id_for_filename('  ') is None


def test_update_filename(backend_db) -> None:
    index = TrackIndex(backend_db)
    index.register(TID_A, 'old.mp3')
    assert index.update_filename(TID_A, 'old.mp3') is False
    assert index.update_filename(TID_A, 'new\\name.mp3', content_key='k1')
    assert index.lookup(TID_A) == 'new/name.mp3'
    assert index.all_rows()[0]['content_key'] == 'k1'

    # content_key=None keeps the stored key.
    assert index.update_filename(TID_A, 'newer.mp3')
    assert index.all_rows()[0]['content_key'] == 'k1'
    assert index.update_filename('bad', 'x.mp3') is False
    assert index.update_filename(TID_B, 'x.mp3') is False


def test_set_content_key_only_fills_blanks(backend_db) -> None:
    index = TrackIndex(backend_db)
    index.register(TID_A, 'a.mp3')
    assert index.set_content_key(TID_A, 'key-1') is True
    assert index.set_content_key(TID_A, 'key-2') is False
    assert index.set_content_key(TID_A, '  ') is False
    assert index.set_content_key('bad', 'key-3') is False
    assert index.all_rows() == [
        {
            'spotify_track_id': TID_A,
            'filename': 'a.mp3',
            'content_key': 'key-1',
        }
    ]


def test_all_rows_and_list_filenames_sorted(backend_db) -> None:
    index = TrackIndex(backend_db)
    index.register(TID_B, 'Zed.mp3')
    index.register(TID_A, r'a\Beta.mp3')
    index.register(TID_C, 'alpha.mp3')

    names = index.list_filenames()
    assert names == sorted(names)
    assert names == ['Zed.mp3', 'a/Beta.mp3', 'alpha.mp3']
    rows = {r['spotify_track_id']: r for r in index.all_rows()}
    assert rows[TID_A]['filename'] == 'a/Beta.mp3'
    assert set(rows) == {TID_A, TID_B, TID_C}


def test_filenames_by_spotify_id(backend_db) -> None:
    index = TrackIndex(backend_db)
    assert index.filenames_by_spotify_id() == {}
    index.register(TID_A, r'A\One.mp3')
    index.register(TID_B, 'Two.flac')
    assert index.filenames_by_spotify_id() == {
        TID_A: 'A/One.mp3',
        TID_B: 'Two.flac',
    }


def test_remove_by_filename_and_forget(backend_db) -> None:
    index = TrackIndex(backend_db)
    index.register(TID_A, 'gone.mp3')
    index.register(TID_B, 'kept.mp3')
    index.register(TID_C, 'other.mp3')

    assert index.remove_by_filename('  ') is False
    assert index.remove_by_filename(r'gone.mp3') is True
    assert index.remove_by_filename('gone.mp3') is False
    assert index.lookup(TID_A) is None

    index.forget(TID_B)
    index.forget('bad')
    assert index.lookup(TID_B) is None
    assert index.list_filenames() == ['other.mp3']


def test_backfill_from_monitor_db(backend_db, tmp_path) -> None:
    monitor = tmp_path / 'monitor.db'
    with sqlite3.connect(str(monitor)) as src:
        src.execute(
            'CREATE TABLE downloaded_tracks '
            '(track_spotify_id TEXT, filename TEXT)'
        )
        src.executemany(
            'INSERT INTO downloaded_tracks VALUES (?, ?)',
            [(TID_A, 'm/a.mp3'), (TID_B, 'm/b.mp3'), (TID_C, '')],
        )
    index = TrackIndex(backend_db)
    index.register(TID_A, 'm/a.mp3')

    imported = index.backfill_from_monitor_db(monitor)
    if backend_db.dialect is Dialect.SQLITE:
        # Only TID_B is new; TID_A already points at the same file.
        assert imported == 1
        assert index.lookup(TID_B) == 'm/b.mp3'
        assert index.lookup(TID_C) is None
    else:
        # The SQLite monitor file is not read on PostgreSQL.
        assert imported == 0
        assert index.lookup(TID_B) is None

    assert index.backfill_from_monitor_db(tmp_path / 'absent.db') == 0
