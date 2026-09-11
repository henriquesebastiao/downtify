"""Tests for Artist Watch: watching a YouTube Music artist's discography
and auto-downloading new releases (downtify/monitor.py:check_artist plus
the URL resolution in downtify/api.py).

All offline — the discography/tracklist providers and the downloader are
faked.
"""

from __future__ import annotations

import asyncio
import sqlite3

import pytest
from fastapi import HTTPException

from downtify import api, monitor

CHANNEL_ID = 'UCartist000000000000000'


def _album(album_id: str, name: str, year: str = '2026') -> dict:
    return {'album_id': album_id, 'name': name, 'year': year}


def _track(song_id: str, name: str, album: str, number: int) -> dict:
    return {
        'song_id': song_id,
        'name': name,
        'album_name': album,
        'track_number': number,
        'artists': ['Test Artist'],
        'source': 'youtube',
    }


class _FakeDownloader:
    organize_by_artist = False
    organize_by_album = False

    def __init__(self, tmp_path, *, fail_song_ids=frozenset()):
        self.download_dir = tmp_path
        self.fail_song_ids = fail_song_ids
        self.calls: list[str] = []

    def download(self, song, progress_cb=None, subdir=None):
        if song['song_id'] in self.fail_song_ids:
            raise RuntimeError('boom')
        self.calls.append(song['song_id'])
        return f'{song["song_id"]}.mp3'


def _db(tmp_path) -> monitor.PlaylistMonitorDB:
    return monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')


def _add_artist(db) -> monitor.MonitoredPlaylist:
    return db.add_playlist(
        CHANNEL_ID, 'Test Artist', 'url', 60, monitor.KIND_ARTIST
    )


def _patch_provider(monkeypatch, albums, tracks_by_album):
    monkeypatch.setattr(
        monitor.providers,
        'artist_albums_from_channel_id',
        lambda channel_id: albums,
    )
    monkeypatch.setattr(
        monitor.providers,
        'album_tracks_from_browse_id',
        lambda album_id: tracks_by_album.get(album_id, []),
    )


def _run_check(playlist, db, downloader, settings=None):
    async def _scenario():
        return await monitor.check_artist(
            playlist,
            db,
            downloader,
            _noop_broadcast,
            asyncio.get_running_loop(),
            settings=settings if settings is not None else {},
        )

    return asyncio.run(_scenario())


async def _noop_broadcast(_msg):
    return None


# ── check_artist ────────────────────────────────────────────────────────────


def test_downloads_every_track_of_a_new_release(monkeypatch, tmp_path):
    albums = [_album('AL1', 'First Album')]
    _patch_provider(
        monkeypatch,
        albums,
        {
            'AL1': [
                _track('t1', 'One', 'First Album', 1),
                _track('t2', 'Two', 'First Album', 2),
            ]
        },
    )
    db = _db(tmp_path)
    pl = _add_artist(db)
    dl = _FakeDownloader(tmp_path)

    assert _run_check(pl, db, dl) == 2
    assert dl.calls == ['t1', 't2']
    assert db.get_seen_album_ids(pl.id) == {'AL1'}


def test_second_sweep_downloads_nothing_new(monkeypatch, tmp_path):
    albums = [_album('AL1', 'First Album')]
    _patch_provider(
        monkeypatch, albums, {'AL1': [_track('t1', 'One', 'First Album', 1)]}
    )
    db = _db(tmp_path)
    pl = _add_artist(db)

    assert _run_check(pl, db, _FakeDownloader(tmp_path)) == 1
    second = _FakeDownloader(tmp_path)
    assert _run_check(pl, db, second) == 0
    assert second.calls == []


def test_only_the_new_release_is_downloaded(monkeypatch, tmp_path):
    tracks = {
        'AL1': [_track('t1', 'One', 'First Album', 1)],
        'AL2': [_track('t2', 'Two', 'Second Album', 1)],
    }
    _patch_provider(monkeypatch, [_album('AL1', 'First Album')], tracks)
    db = _db(tmp_path)
    pl = _add_artist(db)
    _run_check(pl, db, _FakeDownloader(tmp_path))

    # A new release shows up in the discography.
    _patch_provider(
        monkeypatch,
        [_album('AL2', 'Second Album'), _album('AL1', 'First Album')],
        tracks,
    )
    dl = _FakeDownloader(tmp_path)
    assert _run_check(pl, db, dl) == 1
    assert dl.calls == ['t2']
    assert db.get_seen_album_ids(pl.id) == {'AL1', 'AL2'}


def test_release_is_retried_when_a_track_fails(monkeypatch, tmp_path):
    albums = [_album('AL1', 'First Album')]
    _patch_provider(
        monkeypatch,
        albums,
        {
            'AL1': [
                _track('t1', 'One', 'First Album', 1),
                _track('t2', 'Two', 'First Album', 2),
            ]
        },
    )
    db = _db(tmp_path)
    pl = _add_artist(db)

    failing = _FakeDownloader(tmp_path, fail_song_ids={'t2'})
    assert _run_check(pl, db, failing) == 1
    # Not marked seen, so the next sweep retries it.
    assert db.get_seen_album_ids(pl.id) == set()

    retry = _FakeDownloader(tmp_path)
    assert _run_check(pl, db, retry) == 1
    # Only the track that failed is retried; the one that succeeded is
    # skipped via the per-track record.
    assert retry.calls == ['t2']
    assert db.get_seen_album_ids(pl.id) == {'AL1'}


def test_discography_failure_returns_zero_and_marks_checked(
    monkeypatch, tmp_path
):
    def _boom(channel_id):
        raise RuntimeError('network down')

    monkeypatch.setattr(
        monitor.providers, 'artist_albums_from_channel_id', _boom
    )
    db = _db(tmp_path)
    pl = _add_artist(db)

    assert _run_check(pl, db, _FakeDownloader(tmp_path)) == 0
    assert db.get_playlist(pl.id).last_checked is not None


def test_tracklist_failure_skips_only_that_release(monkeypatch, tmp_path):
    monkeypatch.setattr(
        monitor.providers,
        'artist_albums_from_channel_id',
        lambda channel_id: [_album('BAD', 'Broken'), _album('AL1', 'Good')],
    )

    def _tracks(album_id):
        if album_id == 'BAD':
            raise RuntimeError('boom')
        return [_track('t1', 'One', 'Good', 1)]

    monkeypatch.setattr(
        monitor.providers, 'album_tracks_from_browse_id', _tracks
    )
    db = _db(tmp_path)
    pl = _add_artist(db)
    dl = _FakeDownloader(tmp_path)

    assert _run_check(pl, db, dl) == 1
    assert dl.calls == ['t1']
    assert db.get_seen_album_ids(pl.id) == {'AL1'}


def test_delay_between_tracks_is_respected(monkeypatch, tmp_path):
    _patch_provider(
        monkeypatch,
        [_album('AL1', 'First Album')],
        {
            'AL1': [
                _track('t1', 'One', 'First Album', 1),
                _track('t2', 'Two', 'First Album', 2),
            ]
        },
    )
    sleeps = []

    async def _fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(monitor.asyncio, 'sleep', _fake_sleep)
    db = _db(tmp_path)
    pl = _add_artist(db)

    _run_check(
        pl, db, _FakeDownloader(tmp_path), {'download_delay_seconds': 9}
    )
    assert sleeps == [9, 9]


def test_last_track_count_tracks_release_count(monkeypatch, tmp_path):
    _patch_provider(
        monkeypatch,
        [_album('AL1', 'A'), _album('AL2', 'B')],
        {'AL1': [], 'AL2': []},
    )
    db = _db(tmp_path)
    pl = _add_artist(db)
    _run_check(pl, db, _FakeDownloader(tmp_path))
    assert db.get_playlist(pl.id).last_track_count == 2


# ── schema / migration ──────────────────────────────────────────────────────


def test_playlist_watches_default_to_playlist_kind(tmp_path):
    db = _db(tmp_path)
    pl = db.add_playlist('spotifyid', 'A Playlist', 'url', 60)
    assert pl.kind == monitor.KIND_PLAYLIST


def test_existing_database_without_kind_column_is_migrated(tmp_path):
    """A database created before Artist Watch must keep working, with its
    existing rows treated as playlist watches."""
    path = tmp_path / 'old.db'
    conn = sqlite3.connect(path)
    conn.executescript("""
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
        );
    """)
    conn.execute(
        'INSERT INTO monitored_playlists '
        '(spotify_id, name, url, interval_minutes, enabled, created_at) '
        "VALUES ('old1', 'Legacy', 'url', 60, 1, '2026-01-01T00:00:00+00:00')"
    )
    conn.commit()
    conn.close()

    db = monitor.PlaylistMonitorDB(path)
    rows = db.list_playlists()
    assert [r.name for r in rows] == ['Legacy']
    assert rows[0].kind == monitor.KIND_PLAYLIST
    # And the new tables/columns are usable afterwards.
    artist = db.add_playlist('c1', 'Artist', 'u', 60, monitor.KIND_ARTIST)
    db.mark_album_seen(artist.id, 'AL1', 'Album')
    assert db.get_seen_album_ids(artist.id) == {'AL1'}


def test_seen_albums_are_scoped_per_watch(tmp_path):
    db = _db(tmp_path)
    a = db.add_playlist('c1', 'A', 'u', 60, monitor.KIND_ARTIST)
    b = db.add_playlist('c2', 'B', 'u', 60, monitor.KIND_ARTIST)
    db.mark_album_seen(a.id, 'AL1')
    assert db.get_seen_album_ids(a.id) == {'AL1'}
    assert db.get_seen_album_ids(b.id) == set()


# ── URL resolution (api._resolve_watch_target) ──────────────────────────────


def _resolve(url):
    return asyncio.run(api._resolve_watch_target(url))


def test_resolve_spotify_artist_url_maps_to_youtube_channel(monkeypatch):
    monkeypatch.setattr(
        api.spotify, 'artist_name_from_id', lambda artist_id: 'Test Artist'
    )
    monkeypatch.setattr(
        api.providers,
        'search_artists',
        lambda query, limit: [
            {'name': 'Test Artist Tribute', 'artist_id': 'UCwrong'},
            {'name': 'Test Artist', 'artist_id': CHANNEL_ID},
        ],
    )
    kind, key, name = _resolve(
        'https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg'
    )
    assert kind == monitor.KIND_ARTIST
    # An exact name match wins over a higher-ranked near-match.
    assert key == CHANNEL_ID
    assert name == 'Test Artist'


def test_resolve_spotify_artist_falls_back_to_first_result(monkeypatch):
    monkeypatch.setattr(
        api.spotify, 'artist_name_from_id', lambda artist_id: 'Test Artist'
    )
    monkeypatch.setattr(
        api.providers,
        'search_artists',
        lambda query, limit: [
            {'name': 'Close Enough', 'artist_id': 'UCfirst'}
        ],
    )
    _kind, key, name = _resolve(
        'https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg'
    )
    assert key == 'UCfirst'
    assert name == 'Close Enough'


def test_resolve_spotify_artist_with_no_match_is_404(monkeypatch):
    monkeypatch.setattr(
        api.spotify, 'artist_name_from_id', lambda artist_id: 'Nobody'
    )
    monkeypatch.setattr(
        api.providers, 'search_artists', lambda query, limit: []
    )
    with pytest.raises(HTTPException) as exc:
        _resolve('https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg')
    assert exc.value.status_code == 404


def test_resolve_youtube_artist_url(monkeypatch):
    monkeypatch.setattr(
        api.providers, 'parse_youtube_url', lambda url: ('artist', CHANNEL_ID)
    )
    monkeypatch.setattr(
        api.providers,
        'artist_info_from_channel_id',
        lambda channel_id: {'name': 'Test Artist'},
    )
    kind, key, name = _resolve(
        f'https://music.youtube.com/channel/{CHANNEL_ID}'
    )
    assert (kind, key, name) == (
        monitor.KIND_ARTIST,
        CHANNEL_ID,
        'Test Artist',
    )


def test_resolve_spotify_playlist_url_still_works(monkeypatch):
    monkeypatch.setattr(
        api.spotify,
        'playlist_info_and_tracks',
        lambda pid: ('My Playlist', []),
    )
    kind, key, name = _resolve(
        'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M'
    )
    assert kind == monitor.KIND_PLAYLIST
    assert key == '37i9dQZF1DXcBWIGoYBM5M'
    assert name == 'My Playlist'


def test_resolve_rejects_unsupported_url(monkeypatch):
    monkeypatch.setattr(api.providers, 'parse_youtube_url', lambda url: None)
    with pytest.raises(HTTPException) as exc:
        _resolve('https://example.com/not-music')
    assert exc.value.status_code == 400


def test_resolve_rejects_spotify_track_url(monkeypatch):
    monkeypatch.setattr(api.providers, 'parse_youtube_url', lambda url: None)
    with pytest.raises(HTTPException) as exc:
        _resolve('https://open.spotify.com/track/3C0nOe05EIt1390bVABLyN')
    assert exc.value.status_code == 400


# ── monitor_loop dispatch ───────────────────────────────────────────────────


def test_monitor_loop_uses_check_artist_for_artist_watches(
    monkeypatch, tmp_path
):
    db = _db(tmp_path)
    db.add_playlist('c1', 'Artist', 'u', 60, monitor.KIND_ARTIST)
    db.add_playlist('p1', 'Playlist', 'u', 60, monitor.KIND_PLAYLIST)

    called: list[str] = []

    async def _fake_artist(pl, *a, **kw):
        called.append(f'artist:{pl.name}')
        return 0

    async def _fake_playlist(pl, *a, **kw):
        called.append(f'playlist:{pl.name}')
        return 0

    monkeypatch.setattr(monitor, 'check_artist', _fake_artist)
    monkeypatch.setattr(monitor, 'check_playlist', _fake_playlist)

    # Break out of the endless loop after the first sweep.
    class _Stop(Exception):
        pass

    async def _stop(_seconds):
        raise _Stop

    monkeypatch.setattr(monitor.asyncio, 'sleep', _stop)

    async def _scenario():
        with pytest.raises(_Stop):
            await monitor.monitor_loop(
                db,
                lambda: _FakeDownloader(tmp_path),
                _noop_broadcast,
                asyncio.get_running_loop(),
                {},
            )

    asyncio.run(_scenario())
    assert sorted(called) == ['artist:Artist', 'playlist:Playlist']
