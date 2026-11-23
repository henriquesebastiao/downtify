"""Per-user libraries (issue #620): with the setting on, a user sees the
songs they downloaded and those of the playlists they may open. Offline."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest
from starlette.requests import Request

from downtify import api
from downtify.auth import Principal
from downtify.library_catalog import LibraryContext, entry_content_key
from downtify.library_paths_cache import invalidate_library_paths_cache
from downtify.playlist_catalog import ManualPlaylistOwners, PlaylistCatalog
from downtify.playlist_shares import SHARED, PlaylistShares
from downtify.track_owners import TrackOwners
from downtify.users import UserStore

ADMIN_ID = 1
ANA = 2
BO = 3


def _request(user_id: int, role: str = 'user') -> Request:
    scope: dict[str, Any] = {
        'type': 'http',
        'headers': [],
        'query_string': b'',
        'state': {
            'principal': Principal(
                'device', 'client', '', user_id, f'u{user_id}', role
            )
        },
    }
    raw = json.dumps(None).encode()

    async def receive() -> dict[str, Any]:
        return {'type': 'http.request', 'body': raw, 'more_body': False}

    return Request(scope, receive)


def _entry(file: str) -> dict[str, Any]:
    return {
        'file': file,
        'title': file.rsplit('/', maxsplit=1)[-1].removesuffix('.mp3'),
        'artist': 'Mica Ferreira',
        'album': 'Driftlight',
        'size': len(file) * 1000,
    }


ENTRIES = [
    _entry('Mica/Ana One.mp3'),
    _entry('Mica/Ana Two.mp3'),
    _entry('Mica/Bo One.mp3'),
    _entry('Mica/Nobody.mp3'),
]


@pytest.fixture
def world(tmp_path, monkeypatch):
    db = tmp_path / 'lib.db'
    users = UserStore(db)
    users.create('admin', 'password-1', 'admin')
    users.create('ana', 'password-2')
    users.create('bob', 'password-3')
    owners = TrackOwners(db)
    for entry, user in zip(ENTRIES[:3], (ANA, ANA, BO)):
        owners.add(entry_content_key(entry), user, entry['file'])
    manual = ManualPlaylistOwners(db)
    manual.set_owner('Bo Mix', BO)
    shares = PlaylistShares(db)
    found = [
        {
            'name': 'Bo Mix',
            'files': ['Mica/Bo One.mp3'],
            'count': 1,
            'added': 1,
            'cover': '',
            'liked': False,
            'manual': True,
        }
    ]
    root = tmp_path / 'downloads'
    root.mkdir()
    monkeypatch.setattr(
        api, 'library_context', lambda: LibraryContext(download_dir=root)
    )
    monkeypatch.setattr(api, 'listing_for_request', lambda *_a, **_k: ENTRIES)
    monkeypatch.setattr(api, 'list_library_playlists', lambda *a, **k: found)
    monkeypatch.setattr(api, 'hidden_rules', lambda: None)
    monkeypatch.setattr(api.state, 'auth', SimpleNamespace(users=users))
    monkeypatch.setattr(api.state, 'track_owners', owners)
    monkeypatch.setattr(api.state, 'playlist_catalog', PlaylistCatalog(db))
    monkeypatch.setattr(api.state, 'manual_playlist_owners', manual)
    monkeypatch.setattr(api.state, 'playlist_shares', shares)
    monkeypatch.setattr(api.state, 'likes', None)
    monkeypatch.setitem(api.state.settings, 'allow_playlist_sharing', True)
    monkeypatch.setitem(api.state.settings, 'per_user_library', True)
    invalidate_library_paths_cache()
    yield SimpleNamespace(shares=shares)
    invalidate_library_paths_cache()


def _files(request: Request) -> list[str]:
    return [entry['file'] for entry in api.entries_for_request(request)]


def _allowed_files(request: Request) -> set[str]:
    allowed = api.allowed_entry_keys(request)
    assert allowed is not None
    return {e['file'] for e in ENTRIES if entry_content_key(e) in allowed}


def test_a_user_sees_only_the_songs_they_downloaded(world):
    assert _files(_request(ANA)) == ['Mica/Ana One.mp3', 'Mica/Ana Two.mp3']
    assert _allowed_files(_request(ANA)) == {
        'Mica/Ana One.mp3',
        'Mica/Ana Two.mp3',
    }
    assert _files(_request(BO)) == ['Mica/Bo One.mp3']


def test_a_playlist_shared_with_them_brings_its_songs(world):
    world.shares.set_visibility('Bo Mix', SHARED, [ANA])
    assert 'Mica/Bo One.mp3' in _files(_request(ANA))
    assert 'Mica/Bo One.mp3' in _allowed_files(_request(ANA))


def test_admins_still_see_everything(world):
    assert api.allowed_entry_keys(_request(ADMIN_ID, 'admin')) is None
    assert len(_files(_request(ADMIN_ID, 'admin'))) == len(ENTRIES)


def test_the_shared_library_is_unchanged_with_the_setting_off(
    world, monkeypatch
):
    monkeypatch.setitem(api.state.settings, 'per_user_library', False)
    assert api.allowed_entry_keys(_request(ANA)) is None
    assert len(_files(_request(ANA))) == len(ENTRIES)


def test_the_library_is_shared_by_default():
    assert api.DEFAULT_SETTINGS['per_user_library'] is False
