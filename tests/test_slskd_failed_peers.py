"""slskd candidates that failed: remembered, skipped, and cancelled in
slskd when Downtify gives up on them (downtify/slskd_provider.py)."""

from __future__ import annotations

from typing import Any

import httpx

from downtify import slskd_provider
from downtify.slskd_provider import (
    BAD_FILE_SECONDS,
    BUSY_PEER_SECONDS,
    SLOW_FILE_SECONDS,
    SlskdClient,
    download_from_slskd,
    order_by_past_failures,
    remember_failure,
)


def _row(user: str, name: str) -> dict[str, Any]:
    return {'username': user, 'filename': name}


def test_slskd_errors_are_sorted_into_kinds():
    errored = {'state': 'Completed, Errored'}
    assert (
        remember_failure(
            'a', 'x', {**errored, 'exception': 'File not shared.'}
        )
        == 'bad_file'
    )
    assert (
        remember_failure(
            'b',
            'x',
            {
                **errored,
                'exception': 'the remote size of 3112271 does not match '
                'expected size 194352',
            },
        )
        == 'bad_file'
    )
    assert remember_failure('c', 'x', {'state': 'Completed, Rejected'}) == (
        'bad_file'
    )
    assert (
        remember_failure(
            'd', 'x', {**errored, 'exception': 'Overwhelmed with requests'}
        )
        == 'busy_peer'
    )
    assert remember_failure('e', 'x', {'state': 'InProgress'}) == 'slow'
    assert remember_failure('f', 'x', None) == 'slow'


def test_a_bad_file_is_skipped_for_a_day_and_then_tried_again():
    remember_failure(
        'peer', 'song.mp3', {'exception': 'File not shared.'}, now=1000.0
    )
    files = [_row('peer', 'song.mp3'), _row('other', 'song.mp3')]
    later = 1000.0 + BAD_FILE_SECONDS - 1
    assert order_by_past_failures(files, now=later) == [files[1]]
    after = 1000.0 + BAD_FILE_SECONDS + 1
    assert order_by_past_failures(files, now=after) == files


def test_a_slow_file_is_skipped_for_an_hour():
    remember_failure('peer', 'song.mp3', None, now=0.0)
    files = [_row('peer', 'song.mp3')]
    assert order_by_past_failures(files, now=SLOW_FILE_SECONDS - 1) == []
    assert order_by_past_failures(files, now=SLOW_FILE_SECONDS + 1) == files


def test_only_that_file_is_skipped_not_the_peer():
    remember_failure('peer', 'a.mp3', {'exception': 'File not shared.'})
    files = [_row('peer', 'a.mp3'), _row('peer', 'b.mp3')]
    assert order_by_past_failures(files) == [files[1]]


def test_an_overwhelmed_peer_is_tried_last_for_a_while():
    remember_failure(
        'busy', 'x.mp3', {'exception': 'Overwhelmed with requests'}, now=0.0
    )
    files = [_row('busy', 'song.mp3'), _row('calm', 'song.mp3')]
    assert order_by_past_failures(files, now=60.0) == [files[1], files[0]]
    assert order_by_past_failures(files, now=BUSY_PEER_SECONDS + 1) == files


def test_cancel_download_deletes_that_transfer_and_keeps_its_record():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(204)

    client = SlskdClient({'base_url': 'http://slskd', 'api_key': 'k'})
    client.session = httpx.Client(transport=httpx.MockTransport(handler))
    assert client.cancel_download('some user', 'abc-123') is True
    assert seen[0].method == 'DELETE'
    assert (
        seen[0].url.raw_path
        == b'/api/v0/transfers/downloads/some%20user/abc-123'
    )
    # Cancelled, not removed: slskd's own history and stats stay as they are.
    assert 'remove' not in str(seen[0].url)
    assert client.cancel_download('', 'abc') is False


def _fake_client(transfers: dict[str, dict[str, Any]], cancelled: list):
    class FakeClient:
        base_url = 'https://slskd.example'
        configured = staticmethod(lambda: True)
        can_connect = staticmethod(lambda: True)
        start_search = staticmethod(lambda query: 'search-1')
        wait_search_complete = staticmethod(lambda *a, **k: True)
        delete_search = staticmethod(lambda search_id: None)
        enqueue_download = staticmethod(lambda row: True)
        remote_download_directories = staticmethod(lambda: [])

        @staticmethod
        def search_responses(search_id):
            return [{'username': 'p1', 'hasFreeUploadSlot': True}]

        @staticmethod
        def find_transfer(username, filename):
            return transfers.get(username)

        @staticmethod
        def cancel_download(username, transfer_id):
            cancelled.append((username, transfer_id))
            return True

    return FakeClient()


def _download(monkeypatch, tmp_path, client, arrives: set[str]):
    candidates = [
        {
            'username': user,
            'filename': f'Artist - Track ({user}).mp3',
            'size': 1000,
            'match_score': 9,
            'match_reasons': ['artist', 'title'],
        }
        for user in ('p1', 'p2', 'p3')
    ]
    tried: list[str] = []

    def fake_wait(*args, **kwargs):
        tried.append(args[2])
        if args[2] in arrives:
            found = tmp_path / args[3]
            found.write_bytes(b'audio')
            return found
        return None

    monkeypatch.setattr(slskd_provider, 'SlskdClient', lambda s: client)
    monkeypatch.setattr(
        slskd_provider,
        '_rank_slskd_candidates',
        lambda song, responses, settings=None, **k: list(candidates),
    )
    monkeypatch.setattr(
        slskd_provider, '_select_download_candidates', lambda r, s: r
    )
    monkeypatch.setattr(
        slskd_provider, '_search_roots', lambda s, c: [tmp_path]
    )
    monkeypatch.setattr(slskd_provider, '_wait_for_slskd_file', fake_wait)
    monkeypatch.setattr(
        slskd_provider, '_resolve_downloaded_file', lambda *a, **k: None
    )
    settings = {
        'enabled': True,
        'base_url': 'https://slskd.example',
        'api_key': 'key',
        'output_dir': str(tmp_path),
        'source_dir': str(tmp_path),
        'leave_in_place': True,
    }
    download_from_slskd(
        {'name': 'Track', 'artists': ['Artist'], 'album_name': 'Album'},
        settings,
    )
    return tried


def test_a_failed_candidate_is_cancelled_and_not_asked_again(
    monkeypatch, tmp_path
):
    transfers = {
        # p1: the peer's copy changed size; slskd already ended it.
        'p1': {
            'id': 't1',
            'state': 'Completed, Errored',
            'exception': 'the remote size of 3722124 does not match '
            'expected size 3485990',
        },
        # p2: still queued at the peer when Downtify gave up on it.
        'p2': {
            'id': 't2',
            'state': 'Queued, Remotely',
            'bytesRemaining': 1000,
        },
    }
    cancelled: list = []
    client = _fake_client(transfers, cancelled)

    first = _download(monkeypatch, tmp_path, client, arrives={'p3'})
    assert first == ['p1', 'p2', 'p3']
    # Only the transfer slskd was still waiting on is cancelled.
    assert cancelled == [('p2', 't2')]

    # The same song again (a watch's next check): p1 and p2 are skipped.
    second = _download(monkeypatch, tmp_path, client, arrives={'p3'})
    assert second == ['p3']
