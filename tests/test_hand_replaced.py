"""Replacing a track's audio from a file, and keeping hand-replaced files
from being downloaded over (downtify/hand_replaced.py,
audio_replace.replace_from_file, /api/library/replace/upload and
/protected; issue #582)."""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

import main
from downtify import api, audio_replace, library_only
from downtify import downloader as downloader_mod
from downtify.downloader import Downloader, embed_lyrics, embed_metadata
from downtify.hand_replaced import HandReplacedFiles
from downtify.library_metadata import read_audio_metadata
from downtify.library_upgrade import (
    JOB_SKIPPED,
    LibraryUpgradeRunner,
    UpgradeDeps,
    UpgradeOptions,
)
from downtify.lyrics import Lyrics, read_track_lyrics

_needs_ffmpeg = pytest.mark.skipif(
    shutil.which('ffmpeg') is None, reason='no ffmpeg'
)

_CODECS = {
    'mp3': ['-c:a', 'libmp3lame', '-b:a', '64k'],
    'flac': ['-c:a', 'flac'],
    'wav': ['-c:a', 'pcm_s16le'],
}

SONG = {
    'name': 'Roads',
    'artists': ['Portishead'],
    'album_name': 'Dummy',
    'album_artist': 'Portishead',
    'year': '1994',
    'track_number': 3,
}


def _audio(path: Path, seconds: float, freq: int = 440) -> Path:
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
            f'sine=frequency={freq}:duration={seconds}',
            *_CODECS[path.suffix.lstrip('.')],
            str(path),
        ],
        check=True,
    )
    return path


def _tagged(path: Path, seconds: float = 3) -> Path:
    _audio(path, seconds)
    embed_metadata(path, SONG)
    embed_lyrics(path, Lyrics(synced='[00:01.00]Oh', plain='Oh'))
    return path


# ── The store ───────────────────────────────────────────────────────────


def test_the_store_remembers_forgets_and_follows_renames(tmp_path):
    store = HandReplacedFiles(tmp_path / 'library.db')
    assert store.get('Roads.mp3') is None
    store.mark('Portishead\\Roads.mp3', 'file')
    entry = store.get('Portishead/Roads.mp3')
    assert entry['source'] == 'file'
    assert entry['replaced_at'] <= time.time()
    store.mark('Portishead/Roads.mp3', 'youtube')
    assert store.get('Portishead/Roads.mp3')['source'] == 'youtube'
    assert store.count() == 1

    store.rename('Portishead/Roads.mp3', 'Portishead/Roads (Dummy).mp3')
    assert not store.protected('Portishead/Roads.mp3')
    assert store.protected('Portishead/Roads (Dummy).mp3')

    assert store.forget('Portishead/Roads (Dummy).mp3')
    assert not store.forget('Portishead/Roads (Dummy).mp3')
    with pytest.raises(ValueError, match='unknown source'):
        store.mark('Roads.mp3', 'deemix')
    # A second store on the same database sees the same rows.
    store.mark('Roads.mp3', 'soundcloud')
    assert HandReplacedFiles(tmp_path / 'library.db').protected('Roads.mp3')


# ── Downloads leave hand-replaced files alone ───────────────────────────

_DOWNLOAD = {
    'name': 'Song',
    'artists': ['Artist'],
    'youtube_id': 'abc123def45',
    'album_name': 'Album',
    'cover_url': 'https://example.com/cover.jpg',
}


_reached: list[dict[str, Any]] = []


class _YoutubeDL:
    """Stands in for yt-dlp: reaching it means a download went ahead."""

    def __init__(self, opts):
        _reached.append(opts)
        raise RuntimeError('yt-dlp reached')


def test_a_download_doesnt_overwrite_a_hand_replaced_file(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(downloader_mod.yt_dlp, 'YoutubeDL', _YoutubeDL)
    _reached.clear()
    downloads = tmp_path / 'music'
    downloads.mkdir()
    loader = Downloader(downloads)  # "Download again if the file exists" on
    assert loader.overwrite_existing_files
    loader.hand_replaced = HandReplacedFiles(tmp_path / 'library.db')
    replaced = downloads / 'Artist - Song.mp3'
    replaced.write_bytes(b'the right version')
    loader.hand_replaced.mark('Artist - Song.mp3', 'file')
    outcomes = []
    loader.on_outcome = lambda song, outcome, filename=None: outcomes.append((
        outcome,
        filename,
    ))
    messages = []

    result = loader.download(
        dict(_DOWNLOAD),
        progress_cb=lambda pct, msg, provider=None: messages.append(msg),
    )

    assert result == 'Artist - Song.mp3'
    assert replaced.read_bytes() == b'the right version'
    assert not _reached
    assert messages == ['Kept: audio replaced by hand']
    assert outcomes
    assert outcomes[-1][0] == downloader_mod.OUTCOME_SKIPPED


def test_other_files_are_still_downloaded_again(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader_mod.yt_dlp, 'YoutubeDL', _YoutubeDL)
    _reached.clear()
    downloads = tmp_path / 'music'
    downloads.mkdir()
    loader = Downloader(downloads)
    loader.hand_replaced = HandReplacedFiles(tmp_path / 'library.db')
    (downloads / 'Artist - Song.mp3').write_bytes(b'old')
    loader.hand_replaced.mark('Artist - Other.mp3', 'file')

    with contextlib.suppress(Exception):
        loader.download(dict(_DOWNLOAD))
    assert _reached


def test_library_upgrade_keeps_hand_replaced_audio(tmp_path):
    store = HandReplacedFiles(tmp_path / 'library.db')
    store.mark('Roads.mp3', 'file')
    finished = []

    class _Db:
        @staticmethod
        def set_stage(*args):
            pass

        @staticmethod
        def finish_job(run_id, stored, state, **kw):
            finished.append((stored, state, kw.get('detail')))

    class _Deemix:
        @staticmethod
        def prepare(*args):
            raise AssertionError('hand-replaced audio must not be replaced')

    runner = object.__new__(LibraryUpgradeRunner)
    runner.db = _Db()
    runner.deps = UpgradeDeps(
        context=lambda: None,
        settings=dict,
        audio_replacement=_Deemix(),
        hand_replaced=store,
    )
    options = UpgradeOptions(categories=('audio',), replace_audio_deemix=True)

    runner._process(1, 'Roads.mp3', options, ['audio'])

    assert finished == [
        ('Roads.mp3', JOB_SKIPPED, 'Audio replaced by hand; kept')
    ]


# ── Replacing from a file ───────────────────────────────────────────────


@_needs_ffmpeg
def test_a_file_in_the_same_format_is_used_as_it_is(tmp_path):
    target = _tagged(tmp_path / 'Portishead' / 'Roads.mp3', seconds=2)
    old_mtime = time.time() - 86400
    os.utime(target, (old_mtime, old_mtime))
    upload = audio_replace.upload_staging_path(target, 'mp3')
    _audio(upload, 5, freq=880)
    audio_frames = upload.read_bytes()[-2000:]
    before = read_audio_metadata(target)

    result = audio_replace.replace_from_file(target, upload)

    after = read_audio_metadata(target)
    assert result['converted'] is False
    assert result['duration_after'] > result['duration_before'] + 2
    for key in ('title', 'artist', 'album', 'year', 'track_number'):
        assert after[key] == before[key], key
    assert read_track_lyrics(target)['plain']
    # The uploaded audio itself, not a re-encode of it.
    assert target.read_bytes().endswith(audio_frames)
    assert abs(target.stat().st_mtime - old_mtime) < 1
    assert sorted(p.name for p in target.parent.iterdir()) == sorted([
        target.name,
        target.with_suffix('.lrc').name,
    ])


@_needs_ffmpeg
@pytest.mark.parametrize(('own', 'sent'), [('mp3', 'wav'), ('flac', 'mp3')])
def test_another_format_is_converted_to_the_files_own(tmp_path, own, sent):
    target = _tagged(tmp_path / f'Roads.{own}', seconds=2)
    upload = audio_replace.upload_staging_path(target, sent)
    _audio(upload, 5)

    result = audio_replace.replace_from_file(target, upload, bitrate='128')

    assert result['converted'] is True
    assert target.suffix == f'.{own}'
    after = read_audio_metadata(target)
    assert after['title'] == 'Roads'
    assert after['duration'] > 4
    assert not upload.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([
        target.name,
        target.with_suffix('.lrc').name,
    ])


@_needs_ffmpeg
def test_a_file_that_isnt_audio_changes_nothing(tmp_path):
    target = _tagged(tmp_path / 'Roads.mp3', seconds=2)
    original = target.read_bytes()
    upload = audio_replace.upload_staging_path(target, 'mp3')
    upload.write_bytes(b'not audio at all' * 100)

    with pytest.raises(audio_replace.ReplaceError, match='not readable'):
        audio_replace.replace_from_file(target, upload)

    assert target.read_bytes() == original
    assert not upload.exists()


def test_only_audio_files_are_taken():
    assert audio_replace.upload_format('Roads (CD rip).FLAC') == 'flac'
    assert audio_replace.upload_format('roads.wav') == 'wav'
    for name in ('cover.jpg', 'roads', 'roads.exe'):
        with pytest.raises(audio_replace.ReplaceError):
            audio_replace.upload_format(name)


def test_uploads_are_staged_where_the_library_scan_skips_them(tmp_path):
    staged = audio_replace.upload_staging_path(tmp_path / 'Roads.mp3', 'wav')
    assert staged.parent == tmp_path
    assert '.downtify-upgrade' in staged.name
    assert staged.suffix == '.wav'


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
        'hand_replaced',
    ):
        monkeypatch.setattr(api.state, name, getattr(api.state, name))
    monkeypatch.setattr(api.state, 'download_jobs', {})
    app = TestClient(main.build_app(), base_url='http://testserver')
    app.post(
        '/api/auth/login', json={'username': 'admin', 'password': 'downtify'}
    )
    # The lifespan (not run by a bare TestClient) opens the stores.
    monkeypatch.setattr(
        api.state, 'hand_replaced', HandReplacedFiles(tmp_path / 'hand.db')
    )
    api.state.downloader.hand_replaced = api.state.hand_replaced
    app.downloads = downloads
    return app


def _upload(client, file: str, name: str, body: bytes) -> Any:
    return client.post(
        '/api/library/replace/upload',
        params={'file': file, 'name': name},
        content=body,
        headers={'Content-Type': 'application/octet-stream'},
    )


@_needs_ffmpeg
def test_the_upload_route_replaces_and_protects_the_file(client, tmp_path):
    target = _tagged(client.downloads / 'Roads.mp3', seconds=2)
    sent = _audio(tmp_path / 'from my computer.mp3', 5, freq=880)

    body = _upload(client, 'Roads.mp3', sent.name, sent.read_bytes()).json()

    assert body['file'] == 'Roads.mp3'
    assert body['converted'] is False
    assert body['duration_after'] > 4
    assert body['hand_replaced']['source'] == 'file'
    assert read_audio_metadata(target)['title'] == 'Roads'
    assert sorted(p.name for p in client.downloads.iterdir()) == [
        'Roads.lrc',
        'Roads.mp3',
    ]
    kinds = [e['kind'] for e in client.get('/api/activity').json()['entries']]
    assert 'audio_replaced' in kinds

    status = client.get(
        '/api/library/replace/protected', params={'file': 'Roads.mp3'}
    ).json()
    assert status['hand_replaced']['source'] == 'file'
    lifted = client.delete(
        '/api/library/replace/protected', params={'file': 'Roads.mp3'}
    ).json()
    assert lifted == {'file': 'Roads.mp3', 'forgotten': True}
    assert (
        client.get(
            '/api/library/replace/protected', params={'file': 'Roads.mp3'}
        ).json()['hand_replaced']
        is None
    )


@_needs_ffmpeg
def test_the_upload_route_refuses_bad_files(client):
    target = _tagged(client.downloads / 'Roads.mp3', seconds=2)
    original = target.read_bytes()

    wrong_kind = _upload(client, 'Roads.mp3', 'cover.jpg', b'jpeg')
    empty = _upload(client, 'Roads.mp3', 'roads.mp3', b'')
    garbage = _upload(client, 'Roads.mp3', 'roads.mp3', b'nope' * 500)
    missing = _upload(client, 'Gone.mp3', 'roads.mp3', b'x')

    assert wrong_kind.status_code == 400
    assert empty.status_code == 400
    assert garbage.status_code == 400
    assert missing.status_code == 404
    assert target.read_bytes() == original
    assert api.state.hand_replaced.get('Roads.mp3') is None
    assert sorted(p.name for p in client.downloads.iterdir()) == [
        'Roads.lrc',
        'Roads.mp3',
    ]


def test_a_youtube_replacement_protects_the_file_too(client, monkeypatch):
    client.downloads.mkdir(parents=True, exist_ok=True)
    (client.downloads / 'Roads.mp3').write_bytes(b'')
    monkeypatch.setattr(
        api,
        '_replaceable_track',
        lambda file: (client.downloads / file, {'title': 'Roads'}),
    )
    monkeypatch.setattr(
        audio_replace,
        'replace_audio',
        lambda *a, **kw: {'duration_before': 1, 'duration_after': 2},
    )
    monkeypatch.setattr(api, '_after_replacement', lambda *a: None)
    spawned = []
    monkeypatch.setattr(
        api, 'spawn_task', lambda coro, name=None: spawned.append(coro)
    )
    monkeypatch.setattr(api.state, 'loop', None)
    client.post(
        '/api/library/replace',
        json={'file': 'Roads.mp3', 'video_id': 'bbbbbbbbbbb'},
    )
    asyncio.run(spawned[0])

    assert api.state.hand_replaced.get('Roads.mp3')['source'] == 'youtube'


def test_only_admins_upload_or_lift(client):
    api.state.auth.users.create('maria', 'correct horse battery')
    client.cookies.clear()
    client.post(
        '/api/auth/login',
        json={'username': 'maria', 'password': 'correct horse battery'},
    )
    assert _upload(client, 'Roads.mp3', 'r.mp3', b'x').status_code == 403
    assert (
        client.delete(
            '/api/library/replace/protected', params={'file': 'Roads.mp3'}
        ).status_code
        == 403
    )


def test_library_only_mode_still_takes_a_file():
    # Searching YouTube is remote; a file from the admin's computer isn't.
    assert library_only.remote_route('/api/library/replace/candidates', 'GET')
    assert library_only.remote_route('/api/library/replace', 'POST')
    assert not library_only.remote_route('/api/library/replace/upload', 'POST')
    assert not library_only.remote_route(
        '/api/library/replace/protected', 'DELETE'
    )
