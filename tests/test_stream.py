"""Tests for instant full-track streaming (downtify.stream) and
``GET /api/stream``. yt-dlp never runs: its client is faked."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from downtify import api, stream


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
    info = {'url': 'https://r1---sn.googlevideo.com/x', 'ext': 'm4a'}
    with patch(
        'downtify.stream.yt_dlp.YoutubeDL', return_value=_ydl(info)
    ) as ydl:
        result = stream.stream_url_for_video('dQw4w9WgXcQ')
    assert result == {'url': info['url'], 'ext': 'm4a'}
    opts = ydl.call_args[0][0]
    assert opts['format'].startswith('bestaudio[ext=m4a]')


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
        lambda vid, cookies_file='': {'url': 'https://x', 'ext': 'm4a'},
    )
    assert asyncio.run(api.stream_endpoint(video_id='dQw4w9WgXcQ')) == {
        'url': 'https://x'
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
