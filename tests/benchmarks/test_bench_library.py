"""CodSpeed benchmarks for library-wide operations: folding external
library folders onto downloads and building/reading M3U playlists.

Inputs are synthetic and built offline; nothing reads a user's music.
"""

from __future__ import annotations

import hashlib

import pytest

from downtify.external_library import partition_extra_entries, song_identity
from downtify.library_paths import EXTERNAL_LIBRARY_PREFIX
from downtify.m3u import build_m3u_content, read_m3u_entries


def _artist(index: int) -> str:
    return 'Ensemble ' + hashlib.sha256(str(index).encode()).hexdigest()[:12]


def _library_entries(owned: int, external: int) -> list[dict]:
    rows = [
        {
            'file': f'owned/{i}.mp3',
            'title': f'Owned Song {i} (Remastered 2011)',
            'artist': _artist(i % 80),
            'duration': 180,
        }
        for i in range(owned)
    ]
    rows.extend(
        {
            'file': f'{EXTERNAL_LIBRARY_PREFIX}synthetic/{i}.mp3',
            'title': (
                f'Owned Song {i} feat. Someone'
                if i % 3 == 0
                else f'External {i}'
            ),
            'artist': (
                _artist(i % 80).upper()
                if i % 3 == 0
                else _artist(1000 + i % 20)
            ),
            'duration': 181,
        }
        for i in range(external)
    )
    return rows


@pytest.fixture(scope='module')
def library_entries():
    return _library_entries(owned=400, external=200)


@pytest.mark.benchmark
def test_bench_partition_extra_entries(library_entries):
    owned, kept, skipped = partition_extra_entries(library_entries)
    assert len(owned) == 400
    assert len(kept) + len(skipped) == 200


@pytest.mark.benchmark
def test_bench_song_identity(library_entries):
    for entry in library_entries:
        song_identity(entry)


@pytest.fixture
def playlist_library(tmp_path):
    download_dir = tmp_path / 'downloads'
    entries = []
    for i in range(100):
        rel = f'{_artist(i % 10)}/Album {i % 7}/{i:02d} - Track {i}.mp3'
        path = download_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'')
        entries.append({
            'filename': rel,
            'title': f'Track {i}',
            'artist': _artist(i % 10),
            'duration': 200 + i,
        })
    return download_dir, entries


@pytest.mark.benchmark
def test_bench_build_m3u_content(playlist_library):
    download_dir, entries = playlist_library
    content, kept = build_m3u_content(entries, download_dir=download_dir)
    assert kept == len(entries)
    assert content.startswith('#EXTM3U')


@pytest.fixture
def playlist_m3u(playlist_library):
    download_dir, entries = playlist_library
    content, _kept = build_m3u_content(entries, download_dir=download_dir)
    m3u_path = download_dir / 'Playlists' / 'Bench.m3u'
    m3u_path.parent.mkdir(parents=True, exist_ok=True)
    m3u_path.write_text(content, encoding='utf-8')
    return download_dir, m3u_path, len(entries)


@pytest.mark.benchmark
def test_bench_read_m3u_entries(playlist_m3u):
    download_dir, m3u_path, count = playlist_m3u
    rows = read_m3u_entries(m3u_path, download_dir)
    assert len(rows) == count
