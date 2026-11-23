"""Per-user storage quotas (issue #677): the rules, the store, the routes
and the refusal of downloads once an account is out of space. Offline.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from downtify import api, storage_quota_routes
from downtify.auth import ADMIN, CLIENT, Principal, classify
from downtify.library_sync import LibrarySync
from downtify.storage_quota import (
    QUOTA_STATUS_CODE,
    SOURCE_ADMIN,
    SOURCE_DEFAULT,
    SOURCE_USER,
    UNLIMITED,
    QuotaError,
    QuotaExceededError,
    StorageQuotas,
    clean_quota,
    effective_quota,
    exceeded_message,
    format_bytes,
    quota_status,
    used_bytes,
)
from downtify.track_owners import TrackOwners
from downtify.users import UserStore

GB = 1024**3
MB = 1024**2


# ── Rules ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        (None, None),
        ('', None),
        ('  ', None),
        (-1, UNLIMITED),
        ('-1', UNLIMITED),
        (GB, GB),
        (str(2 * GB), 2 * GB),
    ],
)
def test_clean_quota(value, expected):
    assert clean_quota(value) == expected


@pytest.mark.parametrize('value', [0, -5, 'abc', True, 1024**6, [1]])
def test_clean_quota_refuses_nonsense(value):
    with pytest.raises(QuotaError):
        clean_quota(value)


def test_effective_quota():
    assert effective_quota(True, GB, GB) == (None, SOURCE_ADMIN)
    assert effective_quota(False, GB, 5 * GB) == (GB, SOURCE_USER)
    assert effective_quota(False, UNLIMITED, GB) == (None, SOURCE_USER)
    assert effective_quota(False, None, 2 * GB) == (2 * GB, SOURCE_DEFAULT)
    assert effective_quota(False, None, None) == (None, SOURCE_DEFAULT)


def test_used_bytes_counts_only_files_still_there():
    sizes = {'a': 10, 'b': 20}
    assert used_bytes({'a', 'b', 'gone'}, sizes) == 30
    assert used_bytes(set(), sizes) == 0


def test_quota_status_and_message():
    status = quota_status(GB + GB // 2, 2 * GB, SOURCE_DEFAULT)
    assert status['remaining'] == GB // 2
    assert status['exceeded'] is False
    assert status['unlimited'] is False

    full = quota_status(3 * GB, 2 * GB, SOURCE_USER, 2 * GB)
    assert full['remaining'] == 0
    assert full['exceeded'] is True
    assert full['own'] == 2 * GB
    message = exceeded_message(full)
    assert '3.0 GB of 2.0 GB used' in message
    assert '0 B left' in message

    free = quota_status(5, None, SOURCE_ADMIN)
    assert free['limit'] is None
    assert free['remaining'] is None
    assert free['unlimited'] is True
    assert free['exceeded'] is False


def test_format_bytes_matches_the_web_app():
    assert format_bytes(0) == '0 B'
    assert format_bytes(1536) == '1.5 KB'
    assert format_bytes(200 * MB) == '200 MB'


# ── Store ────────────────────────────────────────────────────────────


def test_store_keeps_own_quotas_and_the_default(tmp_path):
    store = StorageQuotas(tmp_path / 'lib.db')
    assert store.default() is None
    assert store.any_set() is False
    assert store.get(5) is None

    assert store.set_default(2 * GB) == 2 * GB
    assert store.default() == 2 * GB
    assert store.set(5, GB) == GB
    assert store.set(7, UNLIMITED) == UNLIMITED
    assert store.any_set() is True
    assert store.all() == {5: GB, 7: UNLIMITED}

    # Back to the default; the default cleared with -1 or None.
    assert store.set(5, None) is None
    assert store.get(5) is None
    store.set_default(UNLIMITED)
    assert store.default() is None

    store.remove_user(7)
    assert store.all() == {}
    with pytest.raises(QuotaError):
        store.set(0, GB)


# ── Usage and refusal ────────────────────────────────────────────────


@pytest.fixture
def quota_state(tmp_path, monkeypatch):
    """Accounts 1 (admin), 2 and 3 (users); 2 owns 600 MB of files."""

    users = UserStore(tmp_path / 'auth.db')
    users.create('boss', 'password1', 'admin')
    users.create('ana', 'password1', 'user')
    users.create('bia', 'password1', 'user')
    auth = MagicMock()
    auth.auth_disabled = False
    auth.users = users
    owners = TrackOwners(tmp_path / 'lib.db')
    owners.add('key-a', 2, 'A.mp3')
    owners.add('key-b', 2, 'B.mp3')
    quotas = StorageQuotas(tmp_path / 'lib.db')
    monkeypatch.setattr(api.state, 'auth', auth)
    monkeypatch.setattr(api.state, 'track_owners', owners)
    monkeypatch.setattr(api.state, 'storage_quotas', quotas)
    monkeypatch.setattr(api.state, 'library_sync', None)
    monkeypatch.setattr(
        api,
        'library_live_sizes',
        lambda: {'key-a': 400 * MB, 'key-b': 200 * MB, 'key-c': MB},
    )
    return quotas


def _request(user_id: int, role: str = 'user') -> Request:
    principal = Principal('session', 'user', '', user_id, f'u{user_id}', role)
    return Request({
        'type': 'http',
        'headers': [],
        'state': {'principal': principal},
    })


def test_usage_is_what_the_account_downloaded(quota_state):
    status = api.storage_status(2)
    assert status['used'] == 600 * MB
    assert status['unlimited'] is True
    assert api.storage_status(3)['used'] == 0


def test_no_quota_never_refuses(quota_state):
    assert api.storage_quota_refusal([2, 3]) is None
    assert api.storage_quota_refusal([]) is None


def test_default_quota_refuses_who_is_out_of_space(quota_state):
    quota_state.set_default(500 * MB)

    message = api.storage_quota_refusal([2])
    assert message
    assert 'Storage quota reached' in message
    # Someone else waiting on the same song still has room.
    assert api.storage_quota_refusal([2, 3]) is None
    # Admins are never limited.
    assert api.storage_quota_refusal([1]) is None
    assert api.storage_status(1)['source'] == SOURCE_ADMIN


def test_own_quota_beats_the_default(quota_state):
    quota_state.set_default(500 * MB)
    quota_state.set(2, UNLIMITED)
    assert api.storage_quota_refusal([2]) is None
    quota_state.set(2, GB)
    status = api.storage_status(2)
    assert status['remaining'] == GB - 600 * MB
    assert status['source'] == SOURCE_USER


def test_ensure_storage_quota_answers_507(quota_state):
    quota_state.set(2, 100 * MB)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(api.ensure_storage_quota(_request(2)))
    assert caught.value.status_code == QUOTA_STATUS_CODE
    assert '100 MB' in caught.value.detail
    asyncio.run(api.ensure_storage_quota(_request(3)))
    asyncio.run(api.ensure_storage_quota(_request(1, 'admin')))


def test_a_queued_download_is_refused_when_it_starts(quota_state):
    quota_state.set(2, 100 * MB)
    downloader = MagicMock()
    downloader.overwrite_existing_files = True
    downloader.download = MagicMock(side_effect=AssertionError('no'))
    song = {'name': 'Track', 'artists': ['Artist'], 'song_id': 'quota-1'}
    loop = asyncio.new_event_loop()
    prev = (api.state.downloader, api.state.loop, api.state.connections)
    try:
        api.state.downloader = downloader
        api.state.loop = loop
        api.state.connections = MagicMock()
        api.state.connections.broadcast = AsyncMock()
        api.state.connections.broadcast_job = AsyncMock()
        song_id = api._register_job(song, status='queued', user_id=2)
        with pytest.raises(QuotaExceededError) as caught:
            loop.run_until_complete(
                api._run_download(song, song_id, user_id=2)
            )
        assert 'Storage quota reached' in str(caught.value)
        job = api.state.download_jobs[song_id]
        assert job['status'] == 'error'
        assert 'Storage quota reached' in job['message']
        downloader.download.assert_not_called()
    finally:
        loop.close()
        api.state.download_jobs.clear()
        api.state.downloader, api.state.loop, api.state.connections = prev


# ── Routes ───────────────────────────────────────────────────────────


def test_my_storage_route(quota_state):
    quota_state.set_default(GB)
    status = storage_quota_routes.my_storage(_request(2))
    assert status['used'] == 600 * MB
    assert status['limit'] == GB
    with pytest.raises(HTTPException):
        storage_quota_routes.my_storage(Request({'type': 'http'}))


def _json_request(body: Any, user_id: int = 1) -> Request:
    payload = json.dumps(body).encode()

    async def receive() -> dict[str, Any]:
        return {'type': 'http.request', 'body': payload}

    principal = Principal('session', 'user', '', user_id, 'boss', 'admin')
    return Request(
        {
            'type': 'http',
            'method': 'PUT',
            'headers': [],
            'state': {'principal': principal},
        },
        receive,
    )


def test_admin_routes_set_and_reset(quota_state, monkeypatch):
    monkeypatch.setattr(api, 'log_activity', AsyncMock())

    everyone = asyncio.run(
        storage_quota_routes.set_default_quota(
            _json_request({'quota_bytes': GB})
        )
    )
    assert everyone['default'] == GB
    by_id = {row['id']: row for row in everyone['users']}
    assert by_id[1]['unlimited'] is True
    assert by_id[2]['limit'] == GB
    assert by_id[2]['used'] == 600 * MB

    status = asyncio.run(
        storage_quota_routes.set_user_quota(
            3, _json_request({'quota_bytes': -1})
        )
    )
    assert status['unlimited'] is True
    assert status['own'] == UNLIMITED

    with pytest.raises(HTTPException) as bad:
        asyncio.run(
            storage_quota_routes.set_user_quota(
                3, _json_request({'quota_bytes': 0})
            )
        )
    assert bad.value.status_code == 400
    with pytest.raises(HTTPException) as missing:
        asyncio.run(
            storage_quota_routes.set_user_quota(
                99, _json_request({'quota_bytes': GB})
            )
        )
    assert missing.value.status_code == 404

    reset = asyncio.run(
        storage_quota_routes.reset_user_usage(2, _json_request({}))
    )
    assert reset['used'] == 0
    assert api.state.track_owners.owned_keys(2) == set()


def test_reset_pokes_the_apps_feed(quota_state, tmp_path, monkeypatch):
    sync = MagicMock(spec=LibrarySync)
    monkeypatch.setattr(api.state, 'library_sync', sync)
    assert storage_quota_routes._reset_usage(2) == 2
    touched = sorted(call.args[0] for call in sync.touch.call_args_list)
    assert touched == ['A.mp3', 'B.mp3']


@pytest.mark.parametrize(
    ('method', 'path', 'scope'),
    [
        ('GET', '/api/me/storage', CLIENT),
        ('GET', '/api/users/storage', ADMIN),
        ('PUT', '/api/users/storage/default', ADMIN),
        ('PUT', '/api/users/4/storage', ADMIN),
        ('POST', '/api/users/4/storage/reset', ADMIN),
    ],
)
def test_who_may_call_what(method, path, scope):
    assert classify(method, path) == scope
