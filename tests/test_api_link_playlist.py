"""Saving a resolved playlist reuses local files and validates source art."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from downtify import api
from downtify.library_catalog import LibraryContext
from downtify.manual_playlists import create_manual_playlist
from downtify.playlist_mosaic import has_explicit_cover


def _request(payload):
    async def receive():
        return {'type': 'http.request', 'body': json.dumps(payload).encode()}

    return Request({'type': 'http', 'headers': []}, receive)


@pytest.fixture
def playlist(tmp_path, monkeypatch):
    ctx = LibraryContext(download_dir=tmp_path)
    create_manual_playlist(ctx, 'Mix')
    monkeypatch.setattr(api, 'library_context', lambda: ctx)
    monkeypatch.setattr(
        api,
        'require_playlist_visible',
        lambda *a, **kw: {'manual': True, 'mine': True, 'can_edit_tracks': True},
    )
    return tmp_path / 'Playlists' / 'Mix.m3u'


def test_save_source_cover_after_native_edit(playlist, monkeypatch):
    calls = []

    def cover(source, pid, path, settings):
        calls.append((source, pid, path))
        path.with_suffix('.jpg').write_bytes(b'official-image')
        return path.with_suffix('.jpg')

    monkeypatch.setattr(api, '_download_playlist_cover_for_batch', cover)
    result = asyncio.run(
        api.edit_library_playlist_tracks_endpoint(
            _request({
                'name': 'Mix',
                'source_playlist_url': 'https://deezer.com/playlist/333',
            })
        )
    )
    assert result['files'] == []
    assert calls == [('deezer', '333', playlist)]
    assert has_explicit_cover(playlist)


@pytest.mark.parametrize(
    'source', ['http://127.0.0.1/private', 'https://deezer.com/track/333']
)
def test_invalid_source_rejected_before_edit(playlist, monkeypatch, source):
    before = playlist.read_bytes()
    monkeypatch.setattr(
        api, 'edit_manual_playlist', lambda *a, **kw: pytest.fail('edited')
    )
    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            api.edit_library_playlist_tracks_endpoint(
                _request({
                    'name': 'Mix',
                    'source_playlist_url': source,
                })
            )
        )
    assert caught.value.status_code == 400
    assert playlist.read_bytes() == before


def test_source_cover_failure_keeps_playlist_edit_successful(
    playlist, monkeypatch
):
    monkeypatch.setattr(
        api, '_download_playlist_cover_for_batch', lambda *a: None
    )
    result = asyncio.run(
        api.edit_library_playlist_tracks_endpoint(
            _request({
                'name': 'Mix',
                'source_playlist_url': 'https://deezer.com/playlist/333',
            })
        )
    )
    assert result['files'] == []
    assert not has_explicit_cover(playlist)


def test_no_source_does_not_request_remote_art(playlist, monkeypatch):
    monkeypatch.setattr(
        api,
        '_download_playlist_cover_for_batch',
        lambda *a: pytest.fail('network'),
    )
    assert (
        asyncio.run(
            api.edit_library_playlist_tracks_endpoint(
                _request({'name': 'Mix'})
            )
        )['files']
        == []
    )
