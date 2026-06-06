"""Tests for playlist batch persistence and completeness helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from downtify.playlist_batches import (
    PlaylistBatchStore,
    active_queue_count_for_playlist,
    ensure_batch_records,
    split_tracks_by_library,
)
from downtify.track_index import TrackIndex


def test_batch_store_start_finish_and_list(tmp_path: Path) -> None:
    store = PlaylistBatchStore(tmp_path / 'lib.db')
    batch_id = store.start_batch(
        'playlist12345678901234567890',
        'My Mix',
        'https://open.spotify.com/playlist/playlist12345678901234567890',
        10,
    )
    store.update_batch_name(batch_id, 'Renamed Mix')
    store.finish_batch(batch_id, 6, 4, status='incomplete')

    open_rows = store.list_open_batches()
    assert len(open_rows) == 1
    assert open_rows[0]['playlist_name'] == 'Renamed Mix'
    assert open_rows[0]['succeeded_count'] == 6
    assert open_rows[0]['failed_count'] == 4
    assert open_rows[0]['status'] == 'incomplete'

    store.mark_complete(batch_id)
    assert store.list_open_batches() == []


def test_list_latest_batches_includes_complete(tmp_path: Path) -> None:
    store = PlaylistBatchStore(tmp_path / 'lib.db')
    open_id = store.start_batch(
        'openplaylist123456789012345',
        'Open',
        'https://open.spotify.com/playlist/openplaylist123456789012345',
        5,
    )
    store.finish_batch(open_id, 3, 2, status='incomplete')
    done_id = store.start_batch(
        'doneplaylist12345678901234',
        'Done',
        'https://open.spotify.com/playlist/doneplaylist12345678901234',
        10,
    )
    store.finish_batch(done_id, 10, 0, status='complete')

    latest = store.list_latest_batches()
    assert len(latest) == 2
    by_name = {row['playlist_name']: row['status'] for row in latest}
    assert by_name['Open'] == 'incomplete'
    assert by_name['Done'] == 'complete'


def test_ensure_batch_records_from_catalog_rows(tmp_path: Path) -> None:
    store = PlaylistBatchStore(tmp_path / 'lib.db')
    rows = [
        {
            'spotify_id': 'catalogonly123456789012345',
            'name': 'Catalog List',
            'url': 'https://open.spotify.com/playlist/catalogonly123456789012345',
            'track_count': 12,
        },
    ]
    created = ensure_batch_records(store, rows)
    assert created == 1
    assert ensure_batch_records(store, rows) == 0
    latest = store.list_latest_batches()
    assert len(latest) == 1
    assert latest[0]['spotify_playlist_id'] == 'catalogonly123456789012345'
    assert latest[0]['playlist_name'] == 'Catalog List'
    assert latest[0]['status'] == 'incomplete'


def test_split_tracks_by_library(tmp_path: Path) -> None:
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    track = download_dir / 'Artist - Song.mp3'
    track.write_bytes(b'audio')

    downloader = MagicMock()
    downloader.download_dir = str(download_dir)
    downloader.organize_by_artist = False

    index = TrackIndex(tmp_path / 'lib.db')
    index.register(
        '4uLU6hMCjMI75M1A2tKUQC', 'Artist - Song.mp3', full_path=track
    )

    songs = [
        {'song_id': '4uLU6hMCjMI75M1A2tKUQC', 'name': 'Song'},
        {'song_id': '1x00000000000000000000', 'name': 'Missing'},
    ]
    downloaded, missing = split_tracks_by_library(
        songs,
        downloader=downloader,
        track_index=index,
    )
    assert downloaded == 1
    assert len(missing) == 1
    assert missing[0]['song_id'] == '1x00000000000000000000'


def test_active_queue_count_for_playlist() -> None:
    sid = 'playlist12345678901234567890'
    url = f'https://open.spotify.com/playlist/{sid}'
    jobs = {
        'a': {
            'status': 'downloading',
            'song': {'downtify_playlist_url': url},
        },
        'b': {
            'status': 'done',
            'song': {'downtify_playlist_url': url},
        },
        'c': {
            'status': 'queued',
            'song': {
                'downtify_playlist_url': 'https://open.spotify.com/playlist/other'
            },
        },
    }
    assert active_queue_count_for_playlist(sid, jobs) == 1
