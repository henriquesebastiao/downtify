from types import SimpleNamespace

import pytest
from ai_test_support import opted_in_store
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from downtify.music_ai import routes


def test_catalog_reads_native_feed_without_scan_and_keeps_visibility(
    tmp_path, monkeypatch
):
    from downtify import api, mobile_routes

    database = opted_in_store(tmp_path / 'derived.db')
    monkeypatch.setattr(routes, 'store', lambda: database)
    monkeypatch.setattr(routes, 'owner', lambda _: 1)
    monkeypatch.setattr(
        api, 'allowed_entry_keys', lambda _, entries=None: {'allowed'}
    )
    monkeypatch.setattr(
        api,
        'library_context',
        lambda: SimpleNamespace(hidden_files={'hidden.mp3'}),
    )

    def forbidden():
        raise AssertionError(
            'An interactive recommendation must never scan the NAS'
        )

    monkeypatch.setattr(mobile_routes, '_refresh', forbidden)

    database.observe([
        {'id': 'visible', 'file': 'visible.mp3', 'fingerprint': 'v'},
        {'id': 'hidden', 'file': 'hidden.mp3', 'fingerprint': 'h'},
    ])
    from downtify import library_catalog

    monkeypatch.setattr(
        library_catalog, 'entry_content_key', lambda _: 'allowed'
    )

    def changes(*args, **kwargs):
        pytest.fail('Interactive reads must not consume the native full feed')

    monkeypatch.setattr(
        mobile_routes, '_sync', lambda: SimpleNamespace(changes=changes)
    )
    assert [row['id'] for row in routes.catalog(None)] == ['visible']
    with database.connect() as db:
        assert db.execute('SELECT count(*) FROM tracks').fetchone()[0] == 2


@pytest.fixture
def client(tmp_path, monkeypatch):
    database = opted_in_store(tmp_path / 'derived.db')
    rows = [
        {
            'id': 'one',
            'file': 'safe-one.mp3',
            'title': 'One',
            'artist': 'A',
            'duration': 100,
            'fingerprint': '1',
        },
        {
            'id': 'two',
            'file': 'safe-two.mp3',
            'title': 'Two',
            'artist': 'B',
            'duration': 100,
            'fingerprint': '2',
        },
    ]
    database.observe(rows)
    monkeypatch.setattr(routes, 'store', lambda: database)
    monkeypatch.setattr(routes, 'current_sources', lambda items: items)
    monkeypatch.setattr(
        routes,
        'catalog',
        lambda request: rows if routes.owner(request) else [],
    )
    monkeypatch.setattr(
        routes,
        'visible_rows',
        lambda request, ids: [
            row for row in routes.catalog(request) if row['id'] in ids
        ],
    )
    app = FastAPI()

    @app.middleware('http')
    async def identity(request, call_next):
        uid = int(request.headers.get('x-test-user', '0'))
        request.scope['state']['principal'] = SimpleNamespace(
            user_id=uid, is_admin=uid == 99
        )
        return await call_next(request)

    app.include_router(routes.router)
    with TestClient(app) as result:
        yield result, database


def test_anonymous_request_rejected(client):
    http, _ = client
    assert http.get('/api/v1/music-ai/capabilities').status_code == 401
    assert http.get('/api/v1/music-ai/playlists').status_code == 401
    assert (
        http.put(
            '/api/v1/music-ai/preferences', json={'daily': False}
        ).status_code
        == 401
    )


@pytest.fixture
def native_playlists(tmp_path, monkeypatch):
    from downtify import api
    from downtify.library_catalog import LibraryContext
    from downtify.playlist_catalog import ManualPlaylistOwners
    from downtify.playlist_shares import PlaylistShares

    root = tmp_path / 'native-library'
    root.mkdir()
    for name in ('safe-one.mp3', 'safe-two.mp3'):
        (root / name).write_bytes(b'synthetic audio fixture')
    ctx = LibraryContext(download_dir=root)
    owners = ManualPlaylistOwners(tmp_path / 'owners.db')
    shares = PlaylistShares(tmp_path / 'shares.db')
    monkeypatch.setattr(api, 'library_context', lambda: ctx)
    monkeypatch.setattr(api.state, 'manual_playlist_owners', owners)
    monkeypatch.setattr(api.state, 'playlist_shares', shares)
    for field in ('auth', 'playlist_catalog', 'playlist_hidden', 'likes'):
        monkeypatch.setattr(api.state, field, None)

    async def announce():
        pass

    monkeypatch.setattr(api, 'announce_playlists_changed', announce)
    return SimpleNamespace(root=root, owners=owners, shares=shares)


def test_playlist_cards_are_current_owned_and_visibility_filtered(
    client, monkeypatch
):
    import json

    from downtify.music_ai import playlists

    http, database = client
    monkeypatch.setattr(
        playlists,
        'period',
        lambda cadence, now=None: (
            '2026-11-06' if cadence == 'daily' else '2026-11-02'
        ),
    )
    with database.connect() as db:
        for owner, cadence, mood, key, ids in [
            (1, 'daily', 'calme', '2026-11-06', ['one', 'hidden']),
            (2, 'daily', 'fete', '2026-11-06', ['two']),
            (1, 'daily', 'energie', '2026-11-05', ['one']),
            (1, 'daily', 'detente', '2026-11-04', ['one']),
            (1, 'weekly', 'concentration', '2026-11-02', ['two']),
        ]:
            db.execute(
                'INSERT INTO playlists VALUES (?,?,?,?,?,?)',
                (owner, cadence, mood, key, json.dumps(ids), 1),
            )
    monkeypatch.setattr(
        playlists,
        'generate',
        lambda *a, **k: pytest.fail('Index must not generate a mix'),
    )
    response = http.get(
        '/api/v1/music-ai/playlists', headers={'x-test-user': '1'}
    )
    assert response.status_code == 200
    rows = response.json()['playlists']
    assert [
        (row['cadence'], row['mood'], row['count'], row['state'])
        for row in rows
    ] == [
        ('daily', 'calme', 1, 'ready'),
        ('daily', 'energie', 1, 'previous'),
        ('weekly', 'concentration', 1, 'ready'),
    ]
    assert not any(
        key in response.text
        for key in ('"owner"', '"ids"', 'safe-one.mp3', 'hidden')
    )
    database.set_preferences(-1, {'daily': False})
    assert [
        row['cadence']
        for row in http.get(
            '/api/v1/music-ai/playlists', headers={'x-test-user': '1'}
        ).json()['playlists']
    ] == ['weekly']
    monkeypatch.setattr(routes, 'catalog', lambda request: [])
    assert http.get(
        '/api/v1/music-ai/playlists', headers={'x-test-user': '1'}
    ).json() == {'playlists': []}


def test_disabled_playlist_index_does_not_read_the_catalog(
    client, monkeypatch
):
    http, database = client
    database.set_preferences(1, {'daily': False, 'weekly': False})
    monkeypatch.setattr(
        routes,
        'catalog',
        lambda request: pytest.fail(
            'Disabled modules must not read the catalog'
        ),
    )
    assert http.get(
        '/api/v1/music-ai/playlists', headers={'x-test-user': '1'}
    ).json() == {'playlists': []}


def test_users_cannot_change_global_features(client):
    http, database = client
    result = http.put(
        '/api/v1/music-ai/admin/features',
        headers={'x-test-user': '1'},
        json={'daily': False},
    )
    assert result.status_code == 403
    assert database.preferences(-1)['daily']


def test_preferences_are_scoped_to_authenticated_owner(client):
    http, database = client
    result = http.put(
        '/api/v1/music-ai/preferences',
        headers={'x-test-user': '1'},
        json={'daily': False},
    )
    assert result.status_code == 200
    assert not database.effective(1)['daily']
    assert database.effective(2)['daily']
    assert (
        http.put(
            '/api/v1/music-ai/preferences',
            headers={'x-test-user': '1'},
            json={'owner': 2, 'weekly': False},
        ).status_code
        == 422
    )


def test_disabled_features_refuse_processing(client):
    http, database = client
    database.set_preferences(-1, {'personalization': False})
    response = http.get(
        '/api/v1/music-ai/recommendations', headers={'x-test-user': '1'}
    )
    assert response.status_code == 409
    assert not database.history(1)


def test_model_missing_is_not_claimed_as_ready(client):
    http, _ = client
    response = http.get(
        '/api/v1/music-ai/recommendations', headers={'x-test-user': '1'}
    )
    assert response.status_code == 503


def test_recommendation_response_exposes_only_media_ids(client):
    http, database = client
    database.set_metadata('model', {'id': 'm', 'ready': True})
    database.put_analysis('one', '1', 'm', [1] + [0] * 511)
    database.put_analysis('two', '2', 'm', [1] + [0] * 511)
    response = http.get(
        '/api/v1/music-ai/recommendations?seed=one',
        headers={'x-test-user': '1'},
    )
    assert response.status_code == 200
    assert response.json()['tracks'][0]['id'] == 'two'
    assert 'file' not in response.json()['tracks'][0]
    assert (
        response.json()['tracks'][0]['stream_url']
        == '/api/v1/tracks/two/stream'
    )


def test_forgetting_one_profile_keeps_other_users_history(client):
    http, database = client
    database.listen(1, 'a', 'one', 90, 'complete')
    database.listen(2, 'a', 'two', 90, 'complete')
    assert (
        http.delete(
            '/api/v1/music-ai/profile', headers={'x-test-user': '1'}
        ).status_code
        == 200
    )
    assert not database.history(1)
    assert database.history(2)


def test_empty_library_has_no_model_dependency(client, monkeypatch):
    http, _ = client
    monkeypatch.setattr(routes, 'catalog', lambda request: [])
    response = http.get(
        '/api/v1/music-ai/recommendations', headers={'x-test-user': '1'}
    )
    assert response.status_code == 200
    assert response.json()['tracks'] == []


def test_save_rechecks_visibility_before_touching_native_playlists(
    client, monkeypatch
):
    from downtify import manual_playlists

    http, _ = client
    monkeypatch.setattr(
        manual_playlists,
        'copy_playlist',
        lambda *args: pytest.fail('Hidden selection must not be saved'),
    )
    response = http.post(
        '/api/v1/music-ai/playlists/save',
        headers={'x-test-user': '1'},
        json={'name': 'Stable', 'ids': ['hidden'], 'source': 'daily'},
    )
    assert response.status_code == 404


def test_save_uses_native_stable_copy_and_claims_owner(client, monkeypatch):
    from downtify import api, manual_playlists

    http, database = client
    written = []
    owner_arguments = []
    owners, shares = object(), object()
    monkeypatch.setattr(api, 'library_context', lambda: 'test-context')
    monkeypatch.setattr(api.state, 'manual_playlist_owners', owners)
    monkeypatch.setattr(api.state, 'playlist_shares', shares)

    def copy(ctx, files, name, *ownership):
        written.append((ctx, files, name))
        owner_arguments.append(ownership)
        return {'name': name, 'count': len(files)}

    async def announce():
        pass

    monkeypatch.setattr(manual_playlists, 'copy_playlist', copy)
    monkeypatch.setattr(api, 'invalidate_library_paths_cache', lambda: None)
    monkeypatch.setattr(api, 'announce_playlists_changed', announce)
    response = http.post(
        '/api/v1/music-ai/playlists/save',
        headers={'x-test-user': '1'},
        json={
            'name': 'Stable',
            'ids': ['two', 'one', 'two'],
            'source': 'daily',
        },
    )
    assert response.status_code == 200
    assert written == [
        ('test-context', ['safe-two.mp3', 'safe-one.mp3'], 'Stable')
    ]
    assert owner_arguments == [(owners, 1, shares)]
    database.forget(1)
    assert len(written) == 1


def test_saved_selection_is_private_owned_and_stable(client, native_playlists):
    from downtify import api
    from downtify.m3u import is_manual_m3u
    from downtify.playlist_shares import PRIVATE

    http, database = client
    world = native_playlists
    response = http.post(
        '/api/v1/music-ai/playlists/save',
        headers={'x-test-user': '1'},
        json={
            'name': 'Stable selection',
            'ids': ['two', 'one', 'two'],
            'source': 'daily',
        },
    )
    assert response.status_code == 200, response.text
    assert response.json() == {'name': 'Stable selection', 'count': 2}
    path = world.root / 'Playlists' / 'Stable selection.m3u'
    assert is_manual_m3u(path)
    assert world.owners.owner('Stable selection') == 1
    assert world.shares.visibility('Stable selection') == PRIVATE

    def request(uid):
        return Request({
            'type': 'http',
            'state': {
                'principal': SimpleNamespace(user_id=uid, is_admin=False)
            },
        })

    own = api.require_playlist_visible(
        'Stable selection', request(1), manage=True
    )
    assert own['manual']
    assert own['mine']
    assert own['files'] == ['safe-two.mp3', 'safe-one.mp3']
    with pytest.raises(HTTPException) as hidden:
        api.require_playlist_visible(
            'Stable selection', request(2), manage=True
        )
    assert hidden.value.status_code == 404
    saved_bytes = path.read_bytes()
    database.forget(1)
    assert path.read_bytes() == saved_bytes
    assert world.owners.owner('Stable selection') == 1


@pytest.mark.parametrize('which', ['owners', 'shares'])
@pytest.mark.parametrize('offline', [False, True])
def test_save_unavailable_native_state_leaves_no_file(
    client, native_playlists, monkeypatch, which, offline
):
    from downtify import api
    from downtify.playlist_shares import PUBLIC

    http, _ = client
    world = native_playlists
    native = getattr(world, which)
    original_path = native._path
    world.shares.set_visibility('Unavailable', PUBLIC)
    if offline:
        # A directory cannot be opened as SQLite: exercise real I/O failure,
        # native rollback and the API response rather than replacing a method.
        monkeypatch.setattr(native, '_path', str(world.root))
    else:
        field = (
            'manual_playlist_owners'
            if which == 'owners'
            else 'playlist_shares'
        )
        monkeypatch.setattr(api.state, field, None)
    response = http.post(
        '/api/v1/music-ai/playlists/save',
        headers={'x-test-user': '1'},
        json={'name': 'Unavailable', 'ids': ['one'], 'source': 'daily'},
    )
    assert response.status_code == 503, response.text
    assert 'temporarily unavailable' in response.json()['detail']
    assert not list(world.root.rglob('*.m3u'))
    if offline:
        monkeypatch.setattr(native, '_path', original_path)
    assert world.owners.owner('Unavailable') is None
    assert world.shares.visibility('Unavailable') == PUBLIC


def test_listen_revisions_erasure_and_visibility(client, monkeypatch):
    from downtify import api, mobile_routes

    http, database = client
    row = {
        'id': 'one',
        'file': 'safe-one.mp3',
        'duration': 100,
        'size': 1,
        'added': 1,
    }
    monkeypatch.setattr(
        mobile_routes,
        '_sync',
        lambda: SimpleNamespace(
            row_for=lambda identity: dict(row) if identity == 'one' else None
        ),
    )
    monkeypatch.setattr(
        api,
        'filter_paths_for_request',
        lambda files, request: files if routes.owner(request) == 1 else [],
    )
    event = {
        'event_id': 'play',
        'track_id': 'one',
        'seconds': 5,
        'sequence': 1,
        'outcome': 'pause',
        'generation': 0,
    }
    assert (
        http.post(
            '/api/v1/music-ai/listens',
            headers={'x-test-user': '2'},
            json=event,
        ).status_code
        == 404
    )
    assert not database.history(2)
    assert http.post(
        '/api/v1/music-ai/listens', headers={'x-test-user': '1'}, json=event
    ).json()['recorded']
    assert not http.post(
        '/api/v1/music-ai/listens', headers={'x-test-user': '1'}, json=event
    ).json()['recorded']
    newer = {**event, 'seconds': 25, 'sequence': 2, 'outcome': 'skip'}
    assert http.post(
        '/api/v1/music-ai/listens', headers={'x-test-user': '1'}, json=newer
    ).json()['recorded']
    assert not http.post(
        '/api/v1/music-ai/listens', headers={'x-test-user': '1'}, json=event
    ).json()['recorded']
    assert database.history(1)[0]['seconds'] == 25
    assert database.history(1)[0]['outcome'] == 'skip'
    http.delete(
        '/api/v1/music-ai/profile', headers={'x-test-user': '1'}
    ).raise_for_status()
    assert not http.post(
        '/api/v1/music-ai/listens',
        headers={'x-test-user': '1'},
        json={**newer, 'sequence': 3},
    ).json()['recorded']
    assert not database.history(1)
    revision = http.get(
        '/api/v1/music-ai/capabilities', headers={'x-test-user': '1'}
    ).json()['profile_revision']
    assert revision == 1
    assert http.post(
        '/api/v1/music-ai/listens',
        headers={'x-test-user': '1'},
        json={**event, 'event_id': 'fresh', 'generation': revision},
    ).json()['recorded']


def test_disabled_external_beta_never_calls_provider(client, monkeypatch):
    from downtify import api

    http, _ = client

    async def forbidden(*args, **kwargs):
        pytest.fail('Disabled beta must not contact the provider')

    monkeypatch.setattr(api, '_external_similar_tracks', forbidden)
    assert (
        http.get(
            '/api/v1/music-ai/external-similar?artist=A&track=One',
            headers={'x-test-user': '1'},
        ).status_code
        == 409
    )


def test_similar_requires_specific_version_when_names_are_ambiguous(
    client, monkeypatch
):
    http, database = client
    rows = [
        {
            'id': 'one',
            'file': 'first.flac',
            'title': 'Song',
            'artist': 'A',
            'fingerprint': '1',
        },
        {
            'id': 'two',
            'file': 'second.flac',
            'title': 'Song',
            'artist': 'A',
            'fingerprint': '2',
        },
        {
            'id': 'third',
            'file': 'third.flac',
            'title': 'Different',
            'artist': 'B',
            'fingerprint': '3',
        },
    ]
    database.observe(rows)
    database.set_metadata('model', {'id': 'm', 'ready': True})
    for row in rows:
        database.put_analysis(
            row['id'], row['fingerprint'], 'm', [1] + [0] * 511
        )
    monkeypatch.setattr(routes, 'catalog', lambda request: rows)
    headers = {'x-test-user': '1'}
    assert (
        http.get(
            '/api/v1/music-ai/similar?artist=A&track=Song', headers=headers
        ).status_code
        == 409
    )
    found = http.get('/api/v1/music-ai/similar?seed=one', headers=headers)
    assert found.status_code == 200
    assert [row['song_id'] for row in found.json()['tracks']] == ['third']


def test_disable_during_ranking_rejects_late_response(client, monkeypatch):
    http, database = client
    database.set_metadata('model', {'id': 'm', 'ready': True})

    def stop(*args, **kwargs):
        database.set_preferences(1, {'personalization': False})
        return []

    monkeypatch.setattr(routes, 'rank', stop)
    assert (
        http.get(
            '/api/v1/music-ai/recommendations', headers={'x-test-user': '1'}
        ).status_code
        == 409
    )


def test_legacy_endpoint_uses_local_engine_and_obeys_switches(
    client, monkeypatch
):
    from downtify import api

    http, database = client
    http.app.include_router(api.router)
    monkeypatch.setenv('DOWNTIFY_MUSIC_AI_ENABLED', '1')
    monkeypatch.setattr(
        api.providers,
        'youtube_similar_tracks',
        lambda *args, **kwargs: pytest.fail('Legacy client must stay local'),
    )
    database.set_preferences(
        1, {'similarity': False, 'personalization': False}
    )
    assert (
        http.get(
            '/api/similar/tracks?artist=A&track=One',
            headers={'x-test-user': '1'},
        ).status_code
        == 409
    )
    assert http.post(
        '/api/discover/listens',
        headers={'x-test-user': '1'},
        json={'artist': 'A'},
    ).json() == {'recorded': False}


def test_admin_profile_erasure_is_limited_to_own_native_history(
    client, monkeypatch
):
    from downtify import api

    http, _ = client
    cleared = []
    monkeypatch.setattr(
        api.state,
        'discover',
        SimpleNamespace(clear_listens=cleared.append),
    )
    assert (
        http.delete(
            '/api/v1/music-ai/profile', headers={'x-test-user': '99'}
        ).status_code
        == 200
    )
    assert cleared == [99]


def test_analysis_admin_controls_are_scoped_and_erasure_pauses(client):
    http, database = client
    for method, path in [
        ('get', '/admin/analyses'),
        ('delete', '/admin/analyses'),
        ('post', '/admin/analysis/retry'),
    ]:
        assert (
            getattr(http, method)(
                '/api/v1/music-ai' + path, headers={'x-test-user': '1'}
            ).status_code
            == 403
        )
    headers = {'x-test-user': '99'}
    http.delete(
        '/api/v1/music-ai/admin/analyses', headers=headers
    ).raise_for_status()
    status = http.get(
        '/api/v1/music-ai/admin/analyses', headers=headers
    ).json()
    assert status['paused']
    assert status['analyzed'] == 0
    assert (
        http.post(
            '/api/v1/music-ai/admin/analysis/retry', headers=headers
        ).status_code
        == 409
    )
    http.post(
        '/api/v1/music-ai/admin/analysis', headers=headers
    ).raise_for_status()
    assert not database.metadata('analysis_paused')


def test_expired_dj_heartbeat_is_not_advertised_as_available(client):
    import time

    http, database = client
    database.set_metadata(
        'dj', {'ready': True, 'prepared_ready': True, 'seen': time.time() - 21}
    )
    status = http.get(
        '/api/v1/music-ai/capabilities', headers={'x-test-user': '1'}
    ).json()['dj']
    assert not status['ready']
    assert not status['prepared_ready']
    assert status['state'] == 'unavailable'


def test_mix_refresh_authenticated_idempotent_and_metadata_only(
    client, monkeypatch
):
    from uuid import uuid4

    http, database = client

    def forbidden(*args, **kwargs):
        pytest.fail(
            'Refresh must not touch library paths or perform inference'
        )

    monkeypatch.setattr(routes, 'catalog', forbidden)
    monkeypatch.setattr(routes, 'visible_rows', forbidden)
    request = {'request_id': str(uuid4())}
    url = '/api/v1/music-ai/playlists/refresh'
    assert http.post(url, json=request).status_code == 401
    assert (
        http.post(
            url, json={'request_id': 'invalid'}, headers={'x-test-user': '1'}
        ).status_code
        == 422
    )
    first = http.post(url, json=request, headers={'x-test-user': '1'})
    assert first.status_code == 200
    assert first.json()['accepted'] is True
    assert (
        http.post(url, json=request, headers={'x-test-user': '1'}).json()
        == first.json()
    )
    assert database.metadata('selection_revision:2', 0) == 0
    database.set_preferences(-1, {'daily': False, 'weekly': False})
    assert (
        http.post(
            url,
            json={'request_id': str(uuid4())},
            headers={'x-test-user': '1'},
        ).status_code
        == 403
    )
