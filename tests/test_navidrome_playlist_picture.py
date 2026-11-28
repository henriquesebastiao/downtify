"""Downtify's own Navidrome playlists get the playlist's picture.

Without one, Navidrome shows a mosaic of the songs' covers. A playlist
Navidrome imports from the M3U finds the picture beside it by itself.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from downtify import navidrome
from downtify.navidrome import (
    NavidromeClient,
    _give_playlist_picture,
    sync_playlist_to_navidrome,
)


@pytest.fixture(autouse=True)
def _no_pictures_given(monkeypatch):
    monkeypatch.setattr(navidrome, '_playlist_pictures', {})


class _Client:
    def __init__(self, ok=True):
        self.ok = ok
        self.uploads: list[tuple[str, bytes]] = []

    def _set_playlist_image(self, playlist_id, image):
        self.uploads.append((playlist_id, image))
        return self.ok


def test_a_picture_is_uploaded_once_until_it_changes(tmp_path):
    cover = tmp_path / 'P.jpg'
    cover.write_bytes(b'MOSAIC')
    client = _Client()

    _give_playlist_picture(client, 'pl-1', cover)
    _give_playlist_picture(client, 'pl-1', cover)
    cover.write_bytes(b'UPLOADED')
    _give_playlist_picture(client, 'pl-1', cover)

    assert client.uploads == [('pl-1', b'MOSAIC'), ('pl-1', b'UPLOADED')]


def test_a_failed_upload_is_tried_again_next_time(tmp_path):
    cover = tmp_path / 'P.jpg'
    cover.write_bytes(b'IMG')
    client = _Client(ok=False)

    _give_playlist_picture(client, 'pl-1', cover)
    _give_playlist_picture(client, 'pl-1', cover)

    assert len(client.uploads) == 2


def test_no_picture_means_no_upload(tmp_path):
    client = _Client()

    _give_playlist_picture(client, 'pl-1', None)
    _give_playlist_picture(client, 'pl-1', tmp_path / 'missing.jpg')

    assert client.uploads == []


def _client():
    return NavidromeClient({
        'url': 'http://nd.test',
        'username': 'downtify',
        'password': 'placeholder',
    })


@patch('downtify.navidrome.httpx.post')
def test_set_playlist_image_signs_in_and_posts_the_image(mock_post):
    login = MagicMock()
    login.json.return_value = {'token': 'jwt'}
    upload = MagicMock()
    mock_post.side_effect = [login, upload]

    assert _client()._set_playlist_image('pl-1', b'IMG') is True

    login_call, upload_call = mock_post.call_args_list
    assert login_call[0][0] == 'http://nd.test/auth/login'
    assert login_call[1]['json']['username'] == 'downtify'
    assert upload_call[0][0] == 'http://nd.test/api/playlist/pl-1/image'
    assert upload_call[1]['headers'] == {'x-nd-authorization': 'Bearer jwt'}
    assert upload_call[1]['files']['image'][1] == b'IMG'


@patch('downtify.navidrome.httpx.post')
def test_set_playlist_image_is_false_on_an_older_navidrome(mock_post):
    login = MagicMock()
    login.json.return_value = {'token': 'jwt'}
    upload = MagicMock()
    upload.raise_for_status.side_effect = httpx.HTTPStatusError(
        '404', request=MagicMock(), response=MagicMock()
    )
    mock_post.side_effect = [login, upload]

    assert _client()._set_playlist_image('pl-1', b'IMG') is False


def _sync(monkeypatch, tmp_path, **cfg):
    uploads: list[tuple[str, bytes]] = []
    monkeypatch.setattr(NavidromeClient, 'ping', lambda self: True)
    monkeypatch.setattr(
        navidrome, '_match_songs_in_library', lambda *a, **k: (['s1'], [])
    )
    monkeypatch.setattr(
        NavidromeClient, 'find_playlist_ids_by_name', lambda self, name: []
    )
    monkeypatch.setattr(
        NavidromeClient, 'create_playlist', lambda self, name, ids: 'pl-9'
    )
    monkeypatch.setattr(
        NavidromeClient, 'update_playlist_meta', lambda self, *a, **k: None
    )
    monkeypatch.setattr(
        NavidromeClient,
        '_set_playlist_image',
        lambda self, pid, image: uploads.append((pid, image)) or True,
    )
    monkeypatch.setattr(
        navidrome, 'remove_own_playlist_copies', lambda client, name: 0
    )
    cover = tmp_path / 'P.jpg'
    cover.write_bytes(b'IMG')
    settings = {
        'navidrome': {
            'enabled': True,
            'url': 'http://nd.test',
            'username': 'downtify',
            'password': 'placeholder',
            'scan_after_download': False,
            **cfg,
        }
    }
    sync_playlist_to_navidrome(
        'P',
        [{'name': 'Track', 'artists': ['Artist'], 'filename': 'A/T.mp3'}],
        settings,
        cover=cover,
    )
    return uploads


def test_sync_gives_downtifys_playlist_its_picture(monkeypatch, tmp_path):
    assert _sync(monkeypatch, tmp_path) == [('pl-9', b'IMG')]


def test_sync_leaves_an_imported_playlist_to_navidrome(monkeypatch, tmp_path):
    assert _sync(monkeypatch, tmp_path, m3u_import=True) == []
