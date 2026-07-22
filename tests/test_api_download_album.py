"""Tests for the whole-album download endpoint.

Regression coverage for the bug where albums were downloaded one track at
a time via ``/api/download/url``, which re-resolves each video's catalog
metadata independently and can drift to a different release than the one
the user actually picked (e.g. a "best of" compilation's tracks resolving
back to their original studio albums). ``/api/download/album`` must instead
download every track from the same, already-resolved tracklist.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from downtify import api
from downtify.api import _songs_for_album_download, download_album_endpoint

ALBUM_URL = 'https://music.youtube.com/browse/MPREb_test123'


# ── _songs_for_album_download ─────────────────────────────────────────────────


def test_songs_for_album_download_rejects_non_album_url(monkeypatch):
    monkeypatch.setattr(
        api.providers, 'parse_youtube_url', lambda url: ('track', 'abc')
    )
    with pytest.raises(HTTPException) as exc_info:
        _songs_for_album_download('https://music.youtube.com/watch?v=abc')
    assert exc_info.value.status_code == 400


def test_songs_for_album_download_rejects_unrecognized_url(monkeypatch):
    monkeypatch.setattr(api.providers, 'parse_youtube_url', lambda url: None)
    with pytest.raises(HTTPException) as exc_info:
        _songs_for_album_download('https://example.com/not-youtube')
    assert exc_info.value.status_code == 400


def test_songs_for_album_download_rejects_empty_tracklist(monkeypatch):
    monkeypatch.setattr(
        api.providers,
        'parse_youtube_url',
        lambda url: ('album', 'MPREb_x'),
    )
    monkeypatch.setattr(
        api.providers, 'album_tracks_from_browse_id', lambda bid: []
    )
    with pytest.raises(HTTPException) as exc_info:
        _songs_for_album_download(ALBUM_URL)
    assert exc_info.value.status_code == 404


def test_songs_for_album_download_returns_resolved_tracks(monkeypatch):
    songs = [{'song_id': 'a'}, {'song_id': 'b'}]
    monkeypatch.setattr(
        api.providers,
        'parse_youtube_url',
        lambda url: ('album', 'MPREb_x'),
    )
    monkeypatch.setattr(
        api.providers, 'album_tracks_from_browse_id', lambda bid: songs
    )
    assert _songs_for_album_download(ALBUM_URL) == songs


# ── download_album_endpoint ────────────────────────────────────────────────────


def test_download_album_endpoint_requires_downloader(monkeypatch):
    monkeypatch.setattr(api.state, 'downloader', None)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(download_album_endpoint(url=ALBUM_URL))
    assert exc_info.value.status_code == 500


def test_download_album_endpoint_keeps_shared_album_metadata(monkeypatch):
    songs = [
        {'song_id': 'good-1', 'album_name': 'Monetine', 'name': 'Song 1'},
        {'song_id': 'good-2', 'album_name': 'Monetine', 'name': 'Song 2'},
        {'song_id': 'bad-1', 'album_name': 'Monetine', 'name': 'Song 3'},
    ]
    monkeypatch.setattr(api, '_songs_for_album_download', lambda url: songs)
    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(api.state, 'download_jobs', {})

    seen_songs = []

    async def fake_run_download(song, job_id, subdir=None):
        seen_songs.append(song)
        if song['song_id'] == 'bad-1':
            raise RuntimeError('boom')
        return f'{song["song_id"]}.mp3'

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    result = asyncio.run(download_album_endpoint(url=ALBUM_URL))

    assert result == {'good-1': 'good-1.mp3', 'good-2': 'good-2.mp3'}
    # every track was downloaded using the exact, shared album metadata -
    # never re-resolved one video at a time (the bug this endpoint fixes)
    assert all(s['album_name'] == 'Monetine' for s in seen_songs)


def test_download_album_endpoint_skips_songs_without_id(monkeypatch):
    monkeypatch.setattr(
        api, '_songs_for_album_download', lambda url: [{'name': 'no id'}]
    )
    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(api.state, 'download_jobs', {})

    async def fake_run_download(song, job_id, subdir=None):
        raise AssertionError(
            'should not attempt to download a song with no id'
        )

    monkeypatch.setattr(api, '_run_download', fake_run_download)

    result = asyncio.run(download_album_endpoint(url=ALBUM_URL))
    assert result == {}
