from __future__ import annotations

import os
from pathlib import Path

import pytest

from downtify import doctor_audio
from downtify.db.config import Dialect
from downtify.doctor_audio import AudioHashCache
from tests.db.helpers import query

DIGEST_A = 'a' * 32
DIGEST_B = 'b' * 32


class FakeHasher:
    """Stands in for ffmpeg: queued answers first, then DIGEST_A."""

    def __init__(self) -> None:
        self.calls: list[Path] = []
        self.next: list[str | None] = []

    def __call__(self, path: Path, *, ffmpeg: str = 'ffmpeg') -> str | None:
        self.calls.append(path)
        if self.next:
            return self.next.pop(0)
        return DIGEST_A


@pytest.fixture
def hasher(monkeypatch) -> FakeHasher:
    fake = FakeHasher()
    monkeypatch.setattr(doctor_audio, 'audio_md5', fake)
    return fake


def _audio(tmp_path: Path, name: str = 'song.flac') -> Path:
    path = tmp_path / name
    path.write_bytes(b'x' * 10)
    return path


def _rows(db) -> list[tuple]:
    rows = query(
        db,
        'SELECT path, size, mtime_ns, digest FROM audio_hashes ORDER BY path',
    )
    return [tuple(row) for row in rows]


def test_wraps_given_database(backend_db) -> None:
    cache = AudioHashCache(backend_db)
    assert cache.db is backend_db
    assert cache.db_path == backend_db.path


def test_digest_is_cached_while_size_and_mtime_hold(
    backend_db, hasher, tmp_path
) -> None:
    cache = AudioHashCache(backend_db)
    song = _audio(tmp_path)
    assert cache.digest(song) == DIGEST_A
    assert cache.digest(song) == DIGEST_A
    assert len(hasher.calls) == 1
    assert _rows(backend_db) == [
        (str(song), 10, song.stat().st_mtime_ns, DIGEST_A)
    ]


def test_changed_mtime_rehashes_and_replaces_row(
    backend_db, hasher, tmp_path
) -> None:
    cache = AudioHashCache(backend_db)
    song = _audio(tmp_path)
    cache.digest(song)
    hasher.next = [DIGEST_B]
    st = song.stat()
    os.utime(song, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    assert cache.digest(song) == DIGEST_B
    assert len(hasher.calls) == 2
    assert _rows(backend_db) == [
        (str(song), 10, song.stat().st_mtime_ns, DIGEST_B)
    ]


def test_changed_size_rehashes(backend_db, hasher, tmp_path) -> None:
    cache = AudioHashCache(backend_db)
    song = _audio(tmp_path)
    cache.digest(song)
    hasher.next = [DIGEST_B]
    song.write_bytes(b'y' * 20)
    assert cache.digest(song) == DIGEST_B
    assert _rows(backend_db)[0][1] == 20


def test_missing_file_returns_none_without_hashing(
    backend_db, hasher, tmp_path
) -> None:
    cache = AudioHashCache(backend_db)
    assert cache.digest(tmp_path / 'gone.flac') is None
    assert hasher.calls == []
    assert _rows(backend_db) == []


def test_unhashable_audio_is_not_cached(backend_db, hasher, tmp_path) -> None:
    cache = AudioHashCache(backend_db)
    song = _audio(tmp_path)
    hasher.next = [None]
    assert cache.digest(song) is None
    assert _rows(backend_db) == []
    assert cache.digest(song) == DIGEST_A
    assert len(hasher.calls) == 2


def test_cache_survives_a_new_instance(backend_db, hasher, tmp_path) -> None:
    song = _audio(tmp_path)
    AudioHashCache(backend_db).digest(song)
    assert AudioHashCache(backend_db).digest(song) == DIGEST_A
    assert len(hasher.calls) == 1


def test_forget_empty_is_noop(backend_db, hasher, tmp_path) -> None:
    cache = AudioHashCache(backend_db)
    cache.digest(_audio(tmp_path))
    cache.forget([])
    assert len(_rows(backend_db)) == 1


def test_forget_drops_rows_so_next_digest_rehashes(
    backend_db, hasher, tmp_path
) -> None:
    cache = AudioHashCache(backend_db)
    song = _audio(tmp_path)
    cache.digest(song)
    cache.forget([str(song)])
    assert _rows(backend_db) == []
    assert cache.digest(song) == DIGEST_A
    assert len(hasher.calls) == 2


def test_forget_many_paths(backend_db, hasher, tmp_path) -> None:
    cache = AudioHashCache(backend_db)
    one = _audio(tmp_path, 'one.flac')
    two = _audio(tmp_path, 'two.flac')
    keep = _audio(tmp_path, 'keep.flac')
    for song in (one, two, keep):
        cache.digest(song)
    cache.forget([str(one), str(two)])
    assert [row[0] for row in _rows(backend_db)] == [str(keep)]


def test_path_constructor_creates_sqlite_file(tmp_path, hasher) -> None:
    db_file = tmp_path / 'doctor' / 'audio_hashes.db'
    cache = AudioHashCache(db_file)
    assert cache.db_path == db_file
    assert cache.db.dialect is Dialect.SQLITE
    song = _audio(tmp_path)
    assert cache.digest(song) == DIGEST_A
    assert db_file.exists()
