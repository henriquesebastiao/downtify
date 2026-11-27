"""The start-up history backfills write only what changed and keep the
playlist order a watch's sweep saved."""

from __future__ import annotations

from pathlib import Path

import pytest

from downtify.db.core import Database
from downtify.monitor import PlaylistMonitorDB
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex

TIDS = [
    '4uLU6hMCjMI75M1A2tKUQC',
    '0VjIjW4GlUZAMYd2vXMi3b',
    '7qiZfU4dY1lWllzX7mPBI3',
    '3n3Ppam7vgaVa1iaRUc9Lp',
]


def _song(download_dir: Path, n: int, size: int = 10) -> str:
    name = f'Artist - Song {n}.mp3'
    (download_dir / name).write_bytes(b'a' * size)
    return name


def _history(db: Database, download_dir: Path, count: int):
    """A watch that downloaded tracks 0..count-1, oldest first."""

    monitor = PlaylistMonitorDB(db)
    watch = monitor.add_playlist('pl' + '0' * 20, 'Road Mix', 'http://x')
    for n in range(count):
        monitor.mark_track_downloaded(
            watch.id, TIDS[n], _song(download_dir, n)
        )
    _dates(db)
    return monitor, watch


def _dates(db: Database) -> None:
    # Distinct, ordered download times (track n downloaded on day n+1).
    with db.connect() as conn:
        for n, tid in enumerate(TIDS):
            conn.execute(
                'UPDATE downloaded_tracks SET downloaded_at = ? '
                'WHERE track_spotify_id = ?',
                (f'2026-01-{n + 1:02d}T00:00:00+00:00', tid),
            )


def _order(catalog: PlaylistCatalog) -> list[str]:
    return [row['track_spotify_id'] for row in catalog.list_tracks('Road Mix')]


def _swept(catalog: PlaylistCatalog, download_dir: Path, tids: list[str]):
    """What a watch's sweep saves: the playlist in Spotify's order."""

    catalog.replace_playlist_tracks(
        'Road Mix',
        [
            (
                {'song_id': tid},
                f'Artist - Song {TIDS.index(tid)}.mp3',
                download_dir / f'Artist - Song {TIDS.index(tid)}.mp3',
            )
            for tid in tids
        ],
    )


@pytest.fixture
def download_dir(tmp_path: Path) -> Path:
    path = tmp_path / 'downloads'
    path.mkdir()
    return path


def test_restart_keeps_the_order_a_sweep_saved(backend_db, download_dir):
    _history(backend_db, download_dir, 3)
    catalog = PlaylistCatalog(backend_db)
    spotify_order = [TIDS[2], TIDS[0], TIDS[1]]
    _swept(catalog, download_dir, spotify_order)

    # Before: every start set track_order 0, so the list came back
    # sorted by track id instead.
    linked = catalog.backfill_from_monitor_db(
        backend_db, download_dir=download_dir
    )

    assert linked == 0
    assert _order(catalog) == spotify_order


def test_second_start_writes_nothing(backend_db, download_dir, monkeypatch):
    _history(backend_db, download_dir, 3)
    index = TrackIndex(backend_db)
    catalog = PlaylistCatalog(backend_db)
    assert index.backfill_from_monitor_db(backend_db) == 3
    assert (
        catalog.backfill_from_monitor_db(backend_db, download_dir=download_dir)
        == 3
    )

    writes = []
    monkeypatch.setattr(
        TrackIndex, 'register', lambda *a, **k: writes.append('index')
    )
    monkeypatch.setattr(
        PlaylistCatalog,
        '_write_member',
        lambda *a, **k: writes.append('member'),
    )
    monkeypatch.setattr(
        PlaylistCatalog,
        'ensure_playlist',
        lambda *a, **k: writes.append('playlist'),
    )

    assert index.backfill_from_monitor_db(backend_db) == 0
    assert (
        catalog.backfill_from_monitor_db(backend_db, download_dir=download_dir)
        == 0
    )
    assert writes == []


def test_first_import_follows_download_order(backend_db, download_dir):
    _history(backend_db, download_dir, 3)
    # Record the newest download first, so table order differs.
    with backend_db.connect() as conn:
        conn.execute(
            "UPDATE downloaded_tracks SET downloaded_at = '2025-12-31' "
            'WHERE track_spotify_id = ?',
            (TIDS[2],),
        )
    catalog = PlaylistCatalog(backend_db)

    catalog.backfill_from_monitor_db(backend_db, download_dir=download_dir)

    assert _order(catalog) == [TIDS[2], TIDS[0], TIDS[1]]
    orders = [row['track_order'] for row in catalog.list_tracks('Road Mix')]
    assert orders == [0, 1, 2]


def test_a_track_the_catalog_lacks_goes_last(backend_db, download_dir):
    monitor, watch = _history(backend_db, download_dir, 4)
    catalog = PlaylistCatalog(backend_db)
    spotify_order = [TIDS[1], TIDS[0], TIDS[2]]
    _swept(catalog, download_dir, spotify_order)

    linked = catalog.backfill_from_monitor_db(
        backend_db, download_dir=download_dir
    )

    assert linked == 1
    assert _order(catalog) == [*spotify_order, TIDS[3]]
    assert catalog.list_tracks('Road Mix')[-1]['track_order'] == 3


def test_a_changed_file_is_updated_in_place(backend_db, download_dir):
    monitor, watch = _history(backend_db, download_dir, 3)
    catalog = PlaylistCatalog(backend_db)
    spotify_order = [TIDS[2], TIDS[1], TIDS[0]]
    _swept(catalog, download_dir, spotify_order)
    before = {
        row['track_spotify_id']: row['content_key']
        for row in catalog.list_tracks('Road Mix')
    }

    # The history now names another file for track 1, and track 0's
    # file grew (new tags): both rows change, neither moves.
    moved = 'Other Folder/Artist - Song 1.mp3'
    (download_dir / 'Other Folder').mkdir()
    (download_dir / moved).write_bytes(b'b' * 20)
    monitor.mark_track_downloaded(watch.id, TIDS[1], moved)
    _dates(backend_db)
    _song(download_dir, 0, size=99)

    linked = catalog.backfill_from_monitor_db(
        backend_db, download_dir=download_dir
    )

    assert linked == 2
    rows = {r['track_spotify_id']: r for r in catalog.list_tracks('Road Mix')}
    assert _order(catalog) == spotify_order
    assert rows[TIDS[1]]['filename'] == moved
    assert rows[TIDS[0]]['content_key'] != before[TIDS[0]]
    assert rows[TIDS[2]]['content_key'] == before[TIDS[2]]


def test_index_still_takes_the_history_file(backend_db, download_dir):
    _history(backend_db, download_dir, 2)
    index = TrackIndex(backend_db)
    index.register(TIDS[0], 'elsewhere.mp3')

    assert index.backfill_from_monitor_db(backend_db) == 2
    assert index.lookup(TIDS[0]) == 'Artist - Song 0.mp3'
    assert index.lookup(TIDS[1]) == 'Artist - Song 1.mp3'
