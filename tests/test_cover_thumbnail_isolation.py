"""Different library directories must not share a track's cached cover."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from mutagen.id3 import APIC, ID3
from starlette.testclient import TestClient

from downtify import api, cover_thumbs, mobile_routes
from downtify.cover_thumbs import CoverThumbs

COVERS = (b'\xff\xd8\xff\xe0album-one', b'\xff\xd8\xff\xe0album-two')
STAMP = 1_700_000_000_000_000_000


def _source(path: Path, cover: bytes, *, embedded: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\x00' * 128)
    if embedded:
        tags = ID3()
        tags.add(APIC(encoding=3, mime='image/jpeg', type=3, data=cover))
        tags.save(str(path))
    else:
        (path.parent / 'cover.jpg').write_bytes(cover)
    os.utime(path, ns=(STAMP, STAMP))
    return path


def _sources(tmp_path: Path, *, embedded: bool = True) -> tuple[Path, Path]:
    first = _source(
        tmp_path / 'downloads' / 'Album A' / 'Intro.mp3',
        COVERS[0],
        embedded=embedded,
    )
    second = _source(
        tmp_path / 'external' / 'Album B' / 'Intro.mp3',
        COVERS[1],
        embedded=embedded,
    )
    # Reproduce the old cache collision without depending on clock timing.
    assert first.name == second.name
    assert first.stat().st_size == second.stat().st_size
    assert first.stat().st_mtime_ns == second.stat().st_mtime_ns
    return first, second


def _scaled(data: bytes, size: int) -> bytes:
    return str(size).encode() + b':' + data


def _unexpected(*_args: Any) -> None:
    raise AssertionError('the cached cover was extracted or scaled again')


@pytest.fixture
def thumbs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CoverThumbs:
    def scale(_self: CoverThumbs, data: bytes, size: int) -> bytes:
        return _scaled(data, size)

    monkeypatch.setattr(CoverThumbs, '_scale', scale)
    return CoverThumbs(tmp_path / 'thumbs', ffmpeg='')


@pytest.mark.parametrize('embedded', [True, False])
@pytest.mark.parametrize('size', [0, 150, 300, 600])
def test_same_file_revision_in_different_directories_has_its_own_cover(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    thumbs: CoverThumbs,
    embedded: bool,
    size: int,
) -> None:
    sources = _sources(tmp_path, embedded=embedded)
    results = [thumbs.get(source, size) for source in sources]

    for result, cover in zip(results, COVERS):
        assert result is not None
        assert result[0] == (_scaled(cover, size) if size else cover)
        assert result[1] == 'image/jpeg'
    assert results[0][2] != results[1][2]
    assert len(list(thumbs._dir.glob('*-full.bin'))) == 2

    monkeypatch.setattr(cover_thumbs, 'extract_cover_art', _unexpected)
    monkeypatch.setattr(CoverThumbs, '_scale', _unexpected)
    reopened = CoverThumbs(thumbs._dir, ffmpeg='')
    assert [reopened.get(source, size) for source in sources] == results


def test_resolved_aliases_of_the_same_file_reuse_the_cached_cover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, thumbs: CoverThumbs
) -> None:
    source, _other = _sources(tmp_path)
    result = thumbs.get(source, 150)
    (source.parent / 'nested').mkdir()
    alias = source.parent / 'nested' / '..' / source.name

    monkeypatch.setattr(cover_thumbs, 'extract_cover_art', _unexpected)
    monkeypatch.setattr(CoverThumbs, '_scale', _unexpected)
    assert thumbs.get(alias, 150) == result
    monkeypatch.chdir(tmp_path)
    assert thumbs.get(source.relative_to(tmp_path), 150) == result


@pytest.mark.parametrize('changed', ['size', 'mtime'])
def test_source_size_and_mtime_still_invalidate_the_cached_cover(
    tmp_path: Path, thumbs: CoverThumbs, changed: str
) -> None:
    source, _other = _sources(tmp_path)
    original_stat = source.stat()
    before = thumbs.get(source, 300)
    _source(source, COVERS[1])
    if changed == 'size':
        source.write_bytes(source.read_bytes() + b'\x00')
        os.utime(source, ns=(STAMP, STAMP))
        assert source.stat().st_size != original_stat.st_size
        assert source.stat().st_mtime_ns == original_stat.st_mtime_ns
    else:
        os.utime(source, ns=(STAMP, STAMP + 1_000))
        assert source.stat().st_size == original_stat.st_size
        assert source.stat().st_mtime_ns != original_stat.st_mtime_ns

    after = thumbs.get(source, 300)
    assert before is not None
    assert after is not None
    assert before[0] == _scaled(COVERS[0], 300)
    assert after[0] == _scaled(COVERS[1], 300)
    assert before[2] != after[2]


def test_legacy_basename_only_cache_entries_are_not_reused(
    tmp_path: Path, thumbs: CoverThumbs
) -> None:
    source, _other = _sources(tmp_path)
    stat = source.stat()
    old_key = hashlib.sha256(
        f'{source.name}\n{stat.st_size}\n{stat.st_mtime_ns}'.encode()
    ).hexdigest()
    thumbs._dir.mkdir()
    legacy_data = thumbs._dir / f'{old_key}-full.bin'
    legacy_data.write_bytes(COVERS[1])
    (thumbs._dir / f'{old_key}-full.json').write_text(
        json.dumps({'mime': 'image/jpeg'}), encoding='utf-8'
    )

    result = thumbs.get(source, 0)

    assert result is not None
    assert result[0] == COVERS[0]
    assert len(list(thumbs._dir.glob('*-full.bin'))) == 2
    assert legacy_data.read_bytes() == COVERS[1]


def test_a_track_without_cover_does_not_inherit_another_tracks_cover(
    tmp_path: Path, thumbs: CoverThumbs
) -> None:
    first, second = _sources(tmp_path, embedded=False)
    (first.parent / 'cover.jpg').unlink()

    assert thumbs.get(first, 150) is None
    assert thumbs.get(second, 150)[0] == _scaled(COVERS[1], 150)
    assert thumbs.get(first, 150) is None


def test_mobile_cover_validator_is_specific_to_the_resolved_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, thumbs: CoverThumbs
) -> None:
    first, second = _sources(tmp_path)
    sources = {'first': first, 'second': second}
    monkeypatch.setattr(
        mobile_routes,
        '_track_path',
        lambda track_id, _request: ({}, sources[track_id]),
    )
    monkeypatch.setattr(api.state, 'cover_thumbs', thumbs)
    app = FastAPI()
    app.include_router(mobile_routes.router)
    client = TestClient(app)

    first_cover = client.get('/api/v1/tracks/first/cover?size=150')
    assert first_cover.status_code == 200
    assert first_cover.content == _scaled(COVERS[0], 150)
    etag = first_cover.headers['etag']
    second_cover = client.get(
        '/api/v1/tracks/second/cover?size=150',
        headers={'If-None-Match': etag},
    )
    assert second_cover.status_code == 200
    assert second_cover.content == _scaled(COVERS[1], 150)
    assert second_cover.headers['etag'] != etag
    again = client.get(
        '/api/v1/tracks/second/cover?size=150',
        headers={'If-None-Match': second_cover.headers['etag']},
    )
    assert again.status_code == 304
    assert not again.content
