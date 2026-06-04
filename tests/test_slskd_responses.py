from pathlib import Path
from typing import Any

from downtify.slskd_provider import (
    SlskdClient,
    _collect_matching_files,
    _contains_keyword,
    _filter_slskd_responses,
    _find_on_disk,
    _flatten_slskd_responses,
    _match_min_score,
    _paths_match,
    _rank_slskd_candidates,
    _slskd_search_queries,
    _slskd_transfer_progress_pct,
    _title_in_basename,
    download_from_slskd,
)


def test_flatten_slskd_responses_attaches_username_to_files():
    rows = _flatten_slskd_responses([
        {
            'username': 'peer1',
            'files': [
                {'filename': 'Artist - Track.mp3', 'size': 1},
            ],
        }
    ])
    assert len(rows) == 1
    assert rows[0]['username'] == 'peer1'
    assert rows[0]['filename'] == 'Artist - Track.mp3'


def test_slskd_search_queries_prefers_title_dash_artist():
    queries = _slskd_search_queries({
        'artists': ['4D4M'],
        'name': "YOU KNOW WHERE WE'RE GOING - Hardstyle Bass Bounce Edition",
        'album_name': "YOU KNOW WHERE WE'RE GOING",
    })
    assert queries[0] == 'YOU KNOW WHERE WERE GOING - 4D4M'
    assert 'YOU KNOW WHERE WERE GOING' in queries


def test_slskd_search_queries_include_full_and_short_radio_mix():
    queries = _slskd_search_queries({
        'artists': ['Y:K'],
        'name': 'Loud Enough - Radio Mix',
    })
    assert queries[0] == 'Loud Enough - Y:K'
    assert 'Loud Enough - Radio Mix - Y:K' in queries
    assert 'Y:K Loud Enough - Radio Mix' in queries


def test_rank_accepts_radio_mix_filename_for_radio_mix_track():
    song = {
        'artists': ['Y:K'],
        'name': 'Loud Enough - Radio Mix',
        'duration': 174,
    }
    responses = [
        {
            'username': 'peer1',
            'fileCount': 1,
            'hasFreeUploadSlot': True,
            'files': [
                {
                    'filename': '@@x\\Y K - Loud Enough - Radio Mix.mp3',
                    'size': 1,
                    'length': 176,
                    'bitRate': 320,
                },
            ],
        },
    ]
    ranked = _rank_slskd_candidates(song, responses, {})
    assert len(ranked) == 1


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
    assert matches[0]['match_score'] >= _match_min_score({})


def test_rank_accepts_title_and_artist_from_parent_folders():
    song = {
        'artists': ['Daft Punk'],
        'name': 'One More Time',
        'album_name': 'Discovery',
        'duration': 320,
    }
    responses = [
        {
            'username': 'peer1',
            'fileCount': 1,
            'hasFreeUploadSlot': True,
            'files': [
                {
                    'filename': '@@files\\Daft Punk\\Discovery\\01 - One More Time.mp3',
                    'size': 1,
                    'length': 320,
                    'bitRate': 320,
                },
            ],
        }
    ]
    ranked = _rank_slskd_candidates(song, responses)
    assert len(ranked) == 1
    assert 'One More Time' in ranked[0]['filename']
    reasons = ranked[0].get('match_reasons') or []
    assert any(
        tag in reasons
        for tag in (
            'title_in_path',
            'folder_segment',
            'artist_in_path',
            'album_folder',
        )
    )


def test_contains_keyword_ignores_remix_in_distant_parent_folder():
    song = {
        'artists': ['Artist'],
        'name': 'Song',
        'album_name': 'Album',
        'duration': 200,
    }

    assert not _contains_keyword(
        song,
        '@@share\\Remix Collections\\Artist\\Song.mp3',
    )
    assert _contains_keyword(song, '@@share\\Artist\\Song (Remix).mp3')


def test_rank_rejects_album_only_without_artist_in_filename():
    song = {
        'artists': ['Pitbull'],
        'name': 'Hotel Room Service',
        'album_name': 'Hotel Room Service Album',
        'duration': 242,
    }
    responses = [
        {
            'username': 'peer1',
            'fileCount': 1,
            'hasFreeUploadSlot': True,
            'files': [
                {
                    'filename': '@@x\\Compilations\\Hotel Room Service Album\\01 Intro.mp3',
                    'size': 1,
                    'length': 242,
                },
            ],
        }
    ]
    ranked = _rank_slskd_candidates(song, responses)
    assert ranked == []


def test_rank_rejects_wrong_file_when_only_folder_matches_title():
    """Folder named after the request must not satisfy match without title on file."""
    song = {
        'artists': ['Tom Jung'],
        'name': 'Light',
        'album_name': 'Light',
        'duration': 210,
    }
    responses = [
        {
            'username': 'peer1',
            'fileCount': 1,
            'hasFreeUploadSlot': True,
            'files': [
                {
                    'filename': (
                        '@@share\\Tom Jung\\Light\\'
                        '04 - RamirezPouyaShakewell - Gold Thangs & '
                        'Pinky Rangs (Da Hooptie).mp3'
                    ),
                    'size': 1,
                    'length': 210,
                    'bitRate': 320,
                },
            ],
        }
    ]
    ranked = _rank_slskd_candidates(song, responses)
    assert ranked == []


def test_rank_rejects_wrong_track_same_artist_short_title():
    song = {
        'artists': ['Gunna'],
        'name': 'W',
        'album_name': 'Single',
        'duration': 200,
    }
    responses = [
        {
            'username': 'peer1',
            'fileCount': 2,
            'hasFreeUploadSlot': True,
            'files': [
                {
                    'filename': 'Unreleased\\Mellow (feat. Gunna & Lil Baby).mp3',
                    'size': 1,
                    'length': 180,
                },
                {
                    'filename': 'Gunna - W.mp3',
                    'size': 2,
                    'length': 200,
                    'bitRate': 320,
                },
            ],
        }
    ]
    ranked = _rank_slskd_candidates(song, responses)
    assert len(ranked) == 1
    assert 'Gunna - W.mp3' in ranked[0]['filename']
    assert ranked[0]['match_score'] >= _match_min_score({})


def test_rank_prefers_better_title_match():
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
                    'filename': '@@x\\Melxdie - DRAMA KING (demo).mp3',
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
    ranked = _rank_slskd_candidates(song, responses)
    assert len(ranked) >= 1
    assert 'DRAMA KING.mp3' in ranked[0]['filename']
    assert 'demo' not in ranked[0]['filename'].casefold()


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
    client = SlskdClient({
        'base_url': 'https://slskd.example',
        'api_key': 'key',
        'timeout_seconds': 5,
    })
    captured: dict[str, Any] = {}

    def fake_request(method, path, *, json_body=None):
        captured['method'] = method
        captured['path'] = path
        captured['json'] = json_body
        return {'id': 'search-1'}

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
    client = SlskdClient({
        'base_url': 'https://slskd.example',
        'api_key': 'key',
        'timeout_seconds': 5,
    })
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
    client = SlskdClient({
        'base_url': 'https://slskd.example',
        'api_key': 'key',
        'timeout_seconds': 5,
    })
    captured: dict[str, Any] = {}

    def fake_request(method, path, *, json_body=None):
        captured['method'] = method
        captured['path'] = path
        captured['json'] = json_body
        return {}

    client._request = fake_request  # type: ignore[method-assign]
    ok = client.enqueue_download({
        'username': 'peer1',
        'filename': 'music\\Artist - Track.mp3',
        'size': 1234,
    })
    assert ok is True
    assert captured['path'] == '/api/v0/transfers/downloads/peer1'
    assert captured['json'] == [
        {'filename': 'music\\Artist - Track.mp3', 'size': 1234}
    ]


def test_title_in_basename_rejects_substring_false_positive():
    assert not _title_in_basename('Artist - highlight.mp3', 'light')
    assert _title_in_basename('Tom Jung - Light.mp3', 'light')


def test_download_from_slskd_retries_when_tags_mismatch(
    monkeypatch, tmp_path
):
    candidates = [
        {
            'username': 'peer1',
            'filename': 'Tom Jung/Light/wrong.mp3',
            'size': 1000,
            'match_score': 8,
        },
        {
            'username': 'peer2',
            'filename': 'Tom Jung - Light.mp3',
            'size': 1000,
            'match_score': 9,
        },
    ]
    good = tmp_path / 'Tom Jung - Light.mp3'
    good.write_bytes(b'ok')
    bad = tmp_path / 'wrong.mp3'
    bad.write_bytes(b'bad')

    class FakeClient:
        base_url = 'https://slskd.example'

        @staticmethod
        def configured() -> bool:
            return True

        @staticmethod
        def can_connect() -> bool:
            return True

        @staticmethod
        def start_search(query: str) -> str:
            return 'search-1'

        @staticmethod
        def wait_search_complete(*args, **kwargs) -> bool:
            return True

        @staticmethod
        def search_responses(search_id: str) -> list[dict[str, Any]]:
            return [{'username': 'peer1', 'hasFreeUploadSlot': True, 'fileCount': 2}]

        @staticmethod
        def delete_search(search_id: str) -> None:
            pass

        @staticmethod
        def enqueue_download(row: dict[str, Any]) -> bool:
            return True

        @staticmethod
        def remote_download_directories() -> list[str]:
            return []

    def fake_wait(*args, **kwargs):
        filename = args[3] if len(args) > 3 else ''
        if 'wrong' in filename:
            return bad
        return good

    def fake_verify(path, song):
        return path == good

    monkeypatch.setattr(
        'downtify.slskd_provider.SlskdClient',
        lambda settings: FakeClient(),
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._rank_slskd_candidates',
        lambda song, responses, settings=None: list(candidates),
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._select_download_candidates',
        lambda ranked, settings: ranked,
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._search_roots',
        lambda settings, client: [tmp_path],
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._wait_for_slskd_file', fake_wait
    )
    monkeypatch.setattr(
        'downtify.slskd_provider.verify_downloaded_file_matches_spotify',
        fake_verify,
    )
    removed: list[Path] = []

    def _record_discard(path: Path) -> None:
        removed.append(path)

    monkeypatch.setattr(
        'downtify.slskd_provider._discard_mismatched_download',
        _record_discard,
    )

    settings = {
        'enabled': True,
        'base_url': 'https://slskd.example',
        'api_key': 'key',
        'output_dir': str(tmp_path),
        'source_dir': str(tmp_path),
        'leave_in_place': True,
    }
    result = download_from_slskd(
        {'name': 'Light', 'artists': ['Tom Jung'], 'album_name': 'Light'},
        settings,
    )
    assert result == good
    assert bad in removed


def test_download_from_slskd_tries_next_candidate_on_failure(
    monkeypatch, tmp_path
):
    candidates = [
        {
            'username': 'peer1',
            'filename': 'Artist - Track (1).mp3',
            'size': 1000,
            'match_score': 8,
            'match_reasons': ['artist', 'title'],
        },
        {
            'username': 'peer2',
            'filename': 'Artist - Track (2).mp3',
            'size': 1000,
            'match_score': 9,
            'match_reasons': ['artist', 'title'],
        },
    ]
    success = tmp_path / 'Artist - Track (2).mp3'
    success.write_bytes(b'audio')

    class FakeClient:
        base_url = 'https://slskd.example'

        @staticmethod
        def configured() -> bool:
            return True

        @staticmethod
        def can_connect() -> bool:
            return True

        @staticmethod
        def start_search(query: str) -> str:
            return 'search-1'

        @staticmethod
        def wait_search_complete(*args, **kwargs) -> bool:
            return True

        @staticmethod
        def search_responses(search_id: str) -> list[dict[str, Any]]:
            return [
                {
                    'username': 'peer1',
                    'hasFreeUploadSlot': True,
                    'fileCount': 1,
                }
            ]

        @staticmethod
        def delete_search(search_id: str) -> None:
            pass

        @staticmethod
        def enqueue_download(row: dict[str, Any]) -> bool:
            return True

        @staticmethod
        def remote_download_directories() -> list[str]:
            return []

    wait_calls: list[str] = []

    def fake_wait(*args, **kwargs):
        filename = args[3] if len(args) > 3 else ''
        wait_calls.append(filename)
        if filename.endswith('(2).mp3'):
            return success
        return None

    monkeypatch.setattr(
        'downtify.slskd_provider.SlskdClient',
        lambda settings: FakeClient(),
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._rank_slskd_candidates',
        lambda song, responses, settings=None: list(candidates),
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._select_download_candidates',
        lambda ranked, settings: ranked,
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._search_roots',
        lambda settings, client: [tmp_path],
    )
    monkeypatch.setattr(
        'downtify.slskd_provider._wait_for_slskd_file', fake_wait
    )

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
