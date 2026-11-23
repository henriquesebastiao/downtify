"""Downloaded playlists in the Library with *Write M3U playlists* off.

The Library lists playlists from their M3U files; with none written the
playlist catalog is the source instead (issue #412). Offline.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest
from starlette.requests import Request

from downtify import api
from downtify.auth import Principal
from downtify.library_catalog import LibraryContext
from downtify.library_paths_cache import invalidate_library_paths_cache
from downtify.playlist_catalog import ManualPlaylistOwners, PlaylistCatalog
from downtify.playlist_shares import PlaylistShares
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


def _m3u_row(name: str, files: list[str], **extra: Any) -> dict[str, Any]:
    return {
        'name': name,
        'files': files,
        'count': len(files),
        'added': 1,
        'cover': '',
        'liked': False,
        'manual': False,
        **extra,
    }


def _song(track_id: str) -> dict[str, Any]:
    return {
        'song_id': track_id,
        'url': f'https://open.spotify.com/track/{track_id}',
    }


@pytest.fixture
def world(tmp_path, monkeypatch):
    db = tmp_path / 'lib.db'
    users = UserStore(db)
    users.create('admin', 'password-1', 'admin')
    users.create('ana', 'password-2')
    users.create('bob', 'password-3')
    root = tmp_path / 'downloads'
    root.mkdir()
    catalog = PlaylistCatalog(db)
    found: list[dict[str, Any]] = []
    monkeypatch.setattr(
        api, 'library_context', lambda: LibraryContext(download_dir=root)
    )
    monkeypatch.setattr(api, 'list_library_playlists', lambda *a, **k: found)
    monkeypatch.setattr(api, 'peek_cached_path_pairs', lambda _ctx: None)
    monkeypatch.setattr(api.state, 'auth', SimpleNamespace(users=users))
    monkeypatch.setattr(api.state, 'playlist_catalog', catalog)
    monkeypatch.setattr(
        api.state, 'manual_playlist_owners', ManualPlaylistOwners(db)
    )
    monkeypatch.setattr(api.state, 'playlist_shares', PlaylistShares(db))
    monkeypatch.setattr(api.state, 'likes', None)
    monkeypatch.setitem(api.state.settings, 'generate_m3u', False)
    invalidate_library_paths_cache()

    def add(playlist: str, files: list[str], owner: int = ANA) -> None:
        catalog.ensure_playlist(playlist, spotify_id='sp', user_id=owner)
        for order, name in reversed(list(enumerate(files))):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
            catalog.upsert_track(
                playlist,
                _song(f'{order:022d}'),
                name,
                path,
                track_order=order,
            )

    yield SimpleNamespace(add=add, found=found, catalog=catalog, root=root)
    invalidate_library_paths_cache()


def _rows(request: Request) -> dict[str, dict[str, Any]]:
    return {p['name']: p for p in api.playlists_for_request(request)}


def test_catalog_lists_a_playlist_downloaded_without_an_m3u(world):
    world.add('Road', ['b/Two.mp3', 'a/One.mp3', 'c/Three.mp3'])

    road = _rows(_request(ANA))['Road']
    assert road['files'] == ['b/Two.mp3', 'a/One.mp3', 'c/Three.mp3']
    assert road['count'] == 3
    assert road['manual'] is False
    # Still private to its owner (and admins).
    assert 'Road' not in _rows(_request(BO))
    assert 'Road' in _rows(_request(ADMIN_ID, 'admin'))
    # The playlist page and its songs open through the same entry.
    entry = api.playlist_entry_for_request('Road', _request(ANA))
    assert entry is not None
    assert entry['files'] == road['files']


def test_catalog_replaces_the_songs_of_an_m3u_written_before(world):
    # Written while M3U files were on, then never updated.
    world.found.append(
        _m3u_row('Road', ['a/One.mp3'], cover='Road.jpg', added=42)
    )
    world.add('Road', ['a/One.mp3', 'b/Two.mp3'])

    rows = [p for p in api.playlists_for_request(_request(ANA))]
    assert [p['name'] for p in rows] == ['Road']
    assert rows[0]['files'] == ['a/One.mp3', 'b/Two.mp3']
    assert rows[0]['count'] == 2
    assert rows[0]['cover'] == 'Road.jpg'
    assert rows[0]['added'] == 42


def test_catalog_matches_the_m3u_named_after_the_sanitized_name(world):
    world.found.append(_m3u_row('ACDC Hits', ['a/One.mp3']))
    world.add('AC/DC Hits', ['a/One.mp3', 'b/Two.mp3'])

    rows = api.playlists_for_request(_request(ADMIN_ID, 'admin'))
    assert [(p['name'], p['count']) for p in rows] == [('ACDC Hits', 2)]


def test_library_playlists_keep_their_own_m3u(world):
    world.found.append(_m3u_row('Mix', ['a/One.mp3'], manual=True))
    world.add('Mix', ['a/One.mp3', 'b/Two.mp3'])

    rows = api.playlists_for_request(_request(ADMIN_ID, 'admin'))
    assert [(p['name'], p['count']) for p in rows] == [('Mix', 1)]


def test_songs_no_longer_on_disk_are_left_out(world, monkeypatch):
    world.add('Road', ['a/One.mp3', 'b/Two.mp3'])
    world.add('Gone', ['c/Three.mp3'])
    monkeypatch.setattr(
        api,
        'peek_cached_path_pairs',
        lambda _ctx: [('a/One.mp3', world.root / 'a/One.mp3')],
    )

    rows = _rows(_request(ADMIN_ID, 'admin'))
    assert rows['Road']['files'] == ['a/One.mp3']
    assert 'Gone' not in rows


def test_with_m3u_files_on_the_listing_is_the_m3u_files(world, monkeypatch):
    monkeypatch.setitem(api.state.settings, 'generate_m3u', True)
    world.found.append(_m3u_row('Road', ['a/One.mp3']))
    world.add('Road', ['a/One.mp3', 'b/Two.mp3'])
    world.add('Other', ['c/Three.mp3'])

    rows = api.playlists_for_request(_request(ADMIN_ID, 'admin'))
    assert [(p['name'], p['count']) for p in rows] == [('Road', 1)]
