"""Hiding songs from an imported playlist, and keeping them out (#466).

A playlist downloaded from a Spotify / YouTube Music link follows its
source, so a song taken out of it by hand would come back on the next
watch sweep or *Download missing*. Hiding remembers it per playlist - see
``downtify/playlist_hidden.py``. Offline.
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

from downtify import api, m3u, mobile_routes, monitor
from downtify.auth import CLIENT, USER, Principal, classify
from downtify.library_catalog import LibraryContext
from downtify.library_paths_cache import invalidate_library_paths_cache
from downtify.monitor import LibraryStores, PlaylistMonitorDB
from downtify.playlist_catalog import ManualPlaylistOwners, PlaylistCatalog
from downtify.playlist_hidden import (
    HiddenSongs,
    HiddenSongsError,
    PlaylistHiddenSongs,
    hidden_key,
    hide_playlist_songs,
    show_playlist_songs,
    source_track_ids,
)
from downtify.playlist_shares import SHARED, PlaylistShares
from downtify.track_index import TrackIndex
from downtify.users import UserStore

TRACK_A = '4uLU6hMCjMI75M1A2tKUQC'
TRACK_B = '7ouMYWpwJ422jRcDASZB7P'
TRACK_C = '1301WleyT98MSxVHPZCA6M'
PLAYLIST_ID = '37i9dQZF1DXcBWIGoYBM5M'

ADMIN_ID = 1
ANA = 2
BO = 3


# ── The store ───────────────────────────────────────────────────────────


def test_store_hides_lists_counts_and_shows_again(tmp_path):
    store = PlaylistHiddenSongs(tmp_path / 'lib.db')

    assert store.hide(
        'Road Trip', track_id=TRACK_A, content_key='k1', path='a.mp3'
    )
    assert not store.hide('Road Trip', track_id=TRACK_A, path='a.mp3')
    assert store.hide('Road Trip', content_key='k2', path='b.mp3')
    assert not store.hide('Road Trip')

    songs = store.songs('road trip')
    assert songs.track_ids == {TRACK_A}
    assert songs.files == {'a.mp3', 'b.mp3'}
    assert songs.hides_song({'song_id': TRACK_A})
    assert songs.hides_song({
        'url': f'https://open.spotify.com/track/{TRACK_A}'
    })
    assert not songs.hides_song({'song_id': TRACK_B})
    assert songs.hides_file('b.mp3')
    assert songs.hides_file('elsewhere.mp3', 'k2')
    assert store.counts() == {'road trip': 2}

    keys = [row['key'] for row in store.items('Road Trip')]
    assert set(keys) == {TRACK_A, 'key:k2'}
    shown = store.show('Road Trip', [TRACK_A, 'nope'])
    assert [row['file'] for row in shown] == ['a.mp3']
    assert store.songs('Road Trip').track_ids == frozenset()
    assert store.forget('Road Trip') == 1
    assert not store.songs('Road Trip')
    assert not store.songs('Never hid anything')


def test_a_watch_name_and_its_m3u_stem_find_the_same_songs(tmp_path):
    """A watch keeps the source's name; the M3U (and the listing) use it
    without the characters a file name can't hold."""

    store = PlaylistHiddenSongs(tmp_path / 'lib.db')
    store.hide('Top 50: USA', track_id=TRACK_A)

    assert hidden_key('Top 50: USA') == hidden_key('top 50 usa')
    assert store.songs('Top 50 USA').hides_song({'song_id': TRACK_A})


def test_a_hidden_song_follows_its_rewritten_file(tmp_path):
    store = PlaylistHiddenSongs(tmp_path / 'lib.db')
    store.hide('Mix', content_key='old', path='a.mp3')

    assert store.rekey('old', 'new', 'a.flac') == 1
    assert store.songs('Mix').hides_file('a.flac', 'new')
    assert not store.songs('Mix').hides_file('a.mp3', 'old')


# ── M3U editing ─────────────────────────────────────────────────────────


def _audio(root: Path, *names: str) -> None:
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'audio-' + name.encode())


def test_removing_a_track_keeps_every_other_line(tmp_path):
    _audio(tmp_path, 'a.mp3', 'b.mp3')
    path = tmp_path / 'Playlists' / 'Mix.m3u'
    path.parent.mkdir()
    path.write_text(
        '#EXTM3U\n#EXTDOWNTIFY:cover\n'
        '#EXTINF:100,X - A\n../a.mp3\n#EXTINF:90,Y - B\n../b.mp3\n'
    )

    assert m3u.read_m3u_entries(path, tmp_path) == [
        ('a.mp3', '#EXTINF:100,X - A'),
        ('b.mp3', '#EXTINF:90,Y - B'),
    ]
    assert m3u.remove_m3u_tracks(path, ['a.mp3'], tmp_path) == 1
    assert path.read_text() == (
        '#EXTM3U\n#EXTDOWNTIFY:cover\n#EXTINF:90,Y - B\n../b.mp3\n'
    )
    assert m3u.remove_m3u_tracks(path, ['zzz.mp3'], tmp_path) == 0


def test_a_track_goes_back_where_it_was(tmp_path):
    _audio(tmp_path, 'a.mp3', 'b.mp3', 'c.mp3')
    path = tmp_path / 'Playlists' / 'Mix.m3u'
    path.parent.mkdir()
    path.write_text('#EXTM3U\n#EXTINF:1,A\n../a.mp3\n#EXTINF:3,C\n../c.mp3\n')

    assert m3u.insert_m3u_track(path, 'b.mp3', 1, '#EXTINF:2,B', tmp_path)
    assert m3u.read_m3u_tracks(path, tmp_path) == ['a.mp3', 'b.mp3', 'c.mp3']
    assert '#EXTINF:2,B\n../b.mp3\n#EXTINF:3,C' in path.read_text()
    # Past the end: appended.
    _audio(tmp_path, 'd.mp3')
    assert m3u.insert_m3u_track(path, 'd.mp3', 99, '', tmp_path)
    assert m3u.read_m3u_tracks(path, tmp_path)[-1] == 'd.mp3'
    assert not m3u.insert_m3u_track(path, 'gone.mp3', 0, '', tmp_path)


# ── Hiding and showing ──────────────────────────────────────────────────

FILES = ('Road Trip/Alpha.mp3', 'Road Trip/Beta.mp3', 'Road Trip/Gamma.mp3')


def _imported(root: Path, name: str = 'Road Trip') -> Path:
    _audio(root, *FILES)
    path, _kept = m3u.write_m3u(
        root,
        name,
        [
            {'filename': f, 'title': Path(f).stem, 'artist': 'Artist'}
            for f in FILES
        ],
        playlist_subdir=name,
    )
    return path


@pytest.fixture
def lib(tmp_path):
    root = tmp_path / 'downloads'
    root.mkdir()
    db = tmp_path / 'lib.db'
    path = _imported(root)
    catalog = PlaylistCatalog(db)
    for order, (tid, name) in enumerate(
        zip((TRACK_A, TRACK_B, TRACK_C), FILES)
    ):
        catalog.upsert_track(
            'Road Trip', {'song_id': tid}, name, root / name, track_order=order
        )
        catalog.upsert_track('Other', {'song_id': tid}, name, root / name)
    invalidate_library_paths_cache()
    yield SimpleNamespace(
        root=root,
        path=path,
        ctx=LibraryContext(download_dir=root),
        store=PlaylistHiddenSongs(db),
        catalog=catalog,
    )
    invalidate_library_paths_cache()


def _tracks(lib) -> list[str]:
    return m3u.read_m3u_tracks(lib.path, lib.root)


def test_hiding_takes_the_song_out_of_the_playlist_only(lib):
    ids = source_track_ids('Road Trip', [FILES[0]], catalog=lib.catalog)
    assert ids == {FILES[0]: TRACK_A}

    result = hide_playlist_songs(
        lib.ctx,
        lib.store,
        'road trip',
        [FILES[0]],
        track_ids=ids,
        catalog=lib.catalog,
    )

    assert result['hidden'] == 1
    assert result['keys'] == [TRACK_A]
    assert result['files'] == list(FILES[1:])
    assert _tracks(lib) == list(FILES[1:])
    # The audio stays in the library, and in the other playlist.
    assert (lib.root / FILES[0]).is_file()
    assert [r['filename'] for r in lib.catalog.list_tracks('Road Trip')] == [
        FILES[1],
        FILES[2],
    ]
    assert len(lib.catalog.list_tracks('Other')) == 3
    [row] = lib.store.items('Road Trip')
    assert row['label'] == 'Artist - Alpha'
    assert row['position'] == 0


def test_hiding_refuses_what_it_cannot_do(lib):
    with pytest.raises(HiddenSongsError) as unknown:
        hide_playlist_songs(lib.ctx, lib.store, 'Nope', [FILES[0]])
    assert unknown.value.status_code == 404
    with pytest.raises(HiddenSongsError):
        hide_playlist_songs(lib.ctx, lib.store, 'Road Trip', ['x.mp3'])
    with pytest.raises(HiddenSongsError, match='at least one'):
        hide_playlist_songs(lib.ctx, lib.store, 'Road Trip', list(FILES))
    manual = lib.root / 'Playlists' / 'Mine.m3u'
    manual.parent.mkdir(exist_ok=True)
    manual.write_text(
        f'#EXTM3U\n{m3u.MANUAL_M3U_MARKER}\n../Road Trip/Alpha.mp3\n'
    )
    with pytest.raises(HiddenSongsError) as library_playlist:
        hide_playlist_songs(lib.ctx, lib.store, 'Mine', [FILES[0]])
    assert library_playlist.value.status_code == 409
    assert _tracks(lib) == list(FILES)


def test_showing_puts_the_song_back_where_it_was(lib):
    hidden = hide_playlist_songs(
        lib.ctx,
        lib.store,
        'Road Trip',
        [FILES[1]],
        track_ids={FILES[1]: TRACK_B},
        catalog=lib.catalog,
    )

    result = show_playlist_songs(
        lib.ctx, lib.store, 'Road Trip', hidden['keys'], catalog=lib.catalog
    )

    assert (result['shown'], result['restored']) == (1, 1)
    assert _tracks(lib) == list(FILES)
    assert '#EXTINF:-1,Artist - Beta' in lib.path.read_text()
    assert not lib.store.songs('Road Trip')
    assert FILES[1] in {
        r['filename'] for r in lib.catalog.list_tracks('Road Trip')
    }


def test_showing_a_song_whose_file_is_gone_only_forgets_it(lib):
    hidden = hide_playlist_songs(lib.ctx, lib.store, 'Road Trip', [FILES[2]])
    (lib.root / FILES[2]).unlink()

    result = show_playlist_songs(
        lib.ctx, lib.store, 'Road Trip', hidden['keys']
    )

    assert (result['shown'], result['restored']) == (1, 0)
    assert _tracks(lib) == list(FILES[:2])
    assert not lib.store.songs('Road Trip')


# ── Watches ─────────────────────────────────────────────────────────────


class _Downloader:
    organize_by_artist = False
    organize_by_album = False
    slskd_settings: dict = {}
    overwrite_existing_files = True

    def __init__(self, download_dir: Path):
        self.download_dir = download_dir
        self.downloaded: list[str] = []

    def download(self, song, cb, subdir=None):
        self.downloaded.append(song['song_id'])
        name = f'{subdir}/{song["name"]}.mp3'
        _audio(self.download_dir, name)
        return name

    @staticmethod
    def existing_filename_for(song, subdir=None):
        return None


def _sweep(playlist, db, downloader, library):
    async def _broadcast(_msg):
        return None

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            monitor.check_playlist(
                playlist,
                db,
                downloader,
                _broadcast,
                loop,
                {'generate_m3u': True},
                library,
            )
        )
    finally:
        loop.close()


def test_a_watch_never_lists_or_downloads_a_hidden_song_again(
    monkeypatch, tmp_path
):
    root = tmp_path / 'downloads'
    source = [
        {'song_id': TRACK_A, 'name': 'Alpha', 'artists': ['Artist']},
        {'song_id': TRACK_B, 'name': 'Beta', 'artists': ['Artist']},
    ]
    monkeypatch.setattr(
        monitor.spotify, 'playlist_tracks_from_id', lambda _id: list(source)
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda _id: {})
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    playlist = db.add_playlist(
        PLAYLIST_ID,
        'Road Trip',
        f'https://open.spotify.com/playlist/{PLAYLIST_ID}',
    )
    library_db = tmp_path / 'library.db'
    library = LibraryStores(
        track_index=TrackIndex(library_db),
        playlist_catalog=PlaylistCatalog(library_db),
        playlist_hidden=PlaylistHiddenSongs(library_db),
    )
    downloader = _Downloader(root)
    assert _sweep(playlist, db, downloader, library) == 2
    m3u_path = root / 'Road Trip' / 'Road Trip.m3u'

    # The owner hides Alpha (its watch knows its Spotify id), deletes its
    # file, and the hourly check forgets it was downloaded.
    ctx = LibraryContext(download_dir=root)
    ids = source_track_ids('Road Trip', ['Road Trip/Alpha.mp3'], monitor_db=db)
    assert ids == {'Road Trip/Alpha.mp3': TRACK_A}
    hide_playlist_songs(
        ctx,
        library.playlist_hidden,
        'Road Trip',
        ['Road Trip/Alpha.mp3'],
        track_ids=ids,
        catalog=library.playlist_catalog,
    )
    (root / 'Road Trip' / 'Alpha.mp3').unlink()
    db.remove_downloaded_tracks([(playlist.id, TRACK_A)])

    source.append({'song_id': TRACK_C, 'name': 'Gamma', 'artists': ['A']})
    assert _sweep(playlist, db, downloader, library) == 1

    assert downloader.downloaded == [TRACK_A, TRACK_B, TRACK_C]
    assert m3u.read_m3u_tracks(m3u_path, root) == [
        'Road Trip/Beta.mp3',
        'Road Trip/Gamma.mp3',
    ]
    assert [
        r['track_spotify_id']
        for r in library.playlist_catalog.list_tracks('Road Trip')
    ] == [TRACK_B, TRACK_C]
    assert db.get_playlist(playlist.id).last_track_count == 2


# ── Downloads from a link, and what is missing ─────────────────────────


def test_a_hidden_song_stays_out_of_the_m3u_of_a_new_download():
    songs = [
        {'song_id': TRACK_A, 'name': 'Alpha', 'artists': ['A']},
        {'song_id': TRACK_B, 'name': 'Beta', 'artists': ['A']},
        {'song_id': '', 'name': 'Gamma', 'artists': ['A']},
    ]
    resolved = {0: 'a.mp3', 1: 'b.mp3', 2: 'c.mp3'}
    hidden = HiddenSongs(frozenset({TRACK_A}), frozenset({'c.mp3'}))

    entries = api._m3u_entries_for(songs, resolved, hidden)

    assert [e['filename'] for e in entries] == ['b.mp3']
    assert len(api._m3u_entries_for(songs, resolved)) == 3


def test_a_hidden_song_is_never_missing(monkeypatch, tmp_path):
    store = PlaylistHiddenSongs(tmp_path / 'lib.db')
    store.hide('Top 50: USA', track_id=TRACK_A)
    monkeypatch.setattr(api.state, 'playlist_hidden', store)
    tracks = [{'song_id': TRACK_A}, {'song_id': TRACK_B}]

    assert api._without_hidden_songs('Top 50 USA', tracks) == [
        {'song_id': TRACK_B}
    ]
    assert api._without_hidden_songs('Other', tracks) == tracks
    assert api.hidden_from_playlist('Top 50: USA', {'song_id': TRACK_A}, '')


# ── The endpoints ───────────────────────────────────────────────────────


def _request(user_id: int, role: str = 'user', body: Any = None) -> Request:
    scope: dict[str, Any] = {
        'type': 'http',
        'headers': [],
        'query_string': b'',
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


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Ana's imported "Road Trip", shared view-only with Bo."""

    root = tmp_path / 'downloads'
    root.mkdir()
    _imported(root)
    db = tmp_path / 'lib.db'
    users = UserStore(db)
    users.create('admin', 'password-1', 'admin')
    users.create('ana', 'password-2')
    users.create('bob', 'password-3')
    catalog = PlaylistCatalog(db)
    catalog.ensure_playlist('Road Trip', spotify_id=PLAYLIST_ID, user_id=ANA)
    shares = PlaylistShares(db)
    shares.set_visibility('Road Trip', SHARED, [BO])
    store = PlaylistHiddenSongs(db)
    ctx = LibraryContext(download_dir=root)
    monkeypatch.setattr(api, 'library_context', lambda: ctx)
    monkeypatch.setattr(api.state, 'auth', SimpleNamespace(users=users))
    monkeypatch.setattr(api.state, 'playlist_catalog', catalog)
    monkeypatch.setattr(
        api.state, 'manual_playlist_owners', ManualPlaylistOwners(db)
    )
    monkeypatch.setattr(api.state, 'playlist_shares', shares)
    monkeypatch.setattr(api.state, 'playlist_hidden', store)
    monkeypatch.setattr(api.state, 'monitor_db', None)
    monkeypatch.setattr(api.state, 'likes', None)
    monkeypatch.setitem(api.state.settings, 'allow_playlist_sharing', True)
    monkeypatch.setitem(api.state.settings, 'sync_navidrome', False)
    invalidate_library_paths_cache()
    yield SimpleNamespace(root=root, store=store)
    invalidate_library_paths_cache()


def _hide(user_id: int, role: str = 'user', **body: Any) -> dict[str, Any]:
    return asyncio.run(
        api.change_hidden_playlist_songs_endpoint(
            _request(user_id, role, body={'name': 'Road Trip', **body})
        )
    )


def _road_trip(user_id: int) -> dict[str, Any]:
    return next(
        p
        for p in api.playlists_for_request(_request(user_id))
        if p['name'] == 'Road Trip'
    )


def test_the_owner_hides_a_song_and_shows_it_again(world):
    result = _hide(ANA, hide=[FILES[0]])

    assert result['hidden'] == 1
    assert result['count'] == 2
    assert _road_trip(ANA)['hidden_count'] == 1
    assert _road_trip(ANA)['files'] == list(FILES[1:])
    # A viewer sees the playlist as its owner keeps it, without the count.
    assert 'hidden_count' not in _road_trip(BO)
    listed = api.hidden_playlist_songs('Road Trip', _request(ANA))
    [song] = listed['songs']
    assert song['label'] == 'Artist - Alpha'
    assert song['present'] is True
    # No source id known for it (no catalog row, no watch): its content
    # key stands in.
    assert song['key'].startswith('key:')

    shown = _hide(ANA, show=[song['key']])
    assert (shown['shown'], shown['restored']) == (1, 1)
    assert _road_trip(ANA)['files'] == list(FILES)
    assert 'hidden_count' not in _road_trip(ANA)


def test_only_the_owner_hides_songs(world):
    with pytest.raises(HTTPException) as viewer:
        _hide(BO, hide=[FILES[0]])
    assert viewer.value.status_code == 403
    with pytest.raises(HTTPException) as nothing:
        _hide(ANA)
    assert nothing.value.status_code == 400
    # An admin may change anyone's playlist.
    assert _hide(ADMIN_ID, 'admin', hide=[FILES[2]])['hidden'] == 1


def test_the_app_hides_by_track_id(world, monkeypatch):
    ids = {f: f't{n}' for n, f in enumerate(FILES)}
    by_id = {v: k for k, v in ids.items()}

    def track_path(track_id):
        if track_id not in by_id:
            raise HTTPException(status_code=404, detail='Track not found')
        return {'file': by_id[track_id]}, world.root / by_id[track_id]

    sync = SimpleNamespace(
        ids_for_paths=lambda paths: {p: ids[p] for p in paths if p in ids}
    )
    monkeypatch.setattr(mobile_routes, '_track_path', track_path)
    monkeypatch.setattr(mobile_routes, '_sync', lambda: sync)

    def call(handler, body=None, query=b''):
        request = _request(ANA, body=body)
        request.scope['query_string'] = query
        return asyncio.run(handler(request))

    hidden = call(
        mobile_routes.change_hidden_songs,
        {'name': 'Road Trip', 'hide': ['t1']},
    )
    assert hidden['track_ids'] == ['t0', 't2']
    assert hidden['hidden'] == 1
    listed = call(mobile_routes.hidden_songs, query=b'name=Road+Trip')
    assert [s['track_id'] for s in listed['songs']] == ['t1']
    shown = call(
        mobile_routes.change_hidden_songs,
        {'name': 'Road Trip', 'show': hidden['keys']},
    )
    assert shown['track_ids'] == ['t0', 't1', 't2']
    with pytest.raises(HTTPException) as unknown:
        call(
            mobile_routes.change_hidden_songs,
            {'name': 'Road Trip', 'hide': ['tnope']},
        )
    assert unknown.value.status_code == 404


def test_routes_are_classified():
    assert classify('GET', '/api/library/playlists/hidden') == USER
    assert classify('POST', '/api/library/playlists/hidden') == USER
    assert classify('GET', '/api/v1/playlists/hidden') == CLIENT
    assert classify('POST', '/api/v1/playlists/hidden') == CLIENT
