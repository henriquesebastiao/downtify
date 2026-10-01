"""Tests for downloading a pasted Deezer link: the single-track
``_song_for_download`` branch, and the playlist-batch helpers that name,
number and cover a Deezer playlist download the same way a Spotify/
YouTube Music one is (``_playlist_target_for_batch``,
``_fetch_playlist_for_batch``, ``_download_playlist_cover_for_batch``)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from downtify import api

_DEEZER_TRACK = 'https://www.deezer.com/track/111'
_DEEZER_ALBUM = 'https://www.deezer.com/album/222'
_DEEZER_PLAYLIST = 'https://www.deezer.com/playlist/333'
_SONG = {'song_id': 'deezer-111', 'name': 'Track', 'source': 'deezer'}


# ── _song_for_download ───────────────────────────────────────────────────


def test_song_for_download_deezer_track(monkeypatch):
    monkeypatch.setattr(api.deezer, 'track_from_id', lambda did: _SONG)
    assert api._song_for_download(_DEEZER_TRACK) == _SONG


def test_song_for_download_deezer_album_is_rejected(monkeypatch):
    def unexpected(did):
        raise AssertionError('should not resolve a whole album here')

    monkeypatch.setattr(api.deezer, 'album_from_id', unexpected)
    with pytest.raises(HTTPException) as exc:
        api._song_for_download(_DEEZER_ALBUM)
    assert exc.value.status_code == 400


# ── _playlist_target_for_batch ───────────────────────────────────────────


def test_playlist_target_prefers_spotify_youtube(monkeypatch):
    monkeypatch.setattr(
        api, 'parse_playlist_url', lambda url: ('spotify', 'abc')
    )
    assert api._playlist_target_for_batch(_DEEZER_PLAYLIST) == (
        'spotify',
        'abc',
    )


def test_playlist_target_falls_back_to_deezer(monkeypatch):
    monkeypatch.setattr(api, 'parse_playlist_url', lambda url: None)
    assert api._playlist_target_for_batch(_DEEZER_PLAYLIST) == (
        'deezer',
        '333',
    )


def test_playlist_target_ignores_a_deezer_track_link(monkeypatch):
    monkeypatch.setattr(api, 'parse_playlist_url', lambda url: None)
    assert api._playlist_target_for_batch(_DEEZER_TRACK) is None


def test_playlist_target_none_for_unrecognized_url(monkeypatch):
    monkeypatch.setattr(api, 'parse_playlist_url', lambda url: None)
    assert api._playlist_target_for_batch('https://example.com/x') is None


# ── _fetch_playlist_for_batch ─────────────────────────────────────────────


def test_fetch_playlist_for_batch_uses_deezer(monkeypatch):
    monkeypatch.setattr(
        api.deezer,
        'playlist_info_and_tracks',
        lambda pid: ('My Playlist', [_SONG]),
    )
    assert api._fetch_playlist_for_batch('deezer', '333') == (
        'My Playlist',
        [_SONG],
    )


def test_fetch_playlist_for_batch_delegates_other_sources(monkeypatch):
    monkeypatch.setattr(
        api, 'fetch_playlist', lambda source, pid: (source, pid)
    )
    assert api._fetch_playlist_for_batch('spotify', 'abc') == (
        'spotify',
        'abc',
    )


# ── _download_playlist_cover_for_batch ────────────────────────────────────


def test_download_playlist_cover_for_batch_saves_deezer_cover(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        api.deezer,
        'playlist_cover_url_from_id',
        lambda pid: 'https://example.test/cover.jpg',
    )
    saved = {}
    monkeypatch.setattr(
        api,
        'save_playlist_cover',
        lambda url, path: saved.update(url=url, path=path),
    )
    m3u_path = tmp_path / 'playlist.m3u'
    api._download_playlist_cover_for_batch(
        'deezer', '333', m3u_path, {'download_cover_art_playlists': True}
    )
    assert saved == {'url': 'https://example.test/cover.jpg', 'path': m3u_path}


def test_download_playlist_cover_for_batch_respects_the_setting(
    monkeypatch, tmp_path
):
    def unexpected(pid):
        raise AssertionError(
            'should not fetch a cover when the setting is off'
        )

    monkeypatch.setattr(api.deezer, 'playlist_cover_url_from_id', unexpected)
    api._download_playlist_cover_for_batch(
        'deezer',
        '333',
        tmp_path / 'playlist.m3u',
        {'download_cover_art_playlists': False},
    )


def test_download_playlist_cover_for_batch_delegates_other_sources(
    monkeypatch, tmp_path
):
    captured = {}
    monkeypatch.setattr(
        api,
        'download_playlist_cover',
        lambda source, pid, path, settings: captured.update(
            source=source, pid=pid
        ),
    )
    api._download_playlist_cover_for_batch(
        'spotify', 'abc', tmp_path / 'playlist.m3u', {}
    )
    assert captured == {'source': 'spotify', 'pid': 'abc'}
