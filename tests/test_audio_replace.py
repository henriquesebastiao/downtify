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
from mutagen.flac import FLAC, Picture
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


def test_a_pasted_soundcloud_link_is_that_track(monkeypatch):
    url = 'https://soundcloud.com/portishead/roads'
    monkeypatch.setattr(
        providers,
        'soundcloud_track_from_url',
        lambda link: {
            'name': 'Roads',
            'artist': 'Portishead',
            'duration': 305,
            'cover_url': 'https://i1.sndcdn.com/roads-t500x500.jpg',
            'url': url,
        },
    )

    found = audio_replace.candidates(f'{url}?si=share')

    assert found == [
        {
            'video_id': url,
            'title': 'Roads',
            'artist': 'Portishead',
            'album': '',
            'duration': 305,
            'thumbnail': 'https://i1.sndcdn.com/roads-t500x500.jpg',
            'source': 'link',
            'url': url,
        }
    ]


def test_an_unreadable_soundcloud_link_is_refused(monkeypatch):
    def fail(link):
        raise RuntimeError('HTTP Error 404')

    monkeypatch.setattr(providers, 'soundcloud_track_from_url', fail)

    with pytest.raises(audio_replace.ReplaceError, match='SoundCloud'):
        audio_replace.candidates('https://soundcloud.com/portishead/roads')


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


def _set_flac_pictures(path: Path, count: int, label: str) -> list[bytes]:
    audio = FLAC(path)
    audio.clear_pictures()
    for index in range(count):
        picture = Picture()
        picture.type = 3 if index == 0 else 4
        picture.mime = 'image/jpeg'
        picture.desc = f'{label} {index}'
        picture.width = picture.height = 1
        picture.depth = 24
        picture.data = _JPEG + f'{label} {index}'.encode()
        audio.add_picture(picture)
    audio.save()
    return [picture.write() for picture in audio.pictures]


def _audio_hash(path: Path) -> bytes:
    result = subprocess.run(
        [
            'ffmpeg',
            '-nostdin',
            '-v',
            'error',
            '-i',
            str(path),
            '-map',
            '0:a:0',
            '-f',
            'hash',
            '-hash',
            'sha256',
            '-',
        ],
        check=True,
        capture_output=True,
    )
    return result.stdout


@_needs_ffmpeg
@pytest.mark.parametrize('picture_count', [0, 1, 3])
@pytest.mark.parametrize('has_comments', [True, False])
def test_copying_flac_tags_replaces_all_replacement_artwork(
    tmp_path: Path, picture_count: int, has_comments: bool
) -> None:
    source = _tagged(tmp_path / 'old.flac', seconds=1)
    pictures = _set_flac_pictures(source, picture_count, 'original')
    if not has_comments:
        FLAC(source).delete()
    target = _tagged(tmp_path / 'new.flac', seconds=2)
    _set_flac_pictures(target, 2, 'replacement')
    original = source.read_bytes()
    audio = _audio_hash(target)

    audio_replace.copy_tags(source, target)

    copied = FLAC(target)
    assert [picture.write() for picture in copied.pictures] == pictures
    assert dict(copied.tags) == dict(FLAC(source).tags or {})
    assert source.read_bytes() == original
    assert _audio_hash(target) == audio


@_needs_ffmpeg
def test_copying_flac_tags_twice_does_not_duplicate_pictures(
    tmp_path: Path,
) -> None:
    source = _tagged(tmp_path / 'old.flac', seconds=1)
    pictures = _set_flac_pictures(source, 3, 'original')
    target = _tagged(tmp_path / 'new.flac', seconds=2)

    audio_replace.copy_tags(source, target)
    audio_replace.copy_tags(source, target)

    assert [picture.write() for picture in FLAC(target).pictures] == pictures


@_needs_ffmpeg
def test_copying_flac_artwork_accepts_uppercase_extensions(
    tmp_path: Path,
) -> None:
    source = _tagged(tmp_path / 'old.flac', seconds=1)
    pictures = _set_flac_pictures(source, 1, 'original')
    target = _tagged(tmp_path / 'new.flac', seconds=2)
    source = source.rename(source.with_suffix('.FLAC'))
    target = target.rename(target.with_suffix('.FLAC'))

    audio_replace.copy_tags(source, target)

    assert [picture.write() for picture in FLAC(target).pictures] == pictures


@_needs_ffmpeg
@pytest.mark.parametrize('fmt', ['mp3', 'm4a', 'opus', 'ogg'])
def test_copying_tags_still_replaces_artwork_in_other_formats(
    tmp_path: Path, fmt: str
) -> None:
    source = _tagged(tmp_path / f'old.{fmt}', seconds=1)
    target = _audio(tmp_path / f'new.{fmt}', seconds=2)
    embed_metadata(
        target,
        {**SONG, 'name': 'Other song'},
        download_cover=True,
        cover_bytes=_JPEG + b'replacement',
    )

    audio_replace.copy_tags(source, target)

    assert main._extract_cover(target) == (_JPEG, 'image/jpeg')
    assert read_audio_metadata(target)['title'] == SONG['name']
    assert (
        read_track_lyrics(target)['plain']
        == read_track_lyrics(source)['plain']
    )


@_needs_ffmpeg
@pytest.mark.parametrize('picture_count', [0, 2])
def test_downloaded_flac_replacement_keeps_only_original_artwork(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, picture_count: int
) -> None:
    target = _tagged(tmp_path / 'Roads.flac', seconds=1)
    pictures = _set_flac_pictures(target, picture_count, 'original')
    before = dict(FLAC(target).tags)
    sidecar = target.with_suffix('.lrc').read_bytes()
    old_mtime_ns = 1_600_000_000_000_000_000
    os.utime(target, ns=(old_mtime_ns, old_mtime_ns))
    loader = _FakeDownloader()
    downloaded: list[bytes] = []

    def fetch(
        _video_id: str,
        target_dir: Path,
        basename: str,
        **_kwargs: Any,
    ) -> Path:
        staged = _tagged(target_dir / f'{basename}.flac', seconds=2)
        _set_flac_pictures(staged, 2, 'replacement')
        downloaded.append(_audio_hash(staged))
        return staged

    monkeypatch.setattr(loader, 'fetch_audio', fetch)

    result = audio_replace.replace_audio(
        loader, target, 'bbbbbbbbbbb', song=SONG
    )

    assert [picture.write() for picture in FLAC(target).pictures] == pictures
    assert dict(FLAC(target).tags) == before
    assert result['duration_after'] > result['duration_before']
    assert _audio_hash(target) == downloaded[0]
    assert target.stat().st_mtime_ns == old_mtime_ns
    assert target.with_suffix('.lrc').read_bytes() == sidecar
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        'Roads.flac',
        'Roads.lrc',
    ]


@_needs_ffmpeg
@pytest.mark.parametrize('picture_count', [0, 2])
def test_uploaded_flac_replacement_keeps_only_original_artwork(
    tmp_path: Path, picture_count: int
) -> None:
    target = _tagged(tmp_path / 'Roads.flac', seconds=1)
    pictures = _set_flac_pictures(target, picture_count, 'original')
    before = dict(FLAC(target).tags)
    sidecar = target.with_suffix('.lrc').read_bytes()
    old_mtime_ns = 1_600_000_000_000_000_000
    os.utime(target, ns=(old_mtime_ns, old_mtime_ns))
    upload = audio_replace.upload_staging_path(target, 'flac')
    _tagged(upload, seconds=2)
    _set_flac_pictures(upload, 2, 'replacement')
    audio = _audio_hash(upload)

    result = audio_replace.replace_from_file(target, upload)

    assert [picture.write() for picture in FLAC(target).pictures] == pictures
    assert dict(FLAC(target).tags) == before
    assert result['converted'] is False
    assert result['duration_after'] > result['duration_before']
    assert _audio_hash(target) == audio
    assert target.stat().st_mtime_ns == old_mtime_ns
    assert target.with_suffix('.lrc').read_bytes() == sidecar
    assert not upload.exists()


@_needs_ffmpeg
def test_failed_flac_artwork_copy_leaves_original_file_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _tagged(tmp_path / 'Roads.flac', seconds=1)
    _set_flac_pictures(target, 2, 'original')
    original = target.read_bytes()
    upload = audio_replace.upload_staging_path(target, 'flac')
    _tagged(upload, seconds=2)
    copy_tags = audio_replace.copy_tags

    def fail_after_copy(source: Path, staged: Path) -> None:
        copy_tags(source, staged)
        raise audio_replace.ReplaceError('Could not save artwork')

    monkeypatch.setattr(audio_replace, 'copy_tags', fail_after_copy)

    with pytest.raises(audio_replace.ReplaceError, match='save artwork'):
        audio_replace.replace_from_file(target, upload)

    assert target.read_bytes() == original
    assert not upload.exists()


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


def test_replace_route_takes_a_soundcloud_track(client, monkeypatch):
    client.downloads.mkdir(parents=True, exist_ok=True)
    (client.downloads / 'Roads.mp3').write_bytes(b'')
    monkeypatch.setattr(
        api,
        'read_audio_metadata',
        lambda path: {'title': 'Roads', 'artist': 'Portishead'},
    )
    replaced = []
    monkeypatch.setattr(
        audio_replace,
        'replace_audio',
        lambda downloader, target, video_id, **kw: replaced.append(video_id),
    )
    spawned = []
    monkeypatch.setattr(
        api, 'spawn_task', lambda coro, name=None: spawned.append(coro)
    )

    started = client.post(
        '/api/library/replace',
        json={
            'file': 'Roads.mp3',
            'video_id': 'https://soundcloud.com/portishead/roads?si=x',
        },
    ).json()
    monkeypatch.setattr(api.state, 'loop', None)
    asyncio.run(spawned[0])

    track_url = 'https://soundcloud.com/portishead/roads'
    job = api.state.download_jobs[started['job_id']]
    assert job['status'] == 'done', job
    assert replaced == [track_url]
    assert job['song']['url'] == track_url
    assert job['song']['replace']['video_id'] == track_url


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
