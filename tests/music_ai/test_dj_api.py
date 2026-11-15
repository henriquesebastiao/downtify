import time
from types import SimpleNamespace

import pytest
from ai_test_support import opted_in_store
from fastapi import FastAPI
from fastapi.testclient import TestClient

from downtify.music_ai import routes
from downtify.music_ai.dj_store import DjStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    from downtify import api, library_catalog, mobile_routes

    database = opted_in_store(tmp_path / 'state' / 'derived.db')
    database.set_preferences(-1, {'dj_prepared': True})
    for owner in (1, 2):
        database.set_preferences(owner, {'dj_prepared': True})
    database.set_metadata('dj', {'prepared_ready': True, 'seen': time.time()})
    music = tmp_path / 'originals'
    music.mkdir()
    rows = {}
    for track in ('one', 'two'):
        (music / (track + '.wav')).write_bytes(b'original-content')
        rows[track] = {
            'id': track,
            'title': track,
            'artist': 'Artist',
            'file': track + '.wav',
            'size': 16,
        }
    access = {'allowed': None, 'hidden': set(), 'hidden_resolved': set()}
    monkeypatch.setattr(routes, 'store', lambda: database)
    monkeypatch.setattr(
        api, 'allowed_entry_keys', lambda _, entries=None: access['allowed']
    )
    monkeypatch.setattr(
        api,
        'library_context',
        lambda: SimpleNamespace(
            hidden_files=access['hidden'],
            hidden_resolved=access['hidden_resolved'],
        ),
    )
    monkeypatch.setattr(
        mobile_routes,
        '_sync',
        lambda: SimpleNamespace(row_for=rows.get),
    )
    monkeypatch.setattr(
        library_catalog,
        'resolve_library_file',
        lambda file, context: music / file,
    )
    app = FastAPI()

    @app.middleware('http')
    async def identity(request, call_next):
        uid = int(request.headers.get('x-test-user', '0'))
        request.state.principal = SimpleNamespace(
            user_id=uid, is_admin=request.headers.get('x-test-admin') == 'yes'
        )
        return await call_next(request)

    app.include_router(routes.router)
    with TestClient(app) as http:
        yield http, database, access, music


def create(http, **changes):
    return http.post(
        '/api/v1/music-ai/dj/sessions',
        headers={'x-test-user': '1'},
        json={
            'request_id': 'retry',
            'theme': 'fete',
            'ids': ['one', 'two'],
            **changes,
        },
    )


def test_dj_requires_auth_and_a_live_enabled_engine(client):
    http, database, _, _ = client
    assert http.get('/api/v1/music-ai/dj/sessions').status_code == 401
    database.set_metadata(
        'dj', {'prepared_ready': True, 'seen': time.time() - 21}
    )
    assert create(http).status_code == 503
    database.set_preferences(-1, {'dj_prepared': False})
    assert create(http).status_code == 409
    assert DjStore(database).list(1) == []


def test_light_status_is_private_cached_and_bounded(client):
    http, database, _, _ = client
    identity = create(http).json()['id']
    summary = http.get(
        '/api/v1/music-ai/dj/sessions?summary=true',
        headers={'x-test-user': '1'},
    ).json()['sessions'][0]
    assert summary['tracks'] == []
    assert summary['timeline'] == []
    assert summary['track_count'] == 2
    url = f'/api/v1/music-ai/dj/sessions/{identity}?view=playback&position=0'
    response = http.get(url, headers={'x-test-user': '1'})
    assert response.status_code == 200
    assert len(response.json()['tracks']) <= 4
    assert (
        http.get(
            url,
            headers={
                'x-test-user': '1',
                'If-None-Match': response.headers['ETag'],
            },
        ).status_code
        == 304
    )
    assert (
        http.get(
            url,
            headers={
                'x-test-user': '2',
                'If-None-Match': response.headers['ETag'],
            },
        ).status_code
        == 404
    )
    assert (
        http.get(
            url.replace('position=0', 'position=nan'),
            headers={'x-test-user': '1'},
        ).status_code
        == 422
    )


def test_trial_is_explicit_and_does_not_make_a_renderer_qualified(client):
    http, database, _, _ = client
    for uid in (-1, 1):
        database.set_preferences(uid, {'dj_interactive': True})
    database.set_metadata(
        'dj',
        {
            'prepared_ready': True,
            'interactive_ready': False,
            'seen': time.time(),
        },
    )
    assert create(http, mode='interactive').status_code == 503
    assert create(http, mode='interactive', trial=True).status_code == 409
    for uid in (-1, 1):
        database.set_preferences(uid, {'dj_trial': True})
    response = create(http, mode='interactive', trial=True)
    assert response.status_code == 202
    assert DjStore(database).get(1, response.json()['id'])['trial'] is True
    assert database.metadata('dj')['interactive_ready'] is False


def test_continuation_accepts_new_tracks_but_never_revives_a_cancelled_render(
    client,
):
    http, database, _, _ = client
    for uid in (-1, 1):
        database.set_preferences(
            uid, {'dj_interactive': True, 'dj_trial': True}
        )
    response = create(http, mode='interactive', continuous=True, trial=True)
    assert response.status_code == 202
    dj = DjStore(database)
    job = dj.claim()
    sources = {
        'third': {
            'path': 'private-fixture',
            'source_version': [1],
            'fingerprint': 'f',
        }
    }
    assert dj.replenish(1, job['id'], ['third'], sources)
    assert dj.get(1, job['id'])['ids'] == ['one', 'two', 'third']
    assert not dj.replenish(
        2, job['id'], ['fourth'], {'fourth': sources['third']}
    )
    dj.stop(1, job['id'])
    assert not dj.replenish(
        1, job['id'], ['fourth'], {'fourth': sources['third']}
    )


def test_requests_are_idempotent_and_never_expose_snapshots(client):
    http, database, _, music = client
    first = create(http)
    assert first.status_code == 202
    assert first.json()['id'] == create(http).json()['id']
    assert len(DjStore(database).list(1)) == 1
    assert 'path' not in first.text
    assert str(music) not in first.text
    assert 'owner' not in first.json()
    assert create(http, theme='calme').status_code == 422
    assert create(http, path='/caller-controlled').status_code == 422


def test_automatic_dj_works_without_recommender_and_retry_keeps_original_selection(
    client, monkeypatch
):
    from downtify import mobile_routes

    http, database, _, _ = client
    for owner in (-1, 1):
        database.set_preferences(
            owner,
            {
                'personalization': False,
                'similarity': False,
                'daily': False,
                'weekly': False,
            },
        )
    rows = [
        dict(mobile_routes._sync().row_for(key), duration=180)
        for key in ('one', 'two')
    ]
    monkeypatch.setattr(routes, 'catalog', lambda _: rows)
    first = create(http, ids=[], count=2)
    assert first.status_code == 202
    assert first.json()['selection_basis'] == 'dj_analysis'
    assert {row['id'] for row in first.json()['tracks']} == {'one', 'two'}
    assert database.metadata('model', None) is None
    with database.connect() as db:
        assert db.execute('SELECT count(*) FROM jobs').fetchone()[0] == 0
    # A network retry must not reselect against a new catalogue or need a live engine.
    rows.clear()
    database.set_metadata('dj', {})
    assert create(http, ids=[], count=2).json()['id'] == first.json()['id']
    assert create(http, ids=[], count=3).status_code == 422
    assert create(http, ids=[], count=2, theme='calme').status_code == 422
    assert len(DjStore(database).list(1)) == 1


def test_automatic_dj_pool_is_bounded_diverse_and_deterministic():
    from downtify.music_ai.dj_routes import local_pool

    rows = [{'id': str(i), 'artist': str(i // 6)} for i in range(30)]
    first = local_pool(rows, 8, 'request')
    assert first == local_pool(list(reversed(rows)), 8, 'request')
    assert len(first) == 8
    assert all(
        sum(row['artist'] == artist for row in first) <= 2
        for artist in {row['artist'] for row in first}
    )


def test_sessions_are_owned_and_read_access_is_rechecked(client):
    http, _, access, _ = client
    session = create(http).json()['id']
    url = '/api/v1/music-ai/dj/sessions/' + session
    assert http.get(url, headers={'x-test-user': '2'}).status_code == 404
    assert http.delete(url, headers={'x-test-user': '2'}).status_code == 404
    access['hidden'] = {'two.wav'}
    assert http.get(url, headers={'x-test-user': '1'}).status_code == 404
    assert http.get(
        '/api/v1/music-ai/dj/sessions', headers={'x-test-user': '1'}
    ).json() == {'sessions': []}
    assert http.delete(url, headers={'x-test-user': '1'}).status_code == 200


def test_prepared_media_supports_range_and_refuses_revoked_or_disabled_access(
    client,
):
    http, database, access, music = client
    before = {p.name: p.read_bytes() for p in music.iterdir()}
    session = create(http).json()['id']
    job = DjStore(database).claim()
    assert DjStore(database).publish(
        session, job['lease_token'], 'ready', {'duration': 10}
    )
    output = database.path.parent / 'dj' / session
    output.mkdir(parents=True)
    (output / 'set.m4a').write_bytes(b'0123456789')
    url = f'/api/v1/music-ai/dj/sessions/{session}/media'
    headers = {'x-test-user': '1', 'Range': 'bytes=2-5'}
    result = http.get(url, headers=headers)
    assert result.status_code == 206
    assert result.content == b'2345'
    assert 'no-store' in result.headers['cache-control']
    access['allowed'] = set()
    assert http.get(url, headers=headers).status_code == 404
    access['allowed'] = None
    database.set_preferences(1, {'dj_prepared': False})
    assert http.get(url, headers=headers).status_code == 409
    assert before == {p.name: p.read_bytes() for p in music.iterdir()}


def test_interactive_is_refused_before_validation_and_unknown_tracks_fail_closed(
    client,
):
    http, database, _, _ = client
    database.set_preferences(-1, {'dj_interactive': True})
    database.set_preferences(1, {'dj_interactive': True})
    assert create(http, mode='interactive').status_code == 503
    assert create(http, ids=['one', 'hidden']).status_code == 404
    assert create(http, ids=['one', 'one']).status_code == 422
    assert DjStore(database).list(1) == []


def test_cache_discard_never_deletes_another_users_set_and_hides_completed_deletion(
    client,
):
    http, database, _, _ = client
    identity = create(http).json()['id']
    url = f'/api/v1/music-ai/dj/sessions/{identity}'
    assert (
        http.delete(url + '/cache', headers={'x-test-user': '2'}).status_code
        == 404
    )
    assert (
        http.delete(url + '/cache', headers={'x-test-user': '1'}).status_code
        == 202
    )
    assert DjStore(database).get(1, identity)['state'] == 'deleting'
    DjStore(database).deleted(identity)
    assert http.get(url, headers={'x-test-user': '1'}).status_code == 404
    assert create(http).status_code == 410


def validation_session(client):
    http, database, _, _ = client
    for owner in (-1, 1):
        database.set_preferences(owner, {'dj_interactive': True})
    return http.post(
        '/api/v1/music-ai/dj/admin/validation-sessions',
        headers={'x-test-user': '1', 'x-test-admin': 'yes'},
        json={
            'request_id': 'proof',
            'mode': 'interactive',
            'theme': 'fete',
            'ids': ['one', 'two'],
        },
    )


def test_only_admin_can_start_validation_and_normal_mode_stays_gated(client):
    http, database, _, _ = client
    response = http.post(
        '/api/v1/music-ai/dj/admin/validation-sessions',
        headers={'x-test-user': '1'},
        json={
            'request_id': 'proof',
            'mode': 'interactive',
            'theme': 'fete',
            'ids': ['one', 'two'],
        },
    )
    assert response.status_code == 403
    found = validation_session(client)
    assert found.status_code == 202
    assert found.json()['validation'] is True
    assert create(http, mode='interactive').status_code == 503
    assert create(http, mode='interactive', validation=True).status_code == 422
    database.set_preferences(-1, {'dj_interactive': False})
    assert validation_session_after_disable(http).status_code == 409


def validation_session_after_disable(http):
    return http.post(
        '/api/v1/music-ai/dj/admin/validation-sessions',
        headers={'x-test-user': '1', 'x-test-admin': 'yes'},
        json={
            'request_id': 'proof2',
            'mode': 'interactive',
            'theme': 'fete',
            'ids': ['one', 'two'],
        },
    )


def test_hls_resources_are_owned_visible_no_store_and_manifest_cannot_escape(
    client,
):
    http, database, access, _ = client
    identity = validation_session(client).json()['id']
    store = DjStore(database)
    job = store.claim()
    assert store.publish(
        identity, job['lease_token'], 'playing', {'rendered': 24}
    )
    output = database.path.parent / 'dj' / identity
    output.mkdir(parents=True)
    manifest = output / 'index.m3u8'
    manifest.write_text('#EXTM3U\n#EXTINF:6,\nsegment-00000000.ts\n')
    (output / 'segment-00000000.ts').write_bytes(b'0123456789')
    url = f'/api/v1/music-ai/dj/sessions/{identity}/hls/'
    headers = {'x-test-user': '1'}
    result = http.get(url + 'index.m3u8', headers=headers)
    assert result.status_code == 200
    assert 'no-store' in result.headers['cache-control']
    ready = store.get(1, identity)['ready_seconds']
    assert ready >= 0
    # Only the first playable manifest read counts, not every reload.
    assert http.get(url + 'index.m3u8', headers=headers).status_code == 200
    assert store.get(1, identity)['ready_seconds'] == ready
    from downtify.music_ai.dj_assets import Assets

    assert Assets(database).pinned(identity)
    assert (
        http.get(
            url + 'segment-00000000.ts',
            headers={**headers, 'Range': 'bytes=2-5'},
        ).content
        == b'2345'
    )
    assert (
        http.get(url + 'index.m3u8', headers={'x-test-user': '2'}).status_code
        == 404
    )
    assert http.get(url + 'private.env', headers=headers).status_code == 404
    manifest.write_text('#EXTM3U\nhttps://untrusted.test/audio.ts\n')
    assert http.get(url + 'index.m3u8', headers=headers).status_code == 503
    manifest.write_text(
        '#EXTM3U\n#EXT-X-KEY:URI="https://untrusted.test/key"\n'
    )
    assert http.get(url + 'index.m3u8', headers=headers).status_code == 503
    access['allowed'] = set()
    assert (
        http.get(url + 'segment-00000000.ts', headers=headers).status_code
        == 404
    )
    access['allowed'] = None
    database.set_preferences(1, {'dj_interactive': False})
    assert (
        http.get(url + 'segment-00000000.ts', headers=headers).status_code
        == 409
    )


def test_completed_stream_navigation_is_owned_idempotent_and_does_not_resume(
    client,
):
    from datetime import datetime, timezone

    http, database, _, _ = client
    identity = validation_session(client).json()['id']
    store = DjStore(database)
    job = store.claim()
    origin = 1_700_000_000
    assert store.publish(
        identity,
        job['lease_token'],
        'ready',
        {
            'media_origin': origin,
            'timeline': [
                {'id': 'one', 'start': 0, 'end': 180},
                {'id': 'two', 'start': 180, 'end': 360},
            ],
        },
    )
    folder = database.path.parent / 'dj' / identity
    folder.mkdir(parents=True)
    stamp = datetime.fromtimestamp(origin + 180, timezone.utc).isoformat()
    (folder / 'index.m3u8').write_text(
        f'#EXTM3U\n#EXT-X-PROGRAM-DATE-TIME:{stamp}\n'
        '#EXTINF:6,\nsegment-00000030.ts\n'
    )
    (folder / 'segment-00000030.ts').write_bytes(b'audio')
    url = f'/api/v1/music-ai/dj/sessions/{identity}/commands'
    payload = {
        'request_id': 'jump',
        'action': 'next',
        'payload': {'position': '175'},
    }
    headers = {'x-test-user': '1'}
    result = http.post(url, headers=headers, json=payload)
    assert result.status_code == 202
    assert result.json()['seek_to_seconds'] == 180
    assert (
        http.post(url, headers=headers, json=payload).json() == result.json()
    )
    assert store.get(1, identity)['state'] == 'ready'
    assert (
        http.post(url, headers={'x-test-user': '2'}, json=payload).status_code
        == 404
    )
    changed = {**payload, 'payload': {'position': '176'}}
    assert http.post(url, headers=headers, json=changed).status_code == 422
    database.set_preferences(1, {'dj_interactive': False})
    assert http.post(url, headers=headers, json=payload).status_code == 409


def test_command_api_receipts_and_continuity_remain_owner_scoped(client):
    http, database, _, _ = client
    identity = validation_session(client).json()['id']
    store = DjStore(database)
    job = store.claim()
    store.publish(identity, job['lease_token'], 'playing', {'rendered': 24})
    url = f'/api/v1/music-ai/dj/sessions/{identity}'
    headers = {'x-test-user': '1'}
    assert (
        http.post(
            url + '/commands',
            headers=headers,
            json={'request_id': 'one', 'action': 'next'},
        ).status_code
        == 202
    )
    assert (
        http.post(
            url + '/commands',
            headers={'x-test-user': '2'},
            json={'request_id': 'two', 'action': 'next'},
        ).status_code
        == 404
    )
    assert (
        http.post(
            url + '/commands',
            headers=headers,
            json={
                'request_id': 'three',
                'action': 'replace',
                'payload': {'id': 'private'},
            },
        ).status_code
        == 422
    )
    result = {'accepted': True, 'effective_after_seconds': 30}
    store.complete_command(identity, job['lease_token'], 'one', result)
    assert (
        http.get(url, headers=headers).json()['commands'][0][
            'effective_after_seconds'
        ]
        == 30
    )
    assert (
        http.post(
            url + '/validation',
            headers=headers,
            json={'position': 0, 'sequence': 0},
        ).status_code
        == 403
    )
    assert (
        http.post(
            url + '/validation',
            headers={**headers, 'x-test-admin': 'yes'},
            json={'position': 0, 'sequence': 0},
        ).status_code
        == 200
    )
    assert (
        http.post(
            url + '/validation',
            headers={**headers, 'x-test-admin': 'yes'},
            json={'position': 3600, 'sequence': 1},
        ).status_code
        == 422
    )


def test_rendered_hls_checks_current_acl_without_reopening_original_nas_files(
    client, monkeypatch
):
    from downtify import library_catalog

    http, database, access, music = client
    identity = validation_session(client).json()['id']
    store = DjStore(database)
    job = store.claim()
    store.publish(identity, job['lease_token'], 'playing', {'rendered': 24})
    output = database.path.parent / 'dj' / identity
    output.mkdir(parents=True)
    (output / 'index.m3u8').write_text(
        '#EXTM3U\n#EXTINF:6,\nsegment-00000000.ts\n'
    )

    def original_nas_io(*_):
        raise AssertionError('Rendered stream must not reopen original files')

    monkeypatch.setattr(
        library_catalog, 'resolve_library_file', original_nas_io
    )
    url = f'/api/v1/music-ai/dj/sessions/{identity}/hls/index.m3u8'
    headers = {'x-test-user': '1'}
    assert http.get(url, headers=headers).status_code == 200
    assert http.get(url, headers={'x-test-user': '2'}).status_code == 404
    access['hidden_resolved'] = {str(music / 'two.wav')}
    assert http.get(url, headers=headers).status_code == 404


def test_queue_mode_preserves_repeated_occurrences_and_owner_scope(client):
    http, database, _, _ = client
    validation_session(client)
    payload = {
        'request_id': 'ordered',
        'theme': 'fete',
        'mode': 'interactive',
        'queue_order': True,
        'ids': ['two', 'one', 'two'],
    }
    response = http.post(
        '/api/v1/music-ai/dj/admin/validation-sessions',
        json=payload,
        headers={'x-test-user': '1', 'x-test-admin': 'yes'},
    )
    assert response.status_code == 202
    value = response.json()
    assert [row['id'] for row in value['tracks']] == ['two', 'one', 'two']
    assert value['queue_order'] is True
    assert all(not row['file'].startswith('/') for row in value['tracks'])
    assert 'sources' not in value
    assert 'owner' not in value
    assert (
        http.get(
            '/api/v1/music-ai/dj/sessions/' + value['id'],
            headers={'x-test-user': '2'},
        ).status_code
        == 404
    )


def test_continuous_and_queue_are_rejected_for_prepared_mode(client):
    http, _, _, _ = client
    for extra in ({'continuous': True}, {'queue_order': True}):
        response = http.post(
            '/api/v1/music-ai/dj/sessions',
            headers={'x-test-user': '1'},
            json={
                'request_id': 'invalid',
                'theme': 'fete',
                'ids': ['one', 'two'],
                **extra,
            },
        )
        assert response.status_code == 422


def test_seed_handover_excludes_the_audible_title_and_requires_two_analyzed_followers(
    client, monkeypatch
):
    import numpy as np

    from downtify import mobile_routes

    http, database, _, music = client
    original = mobile_routes._sync()
    rows = {
        key: dict(original.row_for(key), duration=180)
        for key in ('one', 'two')
    }
    rows['three'] = dict(
        rows['two'], id='three', title='three', file='three.wav'
    )
    (music / 'three.wav').write_bytes(b'original-content')
    monkeypatch.setattr(
        mobile_routes, '_sync', lambda: SimpleNamespace(row_for=rows.get)
    )
    monkeypatch.setattr(routes, 'catalog', lambda _: list(rows.values()))
    monkeypatch.setattr(routes, 'current_sources', lambda values: values)
    database.set_metadata('model', {'id': 'fixture'})
    vectors = {key: np.array([1.0, 0.0], dtype='float32') for key in rows}
    monkeypatch.setattr(database, 'vectors', lambda *_: vectors)
    payload = {'ids': [], 'seed_id': 'one', 'skip_seed': True, 'count': 2}
    response = create(http, **payload)
    assert response.status_code == 202, response.text
    assert {row['id'] for row in response.json()['tracks']} == {'two', 'three'}
    assert create(http, **payload).json()['id'] == response.json()['id']
    assert create(http, **dict(payload, skip_seed=False)).status_code == 422
    vectors.pop('three')
    assert (
        create(http, **dict(payload, request_id='not-enough')).status_code
        == 503
    )
    assert (
        create(http, ids=[], skip_seed=True, request_id='no-seed').status_code
        == 422
    )


def accepted_asset(http, database):
    from downtify.music_ai.dj_assets import Assets

    session = create(http).json()
    dj = DjStore(database)
    job = dj.claim()
    assets = Assets(database, min_free=0)
    directory = assets.directory(session['id'])
    directory.mkdir(mode=0o700)
    (directory / 'set.m4a').write_bytes(b'accepted-audio')
    assert dj.publish(
        session['id'],
        job['lease_token'],
        'ready',
        {'duration': 10, 'timeline': [{'id': 'one', 'start': 0, 'end': 10}]},
    )
    return session['id'], assets


def test_prepared_readers_are_independent_and_stop_keeps_audio(client):
    http, database, _, _ = client
    identity, assets = accepted_asset(http, database)
    url = f'/api/v1/music-ai/dj/sessions/{identity}'
    headers = {'x-test-user': '1'}
    for consumer in ('phone', 'browser'):
        assert (
            http.get(
                url + '/media?consumer=' + consumer, headers=headers
            ).content
            == b'accepted-audio'
        )
    assert (
        http.delete(url + '?consumer=phone', headers=headers).status_code
        == 200
    )
    assert DjStore(database).get(1, identity)['state'] == 'ready'
    assert http.delete(url + '/cache', headers=headers).status_code == 409
    assert (
        http.delete(url + '?consumer=browser', headers=headers).status_code
        == 200
    )
    assert not assets.pinned(identity)
    assert http.delete(url + '/cache', headers=headers).status_code == 202


def test_copy_api_is_owner_scoped_and_weekly_cards_are_metadata_only(
    client, monkeypatch
):
    from downtify.music_ai import compute_budget
    from downtify.music_ai.dj_background import weekly_period

    monkeypatch.setattr(compute_budget, 'pressure_high', lambda: False)
    http, database, _, _ = client
    identity, _ = accepted_asset(http, database)
    url = f'/api/v1/music-ai/dj/sessions/{identity}/copies'
    body = {'request_id': 'my-copy', 'name': 'Mon rock de la semaine'}
    assert (
        http.post(url, headers={'x-test-user': '2'}, json=body).status_code
        == 404
    )
    response = http.post(url, headers={'x-test-user': '1'}, json=body)
    assert response.status_code == 201
    result = response.json()
    assert result['title'] == body['name']
    assert result['immutable_copy']
    assert 'copy_sha256' not in result
    assert 'asset_workspace' not in result
    assert (
        http.post(url, headers={'x-test-user': '1'}, json=body).json()['id']
        == result['id']
    )
    for owner in (-1, 1, 2):
        database.set_preferences(owner, {'dj_weekly': True})
    before = database.metadata('dj')
    weekly = http.get(
        '/api/v1/music-ai/dj/weekly', headers={'x-test-user': '1'}
    )
    assert weekly.status_code == 200
    value = weekly.json()
    assert value['period'] == weekly_period()
    assert len(value['cards']) == 10
    assert len(value['featured']) == 4
    assert {'rock', 'rap', 'pop', 'electro'} <= {
        card['theme'] for card in value['cards']
    }
    assert value['copies'][0]['id'] == result['id']
    assert value['copies'][0]['tracks'] == []
    assert value['copies'][0]['timeline'] == []
    assert (
        http.get(
            '/api/v1/music-ai/dj/weekly', headers={'x-test-user': '2'}
        ).json()['copies']
        == []
    )
    assert database.metadata('dj') == before


def test_playback_304_renews_pin_and_invalid_consumer_is_rejected(client):
    http, database, _, _ = client
    identity, assets = accepted_asset(http, database)
    url = (
        f'/api/v1/music-ai/dj/sessions/{identity}?view=playback&consumer=phone'
    )
    headers = {'x-test-user': '1'}
    first = http.get(url, headers=headers)
    assert first.status_code == 200
    assets.release(1, identity, 'client:phone')
    assert not assets.pinned(identity)
    assert (
        http.get(
            url, headers={**headers, 'if-none-match': first.headers['etag']}
        ).status_code
        == 304
    )
    assert assets.pinned(identity)
    assert (
        http.get(
            url.replace('consumer=phone', 'consumer=bad%2Fpath'),
            headers=headers,
        ).status_code
        == 422
    )


def test_weekly_preparation_is_explicit_and_idempotent(client, monkeypatch):
    import json

    from downtify.music_ai.dj_background import weekly_period

    http, database, _, _ = client
    for owner in (-1, 1):
        database.set_preferences(owner, {'dj_weekly': True})
    database.set_metadata(
        'dj',
        {'prepared_ready': True, 'weekly_protocol': 1, 'seen': time.time()},
    )
    monkeypatch.setattr(
        routes,
        'catalog',
        lambda request: [
            {'id': 'one', 'duration': 180},
            {'id': 'two', 'duration': 180},
        ],
    )
    with database.connect() as db:
        db.execute(
            'INSERT INTO playlists VALUES (?,?,?,?,?,?)',
            (
                1,
                'weekly',
                'rock',
                weekly_period(),
                json.dumps(['one', 'two']),
                time.time(),
            ),
        )
    url = '/api/v1/music-ai/dj/weekly/rock'
    headers = {'x-test-user': '1'}
    response = http.post(
        url, headers=headers, json={'request_id': 'weekly-explicit'}
    )
    assert response.status_code == 202
    identity = response.json()['id']
    assert response.json()['weekly_theme'] == 'rock'
    assert (
        http.post(
            url, headers=headers, json={'request_id': 'weekly-explicit'}
        ).json()['id']
        == identity
    )
    value = http.get('/api/v1/music-ai/dj/weekly', headers=headers).json()
    card = next(card for card in value['cards'] if card['theme'] == 'rock')
    assert card['session']['id'] == identity
    assert card['session']['tracks'] == []
    assert card['session']['cover_ids'] == ['one', 'two']
    assert (
        http.post(
            '/api/v1/music-ai/dj/weekly/no-such-theme',
            headers=headers,
            json={'request_id': 'invalid'},
        ).status_code
        == 404
    )
    database.set_preferences(1, {'dj_weekly': False})
    assert (
        http.post(url, headers=headers, json={'request_id': 'off'}).status_code
        == 409
    )


def test_completed_interactive_audio_is_pinned_by_a_playback_reader(client):
    from downtify.music_ai.dj_assets import Assets

    http, database, _, _ = client
    identity = validation_session(client).json()['id']
    dj = DjStore(database)
    job = dj.claim()
    assert dj.publish(identity, job['lease_token'], 'ready', {'duration': 24})
    headers = {'x-test-user': '1'}
    url = f'/api/v1/music-ai/dj/sessions/{identity}?view=playback&consumer=browser'
    assert http.get(url, headers=headers).status_code == 200
    assets = Assets(database)
    assert assets.pinned(identity)
    assert not assets.expire(identity)
    assert http.delete(url, headers=headers).status_code == 200
    assert not assets.pinned(identity)
