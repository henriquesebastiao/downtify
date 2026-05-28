from unittest.mock import MagicMock, patch

from downtify.navidrome import (
    NavidromeClient,
    _effective_navidrome_settings,
    sync_playlist_to_navidrome,
)


def test_effective_navidrome_settings_defaults():
    out = _effective_navidrome_settings({})
    assert out['enabled'] is False
    assert out['scan_wait_seconds'] == 120


def test_search_song_id_matches_title_and_artist():
    client = NavidromeClient(
        {
            'url': 'https://navidrome.test',
            'username': 'u',
            'password': 'p',
        }
    )

    def fake_request(endpoint, extra=None, **kwargs):
        assert endpoint == 'search3'
        return {
            'searchResult3': {
                'song': [
                    {
                        'id': 'song-1',
                        'title': 'DRAMA KING',
                        'artist': 'Melxdie',
                        'duration': 152,
                        'path': 'Melxdie/DRAMA KING.mp3',
                    }
                ]
            }
        }

    client._request = fake_request  # type: ignore[method-assign]
    sid = client.search_song_id(
        {'name': 'DRAMA KING', 'artists': ['Melxdie'], 'duration': 152}
    )
    assert sid == 'song-1'


@patch('downtify.navidrome.requests.get')
def test_sync_playlist_creates_playlist(mock_get):
    ping_resp = MagicMock()
    ping_resp.json.return_value = {'subsonic-response': {'status': 'ok'}}
    ping_resp.raise_for_status = MagicMock()

    scan_resp = MagicMock()
    scan_resp.json.return_value = {
        'subsonic-response': {'status': 'ok', 'scanStatus': {'scanning': False}}
    }
    scan_resp.raise_for_status = MagicMock()

    search_resp = MagicMock()
    search_resp.json.return_value = {
        'subsonic-response': {
            'status': 'ok',
            'searchResult3': {
                'song': [
                    {
                        'id': 'abc',
                        'title': 'Track',
                        'artist': 'Artist',
                        'duration': 200,
                        'path': 'Artist/Track.mp3',
                    }
                ]
            },
        }
    }
    search_resp.raise_for_status = MagicMock()

    playlists_resp = MagicMock()
    playlists_resp.json.return_value = {
        'subsonic-response': {'status': 'ok', 'playlists': {}}
    }
    playlists_resp.raise_for_status = MagicMock()

    create_resp = MagicMock()
    create_resp.json.return_value = {
        'subsonic-response': {
            'status': 'ok',
            'playlist': {'id': 'pl-1'},
        }
    }
    create_resp.raise_for_status = MagicMock()

    update_resp = MagicMock()
    update_resp.json.return_value = {'subsonic-response': {'status': 'ok'}}
    update_resp.raise_for_status = MagicMock()

    start_scan_resp = MagicMock()
    start_scan_resp.json.return_value = {'subsonic-response': {'status': 'ok'}}
    start_scan_resp.raise_for_status = MagicMock()

    mock_get.side_effect = [
        ping_resp,
        start_scan_resp,
        scan_resp,
        search_resp,
        playlists_resp,
        create_resp,
        update_resp,
    ]

    settings = {
        'navidrome': {
            'enabled': True,
            'url': 'https://navidrome.test',
            'username': 'user',
            'password': 'pass',
            'scan_after_download': True,
            'scan_wait_seconds': 10,
            'scan_poll_seconds': 1,
        }
    }
    result = sync_playlist_to_navidrome(
        'My Spotify List',
        [
            {
                'name': 'Track',
                'artists': ['Artist'],
                'duration': 200,
                'filename': 'Artist/Track.mp3',
            }
        ],
        settings,
    )
    assert result is not None
    assert result.playlist_id == 'pl-1'
    assert result.matched == 1


@patch('downtify.navidrome.requests.get')
def test_sync_playlist_updates_existing_by_id(mock_get):
    """Existing playlists are replaced in place (createPlaylist + playlistId)."""

    ping_resp = MagicMock()
    ping_resp.json.return_value = {'subsonic-response': {'status': 'ok'}}
    ping_resp.raise_for_status = MagicMock()

    search_resp = MagicMock()
    search_resp.json.return_value = {
        'subsonic-response': {
            'status': 'ok',
            'searchResult3': {
                'song': [
                    {
                        'id': 'abc',
                        'title': 'Track',
                        'artist': 'Artist',
                        'duration': 200,
                        'path': 'Artist/Track.mp3',
                    }
                ]
            },
        }
    }
    search_resp.raise_for_status = MagicMock()

    playlists_resp = MagicMock()
    playlists_resp.json.return_value = {
        'subsonic-response': {
            'status': 'ok',
            'playlists': {'playlist': {'id': 'pl-existing', 'name': 'My List'}},
        }
    }
    playlists_resp.raise_for_status = MagicMock()

    replace_resp = MagicMock()
    replace_resp.json.return_value = {
        'subsonic-response': {
            'status': 'ok',
            'playlist': {'id': 'pl-existing'},
        }
    }
    replace_resp.raise_for_status = MagicMock()

    update_resp = MagicMock()
    update_resp.json.return_value = {'subsonic-response': {'status': 'ok'}}
    update_resp.raise_for_status = MagicMock()

    mock_get.side_effect = [
        ping_resp,
        search_resp,
        playlists_resp,
        replace_resp,
        update_resp,
    ]

    settings = {
        'navidrome': {
            'enabled': True,
            'url': 'https://navidrome.test',
            'username': 'user',
            'password': 'pass',
            'scan_after_download': False,
        }
    }
    result = sync_playlist_to_navidrome(
        'My List',
        [
            {
                'name': 'Track',
                'artists': ['Artist'],
                'duration': 200,
                'filename': 'Artist/Track.mp3',
            }
        ],
        settings,
    )
    assert result is not None
    assert result.playlist_id == 'pl-existing'
    all_urls = [call[0][0] for call in mock_get.call_args_list]
    assert any('playlistId=pl-existing' in url for url in all_urls)
    assert not any('deletePlaylist' in url for url in all_urls)
