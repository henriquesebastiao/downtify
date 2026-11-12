"""``GET /api/library/usage`` and ``/usage/scan``, and what feeds them:
the download outcome log (``api.record_download_outcome``), the slskd
transfers a library file was copied from (``FileProviders.source``) and
the hourly size snapshot - offline, against temporary folders."""

from __future__ import annotations

import asyncio
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from downtify import api
from downtify.download_log import DownloadLog
from downtify.file_providers import FileProviders
from downtify.library_catalog import LibraryContext
from downtify.library_usage import UsageSnapshots
from downtify.storage_scan import LEFTOVER_MIN_AGE


@pytest.fixture
def usage(tmp_path, monkeypatch):
    """A library at ``tmp/downloads`` (slskd at ``tmp/slskd``, copies
    not left in place) with fresh stores; ``usage.rows`` is the listing."""

    downloads = tmp_path / 'downloads'
    slskd = tmp_path / 'slskd'
    downloads.mkdir()
    slskd.mkdir()
    db = tmp_path / 'library.db'
    ctx = LibraryContext(download_dir=downloads, slskd_dir=slskd)

    class Usage:
        rows: list[dict] = []

    monkeypatch.setattr(api, 'library_context', lambda: ctx)
    monkeypatch.setattr(api, 'listing_for_request', lambda c: Usage.rows)
    monkeypatch.setattr(
        api,
        'list_library_paths',
        lambda c: [row['file'] for row in Usage.rows],
    )
    monkeypatch.setattr(api.state, 'file_providers', FileProviders(db))
    monkeypatch.setattr(api.state, 'download_log', DownloadLog(db))
    monkeypatch.setattr(api.state, 'usage_snapshots', UsageSnapshots(db))
    monkeypatch.setattr(api.state, 'track_index', None)
    monkeypatch.setattr(
        api.state,
        'settings',
        {
            **api.state.settings,
            'slskd': {'leave_in_place': False, 'source_dir': str(slskd)},
            'lyrics_lrc_dir': str(tmp_path / 'lyrics'),
        },
    )
    monkeypatch.setattr(api, '_usage_scan', {})
    Usage.downloads = downloads
    Usage.slskd = slskd
    return Usage


def _write(path, size):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'x' * size)
    return path


def test_a_finished_download_is_logged_with_its_size(usage):
    _write(usage.downloads / 'Song.mp3', 1234)

    api.record_download_outcome(
        {'name': 'Song', 'download_provider': 'youtube-music'},
        'completed',
        'Song.mp3',
    )
    api.record_download_outcome({'name': 'Gone'}, 'failed')

    rows = api.state.download_log.since(
        datetime.now(timezone.utc) - timedelta(minutes=1)
    )
    assert [(r['outcome'], r['provider'], r['bytes']) for r in rows] == [
        ('completed', 'youtube-music', 1234),
        ('failed', '', 0),
    ]


def test_the_queue_logs_a_song_it_found_already_in_the_library(
    usage, monkeypatch
):
    monkeypatch.setattr(
        api.state, 'downloader', type('D', (), {'overwrite_existing_files': 0})
    )
    monkeypatch.setattr(
        api,
        'resolve_existing_download',
        lambda *a, **k: ('Old.mp3', 'Already in library'),
    )
    job: dict = {}

    found = asyncio.run(api._finish_with_existing({'name': 'Old'}, job, None))

    assert found == 'Old.mp3'
    rows = api.state.download_log.since(
        datetime.now(timezone.utc) - timedelta(minutes=1)
    )
    assert [(r['outcome'], r['bytes']) for r in rows] == [('skipped', 0)]


def test_an_slskd_copy_remembers_the_transfer_it_came_from(usage):
    transfer = _write(usage.slskd / 'user' / '01 Song.flac', 50)
    _write(usage.downloads / 'Artist - Song.flac', 60)

    api.record_download_provider(
        {
            'download_provider': 'slskd',
            'download_source': str(transfer),
        },
        'Artist - Song.flac',
    )

    assert api.state.file_providers.sources() == [str(transfer)]


def test_the_usage_report_keeps_the_transfer_apart_and_notes_the_day(usage):
    transfer = _write(usage.slskd / 'user' / '01 Song.flac', 50)
    _write(usage.downloads / 'Artist - Song.flac', 60)
    usage.rows = [
        {'file': 'Artist - Song.flac', 'size': 60, 'added': 0},
        {'file': 'slskd/user/01 Song.flac', 'size': 50, 'added': 0},
        {'file': 'slskd/user/Stray.flac', 'size': 7, 'added': 0},
    ]
    api.state.file_providers.record(
        'key', 'Artist - Song.flac', 'slskd', str(transfer)
    )

    report = asyncio.run(api.library_usage(days=30))

    assert report['days'] == 30
    assert report['library']['files'] == 1
    assert report['library']['bytes'] == 60
    assert report['library']['by_provider'][0]['id'] == 'slskd'
    # The recorded transfer, and an slskd file nothing calls a library
    # song while copies aren't left in place.
    assert report['working']['files'] == 2
    assert report['working']['bytes'] == 57
    assert report['working']['slskd_in_place'] is False
    assert report['disk']['total'] > 0
    today = datetime.now(timezone.utc).date().isoformat()
    snapshot = api.state.usage_snapshots.since(today)
    assert [
        (s['files'], s['bytes'], s['working_files']) for s in snapshot
    ] == [(1, 60, 2)]


def test_the_hourly_reading_notes_the_size_and_prunes_the_log(usage):
    usage.rows = [{'file': 'A.mp3', 'size': 5, 'added': 0}]
    api.state.download_log.record(
        'completed', at=datetime.now(timezone.utc) - timedelta(days=500)
    )

    api.take_usage_snapshot()

    today = datetime.now(timezone.utc).date().isoformat()
    assert api.state.usage_snapshots.since(today)[0]['bytes'] == 5
    assert api.state.download_log.first_at() is None


def test_the_folder_scan_is_kept_until_asked_again(usage):
    usage.rows = [{'file': 'Song.mp3', 'size': 3}]
    _write(usage.downloads / 'Song.mp3', 3)
    leftover = _write(usage.downloads / 'Song.webm.part', 9)
    old = datetime.now(timezone.utc).timestamp() - LEFTOVER_MIN_AGE - 60
    os.utime(leftover, (old, old))
    _write(usage.downloads / 'Gone.lrc', 4)

    first = asyncio.run(api.library_usage_scan())

    assert [f['id'] for f in first['folders']] == ['downloads', 'slskd']
    assert first['leftovers']['files'] == 1
    assert first['orphans']['files'] == 1
    leftover.unlink()
    assert asyncio.run(api.library_usage_scan()) is first
    again = asyncio.run(api.library_usage_scan(refresh=True))
    assert again['leftovers']['files'] == 0


def test_an_older_provider_table_gains_the_source_column(tmp_path):
    db = tmp_path / 'library.db'
    with sqlite3.connect(db) as conn:
        conn.execute(
            'CREATE TABLE file_providers (content_key TEXT PRIMARY KEY, '
            "path TEXT NOT NULL DEFAULT '', provider TEXT NOT NULL, "
            'recorded_at TEXT NOT NULL)'
        )
        conn.execute(
            "INSERT INTO file_providers VALUES ('k', 'A.mp3', 'youtube', "
            "'2026-01-01T00:00:00+00:00')"
        )

    store = FileProviders(db)

    assert store.recorded({'A.mp3': 'k'}) == {
        'A.mp3': {
            'provider': 'youtube',
            'recorded_at': '2026-01-01T00:00:00+00:00',
        }
    }
    assert store.lookup({'A.mp3': 'other'}) == {'A.mp3': 'youtube'}
    assert store.sources() == []
