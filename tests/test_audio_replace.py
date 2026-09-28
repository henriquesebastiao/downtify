"""Replacing a library track's audio with a version picked by hand
(downtify/audio_replace.py and /api/library/replace)."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
from mutagen import File as MutagenFile
from starlette.testclient import TestClient

import main
from downtify import api, audio_replace, providers
from downtify.downloader import embed_lyrics, embed_metadata
from downtify.library_metadata import read_audio_metadata
from downtify.lyrics import Lyrics, read_track_lyrics

_needs_ffmpeg = pytest.mark.skipif(
    shutil.which('ffmpeg') is None, reason='no ffmpeg'
)

_CODECS = {
    'mp3': ['-c:a', 'libmp3lame', '-b:a', '64k'],
    'flac': ['-c:a', 'flac'],
    'm4a': ['-c:a', 'aac', '-b:a', '64k'],
    'opus': ['-c:a', 'libopus', '-b:a', '32k'],
    'ogg': ['-c:a', 'libvorbis', '-q:a', '1'],
}

# A 1x1 JPEG, enough for every container's picture tag.
_JPEG = bytes.fromhex(
    'ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707'
    '070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c'
    '1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100'
    'ffc4001f0000010501010101010100000000000000000102030405060708090a0bff'
    'c400b5100002010303020403050504040000017d01020300041105122131410613'
    '516107227114328191a1082342b1c11552d1f02433627282090a161718191a2526'
    '2728292a3435363738393a434445464748494a535455565758595a636465666768'
    '696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7'
    'a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3'
    'e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda0008010100003f00fbd3ffd9'
)

SONG = {
    'name': 'Roads',
    'artists': ['Portishead'],
    'album_name': 'Dummy',
    'album_artist': 'Portishead',
    'year': '1994',
    'track_number': 3,
}


def _audio(path: Path, seconds: float) -> Path:
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
            *_CODECS[path.suffix.lstrip('.')],
            str(path),
        ],
        check=True,
    )
    return path


def _tagged(path: Path, seconds: float = 3) -> Path:
    _audio(path, seconds)
    embed_metadata(path, SONG, download_cover=True, cover_bytes=_JPEG)
    embed_lyrics(path, Lyrics(synced='[00:01.00]Oh', plain='Oh'))
    return path


class _FakeDownloader:
    """``fetch_audio`` makes a longer tone instead of calling YouTube."""

    def __init__(self, seconds: float = 6, fail: bool = False) -> None:
        self.seconds = seconds
        self.fail = fail
        self.calls: list[dict[str, Any]] = []

    def fetch_audio(
        self, video_id, target_dir, basename, *, audio_format, **kw
    ) -> Path:
        self.calls.append({'video_id': video_id, 'format': audio_format})
        out = Path(target_dir) / f'{basename}.{audio_format}'
        if self.fail:
            # A half-finished download leaves something behind.
            (Path(target_dir) / f'{basename}.webm').write_bytes(b'partial')
            raise RuntimeError('Video unavailable')
        return _audio(out, self.seconds)


# ── Pieces ──────────────────────────────────────────────────────────────


def test_only_formats_downtify_writes_can_be_replaced(tmp_path):
    assert audio_replace.replacement_format(tmp_path / 'a.FLAC') == 'flac'
    with pytest.raises(audio_replace.ReplaceError, match='can be replaced'):
        audio_replace.replacement_format(tmp_path / 'a.wav')


def test_search_query():
    assert (
        audio_replace.search_query({'title': 'Roads', 'artist': 'A;B'})
        == 'A, B - Roads'
    )
    assert audio_replace.search_query({'title': 'Roads'}) == 'Roads'


def test_candidates_mix_both_sources_without_repeats(monkeypatch):
    monkeypatch.setattr(
        providers,
        'search_songs',
        lambda q, limit: [
            {
                'song_id': 'aaaaaaaaaaa',
                'name': 'Roads',
                'artists': ['Portishead'],
                'album_name': 'Dummy',
                'duration': 305,
                'cover_url': 'https://img/x.jpg',
            }
        ],
    )
    monkeypatch.setattr(
        providers,
        'youtube_search',
        lambda q, limit: [
            {'id': 'aaaaaaaaaaa', 'title': 'dup'},
            {
                'id': 'bbbbbbbbbbb',
                'title': 'Portishead - Roads (Live at Roseland)',
                'channel': 'Portishead',
                'duration': 360,
            },
            {
                'id': 'ccccccccccc',
                'title': 'Live now',
                'live_status': 'is_live',
            },
        ],
    )
    found = audio_replace.candidates('Portishead - Roads')
    assert [c['video_id'] for c in found] == ['aaaaaaaaaaa', 'bbbbbbbbbbb']
    assert found[0]['source'] == 'youtube-music'
    assert found[1]['source'] == 'youtube'
    assert found[1]['url'] == 'https://www.youtube.com/watch?v=bbbbbbbbbbb'


def test_a_pasted_link_is_that_video(monkeypatch):
    monkeypatch.setattr(
        providers,
        'song_from_video_id',
        lambda vid: {'name': 'Roads (Live)', 'artists': ['Portishead']},
    )
    found = audio_replace.candidates(
        'https://www.youtube.com/watch?v=bbbbbbbbbbb'
    )
    assert len(found) == 1
    assert found[0]['video_id'] == 'bbbbbbbbbbb'
    assert found[0]['title'] == 'Roads (Live)'
    assert found[0]['source'] == 'link'
    with pytest.raises(audio_replace.ReplaceError, match='one video'):
        audio_replace.candidates(
            'https://music.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxxxx'
        )


# ── Replacing ───────────────────────────────────────────────────────────


@_needs_ffmpeg
@pytest.mark.parametrize('fmt', ['mp3', 'flac', 'm4a', 'opus', 'ogg'])
def test_replacing_keeps_path_format_tags_and_date(tmp_path, fmt):
    target = _tagged(tmp_path / 'Portishead' / f'Roads.{fmt}')
    old_mtime = time.time() - 86400
    os.utime(target, (old_mtime, old_mtime))
    before = read_audio_metadata(target)

    result = audio_replace.replace_audio(
        _FakeDownloader(seconds=6), target, 'bbbbbbbbbbb', song=SONG
    )

    after = read_audio_metadata(target)
    assert result['duration_after'] > result['duration_before']
    assert after['duration'] > before['duration'] + 2
    for key in ('title', 'artist', 'album', 'year', 'track_number'):
        assert after[key] == before[key], key
    assert after['has_cover'] if 'has_cover' in after else True
    assert read_track_lyrics(target)['plain']
    assert abs(target.stat().st_mtime - old_mtime) < 1
    # Only the track (and its .lrc, untouched) is left in the folder.
    assert sorted(p.name for p in target.parent.iterdir()) == sorted([
        target.name,
        target.with_suffix('.lrc').name,
    ])


@_needs_ffmpeg
def test_the_cover_survives(tmp_path):
    target = _tagged(tmp_path / 'Roads.mp3')
    audio_replace.replace_audio(
        _FakeDownloader(), target, 'bbbbbbbbbbb', song=SONG
    )
    tags = MutagenFile(str(target)).tags
    assert tags.getall('APIC')[0].data == _JPEG


@_needs_ffmpeg
def test_a_failed_download_changes_nothing(tmp_path):
    target = _tagged(tmp_path / 'Roads.flac')
    original = target.read_bytes()

    with pytest.raises(RuntimeError, match='unavailable'):
        audio_replace.replace_audio(
            _FakeDownloader(fail=True), target, 'bbbbbbbbbbb', song=SONG
        )

    assert target.read_bytes() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        'Roads.flac',
        'Roads.lrc',
    ]


def test_a_missing_file_is_refused(tmp_path):
    with pytest.raises(audio_replace.ReplaceError, match='no longer'):
        audio_replace.replace_audio(
            _FakeDownloader(), tmp_path / 'gone.mp3', 'bbbbbbbbbbb', song=SONG
        )


# ── Over HTTP ───────────────────────────────────────────────────────────


@pytest.fixture
def client(tmp_path, monkeypatch):
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    downloads = tmp_path / 'downloads'
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', downloads)
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    for name in (
        'auth',
        'activity',
        'identity',
        'downloader',
        'settings',
        'metadata_cache',
        'track_index',
        'download_jobs',
    ):
        monkeypatch.setattr(api.state, name, getattr(api.state, name))
    monkeypatch.setattr(api.state, 'download_jobs', {})
    app = TestClient(main.build_app(), base_url='http://testserver')
    app.post(
        '/api/auth/login', json={'username': 'admin', 'password': 'downtify'}
    )
    app.downloads = downloads
    return app


def test_candidates_route(client, monkeypatch):
    client.downloads.mkdir(parents=True, exist_ok=True)
    target = client.downloads / 'Roads.mp3'
    target.write_bytes(b'')
    monkeypatch.setattr(
        api,
        'read_audio_metadata',
        lambda path: {
            'title': 'Roads',
            'artist': 'Portishead',
            'duration': 300,
        },
    )
    asked = []
    monkeypatch.setattr(
        audio_replace,
        'candidates',
        lambda q: (
            asked.append(q)
            or [{'video_id': 'bbbbbbbbbbb', 'duration': 310, 'title': 'x'}]
        ),
    )

    body = client.get(
        '/api/library/replace/candidates', params={'file': 'Roads.mp3'}
    ).json()
    assert asked == ['Portishead - Roads']
    assert body['track']['title'] == 'Roads'
    assert body['candidates'][0]['duration_diff'] == 10
    missing = client.get(
        '/api/library/replace/candidates', params={'file': 'nope.mp3'}
    )
    assert missing.status_code == 404


@_needs_ffmpeg
def test_replace_route_runs_a_queue_job(client, monkeypatch):
    target = _tagged(client.downloads / 'Roads.mp3', seconds=2)
    fake = _FakeDownloader(seconds=5)
    monkeypatch.setattr(api.state.downloader, 'fetch_audio', fake.fetch_audio)

    bad = client.post(
        '/api/library/replace', json={'file': 'Roads.mp3', 'video_id': 'x'}
    )
    assert bad.status_code == 400
    # The job runs in the background; here, right away on its own loop.
    spawned = []
    monkeypatch.setattr(
        api, 'spawn_task', lambda coro, name=None: spawned.append(coro)
    )
    started = client.post(
        '/api/library/replace',
        json={'file': 'Roads.mp3', 'video_id': 'bbbbbbbbbbb'},
    ).json()
    assert started['job_id'] == 'replace:Roads.mp3'
    assert len(spawned) == 1
    monkeypatch.setattr(api.state, 'loop', None)
    asyncio.run(spawned[0])

    job = api.state.download_jobs[started['job_id']]
    assert job['status'] == 'done', job
    assert read_audio_metadata(target)['duration'] > 4
    kinds = [e['kind'] for e in client.get('/api/activity').json()['entries']]
    assert 'audio_replaced' in kinds


def test_only_admins_replace_audio(client):
    api.state.auth.users.create('maria', 'correct horse battery')
    client.cookies.clear()
    client.post(
        '/api/auth/login',
        json={'username': 'maria', 'password': 'correct horse battery'},
    )
    refused = client.post(
        '/api/library/replace',
        json={'file': 'Roads.mp3', 'video_id': 'bbbbbbbbbbb'},
    )
    assert refused.status_code == 403
