"""Tests for instant full-track streaming (downtify.stream),
``GET /api/stream`` and ``GET /api/stream/chunk``. yt-dlp and ffmpeg
never run: both are faked."""

from __future__ import annotations

import asyncio
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from downtify import api, stream


@pytest.fixture(autouse=True)
def _fresh_url_cache():
    stream._url_cache.clear()
    yield
    stream._url_cache.clear()


def _ydl(info):
    client = MagicMock()
    client.__enter__.return_value.extract_info.return_value = info
    client.__exit__.return_value = False
    return client


def test_clean_video_id_accepts_an_11_char_id():
    assert stream.clean_video_id('dQw4w9WgXcQ') == 'dQw4w9WgXcQ'


def test_clean_video_id_rejects_anything_else():
    for bad in ('', '  ', 'short', 'toolong' * 10, 'not a url at all'):
        with pytest.raises(ValueError, match='video id'):
            stream.clean_video_id(bad)


def test_stream_url_returns_the_direct_audio_url():
    info = {
        'url': 'https://r1---sn.googlevideo.com/x',
        'ext': 'm4a',
        'duration': 200,
    }
    with patch(
        'downtify.stream.yt_dlp.YoutubeDL', return_value=_ydl(info)
    ) as ydl:
        result = stream.stream_url_for_video('dQw4w9WgXcQ')
    assert result == {'url': info['url'], 'ext': 'm4a', 'duration': 200.0}
    opts = ydl.call_args[0][0]
    assert opts['format'].startswith('bestaudio[ext=m4a]')


def test_stream_url_reuses_a_fresh_cache_entry():
    info = {'url': 'https://r1---sn.googlevideo.com/x', 'ext': 'm4a'}
    with patch(
        'downtify.stream.yt_dlp.YoutubeDL', return_value=_ydl(info)
    ) as ydl:
        stream.stream_url_for_video('dQw4w9WgXcQ')
        stream.stream_url_for_video('dQw4w9WgXcQ')
    assert ydl.call_count == 1


def test_audio_chunk_cuts_mp3_with_ffmpeg(monkeypatch):
    monkeypatch.setattr(
        stream, '_resolve_direct', lambda *a: ('https://x', 200.0, 'm4a')
    )
    monkeypatch.setattr(stream.shutil, 'which', lambda name: '/usr/bin/ffmpeg')
    calls = {}

    def fake_run(cmd, **kwargs):
        calls['cmd'] = cmd
        result = MagicMock()
        result.returncode = 0
        result.stdout = b'ID3' + bytes(400 * 1024)
        result.stderr = b''
        return result

    monkeypatch.setattr(stream.subprocess, 'run', fake_run)
    chunk = stream.audio_chunk('dQw4w9WgXcQ', 40)
    assert chunk['data'][:3] == b'ID3'
    assert chunk['start'] == 40
    assert chunk['duration'] == 200.0
    cmd = calls['cmd']
    assert cmd[cmd.index('-ss') + 1] == '40'
    assert cmd[cmd.index('-t') + 1] == str(stream.CHUNK_SECONDS)
    assert cmd[cmd.index('-i') + 1] == 'https://x'


def test_audio_chunk_rejects_a_negative_start():
    with pytest.raises(ValueError, match='negative'):
        stream.audio_chunk('dQw4w9WgXcQ', -5)


def test_audio_chunk_rejects_a_start_past_the_end(monkeypatch):
    monkeypatch.setattr(
        stream, '_resolve_direct', lambda *a: ('https://x', 200.0, 'm4a')
    )
    monkeypatch.setattr(stream.shutil, 'which', lambda name: '/usr/bin/ffmpeg')
    with pytest.raises(ValueError, match='past the end'):
        stream.audio_chunk('dQw4w9WgXcQ', 200.0)


def test_audio_chunk_needs_ffmpeg(monkeypatch):
    monkeypatch.setattr(stream.shutil, 'which', lambda name: None)
    with pytest.raises(ValueError, match='ffmpeg'):
        stream.audio_chunk('dQw4w9WgXcQ', 0)


def test_audio_chunk_reports_transcode_failures(monkeypatch):
    monkeypatch.setattr(
        stream, '_resolve_direct', lambda *a: ('https://x', 200.0, 'm4a')
    )
    monkeypatch.setattr(stream.shutil, 'which', lambda name: '/usr/bin/ffmpeg')

    def failed(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 1
        result.stdout = b''
        result.stderr = b'boom'
        return result

    monkeypatch.setattr(stream.subprocess, 'run', failed)
    with pytest.raises(ValueError, match='transcode failed'):
        stream.audio_chunk('dQw4w9WgXcQ', 0)


def test_audio_chunk_reports_timeouts(monkeypatch):
    monkeypatch.setattr(
        stream, '_resolve_direct', lambda *a: ('https://x', 200.0, 'm4a')
    )
    monkeypatch.setattr(stream.shutil, 'which', lambda name: '/usr/bin/ffmpeg')

    def slow(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 60)

    monkeypatch.setattr(stream.subprocess, 'run', slow)
    with pytest.raises(ValueError, match='timed out'):
        stream.audio_chunk('dQw4w9WgXcQ', 0)


def test_stream_chunk_endpoint(monkeypatch):
    monkeypatch.setattr(stream, 'resolve_cookies_file', lambda store: '')
    monkeypatch.setattr(
        stream,
        'audio_chunk',
        lambda vid, start, cookies_file='': {
            'data': b'ID3' + bytes(10),
            'start': 20.0,
            'duration': 200.0,
        },
    )
    response = asyncio.run(
        api.stream_chunk_endpoint(video_id='dQw4w9WgXcQ', t=20)
    )
    assert response.media_type == 'audio/mpeg'
    assert response.body[:3] == b'ID3'
    assert response.headers['X-Chunk-Start'] == '20.0'
    assert response.headers['X-Audio-Duration'] == '200.0'


def test_stream_chunk_endpoint_rejects_a_bad_id():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.stream_chunk_endpoint(video_id='nope', t=0))
    assert exc.value.status_code == 400


def test_stream_chunk_endpoint_maps_upstream_failures(monkeypatch):
    monkeypatch.setattr(stream, 'resolve_cookies_file', lambda store: '')

    def down(*_args, **_kwargs):
        raise ValueError('Chunk transcode failed')

    monkeypatch.setattr(stream, 'audio_chunk', down)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.stream_chunk_endpoint(video_id='dQw4w9WgXcQ', t=0))
    assert exc.value.status_code == 503


def test_stream_url_passes_cookies_through():
    info = {'url': 'https://r1---sn.googlevideo.com/x', 'ext': 'webm'}
    with patch(
        'downtify.stream.yt_dlp.YoutubeDL', return_value=_ydl(info)
    ) as ydl:
        stream.stream_url_for_video('dQw4w9WgXcQ', cookies_file='/c.txt')
    assert ydl.call_args[0][0]['cookiefile'] == '/c.txt'


def test_stream_url_reports_unplayable_replies():
    with patch('downtify.stream.yt_dlp.YoutubeDL', return_value=_ydl({})):
        with pytest.raises(ValueError, match='unreadable'):
            stream.stream_url_for_video('dQw4w9WgXcQ')


def test_stream_url_reports_network_failures():
    client = MagicMock()
    client.__enter__.side_effect = Exception('down')
    with patch('downtify.stream.yt_dlp.YoutubeDL', return_value=client):
        with pytest.raises(ValueError, match='did not answer'):
            stream.stream_url_for_video('dQw4w9WgXcQ')


def test_stream_url_names_age_gated_tracks():
    client = MagicMock()
    client.__enter__.side_effect = Exception(
        'Sign in to confirm your age. This video may be inappropriate.'
    )
    with patch('downtify.stream.yt_dlp.YoutubeDL', return_value=client):
        with pytest.raises(ValueError, match='age-restricted'):
            stream.stream_url_for_video('dQw4w9WgXcQ')


def test_stream_endpoint(monkeypatch):
    monkeypatch.setattr(stream, 'resolve_cookies_file', lambda store: '/c.txt')
    monkeypatch.setattr(
        stream,
        'stream_url_for_video',
        lambda vid, cookies_file='': {
            'url': 'https://x',
            'ext': 'm4a',
            'duration': 200.0,
        },
    )
    assert asyncio.run(api.stream_endpoint(video_id='dQw4w9WgXcQ')) == {
        'url': 'https://x',
        'ext': 'm4a',
        'duration': 200.0,
    }


def test_stream_endpoint_rejects_a_bad_id():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.stream_endpoint(video_id='nope'))
    assert exc.value.status_code == 400


def test_stream_endpoint_maps_upstream_failures(monkeypatch):
    monkeypatch.setattr(stream, 'resolve_cookies_file', lambda store: '')

    def down(*_args, **_kwargs):
        raise ValueError('YouTube did not answer: down')

    monkeypatch.setattr(stream, 'stream_url_for_video', down)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.stream_endpoint(video_id='dQw4w9WgXcQ'))
    assert exc.value.status_code == 503
