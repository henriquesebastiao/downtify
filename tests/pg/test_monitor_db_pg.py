"""PlaylistMonitorDB on both backends (SQLite file, migrated PostgreSQL)."""

from __future__ import annotations

from downtify.db.config import Dialect
from downtify.db.dialect import table_exists
from downtify.monitor import (
    ALL_RELEASE_TYPES,
    KIND_ARTIST,
    PlaylistMonitorDB,
    delete_user_watches,
    repoint_downloaded_file,
)
from downtify.watch_history import OUTCOME_DOWNLOADED
from tests.db.helpers import query

SPOTIFY_ID = 'sp-road-trip'
URL = 'https://open.spotify.com/playlist/sp-road-trip'


def _add(db: PlaylistMonitorDB, spotify_id: str = SPOTIFY_ID, **kwargs):
    kwargs.setdefault('name', 'Road Trip')
    kwargs.setdefault('url', URL)
    return db.add_playlist(spotify_id, **kwargs)


def test_constructing_builds_tables_and_sub_stores(backend_db):
    db = PlaylistMonitorDB(backend_db)

    assert db.db is backend_db
    if backend_db.dialect is Dialect.POSTGRES:
        assert db._path is None
    else:
        assert db._path == str(backend_db.path)
    with db._connect() as conn:
        for table in (
            'monitored_playlists',
            'downloaded_tracks',
            'seen_albums',
            'artist_release_tracks',
            'download_policy',
            'watch_events',
            'watch_failures',
        ):
            assert table_exists(conn, table), table

    # The three sub-stores share the same connection and schema.
    assert db.releases.tracks(1, 'missing') == {}
    assert db.download_policy is not None
    assert db.history.events() == []


def test_constructing_from_a_path_keeps_sqlite_path(tmp_path):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')

    assert db._path == str(tmp_path / 'monitor.db')
    assert db.db.dialect is Dialect.SQLITE


def test_add_get_and_list_playlists(backend_db):
    db = PlaylistMonitorDB(backend_db)

    plain = _add(db, interval_minutes=30, user_id=7)
    assert plain.id > 0
    assert plain.spotify_id == SPOTIFY_ID
    assert plain.enabled is True
    assert plain.interval_minutes == 30
    assert plain.user_id == 7
    assert plain.kind == 'playlist'
    assert plain.release_types == ALL_RELEASE_TYPES
    assert plain.new_only is False
    assert plain.baseline_pending is False
    assert not plain.deezer_id

    artist = _add(
        db,
        spotify_id='chan-1',
        name='Artist',
        kind=KIND_ARTIST,
        release_types='album',
        new_only=True,
        user_id=8,
    )
    assert artist.kind == KIND_ARTIST
    assert artist.release_types == 'album'
    assert artist.new_only is True
    assert artist.baseline_pending is True

    assert db.get_playlist(plain.id) == plain
    assert db.get_playlist(999_999) is None
    assert db.get_by_spotify_id(SPOTIFY_ID) == plain
    assert db.get_by_spotify_id(SPOTIFY_ID, user_id=7) == plain
    assert db.get_by_spotify_id(SPOTIFY_ID, user_id=8) is None
    assert db.get_by_spotify_id('unknown') is None

    assert {p.id for p in db.list_playlists()} == {plain.id, artist.id}
    assert [p.id for p in db.list_playlists(user_id=7)] == [plain.id]
    assert db.list_playlists(user_id=99) == []

    data = plain.to_dict()
    assert data['release_types'] == ['album', 'single', 'ep']
    assert 'baseline_pending' not in data


def test_update_playlist_fields_and_edge_cases(backend_db):
    db = PlaylistMonitorDB(backend_db)
    watch = _add(db)

    updated = db.update_playlist(
        watch.id,
        enabled=False,
        name='Renamed',
        url='https://example.test/new',
        interval_minutes=5,
        last_checked='2026-01-02T03:04:05+00:00',
        last_track_count=3,
        release_types='album,ep',
        new_only=True,
        baseline_pending=True,
        deezer_id='dz-1',
        not_a_column='ignored',
    )
    assert updated.enabled is False
    assert updated.name == 'Renamed'
    assert updated.url == 'https://example.test/new'
    assert updated.interval_minutes == 5
    assert updated.last_checked == '2026-01-02T03:04:05+00:00'
    assert updated.last_track_count == 3
    assert updated.release_types == 'album,ep'
    assert updated.new_only is True
    assert updated.baseline_pending is True
    assert updated.deezer_id == 'dz-1'

    # Only unknown keys: nothing to write, the current row comes back.
    assert db.update_playlist(watch.id, bogus=1) == updated
    assert db.update_playlist(999_999, name='x') is None


def test_reassign_legacy_watches(backend_db):
    db = PlaylistMonitorDB(backend_db)
    legacy = _add(db, user_id=0)
    owned = _add(db, spotify_id='other', user_id=3)

    assert db.reassign_legacy(0) == 0
    assert db.reassign_legacy(5) == 1
    assert db.get_playlist(legacy.id).user_id == 5
    assert db.get_playlist(owned.id).user_id == 3


def test_set_new_only_baseline_and_forget(backend_db):
    db = PlaylistMonitorDB(backend_db)
    watch = _add(db, kind=KIND_ARTIST, spotify_id='chan-2')

    on = db.set_new_only(watch.id, True)
    assert on.new_only is True
    assert on.baseline_pending is True
    # Already on: unchanged.
    assert db.set_new_only(watch.id, True) == on

    db.mark_albums_skipped(watch.id, [{'album_id': 'old', 'name': 'Old'}])
    off = db.set_new_only(watch.id, False)
    assert off.new_only is False
    assert off.baseline_pending is False
    assert db.get_seen_album_ids(watch.id) == set()

    assert db.set_new_only(999_999, True) is None


def test_retarget_resets_watch_history(backend_db):
    db = PlaylistMonitorDB(backend_db)
    watch = _add(db, new_only=True)
    db.mark_track_downloaded(watch.id, 'tr-1', 'a.mp3')
    db.mark_album_seen(watch.id, 'al-1', 'Album')
    db.releases.record(watch.id, 'al-1', 0, 'tr-1', 'a.mp3')

    moved = db.retarget_playlist(watch.id, 'sp-new', 'New', 'https://n.test')
    assert moved.spotify_id == 'sp-new'
    assert moved.name == 'New'
    assert moved.last_checked is None
    assert moved.last_track_count == 0
    assert moved.baseline_pending is True
    assert db.get_track_filenames(watch.id) == {}
    assert db.get_seen_album_ids(watch.id) == set()
    assert db.releases.tracks(watch.id, 'al-1') == {}

    assert db.retarget_playlist(999_999, 'x', 'x', 'x') is None


def test_delete_playlist_cascades_to_tracks_and_albums(backend_db):
    db = PlaylistMonitorDB(backend_db)
    watch = _add(db)
    other = _add(db, spotify_id='keep')
    db.mark_track_downloaded(watch.id, 'tr-1', 'a.mp3')
    db.mark_album_seen(watch.id, 'al-1', 'Album')
    db.releases.record(watch.id, 'al-1', 0, 'tr-1', 'a.mp3')
    db.mark_track_downloaded(other.id, 'tr-2', 'b.mp3')

    assert db.delete_playlist(watch.id) is True
    assert db.delete_playlist(watch.id) is False
    assert db.get_playlist(watch.id) is None

    assert (
        query(
            backend_db,
            'SELECT COUNT(*) FROM downloaded_tracks WHERE playlist_id = ?',
            watch.id,
        )[0][0]
        == 0
    )
    assert (
        query(
            backend_db,
            'SELECT COUNT(*) FROM seen_albums WHERE playlist_id = ?',
            watch.id,
        )[0][0]
        == 0
    )
    assert (
        query(
            backend_db,
            'SELECT COUNT(*) FROM artist_release_tracks WHERE playlist_id = ?',
            watch.id,
        )[0][0]
        == 0
    )
    # The other watch keeps its rows.
    assert db.get_track_filenames(other.id) == {'tr-2': 'b.mp3'}


def test_delete_user_watches_removes_only_that_owner(backend_db):
    db = PlaylistMonitorDB(backend_db)
    _add(db, spotify_id='a', user_id=4)
    _add(db, spotify_id='b', user_id=4)
    keep = _add(db, spotify_id='c', user_id=5)

    delete_user_watches(db, 4)

    assert [p.id for p in db.list_playlists()] == [keep.id]


def test_mark_track_downloaded_upserts_and_logs_history(backend_db):
    db = PlaylistMonitorDB(backend_db)
    watch = _add(db)

    db.mark_track_downloaded(watch.id, 'tr-1', 'a.mp3')
    assert db.get_track_filenames(watch.id) == {'tr-1': 'a.mp3'}

    # Same track again: one row, the new filename.
    db.mark_track_downloaded(
        watch.id,
        'tr-1',
        'b.mp3',
        outcome=OUTCOME_DOWNLOADED,
        provider='youtube',
        initial=True,
    )
    assert db.get_track_filenames(watch.id) == {'tr-1': 'b.mp3'}
    events = db.history.events(playlist_id=watch.id)
    assert [e['outcome'] for e in events] == [OUTCOME_DOWNLOADED]
    assert events[0]['provider'] == 'youtube'
    assert events[0]['initial'] == 1


def test_track_lookups_and_filenames(backend_db):
    db = PlaylistMonitorDB(backend_db)
    watch = _add(db)
    db.mark_track_downloaded(watch.id, 'tr-1', 'a.mp3')
    db.mark_track_downloaded(watch.id, 'tr-2', None)

    assert db.playlists_for_track('tr-1') == {'Road Trip'}
    assert db.playlists_for_track('  ') == set()
    assert db.playlists_for_track('nope') == set()

    rows = db.list_all_downloaded_tracks()
    # Rows without a filename are left out.
    assert [
        (r['playlist_id'], r['track_spotify_id'], r['filename']) for r in rows
    ] == [(watch.id, 'tr-1', 'a.mp3')]

    assert db.update_filename_for_spotify('', 'x.mp3') == set()
    assert db.update_filename_for_spotify('tr-1', '') == set()
    renamed = db.update_filename_for_spotify('tr-1', 'dir\\c.mp3')
    assert renamed == {'Road Trip'}
    assert db.get_track_filenames(watch.id)['tr-1'] == 'dir/c.mp3'


def test_repoint_downloaded_file_moves_records(backend_db):
    db = PlaylistMonitorDB(backend_db)
    watch = _add(db)
    db.mark_track_downloaded(watch.id, 'tr-1', 'old.mp3')

    assert repoint_downloaded_file(db, 'old.mp3', 'new.mp3') == 1
    assert db.get_track_filenames(watch.id) == {'tr-1': 'new.mp3'}
    assert repoint_downloaded_file(db, 'same.mp3', 'same.mp3') == 0
    assert repoint_downloaded_file(db, '', 'new.mp3') == 0


def test_remove_downloaded_tracks(backend_db):
    db = PlaylistMonitorDB(backend_db)
    watch = _add(db)
    db.mark_track_downloaded(watch.id, 'tr-1', 'a.mp3')
    db.mark_track_downloaded(watch.id, 'tr-2', 'b.mp3')

    assert db.remove_downloaded_tracks([]) == 0
    assert db.remove_downloaded_tracks([(watch.id, 'tr-1')]) == 1
    assert db.get_track_filenames(watch.id) == {'tr-2': 'b.mp3'}


def test_seen_albums_skip_and_forget(backend_db):
    db = PlaylistMonitorDB(backend_db)
    watch = _add(db, kind=KIND_ARTIST, spotify_id='chan-3')

    db.mark_album_seen(watch.id, 'al-1', 'First')
    db.mark_album_seen(watch.id, 'al-1', 'First (remaster)')
    assert db.get_seen_album_ids(watch.id) == {'al-1'}
    assert db.releases.next_release(watch.id) == 'al-1'

    added = db.mark_albums_skipped(
        watch.id,
        [
            {'album_id': 'al-1', 'name': 'Already here'},
            {'album_id': 'al-2', 'name': 'Second'},
            {'album_id': None, 'name': 'No id'},
        ],
    )
    assert added == 1
    assert db.get_seen_album_ids(watch.id) == {'al-1', 'al-2'}
    # Skipped releases are not picked for a historical recheck.
    assert db.releases.next_release(watch.id) == 'al-1'

    assert db.forget_skipped_albums(watch.id) == 1
    assert db.get_seen_album_ids(watch.id) == {'al-1'}
    assert db.forget_skipped_albums(watch.id) == 0
