from typing import Any
from pathlib import Path
from unittest.mock import MagicMock

from downtify.slskd_provider import (
    _slskd_transfer_progress_pct,
    SlskdClient,
    _collect_matching_files,
    _filter_slskd_responses,
    _find_on_disk,
    _flatten_slskd_responses,
    _paths_match,
    _slskd_search_queries,
    download_from_slskd,
)


def test_flatten_slskd_responses_attaches_username_to_files():
    rows = _flatten_slskd_responses(
        [
            {
                'username': 'peer1',
                'files': [
                    {'filename': 'Artist - Track.mp3', 'size': 1},
                ],
            }
        ]
    )
    assert len(rows) == 1
    assert rows[0]['username'] == 'peer1'
    assert rows[0]['filename'] == 'Artist - Track.mp3'


def test_slskd_search_queries_prefers_title_dash_artist():
    queries = _slskd_search_queries(
        {
            'artists': ['4D4M'],
            'name': "YOU KNOW WHERE WE'RE GOING - Hardstyle Bass Bounce Edition",
            'album_name': "YOU KNOW WHERE WE'RE GOING",
        }
    )
    assert queries[0] == "YOU KNOW WHERE WE'RE GOING - 4D4M"
    assert 'YOU KNOW WHERE WERE GOING' in queries


def test_collect_matching_files_skips_wrong_extension_and_keywords():
    song = {
        'artists': ['Melxdie'],
        'name': 'DRAMA KING',
        'album_name': 'FAILED ROCKSTAR',
        'duration': 152,
    }
    responses = [
        {
            'username': 'peer1',
            'fileCount': 2,
            'hasFreeUploadSlot': True,
            'files': [
                {
                    'filename': '@@x\\Artist - DRAMA KING (live).mp3',
                    'size': 1,
                    'length': 152,
                },
                {
                    'filename': '@@x\\Melxdie - DRAMA KING.mp3',
                    'size': 2,
                    'length': 152,
                    'bitRate': 320,
                },
            ],
        }
    ]
    matches = _collect_matching_files(song, responses)
    assert len(matches) == 1
    assert 'DRAMA KING.mp3' in matches[0]['filename']


def test_filter_slskd_responses_hides_no_free_slot_and_locked_files():
    song = {
        'artists': ['Melxdie'],
        'name': 'DRAMA KING',
        'album_name': 'FAILED ROCKSTAR',
        'duration': 152,
    }
    responses = [
        {
            'username': 'no_slot',
            'fileCount': 1,
            'hasFreeUploadSlot': False,
            'files': [
                {
                    'filename': '@@x\\Melxdie - DRAMA KING.mp3',
                    'size': 1,
                    'length': 152,
                },
            ],
        },
        {
            'username': 'locked_peer',
            'fileCount': 1,
            'hasFreeUploadSlot': True,
            'lockedFiles': [
                {'filename': '@@x\\Melxdie - DRAMA KING.mp3'},
            ],
            'files': [
                {
                    'filename': '@@x\\Melxdie - DRAMA KING.mp3',
                    'size': 1,
                    'length': 152,
                    'isLocked': True,
                },
            ],
        },
        {
            'username': 'good_peer',
            'fileCount': 1,
            'hasFreeUploadSlot': True,
            'files': [
                {
                    'filename': '@@x\\Melxdie - DRAMA KING.mp3',
                    'size': 2,
                    'length': 152,
                    'bitRate': 320,
                },
            ],
        },
    ]
    filtered = _filter_slskd_responses(responses)
    assert [r['username'] for r in filtered] == ['locked_peer', 'good_peer']
    matches = _collect_matching_files(song, responses)
    assert len(matches) == 1
    assert matches[0]['username'] == 'good_peer'


def test_start_search_requests_filtered_responses():
    client = SlskdClient(
        {'base_url': 'https://slskd.example', 'api_key': 'key', 'timeout_seconds': 5}
    )
    captured: dict[str, Any] = {}

    def fake_request(method, path, **kwargs):
        captured['method'] = method
        captured['path'] = path
        captured['json'] = kwargs.get('json')
        resp = MagicMock()
        resp.content = b'{"id":"search-1"}'
        resp.raise_for_status = lambda: None
        resp.json = lambda: {'id': 'search-1'}
        return resp

    client._request = fake_request  # type: ignore[method-assign]
    search_id = client.start_search('Artist - Track')
    assert search_id == 'search-1'
    assert captured['json']['filterResponses'] is True
    assert captured['json']['minimumResponseFileCount'] == 1


def test_paths_match_compares_basenames():
    assert _paths_match(
        '@@music\\Artist - Track.mp3',
        'Artist - Track.mp3',
    )
    assert not _paths_match('a.mp3', 'b.mp3')


def test_find_on_disk_searches_username_nested_layout(tmp_path):
    root = tmp_path / 'downloads'
    track = root / 'peer1' / 'My Share' / 'Artist - Track.mp3'
    track.parent.mkdir(parents=True)
    track.write_bytes(b'x' * 4096)
    found = _find_on_disk(
        [root],
        '@@My Share\\Artist - Track.mp3',
        username='peer1',
    )
    assert found == track


def test_slskd_transfer_progress_uses_percent_complete():
    pct, msg = _slskd_transfer_progress_pct(
        transfer={'percentComplete': 50.0, 'size': 1000},
        expected_size=1000,
    )
    assert msg == 'Downloading'
    assert 65.0 < pct < 67.0


def test_slskd_transfer_progress_uses_bytes_transferred():
    pct, _msg = _slskd_transfer_progress_pct(
        transfer={'bytesTransferred': 250, 'size': 1000},
        expected_size=1000,
    )
    assert 52.0 < pct < 54.0


def test_slskd_transfer_progress_falls_back_when_no_stats():
    pct, msg = _slskd_transfer_progress_pct(poll_attempt=3)
    assert msg == 'Waiting for slskd'
    assert 40.0 < pct < 45.0


def test_find_transfer_matches_basename_not_full_path():
    client = SlskdClient(
        {'base_url': 'https://slskd.example', 'api_key': 'key', 'timeout_seconds': 5}
    )
    client.list_download_transfers = lambda: [  # type: ignore[method-assign]
        {
            'username': 'peer1',
            'directories': [
                {
                    'files': [
                        {
                            'filename': 'Artist - Track.mp3',
                            'state': 'Completed, Succeeded',
                            'bytesRemaining': 0,
                        }
                    ]
                }
            ],
        }
    ]
    row = client.find_transfer('peer1', '@@music\\Artist - Track.mp3')
    assert row is not None
    assert row['state'] == 'Completed, Succeeded'


def test_enqueue_download_uses_username_endpoint():
    client = SlskdClient(
        {'base_url': 'https://slskd.example', 'api_key': 'key', 'timeout_seconds': 5}
    )
    captured: dict[str, Any] = {}

    def fake_request(method, path, **kwargs):
        captured['method'] = method
        captured['path'] = path
        captured['json'] = kwargs.get('json')
        resp = MagicMock()
        resp.content = b'{}'
        resp.raise_for_status = lambda: None
        resp.json = lambda: {}
        return resp

    client._request = fake_request  # type: ignore[method-assign]
    ok = client.enqueue_download(
        {
            'username': 'peer1',
            'filename': 'music\\Artist - Track.mp3',
            'size': 1234,
        }
    )
    assert ok is True
    assert captured['path'] == '/api/v0/transfers/downloads/peer1'
    assert captured['json'] == [
        {'filename': 'music\\Artist - Track.mp3', 'size': 1234}
    ]


def test_download_from_slskd_tries_next_candidate_on_failure(monkeypatch, tmp_path):
    candidates = [
        {
            'username': 'peer1',
            'filename': 'Artist - Track (1).mp3',
            'size': 1000,
        },
        {
            'username': 'peer2',
            'filename': 'Artist - Track (2).mp3',
            'size': 1000,
        },
    ]
    success = tmp_path / 'Artist - Track (2).mp3'
    success.write_bytes(b'audio')

    class FakeClient:
        base_url = 'https://slskd.example'

        def configured(self) -> bool:
            return True

        def can_connect(self) -> bool:
            return True

        def start_search(self, query: str) -> str:
            return 'search-1'

        def wait_search_complete(self, *args, **kwargs) -> bool:
            return True

        def search_responses(self, search_id: str) -> list[dict[str, Any]]:
            return [{'username': 'peer1', 'hasFreeUploadSlot': True, 'fileCount': 1}]

        def delete_search(self, search_id: str) -> None:
            pass

        def enqueue_download(self, row: dict[str, Any]) -> bool:
            return True

        def remote_download_directories(self) -> list[str]:
            return []

    wait_calls: list[str] = []

    def fake_wait(client, song, username, filename, settings, roots, **kwargs):
        wait_calls.append(filename)
        if filename.endswith('(2).mp3'):
            return success
        return None

    monkeypatch.setattr(
        'downtify.slskd_provider.SlskdClient',
        lambda settings: FakeClient(),
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._collect_matching_files',
        lambda song, responses: list(candidates),
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._filter_by_quality',
        lambda files, settings: files,
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._search_roots',
        lambda settings, client: [tmp_path],
    )
    monkeypatch.setattr('downtify.slskd_provider._wait_for_slskd_file', fake_wait)

    settings = {
        'enabled': True,
        'base_url': 'https://slskd.example',
        'api_key': 'key',
        'output_dir': str(tmp_path),
        'source_dir': str(tmp_path),
        'leave_in_place': True,
    }
    result = download_from_slskd(
        {'name': 'Track', 'artists': ['Artist'], 'album_name': 'Album'},
        settings,
    )
    assert result == success
    assert len(wait_calls) == 2
    assert wait_calls[0].endswith('(1).mp3')
    assert wait_calls[1].endswith('(2).mp3')
