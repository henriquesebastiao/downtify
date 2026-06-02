from unittest.mock import MagicMock, patch

from downtify.navidrome import (
    NavidromeClient,
    _effective_navidrome_settings,
    _path_matches,
    sync_playlist_to_navidrome,
)


def _route_mock_get(responses: dict[str, MagicMock]):
    def _handler(url: str, *args, **kwargs):
        for key, resp in responses.items():
            if key in url:
                return resp
        raise AssertionError(f'unexpected GET {url}')

    return _handler


def test_effective_navidrome_settings_defaults():
    out = _effective_navidrome_settings({})
    assert out['enabled'] is False
    assert out['scan_wait_seconds'] == 120


def test_search_song_id_exact_mutagen_tags():
    client = NavidromeClient({
        'url': 'https://navidrome.test',
        'username': 'u',
        'password': 'p',
    })

    def fake_request(endpoint, extra=None, **kwargs):
        assert endpoint == 'search3'
        return {
            'searchResult3': {
                'song': [
                    {
                        'id': 'wrong',
                        'title': 'Tona',
                        'artist': 'Other',
                        'duration': 200,
                        'path': 'other/tona.mp3',
                    },
                    {
                        'id': 'right',
                        'title': 'Tona',
                        'artist': 'Solo, DJ A-Boom, ARLENN',
                        'duration': 201,
                        'path': 'other/path.mp3',
                    },
                ]
            }
        }

    client._request = fake_request  # type: ignore[method-assign]
    sid = client.search_song_id({
        'name': 'Tona',
        'artists': ['Solo', 'DJ A-Boom', 'ARLENN'],
        'duration': 200,
        'filename': 'Albanian Car Songs/Solo, DJ A-Boom, ARLENN - Tona.mp3',
        'library_from_tags': True,
    })
    assert sid == 'right'


def test_search_song_id_matches_title_and_artist():
    client = NavidromeClient({
        'url': 'https://navidrome.test',
        'username': 'u',
        'password': 'p',
    })

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
    sid = client.search_song_id({
        'name': 'DRAMA KING',
        'artists': ['Melxdie'],
        'duration': 152,
    })
    assert sid == 'song-1'


def test_path_matches_basename_when_parent_folder_differs():
    keys = ['albanian car songs/solo - tona.mp3', 'solo - tona.mp3']
    assert _path_matches(keys, 'Music/Imports/solo - tona.mp3')
    assert not _path_matches(keys, 'Music/Imports/other.mp3')


def test_path_matches_ampersand_in_artist_name():
    keys = ['albanian car songs/blunt & real, kaos, bardool - hey.mp3']
    assert _path_matches(keys, 'music/Blunt & Real, Kaos, Bardool - Hey.mp3')
    assert _path_matches(keys, 'music/Blunt and Real, Kaos, Bardool - Hey.mp3')


def test_path_matches_when_navidrome_has_extra_parent_folders():
    keys = ['albanian car songs/solo, dj a-boom, arlenn - tona.mp3']
    navidrome = 'my/local/root/downtify/Albanian Car Songs/Solo, DJ A-Boom, ARLENN - Tona.mp3'
    assert _path_matches(keys, navidrome)


def test_search_song_id_finds_track_by_filename_stem_first():
    """Filename search finds the row when title+artist search does not."""

    client = NavidromeClient({
        'url': 'https://navidrome.test',
        'username': 'u',
        'password': 'p',
    })

    def fake_request(endpoint, extra=None, **kwargs):
        assert endpoint == 'search3'
        query = str((extra or {}).get('query') or '')
        if query.casefold() == 'tona solo':
            return {'searchResult3': {'song': []}}
        if 'arlenn - tona' in query.casefold():
            return {
                'searchResult3': {
                    'song': [
                        {
                            'id': 'tona-id',
                            'title': 'Other Tags',
                            'artist': 'X',
                            'duration': 1,
                            'path': (
                                'library/imports/Albanian Car Songs/'
                                'Solo, DJ A-Boom, ARLENN - Tona.mp3'
                            ),
                        }
                    ]
                }
            }
        return {'searchResult3': {'song': []}}

    client._request = fake_request  # type: ignore[method-assign]
    sid = client.search_song_id({
        'name': 'Tona',
        'artists': ['Solo', 'DJ A-Boom', 'ARLENN'],
        'duration': 200,
        'filename': 'Albanian Car Songs/Solo, DJ A-Boom, ARLENN - Tona.mp3',
    })
    assert sid == 'tona-id'


def test_search_song_id_matches_by_filename_in_navidrome_path():
    """Track is in Navidrome under a different folder prefix than Downtify stored path."""

    client = NavidromeClient({
        'url': 'https://navidrome.test',
        'username': 'u',
        'password': 'p',
    })
    calls: list[str] = []

    def fake_request(endpoint, extra=None, **kwargs):
        assert endpoint == 'search3'
        calls.append(str((extra or {}).get('query')))
        return {
            'searchResult3': {
                'song': [
                    {
                        'id': 'song-82',
                        'title': 'Different Tag Title',
                        'artist': 'Someone Else',
                        'duration': 999,
                        'path': 'library/imports/solo, dj a-boom, arlenn - tona.mp3',
                    }
                ]
            }
        }

    client._request = fake_request  # type: ignore[method-assign]
    sid = client.search_song_id({
        'name': 'Tona',
        'artists': ['Solo', 'DJ A-Boom', 'ARLENN'],
        'duration': 200,
        'filename': 'Albanian Car Songs/Solo, DJ A-Boom, ARLENN - Tona.mp3',
    })
    assert sid == 'song-82'
    assert any('tona' in q.casefold() for q in calls)


@patch('downtify.navidrome.requests.post')
@patch('downtify.navidrome.requests.get')
def test_sync_playlist_creates_playlist(mock_get, mock_post):
    ping_resp = MagicMock()
    ping_resp.json.return_value = {'subsonic-response': {'status': 'ok'}}
    ping_resp.raise_for_status = MagicMock()

    scan_resp = MagicMock()
    scan_resp.json.return_value = {
        'subsonic-response': {
            'status': 'ok',
            'scanStatus': {'scanning': False},
        }
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

    mock_get.side_effect = _route_mock_get({
        '/rest/ping': ping_resp,
        '/rest/startScan': start_scan_resp,
        '/rest/getScanStatus': scan_resp,
        '/rest/search3': search_resp,
        '/rest/getPlaylists': playlists_resp,
        '/rest/updatePlaylist': update_resp,
    })
    mock_post.side_effect = [create_resp]

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
                'library_from_tags': True,
            }
        ],
        settings,
    )
    assert result is not None
    assert result.playlist_id == 'pl-1'
    assert result.matched == 1


@patch('downtify.navidrome.requests.post')
@patch('downtify.navidrome.requests.get')
def test_sync_playlist_updates_existing_by_id(mock_get, mock_post):
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
            'playlists': {
                'playlist': {'id': 'pl-existing', 'name': 'My List'}
            },
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

    mock_get.side_effect = _route_mock_get({
        '/rest/ping': ping_resp,
        '/rest/search3': search_resp,
        '/rest/getPlaylists': playlists_resp,
        '/rest/updatePlaylist': update_resp,
    })
    mock_post.side_effect = [replace_resp]

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
    create_calls = [
        call
        for call in mock_post.call_args_list
        if 'createPlaylist' in call[0][0]
    ]
    assert len(create_calls) == 1
    assert create_calls[0][1]['params']['playlistId'] == 'pl-existing'
    all_get_urls = [call[0][0] for call in mock_get.call_args_list]
    assert not any('deletePlaylist' in url for url in all_get_urls)


@patch('downtify.navidrome.requests.post')
def test_create_playlist_batches_many_songs(mock_post):
    """Large playlists use POST and batch songIdToAdd to avoid HTTP 414."""

    ok = MagicMock()
    ok.json.return_value = {
        'subsonic-response': {
            'status': 'ok',
            'playlist': {'id': 'pl-big'},
        }
    }
    ok.raise_for_status = MagicMock()
    mock_post.return_value = ok

    client = NavidromeClient({
        'url': 'https://navidrome.test',
        'username': 'u',
        'password': 'p',
    })
    song_ids = [f'song-{index}' for index in range(150)]
    playlist_id = client.create_playlist('Big List', song_ids)
    assert playlist_id == 'pl-big'
    assert mock_post.call_count == 2
    create_url, create_kwargs = mock_post.call_args_list[0][0][0], mock_post.call_args_list[0][1]
    assert 'createPlaylist' in create_url
    assert len(create_kwargs['data']) == 80
    update_url, update_kwargs = mock_post.call_args_list[1][0][0], mock_post.call_args_list[1][1]
    assert 'updatePlaylist' in update_url
    assert update_kwargs['params']['playlistId'] == 'pl-big'
    assert len(update_kwargs['data']) == 70
