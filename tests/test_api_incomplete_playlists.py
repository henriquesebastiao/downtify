"""Incomplete playlist reporting."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from downtify import api
from downtify.playlist_batches import (
    PlaylistBatchStore,
    split_tracks_by_library,
)
from downtify.playlist_catalog import PlaylistCatalog
from downtify.playlist_spotify_cache import PlaylistSpotifyCache
from downtify.track_index import TrackIndex


def test_build_incomplete_playlist_reports_marks_complete(
    tmp_path: Path,
) -> None:
    db = tmp_path / 'lib.db'
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()

    store = PlaylistBatchStore(db)
    batch_id = store.start_batch(
        'playlist12345678901234567890',
        'Test List',
        'https://open.spotify.com/playlist/playlist12345678901234567890',
        1,
    )
    store.finish_batch(batch_id, 0, 1, status='incomplete')

    track = download_dir / 'Artist - Song.mp3'
    track.write_bytes(b'audio')
    index = TrackIndex(db)
    index.register(
        '4uLU6hMCjMI75M1A2tKUQC', 'Artist - Song.mp3', full_path=track
    )

    downloader = MagicMock()
    downloader.download_dir = str(download_dir)
    downloader.organize_by_artist = False

    spotify_tracks = [
        {'song_id': '4uLU6hMCjMI75M1A2tKUQC', 'name': 'Song'},
    ]

    api.state.playlist_batch_store = store
    api.state.track_index = index
    api.state.downloader = downloader
    api.state.download_jobs = {}

    try:
        with patch(
            'downtify.api.spotify.playlist_info_and_tracks',
            return_value=('Test List', spotify_tracks),
        ):
            reports = api._build_incomplete_playlist_reports(
                include_tracks=True,
            )
        assert reports == []
        assert store.list_open_batches() == []
    finally:
        api.state.playlist_batch_store = None
        api.state.track_index = None
        api.state.downloader = None
        api.state.download_jobs.clear()


def test_build_incomplete_playlist_reports_summary_skips_spotify(
    tmp_path: Path,
) -> None:
    db = tmp_path / 'lib.db'
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()

    store = PlaylistBatchStore(db)
    batch_id = store.start_batch(
        'playlist12345678901234567890',
        'Test List',
        'https://open.spotify.com/playlist/playlist12345678901234567890',
        2,
    )
    store.finish_batch(batch_id, 1, 1, status='incomplete')

    cache = PlaylistSpotifyCache(db)
    cache.store(
        'playlist12345678901234567890',
        'Test List',
        [
            {'song_id': '4uLU6hMCjMI75M1A2tKUQC', 'name': 'Have'},
            {'song_id': '1x00000000000000000000', 'name': 'Need'},
        ],
    )

    index = TrackIndex(db)
    downloader = MagicMock()
    downloader.download_dir = str(download_dir)
    downloader.organize_by_artist = False

    api.state.playlist_batch_store = store
    api.state.playlist_spotify_cache = cache
    api.state.track_index = index
    api.state.downloader = downloader
    api.state.download_jobs = {}

    try:
        with patch(
            'downtify.api.spotify.playlist_info_and_tracks',
        ) as mock_fetch:
            reports = api._build_incomplete_playlist_reports()
            mock_fetch.assert_not_called()
        assert len(reports) == 1
        row = reports[0]
        assert row['expected_count'] == 2
        assert row['downloaded_count'] == 0
        assert row['missing_count'] == 2
        assert row['missing_tracks'] == []
        assert row['status'] == 'incomplete'
        assert row['source'] == 'cache'
    finally:
        api.state.playlist_batch_store = None
        api.state.playlist_spotify_cache = None
        api.state.track_index = None
        api.state.downloader = None
        api.state.download_jobs.clear()


def test_report_for_spotify_playlist_includes_missing_tracks(
    tmp_path: Path,
) -> None:
    db = tmp_path / 'lib.db'
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()

    store = PlaylistBatchStore(db)
    batch_id = store.start_batch(
        'playlist12345678901234567890',
        'Test List',
        'https://open.spotify.com/playlist/playlist12345678901234567890',
        2,
    )
    store.finish_batch(batch_id, 1, 1, status='incomplete')

    index = TrackIndex(db)
    downloader = MagicMock()
    downloader.download_dir = str(download_dir)
    downloader.organize_by_artist = False

    spotify_tracks = [
        {'song_id': '4uLU6hMCjMI75M1A2tKUQC', 'name': 'Have'},
        {'song_id': '1x00000000000000000000', 'name': 'Need'},
    ]

    api.state.playlist_batch_store = store
    api.state.track_index = index
    api.state.downloader = downloader
    api.state.download_jobs = {}

    try:
        with patch(
            'downtify.api.spotify.playlist_info_and_tracks',
            return_value=('Test List', spotify_tracks),
        ):
            row = api._report_for_spotify_playlist(
                'playlist12345678901234567890',
                mode='spotify',
            )
        assert row is not None
        assert row['downloaded_count'] == 0
        assert row['missing_count'] == 2
        assert len(row['missing_tracks']) == 2
    finally:
        api.state.playlist_batch_store = None
        api.state.track_index = None
        api.state.downloader = None
        api.state.download_jobs.clear()


def test_report_for_spotify_playlist_counts_only(
    tmp_path: Path,
) -> None:
    db = tmp_path / 'lib.db'
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()

    store = PlaylistBatchStore(db)
    batch_id = store.start_batch(
        'playlist12345678901234567890',
        'Test List',
        'https://open.spotify.com/playlist/playlist12345678901234567890',
        2,
    )
    store.finish_batch(batch_id, 1, 1, status='incomplete')

    index = TrackIndex(db)
    downloader = MagicMock()
    downloader.download_dir = str(download_dir)
    downloader.organize_by_artist = False

    spotify_tracks = [
        {'song_id': '4uLU6hMCjMI75M1A2tKUQC', 'name': 'Have'},
        {'song_id': '1x00000000000000000000', 'name': 'Need'},
    ]

    api.state.playlist_batch_store = store
    api.state.track_index = index
    api.state.downloader = downloader
    api.state.download_jobs = {}

    try:
        with patch(
            'downtify.api.spotify.playlist_info_and_tracks',
            return_value=('Test List', spotify_tracks),
        ):
            row = api._report_for_spotify_playlist(
                'playlist12345678901234567890',
                mode='spotify',
                include_missing_tracks=False,
            )
        assert row is not None
        assert row['missing_count'] == 2
        assert row['missing_tracks'] == []
        assert row['source'] == 'spotify'
    finally:
        api.state.playlist_batch_store = None
        api.state.track_index = None
        api.state.downloader = None
        api.state.download_jobs.clear()


def test_build_playlist_batch_reports_from_catalog_only(
    tmp_path: Path,
) -> None:
    db = tmp_path / 'lib.db'
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()

    catalog = PlaylistCatalog(db)
    catalog.replace_playlist_tracks(
        'My Saved List',
        [],
        spotify_id='catalogonly123456789012345',
    )

    index = TrackIndex(db)
    downloader = MagicMock()
    downloader.download_dir = str(download_dir)
    downloader.organize_by_artist = False

    api.state.playlist_batch_store = PlaylistBatchStore(db)
    api.state.playlist_catalog = catalog
    api.state.playlist_spotify_cache = PlaylistSpotifyCache(db)
    api.state.track_index = index
    api.state.downloader = downloader
    api.state.monitor_db = None
    api.state.download_jobs = {}

    try:
        with patch(
            'downtify.api.spotify.playlist_info_and_tracks',
        ) as mock_fetch:
            rows = api._build_playlist_batch_reports()
            mock_fetch.assert_not_called()
        assert len(rows) == 1
        assert rows[0]['spotify_playlist_id'] == 'catalogonly123456789012345'
        assert rows[0]['playlist_name'] == 'My Saved List'
        assert rows[0]['source'] == 'pending'
        assert rows[0]['status'] == 'pending'
    finally:
        api.state.playlist_batch_store = None
        api.state.playlist_catalog = None
        api.state.playlist_spotify_cache = None
        api.state.track_index = None
        api.state.downloader = None
        api.state.download_jobs.clear()


def test_build_playlist_batch_reports_includes_complete(
    tmp_path: Path,
) -> None:
    db = tmp_path / 'lib.db'
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()

    store = PlaylistBatchStore(db)
    batch_id = store.start_batch(
        'doneplaylist12345678901234',
        'Done List',
        'https://open.spotify.com/playlist/doneplaylist12345678901234',
        1,
    )
    store.finish_batch(batch_id, 1, 0, status='complete')

    track = download_dir / 'Artist - Song.mp3'
    track.write_bytes(b'audio')
    index = TrackIndex(db)
    index.register(
        '4uLU6hMCjMI75M1A2tKUQC', 'Artist - Song.mp3', full_path=track
    )
    cache = PlaylistSpotifyCache(db)
    cache.store(
        'doneplaylist12345678901234',
        'Done List',
        [{'song_id': '4uLU6hMCjMI75M1A2tKUQC', 'name': 'Song'}],
    )

    downloader = MagicMock()
    downloader.download_dir = str(download_dir)
    downloader.organize_by_artist = False

    api.state.playlist_batch_store = store
    api.state.playlist_spotify_cache = cache
    api.state.track_index = index
    api.state.downloader = downloader
    api.state.download_jobs = {}

    try:
        with patch(
            'downtify.api.spotify.playlist_info_and_tracks',
        ) as mock_fetch:
            all_rows = api._build_playlist_batch_reports()
            open_rows = api._build_incomplete_playlist_reports()
            mock_fetch.assert_not_called()
        assert len(all_rows) == 1
        assert all_rows[0]['status'] == 'complete'
        assert all_rows[0]['missing_count'] == 0
        assert all_rows[0]['source'] == 'cache'
        assert open_rows == []
    finally:
        api.state.playlist_batch_store = None
        api.state.playlist_spotify_cache = None
        api.state.track_index = None
        api.state.downloader = None
        api.state.download_jobs.clear()


def test_playlist_batch_summary_complete_from_catalog_counts(
    tmp_path: Path,
) -> None:
    db = tmp_path / 'lib.db'
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    sid = 'stalebatch1234567890123456'

    store = PlaylistBatchStore(db)
    batch_id = store.start_batch(
        sid,
        'Full List',
        f'https://open.spotify.com/playlist/{sid}',
        108,
    )
    store.finish_batch(batch_id, 0, 0, status='incomplete')

    catalog = PlaylistCatalog(db)
    index = TrackIndex(db)
    rows = []
    for i in range(108):
        track_id = f'1{i:021x}'
        path = download_dir / f'Artist - Song {i}.mp3'
        path.write_bytes(b'audio')
        rows.append(({'song_id': track_id}, str(path.name), path))
        index.register(track_id, str(path.name), full_path=path)
    catalog.replace_playlist_tracks('Full List', rows, spotify_id=sid)

    cache = PlaylistSpotifyCache(db)
    cache.store(
        sid,
        'Full List',
        [song for song, _, _ in rows],
    )

    downloader = MagicMock()
    downloader.download_dir = str(download_dir)
    downloader.organize_by_artist = False

    api.state.playlist_batch_store = store
    api.state.playlist_catalog = catalog
    api.state.playlist_spotify_cache = cache
    api.state.track_index = index
    api.state.downloader = downloader
    api.state.download_jobs = {}

    try:
        with patch(
            'downtify.api.spotify.playlist_info_and_tracks'
        ) as mock_fetch:
            row = api._playlist_batch_summary(
                sid,
                'Full List',
                f'https://open.spotify.com/playlist/{sid}',
                batch=store.get_batch(batch_id),
                expected_hint=108,
            )
            mock_fetch.assert_not_called()
        assert row['downloaded_count'] == 108
        assert row['missing_count'] == 0
        assert row['status'] == 'complete'
        assert row['source'] == 'cache'
        assert store.get_batch(batch_id)['status'] == 'complete'
    finally:
        api.state.playlist_batch_store = None
        api.state.playlist_catalog = None
        api.state.playlist_spotify_cache = None
        api.state.track_index = None
        api.state.downloader = None
        api.state.download_jobs.clear()


def test_split_tracks_by_library_uses_playlist_catalog(
    tmp_path: Path,
) -> None:
    db = tmp_path / 'lib.db'
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    sid = 'catalogsplit12345678901234'
    tid = '4uLU6hMCjMI75M1A2tKUQC'
    path = download_dir / 'Artist - Song.mp3'
    path.write_bytes(b'audio')

    catalog = PlaylistCatalog(db)
    catalog.replace_playlist_tracks(
        'House Classics',
        [({'song_id': tid}, str(path.name), path)],
        spotify_id=sid,
    )
    cache = PlaylistSpotifyCache(db)
    cache.store(
        sid,
        'House Classics',
        [{'song_id': tid, 'name': 'Song', 'artists': ['Artist']}],
    )

    index = TrackIndex(db)
    downloader = MagicMock()
    downloader.download_dir = str(download_dir)
    downloader.organize_by_artist = False

    api.state.playlist_catalog = catalog
    try:
        catalog_filenames = api._catalog_filenames_for_playlist(
            'House Classics',
            sid,
        )
        downloaded, missing = split_tracks_by_library(
            [{'song_id': tid, 'name': 'Song'}],
            downloader=downloader,
            track_index=index,
            subdir='House Classics',
            catalog_filenames=catalog_filenames,
        )
        assert downloaded == 1
        assert missing == []
    finally:
        api.state.playlist_catalog = None


def test_delete_playlist_batch_endpoint(tmp_path: Path) -> None:
    db = tmp_path / 'lib.db'
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    sid = 'deletebatch12345678901234'
    pl_name = 'Gone List'
    path = download_dir / 'Artist - Song.mp3'
    path.write_bytes(b'audio')

    catalog = PlaylistCatalog(db)
    catalog.replace_playlist_tracks(
        pl_name,
        [({'song_id': '4uLU6hMCjMI75M1A2tKUQC'}, str(path.name), path)],
        spotify_id=sid,
    )
    store = PlaylistBatchStore(db)
    batch_id = store.start_batch(
        sid,
        pl_name,
        f'https://open.spotify.com/playlist/{sid}',
        1,
    )
    store.finish_batch(batch_id, 1, 0, status='complete')
    cache = PlaylistSpotifyCache(db)
    cache.store(
        sid, pl_name, [{'song_id': '4uLU6hMCjMI75M1A2tKUQC', 'name': 'Song'}]
    )
    index = TrackIndex(db)
    index.register('4uLU6hMCjMI75M1A2tKUQC', str(path.name), full_path=path)

    downloader = MagicMock()
    downloader.download_dir = str(download_dir)
    downloader.organize_by_artist = False

    api.state.playlist_batch_store = store
    api.state.playlist_catalog = catalog
    api.state.playlist_spotify_cache = cache
    api.state.track_index = index
    api.state.downloader = downloader
    api.state.settings = {'organize_by_artist': False}
    api.state.monitor_db = None
    api.state.download_jobs = {}

    try:

        async def _run() -> dict[str, Any]:
            return await api.delete_playlist_batch_endpoint(sid)

        result = asyncio.run(_run())
        assert result['ok'] is True
        assert result['deleted_count'] == 1
        assert not path.exists()
        assert store.list_latest_batches() == []
        assert cache.get(sid) is None
        assert catalog.list_playlist_names() == []
    finally:
        api.state.playlist_batch_store = None
        api.state.playlist_catalog = None
        api.state.playlist_spotify_cache = None
        api.state.track_index = None
        api.state.downloader = None
        api.state.download_jobs.clear()
