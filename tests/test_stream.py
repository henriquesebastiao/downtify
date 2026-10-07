"""Tests for instant full-track streaming (downtify.stream) and
``GET /api/stream``. yt-dlp never runs: its client is faked."""

from __future__ import annotations

import asyncio
import os
import time
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


def _cache(tmp_path, **kwargs):
    kwargs.setdefault('max_bytes', 10 * 1024**2)
    return stream.StreamCache(tmp_path / 'stream_cache', **kwargs)


def test_cache_serves_a_finished_file_without_fetching(tmp_path, monkeypatch):
    cache = _cache(tmp_path)
    cache._dir.mkdir(parents=True)
    (cache._dir / 'dQw4w9WgXcQ.m4a').write_bytes(b'audio')

    def boom(*_args, **_kwargs):
        raise AssertionError('must not fetch')

    monkeypatch.setattr(cache, '_fetch', boom)
    found = asyncio.run(cache.get('dQw4w9WgXcQ'))
    assert found.name == 'dQw4w9WgXcQ.m4a'


def test_cache_downloads_once_for_concurrent_requests(tmp_path):
    cache = _cache(tmp_path)
    calls = []

    def fake_fetch(video_id, cookies_file=''):
        calls.append(video_id)
        (cache._dir / f'{video_id}.m4a').write_bytes(b'audio')

    cache._fetch = fake_fetch

    async def scenario():
        return await asyncio.gather(
            cache.get('dQw4w9WgXcQ'), cache.get('dQw4w9WgXcQ')
        )

    first, second = asyncio.run(scenario())
    assert calls == ['dQw4w9WgXcQ']
    assert first == second


def test_cache_reports_an_empty_download(tmp_path):
    cache = _cache(tmp_path)
    cache._fetch = lambda *a, **k: None
    with pytest.raises(ValueError, match='nothing to stream'):
        asyncio.run(cache.get('dQw4w9WgXcQ'))


def test_cache_prunes_least_recently_used(tmp_path):
    cache = _cache(tmp_path, max_bytes=10)
    cache._dir.mkdir(parents=True)
    old = cache._dir / 'old12345678.m4a'
    new = cache._dir / 'new12345678.m4a'
    old.write_bytes(b'123456')
    new.write_bytes(b'123456')
    ancient = time.time() - 100
    os.utime(old, (ancient, ancient))
    assert cache.prune() == 1
    assert not old.exists()
    assert new.exists()


def test_media_type_for_known_extensions(tmp_path):
    assert stream.media_type_for(tmp_path / 'x.m4a') == 'audio/mp4'
    assert stream.media_type_for(tmp_path / 'x.mp4') == 'audio/mp4'
    assert stream.media_type_for(tmp_path / 'x.webm') == 'audio/webm'
    assert (
        stream.media_type_for(tmp_path / 'x.unknown')
        == 'application/octet-stream'
    )


def test_stream_file_endpoint_serves_the_cached_file(tmp_path, monkeypatch):
    cached = tmp_path / 'dQw4w9WgXcQ.m4a'
    cached.write_bytes(b'audio')

    async def fake_get(video_id, cookies_file=''):
        assert video_id == 'dQw4w9WgXcQ'
        assert cookies_file == '/c.txt'
        return cached

    fake_cache = MagicMock()
    fake_cache.get = fake_get
    monkeypatch.setattr(api.state, 'stream_cache', fake_cache)
    monkeypatch.setattr(stream, 'resolve_cookies_file', lambda store: '/c.txt')
    response = asyncio.run(api.stream_file_endpoint(video_id='dQw4w9WgXcQ'))
    assert response.status_code == 200
    assert response.media_type == 'audio/mp4'


def test_stream_file_endpoint_rejects_a_bad_id():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.stream_file_endpoint(video_id='nope'))
    assert exc.value.status_code == 400


def test_stream_file_endpoint_needs_a_cache(monkeypatch):
    monkeypatch.setattr(api.state, 'stream_cache', None)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.stream_file_endpoint(video_id='dQw4w9WgXcQ'))
    assert exc.value.status_code == 503


def test_stream_file_endpoint_maps_download_failures(monkeypatch):
    async def down(*_args, **_kwargs):
        raise ValueError('YouTube did not answer: down')

    fake_cache = MagicMock()
    fake_cache.get = down
    monkeypatch.setattr(api.state, 'stream_cache', fake_cache)
    monkeypatch.setattr(stream, 'resolve_cookies_file', lambda store: '')
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.stream_file_endpoint(video_id='dQw4w9WgXcQ'))
    assert exc.value.status_code == 503


class _FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def test_stream_prefetch_queues_a_background_download(monkeypatch):
    seen = {}
    started = {}

    async def fake_get(video_id, cookies_file=''):
        seen['video_id'] = video_id
        seen['cookies_file'] = cookies_file

    fake_cache = MagicMock()
    fake_cache.get = fake_get

    def fake_spawn(coro, name=None):
        started['name'] = name
        return asyncio.ensure_future(coro)

    async def scenario():
        result = await api.stream_prefetch_endpoint(
            _FakeRequest({'video_id': 'dQw4w9WgXcQ'})
        )
        await asyncio.sleep(0.1)
        return result

    monkeypatch.setattr(api.state, 'stream_cache', fake_cache)
    monkeypatch.setattr(api, 'spawn_task', fake_spawn)
    monkeypatch.setattr(stream, 'resolve_cookies_file', lambda store: '/c.txt')
    assert asyncio.run(scenario()) == {'queued': True}
    assert started['name'] == 'stream-prefetch-dQw4w9WgXcQ'
    assert seen == {'video_id': 'dQw4w9WgXcQ', 'cookies_file': '/c.txt'}


def test_stream_prefetch_rejects_a_bad_id():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            api.stream_prefetch_endpoint(_FakeRequest({'video_id': 'nope'}))
        )
    assert exc.value.status_code == 400


def test_stream_prefetch_needs_a_cache(monkeypatch):
    monkeypatch.setattr(api.state, 'stream_cache', None)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            api.stream_prefetch_endpoint(
                _FakeRequest({'video_id': 'dQw4w9WgXcQ'})
            )
        )
    assert exc.value.status_code == 503


def test_stream_cache_from_env_reads_limits(tmp_path, monkeypatch):
    monkeypatch.setenv('DOWNTIFY_STREAM_CACHE_MB', '10')
    monkeypatch.setenv('DOWNTIFY_STREAM_CONCURRENCY', '4')
    cache = stream.stream_cache_from_env(tmp_path)
    assert cache._dir == tmp_path / 'stream_cache'
    assert cache._max_bytes == 10 * 1024**2
