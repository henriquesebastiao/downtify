"""Global Spotify track deduplication index."""

from __future__ import annotations

from downtify.downloader import Downloader
from downtify.library_paths import library_stored_path
from downtify.track_index import (
    TrackIndex,
    normalize_spotify_track_id,
    resolve_existing_download,
)

SPOTIFY_ID = '4uLU6hMCjMI75M1A2tKUQC'


def test_normalize_spotify_track_id_from_song_id():
    assert normalize_spotify_track_id({'song_id': SPOTIFY_ID}) == SPOTIFY_ID


def test_normalize_spotify_track_id_from_uri():
    assert (
        normalize_spotify_track_id({'song_id': f'spotify:track:{SPOTIFY_ID}'})
        == SPOTIFY_ID
    )


def test_normalize_ignores_youtube_ids():
    assert normalize_spotify_track_id({'song_id': 'dQw4w9WgXcQ'}) is None


def test_resolve_existing_prefers_global_library(tmp_path):
    download_dir = tmp_path / 'music'
    download_dir.mkdir()
    slskd_dir = tmp_path / 'slskd'
    target = slskd_dir / 'Artist - Track.mp3'
    slskd_dir.mkdir(parents=True)
    target.write_bytes(b'x' * 100)

    stored = library_stored_path(target, download_dir, slskd_dir)
    index = TrackIndex(tmp_path / 'library.db')
    index.register(SPOTIFY_ID, stored)

    d = Downloader(
        download_dir,
        audio_format='mp3',
        audio_providers=['youtube'],
        slskd_settings={'source_dir': str(slskd_dir)},
    )
    song = {
        'song_id': SPOTIFY_ID,
        'name': 'Track',
        'artists': ['Artist'],
    }
    hit = resolve_existing_download(
        d,
        song,
        subdir='Playlist B',
        track_index=index,
    )
    assert hit is not None
    assert hit[1] == 'Already in library'
    assert hit[0] == stored


def test_register_updates_path_for_same_track(tmp_path):
    index = TrackIndex(tmp_path / 'library.db')
    first = tmp_path / 'first' / 'Artist - Song.mp3'
    second = tmp_path / 'second' / 'Artist - Song.mp3'
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_bytes(b'same')
    second.write_bytes(b'same')
    index.register(SPOTIFY_ID, 'first/path.mp3', full_path=first)
    index.register(SPOTIFY_ID, 'second/path.mp3', full_path=second)
    assert index.lookup(SPOTIFY_ID) == 'second/path.mp3'
