"""What the browser may keep: repeat reads of large listings cost nothing,
the hashed frontend files are kept for good and ``index.html`` is always
checked, so an upgrade reaches the browser without a forced reload."""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.testclient import TestClient

import main
from downtify import api
from downtify.http_etag import JsonETagMiddleware
from downtify.library_paths_cache import invalidate_library_paths_cache

BIG = list(range(2000))


@pytest.fixture
def listing():
    data = {'rows': BIG, 'status': 200}

    async def tracks(_request):
        return JSONResponse(data['rows'], status_code=data['status'])

    async def other(_request):
        return JSONResponse(BIG)

    app = Starlette(
        routes=[
            Route('/tracks', tracks, methods=['GET', 'POST']),
            Route('/other', other),
        ]
    )
    app.add_middleware(JsonETagMiddleware, paths=('/tracks',))
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=4)
    return TestClient(app), data


def test_a_listing_says_how_to_keep_it(listing):
    client, _data = listing
    response = client.get('/tracks')
    assert response.status_code == 200
    assert response.json() == BIG
    assert response.headers['etag'].startswith('"')
    assert response.headers['cache-control'] == 'private, no-cache'
    assert response.headers['content-encoding'] == 'gzip'


def test_an_unchanged_listing_answers_304_with_no_body(listing):
    client, _data = listing
    etag = client.get('/tracks').headers['etag']

    response = client.get('/tracks', headers={'If-None-Match': etag})

    assert response.status_code == 304
    assert not response.content
    assert response.headers['etag'] == etag
    assert response.headers['cache-control'] == 'private, no-cache'


def test_a_changed_listing_is_sent_again(listing):
    client, data = listing
    etag = client.get('/tracks').headers['etag']
    data['rows'] = [1, 2, 3]

    response = client.get('/tracks', headers={'If-None-Match': etag})

    assert response.status_code == 200
    assert response.json() == [1, 2, 3]
    assert response.headers['etag'] != etag


def test_a_failed_read_is_never_kept(listing):
    client, data = listing
    data['status'] = 401
    response = client.get('/tracks')
    assert response.status_code == 401
    assert 'etag' not in response.headers
    assert 'cache-control' not in response.headers


@pytest.mark.parametrize(
    ('method', 'path'), [('post', '/tracks'), ('get', '/other')]
)
def test_other_requests_are_left_alone(listing, method, path):
    client, _data = listing
    response = getattr(client, method)(path)
    assert response.status_code == 200
    assert 'etag' not in response.headers


@pytest.fixture
def spa(tmp_path):
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets' / 'index-abc123.js').write_text('let a = 1')
    (tmp_path / 'index.html').write_text('<html></html>')
    (tmp_path / 'icon.png').write_bytes(b'\x89PNG')
    app = Starlette(
        routes=[Mount('/', main.SPAStaticFiles(directory=tmp_path, html=True))]
    )
    return TestClient(app)


def test_hashed_frontend_files_are_kept_for_good(spa):
    response = spa.get('/assets/index-abc123.js')
    assert response.status_code == 200
    assert response.headers['cache-control'] == main.IMMUTABLE_ASSET


@pytest.mark.parametrize('path', ['/', '/library/albums'])
def test_the_page_itself_is_always_checked(spa, path):
    response = spa.get(path)
    assert response.status_code == 200
    assert response.text == '<html></html>'
    assert response.headers['cache-control'] == 'no-cache'


def test_a_missing_hashed_file_is_not_kept(spa):
    """An old page asking for a file an upgrade removed gets the page; that
    answer must not be remembered as the file."""

    response = spa.get('/assets/index-gone.js')
    assert response.headers['cache-control'] == 'no-cache'


def test_other_public_files_keep_their_default(spa):
    response = spa.get('/icon.png')
    assert response.status_code == 200
    assert 'cache-control' not in response.headers


@pytest.fixture
def accounts(tmp_path, monkeypatch):
    """The real app with accounts on: an admin, a user and two playlists
    holding the same song, one private and one public."""

    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html></html>')
    downloads = tmp_path / 'downloads'
    (downloads / 'Playlists').mkdir(parents=True)
    (downloads / 'Shown.mp3').write_bytes(b'shown')
    (downloads / 'Hidden.mp3').write_bytes(b'hidden')
    for name in ('Secret plans', 'Open'):
        (downloads / 'Playlists' / f'{name}.m3u').write_text(
            '#EXTM3U\n../Shown.mp3\n../Hidden.mp3\n', encoding='utf-8'
        )
    invalidate_library_paths_cache()
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', downloads)
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    for name in (
        'auth',
        'activity',
        'identity',
        'downloader',
        'settings',
        'cover_thumbs',
        'cover_cache',
        'metadata_cache',
        'track_index',
        'playlist_catalog',
        'playlist_shares',
        'library_visibility',
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
    hidden = admin.post(
        '/api/library/visibility',
        json={
            'action': 'hide',
            'items': [{'kind': 'track', 'file': 'Hidden.mp3'}],
        },
    )
    assert hidden.status_code == 200
    for owned, spotify_id in (('Secret plans', 'sp1'), ('Open', 'sp2')):
        api.state.playlist_catalog.ensure_playlist(
            owned, spotify_id=spotify_id, user_id=1
        )
    invalidate_library_paths_cache()
    public = admin.put(
        '/api/library/playlists/visibility',
        json={'name': 'Open', 'visibility': 'public'},
    )
    assert public.status_code == 200
    ana = TestClient(app, base_url='http://testserver')
    assert _sign_in(ana, 'ana', 'password-2').status_code == 200
    anonymous = TestClient(app, base_url='http://testserver')
    return admin, ana, anonymous


def _sign_in(client, username, password):
    return client.post(
        '/api/auth/login', json={'username': username, 'password': password}
    )


def _files(response):
    return sorted(row['file'] for row in response.json())


def test_a_signed_in_browser_gets_a_304_for_its_own_listing(accounts):
    admin, _ana, _anonymous = accounts
    first = admin.get('/tracks')
    assert _files(first) == ['Hidden.mp3', 'Shown.mp3']

    again = admin.get(
        '/tracks', headers={'If-None-Match': first.headers['etag']}
    )

    assert again.status_code == 304
    assert not again.content


def test_another_account_never_gets_a_304_for_what_it_may_not_see(accounts):
    """Same browser, next account: the tag kept from the admin's listing,
    with a song hidden from users in it, must not validate."""

    admin, ana, _anonymous = accounts
    tag = admin.get('/tracks').headers['etag']

    response = ana.get('/tracks', headers={'If-None-Match': tag})

    assert response.status_code == 200
    assert _files(response) == ['Shown.mp3']


def test_a_signed_out_browser_gets_nothing_for_a_tag_it_kept(accounts):
    admin, _ana, anonymous = accounts
    for path in ('/tracks', '/playlists', '/api/library/albums'):
        tag = admin.get(path).headers['etag']
        response = anonymous.get(path, headers={'If-None-Match': tag})
        assert response.status_code == 401
        assert 'etag' not in response.headers


def test_signing_out_ends_the_304s(accounts):
    admin, _ana, _anonymous = accounts
    tag = admin.get('/tracks').headers['etag']

    admin.post('/api/auth/logout')
    response = admin.get('/tracks', headers={'If-None-Match': tag})

    assert response.status_code == 401


def test_a_playlist_row_hides_songs_and_names_of_other_peoples_playlists(
    accounts,
):
    """The rows come from the shared snapshot now, which knows about every
    playlist: a user must not learn the name of a private one from them."""

    admin, ana, _anonymous = accounts
    listing = admin.get('/tracks?playlist=Open')
    assert _files(listing) == ['Hidden.mp3', 'Shown.mp3']
    seen = {
        name for row in listing.json() for name in row.get('playlists', [])
    }
    assert 'Secret plans' in seen

    response = ana.get('/tracks?playlist=Open')

    assert response.status_code == 200
    assert _files(response) == ['Shown.mp3']
    assert 'Secret plans' not in response.text


def test_a_playlist_a_user_may_not_open_lists_nothing(accounts):
    _admin, ana, _anonymous = accounts
    response = ana.get('/tracks?playlist=Secret%20plans')
    assert response.status_code == 200
    assert response.json() == []
