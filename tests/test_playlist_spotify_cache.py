"""Spotify playlist track cache."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from downtify.playlist_spotify_cache import (
    PlaylistSpotifyCache,
    fetch_playlist_tracks,
    fetch_track_metadata,
)


def test_cache_store_and_get(tmp_path: Path) -> None:
    cache = PlaylistSpotifyCache(tmp_path / 'lib.db')
    tracks = [
        {
            'song_id': '4uLU6hMCjMI75M1A2tKUQC',
            'name': 'Song',
            'artists': ['Artist'],
        },
    ]
    cache.store('playlist12345678901234567890', 'My Mix', tracks)
    hit = cache.get('playlist12345678901234567890')
    assert hit is not None
    name, rows = hit
    assert name == 'My Mix'
    assert len(rows) == 1
    assert rows[0]['song_id'] == '4uLU6hMCjMI75M1A2tKUQC'
    assert cache.track_count('playlist12345678901234567890') == 1


def test_fetch_playlist_tracks_uses_cache(tmp_path: Path) -> None:
    cache = PlaylistSpotifyCache(tmp_path / 'lib.db')
    sid = 'playlist12345678901234567890'
    cache.store(
        sid,
        'Cached',
        [{'song_id': '4uLU6hMCjMI75M1A2tKUQC', 'name': 'Song'}],
    )
    with patch(
        'downtify.playlist_spotify_cache.spotify.playlist_info_and_tracks'
    ) as mock_fetch:
        name, tracks = fetch_playlist_tracks(sid, cache=cache)
        mock_fetch.assert_not_called()
    assert name == 'Cached'
    assert len(tracks) == 1


def test_fetch_playlist_tracks_refresh_bypasses_cache(tmp_path: Path) -> None:
    cache = PlaylistSpotifyCache(tmp_path / 'lib.db')
    sid = 'playlist12345678901234567890'
    cache.store(sid, 'Old', [])
    fresh = [{'song_id': '1x00000000000000000000', 'name': 'New'}]
    with patch(
        'downtify.playlist_spotify_cache.spotify.playlist_info_and_tracks',
        return_value=('Fresh', fresh),
    ):
        name, tracks = fetch_playlist_tracks(sid, cache=cache, refresh=True)
    assert name == 'Fresh'
    assert tracks == fresh
    hit = cache.get(sid)
    assert hit is not None
    assert hit[0] == 'Fresh'
    assert len(hit[1]) == 1


def test_store_indexes_tracks_for_lookup(tmp_path: Path) -> None:
    cache = PlaylistSpotifyCache(tmp_path / 'lib.db')
    sid = 'playlist12345678901234567890'
    tid = '4uLU6hMCjMI75M1A2tKUQC'
    cache.store(
        sid,
        'Mix',
        [{'song_id': tid, 'name': 'Song', 'artists': ['Artist']}],
    )
    assert cache.get_playlist_track(sid, tid) is not None
    assert cache.find_track_in_playlists(tid) is not None
    assert cache.playlists_for_track(tid) == [sid]
    assert cache.list_playlists()[0]['track_count'] == 1


def test_store_allows_duplicate_track_ids(tmp_path: Path) -> None:
    cache = PlaylistSpotifyCache(tmp_path / 'lib.db')
    sid = 'playlist12345678901234567890'
    tid = '4uLU6hMCjMI75M1A2tKUQC'
    tracks = [
        {'song_id': tid, 'name': 'Song', 'artists': ['Artist']},
        {'song_id': tid, 'name': 'Song', 'artists': ['Artist']},
    ]
    cache.store(sid, 'Dupes', tracks)
    assert cache.track_count(sid) == 2
    hit = cache.get(sid)
    assert hit is not None
    assert len(hit[1]) == 2


def test_fetch_track_metadata_uses_playlist_cache(tmp_path: Path) -> None:
    cache = PlaylistSpotifyCache(tmp_path / 'lib.db')
    sid = 'playlist12345678901234567890'
    tid = '4uLU6hMCjMI75M1A2tKUQC'
    cache.store(sid, 'Mix', [{'song_id': tid, 'name': 'Cached Song'}])
    with patch(
        'downtify.playlist_spotify_cache.spotify.track_from_id'
    ) as mock_fetch:
        track = fetch_track_metadata(tid, cache=cache, playlist_id=sid)
        mock_fetch.assert_not_called()
    assert track['name'] == 'Cached Song'
