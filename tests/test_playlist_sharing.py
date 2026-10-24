"""Sharing playlists view-only, and detaching an imported playlist. Offline.

A playlist is private to its owner (and admins) until the owner shares it
with named users or makes it public; viewers play, follow and copy, never
edit. See ``downtify/playlist_shares.py``.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from downtify import api, mobile_routes
from downtify.auth import USER, Principal, classify
from downtify.library_catalog import LibraryContext
from downtify.library_paths_cache import invalidate_library_paths_cache
from downtify.m3u import MANUAL_M3U_MARKER, is_manual_m3u
from downtify.manual_playlists import (
    ManualPlaylistError,
    copy_playlist,
    detach_imported_playlist,
)
from downtify.monitor import PlaylistMonitorDB
from downtify.playlist_catalog import ManualPlaylistOwners, PlaylistCatalog
from downtify.playlist_shares import (
    PRIVATE,
    PUBLIC,
    SHARED,
    PlaylistShares,
)
from downtify.users import UserStore

ADMIN_ID = 1
ANA = 2
BO = 3
CY = 4


def _request(
    user_id: int, role: str = 'user', body: Any = None, query: bytes = b''
) -> Request:
    scope: dict[str, Any] = {
        'type': 'http',
        'headers': [],
        'query_string': query,
    }
    scope['state'] = {
        'principal': Principal(
            'device', 'client', '', user_id, f'u{user_id}', role
        )
    }
    raw = json.dumps(body).encode() if body is not None else b''

    async def receive() -> dict[str, Any]:
        return {'type': 'http.request', 'body': raw, 'more_body': False}

    return Request(scope, receive)


def _admin(body: Any = None) -> Request:
    return _request(ADMIN_ID, 'admin', body)


def _row(name: str, manual: bool = False, files=('a.mp3',)) -> dict[str, Any]:
    return {
        'name': name,
        'files': list(files),
        'count': len(files),
        'added': 1,
        'cover': '',
        'liked': False,
        'manual': manual,
    }


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Four accounts and three playlists: Ana's imported "Road", Ana's
    own "Mix" and Bo's "Chill"."""

    db = tmp_path / 'lib.db'
    users = UserStore(db)
    users.create('admin', 'password-1', 'admin')
    users.create('ana', 'password-2')
    users.create('bob', 'password-3')
    users.create('cyd', 'password-4')
    catalog = PlaylistCatalog(db)
    catalog.ensure_playlist('Road', spotify_id='sp1', user_id=ANA)
    manual = ManualPlaylistOwners(db)
    manual.set_owner('Mix', ANA)
    manual.set_owner('Chill', BO)
    shares = PlaylistShares(db)
    root = tmp_path / 'downloads'
    root.mkdir()
    ctx = LibraryContext(download_dir=root)
    found = [_row('Road'), _row('Mix', True), _row('Chill', True)]
    monkeypatch.setattr(api, 'library_context', lambda: ctx)
    monkeypatch.setattr(api, 'list_library_playlists', lambda *a, **k: found)
    monkeypatch.setattr(api.state, 'auth', SimpleNamespace(users=users))
    monkeypatch.setattr(api.state, 'playlist_catalog', catalog)
    monkeypatch.setattr(api.state, 'manual_playlist_owners', manual)
    monkeypatch.setattr(api.state, 'playlist_shares', shares)
    monkeypatch.setattr(api.state, 'likes', None)
    monkeypatch.setitem(api.state.settings, 'allow_playlist_sharing', True)
    invalidate_library_paths_cache()
    yield SimpleNamespace(
        ctx=ctx,
        shares=shares,
        users=users,
        catalog=catalog,
        manual=manual,
        found=found,
    )
    invalidate_library_paths_cache()


def _names(request: Request) -> list[str]:
    return [p['name'] for p in api.playlists_for_request(request)]


def _share(request: Request) -> dict[str, Any]:
    return asyncio.run(api.set_playlist_visibility_endpoint(request))


def test_imported_playlist_display_name_preserves_identity_and_sharing(world):
    world.shares.set_visibility('Road', SHARED, [BO])
    result = asyncio.run(
        api.rename_library_playlist_endpoint(
            _request(ANA, body={'name': 'Road', 'new_name': 'My road trip'})
        )
    )
    assert result['name'] == 'Road'
    assert result['display_name'] == 'My road trip'
    assert world.catalog.spotify_id_for_playlist('Road') == 'sp1'
    assert world.shares.visibility('Road') == SHARED
    shared = next(
        row
        for row in api.playlists_for_request(_request(BO))
        if row['name'] == 'Road'
    )
    assert shared['display_name'] == 'My road trip'
    assert api.playlist_display_identity({'name': 'Road'}) == 'source:sp1'


def test_imported_display_name_reset_and_owner_only(world):
    world.shares.set_visibility('Road', PUBLIC)
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            api.rename_library_playlist_endpoint(
                _request(BO, body={'name': 'Road', 'new_name': 'No'})
            )
        )
    assert error.value.status_code == 403
    asyncio.run(
        api.rename_library_playlist_endpoint(
            _request(ANA, body={'name': 'Road', 'new_name': 'Alias'})
        )
    )
    result = asyncio.run(
        api.rename_library_playlist_endpoint(
            _request(ANA, body={'name': 'Road', 'reset_display_name': True})
        )
    )
    assert result['display_name'] == 'Road'
    assert world.shares.display_names() == {}


def test_favorites_are_personal_persistent_and_do_not_grant_access(world):
    payload = {'name': 'Mix', 'favorite': True}
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            api.set_playlist_favorite_endpoint(_request(BO, body=payload))
        )
    assert error.value.status_code == 404
    asyncio.run(
        api.set_playlist_favorite_endpoint(_request(ANA, body=payload))
    )
    rows = api.playlists_for_request(_request(ANA))
    assert rows[0]['name'] == 'Mix'
    assert rows[0]['favorite'] is True
    assert not any(
        p.get('favorite') for p in api.playlists_for_request(_request(BO))
    )
    reopened = PlaylistShares(Path(world.shares._path))
    assert reopened.favorites(ANA) == frozenset({'mix'})


def test_favorites_follow_rename_and_are_cleaned_on_delete(world):
    world.shares.set_favorite(ANA, 'Mix', True)
    world.shares.rename('Mix', 'Renamed')
    assert world.shares.favorites(ANA) == frozenset({'renamed'})
    world.shares.forget('Renamed')
    assert world.shares.favorites(ANA) == frozenset()
    world.shares.set_favorite(ANA, 'Mix', True)
    world.shares.remove_user(ANA)
    assert not world.shares.favorites(ANA)


def test_imported_favorite_keeps_the_source_identity(world):
    asyncio.run(
        api.set_playlist_favorite_endpoint(
            _request(ANA, body={'name': 'Road', 'favorite': True})
        )
    )
    world.catalog.ensure_playlist(
        'New source title', spotify_id='sp1', user_id=ANA
    )
    world.found[0] = _row('New source title')
    renamed = next(
        p
        for p in api.playlists_for_request(_request(ANA))
        if p['name'] == 'New source title'
    )
    assert renamed['favorite']
    world.catalog.ensure_playlist(
        'Different source', spotify_id='SP1', user_id=ANA
    )
    assert api.playlist_favorite_identity({
        'name': 'Different source'
    }) != api.playlist_favorite_identity({'name': 'New source title'})


def test_revoked_playlist_favorite_is_not_disclosed(world):
    world.shares.set_visibility('Mix', SHARED, [BO])
    world.shares.set_favorite(BO, 'Mix', True)
    assert next(
        p
        for p in api.playlists_for_request(_request(BO))
        if p['name'] == 'Mix'
    )['favorite']
    world.shares.set_visibility('Mix', PRIVATE)
    assert 'Mix' not in _names(_request(BO))
    result = asyncio.run(
        api.set_playlist_favorite_endpoint(
            _request(BO, body={'name': 'Mix', 'favorite': False})
        )
    )
    assert result['favorite'] is False


def test_source_cover_cannot_edit_someone_elses_playlist(world, monkeypatch):
    monkeypatch.setattr(
        api,
        '_download_playlist_cover_for_batch',
        lambda *a: pytest.fail('network'),
    )
    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            api.edit_library_playlist_tracks_endpoint(
                _request(
                    BO,
                    body={
                        'name': 'Mix',
                        'source_playlist_url': 'https://deezer.com/playlist/333',
                    },
                )
            )
        )
    # A private playlist is deliberately hidden, even from other users.
    assert caught.value.status_code == 404


# ── the store ────────────────────────────────────────────────────────


def test_visibility_defaults_to_private(world):
    assert world.shares.visibility('Mix') == PRIVATE
    assert world.shares.view_for(BO).public == frozenset()


def test_shared_playlists_reach_only_the_listed_users(world):
    world.shares.set_visibility('Mix', SHARED, [BO])

    assert world.shares.view_for(BO).to_me == {'mix': False}
    assert world.shares.view_for(CY).to_me == {}
    assert world.shares.visibility('mix') == SHARED


def test_a_user_keeps_their_seen_marker_when_the_list_changes(world):
    world.shares.set_visibility('Mix', SHARED, [BO])
    world.shares.mark_seen('Mix', BO)
    world.shares.set_visibility('Mix', SHARED, [BO, CY])

    assert world.shares.view_for(BO).to_me == {'mix': True}
    assert world.shares.view_for(CY).to_me == {'mix': False}


def test_following_ends_when_a_playlist_stops_being_public(world):
    world.shares.set_visibility('Mix', PUBLIC)
    world.shares.follow(BO, 'Mix')
    assert world.shares.view_for(BO).followed == {'mix'}

    world.shares.set_visibility('Mix', SHARED, [CY])
    assert world.shares.view_for(BO).followed == frozenset()
    world.shares.set_visibility('Mix', PUBLIC)
    assert world.shares.view_for(BO).followed == frozenset()


def test_sharing_follows_a_rename_and_goes_with_a_delete(world):
    world.shares.set_visibility('Mix', PUBLIC)
    world.shares.follow(BO, 'Mix')
    world.shares.rename('Mix', 'Mix 2')

    assert world.shares.visibility('Mix 2') == PUBLIC
    assert world.shares.view_for(BO).followed == {'mix 2'}
    world.shares.forget('Mix 2')
    assert world.shares.visibility('Mix 2') == PRIVATE
    assert world.shares.view_for(BO).followed == frozenset()


def test_deleting_an_account_drops_its_follows_and_invitations(world):
    world.shares.set_visibility('Mix', PUBLIC)
    world.shares.follow(BO, 'Mix')
    world.shares.set_visibility('Road', SHARED, [BO])
    world.shares.remove_user(BO)

    view = world.shares.view_for(BO)
    assert view.followed == frozenset()
    assert view.to_me == {}


# ── who sees what ────────────────────────────────────────────────────


def test_nothing_is_visible_to_others_by_default(world):
    assert _names(_request(ANA)) == ['Mix', 'Road']
    assert _names(_request(BO)) == ['Chill']
    assert _names(_request(CY)) == []
    assert _names(_admin()) == ['Chill', 'Mix', 'Road']


def test_own_rows_say_who_owns_them_and_who_they_are_shared_with(world):
    world.shares.set_visibility('Mix', SHARED, [BO, CY])
    rows = {p['name']: p for p in api.playlists_for_request(_request(ANA))}

    assert rows['Mix']['owner'] == 'ana'
    assert rows['Mix']['mine'] is True
    assert rows['Mix']['visibility'] == SHARED
    assert rows['Mix']['shared_with'] == ['bob', 'cyd']
    assert rows['Road']['visibility'] == PRIVATE


def test_a_playlist_shared_by_name_shows_for_that_user_as_new(world):
    world.shares.set_visibility('Mix', SHARED, [BO])
    rows = {p['name']: p for p in api.playlists_for_request(_request(BO))}

    shared = rows['Mix']
    assert shared['mine'] is False
    assert shared['owner'] == 'ana'
    assert shared['shared_with_me'] is True
    assert shared['new'] is True
    assert 'shared_with' not in shared
    assert 'Mix' not in _names(_request(CY))

    world.shares.mark_seen('Mix', BO)
    again = {p['name']: p for p in api.playlists_for_request(_request(BO))}
    assert again['Mix']['new'] is False


def test_public_playlists_show_unless_the_user_turned_them_off(world):
    world.shares.set_visibility('Mix', PUBLIC)
    assert _names(_request(CY)) == ['Mix']

    world.users.set_preferences(CY, {'show_public_playlists': False})
    assert _names(_request(CY)) == []


def test_a_followed_public_playlist_stays_when_public_ones_are_off(world):
    world.shares.set_visibility('Mix', PUBLIC)
    world.shares.follow(CY, 'Mix')
    world.users.set_preferences(CY, {'show_public_playlists': False})

    rows = api.playlists_for_request(_request(CY))
    assert [p['name'] for p in rows] == ['Mix']
    assert rows[0]['followed'] is True


def test_unsharing_removes_it_even_for_a_follower(world):
    world.shares.set_visibility('Mix', PUBLIC)
    world.shares.follow(CY, 'Mix')
    assert _names(_request(CY)) == ['Mix']

    world.shares.set_visibility('Mix', PRIVATE)
    assert _names(_request(CY)) == []


def test_removing_a_user_from_the_list_removes_it_for_them(world):
    world.shares.set_visibility('Mix', SHARED, [BO, CY])
    world.shares.set_visibility('Mix', SHARED, [CY])

    assert _names(_request(BO)) == ['Chill']
    assert _names(_request(CY)) == ['Mix']


def test_the_admin_switch_turns_every_share_off(world, monkeypatch):
    world.shares.set_visibility('Mix', PUBLIC)
    monkeypatch.setitem(api.state.settings, 'allow_playlist_sharing', False)

    assert _names(_request(CY)) == []
    rows = {p['name']: p for p in api.playlists_for_request(_request(ANA))}
    assert rows['Mix']['visibility'] == PRIVATE


def test_a_playlist_nobody_owns_is_never_shared(world):
    world.shares.set_visibility('Orphan', PUBLIC)
    api.state.playlist_catalog.ensure_playlist('Orphan', user_id=0)
    found = [_row('Orphan')]
    assert api._filter_playlists_for(found, _request(CY)) == []


# ── viewing is not editing ───────────────────────────────────────────


def test_a_viewer_can_open_but_not_change_a_shared_playlist(world):
    world.shares.set_visibility('Mix', PUBLIC)
    request = _request(CY)

    assert api.require_playlist_visible('Mix', request)['name'] == 'Mix'
    with pytest.raises(HTTPException) as err:
        api.require_playlist_visible('Mix', request, manage=True)
    assert err.value.status_code == 403
    # The owner and an admin may.
    assert api.require_playlist_visible('Mix', _request(ANA), manage=True)
    assert api.require_playlist_visible('Mix', _admin(), manage=True)


def test_a_private_playlist_reads_as_unknown(world):
    with pytest.raises(HTTPException) as err:
        api.require_playlist_visible('Mix', _request(CY))
    assert err.value.status_code == 404


def test_a_viewer_cannot_edit_rename_or_delete(world):
    world.shares.set_visibility('Mix', PUBLIC)
    for endpoint, body in (
        (api.edit_library_playlist_tracks_endpoint, {'name': 'Mix'}),
        (
            api.rename_library_playlist_endpoint,
            {'name': 'Mix', 'new_name': 'Nope'},
        ),
        (api.detach_library_playlist_endpoint, {'name': 'Road'}),
    ):
        with pytest.raises(HTTPException) as err:
            asyncio.run(endpoint(_request(CY, body=body)))
        assert err.value.status_code in {403, 404}

    with pytest.raises(HTTPException) as err:
        asyncio.run(api._delete_playlist_by_name(_request(CY), 'Mix'))
    assert err.value.status_code == 403


# ── the visibility endpoint ──────────────────────────────────────────


def test_the_owner_shares_with_named_users(world):
    result = _share(
        _request(
            ANA,
            body={
                'name': 'Mix',
                'visibility': 'shared',
                'shared_with': ['BOB', 'ana'],
            },
        )
    )

    assert result == {
        'name': 'Mix',
        'visibility': 'shared',
        'shared_with': ['bob'],
    }
    assert _names(_request(BO)) == ['Chill', 'Mix']


def test_the_owner_makes_a_playlist_public_and_private_again(world):
    _share(_request(ANA, body={'name': 'Road', 'visibility': 'public'}))
    assert 'Road' in _names(_request(CY))

    _share(_request(ANA, body={'name': 'Road', 'visibility': 'private'}))
    assert 'Road' not in _names(_request(CY))


@pytest.mark.parametrize(
    ('who', 'body', 'status'),
    [
        (CY, {'name': 'Mix', 'visibility': 'public'}, 404),
        (ANA, {'name': 'Mix', 'visibility': 'friends'}, 400),
        (ANA, {'name': 'Mix', 'visibility': 'shared'}, 400),
        (
            ANA,
            {'name': 'Mix', 'visibility': 'shared', 'shared_with': ['zed']},
            400,
        ),
        (ANA, {'name': 'Downtify Liked Songs', 'visibility': 'public'}, 400),
    ],
)
def test_bad_sharing_requests_are_refused(world, who, body, status):
    with pytest.raises(HTTPException) as err:
        _share(_request(who, body=body))
    assert err.value.status_code == status


def test_a_viewer_cannot_reshare_what_is_shared_with_them(world):
    world.shares.set_visibility('Mix', PUBLIC)
    with pytest.raises(HTTPException) as err:
        _share(_request(CY, body={'name': 'Mix', 'visibility': 'private'}))
    assert err.value.status_code == 403


def test_sharing_can_be_switched_off_but_still_withdrawn(world, monkeypatch):
    world.shares.set_visibility('Mix', PUBLIC)
    monkeypatch.setitem(api.state.settings, 'allow_playlist_sharing', False)

    with pytest.raises(HTTPException) as err:
        _share(_request(ANA, body={'name': 'Road', 'visibility': 'public'}))
    assert err.value.status_code == 403
    _share(_request(ANA, body={'name': 'Mix', 'visibility': 'private'}))
    assert world.shares.visibility('Mix') == PRIVATE


def test_the_visibility_route_is_for_signed_in_users():
    assert classify('PUT', '/api/library/playlists/visibility') == USER
    assert classify('POST', '/api/library/playlists/detach') == USER
    assert classify('POST', '/api/library/playlists/copy') == USER


# ── follow and the share picker ──────────────────────────────────────


def _follow(request: Request) -> dict[str, Any]:
    return asyncio.run(mobile_routes.follow_playlist(request))


def test_following_a_public_playlist(world):
    world.shares.set_visibility('Mix', PUBLIC)
    assert _follow(_request(CY, body={'name': 'Mix'})) == {
        'name': 'Mix',
        'followed': True,
    }
    assert world.shares.view_for(CY).followed == {'mix'}

    asyncio.run(
        mobile_routes.unfollow_playlist(_request(CY, query=b'name=Mix'))
    )
    assert world.shares.view_for(CY).followed == frozenset()


@pytest.mark.parametrize('visibility', [PRIVATE, SHARED])
def test_only_public_playlists_can_be_followed(world, visibility):
    world.shares.set_visibility(
        'Mix', visibility, [CY] if visibility == SHARED else []
    )
    with pytest.raises(HTTPException) as err:
        _follow(_request(CY, body={'name': 'Mix'}))
    assert err.value.status_code in {400, 404}


def test_you_cannot_follow_your_own_playlist(world):
    world.shares.set_visibility('Mix', PUBLIC)
    with pytest.raises(HTTPException) as err:
        _follow(_request(ANA, body={'name': 'Mix'}))
    assert err.value.status_code == 400


def test_the_share_picker_lists_everyone_else_by_name(world, monkeypatch):
    result = asyncio.run(mobile_routes.usernames(_request(ANA)))
    assert result == {'enabled': True, 'usernames': ['admin', 'bob', 'cyd']}

    monkeypatch.setitem(api.state.settings, 'allow_playlist_sharing', False)
    result = asyncio.run(mobile_routes.usernames(_request(ANA)))
    assert result == {'enabled': False, 'usernames': []}


def test_the_apps_playlist_rows_carry_owner_and_following(world, monkeypatch):
    world.shares.set_visibility('Mix', PUBLIC)
    world.shares.follow(CY, 'Mix')
    monkeypatch.setattr(mobile_routes, '_refresh', lambda: 0)
    monkeypatch.setattr(
        api.state,
        'library_sync',
        SimpleNamespace(ids_for_paths=lambda paths: {'a.mp3': 'id-a'}),
    )

    rows = asyncio.run(mobile_routes.playlists(_request(CY)))
    assert len(rows) == 1
    assert rows[0]['owner'] == 'ana'
    assert rows[0]['visibility'] == PUBLIC
    assert rows[0]['followed'] is True
    assert rows[0]['mine'] is False
    assert rows[0]['track_ids'] == ['id-a']


# ── saving a copy ────────────────────────────────────────────────────


def _track(root: Path, name: str) -> str:
    (root / name).write_bytes(b'audio')
    return name


def test_copy_playlist_writes_an_editable_playlist(world):
    root = world.ctx.download_dir
    files = [_track(root, 'one.mp3'), _track(root, 'two.mp3')]

    result = copy_playlist(world.ctx, files + ['one.mp3'], 'Road (copy)')

    assert result['name'] == 'Road (copy)'
    assert result['files'] == files
    path = root / 'Playlists' / 'Road (copy).m3u'
    assert is_manual_m3u(path)
    with pytest.raises(ManualPlaylistError) as err:
        copy_playlist(world.ctx, files, 'road (COPY)')
    assert err.value.status_code == 409


def test_a_viewer_saves_a_private_copy_they_own(world):
    root = world.ctx.download_dir
    _track(root, 'a.mp3')
    world.shares.set_visibility('Mix', PUBLIC)

    result = asyncio.run(
        api.copy_library_playlist_endpoint(_request(CY, body={'name': 'Mix'}))
    )

    assert result['name'] == 'Mix (copy)'
    assert world.manual.owner('Mix (copy)') == CY
    assert world.shares.visibility('Mix (copy)') == PRIVATE
    # A second copy gets the next free name.
    again = asyncio.run(
        api.copy_library_playlist_endpoint(_request(CY, body={'name': 'Mix'}))
    )
    assert again['name'] == 'Mix (copy) 2'


# ── detaching an imported playlist ───────────────────────────────────


def _imported(world, name: str = 'Road') -> Path:
    root = world.ctx.download_dir
    _track(root, 'a.mp3')
    path = root / 'Playlists' / f'{name}.m3u'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('#EXTM3U\n#EXTINF:1,A\n../a.mp3\n', encoding='utf-8')
    return path


def test_detach_marks_the_m3u_and_keeps_its_tracks(world):
    path = _imported(world)
    assert not is_manual_m3u(path)

    result = detach_imported_playlist(world.ctx, 'road')

    assert result['manual'] is True
    assert result['files'] == ['a.mp3']
    assert is_manual_m3u(path)
    lines = path.read_text(encoding='utf-8').splitlines()
    assert lines[:2] == ['#EXTM3U', MANUAL_M3U_MARKER]
    assert '../a.mp3' in lines


def test_detach_refuses_what_is_already_editable_or_missing(world):
    path = _imported(world)
    detach_imported_playlist(world.ctx, 'Road')
    with pytest.raises(ManualPlaylistError) as err:
        detach_imported_playlist(world.ctx, 'Road')
    assert err.value.status_code == 409
    path.unlink()
    with pytest.raises(ManualPlaylistError) as err:
        detach_imported_playlist(world.ctx, 'Road')
    assert err.value.status_code == 404


def test_detach_endpoint_unlinks_the_source_and_the_watch(world, monkeypatch):
    _imported(world)
    monitor = PlaylistMonitorDB(world.ctx.download_dir / 'monitor.db')
    watch = monitor.add_playlist(
        'sp1',
        'Road',
        'https://open.spotify.com/playlist/sp1',
        user_id=ANA,
    )
    other = monitor.add_playlist(
        'sp9',
        'Elsewhere',
        'https://open.spotify.com/playlist/sp9',
        user_id=ANA,
    )
    monkeypatch.setattr(api.state, 'monitor_db', monitor)
    monkeypatch.setattr(api.state, 'playlist_batch_store', None)
    monkeypatch.setattr(api.state, 'playlist_spotify_cache', None)

    result = asyncio.run(
        api.detach_library_playlist_endpoint(
            _request(ANA, body={'name': 'Road'})
        )
    )

    assert result['manual'] is True
    assert world.manual.owner('Road') == ANA
    assert 'Road' not in world.catalog.list_playlist_names()
    assert monitor.get_playlist(watch.id) is None
    assert monitor.get_playlist(other.id) is not None
    # Now an ordinary Library playlist: owned, shareable, and editable.
    world.found[0]['manual'] = True
    rows = {p['name']: p for p in api.playlists_for_request(_request(ANA))}
    assert rows['Road']['manual'] is True
    assert rows['Road']['mine'] is True


def test_detaching_a_library_playlist_is_a_conflict(world):
    with pytest.raises(HTTPException) as err:
        asyncio.run(
            api.detach_library_playlist_endpoint(
                _request(ANA, body={'name': 'Mix'})
            )
        )
    assert err.value.status_code == 409
