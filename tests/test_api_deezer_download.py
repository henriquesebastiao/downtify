"""Tests for downloading a pasted Deezer link: the single-track
``_song_for_download`` branch, and a Deezer playlist download, named,
numbered and covered the same way a Spotify/YouTube Music one is (through
the monitor's ``parse_playlist_url`` / ``fetch_playlist`` and
``_download_playlist_cover_for_batch``)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from downtify import api, monitor

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


# ── a Deezer playlist batch: parsed, fetched and covered as a watch is ───


def test_playlist_url_parser_knows_deezer():
    assert api.parse_playlist_url(_DEEZER_PLAYLIST) == ('deezer', '333')
    assert api.parse_playlist_url(_DEEZER_TRACK) is None
    assert api.parse_playlist_url(_DEEZER_ALBUM) is None
    assert api.parse_playlist_url('https://example.com/x') is None


def test_fetch_playlist_uses_deezer(monkeypatch):
    monkeypatch.setattr(
        monitor.deezer,
        'playlist_info_and_tracks',
        lambda pid: ('My Playlist', [_SONG]),
    )
    assert api.fetch_playlist('deezer', '333') == ('My Playlist', [_SONG])


def test_download_playlist_cover_for_batch_saves_deezer_cover(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        monitor.deezer,
        'playlist_cover_url_from_id',
        lambda pid: 'https://example.test/cover.jpg',
    )
    saved = {}
    monkeypatch.setattr(
        monitor,
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

    monkeypatch.setattr(
        monitor.deezer, 'playlist_cover_url_from_id', unexpected
    )
    api._download_playlist_cover_for_batch(
        'deezer',
        '333',
        tmp_path / 'playlist.m3u',
        {'download_cover_art_playlists': False},
    )


def test_download_playlist_cover_for_batch_swallows_a_save_failure(
    monkeypatch, tmp_path
):
    def broken(source, pid, path, settings):
        raise OSError('disk full')

    monkeypatch.setattr(api, 'download_playlist_cover', broken)
    assert (
        api._download_playlist_cover_for_batch(
            'spotify', 'abc', tmp_path / 'playlist.m3u', {}
        )
        is None
    )
