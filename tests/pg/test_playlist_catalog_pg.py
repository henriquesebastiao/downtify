"""PlaylistCatalog and ManualPlaylistOwners on both backends.

The same calls must give the same results on SQLite and PostgreSQL.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from downtify.db.config import Dialect
from downtify.playlist_catalog import ManualPlaylistOwners, PlaylistCatalog

SID_A = '4uLU6hMCjMI75M1A2tKUQC'
SID_B = '2dLLR6qlu5UJ5gk0dKz83h'


def _track(directory: Path, name: str) -> Path:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(name.encode() * 3)
    return path


def _content_key(catalog: PlaylistCatalog, playlist: str, sid: str) -> str:
    for row in catalog.list_tracks(playlist):
        if row['track_spotify_id'] == sid:
            return row['content_key']
    raise AssertionError(f'{sid} not in {playlist!r}')


def test_playlist_rows_owners_and_names(backend_db) -> None:
    catalog = PlaylistCatalog(backend_db)

    catalog.ensure_playlist('')
    catalog.ensure_playlist('beta', user_id=7)
    catalog.ensure_playlist('  apple ', spotify_id=' sp1 ')
    catalog.ensure_playlist('beta', user_id=9)
    catalog.ensure_playlist('Banana', spotify_id='   ')

    # Sorted bytewise on both backends: 'B' sorts before 'a'.
    assert catalog.list_playlist_names() == ['Banana', 'apple', 'beta']
    assert catalog.playlist_owner_map() == {
        'Banana': 0,
        'apple': 0,
        'beta': 7,
    }
    assert catalog.spotify_id_for_playlist('apple') == 'sp1'
    assert catalog.spotify_id_for_playlist('Banana') is None
    assert catalog.spotify_id_for_playlist('') is None
    assert catalog.list_playlists_with_spotify_id() == [
        {'name': 'apple', 'spotify_id': 'sp1', 'track_count': 0}
    ]

    assert catalog.reassign_legacy(0) == 0
    assert catalog.reassign_legacy(4) == 2
    assert catalog.reassign_legacy(5) == 0
    assert catalog.playlist_owner_map() == {
        'Banana': 4,
        'apple': 4,
        'beta': 7,
    }


def test_tracks_lookups_and_updates(backend_db, tmp_path: Path) -> None:
    catalog = PlaylistCatalog(backend_db)
    a_path = _track(tmp_path, 'a.mp3')
    b_path = _track(tmp_path, 'b.mp3')
    c_path = _track(tmp_path, 'c.mp3')

    catalog.upsert_track(
        'Mix', {'song_id': SID_A}, 'Artist/a.mp3', a_path, track_order=2
    )
    catalog.upsert_track(
        'Mix', {'song_id': SID_B}, 'b.mp3', b_path, track_order=1
    )
    catalog.upsert_track(
        'Mix',
        {'song_id': 'deezer-42', 'source': 'deezer'},
        'c.mp3',
        c_path,
    )
    # No usable id: ignored.
    catalog.upsert_track('Mix', {'song_id': 'nope'}, 'x.mp3', c_path)
    # Same song, second playlist.
    catalog.upsert_track('Other', {'song_id': SID_A}, 'a-copy.mp3', a_path)

    rows = catalog.list_tracks('Mix')
    assert [r['track_spotify_id'] for r in rows] == [
        'deezer-42',
        SID_B,
        SID_A,
    ]
    assert [r['track_order'] for r in rows] == [0, 1, 2]
    assert rows[2]['filename'] == 'Artist/a.mp3'
    assert all(isinstance(r['track_order'], int) for r in rows)
    assert catalog.list_tracks('') == []
    assert catalog.list_tracks('Nobody') == []
    assert len(catalog.all_track_rows()) == 4

    assert catalog.playlists_for_track(SID_A) == ['Mix', 'Other']
    assert catalog.playlists_for_track(SID_B) == ['Mix']
    assert catalog.playlists_for_track('') == []

    ck_a = _content_key(catalog, 'Mix', SID_A)
    ck_b = _content_key(catalog, 'Mix', SID_B)
    assert ck_a
    assert ck_b
    assert catalog.playlists_by_content_keys([ck_a, '', ck_a, 'missing']) == {
        ck_a: ['Mix', 'Other'],
        'missing': [],
    }
    assert catalog.playlists_by_content_keys([]) == {}
    assert catalog.playlists_by_filenames(['Artist\\a.mp3', 'b.mp3', '']) == {
        'Artist/a.mp3': ['Mix'],
        'b.mp3': ['Mix'],
    }
    assert catalog.playlists_by_filenames(['']) == {}

    catalog.set_content_key('Mix', SID_B, 'ck-new')
    catalog.set_content_key('Mix', SID_B, '')
    assert _content_key(catalog, 'Mix', SID_B) == 'ck-new'

    assert catalog.update_filename_by_content_key(
        'ck-new', 'moved\\b.mp3'
    ) == ['Mix']
    assert catalog.update_filename_by_content_key('', 'x.mp3') == []
    names = [
        r['filename']
        for r in catalog.list_tracks('Mix')
        if r['track_spotify_id'] == SID_B
    ]
    assert names == ['moved/b.mp3']


def test_remove_track_and_remove_by_filename(
    backend_db, tmp_path: Path
) -> None:
    catalog = PlaylistCatalog(backend_db)
    a_path = _track(tmp_path, 'a.mp3')
    b_path = _track(tmp_path, 'b.mp3')
    catalog.upsert_track('Mix', {'song_id': SID_A}, 'a.mp3', a_path)
    catalog.upsert_track('Other', {'song_id': SID_A}, 'a.mp3', a_path)
    catalog.upsert_track('Mix', {'song_id': SID_B}, 'moved/b.mp3', b_path)
    catalog.upsert_track('Other', {'song_id': SID_B}, 'moved/b.mp3', b_path)

    assert catalog.remove_track('Mix', SID_A) is True
    assert catalog.remove_track('Mix', SID_A) is False
    assert catalog.remove_track('', SID_A) is False
    assert catalog.remove_track('Mix', '') is False
    assert catalog.playlists_for_track(SID_A) == ['Other']

    assert catalog.remove_tracks_for_filename('') == []
    assert catalog.remove_tracks_for_filename('moved\\b.mp3', 'Other') == [
        'Other'
    ]
    assert catalog.playlists_for_track(SID_B) == ['Mix']
    assert catalog.remove_tracks_for_filename('moved/b.mp3') == ['Mix']
    assert catalog.playlists_for_track(SID_B) == []
    assert catalog.all_track_rows() == [
        {
            'playlist_name': 'Other',
            'track_spotify_id': SID_A,
            'content_key': catalog.all_track_rows()[0]['content_key'],
            'filename': 'a.mp3',
            'track_order': 0,
        }
    ]


def test_delete_playlist_removes_its_tracks(
    backend_db, tmp_path: Path
) -> None:
    catalog = PlaylistCatalog(backend_db)
    a_path = _track(tmp_path, 'a.mp3')
    b_path = _track(tmp_path, 'b.mp3')
    catalog.replace_playlist_tracks(
        'Gone',
        [
            ({'song_id': SID_A}, 'a.mp3', a_path),
            ({'song_id': SID_B}, 'b.mp3', b_path),
        ],
        spotify_id='playlist12345678901234567890',
        user_id=3,
    )
    catalog.upsert_track('Kept', {'song_id': SID_A}, 'a.mp3', a_path)

    assert catalog.delete_playlist('') == []
    assert catalog.delete_playlist('Nobody') == []
    assert sorted(catalog.delete_playlist('Gone')) == ['a.mp3', 'b.mp3']
    assert catalog.list_playlist_names() == ['Kept']
    assert catalog.list_tracks('Gone') == []
    assert catalog.playlists_for_track(SID_B) == []
    assert [r['playlist_name'] for r in catalog.all_track_rows()] == ['Kept']
    assert catalog.list_playlists_with_spotify_id() == []


def test_postgres_cascade_removes_child_rows(
    backend_db, tmp_path: Path
) -> None:
    """Deleting the parent row alone drops its tracks on PostgreSQL."""

    if backend_db.dialect is not Dialect.POSTGRES:
        return
    catalog = PlaylistCatalog(backend_db)
    catalog.upsert_track(
        'Cascade', {'song_id': SID_A}, 'a.mp3', _track(tmp_path, 'a.mp3')
    )
    with backend_db.connect() as conn:
        conn.execute('DELETE FROM playlists WHERE name = ?', ('Cascade',))
    assert catalog.list_tracks('Cascade') == []
    assert catalog.all_track_rows() == []


def test_backfill_from_monitor_db(backend_db, tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    _track(download_dir, 'Artist - Song.mp3')
    monitor_db = tmp_path / 'monitor.db'
    with sqlite3.connect(monitor_db) as conn:
        conn.executescript("""
            CREATE TABLE monitored_playlists (
                id INTEGER PRIMARY KEY,
                spotify_id TEXT NOT NULL,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                interval_minutes INTEGER DEFAULT 60,
                enabled INTEGER DEFAULT 1,
                last_checked TEXT,
                last_track_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE downloaded_tracks (
                id INTEGER PRIMARY KEY,
                playlist_id INTEGER NOT NULL,
                track_spotify_id TEXT NOT NULL,
                downloaded_at TEXT NOT NULL,
                filename TEXT
            );
            INSERT INTO monitored_playlists VALUES (
                1, 'playlist12345678901234567890', 'Old Mix', 'http://x',
                60, 1, NULL, 0, 'now'
            );
            INSERT INTO downloaded_tracks VALUES (
                1, 1, '4uLU6hMCjMI75M1A2tKUQC', 'now', 'Artist - Song.mp3'
            );
        """)

    catalog = PlaylistCatalog(backend_db)
    linked = catalog.backfill_from_monitor_db(
        monitor_db, download_dir=download_dir
    )
    if backend_db.dialect is Dialect.SQLITE:
        assert linked == 1
        assert catalog.list_tracks('Old Mix')[0]['filename'] == (
            'Artist - Song.mp3'
        )
    else:
        # The monitor history is only read from its SQLite file.
        assert linked == 0
        assert catalog.list_tracks('Old Mix') == []
    assert (
        catalog.backfill_from_monitor_db(
            tmp_path / 'missing.db', download_dir=download_dir
        )
        == 0
    )


def test_manual_playlist_owners(backend_db) -> None:
    owners = ManualPlaylistOwners(backend_db)

    owners.set_owner('  Road Trip ', 5)
    owners.set_owner('', 5)
    owners.set_owner('Nobody', 0)
    assert owners.owner('road trip') == 5
    assert owners.owner('Nobody') is None
    assert owners.owner('') is None
    assert owners.owner('missing') is None

    assert owners.claim_owner('Road Trip', 6) is False
    assert owners.claim_owner('', 1) is False
    assert owners.claim_owner('New', 0) is False
    assert owners.claim_owner('New', 6) is True
    assert owners.claim_owner('new', 7) is False
    assert owners.owner('new') == 6
    assert owners.owner_map() == {'road trip': 5, 'new': 6}

    owners.rename_owner('Road Trip', 'Road Trip 2')
    assert owners.owner('road trip') is None
    assert owners.owner('road trip 2') == 5
    owners.rename_owner('Missing', 'Still Missing')
    assert owners.owner('still missing') is None

    owners.forget_owner('NEW')
    assert owners.owner('new') is None

    owners.set_owner('Keep', 9)
    owners.remove_user(5)
    assert owners.owner_map() == {'keep': 9}
