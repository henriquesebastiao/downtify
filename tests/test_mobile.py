"""The mobile API: stable track ids and the library feed
(downtify/library_sync.py), transcoding (downtify/transcode.py), cover
sizes (downtify/cover_thumbs.py) and the /api/v1 routes
(downtify/mobile_routes.py). Offline; the ffmpeg-dependent tests are
skipped where ffmpeg isn't installed."""

from __future__ import annotations

import asyncio
import os
import shutil
import stat
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from mutagen.id3 import APIC, ID3, TALB, TIT2, TPE1
from starlette.testclient import TestClient

import main
from downtify import api
from downtify.cover_thumbs import CoverThumbs, normalize_size
from downtify.discover import DiscoverStore
from downtify.discovery import (
    discovery_enabled,
    instance_name,
    local_addresses,
    txt_record,
)
from downtify.library_metadata import read_audio_metadata
from downtify.library_sync import (
    TOMBSTONE_DAYS,
    LibrarySync,
    grouping_keys,
    split_artists,
)
from downtify.server_identity import ServerIdentity
from downtify.transcode import (
    FORMATS,
    Transcoder,
    cache_key,
    ffmpeg_args,
    normalize_bitrate,
    serve_original,
)

_HAS_FFMPEG = bool(shutil.which('ffmpeg'))
_needs_ffmpeg = pytest.mark.skipif(not _HAS_FFMPEG, reason='no ffmpeg')
NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


def _entry(file: str, **kw: Any) -> dict[str, Any]:
    row = {
        'file': file,
        'title': kw.pop('title', Path(file).stem),
        'artist': 'Portishead',
        'album': 'Dummy',
        'album_artist': '',
        'track_number': 1,
        'year': '1994',
        'duration': 200.0,
        'codec': 'mp3',
        'bitrate': 320000,
        'sample_rate': 44100,
        'channels': 2,
        'has_cover': True,
        'cover_px': 600,
        'added': 1,
        'size': 1000,
        'playlists': [],
    }
    row.update(kw)
    return row


# ── library sync ────────────────────────────────────────────────────────


def test_split_artists_matches_the_web_app():
    assert split_artists('A, B') == ['A', 'B']
    assert split_artists('A; B, C') == ['A', 'B, C']
    assert split_artists('AC/DC') == ['AC/DC']
    assert split_artists('A / B') == ['A', 'B']
    assert split_artists('') == []


def test_grouping_keys():
    one = grouping_keys({'artist': 'Portishead', 'album': 'Dummy'})
    same = grouping_keys({'artist': 'PORTISHEAD', 'album': 'dummy'})
    assert one['album_artist'] == 'Portishead'
    assert one['album_id'] == same['album_id']
    assert one['album_id']
    assert one['artist_id'] == same['artist_id']
    assert not grouping_keys({'artist': 'X', 'album': ''})['album_id']
    assert (
        grouping_keys({
            'artist': 'X, Y',
            'album_artist': 'Various',
            'album': 'Z',
        })['album_artist']
        == 'Various'
    )


def _sync(tmp_path) -> LibrarySync:
    return LibrarySync(tmp_path / 'lib.db')


def test_first_sync_is_full_and_ids_are_stable(tmp_path):
    sync = _sync(tmp_path)
    cursor = sync.refresh([_entry('a.mp3'), _entry('b.mp3')])
    first = sync.changes(0)

    assert first['full'] is True
    assert first['cursor'] == cursor == 2
    ids = {t['file']: t['id'] for t in first['tracks']}
    assert sync.refresh([_entry('a.mp3'), _entry('b.mp3')]) == cursor
    again = {t['file']: t['id'] for t in sync.changes(0)['tracks']}
    assert again == ids
    assert sync.changes(cursor) == {
        'cursor': cursor,
        'full': False,
        'tracks': [],
        'deleted': [],
    }


def test_a_retag_in_place_keeps_the_id_and_shows_up_as_changed(tmp_path):
    sync = _sync(tmp_path)
    cursor = sync.refresh([_entry('a.mp3')])
    track_id = sync.changes(0)['tracks'][0]['id']

    sync.refresh([_entry('a.mp3', album='Dummy (Deluxe)', size=1200)])
    changed = sync.changes(cursor)

    assert [t['id'] for t in changed['tracks']] == [track_id]
    assert changed['tracks'][0]['album'] == 'Dummy (Deluxe)'


def test_a_moved_file_keeps_its_id(tmp_path):
    sync = _sync(tmp_path)
    sync.refresh([_entry('Roads.mp3')])
    track_id = sync.changes(0)['tracks'][0]['id']

    sync.refresh([_entry('Portishead/Dummy/Roads.mp3')])

    assert sync.path_for(track_id) == 'Portishead/Dummy/Roads.mp3'
    assert sync.changes(0)['tracks'][0]['id'] == track_id


def test_a_renamed_file_keeps_its_id_by_its_tags(tmp_path):
    sync = _sync(tmp_path)
    sync.refresh([_entry('Portishead - Roads.mp3', title='Roads')])
    track_id = sync.changes(0)['tracks'][0]['id']

    sync.refresh([_entry('01 - Roads.mp3', title='Roads', size=1001)])

    assert sync.path_for(track_id) == '01 - Roads.mp3'


def test_an_ambiguous_move_gets_a_new_id(tmp_path):
    sync = _sync(tmp_path)
    sync.refresh([
        _entry('x/Roads.mp3', title='Roads'),
        _entry('y/Roads.mp3', title='Roads'),
    ])
    old = {t['id'] for t in sync.changes(0)['tracks']}

    cursor = sync.cursor()
    sync.refresh([_entry('z/Roads.mp3', title='Roads')])
    after = sync.changes(cursor)

    assert after['tracks'][0]['id'] not in old
    assert set(after['deleted']) == old


def test_removed_tracks_are_reported_then_forgotten(tmp_path):
    sync = _sync(tmp_path)
    sync.refresh([_entry('a.mp3'), _entry('b.mp3')], now=NOW)
    ids = {t['file']: t['id'] for t in sync.changes(0)['tracks']}
    cursor = sync.cursor()

    sync.refresh([_entry('a.mp3')], now=NOW)
    assert sync.changes(cursor)['deleted'] == [ids['b.mp3']]
    assert sync.row_for(ids['b.mp3']) is None

    later = NOW + timedelta(days=TOMBSTONE_DAYS + 1)
    sync.refresh([_entry('a.mp3')], now=later)
    stale = sync.changes(cursor)
    assert stale['full'] is True
    assert [t['id'] for t in stale['tracks']] == [ids['a.mp3']]


def test_a_cursor_from_the_future_gets_a_full_list(tmp_path):
    sync = _sync(tmp_path)
    sync.refresh([_entry('a.mp3')])
    assert sync.changes(999)['full'] is True


def test_ids_for_paths(tmp_path):
    sync = _sync(tmp_path)
    sync.refresh([_entry('a.mp3'), _entry('b.mp3')])
    found = sync.ids_for_paths(['a.mp3', 'nope.mp3'])
    assert list(found) == ['a.mp3']


# ── transcoding ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ('value', 'expected'),
    [(160, 160), (150, 160), ('96', 96), (1000, 320), (0, 0), ('x', 0)],
)
def test_normalize_bitrate(value, expected):
    assert normalize_bitrate(value) == expected


@pytest.mark.parametrize(
    ('codec', 'bps', 'kbps', 'original'),
    [
        ('mp3', 128_000, 160, True),
        ('aac', 170_000, 160, True),  # VBR margin
        ('opus', 256_000, 160, False),
        ('flac', 900_000, 320, False),
        ('mp3', 0, 160, False),
        ('', 100_000, 160, False),
    ],
)
def test_serve_original(codec, bps, kbps, original):
    assert serve_original(codec, bps, kbps) is original


def test_ffmpeg_args(tmp_path):
    args = ffmpeg_args(
        'ffmpeg', tmp_path / 'in.flac', tmp_path / 'out', FORMATS['opus'], 160
    )
    assert args[0] == 'ffmpeg'
    assert args[args.index('-i') + 1] == str(tmp_path / 'in.flac')
    assert args[args.index('-b:a') + 1] == '160k'
    assert args[args.index('-c:a') + 1] == 'libopus'
    assert '-vn' in args
    assert args[-1] == str(tmp_path / 'out')


def test_cache_key_follows_the_source_file(tmp_path):
    source = tmp_path / 'a.flac'
    source.write_bytes(b'x')
    first = cache_key(source, 'opus', 160)
    assert cache_key(source, 'opus', 128) != first
    assert cache_key(source, 'aac', 160) != first
    os.utime(source, ns=(1, 1))
    assert cache_key(source, 'opus', 160) != first


def _fake_ffmpeg(tmp_path: Path, delay: float = 0.3) -> tuple[str, Path]:
    """A stand-in ffmpeg: waits, notes the run, writes the last arg."""

    runs = tmp_path / 'runs.log'
    script = tmp_path / 'fake-ffmpeg'
    script.write_text(
        '#!/bin/sh\n'
        f'echo run >> "{runs}"\n'
        f'sleep {delay}\n'
        'for last; do :; done\n'
        'printf transcoded > "$last"\n'
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script), runs


def _sources(tmp_path: Path, count: int) -> list[Path]:
    paths = []
    for i in range(count):
        path = tmp_path / f'song{i}.flac'
        path.write_bytes(b'flac' * (i + 1))
        paths.append(path)
    return paths


def test_concurrent_transcodes_are_capped(tmp_path):
    ffmpeg, _runs = _fake_ffmpeg(tmp_path)
    transcoder = Transcoder(
        tmp_path / 'cache', max_concurrent=2, ffmpeg=ffmpeg
    )
    peak = 0

    async def scenario():
        nonlocal peak
        jobs = [
            asyncio.ensure_future(transcoder.get(s, 'opus', 160))
            for s in _sources(tmp_path, 5)
        ]
        while not all(j.done() for j in jobs):
            peak = max(peak, transcoder.running)
            await asyncio.sleep(0.02)
        return [j.result() for j in jobs]

    outputs = asyncio.run(scenario())
    assert peak == 2
    assert all(p.read_bytes() == b'transcoded' for p in outputs)


def test_same_copy_is_made_once_and_then_cached(tmp_path):
    ffmpeg, runs = _fake_ffmpeg(tmp_path)
    transcoder = Transcoder(tmp_path / 'cache', ffmpeg=ffmpeg)
    source = _sources(tmp_path, 1)[0]

    async def scenario():
        first, second = await asyncio.gather(
            transcoder.get(source, 'opus', 160),
            transcoder.get(source, 'opus', 160),
        )
        third = await transcoder.get(source, 'opus', 160)
        return first, second, third

    first, second, third = asyncio.run(scenario())
    assert first == second == third
    assert runs.read_text().count('run') == 1


def test_a_transcode_nobody_waits_for_is_stopped(tmp_path):
    ffmpeg, _runs = _fake_ffmpeg(tmp_path, delay=5)
    transcoder = Transcoder(tmp_path / 'cache', ffmpeg=ffmpeg)
    source = _sources(tmp_path, 1)[0]

    async def scenario():
        job = asyncio.ensure_future(transcoder.get(source, 'opus', 160))
        await asyncio.sleep(0.3)
        job.cancel()
        with pytest.raises(asyncio.CancelledError):
            await job
        await asyncio.sleep(0.2)

    started = time.monotonic()
    asyncio.run(scenario())
    assert time.monotonic() - started < 3
    cache = tmp_path / 'cache'
    assert not any(cache.iterdir()) if cache.exists() else True
    assert transcoder.running == 0


def test_the_cache_stays_under_its_size(tmp_path):
    transcoder = Transcoder(tmp_path / 'cache', max_bytes=250, ffmpeg='x')
    cache = tmp_path / 'cache'
    cache.mkdir()
    for i in range(4):
        path = cache / f'{i}.opus'
        path.write_bytes(b'x' * 100)
        os.utime(path, (1000 + i, 1000 + i))

    assert transcoder.prune() == 2
    assert sorted(p.name for p in cache.iterdir()) == ['2.opus', '3.opus']


def test_without_ffmpeg_there_is_no_transcoding(tmp_path):
    transcoder = Transcoder(tmp_path, ffmpeg='')
    assert transcoder.capability() == {
        'available': False,
        'formats': [],
        'bitrates': [],
    }


# ── real audio (ffmpeg) ─────────────────────────────────────────────────


def _make_mp3(path: Path, seconds: int = 4, cover: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            'ffmpeg',
            '-nostdin',
            '-loglevel',
            'error',
            '-y',
            '-f',
            'lavfi',
            '-i',
            f'sine=frequency=440:duration={seconds}',
            '-c:a',
            'libmp3lame',
            '-b:a',
            '192k',
            str(path),
        ],
        check=True,
    )
    tags = ID3()
    tags.add(TIT2(encoding=3, text='Roads'))
    tags.add(TPE1(encoding=3, text='Portishead'))
    tags.add(TALB(encoding=3, text='Dummy'))
    if cover:
        jpeg = subprocess.run(
            [
                'ffmpeg',
                '-nostdin',
                '-loglevel',
                'error',
                '-f',
                'lavfi',
                '-i',
                'color=c=blue:s=640x640',
                '-frames:v',
                '1',
                '-f',
                'image2',
                '-c:v',
                'mjpeg',
                'pipe:1',
            ],
            capture_output=True,
            check=True,
        ).stdout
        tags.add(APIC(encoding=3, mime='image/jpeg', type=3, data=jpeg))
    tags.save(str(path))
    return path


@_needs_ffmpeg
def test_audio_format_is_read_from_the_file(tmp_path):
    meta = read_audio_metadata(_make_mp3(tmp_path / 'a.mp3'))
    assert meta['codec'] == 'mp3'
    assert 180_000 <= meta['bitrate'] <= 200_000
    assert meta['sample_rate'] in {44100, 48000}
    assert meta['channels'] >= 1


@_needs_ffmpeg
def test_a_real_opus_transcode(tmp_path):
    source = _make_mp3(tmp_path / 'a.mp3', cover=False)
    transcoder = Transcoder(tmp_path / 'cache')
    out = asyncio.run(transcoder.get(source, 'opus', 96))
    assert out.suffix == '.opus'
    assert read_audio_metadata(out)['codec'] == 'opus'


@_needs_ffmpeg
def test_cover_sizes_are_made_once(tmp_path, monkeypatch):
    source = _make_mp3(tmp_path / 'a.mp3')
    thumbs = CoverThumbs(tmp_path / 'thumbs')

    full = thumbs.get(source, 0)
    small = thumbs.get(source, 150)
    assert full is not None
    assert small is not None
    assert len(small[0]) < len(full[0])
    assert small[1] == 'image/jpeg'
    assert small[2] != full[2]

    def boom(*_args):
        raise AssertionError('re-extracted')

    monkeypatch.setattr('downtify.cover_thumbs.extract_cover_art', boom)
    assert thumbs.get(source, 150)[0] == small[0]


@pytest.mark.parametrize(
    ('value', 'size'),
    [('150', 150), (100, 150), ('600', 600), ('full', 0), ('', 0), (900, 0)],
)
def test_normalize_size(value, size):
    assert normalize_size(value) == size


# ── listens from an app ─────────────────────────────────────────────────


def test_a_play_reported_twice_counts_once(tmp_path):
    store = DiscoverStore(tmp_path / 'lib.db')
    store.record_listen('Air', play_id='p1')
    row = store.record_listen('Air', play_id='p1')
    assert row['plays'] == 1
    assert store.record_listen('Air', play_id='p2')['plays'] == 2


def test_a_late_report_never_moves_last_played_back(tmp_path):
    store = DiscoverStore(tmp_path / 'lib.db')
    store.record_listen('Air', when=NOW)
    row = store.record_listen('Air', when=NOW - timedelta(days=3))
    assert row['last_played'] == NOW.isoformat()
    assert row['plays'] == 2


# ── the routes ──────────────────────────────────────────────────────────


@pytest.fixture
def app_dirs(tmp_path, monkeypatch):
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
        'identity',
        'downloader',
        'settings',
        'library_sync',
        'transcoder',
        'cover_thumbs',
        'likes',
        'discover',
        'metadata_cache',
        'track_index',
        'playlist_catalog',
    ):
        monkeypatch.setattr(api.state, name, getattr(api.state, name, None))
    return downloads, data


@pytest.fixture
def client(app_dirs):
    downloads, data = app_dirs
    app = main.build_app()
    main._open_library_stores(data / 'downtify_monitor.db')
    return TestClient(app)


def _library(client) -> dict[str, Any]:
    response = client.get('/api/v1/library')
    assert response.status_code == 200
    return response.json()


@_needs_ffmpeg
def test_library_feed_over_http(client, app_dirs):
    downloads, _data = app_dirs
    _make_mp3(downloads / 'Portishead - Roads.mp3')

    first = _library(client)
    assert first['full'] is True
    track = first['tracks'][0]
    assert track['title'] == 'Roads'
    assert track['codec'] == 'mp3'
    assert track['album_id']

    etag = client.get('/api/v1/library').headers['etag']
    again = client.get('/api/v1/library', headers={'If-None-Match': etag})
    assert again.status_code == 304
    assert (
        client.get(f'/api/v1/library?since={first["cursor"]}').json()['tracks']
        == []
    )
    assert (
        client.get(f'/api/v1/tracks/{track["id"]}').json()['id'] == track['id']
    )
    assert client.get('/api/v1/tracks/tnope').status_code == 404


@_needs_ffmpeg
def test_stream_supports_range(client, app_dirs):
    downloads, _data = app_dirs
    path = _make_mp3(downloads / 'Portishead - Roads.mp3')
    track_id = _library(client)['tracks'][0]['id']
    url = f'/api/v1/tracks/{track_id}/stream'

    whole = client.get(url)
    assert whole.status_code == 200
    assert whole.headers['accept-ranges'] == 'bytes'
    assert int(whole.headers['content-length']) == path.stat().st_size
    assert whole.headers['content-type'] == 'audio/mpeg'

    part = client.get(url, headers={'Range': 'bytes=100-199'})
    assert part.status_code == 206
    assert part.content == path.read_bytes()[100:200]
    assert part.headers['content-range'] == (
        f'bytes 100-199/{path.stat().st_size}'
    )

    head = client.head(url)
    assert head.status_code == 200
    assert head.content == b''

    saved = client.get(url + '?download=true')
    assert 'attachment' in saved.headers['content-disposition']


@_needs_ffmpeg
def test_stream_transcodes_and_seeks(client, app_dirs):
    downloads, _data = app_dirs
    _make_mp3(downloads / 'Portishead - Roads.mp3')
    track_id = _library(client)['tracks'][0]['id']
    url = f'/api/v1/tracks/{track_id}/stream?format=opus&bitrate=96'

    whole = client.get(url)
    assert whole.status_code == 200
    assert whole.headers['x-downtify-transcoded'] == 'opus/96'
    assert whole.headers['content-type'] == 'audio/ogg'
    size = int(whole.headers['content-length'])

    part = client.get(url, headers={'Range': f'bytes={size // 2}-'})
    assert part.status_code == 206
    assert part.content == whole.content[size // 2 :]

    # 192 kbps mp3 at "mp3 320": the original already fits.
    fits = client.get(
        f'/api/v1/tracks/{track_id}/stream?format=mp3&bitrate=320'
    )
    assert fits.headers['x-downtify-transcoded'] == 'no'
    assert client.get(url.replace('opus', 'wav')).status_code == 400


@_needs_ffmpeg
def test_cover_route(client, app_dirs):
    downloads, _data = app_dirs
    _make_mp3(downloads / 'Portishead - Roads.mp3')
    track_id = _library(client)['tracks'][0]['id']

    small = client.get(f'/api/v1/tracks/{track_id}/cover?size=150')
    assert small.status_code == 200
    assert small.headers['content-type'] == 'image/jpeg'
    again = client.get(
        f'/api/v1/tracks/{track_id}/cover?size=150',
        headers={'If-None-Match': small.headers['etag']},
    )
    assert again.status_code == 304


@_needs_ffmpeg
def test_likes_by_track_id(client, app_dirs):
    downloads, _data = app_dirs
    _make_mp3(downloads / 'Portishead - Roads.mp3')
    track_id = _library(client)['tracks'][0]['id']

    liked = client.put(
        '/api/v1/likes', json={'track_id': track_id, 'liked': True}
    )
    assert liked.json() == {'track_id': track_id, 'liked': True}
    assert client.get('/api/v1/likes').json() == {'track_ids': [track_id]}
    assert client.put('/api/v1/likes', json={}).status_code == 400
    playlists = client.get('/api/v1/playlists').json()
    assert playlists[0]['liked'] is True
    assert playlists[0]['track_ids'] == [track_id]


@_needs_ffmpeg
def test_signed_stream_url_for_a_cast_receiver(client, app_dirs):
    downloads, _data = app_dirs
    _make_mp3(downloads / 'Portishead - Roads.mp3')
    store = api.state.auth
    store.set_password('correct horse battery')
    store.set_require_sign_in(True)
    _device, token = store.create_device('Pixel')
    headers = {'Authorization': f'Bearer {token}'}
    track_id = client.get('/api/v1/library', headers=headers).json()['tracks'][
        0
    ]['id']
    path = f'/api/v1/tracks/{track_id}/stream'

    signed = client.post(
        '/api/v1/sign',
        json={'items': [{'path': path, 'params': {'format': 'original'}}]},
        headers=headers,
    ).json()
    url = signed['urls'][0]
    assert 'sig=' in url
    assert token not in url

    assert client.get(path).status_code == 401  # no credentials
    ranged = client.get(url, headers={'Range': 'bytes=0-9'})
    assert ranged.status_code == 206
    assert client.get(url.replace('original', 'opus')).status_code == 401
    refused = client.post(
        '/api/v1/sign',
        json={'items': [{'path': '/api/settings'}]},
        headers=headers,
    )
    assert refused.status_code == 400


@_needs_ffmpeg
def test_listen_by_track_id(client, app_dirs):
    downloads, _data = app_dirs
    _make_mp3(downloads / 'Portishead - Roads.mp3')
    track_id = _library(client)['tracks'][0]['id']

    first = client.post(
        '/api/discover/listens',
        json={
            'track_id': track_id,
            'play_id': 'abc',
            'played_at': '2026-09-20T10:00:00Z',
        },
    ).json()
    again = client.post(
        '/api/discover/listens',
        json={'track_id': track_id, 'play_id': 'abc'},
    ).json()
    assert first['name'] == 'Portishead'
    assert first['last_played'].startswith('2026-09-20')
    assert again['plays'] == 1


# ── LAN discovery ───────────────────────────────────────────────────────


def test_instance_name_is_a_safe_dns_sd_label():
    assert instance_name('nas.local') == 'nas local'
    assert instance_name('  ') == 'Downtify'
    assert len(instance_name('é' * 100).encode()) <= 63


def test_txt_record(tmp_path):
    identity = ServerIdentity(tmp_path)
    record = txt_record(identity, version='3.2.0', port=8000, scheme='http')
    assert record == {
        'id': identity.server_id,
        'name': identity.name,
        'version': '3.2.0',
        'api': '1',
        'port': '8000',
        'scheme': 'http',
        'path': '/',
    }


@pytest.mark.parametrize(
    ('value', 'enabled'),
    [
        ('', True),
        ('true', True),
        ('false', False),
        ('0', False),
        ('off', False),
    ],
)
def test_discovery_can_be_turned_off(monkeypatch, value, enabled):
    monkeypatch.setenv('DOWNTIFY_DISCOVERY', value)
    assert discovery_enabled() is enabled


def test_a_bound_host_is_the_only_address_announced():
    assert local_addresses('192.168.1.20') == ['192.168.1.20']
    assert all(not a.startswith('127.') for a in local_addresses('0.0.0.0'))
