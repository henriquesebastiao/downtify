"""Batch/URL downloads skip tracks that already exist on disk."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from downtify import api
from downtify.downloader import Downloader
from downtify.track_index import TrackIndex

SPOTIFY_ID = '4uLU6hMCjMI75M1A2tKUQC'


def _run_download(coro):
    loop = asyncio.new_event_loop()
    try:
        api.state.loop = loop
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_run_download_skips_when_matching_file_exists(tmp_path):
    download_dir = tmp_path / 'music'
    d = Downloader(
        download_dir,
        audio_format='mp3',
        audio_providers=['youtube'],
    )
    song = {'name': 'Track', 'artists': ['Artist']}
    target = download_dir / 'Artist - Track.mp3'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b'fake')

    d.download = MagicMock(side_effect=AssertionError('must not download'))

    prev_downloader = api.state.downloader
    prev_loop = api.state.loop
    prev_connections = api.state.connections
    try:
        api.state.downloader = d
        api.state.connections = MagicMock()
        api.state.connections.broadcast = AsyncMock()
        song_id = api._register_job(song, status='queued')

        filename = _run_download(api._run_download(song, song_id))

        assert filename == 'Artist - Track.mp3'
        assert api.state.download_jobs[song_id]['status'] == 'done'
        assert api.state.download_jobs[song_id]['message'] == 'Already on disk'
        d.download.assert_not_called()
    finally:
        api.state.download_jobs.clear()
        api.state.downloader = prev_downloader
        api.state.loop = prev_loop
        api.state.connections = prev_connections


def test_run_download_skips_via_global_library(tmp_path):
    download_dir = tmp_path / 'music'
    d = Downloader(
        download_dir,
        audio_format='mp3',
        audio_providers=['youtube'],
    )
    other = download_dir / 'Other Playlist' / 'Artist - Track.mp3'
    other.parent.mkdir(parents=True)
    other.write_bytes(b'x' * 100)

    library = TrackIndex(tmp_path / 'library.db')
    library.register(SPOTIFY_ID, 'Other Playlist/Artist - Track.mp3')

    d.download = MagicMock(side_effect=AssertionError('must not download'))

    prev_downloader = api.state.downloader
    prev_loop = api.state.loop
    prev_connections = api.state.connections
    prev_index = api.state.track_index
    try:
        api.state.downloader = d
        api.state.track_index = library
        api.state.connections = MagicMock()
        api.state.connections.broadcast = AsyncMock()
        song = {
            'song_id': SPOTIFY_ID,
            'name': 'Track',
            'artists': ['Artist'],
        }
        song_id = api._register_job(song, status='queued')

        filename = _run_download(
            api._run_download(song, song_id, subdir='New Playlist')
        )

        assert filename == 'Other Playlist/Artist - Track.mp3'
        assert (
            api.state.download_jobs[song_id]['message'] == 'Already in library'
        )
        d.download.assert_not_called()
    finally:
        api.state.download_jobs.clear()
        api.state.downloader = prev_downloader
        api.state.loop = prev_loop
        api.state.connections = prev_connections
        api.state.track_index = prev_index


def test_run_download_skips_in_playlist_subdir(tmp_path):
    download_dir = tmp_path / 'music'
    d = Downloader(
        download_dir,
        audio_format='mp3',
        audio_providers=['youtube'],
    )
    song = {'name': 'Track', 'artists': ['Artist']}
    pl_dir = download_dir / 'My Playlist'
    target = pl_dir / 'Artist - Track.mp3'
    pl_dir.mkdir(parents=True)
    target.write_bytes(b'fake')

    d.download = MagicMock(side_effect=AssertionError('must not download'))

    prev_downloader = api.state.downloader
    prev_loop = api.state.loop
    prev_connections = api.state.connections
    try:
        api.state.downloader = d
        api.state.connections = MagicMock()
        api.state.connections.broadcast = AsyncMock()
        song_id = api._register_job(song, status='queued')

        filename = _run_download(
            api._run_download(song, song_id, subdir='My Playlist')
        )

        assert filename == 'My Playlist/Artist - Track.mp3'
        d.download.assert_not_called()
    finally:
        api.state.downloader = prev_downloader
        api.state.loop = prev_loop
        api.state.connections = prev_connections
        api.state.download_jobs.clear()
