"""Process isolation and snapshot safety under concurrent completions."""

from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from downtify import catalog_worker as worker
from downtify import library_catalog as catalog
from downtify.external_library import finish_library_entries
from downtify.library_paths import EXTERNAL_LIBRARY_PREFIX
from downtify.library_paths_cache import invalidate_library_paths_cache


def test_spawn_worker_matches_inline_and_has_separate_pid() -> None:
    entries = [
        {'file': 'one.mp3', 'artist': 'The Beatles', 'title': 'Help'},
        {
            'file': EXTERNAL_LIBRARY_PREFIX + 'extra/two.mp3',
            'artist': 'Beatles',
            'title': 'Yesterday',
        },
    ]
    worker.start_catalog_worker()
    try:
        assert worker.fold_library_entries(entries) == finish_library_entries(
            entries
        )
        assert worker._pool is not None
        assert worker._pool.submit(os.getpid).result(timeout=15) != os.getpid()
    finally:
        worker.stop_catalog_worker()


def test_worker_can_restart_and_restores_inline_library_use() -> None:
    for _ in range(2):
        worker.start_catalog_worker()
        assert worker.fold_library_entries([]) == []
        worker.stop_catalog_worker()
        assert worker._pool is None
        assert worker.fold_library_entries([]) == []


def test_concurrent_merges_keep_both_tracks_and_readable_snapshot(
    tmp_path, monkeypatch
) -> None:
    root = tmp_path / 'downloads'
    root.mkdir()
    (root / 'first.mp3').write_bytes(b'first')
    ctx = catalog.LibraryContext(download_dir=root)
    invalidate_library_paths_cache(drop_entries=True)
    catalog.list_library_entries(ctx)
    (root / 'second.mp3').write_bytes(b'second')
    (root / 'third.mp3').write_bytes(b'third')
    entered = threading.Event()
    release = threading.Event()
    fold = catalog.fold_library_entries

    def paused_fold(entries):
        entered.set()
        assert release.wait(timeout=10)
        return fold(entries)

    monkeypatch.setattr(catalog, 'fold_library_entries', paused_fold)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            catalog.merge_library_listing_file, ctx, 'second.mp3'
        )
        assert entered.wait(timeout=10)
        second = pool.submit(
            catalog.merge_library_listing_file, ctx, 'third.mp3'
        )
        # Reading the last snapshot does not wait on the blocked writer.
        assert catalog.library_home_summary(ctx)['track_count'] == 1
        release.set()
        first.result(timeout=10)
        second.result(timeout=10)
    assert {row['file'] for row in catalog.listing_for_request(ctx)} == {
        'first.mp3',
        'second.mp3',
        'third.mp3',
    }


def test_failed_fold_preserves_previous_snapshot(
    tmp_path, monkeypatch
) -> None:
    root = tmp_path / 'downloads'
    root.mkdir()
    (root / 'first.mp3').write_bytes(b'first')
    ctx = catalog.LibraryContext(download_dir=root)
    invalidate_library_paths_cache(drop_entries=True)
    catalog.list_library_entries(ctx)
    (root / 'second.mp3').write_bytes(b'second')

    def fail(_entries):
        raise RuntimeError('worker failed')

    monkeypatch.setattr(catalog, 'fold_library_entries', fail)
    with pytest.raises(RuntimeError, match='worker failed'):
        catalog.merge_library_listing_file(ctx, 'second.mp3')
    assert catalog.library_home_summary(ctx)['track_count'] == 1
