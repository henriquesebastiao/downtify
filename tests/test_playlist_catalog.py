"""Tests for playlist catalog."""

from __future__ import annotations

from pathlib import Path

from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import normalize_spotify_track_id


def test_replace_and_list_tracks(tmp_path: Path) -> None:
    catalog = PlaylistCatalog(tmp_path / 'lib.db')
    track = tmp_path / 'Artist - Song.mp3'
    track.write_bytes(b'audio')
    song = {'song_id': '4uLU6hMCjMI75M1A2tKUQC', 'name': 'Song'}
    catalog.replace_playlist_tracks(
        'My List',
        [(song, 'Artist - Song.mp3', track)],
        spotify_id='playlist12345678901234567890',
    )
    rows = catalog.list_tracks('My List')
    assert len(rows) == 1
    assert rows[0]['filename'] == 'Artist - Song.mp3'
    assert normalize_spotify_track_id(song) == rows[0]['track_spotify_id']


def test_update_filename_by_content_key(tmp_path: Path) -> None:
    track = tmp_path / 't.mp3'
    track.write_bytes(b'12345')
    catalog = PlaylistCatalog(tmp_path / 'lib.db')
    song = {'song_id': '4uLU6hMCjMI75M1A2tKUQC'}
    catalog.upsert_track('Pl', song, 'old/t.mp3', track)
    ck = catalog.list_tracks('Pl')[0]['content_key']
    assert ck
    names = catalog.update_filename_by_content_key(ck, 'new/t.mp3')
    assert 'Pl' in names
    assert catalog.list_tracks('Pl')[0]['filename'] == 'new/t.mp3'
