import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from downtify import api, mobile_routes
from downtify.library_catalog import (
    LibraryContext,
    entry_content_key,
    list_library_entries,
)
from downtify.library_visibility import LibraryVisibility
from tests.test_mobile import _library, _make_mp3, _needs_ffmpeg

pytest_plugins = ('tests.test_mobile',)


def _request(user_id=2, admin=False):
    request = Request({'type': 'http', 'headers': [], 'query_string': b''})
    request.scope['state'] = {
        'principal': SimpleNamespace(
            kind='session',
            user_id=user_id,
            is_admin=admin,
            scope='user',
            device_id='',
            username='owner',
            role='user',
        )
    }
    return request


def test_track_path_rejects_hidden_track_for_owner_and_editor(monkeypatch):
    row = {'file': 'hidden.mp3'}
    monkeypatch.setattr(
        mobile_routes,
        '_sync',
        lambda: SimpleNamespace(row_for=lambda track_id: row),
    )
    monkeypatch.setattr(api, 'filter_paths_for_request', lambda paths, req: [])
    monkeypatch.setattr(api, 'library_context', SimpleNamespace)

    for user_id in (2, 3):
        with pytest.raises(HTTPException) as error:
            mobile_routes._track_path('track-id', _request(user_id))
        assert error.value.status_code == 404


def test_admin_can_resolve_hidden_track(monkeypatch, tmp_path):
    audio = tmp_path / 'hidden.mp3'
    audio.write_bytes(b'audio')
    row = {'file': 'hidden.mp3'}
    monkeypatch.setattr(
        mobile_routes,
        '_sync',
        lambda: SimpleNamespace(row_for=lambda track_id: row),
    )
    monkeypatch.setattr(
        api, 'filter_paths_for_request', lambda paths, req: paths
    )
    monkeypatch.setattr(
        api, 'library_context', lambda: LibraryContext(download_dir=tmp_path)
    )
    assert mobile_routes._track_path('track-id', _request(1, True)) == (
        row,
        audio,
    )


@pytest.mark.parametrize(
    ('role', 'visible'), [('admin', True), ('user', False)]
)
def test_signed_track_visibility_uses_device_owner_role(
    monkeypatch, tmp_path, role, visible
):
    audio = tmp_path / 'hidden.mp3'
    audio.write_bytes(b'audio')
    row = {'file': 'hidden.mp3'}
    device = {'user_id': 7, 'username': 'paired', 'revoked_at': None}
    users = SimpleNamespace(
        get=lambda user_id: {
            'username': 'paired',
            'role': role,
        }
    )
    auth = SimpleNamespace(get_device=lambda device_id: device, users=users)
    monkeypatch.setattr(api.state, 'auth', auth)
    monkeypatch.setattr(
        mobile_routes,
        '_sync',
        lambda: SimpleNamespace(row_for=lambda track_id: row),
    )
    monkeypatch.setattr(
        api, 'library_context', lambda: LibraryContext(download_dir=tmp_path)
    )
    seen = []

    def visible_paths(paths, req):
        principal = api.principal_of(req)
        seen.append(principal)
        return paths if principal.is_admin else []

    monkeypatch.setattr(api, 'filter_paths_for_request', visible_paths)
    request = _request()
    request.scope['state']['principal'] = mobile_routes.Principal(
        'signed', 'client', 'device-id'
    )
    if visible:
        assert mobile_routes._track_path('track-id', request) == (row, audio)
    else:
        with pytest.raises(HTTPException) as error:
            mobile_routes._track_path('track-id', request)
        assert error.value.status_code == 404
    assert seen[0].user_id == 7
    assert seen[0].is_admin is (role == 'admin')
    assert (
        mobile_routes.Principal('signed', 'client', 'device-id').user_id == 0
    )


def test_playlist_mutation_result_filters_order_duplicates_and_count(
    monkeypatch,
):
    request = _request()
    calls = []

    def visible(paths, req):
        calls.append((paths.copy(), req))
        return [path for path in paths if path != 'hidden.mp3']

    monkeypatch.setattr(api, 'filter_paths_for_request', visible)

    async def inline(function, *args):
        return function(*args)

    monkeypatch.setattr(mobile_routes.asyncio, 'to_thread', inline)
    monkeypatch.setattr(
        mobile_routes,
        '_sync',
        lambda: SimpleNamespace(
            ids_for_paths=lambda paths: {
                p: p.removesuffix('.mp3') for p in paths
            }
        ),
    )
    result = asyncio.run(
        mobile_routes._mobile_playlist_result(
            {
                'name': 'Mix',
                'files': ['b.mp3', 'hidden.mp3', 'b.mp3', 'a.mp3'],
                'added': 2,
                'removed': 1,
                'already': ['a.mp3', 'hidden.mp3', 'a.mp3'],
            },
            request,
        )
    )

    assert result == {
        'name': 'Mix',
        'manual': False,
        'count': 3,
        'track_ids': ['b', 'b', 'a'],
        'added': 2,
        'removed': 1,
        'already': ['a', 'a'],
    }
    assert all(seen_request is request for _, seen_request in calls)


@_needs_ffmpeg
def test_hidden_track_http_visibility_and_playlist_results(  # noqa: PLR0914
    client, app_dirs, monkeypatch
):
    downloads, data = app_dirs
    monkeypatch.setattr(
        api.state,
        'library_visibility',
        LibraryVisibility(data / 'visibility-test.db'),
    )
    _make_mp3(downloads / 'Visible.mp3')
    _make_mp3(downloads / 'Hidden.mp3')
    tracks = _library(client)['tracks']
    by_file = {Path(row['file']).name: row for row in tracks}
    visible, hidden = by_file['Visible.mp3'], by_file['Hidden.mp3']

    auth = api.state.auth
    owner = auth.users.create('hidden-owner', 'correct horse battery')
    editor = auth.users.create('hidden-editor', 'correct horse battery')
    _owner_device, owner_token = auth.create_device(
        'owner-phone', user_id=owner['id']
    )
    _editor_device, editor_token = auth.create_device(
        'editor-phone', user_id=editor['id']
    )
    owner_headers = {'Authorization': f'Bearer {owner_token}'}
    editor_headers = {'Authorization': f'Bearer {editor_token}'}

    created = client.post(
        '/api/v1/playlists',
        json={'name': 'Visibility mix'},
        headers=owner_headers,
    )
    assert created.status_code == 200
    added = client.post(
        '/api/v1/playlists/tracks',
        json={'name': 'Visibility mix', 'add': [visible['id'], hidden['id']]},
        headers=owner_headers,
    )
    assert added.status_code == 200
    api.state.playlist_shares.set_visibility(
        'Visibility mix', 'shared', [editor['id']], editors=[editor['id']]
    )

    row = next(
        item
        for item in list_library_entries(api.library_context())
        if item.get('file', '').endswith('Hidden.mp3')
    )
    api.state.library_visibility.hide(
        'track', entry_content_key(row), path=row['file']
    )

    listing = client.get('/api/v1/playlists', headers=editor_headers)
    assert listing.status_code == 200
    playlist = next(p for p in listing.json() if p['name'] == 'Visibility mix')
    assert playlist['track_ids'] == [visible['id']]
    assert playlist['count'] == 1

    edited = client.post(
        '/api/v1/playlists/tracks',
        json={'name': 'Visibility mix', 'remove': [visible['id']]},
        headers=editor_headers,
    )
    assert edited.status_code == 200
    assert edited.json()['count'] == 0
    assert edited.json()['track_ids'] == []
    reordered = client.put(
        '/api/v1/playlists/order',
        json={'name': 'Visibility mix', 'track_ids': []},
        headers=editor_headers,
    )
    assert reordered.status_code == 200
    assert reordered.json()['count'] == 0
    assert reordered.json()['track_ids'] == []
    admin_listing = client.get('/api/v1/playlists').json()
    playlist = next(p for p in admin_listing if p['name'] == 'Visibility mix')
    assert playlist['track_ids'] == [hidden['id']]

    assert (
        client.get(
            f'/api/v1/tracks/{hidden["id"]}', headers=editor_headers
        ).status_code
        == 404
    )
    assert (
        client.get(
            f'/api/v1/tracks/{hidden["id"]}/stream', headers=editor_headers
        ).status_code
        == 404
    )
    assert (
        client.get(
            f'/api/v1/tracks/{hidden["id"]}',
        ).status_code
        == 200
    )

    signed_user = client.post(
        '/api/v1/sign',
        json={
            'items': [{'path': f'/api/v1/tracks/{hidden["id"]}', 'params': {}}]
        },
        headers=owner_headers,
    )
    assert signed_user.status_code == 200
    client.cookies.clear()
    assert client.get(signed_user.json()['urls'][0]).status_code == 404
    _admin_device, admin_token = auth.create_device('admin-phone', user_id=1)
    signed_admin = client.post(
        '/api/v1/sign',
        json={
            'items': [{'path': f'/api/v1/tracks/{hidden["id"]}', 'params': {}}]
        },
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert signed_admin.status_code == 200
    assert client.get(signed_admin.json()['urls'][0]).status_code == 200
