"""The library listing cache persists through the bound store on both
backends, so a restart is served from the database and not a disk walk."""

from __future__ import annotations

import pytest

from downtify import library_paths_cache as paths_cache
from downtify.library_catalog import LibraryContext, list_library_entries


@pytest.fixture
def bound_store(backend_db):
    paths_cache.drop_listing_memory_caches()
    paths_cache.bind_listing_store(backend_db)
    try:
        yield backend_db
    finally:
        paths_cache.bind_listing_store(None)
        paths_cache.drop_listing_memory_caches()


def test_listing_is_served_from_persisted_store(bound_store, tmp_path):
    download_dir = tmp_path / 'downloads'
    download_dir.mkdir()
    (download_dir / 'One.mp3').write_bytes(b'1')
    ctx = LibraryContext(download_dir=download_dir)

    list_library_entries(ctx)

    paths_cache.drop_listing_memory_caches()
    assert paths_cache._ENTRIES_CACHE == {}
    peeked = paths_cache.peek_cached_track_entries(ctx)
    assert peeked is not None
    assert [row['file'] for row in peeked] == ['One.mp3']
