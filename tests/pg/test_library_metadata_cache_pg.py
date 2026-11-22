"""LibraryMetadataCache on both backends: the same results on SQLite and PostgreSQL."""

from __future__ import annotations

from pathlib import Path

from downtify import library_metadata_cache
from downtify.library_metadata_cache import META_VERSION, LibraryMetadataCache


def _entry(stored: str, full: Path, **overrides) -> dict:
    """A tag read as ``library_entry_for_file`` returns it, shaped like a /tracks row."""
    stat = full.stat() if full.exists() else None
    entry = {
        'file': stored,
        'title': full.stem,
        'artist': 'Portishead',
        'artists': ['Portishead', 'Beth Gibbons'],
        'album': 'Dummy',
        'album_artist': 'Portishead',
        'track_number': 3,
        'year': '1994',
        'release_date': '1994-08-22',
        'duration': 233.5,
        'codec': 'mp3',
        'bitrate': 320000,
        'sample_rate': 44100,
        'channels': 2,
        'genre': 'Trip Hop',
        'explicit': True,
        'compilation': False,
        'isrc': '',
        'has_cover': True,
        'cover_px': 600,
        'added': int(stat.st_mtime_ns) // 1_000_000_000 if stat else 0,
        'size': int(stat.st_size) if stat else 0,
    }
    entry.update(overrides)
    return entry


def _reads(monkeypatch) -> list[str]:
    calls: list[str] = []

    def read(stored, full):
        calls.append(full.name)
        return _entry(stored, full)

    monkeypatch.setattr(library_metadata_cache, 'library_entry_for_file', read)
    return calls


def _file(tmp_path: Path, name: str, data: bytes = b'audio') -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def _row_count(
    cache: LibraryMetadataCache, filename: str | None = None
) -> int:
    with cache.db.connect() as conn:
        if filename is None:
            row = conn.execute(
                'SELECT COUNT(*) FROM library_metadata'
            ).fetchone()
        else:
            row = conn.execute(
                'SELECT COUNT(*) FROM library_metadata WHERE filename = ?',
                (filename,),
            ).fetchone()
    return int(row[0])


def test_accepts_a_database_and_keeps_it(backend_db) -> None:
    cache = LibraryMetadataCache(backend_db)
    assert cache.db is backend_db
    assert cache.get_entries_batch([]) == []
    assert _row_count(cache) == 0


def test_get_entry_reads_once_then_serves_the_cache(
    backend_db, tmp_path, monkeypatch
) -> None:
    reads = _reads(monkeypatch)
    cache = LibraryMetadataCache(backend_db)
    track = _file(tmp_path, 'a.mp3')

    first = cache.get_entry('a.mp3', track)
    second = cache.get_entry('a.mp3', track)

    assert reads == ['a.mp3']
    assert second == first
    assert second['explicit'] is True
    assert second['compilation'] is False
    assert second['has_cover'] is True
    assert second['artists'] == ['Portishead', 'Beth Gibbons']
    assert isinstance(second['duration'], float)
    assert second['duration'] == 233.5
    assert second['bitrate'] == 320000


def test_batch_round_trips_every_column(
    backend_db, tmp_path, monkeypatch
) -> None:
    reads = _reads(monkeypatch)
    cache = LibraryMetadataCache(backend_db)
    a = _file(tmp_path, 'a.mp3')
    b = _file(tmp_path, 'b.flac', b'other bytes')
    items = [('a.mp3', a), ('b.flac', b)]

    first = cache.get_entries_batch(items)
    second = cache.get_entries_batch(items)

    assert sorted(reads) == ['a.mp3', 'b.flac']
    assert second == first
    assert [e['file'] for e in second] == ['a.mp3', 'b.flac']


def test_explicit_false_and_compilation_true_round_trip(
    backend_db, tmp_path, monkeypatch
) -> None:
    def read(stored, full):
        return _entry(stored, full, explicit=False, compilation=True)

    monkeypatch.setattr(library_metadata_cache, 'library_entry_for_file', read)
    cache = LibraryMetadataCache(backend_db)
    track = _file(tmp_path, 'c.mp3')

    cache.get_entry('c.mp3', track)
    cached = cache.get_entry('c.mp3', track)

    assert cached['explicit'] is False
    assert cached['compilation'] is True


def test_changed_file_is_read_again(backend_db, tmp_path, monkeypatch) -> None:
    reads = _reads(monkeypatch)
    cache = LibraryMetadataCache(backend_db)
    track = _file(tmp_path, 'a.mp3')
    cache.get_entry('a.mp3', track)

    track.write_bytes(b'retagged, different size')
    cache.get_entry('a.mp3', track)

    assert reads == ['a.mp3', 'a.mp3']


def test_older_meta_version_is_read_again(
    backend_db, tmp_path, monkeypatch
) -> None:
    reads = _reads(monkeypatch)
    cache = LibraryMetadataCache(backend_db)
    track = _file(tmp_path, 'a.mp3')
    cache.get_entry('a.mp3', track)

    with cache.db.connect() as conn:
        conn.execute(
            'UPDATE library_metadata SET meta_version = ?', (META_VERSION - 1,)
        )
    cache.get_entry('a.mp3', track)

    assert reads == ['a.mp3', 'a.mp3']


def test_files_that_cannot_be_cached_are_not_stored(
    backend_db, tmp_path, monkeypatch
) -> None:
    reads = _reads(monkeypatch)
    cache = LibraryMetadataCache(backend_db)
    ghost = tmp_path / 'ghost.mp3'

    rows = cache.get_entries_batch([('ghost.mp3', ghost)])

    assert len(rows) == 1
    assert reads == ['ghost.mp3']
    assert _row_count(cache) == 0


def test_refresh_stores_a_fresh_read(
    backend_db, tmp_path, monkeypatch
) -> None:
    reads = _reads(monkeypatch)
    cache = LibraryMetadataCache(backend_db)
    track = _file(tmp_path, 'a.mp3')

    entry = cache.refresh('a.mp3', track)
    cached = cache.get_entry('a.mp3', track)

    assert entry is not None
    assert cached == entry
    assert reads == ['a.mp3']
    assert _row_count(cache, 'a.mp3') == 1


def test_refresh_of_a_missing_file_forgets_it(
    backend_db, tmp_path, monkeypatch
) -> None:
    _reads(monkeypatch)
    cache = LibraryMetadataCache(backend_db)
    track = _file(tmp_path, 'a.mp3')
    cache.refresh('a.mp3', track)

    track.unlink()

    assert cache.refresh('a.mp3', track) is None
    assert _row_count(cache, 'a.mp3') == 0


def test_refresh_stored_path_resolves_the_file(
    backend_db, tmp_path, monkeypatch
) -> None:
    _reads(monkeypatch)
    track = _file(tmp_path, 'a.mp3')

    def locate(stored, download_dir, slskd_dir=None):
        return track if stored == 'a.mp3' else None

    monkeypatch.setattr(library_metadata_cache, 'locate_library_file', locate)
    cache = LibraryMetadataCache(backend_db)

    cache.refresh_stored_path('a.mp3', download_dir=tmp_path)
    cache.refresh_stored_path('missing.mp3', download_dir=tmp_path)

    assert _row_count(cache, 'a.mp3') == 1
    assert _row_count(cache) == 1


def test_forget_by_filename_and_by_content_key(
    backend_db, tmp_path, monkeypatch
) -> None:
    _reads(monkeypatch)
    cache = LibraryMetadataCache(backend_db)
    a = _file(tmp_path, 'a.mp3')
    b = _file(tmp_path, 'b.mp3', b'bb')
    cache.get_entries_batch([('a.mp3', a), ('moved/b.mp3', b)])
    assert _row_count(cache) == 2

    cache.forget('a.mp3')
    assert _row_count(cache, 'a.mp3') == 0
    assert _row_count(cache) == 1

    # Forgetting by a different stored name still finds the row by content key.
    cache.forget('gone.mp3', full_path=b)
    assert _row_count(cache) == 0


def test_merge_fields_patches_without_rereading(
    backend_db, tmp_path, monkeypatch
) -> None:
    reads = _reads(monkeypatch)
    cache = LibraryMetadataCache(backend_db)
    track = _file(tmp_path, 'a.mp3')
    cache.get_entry('a.mp3', track)

    cache.merge_fields(
        'a.mp3',
        track,
        {'has_cover': False, 'cover_px': 0, 'genre': 'Rock'},
    )
    cache.merge_fields('a.mp3', track, {'title': 'ignored'})
    cache.merge_fields('a.mp3', track, {})

    patched = cache.get_entry('a.mp3', track)
    assert patched['has_cover'] is False
    assert patched['cover_px'] == 0
    assert patched['genre'] == 'Rock'
    assert patched['title'] == 'a'
    assert reads == ['a.mp3']
