"""Per-user libraries: ownership, scoped likes/playlists/queue/feeds.

A ``user`` sees only tracks they asked to download (one file on disk,
one ownership row each - see ``downtify/track_owners.py``); an
``admin`` sees everything. Offline.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from downtify import account_routes, api
from downtify.auth import Principal
from downtify.discover import DiscoverStore, artist_key
from downtify.downloader import Downloader
from downtify.library_cache_keys import file_content_key_from_name_and_size
from downtify.library_sync import LibrarySync
from downtify.likes import LikedTracks, sync_liked_playlist
from downtify.monitor import (
    LibraryStores,
    PlaylistMonitorDB,
    _record_sweep_owner,
)
from downtify.playlist_batches import PlaylistBatchStore
from downtify.playlist_catalog import ManualPlaylistOwners, PlaylistCatalog
from downtify.podcasts import EpisodeInfo, PodcastStore
from downtify.track_owners import TrackOwners
from downtify.traffic import (
    DIRECTION_IN,
    DIRECTION_OUT,
    TrafficCounters,
    TrafficMiddleware,
)
from downtify.users import UserStore


def _principal(
    user_id: int = 0, role: str = 'user', username: str = ''
) -> Principal:
    return Principal(
        'device', 'client', '', user_id, username or f'user{user_id}', role
    )


def _request(user_id: int = 0, role: str = 'user') -> Request:
    scope: dict[str, Any] = {'type': 'http', 'headers': []}
    if user_id or role == 'admin':
        scope['state'] = {'principal': _principal(user_id, role)}
    return Request(scope)


def _admin_request() -> Request:
    return _request(1, 'admin')


def _key(name: str, size: int = 100) -> str:
    key = file_content_key_from_name_and_size(name, size)
    assert key
    return key


def _entry(name: str, size: int = 100, **kw: Any) -> dict[str, Any]:
    row = {'file': name, 'size': size, 'playlists': []}
    row.update(kw)
    return row


# ── TrackOwners ──────────────────────────────────────────────────────


def test_two_owners_share_one_file(tmp_path):
    owners = TrackOwners(tmp_path / 'lib.db')

    assert owners.add('key-a', 5) is True
    assert owners.add('key-a', 5) is False
    assert owners.add('key-a', 7) is True
    assert owners.add('key-a', 0) is False
    assert owners.add('', 5) is False

    assert owners.owners('key-a') == [5, 7]
    assert owners.count('key-a') == 2
    assert owners.owned_keys(5) == {'key-a'}
    assert owners.owned_keys(9) == set()


def test_removing_the_last_owner_empties_the_file(tmp_path):
    owners = TrackOwners(tmp_path / 'lib.db')
    owners.add('key-a', 5)
    owners.add('key-a', 7)

    assert owners.remove('key-a', 5) == 1
    assert owners.owners('key-a') == [7]
    assert owners.remove('key-a', 7) == 0
    assert owners.count('key-a') == 0


def test_drop_file_and_remove_user(tmp_path):
    owners = TrackOwners(tmp_path / 'lib.db')
    owners.add('key-a', 5)
    owners.add('key-b', 5)
    owners.add('key-a', 7)

    owners.drop_file('key-a')
    assert owners.count('key-a') == 0
    assert owners.owned_keys(5) == {'key-b'}

    assert owners.remove_user(5) == 1
    assert owners.owned_keys(5) == set()
    assert owners.owned_keys(7) == set()


def test_owned_subset_is_chunked_and_scoped(tmp_path):
    owners = TrackOwners(tmp_path / 'lib.db')
    owners.add('key-a', 5)
    owners.add('key-b', 7)

    assert owners.owned_subset(['key-a', 'key-b', 'key-c'], 5) == {'key-a'}
    assert owners.owned_subset(['key-a'], 0) == set()
    assert owners.owned_subset([], 5) == set()


# ── likes ────────────────────────────────────────────────────────────


def test_hearts_belong_to_who_tapped(tmp_path):
    store = LikedTracks(tmp_path / 'lib.db')
    assert store.like('a.mp3', user_id=5) is True
    assert store.like('a.mp3', user_id=5) is False
    assert store.like('a.mp3', user_id=7) is True

    assert store.paths(5) == ['a.mp3']
    assert store.paths(7) == ['a.mp3']
    assert store.paths() == ['a.mp3', 'a.mp3']
    assert store.count(5) == 1

    assert store.unlike('a.mp3', 5) is True
    assert store.paths(5) == []
    assert store.paths(7) == ['a.mp3']

    assert store.unlike('a.mp3') is True
    assert store.count() == 0


def test_clearing_is_scoped(tmp_path):
    store = LikedTracks(tmp_path / 'lib.db')
    store.like('a.mp3', user_id=5)
    store.like('b.mp3', user_id=7)

    assert store.clear(5) == 1
    assert store.paths(7) == ['b.mp3']
    assert store.clear() == 1


def test_legacy_hearts_read_as_admin_made(tmp_path):
    db = tmp_path / 'lib.db'
    with sqlite3.connect(str(db)) as conn:
        conn.execute("""
            CREATE TABLE liked_tracks (
                stored_path TEXT PRIMARY KEY,
                content_key TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                artist TEXT NOT NULL DEFAULT '',
                duration REAL NOT NULL DEFAULT 0,
                liked_at TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO liked_tracks VALUES ('a.mp3', '', 'A', 'X', 200, "
            "'2024-01-01T00:00:00')"
        )
    store = LikedTracks(db)

    assert store.paths() == ['a.mp3']
    assert store.paths(0) == ['a.mp3']
    assert store.paths(5) == []
    store.like('b.mp3', user_id=5)
    assert store.paths(5) == ['b.mp3']


def test_the_shared_playlist_holds_admin_hearts_only(tmp_path):
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    (downloads / 'a.mp3').write_bytes(b'audio-a')
    (downloads / 'b.mp3').write_bytes(b'audio-b')
    store = LikedTracks(tmp_path / 'lib.db')
    store.like('a.mp3', user_id=5)
    store.like('b.mp3')

    path = sync_liked_playlist(store, downloads, user_ids={0})
    assert path is not None
    text = path.read_text(encoding='utf-8')
    assert 'b.mp3' in text
    assert 'a.mp3' not in text


def test_repointing_is_scoped(tmp_path):
    store = LikedTracks(tmp_path / 'lib.db')
    store.like('old.mp3', user_id=5)
    store.like('old.mp3', user_id=7)

    assert store.update_path('old.mp3', 'new.mp3', 5) is True
    assert store.paths(5) == ['new.mp3']
    assert store.paths(7) == ['old.mp3']


# ── playlists ────────────────────────────────────────────────────────


def test_playlist_ownership_sticks_to_the_creator(tmp_path):
    catalog = PlaylistCatalog(tmp_path / 'lib.db')
    catalog.ensure_playlist('Mix', user_id=7)

    assert catalog.playlist_owner_map() == {'Mix': 7}
    catalog.ensure_playlist('Mix', user_id=9)
    assert catalog.playlist_owner_map() == {'Mix': 7}


def test_manual_playlist_owners(tmp_path):
    owners = ManualPlaylistOwners(tmp_path / 'lib.db')
    owners.set_owner('Road Trip', 7)

    assert owners.owner('road trip') == 7
    assert owners.owner('Other') is None
    owners.rename_owner('Road Trip', 'Road Trip 2')
    assert owners.owner('Road Trip') is None
    assert owners.owner('road trip 2') == 7
    owners.forget_owner('Road Trip 2')
    assert owners.owner('road trip 2') is None

    owners.set_owner('Kept', 7)
    owners.set_owner('Gone', 7)
    assert owners.owner_map() == {'kept': 7, 'gone': 7}
    owners.remove_user(7)
    assert owners.owner_map() == {}


# ── batches ──────────────────────────────────────────────────────────


def _batch(store: PlaylistBatchStore, sid: str, user_id: int = 0) -> int:
    return store.start_batch(
        sid,
        f'Name {sid}',
        f'https://open.spotify.com/playlist/{sid}',
        3,
        user_id=user_id,
    )


def test_batches_are_scoped_to_who_queued_them(tmp_path):
    store = PlaylistBatchStore(tmp_path / 'lib.db')
    _batch(store, 'pl-old')
    _batch(store, 'pl-mine', user_id=5)

    assert {b['spotify_playlist_id'] for b in store.list_latest_batches()} == {
        'pl-old',
        'pl-mine',
    }
    assert [
        b['spotify_playlist_id'] for b in store.list_latest_batches(5)
    ] == ['pl-mine']
    assert store.list_latest_batches(9) == []
    assert [b['spotify_playlist_id'] for b in store.list_open_batches(5)] == [
        'pl-mine'
    ]


# ── mobile feed ──────────────────────────────────────────────────────


def _sync(tmp_path: Path) -> LibrarySync:
    return LibrarySync(tmp_path / 'lib.db')


def test_sync_feed_shows_only_owned_tracks(tmp_path):
    sync = _sync(tmp_path)
    first = {
        'file': 'a.mp3',
        'title': 'A',
        'artist': 'X',
        'size': 100,
        'duration': 200.0,
    }
    second = dict(first, file='b.mp3', title='B')
    sync.refresh([first, second])

    allowed = {_key('a.mp3')}
    feed = sync.changes(0, allowed_keys=allowed)
    assert feed['full'] is True
    assert [t['file'] for t in feed['tracks']] == ['a.mp3']
    assert feed['deleted'] == []

    open_feed = sync.changes(0)
    assert {t['file'] for t in open_feed['tracks']} == {'a.mp3', 'b.mp3'}


def test_released_tracks_leave_through_deleted(tmp_path):
    sync = _sync(tmp_path)
    cursor = sync.refresh([
        {
            'file': 'a.mp3',
            'title': 'A',
            'artist': 'X',
            'size': 100,
            'duration': 200.0,
        },
    ])
    assert sync.touch('a.mp3') is True
    assert sync.touch('missing.mp3') is False

    feed = sync.changes(cursor, allowed_keys=set())
    assert feed['full'] is False
    assert feed['tracks'] == []
    assert len(feed['deleted']) == 1

    kept = sync.changes(cursor, allowed_keys={_key('a.mp3')})
    assert [t['file'] for t in kept['tracks']] == ['a.mp3']
    assert kept['deleted'] == []


# ── role changes keep ownership ──────────────────────────────────────


def test_promotion_shows_everything_without_losing_rows(monkeypatch, tmp_path):
    _wired_state(monkeypatch, tmp_path, {_key('a.mp3'): 5})
    entries = [_entry('a.mp3'), _entry('b.mp3')]
    user_request = _request(5)
    admin_request = Request({
        'type': 'http',
        'headers': [],
        'state': {'principal': _principal(5, 'admin', 'maria')},
    })

    # As a user: only their own track.
    assert [
        e['file'] for e in api._filter_entries_for(entries, user_request)
    ] == ['a.mp3']
    # Promoted to admin: the whole library, same rows underneath.
    assert api._filter_entries_for(entries, admin_request) == entries
    assert api._filter_playlists_for([], admin_request) == []
    # Demoted back: only their own again, nothing was dropped.
    assert [
        e['file'] for e in api._filter_entries_for(entries, user_request)
    ] == ['a.mp3']
    assert api.likes_scope(admin_request) is None
    assert api.likes_scope(user_request) == 5


# ── request helpers ──────────────────────────────────────────────────


def test_request_identity_helpers():
    assert api.request_user_id(_request()) == 0
    assert api.request_is_admin(_request()) is False
    assert api.request_user_id(_admin_request()) == 1
    assert api.request_is_admin(_admin_request()) is True
    assert api.request_user_id(None) == 0
    assert api.request_is_admin(None) is False
    assert api.likes_scope(_admin_request()) is None
    assert api.likes_scope(_request(5)) == 5


def test_queue_shows_own_jobs_to_users_and_all_to_admins():
    api.state.download_jobs.clear()
    try:
        mine = api._register_job(
            {'song_id': 'm1', 'name': 'Mine'}, status='queued', user_id=5
        )
        hers = api._register_job(
            {'song_id': 'h1', 'name': 'Hers'}, status='queued', user_id=7
        )
        legacy = api._register_job(
            {'song_id': 'l1', 'name': 'Legacy'}, status='done'
        )
        own = api.get_queue(_request(5))
        assert {j['song']['song_id'] for j in own} == {'m1'}
        all_jobs = api.get_queue(_admin_request())
        assert {j['song']['song_id'] for j in all_jobs} == {'m1', 'h1', 'l1'}

        assert api.remove_queue_item(_request(5), song_id=hers) == {
            'removed': False
        }
        assert api.remove_queue_item(_request(5), song_id=mine) == {
            'removed': True
        }
        assert mine not in api.state.download_jobs
        assert hers in api.state.download_jobs
        assert legacy in api.state.download_jobs
    finally:
        api.state.download_jobs.clear()


def test_queue_clearing_is_scoped():
    api.state.download_jobs.clear()
    try:
        api._register_job({'song_id': 'm1'}, status='done', user_id=5)
        api._register_job({'song_id': 'h1'}, status='done', user_id=7)
        assert api.clear_completed_queue(_request(5)) == {'removed': 1}
        assert set(api.state.download_jobs) == {'h1'}
        assert api.clear_queue(_request(5)) == {'cleared': True}
        assert set(api.state.download_jobs) == {'h1'}
        assert api.clear_queue(_admin_request()) == {'cleared': True}
        assert api.state.download_jobs == {}
    finally:
        api.state.download_jobs.clear()


# ── entry and playlist filtering ─────────────────────────────────────


def _wired_state(monkeypatch, tmp_path, owners: dict[str, int]) -> None:
    store = TrackOwners(tmp_path / 'lib.db')
    for key, user_id in owners.items():
        store.add(key, user_id)
    monkeypatch.setattr(api.state, 'track_owners', store)


def test_entries_keep_only_owned_files(monkeypatch, tmp_path):
    _wired_state(monkeypatch, tmp_path, {_key('a.mp3'): 5})
    entries = [_entry('a.mp3'), _entry('b.mp3')]

    mine = api._filter_entries_for(entries, _request(5))
    assert [e['file'] for e in mine] == ['a.mp3']
    assert api._filter_entries_for(entries, _request(7)) == []
    assert api._filter_entries_for(entries, _admin_request()) == entries
    assert api._filter_entries_for(entries, _request()) == []


def test_entries_scrub_foreign_playlists(monkeypatch, tmp_path):
    _wired_state(monkeypatch, tmp_path, {_key('a.mp3'): 5, _key('b.mp3'): 5})
    catalog = PlaylistCatalog(tmp_path / 'lib.db')
    catalog.ensure_playlist('Mine', user_id=5)
    catalog.ensure_playlist('Theirs', user_id=7)
    manual = ManualPlaylistOwners(tmp_path / 'lib.db')
    manual.set_owner('My Mix', 5)
    monkeypatch.setattr(api.state, 'playlist_catalog', catalog)
    monkeypatch.setattr(api.state, 'manual_playlist_owners', manual)
    entries = [
        _entry(
            'a.mp3',
            playlists=['Mine', 'Theirs', 'My Mix', 'Downtify Liked Songs'],
        ),
        _entry('b.mp3'),
    ]

    mine = api._filter_entries_for(entries, _request(5))
    assert mine[0]['playlists'] == ['Mine', 'My Mix', 'Downtify Liked Songs']
    # The shared snapshot is never mutated.
    assert entries[0]['playlists'] == [
        'Mine',
        'Theirs',
        'My Mix',
        'Downtify Liked Songs',
    ]


def test_playlist_listing_is_scoped_with_a_personal_liked(
    monkeypatch, tmp_path
):
    catalog = PlaylistCatalog(tmp_path / 'lib.db')
    catalog.ensure_playlist('Mine', user_id=5)
    catalog.ensure_playlist('Theirs', user_id=7)
    manual = ManualPlaylistOwners(tmp_path / 'lib.db')
    manual.set_owner('My Mix', 5)
    monkeypatch.setattr(api.state, 'playlist_catalog', catalog)
    monkeypatch.setattr(api.state, 'manual_playlist_owners', manual)
    likes = LikedTracks(tmp_path / 'lib.db')
    likes.like('a.mp3', user_id=5)
    monkeypatch.setattr(api.state, 'likes', likes)
    found = [
        {
            'name': 'Mine',
            'files': ['m.mp3'],
            'count': 1,
            'added': 1,
            'cover': '',
            'liked': False,
            'manual': False,
        },
        {
            'name': 'Theirs',
            'files': ['t.mp3'],
            'count': 1,
            'added': 2,
            'cover': '',
            'liked': False,
            'manual': False,
        },
        {
            'name': 'My Mix',
            'files': [],
            'count': 0,
            'added': 3,
            'cover': '',
            'liked': False,
            'manual': True,
        },
        {
            'name': 'Downtify Liked Songs',
            'files': ['t.mp3'],
            'count': 1,
            'added': 4,
            'cover': 'x.jpg',
            'liked': True,
            'manual': False,
        },
    ]

    mine = api._filter_playlists_for(found, _request(5))
    assert [p['name'] for p in mine] == [
        'Downtify Liked Songs',
        'Mine',
        'My Mix',
    ]
    liked = mine[0]
    assert liked['liked'] is True
    assert liked['files'] == ['a.mp3']
    assert not liked['cover']

    assert api._filter_playlists_for(found, _request(7)) == [
        p for p in found if p['name'] == 'Theirs'
    ]
    assert api._filter_playlists_for(found, _admin_request()) == found


# ── first-start backfill ─────────────────────────────────────────────


def _auth_with(users) -> Any:
    class _Auth:
        pass

    auth = _Auth()
    auth.users = users
    return auth


def test_backfill_gives_current_files_to_brillik(monkeypatch, tmp_path):

    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    (downloads / 'Old Song.mp3').write_bytes(b'x' * 100)
    users = UserStore(tmp_path / 'auth.db')
    users.create('admin', 'password123', role='admin')
    brillik = users.create('brillik', 'password123', role='user')
    monkeypatch.setattr(api.state, 'auth', _auth_with(users))
    monkeypatch.setattr(
        api.state,
        'downloader',
        Downloader(download_dir=downloads, audio_format='mp3'),
    )
    monkeypatch.setattr(api.state, 'settings', {})
    monkeypatch.setattr(
        api.state, 'track_owners', TrackOwners(tmp_path / 'lib.db')
    )
    likes = LikedTracks(tmp_path / 'lib.db')
    likes.like('Old Song.mp3')
    monkeypatch.setattr(api.state, 'likes', likes)
    monkeypatch.setattr(api.state, 'playlist_catalog', None)
    monkeypatch.setattr(api.state, 'playlist_batch_store', None)
    monkeypatch.setattr(api.state, 'library_sync', None)

    done = api.migrate_first_run_ownership()

    assert done['files'] == 1
    assert done['likes'] == 1
    owners = api.state.track_owners
    assert owners is not None
    assert owners.owned_keys(brillik['id']) == {_key('Old Song.mp3', 100)}
    assert likes.paths(brillik['id']) == ['Old Song.mp3']
    # Second start: nothing left to do.
    assert api.migrate_first_run_ownership() == {
        'files': 0,
        'likes': 0,
        'playlists': 0,
        'batches': 0,
        'podcasts': 0,
        'watches': 0,
        'listens': 0,
    }


def test_backfill_falls_back_to_the_oldest_admin(monkeypatch, tmp_path):

    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    (downloads / 'Old Song.mp3').write_bytes(b'x' * 100)
    users = UserStore(tmp_path / 'auth.db')
    admin = users.create('admin', 'password123', role='admin')
    monkeypatch.setattr(api.state, 'auth', _auth_with(users))
    monkeypatch.setattr(
        api.state,
        'downloader',
        Downloader(download_dir=downloads, audio_format='mp3'),
    )
    monkeypatch.setattr(api.state, 'settings', {})
    monkeypatch.setattr(
        api.state, 'track_owners', TrackOwners(tmp_path / 'lib.db')
    )
    monkeypatch.setattr(api.state, 'likes', LikedTracks(tmp_path / 'lib.db'))
    monkeypatch.setattr(api.state, 'playlist_catalog', None)
    monkeypatch.setattr(api.state, 'playlist_batch_store', None)
    monkeypatch.setattr(api.state, 'library_sync', None)

    done = api.migrate_first_run_ownership()

    assert done['files'] == 1
    owners = api.state.track_owners
    assert owners is not None
    assert len(owners.owned_keys(admin['id'])) == 1


def test_backfill_takes_shows_watches_and_listens(monkeypatch, tmp_path):

    users = UserStore(tmp_path / 'auth.db')
    users.create('admin', 'password123', role='admin')
    brillik = users.create('brillik', 'password123', role='user')
    monkeypatch.setattr(api.state, 'auth', _auth_with(users))
    monkeypatch.setattr(
        api.state, 'track_owners', TrackOwners(tmp_path / 'lib.db')
    )
    shows = PodcastStore(tmp_path / 'lib.db')
    show = shows.add_show('https://example.com/feed.xml', 'Show')
    episode = shows.upsert_episodes(show['id'], [_episode()])[0]
    shows.set_playback(episode['id'], position_seconds=5.0)
    monkeypatch.setattr(api.state, 'podcasts', shows)
    watches = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watches.add_playlist('sid-1', 'Mix', 'https://x/1', 60)
    monkeypatch.setattr(api.state, 'monitor_db', watches)
    history = DiscoverStore(tmp_path / 'lib.db')
    history.record_listen('Daft Punk')
    history.block('Nope')
    monkeypatch.setattr(api.state, 'discover', history)
    monkeypatch.setattr(api.state, 'likes', LikedTracks(tmp_path / 'lib.db'))
    monkeypatch.setattr(
        api.state, 'playlist_catalog', PlaylistCatalog(tmp_path / 'lib.db')
    )
    monkeypatch.setattr(
        api.state,
        'playlist_batch_store',
        PlaylistBatchStore(tmp_path / 'lib.db'),
    )
    monkeypatch.setattr(api.state, 'library_sync', None)
    monkeypatch.setattr(
        api.state,
        'downloader',
        Downloader(download_dir=tmp_path / 'downloads', audio_format='mp3'),
    )
    monkeypatch.setattr(api.state, 'settings', {})
    (tmp_path / 'downloads').mkdir(exist_ok=True)

    done = api.migrate_first_run_ownership()

    bid = brillik['id']
    assert done['podcasts'] == 2
    assert done['watches'] == 1
    assert done['listens'] == 2
    assert [s['id'] for s in shows.list_shows(bid)] == [show['id']]
    assert shows.get_episode(episode['id'], bid)['position_seconds'] == 5.0
    assert [w.spotify_id for w in watches.list_playlists(bid)] == ['sid-1']
    assert [row['name'] for row in history.listens(bid)] == ['Daft Punk']
    assert [row['name'] for row in history.blocked(bid)] == ['Nope']


def test_deleting_a_user_releases_everything(monkeypatch, tmp_path):

    users = UserStore(tmp_path / 'auth.db')
    users.create('admin', 'password123', role='admin')
    users.create('maria', 'password123', role='user')
    monkeypatch.setattr(api.state, 'auth', _auth_with(users))
    owners = TrackOwners(tmp_path / 'lib.db')
    owners.add('key-a', 2)
    monkeypatch.setattr(api.state, 'track_owners', owners)
    likes = LikedTracks(tmp_path / 'lib.db')
    likes.like('a.mp3', user_id=2)
    monkeypatch.setattr(api.state, 'likes', likes)
    manual = ManualPlaylistOwners(tmp_path / 'lib.db')
    manual.set_owner('Mine', 2)
    monkeypatch.setattr(api.state, 'manual_playlist_owners', manual)
    shows = PodcastStore(tmp_path / 'lib.db')
    shows.add_show('https://example.com/feed.xml', 'Show', user_id=2)
    monkeypatch.setattr(api.state, 'podcasts', shows)
    watches = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watches.add_playlist('sid-1', 'Mix', 'https://x/1', 60, user_id=2)
    monkeypatch.setattr(api.state, 'monitor_db', watches)
    history = DiscoverStore(tmp_path / 'lib.db')
    history.record_listen('Daft Punk', user_id=2)
    monkeypatch.setattr(api.state, 'discover', history)
    traffic = TrafficCounters(tmp_path / 'lib.db')
    traffic.add(2, DIRECTION_IN, 100)
    monkeypatch.setattr(api.state, 'traffic', traffic)

    account_routes._forget_user_library(2)

    assert owners.owned_keys(2) == set()
    assert likes.paths(2) == []
    assert manual.owner_map() == {}
    assert shows.list_shows(2) == []
    assert watches.list_playlists(2) == []
    assert history.listens(2) == []
    assert traffic.totals() == {}


# ── ownership recording and deleting ─────────────────────────────────


def _downloader_state(monkeypatch, tmp_path):
    downloads = tmp_path / 'downloads'
    downloads.mkdir(exist_ok=True)
    monkeypatch.setattr(
        api.state,
        'downloader',
        Downloader(download_dir=downloads, audio_format='mp3'),
    )
    monkeypatch.setattr(api.state, 'settings', {})
    monkeypatch.setattr(
        api.state, 'track_owners', TrackOwners(tmp_path / 'lib.db')
    )
    return downloads


def test_two_downloads_share_one_file_with_one_row_each(monkeypatch, tmp_path):
    downloads = _downloader_state(monkeypatch, tmp_path)
    (downloads / 'Artist - Song.mp3').write_bytes(b'audio-bytes')

    api._note_download_owner('Artist - Song.mp3', 5)
    api._note_download_owner('Artist - Song.mp3', 7)
    api._note_download_owner('Artist - Song.mp3', 0)
    api._note_download_owner('missing.mp3', 5)

    owners = api.state.track_owners
    assert owners is not None
    keys = owners.owned_keys(5)
    assert len(keys) == 1
    assert owners.owners(next(iter(keys))) == [5, 7]
    assert owners.owned_keys(9) == set()


def test_delete_actions_follow_ownership(monkeypatch, tmp_path):
    downloads = _downloader_state(monkeypatch, tmp_path)
    (downloads / 'Solo.mp3').write_bytes(b'solo')
    (downloads / 'Shared.mp3').write_bytes(b'shared')
    (downloads / 'Old.mp3').write_bytes(b'old')
    owners = api.state.track_owners
    assert owners is not None
    api._note_download_owner('Solo.mp3', 5)
    api._note_download_owner('Shared.mp3', 5)
    api._note_download_owner('Shared.mp3', 7)

    assert api.ownership_action('Solo.mp3', _request(5))[0] == 'delete'
    assert api.ownership_action('Shared.mp3', _request(5))[0] == 'release'
    assert api.ownership_action('Shared.mp3', _request(7))[0] == 'release'
    assert api.ownership_action('Shared.mp3', _request(9))[0] == 'foreign'
    assert api.ownership_action('Old.mp3', _request(5))[0] == 'foreign'
    assert api.ownership_action('Old.mp3', _admin_request())[0] == 'delete'
    assert api.ownership_action('missing.mp3', _request(5))[0] == 'missing'


def test_releasing_drops_the_row_and_pokes_the_feed(monkeypatch, tmp_path):
    downloads = _downloader_state(monkeypatch, tmp_path)
    (downloads / 'Shared.mp3').write_bytes(b'shared')
    sync = LibrarySync(tmp_path / 'lib.db')
    monkeypatch.setattr(api.state, 'library_sync', sync)
    owners = api.state.track_owners
    assert owners is not None
    api._note_download_owner('Shared.mp3', 5)
    api._note_download_owner('Shared.mp3', 7)

    result = api.release_file_ownership(
        'Shared.mp3', next(iter(owners.owned_keys(5))), 5
    )
    assert result == {'released': True}
    assert owners.owned_keys(5) == set()
    assert len(owners.owned_keys(7)) == 1
    assert (downloads / 'Shared.mp3').is_file()


# ── podcasts per user ────────────────────────────────────────────────


def _episode() -> EpisodeInfo:
    return EpisodeInfo(
        guid='ep-1',
        title='Pilot',
        description='',
        published_at='2024-01-01',
        duration_seconds=60.0,
        season_number=1,
        episode_number=1,
        enclosure_url='https://example.com/ep1.mp3',
        enclosure_type='audio/mpeg',
    )


def test_two_users_subscribe_to_the_same_feed(tmp_path):
    store = PodcastStore(tmp_path / 'lib.db')
    first = store.add_show('https://example.com/feed.xml', 'Show', user_id=5)
    second = store.add_show('https://example.com/feed.xml', 'Show', user_id=7)

    assert first['id'] != second['id']
    assert first['folder_name'] != second['folder_name']
    assert [s['id'] for s in store.list_shows(5)] == [first['id']]
    assert [s['id'] for s in store.list_shows(7)] == [second['id']]
    assert len(store.list_shows()) == 2
    again = store.add_show('https://example.com/feed.xml', 'Show', user_id=5)
    assert again['id'] == first['id']


def test_playback_position_is_per_user(tmp_path):
    store = PodcastStore(tmp_path / 'lib.db')
    show = store.add_show('https://example.com/feed.xml', 'Show', user_id=5)
    episode = store.upsert_episodes(show['id'], [_episode()])[0]

    store.set_playback(episode['id'], position_seconds=10.0, user_id=5)
    assert store.get_episode(episode['id'], 5)['position_seconds'] == 10.0
    assert store.get_episode(episode['id'], 7)['position_seconds'] == 0
    assert store.get_episode(episode['id'])['position_seconds'] == 0
    store.set_playback(episode['id'], played=True, user_id=7)
    assert store.get_episode(episode['id'], 7)['played'] is True
    assert store.get_episode(episode['id'], 5)['played'] is False


def test_podcast_endpoints_scope_shows_to_their_owner(monkeypatch, tmp_path):
    store = PodcastStore(tmp_path / 'lib.db')
    mine = store.add_show('https://example.com/mine.xml', 'Mine', user_id=5)
    store.add_show('https://example.com/theirs.xml', 'Theirs', user_id=7)
    monkeypatch.setattr(api.state, 'podcasts', store)
    monkeypatch.setattr(api.state, 'monitor_db', None)

    shows = asyncio.run(api.list_podcast_shows(_request(5)))
    assert [s['id'] for s in shows] == [mine['id']]
    assert len(asyncio.run(api.list_podcast_shows(_admin_request()))) == 2
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.get_podcast_show(_request(7), mine['id']))
    assert exc.value.status_code == 404
    assert (
        asyncio.run(api.get_podcast_show(_request(5), mine['id']))['id']
        == mine['id']
    )


# ── legacy schema migrations ─────────────────────────────────────────


def _legacy_monitor_db(path: Path):
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE monitored_playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spotify_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            interval_minutes INTEGER NOT NULL DEFAULT 60,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_checked TEXT,
            last_track_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute(
        'INSERT INTO monitored_playlists (spotify_id, name, url, created_at)'
        " VALUES ('sid-1', 'Mix', 'https://x/1', '2024-01-01')"
    )
    conn.commit()
    conn.close()
    return PlaylistMonitorDB(path)


def test_legacy_watches_migrate_and_allow_same_url_twice(tmp_path):
    db = _legacy_monitor_db(tmp_path / 'monitor.db')

    assert db.reassign_legacy(5) == 1
    assert [w.spotify_id for w in db.list_playlists(5)] == ['sid-1']
    second = db.add_playlist('sid-1', 'Mix', 'https://x/1', 60, user_id=7)
    assert [w.id for w in db.list_playlists(7)] == [second.id]
    assert len(db.list_playlists()) == 2


def test_legacy_podcasts_migrate_to_per_user(tmp_path):
    db = tmp_path / 'lib.db'
    conn = sqlite3.connect(str(db))
    conn.execute("""
        CREATE TABLE podcast_shows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_url TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            author TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            artwork_url TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            folder_name TEXT NOT NULL,
            retention INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute(
        'INSERT INTO podcast_shows (feed_url, name, folder_name, created_at)'
        " VALUES ('https://example.com/feed.xml', 'Show', 'Show',"
        " '2024-01-01')"
    )
    conn.execute("""
        CREATE TABLE podcast_episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            show_id INTEGER NOT NULL,
            guid TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            published_at TEXT NOT NULL DEFAULT '',
            duration_seconds REAL NOT NULL DEFAULT 0,
            season_number INTEGER,
            episode_number INTEGER,
            enclosure_url TEXT NOT NULL DEFAULT '',
            enclosure_type TEXT NOT NULL DEFAULT '',
            filename TEXT,
            downloaded_at TEXT,
            dismissed INTEGER NOT NULL DEFAULT 0,
            UNIQUE(show_id, guid)
        )
    """)
    conn.execute("""
        CREATE TABLE podcast_playback (
            episode_id INTEGER PRIMARY KEY,
            position_seconds REAL NOT NULL DEFAULT 0,
            played INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

    store = PodcastStore(db)
    shows = store.list_shows()
    assert len(shows) == 1
    # Same feed twice now works, in two folders.
    other = store.add_show('https://example.com/feed.xml', 'Show', user_id=7)
    assert other['folder_name'] == 'Show (2)'
    assert store.reassign_legacy(0) == 0


def test_legacy_discover_history_migrates_to_per_user(tmp_path):
    db = tmp_path / 'lib.db'
    conn = sqlite3.connect(str(db))
    conn.execute("""
        CREATE TABLE discover_listens (
            artist_key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            plays INTEGER NOT NULL DEFAULT 0,
            last_played TEXT NOT NULL
        )
    """)
    conn.execute(
        "INSERT INTO discover_listens VALUES ('daft punk', 'Daft Punk', 3,"
        " '2024-01-01')"
    )
    conn.execute("""
        CREATE TABLE discover_blocked (
            artist_key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            blocked_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

    store = DiscoverStore(db)
    assert [row['plays'] for row in store.listens(0)] == [3]
    assert store.listens(5) == []
    assert store.reassign_legacy(5) == 1
    assert [row['plays'] for row in store.listens(5)] == [3]
    assert store.listens(0) == []


# ── monitor watches per user ─────────────────────────────────────────


def test_two_users_watch_the_same_url(tmp_path):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    first = db.add_playlist('sid-1', 'Mix', 'https://x/1', 60, user_id=5)
    second = db.add_playlist('sid-1', 'Mix', 'https://x/1', 60, user_id=7)

    assert first.id != second.id
    assert [w.id for w in db.list_playlists(5)] == [first.id]
    assert [w.id for w in db.list_playlists(7)] == [second.id]
    assert len(db.list_playlists()) == 2
    assert db.get_by_spotify_id('sid-1', 5).id == first.id
    assert db.get_by_spotify_id('sid-1', 7).id == second.id


def test_watch_endpoints_scope_to_their_owner(monkeypatch, tmp_path):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    mine = db.add_playlist('sid-1', 'Mine', 'https://x/1', 60, user_id=5)
    db.add_playlist('sid-2', 'Theirs', 'https://x/2', 60, user_id=7)
    monkeypatch.setattr(api.state, 'monitor_db', db)

    listed = asyncio.run(api.list_monitor_playlists(_request(5)))
    assert [w['id'] for w in listed] == [mine.id]
    assert len(asyncio.run(api.list_monitor_playlists(_admin_request()))) == 2
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.delete_monitor_playlist(mine.id + 1, _request(5)))
    assert exc.value.status_code == 404
    assert asyncio.run(api.delete_monitor_playlist(mine.id, _request(5))) == {
        'deleted': True,
        'id': mine.id,
    }


def test_sweep_download_attributes_the_watch_owner(tmp_path):
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    target = downloads / 'Artist - Song.mp3'
    target.write_bytes(b'x' * 100)
    owners = TrackOwners(tmp_path / 'lib.db')
    library = LibraryStores(track_owners=owners)

    _record_sweep_owner(library, target, 5)
    assert owners.owned_keys(5) == {
        file_content_key_from_name_and_size('Artist - Song.mp3', 100)
    }
    assert owners.owned_keys(7) == set()


# ── discover per user ────────────────────────────────────────────────


def test_listens_and_blocks_are_per_user(tmp_path):
    store = DiscoverStore(tmp_path / 'lib.db')
    store.record_listen('Daft Punk', user_id=5)
    store.record_listen('Daft Punk', user_id=7)
    store.record_listen('Daft Punk', user_id=7)

    assert [row['plays'] for row in store.listens(5)] == [1]
    assert [row['plays'] for row in store.listens(7)] == [2]
    assert store.clear_listens(5) == 1
    assert [row['plays'] for row in store.listens(7)] == [2]

    store.block('Nope', user_id=5)
    assert [row['name'] for row in store.blocked(5)] == ['Nope']
    assert store.blocked(7) == []
    assert store.blocked_keys(5) == {artist_key('nope')}
    assert store.blocked_keys(7) == set()
    assert store.unblock('nope', 7) is False
    assert store.unblock('nope', 5) is True


def test_discover_endpoints_scope_history(monkeypatch, tmp_path):
    store = DiscoverStore(tmp_path / 'lib.db')
    monkeypatch.setattr(api.state, 'discover', store)

    asyncio.run(api.record_listen_endpoint(_listen_request('Air', 5)))
    asyncio.run(api.record_listen_endpoint(_listen_request('Air', 7)))
    assert [
        row['plays']
        for row in asyncio.run(api.blocked_artists_endpoint(_request(5)))
    ] == []
    asyncio.run(api.block_artist_endpoint(_listen_request('Air', 5)))
    assert [
        row['name']
        for row in asyncio.run(api.blocked_artists_endpoint(_request(5)))
    ] == ['Air']
    assert asyncio.run(api.blocked_artists_endpoint(_request(7))) == []
    assert asyncio.run(api.clear_listens_endpoint(_request(5))) == {
        'cleared': 1
    }


# ── duration setting on streams ──────────────────────────────────────


def test_stream_file_uses_the_duration_setting(monkeypatch, tmp_path):
    cached = tmp_path / 'dQw4w9WgXcQ.m4a'
    cached.write_bytes(b'audio')

    async def fake_get(video_id, cookies_file='', **_kwargs):
        return cached

    fake_cache = MagicMock()
    fake_cache.get = fake_get
    fake_cache.cached_path = lambda vid: cached
    monkeypatch.setattr(api.state, 'stream_cache', fake_cache)
    monkeypatch.setattr(
        api.state, 'settings', {'max_track_duration_seconds': 600}
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            api.stream_file_endpoint(
                _request(), video_id='dQw4w9WgXcQ', duration=3600
            )
        )
    assert exc.value.status_code == 400

    monkeypatch.setattr(
        api.state, 'settings', {'max_track_duration_seconds': 0}
    )
    response = asyncio.run(
        api.stream_file_endpoint(
            _request(), video_id='dQw4w9WgXcQ', duration=3600
        )
    )
    assert response.status_code == 200


# ── traffic accounting ───────────────────────────────────────────────


def test_counters_add_up_per_user_and_direction(tmp_path):
    counters = TrafficCounters(tmp_path / 'lib.db')
    counters.add(5, DIRECTION_IN, 100)
    counters.add(5, DIRECTION_IN, 50)
    counters.add(5, DIRECTION_OUT, 1000)
    counters.add(0, DIRECTION_IN, 999)
    counters.add(5, 'sideways', 999)
    counters.add(5, DIRECTION_IN, 0)
    counters.add(5, DIRECTION_IN, -5)

    assert counters.totals() == {5: {'in': 150, 'out': 1000}}
    counters.remove_user(5)
    assert counters.totals() == {}


def test_middleware_counts_served_bytes_per_user(tmp_path):
    async def app(scope, receive, send):
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [],
        })
        await send({'type': 'http.response.body', 'body': b'hello'})
        await send({'type': 'http.response.body', 'body': b'!'})

    counters = TrafficCounters(tmp_path / 'lib.db')
    middleware = TrafficMiddleware(app, lambda: counters)
    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    scope = {
        'type': 'http',
        'state': {'principal': _principal(5)},
    }
    asyncio.run(middleware(scope, None, send))
    assert counters.totals() == {5: {'in': 0, 'out': 6}}
    assert len(sent) == 3

    # Nobody signed in: passthrough, nothing counted.
    before = dict(counters.totals())
    asyncio.run(middleware({'type': 'http', 'state': {}}, None, send))
    assert counters.totals() == before

    # WebSocket frames never pass through the counter.
    asyncio.run(middleware({'type': 'websocket', 'state': {}}, None, send))
    assert counters.totals() == before


def test_finished_downloads_count_as_upstream(monkeypatch, tmp_path):
    downloads = _downloader_state(monkeypatch, tmp_path)
    (downloads / 'Song.mp3').write_bytes(b'x' * 100)
    traffic = TrafficCounters(tmp_path / 'lib.db')
    monkeypatch.setattr(api.state, 'traffic', traffic)

    api._record_download_traffic('Song.mp3', 5)
    api._record_download_traffic('Song.mp3', 0)
    api._record_download_traffic('missing.mp3', 5)

    assert traffic.totals() == {5: {'in': 100, 'out': 0}}


# ── users stats ──────────────────────────────────────────────────────


def test_users_stats_aggregates_per_account(monkeypatch, tmp_path):

    users = UserStore(tmp_path / 'auth.db')
    users.create('admin', 'password123', role='admin')
    users.create('maria', 'password123', role='user')
    monkeypatch.setattr(api.state, 'auth', _auth_with(users))
    owners = TrackOwners(tmp_path / 'lib.db')
    owners.add(_key('a.mp3', 100), 2)
    owners.add(_key('b.mp3', 200), 2)
    owners.add(_key('b.mp3', 200), 1)
    monkeypatch.setattr(api.state, 'track_owners', owners)
    likes = LikedTracks(tmp_path / 'lib.db')
    likes.like('a.mp3', user_id=2)
    monkeypatch.setattr(api.state, 'likes', likes)
    catalog = PlaylistCatalog(tmp_path / 'lib.db')
    catalog.ensure_playlist('Mix', user_id=2)
    monkeypatch.setattr(api.state, 'playlist_catalog', catalog)
    manual = ManualPlaylistOwners(tmp_path / 'lib.db')
    manual.set_owner('Mine', 2)
    monkeypatch.setattr(api.state, 'manual_playlist_owners', manual)
    traffic = TrafficCounters(tmp_path / 'lib.db')
    traffic.add(2, DIRECTION_IN, 100)
    traffic.add(2, DIRECTION_OUT, 200)
    monkeypatch.setattr(api.state, 'traffic', traffic)
    monkeypatch.setattr(
        account_routes,
        'listing_for_request',
        lambda ctx: [
            {'file': 'a.mp3', 'size': 100},
            {'file': 'b.mp3', 'size': 200},
        ],
    )

    result = asyncio.run(account_routes.user_library_stats(_admin_request()))

    by_name = {row['username']: row for row in result['users']}
    assert by_name['maria']['tracks'] == 2
    assert by_name['maria']['bytes'] == 300
    assert by_name['maria']['likes'] == 1
    assert by_name['maria']['playlists'] == 2
    assert by_name['maria']['downloads'] == 2
    assert by_name['maria']['traffic_in'] == 100
    assert by_name['maria']['traffic_out'] == 200
    assert by_name['admin']['tracks'] == 1
    assert result['totals']['tracks'] == 2
    assert result['totals']['bytes'] == 300
    assert result['totals']['likes'] == 1
    assert result['totals']['traffic_in'] == 100


def _listen_request(name: str, user_id: int) -> Request:
    body = json.dumps({'artist': name, 'name': name}).encode()

    async def receive() -> dict[str, Any]:
        return {'type': 'http.request', 'body': body, 'more_body': False}

    return Request(
        {
            'type': 'http',
            'method': 'POST',
            'headers': [],
            'state': {'principal': _principal(user_id)},
        },
        receive,
    )
