"""LikedTracks on both backends (SQLite file, migrated PostgreSQL)."""

from __future__ import annotations

from pathlib import Path

from downtify import likes, m3u
from downtify.library_catalog import LibraryContext
from downtify.likes import (
    LIKED_PLAYLIST_NAME,
    LikedTracks,
    remap_moved,
    sync_liked_playlist,
)
from tests.db.helpers import query


def _track(base: Path, name: str, content: bytes = b'audio') -> Path:
    path = base / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _stored_paths(db) -> list[str]:
    return [
        row[0]
        for row in query(
            db, 'SELECT stored_path FROM liked_tracks ORDER BY stored_path'
        )
    ]


def test_like_unlike_and_count(backend_db):
    store = LikedTracks(backend_db)

    assert store.like('a.mp3', title='A', artist='X', duration=200) is True
    assert store.like('b.mp3') is True
    assert store.like('') is False

    assert store.count() == 2
    assert store.paths() == ['b.mp3', 'a.mp3']
    row = store.rows()[1]
    assert row['title'] == 'A'
    assert row['artist'] == 'X'
    assert row['duration'] == 200.0
    assert isinstance(row['duration'], float)
    assert isinstance(row['user_id'], int)

    assert store.unlike('a.mp3') is True
    assert store.unlike('a.mp3') is False
    assert store.count() == 1


def test_newest_like_comes_first_and_a_double_tap_keeps_its_place(
    backend_db,
):
    store = LikedTracks(backend_db)
    for name in ('a.mp3', 'b.mp3', 'c.mp3'):
        store.like(name)

    assert store.paths() == ['c.mp3', 'b.mp3', 'a.mp3']

    # Liking again is a no-op: the song must not move to the top.
    assert store.like('a.mp3') is False
    assert store.paths() == ['c.mp3', 'b.mp3', 'a.mp3']
    assert store.count() == 3


def test_backslashes_are_the_same_song(backend_db):
    store = LikedTracks(backend_db)
    store.like('Album\\a.mp3')

    assert store.paths() == ['Album/a.mp3']
    assert store.unlike('Album/a.mp3') is True


def test_likes_survive_reopening_the_store(backend_db):
    LikedTracks(backend_db).like('a.mp3', title='A')

    reopened = LikedTracks(backend_db)

    assert reopened.paths() == ['a.mp3']
    assert reopened.rows()[0]['title'] == 'A'


def test_per_user_likes_counts_and_removal(backend_db):
    store = LikedTracks(backend_db)
    store.like('a.mp3', user_id=1)
    store.like('b.mp3', user_id=1)
    store.like('a.mp3', user_id=2)

    assert store.count() == 3
    assert store.count(1) == 2
    assert store.count(2) == 1
    assert store.count_by_user() == {1: 2, 2: 1}
    assert store.paths(2) == ['a.mp3']

    # A user unliking removes only their own heart.
    assert store.unlike('a.mp3', user_id=1) is True
    assert store.unlike('a.mp3', user_id=1) is False
    assert store.paths(2) == ['a.mp3']

    # Without a user every heart for the path goes (the file is gone).
    assert store.unlike('a.mp3') is True
    assert store.count() == 1

    assert store.remove_user(1) == 1
    assert store.count_by_user() == {}


def test_clear_removes_everything_or_one_users_likes(backend_db):
    store = LikedTracks(backend_db)
    store.like('a.mp3', user_id=1)
    store.like('b.mp3', user_id=1)
    store.like('c.mp3', user_id=2)

    assert store.clear(1) == 2
    assert store.paths() == ['c.mp3']
    assert store.clear() == 1
    assert store.count() == 0


def test_reassign_legacy_gives_system_rows_to_a_user(backend_db):
    store = LikedTracks(backend_db)
    store.like('old.mp3')  # user_id 0: predates per-user likes
    store.like('mine.mp3', user_id=5)

    assert store.reassign_legacy(3) == 1
    assert store.reassign_legacy(0) == 0
    assert store.count(3) == 1
    assert store.paths(3) == ['old.mp3']
    assert store.paths(5) == ['mine.mp3']


def test_update_path_repoints_a_like_and_keeps_its_place(backend_db):
    store = LikedTracks(backend_db)
    store.like('old.mp3')
    store.like('other.mp3')

    assert store.update_path('old.mp3', 'new/old.mp3') is True
    assert store.paths() == ['other.mp3', 'new/old.mp3']
    assert store.update_path('missing.mp3', 'x.mp3') is False
    assert store.update_path('same.mp3', 'same.mp3') is False


def test_update_path_onto_a_liked_path_drops_the_duplicate(backend_db):
    store = LikedTracks(backend_db)
    store.like('old.mp3')
    store.like('new.mp3')

    assert store.update_path('old.mp3', 'new.mp3') is True
    assert store.paths() == ['new.mp3']


def test_update_path_scoped_to_one_user(backend_db):
    store = LikedTracks(backend_db)
    store.like('old.mp3', user_id=1)
    store.like('old.mp3', user_id=2)

    assert store.update_path('old.mp3', 'new.mp3', user_id=1) is True
    assert store.paths(1) == ['new.mp3']
    assert store.paths(2) == ['old.mp3']


def test_remap_moved_follows_a_moved_file(backend_db, tmp_path):
    downloads = tmp_path / 'downloads'
    original = _track(downloads, 'Song.mp3', b'same bytes')
    store = LikedTracks(backend_db)
    store.like(
        'Song.mp3',
        content_key=likes.content_key_for(original),
        title='Song',
    )
    moved = downloads / 'Sorted' / 'Song.mp3'
    moved.parent.mkdir()
    original.rename(moved)

    ctx = LibraryContext(download_dir=downloads)
    assert remap_moved(store, ctx) == 1
    assert store.paths() == ['Sorted/Song.mp3']


def test_sync_writes_and_removes_the_liked_playlist(backend_db, tmp_path):
    downloads = tmp_path / 'downloads'
    _track(downloads, 'Old Artist - Old.mp3')
    _track(downloads, 'New Artist - New.mp3')
    store = LikedTracks(backend_db)
    store.like(
        'Old Artist - Old.mp3', title='Old', artist='Old Artist', duration=200
    )
    store.like(
        'New Artist - New.mp3', title='New', artist='New Artist', duration=180
    )

    path = sync_liked_playlist(store, downloads)

    assert path == m3u.m3u_path_for(downloads, LIKED_PLAYLIST_NAME)
    assert path.read_text(encoding='utf-8').splitlines() == [
        '#EXTM3U',
        '#EXTINF:180,New Artist - New',
        '../New Artist - New.mp3',
        '#EXTINF:200,Old Artist - Old',
        '../Old Artist - Old.mp3',
    ]

    store.clear()
    assert sync_liked_playlist(store, downloads) is None
    assert not path.exists()


def test_rows_are_read_back_as_plain_values(backend_db):
    store = LikedTracks(backend_db)
    store.like('a.mp3', content_key='k', title='T', artist='A', duration=1.5)

    assert _stored_paths(backend_db) == ['a.mp3']
    row = store.rows()[0]
    assert set(row) == {
        'stored_path',
        'user_id',
        'content_key',
        'title',
        'artist',
        'duration',
        'liked_at',
    }
    assert row['content_key'] == 'k'
    assert row['duration'] == 1.5
    assert isinstance(row['liked_at'], str)
