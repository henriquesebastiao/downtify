"""Saved links: playlist and album links an account keeps to stream (#731).

A bookmark per account, nothing more: saving a link downloads nothing and
writes no M3U, Navidrome playlist or catalog row. Offline - the links are
only parsed, never resolved. See ``downtify/saved_links.py``.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.testclient import TestClient

import main
from downtify import account_routes, api, saved_links
from downtify.auth import Principal
from downtify.saved_links import (
    MAX_NAME_LENGTH,
    LinkTarget,
    SavedLinks,
    SavedLinksFull,
    clean_cover,
    clean_name,
    saved_link_target,
)

ANA = 2
BO = 3

SPOTIFY_ID = '37i9dQZF1DXcBWIGoYBM5M'
SPOTIFY = f'https://open.spotify.com/playlist/{SPOTIFY_ID}'
ALBUM_ID = '1DFixLWuPkv3KT3TnV35m3'
YTM_PLAYLIST = 'PLx6XKQDAhfWZ4vxtvdmpkDKUnR2omdAdr'
YTM_ALBUM = 'MPREb_9sF6pOQWnfK'
YTM_AUDIO_PLAYLIST = 'OLAK5uy_kVa5Jt1w6mNE3P0WZ8DqT1Kb0Gx3M9vXs'


# ── Which links, under which URL ───────────────────────────────────────


@pytest.mark.parametrize(
    ('pasted', 'source', 'kind', 'canonical'),
    [
        (f'{SPOTIFY}?si=abc123&pt=x', 'spotify', 'playlist', SPOTIFY),
        (
            f'https://open.spotify.com/intl-de/album/{ALBUM_ID}?si=1',
            'spotify',
            'album',
            f'https://open.spotify.com/album/{ALBUM_ID}',
        ),
        (f'spotify:playlist:{SPOTIFY_ID}', 'spotify', 'playlist', SPOTIFY),
        (
            f'https://music.youtube.com/playlist?list={YTM_PLAYLIST}&si=Zz',
            'youtube',
            'playlist',
            f'https://music.youtube.com/playlist?list={YTM_PLAYLIST}',
        ),
        (
            f'https://www.youtube.com/playlist?list={YTM_PLAYLIST}',
            'youtube',
            'playlist',
            f'https://music.youtube.com/playlist?list={YTM_PLAYLIST}',
        ),
        (
            f'https://music.youtube.com/browse/{YTM_ALBUM}',
            'youtube',
            'album',
            f'https://music.youtube.com/browse/{YTM_ALBUM}',
        ),
        (
            f'https://music.youtube.com/playlist?list={YTM_AUDIO_PLAYLIST}',
            'youtube',
            'album',
            f'https://music.youtube.com/playlist?list={YTM_AUDIO_PLAYLIST}',
        ),
        (
            'https://www.deezer.com/fr/playlist/908622995?utm_source=x',
            'deezer',
            'playlist',
            'https://www.deezer.com/playlist/908622995',
        ),
        (
            'https://deezer.com/album/302127',
            'deezer',
            'album',
            'https://www.deezer.com/album/302127',
        ),
    ],
)
def test_a_link_is_saved_under_its_canonical_url(
    pasted, source, kind, canonical
):
    target = saved_link_target(pasted)

    assert target is not None
    assert (target.source, target.kind, target.url) == (
        source,
        kind,
        canonical,
    )
    # The canonical URL reads back as the same link.
    assert saved_link_target(target.url) == target


@pytest.mark.parametrize(
    'url',
    [
        '',
        None,
        'not a link',
        f'https://open.spotify.com/track/{SPOTIFY_ID}',
        f'https://open.spotify.com/artist/{SPOTIFY_ID}',
        'https://www.deezer.com/track/3135556',
        'https://music.youtube.com/watch?v=dQw4w9WgXcQ&list=PLabc',
        'https://music.youtube.com/channel/UCabcdefghijklmnop',
        'https://soundcloud.com/artist/track',
        'https://example.com/playlist/123',
        'javascript:alert(1)',
        'spotify:playlist:<script>',
        f'{SPOTIFY}?{"x" * 3000}',
    ],
)
def test_only_playlist_and_album_links_the_app_reads_are_saved(url):
    assert saved_link_target(url) is None


def test_a_name_is_kept_on_one_line_and_bounded():
    assert clean_name('  Late \n night\tmix  ') == 'Late night mix'
    assert len(clean_name('x' * 5000)) == MAX_NAME_LENGTH
    assert not clean_name(None)


@pytest.mark.parametrize(
    ('cover', 'kept'),
    [
        ('https://i.scdn.co/image/ab67616d0000b273', True),
        ('http://i.scdn.co/image/ab67', False),
        ('javascript:alert(1)', False),
        ('data:image/png;base64,AAAA', False),
        ('//i.scdn.co/image/ab67', False),
        ('/cover?file=a.mp3', False),
        ('https://exa mple.com/x.jpg', False),
        ('https:///x.jpg', False),
        ('https://e.com/' + 'x' * 3000, False),
        (None, False),
    ],
)
def test_only_an_https_cover_is_kept(cover, kept):
    assert clean_cover(cover) == (cover if kept else '')


# ── The store, on SQLite and (with TEST_DATABASE_URL) PostgreSQL ───────


def _target(n: int) -> LinkTarget:
    found = saved_link_target(f'https://www.deezer.com/playlist/{n}')
    assert found is not None
    return found


def test_links_are_listed_newest_first(backend_db):
    store = SavedLinks(backend_db)
    for n in (1, 2, 3):
        store.save(ANA, _target(n), f'List {n}')

    assert [link['name'] for link in store.list(ANA)] == [
        'List 3',
        'List 2',
        'List 1',
    ]
    first = store.list(ANA)[0]
    assert first['url'] == 'https://www.deezer.com/playlist/3'
    assert (first['source'], first['kind']) == ('deezer', 'playlist')
    assert first['saved_at']


def test_saving_again_refreshes_the_name_and_keeps_the_place(backend_db):
    store = SavedLinks(backend_db)
    store.save(ANA, _target(1), 'Old name', 'https://e.com/a.jpg')
    store.save(ANA, _target(2), 'Other')

    again = store.save(ANA, _target(1), 'New name', 'javascript:x')

    assert again['name'] == 'New name'
    assert not again['cover']
    assert [link['name'] for link in store.list(ANA)] == [
        'Other',
        'New name',
    ]


def test_each_account_sees_only_its_own_links(backend_db):
    store = SavedLinks(backend_db)
    store.save(ANA, _target(1), 'Ana')
    store.save(BO, _target(1), 'Bo')
    store.save(BO, _target(2), 'Bo too')

    assert [link['name'] for link in store.list(ANA)] == ['Ana']
    assert store.get(ANA, _target(2).url) is None
    assert store.remove(ANA, _target(1).url) is True
    assert store.remove(ANA, _target(1).url) is False
    assert store.list(ANA) == []
    assert len(store.list(BO)) == 2


def test_a_deleted_account_takes_its_links_along(backend_db):
    store = SavedLinks(backend_db)
    store.save(ANA, _target(1), 'Ana')
    store.save(BO, _target(1), 'Bo')

    store.remove_user(ANA)

    assert store.list(ANA) == []
    assert [link['name'] for link in store.list(BO)] == ['Bo']


def test_an_account_keeps_a_bounded_number_of_links(backend_db, monkeypatch):
    monkeypatch.setattr(saved_links, 'MAX_SAVED_LINKS', 2)
    store = SavedLinks(backend_db)
    store.save(ANA, _target(1), 'One')
    store.save(ANA, _target(2), 'Two')

    with pytest.raises(SavedLinksFull):
        store.save(ANA, _target(3), 'Three')
    # One already saved can still be saved again, and others are free.
    store.save(ANA, _target(1), 'One again')
    store.save(BO, _target(3), 'Three')

    assert len(store.list(ANA)) == 2


# ── The endpoints ──────────────────────────────────────────────────────


def _request(user_id: int, body: Any = None) -> Request:
    scope: dict[str, Any] = {
        'type': 'http',
        'headers': [],
        'query_string': b'',
        'state': {
            'principal': Principal(
                'device', 'client', '', user_id, f'u{user_id}', 'user'
            )
        },
    }
    raw = json.dumps(body).encode() if body is not None else b''

    async def receive() -> dict[str, Any]:
        return {'type': 'http.request', 'body': raw, 'more_body': False}

    return Request(scope, receive)


def _save(user_id: int, **body: Any) -> dict[str, Any]:
    return asyncio.run(api.save_link_endpoint(_request(user_id, body)))


def _list(user_id: int, url: str = '') -> list[dict[str, Any]]:
    return asyncio.run(
        api.list_saved_links_endpoint(_request(user_id), url=url)
    )['links']


def _remove(user_id: int, url: str) -> dict[str, Any]:
    return asyncio.run(
        api.remove_saved_link_endpoint(_request(user_id), url=url)
    )


def _status(call) -> int:
    with pytest.raises(HTTPException) as error:
        call()
    return error.value.status_code


@pytest.fixture
def store(tmp_path, monkeypatch):
    found = SavedLinks(tmp_path / 'lib.db')
    monkeypatch.setattr(api.state, 'saved_links', found)
    return found


def test_saving_a_link_from_the_link_page(store):
    saved = _save(
        ANA,
        url=f'{SPOTIFY}?si=abc',
        name='Today\u2019s Top Hits',
        cover='https://i.scdn.co/image/ab67',
    )

    assert saved['url'] == SPOTIFY
    assert saved['source'] == 'spotify'
    assert saved['kind'] == 'playlist'
    assert saved['cover'] == 'https://i.scdn.co/image/ab67'
    assert _list(ANA) == [saved]
    # The link page asks about its own link, pasted in any form.
    assert _list(ANA, url=f'{SPOTIFY}?si=other') == [saved]
    assert _list(BO, url=SPOTIFY) == []


def test_saving_twice_keeps_one_link(store):
    _save(ANA, url=f'{SPOTIFY}?si=one', name='Hits')
    _save(ANA, url=f'{SPOTIFY}?si=two', name='Hits')

    assert len(_list(ANA)) == 1


def test_removing_a_link(store):
    _save(ANA, url=SPOTIFY, name='Hits')
    _save(BO, url=SPOTIFY, name='Hits')

    assert _remove(ANA, f'{SPOTIFY}?si=x') == {
        'url': SPOTIFY,
        'removed': True,
    }
    assert _list(ANA) == []
    assert len(_list(BO)) == 1
    assert _remove(ANA, SPOTIFY)['removed'] is False


def test_links_the_app_cannot_stream_are_refused(store):
    track = f'https://open.spotify.com/track/{SPOTIFY_ID}'

    assert _status(lambda: _save(ANA, url='https://example.com/x')) == 400
    assert _status(lambda: _save(ANA, url=track, name='Song')) == 400
    assert _status(lambda: _save(ANA, name='No link')) == 400
    assert _status(lambda: _save(ANA, url=SPOTIFY, name=['x'])) == 400
    assert _status(lambda: _list(ANA, url='https://example.com')) == 400
    assert _status(lambda: _remove(ANA, track)) == 400
    assert store.list(ANA) == []


def test_saved_links_need_a_signed_in_account(store):
    assert _status(lambda: _save(0, url=SPOTIFY, name='Hits')) == 401
    assert _status(lambda: _list(0)) == 401
    assert _status(lambda: _remove(0, SPOTIFY)) == 401


def test_a_full_list_is_refused_with_a_clear_error(store, monkeypatch):
    monkeypatch.setattr(saved_links, 'MAX_SAVED_LINKS', 1)
    _save(ANA, url=SPOTIFY, name='Hits')

    with pytest.raises(HTTPException) as error:
        _save(ANA, url='https://www.deezer.com/album/302127', name='Album')

    assert error.value.status_code == 409
    assert 'Remove one first' in error.value.detail


def test_deleting_an_account_forgets_its_saved_links(store, monkeypatch):
    for name in (
        'track_owners',
        'storage_quotas',
        'likes',
        'manual_playlist_owners',
        'playlist_shares',
        'podcasts',
        'discover',
        'traffic',
        'monitor_db',
    ):
        monkeypatch.setattr(api.state, name, None)
    store.save(ANA, _target(1), 'Ana')
    store.save(BO, _target(1), 'Bo')

    account_routes._forget_user_library(ANA)

    assert store.list(ANA) == []
    assert len(store.list(BO)) == 1


# ── Through the real app: sign-in, scopes and nothing downloaded ───────


@pytest.fixture
def accounts(tmp_path, monkeypatch):
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html></html>')
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', downloads)
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    for name in (
        'auth',
        'activity',
        'identity',
        'downloader',
        'settings',
        'track_index',
        'playlist_catalog',
        'playlist_shares',
        'library_visibility',
        'saved_links',
    ):
        monkeypatch.setattr(api.state, name, getattr(api.state, name, None))
    (tmp_path / 'data').mkdir()
    app = main.build_app()
    main._open_library_stores(tmp_path / 'data' / 'downtify_monitor.db')
    admin = TestClient(app, base_url='http://testserver')
    assert _sign_in(admin, 'admin', 'downtify').status_code == 200
    created = admin.post(
        '/api/users', json={'username': 'ana', 'password': 'password-2'}
    )
    assert created.status_code == 200
    ana = TestClient(app, base_url='http://testserver')
    assert _sign_in(ana, 'ana', 'password-2').status_code == 200
    anonymous = TestClient(app, base_url='http://testserver')
    return SimpleNamespace(
        admin=admin, ana=ana, anonymous=anonymous, downloads=downloads
    )


def _sign_in(client: TestClient, username: str, password: str) -> Any:
    return client.post(
        '/api/auth/login', json={'username': username, 'password': password}
    )


def test_a_user_saves_a_link_and_nothing_is_downloaded(accounts):
    body = {'url': f'{SPOTIFY}?si=abc', 'name': 'Hits', 'cover': ''}

    assert accounts.anonymous.get('/api/library/saved-links').status_code == (
        401
    )
    saved = accounts.ana.put('/api/library/saved-links', json=body)

    assert saved.status_code == 200
    assert saved.json()['url'] == SPOTIFY
    listed = accounts.ana.get('/api/library/saved-links').json()
    assert [link['url'] for link in listed['links']] == [SPOTIFY]
    assert listed['limit'] == saved_links.MAX_SAVED_LINKS
    # Private: the admin has none of their own and doesn't see Ana's.
    assert accounts.admin.get('/api/library/saved-links').json()['links'] == []
    # A bookmark only: no file, M3U or playlist appeared.
    assert list(accounts.downloads.rglob('*')) == []
    assert accounts.ana.get('/playlists').json() == []
    removed = accounts.ana.delete(
        '/api/library/saved-links', params={'url': SPOTIFY}
    )
    assert removed.json() == {'url': SPOTIFY, 'removed': True}
    assert accounts.ana.get('/api/library/saved-links').json()['links'] == []
