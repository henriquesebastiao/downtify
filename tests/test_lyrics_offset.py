"""Moving a song's time-synced lyrics earlier or later (issue #663)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from mutagen.flac import FLAC
from mutagen.id3 import ID3, SYLT, USLT
from starlette.testclient import TestClient

import main
from downtify import api
from downtify.lyrics import (
    read_track_lyrics,
    shift_lrc,
    shift_track_lyrics,
)

_LRC = (
    '[ti:Harbor Lights]\n'
    '[00:12.00]The harbor lights are blinking out\n'
    '[00:15.50]One by one'
)

needs_ffmpeg = pytest.mark.skipif(
    shutil.which('ffmpeg') is None, reason='no ffmpeg'
)


# ── shift_lrc ─────────────────────────────────────────────────────────


def test_moves_every_line_later() -> None:
    assert shift_lrc(_LRC, 1500) == (
        '[ti:Harbor Lights]\n'
        '[00:13.50]The harbor lights are blinking out\n'
        '[00:17.00]One by one'
    )


def test_moves_lines_sooner_and_stops_at_zero() -> None:
    assert shift_lrc('[00:00.40]Intro\n[01:00.00]Verse', -500) == (
        '[00:00.00]Intro\n[00:59.50]Verse'
    )


def test_crosses_minutes_and_keeps_millisecond_precision() -> None:
    assert shift_lrc('[00:59.950]Chorus', 100) == '[01:00.050]Chorus'


def test_shifts_every_tag_of_a_repeated_line_only() -> None:
    text = '[00:10.00][00:40.00]Chorus at [00:10.00] sharp'

    assert shift_lrc(text, 1000) == (
        '[00:11.00][00:41.00]Chorus at [00:10.00] sharp'
    )


def test_folds_the_offset_header_into_the_times() -> None:
    # [offset:+500] shows the lyrics 500 ms sooner; many players ignore it.
    text = '[offset:+500]\n[00:10.00]Line'

    assert shift_lrc(text, 0) == '[00:09.50]Line'
    assert shift_lrc(text, 200) == '[00:09.70]Line'


def test_short_timestamps_are_read() -> None:
    assert shift_lrc('[1:05]Line', 250) == '[01:05.25]Line'


# ── shift_track_lyrics ────────────────────────────────────────────────


def _mp3(path: Path, *frames: object) -> Path:
    tags = ID3()
    for frame in frames:
        tags.add(frame)
    tags.save(str(path), v2_version=4)
    return path


def test_rewrites_the_sidecar(tmp_path: Path) -> None:
    track = _mp3(tmp_path / 'Song.mp3')
    track.with_suffix('.lrc').write_text(_LRC, encoding='utf-8')

    assert shift_track_lyrics(track, -2000) == ['sidecar']
    assert read_track_lyrics(track)['synced'] == (
        '[ti:Harbor Lights]\n'
        '[00:10.00]The harbor lights are blinking out\n'
        '[00:13.50]One by one'
    )


def test_rewrites_synced_lyrics_in_the_tags(tmp_path: Path) -> None:
    track = _mp3(
        tmp_path / 'Song.mp3', USLT(encoding=3, lang='eng', desc='', text=_LRC)
    )
    track.with_suffix('.lrc').write_text(_LRC, encoding='utf-8')

    assert shift_track_lyrics(track, 1000) == ['sidecar', 'tags']
    embedded = str(ID3(str(track)).getall('USLT')[0].text)
    assert '[00:13.00]The harbor lights' in embedded
    assert '[00:16.50]One by one' in embedded


def test_plain_lyrics_in_the_tags_are_left_alone(tmp_path: Path) -> None:
    track = _mp3(
        tmp_path / 'Song.mp3',
        USLT(encoding=3, lang='eng', desc='', text='Just words'),
    )
    track.with_suffix('.lrc').write_text(_LRC, encoding='utf-8')

    assert shift_track_lyrics(track, 1000) == ['sidecar']
    assert str(ID3(str(track)).getall('USLT')[0].text) == 'Just words'


def test_moves_sylt_frames(tmp_path: Path) -> None:
    track = _mp3(
        tmp_path / 'Song.mp3',
        SYLT(
            encoding=3,
            lang='eng',
            format=2,
            type=1,
            text=[('First', 300), ('Second', 5000)],
        ),
    )

    assert shift_track_lyrics(track, -500) == ['tags']
    assert ID3(str(track)).getall('SYLT')[0].text == [
        ('First', 0),
        ('Second', 4500),
    ]


def test_nothing_synced_changes_nothing(tmp_path: Path) -> None:
    track = _mp3(
        tmp_path / 'Song.mp3',
        USLT(encoding=3, lang='eng', desc='', text='Just words'),
    )

    assert not shift_track_lyrics(track, 1000)


@needs_ffmpeg
def test_rewrites_vorbis_lyrics(tmp_path: Path) -> None:
    track = tmp_path / 'Song.flac'
    subprocess.run(
        [
            'ffmpeg',
            '-nostdin',
            '-loglevel',
            'error',
            '-f',
            'lavfi',
            '-i',
            'anullsrc=r=44100:cl=mono',
            '-t',
            '0.2',
            str(track),
        ],
        check=True,
    )
    audio = FLAC(str(track))
    audio['lyrics'] = _LRC
    audio.save()

    assert shift_track_lyrics(track, 500) == ['tags']
    assert '[00:12.50]The harbor lights' in FLAC(str(track))['lyrics'][0]


# ── POST /api/library/lyrics/offset ───────────────────────────────────


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html></html>', encoding='utf-8')
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
        'library_sync',
        'metadata_cache',
        'track_index',
    ):
        monkeypatch.setattr(api.state, name, getattr(api.state, name, None))
    app = TestClient(main.build_app(), base_url='http://testserver')
    app.downloads = downloads
    return app


def _login(client: TestClient) -> None:
    client.post(
        '/api/auth/login', json={'username': 'admin', 'password': 'downtify'}
    )


def test_route_shifts_and_logs(client: TestClient) -> None:
    _login(client)
    track = _mp3(client.downloads / 'Song.mp3')
    track.with_suffix('.lrc').write_text(_LRC, encoding='utf-8')

    res = client.post(
        '/api/library/lyrics/offset',
        json={'file': 'Song.mp3', 'offset_ms': 300},
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body['changed'] == ['sidecar']
    assert body['offset_ms'] == 300
    assert '[00:12.30]The harbor lights' in body['synced']
    assert (
        client.get('/lyrics', params={'file': 'Song.mp3'}).json()['synced']
        == body['synced']
    )
    kinds = [e['kind'] for e in client.get('/api/activity').json()['entries']]
    assert 'lyrics_offset' in kinds


@pytest.mark.parametrize('offset', [0, 60_001, -60_001, 1.5, True, '500'])
def test_route_rejects_bad_offsets(client: TestClient, offset: object) -> None:
    _login(client)
    _mp3(client.downloads / 'Song.mp3')

    res = client.post(
        '/api/library/lyrics/offset',
        json={'file': 'Song.mp3', 'offset_ms': offset},
    )

    assert res.status_code == 400


def test_route_404s_without_synced_lyrics(client: TestClient) -> None:
    _login(client)
    _mp3(client.downloads / 'Song.mp3')

    for file in ('Song.mp3', 'Missing.mp3', '../outside.mp3'):
        res = client.post(
            '/api/library/lyrics/offset',
            json={'file': file, 'offset_ms': 500},
        )
        assert res.status_code == 404, file


def test_route_needs_sign_in(client: TestClient) -> None:
    track = _mp3(client.downloads / 'Song.mp3')
    track.with_suffix('.lrc').write_text(_LRC, encoding='utf-8')

    res = client.post(
        '/api/library/lyrics/offset',
        json={'file': 'Song.mp3', 'offset_ms': 500},
    )

    assert res.status_code == 401
    assert track.with_suffix('.lrc').read_text(encoding='utf-8') == _LRC
