"""The shared library and what an admin hides from users. Offline.

Every account browses every downloaded track; an admin can hide songs,
albums or artists from users (never from admins). See
``downtify/library_visibility.py``.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException
from mutagen.id3 import ID3, TALB, TIT2, TPE1, TPE2
from starlette.requests import Request

from downtify import api
from downtify.auth import ADMIN, Principal, classify
from downtify.library_catalog import (
    LibraryContext,
    entry_content_key,
    library_album_index,
    library_artist_index,
    list_library_entries,
)
from downtify.library_paths_cache import (
    invalidate_library_paths_cache,
    set_listing_refresh_fn,
)
from downtify.library_sync import LibrarySync
from downtify.library_visibility import (
    KIND_ALBUM,
    KIND_ARTIST,
    KIND_TRACK,
    HiddenRules,
    LibraryVisibility,
    album_key,
    artist_key,
)
from downtify.track_owners import TrackOwners

TRACKS = (
    # file, title, artist, album
    ('Ana/Sun/Ana - One.mp3', 'One', 'Ana', 'Sun'),
    ('Ana/Sun/Ana - Two.mp3', 'Two', 'Ana', 'Sun'),
    ('Ana/Moon/Ana - Three.mp3', 'Three', 'Ana', 'Moon'),
    ('Bo/Sea/Bo - Four.mp3', 'Four', 'Bo', 'Sea'),
)


def _principal(user_id: int, role: str = 'user') -> Principal:
    return Principal('device', 'client', '', user_id, f'u{user_id}', role)


def _request(user_id: int = 0, role: str = 'user', body: Any = None):
    scope: dict[str, Any] = {'type': 'http', 'headers': []}
    if user_id:
        scope['state'] = {'principal': _principal(user_id, role)}
    raw = json.dumps(body).encode() if body is not None else b''

    async def receive() -> dict[str, Any]:
        return {'type': 'http.request', 'body': raw, 'more_body': False}

    return Request(scope, receive)


def _admin(body: Any = None) -> Request:
    return _request(1, 'admin', body)


def _write_track(root: Path, rel: str, title: str, artist: str, album: str):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'audio-' + title.encode())
    tags = ID3()
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text=artist))
    tags.add(TPE2(encoding=3, text=artist))
    tags.add(TALB(encoding=3, text=album))
    tags.save(str(path), v2_version=3)


@pytest.fixture
def library(tmp_path, monkeypatch):
    """A tagged library on disk wired into ``api.state``."""

    root = tmp_path / 'downloads'
    root.mkdir()
    for rel, title, artist, album in TRACKS:
        _write_track(root, rel, title, artist, album)
    ctx = LibraryContext(download_dir=root)
    invalidate_library_paths_cache()
    set_listing_refresh_fn(lambda: list_library_entries(ctx))
    list_library_entries(ctx)
    db = tmp_path / 'lib.db'
    monkeypatch.setattr(api, 'library_context', lambda: ctx)
    monkeypatch.setattr(api.state, 'library_visibility', LibraryVisibility(db))
    monkeypatch.setattr(api.state, 'track_owners', TrackOwners(db))
    monkeypatch.setattr(api.state, 'library_sync', LibrarySync(db))
    yield ctx
    set_listing_refresh_fn(lambda: None)
    invalidate_library_paths_cache()


def _files(rows: list[dict[str, Any]]) -> list[str]:
    return sorted(row['file'] for row in rows)


def _update(request: Request) -> dict[str, Any]:
    return asyncio.run(api.library_visibility_update(request))


# ── rules ────────────────────────────────────────────────────────────


def test_nothing_hidden_matches_nothing():
    rules = HiddenRules()

    assert not rules
    assert not rules.reason({'file': 'a.mp3', 'artist': 'Ana'})


def test_rules_match_the_way_the_library_groups():
    entry = {
        'file': 'a/b.mp3',
        'artist': 'Ana',
        'album_artist': 'Ana',
        'album': 'Sun',
        'size': 10,
    }

    # Names compare case-insensitively.
    assert (
        HiddenRules(artists=frozenset({artist_key('ANA')})).reason(entry)
        == KIND_ARTIST
    )
    assert (
        HiddenRules(albums=frozenset({album_key('ana', 'SUN')})).reason(entry)
        == KIND_ALBUM
    )
    assert (
        HiddenRules(track_paths=frozenset({'a/b.mp3'})).reason(entry)
        == KIND_TRACK
    )
    assert HiddenRules(track_keys=frozenset({entry_content_key(entry)})).hides(
        entry
    )
    # The same album title under another artist is a different album.
    assert not HiddenRules(albums=frozenset({album_key('Bo', 'Sun')})).hides(
        entry
    )


def test_the_widest_rule_names_the_reason():
    entry = {'file': 'a.mp3', 'artist': 'Ana', 'album': 'Sun', 'size': 1}
    rules = HiddenRules(
        track_paths=frozenset({'a.mp3'}),
        albums=frozenset({album_key('Ana', 'Sun')}),
        artists=frozenset({artist_key('Ana')}),
    )

    assert rules.reason(entry) == KIND_ARTIST
    assert rules.album_reason('Ana', 'Sun') == KIND_ARTIST
    assert not rules.album_reason('Bo', 'Sun')


# ── the store ────────────────────────────────────────────────────────


def test_hide_and_show_are_idempotent_and_cached(tmp_path):
    store = LibraryVisibility(tmp_path / 'lib.db')
    assert not store.rules()

    assert store.hide(KIND_ARTIST, artist_key('Ana'), label='Ana') is True
    assert store.hide(KIND_ARTIST, artist_key('Ana'), label='Ana') is False
    assert store.rules().artists == {'ana'}
    assert store.show(KIND_ARTIST, 'ana') is True
    assert store.show(KIND_ARTIST, 'ana') is False
    assert not store.rules()


def test_rules_survive_a_restart(tmp_path):
    db = tmp_path / 'lib.db'
    LibraryVisibility(db).hide(
        KIND_TRACK, 'key-1', label='Ana - One', path='Ana\\One.mp3'
    )

    rules = LibraryVisibility(db).rules()

    assert rules.track_keys == {'key-1'}
    # Paths are stored with forward slashes.
    assert rules.track_paths == {'Ana/One.mp3'}


def test_unknown_kinds_and_empty_keys_are_ignored(tmp_path):
    store = LibraryVisibility(tmp_path / 'lib.db')

    assert store.hide('playlist', 'x') is False
    assert store.hide(KIND_ARTIST, '') is False
    assert not store.rules()


def test_a_rewritten_file_stays_hidden(tmp_path):
    store = LibraryVisibility(tmp_path / 'lib.db')
    store.hide(KIND_TRACK, 'old', label='x', path='a.mp3')

    assert store.rekey_track('old', 'new', 'a.mp3') == 1

    assert store.rules().track_keys == {'new'}
    assert store.rekey_track('old', 'new') == 0
    assert store.rekey_track('new', 'new') == 0


def test_a_deleted_file_forgets_its_rule(tmp_path):
    store = LibraryVisibility(tmp_path / 'lib.db')
    store.hide(KIND_TRACK, 'k', path='a.mp3')

    store.drop_track('k')

    assert not store.rules()


def test_show_track_by_path_finds_a_rule_with_a_stale_key(tmp_path):
    store = LibraryVisibility(tmp_path / 'lib.db')
    store.hide(KIND_TRACK, 'stale', path='a.mp3')

    assert store.show_track_by_path('a.mp3') == 1
    assert store.show_track_by_path('a.mp3') == 0
    assert store.show_track_by_path('') == 0


def test_items_list_newest_first_with_labels(tmp_path):
    store = LibraryVisibility(tmp_path / 'lib.db')
    store.hide(KIND_ARTIST, 'ana', label='Ana')
    store.hide(KIND_ALBUM, album_key('Ana', 'Sun'), label='Sun', detail='Ana')
    store.hide(KIND_TRACK, 'k', label='Ana - One', detail='Sun', path='a.mp3')

    items = store.items()

    assert [row['name'] for row in items['artists']] == ['Ana']
    assert items['albums'][0]['title'] == 'Sun'
    assert items['albums'][0]['artist'] == 'Ana'
    assert items['tracks'][0]['file'] == 'a.mp3'
    assert items['tracks'][0]['label'] == 'Ana - One'


# ── who sees what ────────────────────────────────────────────────────


def test_users_see_every_download_when_nothing_is_hidden(library):
    # Nobody owns anything: still every account browses everything.
    for request in (_request(5), _request(7), _admin()):
        assert api.allowed_entry_keys(request) is None
        assert len(api.entries_for_request(request)) == len(TRACKS)


def test_someone_elses_download_is_visible(library):
    api.state.track_owners.add(
        entry_content_key(api.entries_for_request(_admin())[0]), 5
    )

    assert len(api.entries_for_request(_request(7))) == len(TRACKS)


def test_an_unidentified_request_sees_nothing(library):
    assert api.allowed_entry_keys(_request()) == set()
    assert api.entries_for_request(_request()) == []


def test_hiding_cuts_users_and_marks_admins(library):
    _update(
        _admin({
            'action': 'hide',
            'items': [{'kind': 'track', 'file': 'Ana/Sun/Ana - One.mp3'}],
        })
    )

    seen = api.entries_for_request(_request(5))
    assert 'Ana/Sun/Ana - One.mp3' not in _files(seen)
    assert len(seen) == len(TRACKS) - 1
    allowed = api.allowed_entry_keys(_request(5))
    assert allowed is not None
    assert len(allowed) == len(TRACKS) - 1

    everything = api.entries_for_request(_admin())
    assert len(everything) == len(TRACKS)
    marks = {r['file']: r.get('hidden_by') for r in everything}
    assert marks['Ana/Sun/Ana - One.mp3'] == KIND_TRACK
    assert marks['Ana/Sun/Ana - Two.mp3'] is None
    assert api.allowed_entry_keys(_admin()) is None


def test_hiding_an_album_hides_all_of_it(library):
    _update(
        _admin({
            'action': 'hide',
            'items': [{'kind': 'album', 'artist': 'ana', 'title': 'SUN'}],
        })
    )

    assert _files(api.entries_for_request(_request(5))) == [
        'Ana/Moon/Ana - Three.mp3',
        'Bo/Sea/Bo - Four.mp3',
    ]
    albums = library_album_index(
        library,
        allowed_keys=api.allowed_entry_keys(_request(5)),
        hidden=api.admin_hidden_rules(_request(5)),
    )
    assert sorted(a['title'] for a in albums) == ['Moon', 'Sea']
    admin_albums = library_album_index(
        library,
        allowed_keys=api.allowed_entry_keys(_admin()),
        hidden=api.admin_hidden_rules(_admin()),
    )
    marks = {a['title']: a.get('hidden_by') for a in admin_albums}
    assert marks == {'Sun': KIND_ALBUM, 'Moon': None, 'Sea': None}


def test_hiding_an_artist_hides_every_album_of_theirs(library):
    _update(
        _admin({
            'action': 'hide',
            'items': [{'kind': 'artist', 'name': 'ANA'}],
        })
    )

    assert _files(api.entries_for_request(_request(5))) == [
        'Bo/Sea/Bo - Four.mp3'
    ]
    allowed = api.allowed_entry_keys(_request(5))
    artists = library_artist_index(library, set(), allowed_keys=allowed)
    assert [a['name'] for a in artists] == ['Bo']
    admin_artists = library_artist_index(
        library,
        set(),
        allowed_keys=None,
        hidden=api.admin_hidden_rules(_admin()),
    )
    marks = {a['name']: a.get('hidden_by') for a in admin_artists}
    assert marks == {'Ana': KIND_ARTIST, 'Bo': None}
    albums = library_album_index(
        library, hidden=api.admin_hidden_rules(_admin())
    )
    assert {a['title']: a.get('hidden_by') for a in albums} == {
        'Sun': KIND_ARTIST,
        'Moon': KIND_ARTIST,
        'Sea': None,
    }


def test_showing_brings_everything_back(library):
    item = {'kind': 'album', 'artist': 'Ana', 'title': 'Sun'}
    _update(_admin({'action': 'hide', 'items': [item]}))
    assert len(api.entries_for_request(_request(5))) == 2

    result = _update(_admin({'action': 'show', 'items': [item]}))

    assert result['changed'] == 1
    assert len(api.entries_for_request(_request(5))) == len(TRACKS)
    assert api.allowed_entry_keys(_request(5)) is None
    assert result['albums'] == []


def test_showing_a_track_works_by_path_alone(library):
    item = {'kind': 'track', 'file': 'Bo/Sea/Bo - Four.mp3'}
    _update(_admin({'action': 'hide', 'items': [item]}))

    result = _update(_admin({'action': 'show', 'items': [item]}))

    assert result['changed'] == 1
    assert result['tracks'] == []


def test_hiding_twice_counts_once(library):
    body = {
        'action': 'hide',
        'items': [{'kind': 'artist', 'name': 'Bo'}] * 2,
    }

    assert _update(_admin(body))['changed'] == 1
    assert _update(_admin(body))['changed'] == 0


def test_a_hidden_song_stays_hidden_after_a_move(library):
    _update(
        _admin({
            'action': 'hide',
            'items': [{'kind': 'track', 'file': 'Bo/Sea/Bo - Four.mp3'}],
        })
    )
    original = next(
        e
        for e in api.entries_for_request(_admin())
        if e['file'] == 'Bo/Sea/Bo - Four.mp3'
    )
    # Same name and size under another folder: the content key matches.
    moved = {**original, 'file': 'Elsewhere/Bo - Four.mp3'}

    assert api.hidden_rules().hides(moved)


def test_a_playlists_tracks_leave_out_hidden_songs(library):
    _update(
        _admin({
            'action': 'hide',
            'items': [{'kind': 'artist', 'name': 'Bo'}],
        })
    )
    rows = api.entries_for_request(_admin())

    assert _files(api.visible_entries(rows, _request(5))) == _files([
        r for r in rows if r['artist'] != 'Bo'
    ])
    assert len(api.visible_entries(rows, _admin())) == len(TRACKS)


def test_the_path_listing_follows_the_same_rule(library):
    _update(
        _admin({
            'action': 'hide',
            'items': [{'kind': 'artist', 'name': 'Bo'}],
        })
    )
    paths = [row['file'] for row in api.entries_for_request(_admin())]

    assert 'Bo/Sea/Bo - Four.mp3' not in api.filter_paths_for_request(
        paths, _request(5)
    )
    assert api.filter_paths_for_request(paths, _admin()) == paths


def test_hiding_pokes_the_sync_feed_for_apps(library):
    sync = api.state.library_sync
    touched: list[str] = []
    sync.touch = lambda path: touched.append(path) or True

    _update(
        _admin({
            'action': 'hide',
            'items': [{'kind': 'album', 'artist': 'Ana', 'title': 'Sun'}],
        })
    )

    assert sorted(touched) == [
        'Ana/Sun/Ana - One.mp3',
        'Ana/Sun/Ana - Two.mp3',
    ]
    touched.clear()
    _update(
        _admin({
            'action': 'show',
            'items': [{'kind': 'album', 'artist': 'Ana', 'title': 'Sun'}],
        })
    )
    assert len(touched) == 2


# ── the endpoint ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    'body',
    [
        None,
        {},
        {'action': 'remove', 'items': []},
        {'action': 'hide', 'items': 'nope'},
        {'action': 'hide', 'items': [{'kind': 'playlist'}]},
        {'action': 'hide', 'items': [{'kind': 'album', 'artist': 'Ana'}]},
        {'action': 'hide', 'items': [{'kind': 'artist', 'name': ' '}]},
        {'action': 'hide', 'items': [{'kind': 'track', 'file': 'no.mp3'}]},
    ],
)
def test_bad_requests_are_rejected(library, body):
    with pytest.raises(HTTPException) as caught:
        _update(_admin(body))

    assert caught.value.status_code in {400, 404}
    assert not api.hidden_rules()


def test_too_many_items_are_refused(library):
    items = [{'kind': 'artist', 'name': str(n)} for n in range(2001)]

    with pytest.raises(HTTPException) as caught:
        _update(_admin({'action': 'hide', 'items': items}))

    assert caught.value.status_code == 413


def test_non_item_entries_are_skipped(library):
    result = _update(_admin({'action': 'hide', 'items': ['x', 3]}))

    assert result['changed'] == 0


def test_hiding_and_showing_are_logged_with_what_changed(library, monkeypatch):
    logged: list[tuple[str, str, dict]] = []

    async def record(request, kind, summary='', detail=None):
        logged.append((kind, summary, detail))

    monkeypatch.setattr(api, 'log_activity', record)
    items = [{'kind': 'artist', 'name': n} for n in ('Ana', 'Bo')]

    _update(_admin({'action': 'hide', 'items': items}))
    _update(_admin({'action': 'show', 'items': items[:1]}))
    # Nothing changed: nothing logged.
    _update(_admin({'action': 'show', 'items': items[:1]}))

    assert logged == [
        ('library_hidden', 'Ana, Bo', {'count': 2}),
        ('library_shown', 'Ana', {'count': 1}),
    ]


def test_the_list_endpoint_returns_what_is_hidden(library):
    _update(
        _admin({
            'action': 'hide',
            'items': [
                {'kind': 'artist', 'name': 'Bo'},
                {'kind': 'track', 'file': 'Ana/Sun/Ana - One.mp3'},
            ],
        })
    )

    listed = api.library_visibility_list()

    assert [a['name'] for a in listed['artists']] == ['Bo']
    assert listed['tracks'][0]['label'] == 'Ana - One'
    assert listed['albums'] == []


def test_the_endpoint_is_admin_only():
    for method in ('GET', 'POST'):
        assert classify(method, '/api/library/visibility') == ADMIN


def test_a_missing_store_is_a_503(monkeypatch):
    monkeypatch.setattr(api.state, 'library_visibility', None)

    with pytest.raises(HTTPException) as caught:
        api.library_visibility_list()

    assert caught.value.status_code == 503
    assert not api.hidden_rules()


# ── deleting stays with whoever downloaded it ────────────────────────


def test_only_the_owner_or_an_admin_may_delete(library):
    key = entry_content_key(api.entries_for_request(_admin())[0])
    file = api.entries_for_request(_admin())[0]['file']
    api.state.track_owners.add(key, 5)

    assert api.ownership_action(file, _request(5))[0] == 'delete'
    assert api.ownership_action(file, _request(7))[0] == 'foreign'
    assert api.ownership_action(file, _admin())[0] == 'delete'


def test_rewrite_and_delete_hooks_keep_the_rules_in_step(library):
    _update(
        _admin({
            'action': 'hide',
            'items': [{'kind': 'track', 'file': 'Bo/Sea/Bo - Four.mp3'}],
        })
    )
    old = next(iter(api.hidden_rules().track_keys))

    api.rekey_file_owners(old, 'new-key', 'Bo/Sea/Bo - Four.mp3')
    assert api.hidden_rules().track_keys == {'new-key'}

    api.drop_file_owners('new-key')
    assert not api.hidden_rules()


def test_the_delete_error_names_who_may_delete():
    assert 'admin' in api.NOT_YOURS_ERROR
