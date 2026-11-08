"""Playlist M3U/Navidrome refresh after single-track and retry downloads."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

from downtify import api
from downtify.downloader import Downloader
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import normalize_spotify_track_id
from downtify.track_owners import TrackOwners


def test_playlists_for_track_returns_distinct_playlists(
    tmp_path: Path,
) -> None:
    catalog = PlaylistCatalog(tmp_path / 'lib.db')
    track = tmp_path / 'song.mp3'
    track.write_bytes(b'x')
    tid = '4uLU6hMCjMI75M1A2tKUQC'
    song = {'song_id': tid, 'name': 'Song'}
    catalog.upsert_track('List A', song, 'song.mp3', track)
    catalog.upsert_track('List B', song, 'song.mp3', track)
    assert catalog.playlists_for_track(tid) == ['List A', 'List B']


def test_playlist_context_from_url_hint_resolves_name() -> None:
    api.state.downloader = MagicMock()
    api.state.downloader.organize_by_artist = False
    api.state.downloader.organize_by_album = False
    api.state.settings = {'organize_by_artist': False}
    with patch(
        'downtify.api.spotify.playlist_info_and_tracks',
        return_value=('Summer Hits', []),
    ):
        ctx = api._playlist_context_from_hints({
            'downtify_playlist_url': (
                'https://open.spotify.com/playlist/abc123'
            ),
            'downtify_track_order': 3,
        })
    assert ctx['playlist_name'] == 'Summer Hits'
    assert ctx['spotify_playlist_id'] == 'abc123'
    assert ctx['track_order'] == 3
    assert ctx['subdir'] == 'Summer Hits'


def test_playlists_for_successful_download_merges_catalog_and_primary() -> (
    None
):
    api.state.playlist_catalog = MagicMock()
    api.state.monitor_db = MagicMock()
    api.state.playlist_catalog.playlists_for_track.return_value = ['Other']
    api.state.monitor_db.playlists_for_track.return_value = {'Monitored'}
    tid = '4uLU6hMCjMI75M1A2tKUQC'
    names = api._playlists_for_successful_download(
        {'song_id': tid},
        primary_playlist='Batch List',
    )
    assert names == {'Batch List', 'Other', 'Monitored'}


def test_register_download_playlists_updates_monitor_and_catalog(
    tmp_path: Path,
) -> None:
    dl_dir = tmp_path / 'downloads'
    dl_dir.mkdir()
    audio = dl_dir / 'Artist - Song.mp3'
    audio.write_bytes(b'mp3')
    catalog = PlaylistCatalog(tmp_path / 'catalog.db')
    track_index = MagicMock()
    monitor_db = MagicMock()
    monitor_db.playlists_for_track.return_value = set()

    api.state.downloader = MagicMock()
    api.state.downloader.download_dir = str(dl_dir)
    api.state.playlist_catalog = catalog
    api.state.track_index = track_index
    api.state.monitor_db = monitor_db

    song = {
        'song_id': '4uLU6hMCjMI75M1A2tKUQC',
        'name': 'Song',
        'artists': ['Artist'],
    }
    affected = api._register_download_playlists_on_disk(
        song,
        'Artist - Song.mp3',
        playlist_name='My Playlist',
        spotify_playlist_id='playlist12345678901234567890',
        track_order=2,
    )
    assert 'My Playlist' in affected
    rows = catalog.list_tracks('My Playlist')
    assert len(rows) == 1
    assert rows[0]['track_order'] == 2
    tid = normalize_spotify_track_id(song)
    monitor_db.update_filename_for_spotify.assert_called_once_with(
        tid, 'Artist - Song.mp3'
    )
    track_index.register_song.assert_called_once()


def test_a_failing_playlist_store_never_hides_the_download(
    monkeypatch, tmp_path: Path
) -> None:
    """Ownership is claimed before (and independently of) the bookkeeping.

    A store refusing writes (sqlite locked under parallel downloads)
    used to abort the whole registration while the job reported done:
    the file was on disk and nobody owned it, so the account that
    ordered it never saw it in their library.
    """

    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    (downloads / 'Artist - Song.mp3').write_bytes(b'audio')
    monkeypatch.setattr(
        api.state,
        'downloader',
        Downloader(download_dir=downloads, audio_format='mp3'),
    )
    owners = TrackOwners(tmp_path / 'lib.db')
    monkeypatch.setattr(api.state, 'track_owners', owners)
    catalog = MagicMock()
    catalog.playlists_for_track.side_effect = RuntimeError(
        'database is locked'
    )
    monkeypatch.setattr(api.state, 'playlist_catalog', catalog)
    monkeypatch.setattr(api.state, 'monitor_db', None)
    monkeypatch.setattr(api.state, 'track_index', None)
    monkeypatch.setattr(api.state, 'settings', {})

    song = {
        'song_id': '4uLU6hMCjMI75M1A2tKUQC',
        'name': 'Song',
        'artists': ['Artist'],
    }
    asyncio.run(
        api._record_finished_download(
            song,
            'Artist - Song.mp3',
            playlist_name='My Playlist',
            spotify_playlist_id=None,
            track_order=0,
            refresh_playlists=True,
            user_id=5,
        )
    )

    assert len(owners.owned_keys(5)) == 1
    assert (downloads / 'Artist - Song.mp3').is_file()
