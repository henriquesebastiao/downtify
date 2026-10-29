"""``GET /cover?size=``: grids and lists ask for a small, cached copy.

A Library grid showed every album at ~250 px from the full embedded
picture (~640 px, ~1.6 MB decoded each): scrolling 3,700 albums held
~2.4 GB in the browser.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest
from mutagen.id3 import APIC, ID3, TIT2
from starlette.testclient import TestClient

import main
from downtify import api, cover_thumbs
from downtify.cover_thumbs import CoverThumbs

FULL = b'\xff\xd8\xff\xe0' + b'full-size-cover' * 100
SMALL = b'\xff\xd8\xff\xe0small'


def _tagged_mp3(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\x00' * 1024)
    tags = ID3()
    tags.add(TIT2(encoding=3, text='Roads'))
    tags.add(APIC(encoding=3, mime='image/jpeg', type=3, data=FULL))
    tags.save(str(path))
    return path


@pytest.fixture
def client(tmp_path, monkeypatch):
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html></html>')
    downloads = tmp_path / 'downloads'
    data = tmp_path / 'data'
    downloads.mkdir()
    data.mkdir()
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', downloads)
    monkeypatch.setattr(main, 'DATABASE_DIR', data)
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    for name in (
        'auth',
        'activity',
        'identity',
        'downloader',
        'settings',
        'cover_thumbs',
        'cover_cache',
        'metadata_cache',
        'track_index',
        'playlist_catalog',
    ):
        monkeypatch.setattr(api.state, name, getattr(api.state, name, None))
    monkeypatch.setattr(
        CoverThumbs, '_scale', lambda _self, _data, _size: SMALL
    )
    app = main.build_app()
    main._open_library_stores(data / 'downtify_monitor.db')
    test_client = TestClient(app)
    test_client.post(
        '/api/auth/login', json={'username': 'admin', 'password': 'downtify'}
    )
    _tagged_mp3(downloads / 'Portishead - Roads.mp3')
    return test_client


def test_a_sized_cover_is_the_scaled_copy(client):
    small = client.get('/cover', params={'file': 'Portishead - Roads.mp3'})
    sized = client.get(
        '/cover', params={'file': 'Portishead - Roads.mp3', 'size': '300'}
    )

    assert small.status_code == 200
    assert small.content == FULL
    assert sized.status_code == 200
    assert sized.content == SMALL
    assert sized.headers['content-type'] == 'image/jpeg'
    assert sized.headers['etag'].endswith('-300"')
    assert 'max-age' in sized.headers['cache-control']


def test_an_odd_size_rounds_up_and_a_huge_one_is_full_size(client):
    up = client.get(
        '/cover', params={'file': 'Portishead - Roads.mp3', 'size': '120'}
    )
    huge = client.get(
        '/cover', params={'file': 'Portishead - Roads.mp3', 'size': '5000'}
    )

    assert up.headers['etag'].endswith('-150"')
    assert huge.content == FULL


def test_a_sized_cover_of_an_unknown_file_is_404(client):
    missing = client.get('/cover', params={'file': 'nope.mp3', 'size': '150'})
    assert missing.status_code == 404


def test_scaling_runs_a_bounded_number_of_ffmpeg_at_once(
    tmp_path, monkeypatch
):
    """A first scroll through a big library asks for thousands of
    thumbnails at once; only a few ffmpeg processes may run together."""

    thumbs = CoverThumbs(tmp_path / 'thumbs', ffmpeg='ffmpeg')
    running = 0
    peak = 0
    lock = threading.Lock()

    def slow_ffmpeg(_self, _data, _size):
        nonlocal running, peak
        with lock:
            running += 1
            peak = max(peak, running)
        time.sleep(0.05)
        with lock:
            running -= 1

        class Done:
            returncode = 0
            stdout = SMALL

        return Done()

    monkeypatch.setattr(CoverThumbs, '_run_ffmpeg', slow_ffmpeg)
    workers = [
        threading.Thread(target=thumbs._scale, args=(FULL, 150))
        for _ in range(cover_thumbs.MAX_PARALLEL_SCALES * 3)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    assert peak == cover_thumbs.MAX_PARALLEL_SCALES


def test_a_cover_only_in_the_cover_cache_falls_back_to_full_size(
    client, tmp_path
):
    """Read-only extra folders keep their covers in the cover cache only:
    there is nothing embedded to scale, so a sized request still gets
    the picture (full size) instead of a 404."""

    bare = tmp_path / 'downloads' / 'Bare.mp3'
    bare.write_bytes(b'\x00' * 2048)
    api.state.cover_cache.store('Bare.mp3', bare, FULL, 'image/jpeg')

    sized = client.get('/cover', params={'file': 'Bare.mp3', 'size': '150'})

    assert sized.status_code == 200
    assert sized.content == FULL
