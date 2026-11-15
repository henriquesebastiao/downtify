"""Device DJ preparation only reads bounded current native/cache records."""

import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict
from types import SimpleNamespace

import pytest
from ai_test_support import opted_in_store
from fastapi import FastAPI
from fastapi.testclient import TestClient

from downtify.music_ai import (
    catalog,
    dj_routes,
    dj_worker,
    local_plans,
    local_sources,
    routes,
)
from downtify.music_ai.dj_plan import Profile
from downtify.music_ai.dj_store import DjStore
from downtify.music_ai.worker import signature

URL = '/api/v1/music-ai/dj/local-plans'
MODEL = 'private-model-identity'


def forbidden(*args, **kwargs):
    pytest.fail('Interactive local planning must not scan or schedule work')


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    from downtify import api, library_catalog, mobile_routes

    database = opted_in_store(tmp_path / 'derived.db')
    for owner in (-1, 1, 2):
        database.set_preferences(owner, {'dj_interactive': True})
    database.set_metadata('rhythm', {'model': MODEL})
    cache = DjStore(database)
    rows, calls, files, sources = {}, [], {}, {}
    access = {'allowed': None, 'hidden': set()}
    for identity in ('one', 'two', 'three', 'four'):
        files[identity] = tmp_path / (identity + '.wav')
        files[identity].write_bytes(b'original audio')
        sources[identity] = list(signature(files[identity]))
        row = {
            'id': identity,
            'file': 'PRIVATE_PATH/' + identity,
            'size': 42,
            'modified': 10,
            'duration': 120,
            'revision': 'native-v1',
        }
        rows[identity] = row
        database.observe([{**row, 'fingerprint': catalog.fingerprint(row)}])
        database.observe_source(identity, sources[identity])
        value = Profile(
            identity,
            120,
            120,
            0.95,
            tuple(range(0, 120, 2)),
            0.5,
            instrumental_confidence=0.9,
        )
        cache.put_profile(
            identity,
            MODEL,
            catalog.fingerprint(row),
            sources[identity],
            {'profile': asdict(value)},
        )

    def rows_for(identities):
        assert len(identities) <= 4
        calls.append(list(identities))
        return {
            identity: rows[identity]
            for identity in identities
            if identity in rows
        }

    monkeypatch.setattr(routes, 'store', lambda: database)
    monkeypatch.setattr(
        api,
        'library_context',
        lambda: SimpleNamespace(hidden_files=access['hidden']),
    )
    monkeypatch.setattr(
        api, 'allowed_entry_keys', lambda _, entries: access['allowed']
    )
    monkeypatch.setattr(
        mobile_routes, '_sync', lambda: SimpleNamespace(rows_for=rows_for)
    )
    monkeypatch.setattr(routes, 'catalog', forbidden)
    monkeypatch.setattr(database, 'enqueue', forbidden)
    monkeypatch.setattr(database, 'observe', forbidden)
    monkeypatch.setattr(dj_routes, 'database', forbidden)
    monkeypatch.setattr(dj_worker.DjWorker, 'analysis_result', forbidden)
    monkeypatch.setattr(
        library_catalog,
        'resolve_library_file',
        lambda file, _: files.get(file.rsplit('/', 1)[-1]),
    )
    app = FastAPI()

    @app.middleware('http')
    async def identity(request, call_next):
        request.state.principal = SimpleNamespace(
            user_id=int(request.headers.get('x-test-user', '0')),
            is_admin=False,
        )
        return await call_next(request)

    app.include_router(routes.router)
    with TestClient(app) as http:
        yield SimpleNamespace(
            http=http,
            database=database,
            cache=cache,
            rows=rows,
            calls=calls,
            access=access,
            files=files,
            sources=sources,
        )


def request(fixture, ids=None, **changes):
    return fixture.http.post(
        URL,
        headers={'x-test-user': '1'},
        json={'ids': ids or ['one', 'two'], **changes},
    )


def put(fixture, identity='one', **changes):
    original = fixture.cache.profile(
        identity,
        MODEL,
        catalog.fingerprint(fixture.rows[identity]),
        fixture.sources[identity],
    )['profile']
    original.update(changes)
    fixture.cache.put_profile(
        identity,
        MODEL,
        catalog.fingerprint(fixture.rows[identity]),
        fixture.sources[identity],
        {'profile': original},
    )


def test_owner_and_feature_checks_precede_any_lookup(fixture):
    assert (
        fixture.http.post(URL, json={'ids': ['one', 'two']}).status_code == 401
    )
    for owner in (-1, 1):
        fixture.database.set_preferences(owner, {'dj_interactive': False})
        assert request(fixture).status_code == 409
        fixture.database.set_preferences(owner, {'dj_interactive': True})
    assert fixture.calls == []


@pytest.mark.parametrize('restriction', ['hidden', 'denied', 'missing'])
def test_native_visibility_is_current_and_does_not_disclose_existence(
    fixture, restriction
):
    if restriction == 'hidden':
        fixture.access['hidden'].add(fixture.rows['two']['file'])
    elif restriction == 'denied':
        fixture.access['allowed'] = set()
    else:
        del fixture.rows['two']
    response = request(fixture)
    assert response.status_code == 404
    assert 'PRIVATE' not in response.text


def test_occurrences_cached_plan_and_half_tempo(fixture):
    put(fixture, 'two', bpm=60)
    response = request(fixture, ['two', 'one', 'two', 'three'])
    assert response.status_code == 200
    result = response.json()
    assert result['version'] == 1
    assert fixture.calls == [['two', 'one', 'three']]
    assert [item['index'] for item in result['tracks']] == [0, 1, 2, 3]
    assert [
        (item['from_index'], item['to_index']) for item in result['plans']
    ] == [(0, 1), (1, 2), (2, 3)]
    for item in result['tracks']:
        assert item['status'] == 'ready'
        assert item['validity'] == 'source_verified'
        assert item['downbeats_ms'] == sorted(set(item['downbeats_ms']))
    for item in result['plans']:
        assert item['state'] == 'ready'
        assert item['speed'] == 1
        assert item['duration_ms'] == 4000
        assert (
            item['source_end_ms'] - item['outgoing_start_ms']
            == item['duration_ms']
        )
    assert all(
        secret not in response.text
        for secret in ('PRIVATE_PATH', MODEL, 'fingerprint', 'source_version')
    )
    assert response.headers['Cache-Control'] == 'private, no-cache'


def test_ready_revision_is_stable_and_owner_and_profile_specific(fixture):
    first = request(fixture).json()
    assert request(fixture).json() == first
    other = fixture.http.post(
        URL, headers={'x-test-user': '2'}, json={'ids': ['one', 'two']}
    ).json()
    assert first['revision'] != other['revision']
    put(fixture, confidence=0.8)
    assert request(fixture).json()['revision'] != first['revision']


@pytest.mark.parametrize(
    ('mutation', 'status'),
    [
        ('missing', 'missing'),
        ('model', 'missing'),
        ('fingerprint', 'stale'),
        ('native', 'stale'),
        ('source', 'stale'),
    ],
)
def test_missing_and_stale_analysis_never_starts_work(
    fixture, mutation, status
):
    with fixture.database.connect() as db:
        if mutation == 'missing':
            db.execute("DELETE FROM dj_profiles WHERE track='one'")
        elif mutation == 'model':
            db.execute("UPDATE dj_profiles SET model='old' WHERE track='one'")
        elif mutation == 'fingerprint':
            db.execute(
                "UPDATE tracks SET fingerprint='changed' WHERE id='one'"
            )
        elif mutation == 'source':
            db.execute(
                "UPDATE source_versions SET signature='[9,8,7,6,5]' WHERE id='one'"
            )
        else:
            fixture.rows['one']['size'] += 1
    result = request(fixture).json()
    assert result['tracks'][0]['status'] == status
    assert 'bpm' not in result['tracks'][0]
    assert result['plans'][0]['state'] == 'unavailable'
    assert result['plans'][0]['reason'] == status + '_analysis'


@pytest.mark.parametrize(
    'changes',
    [
        {'bpm': 301},
        {'bpm': float('nan')},
        {'confidence': 0.74},
        {'downbeats': [0, 2, 1]},
        {'downbeats': [0] * 20001},
        {'bpm': True},
        {'bpm': 10**500},
    ],
)
def test_corrupt_or_unreliable_profile_is_explicit(fixture, changes):
    put(fixture, **changes)
    result = request(fixture).json()
    assert result['tracks'][0]['status'] == 'unreliable'
    assert result['plans'][0]['reason'] == 'unreliable_analysis'


def test_tempo_mismatch_and_duration_limit_are_explicit(fixture):
    put(fixture, 'two', bpm=80)
    assert request(fixture).json()['plans'][0]['reason'] == 'tempo_mismatch'
    put(fixture, 'two', bpm=120)
    assert (
        request(fixture, transition_ms=1000).json()['plans'][0]['reason']
        == 'duration_too_short'
    )
    put(fixture, 'one', instrumental_confidence=0)
    assert request(fixture).json()['plans'][0]['duration_ms'] == 2000


def test_subsecond_bar_is_valid_and_remains_within_request(fixture):
    for identity in ('one', 'two'):
        put(
            fixture,
            identity,
            bpm=300,
            downbeats=[index * 0.8 for index in range(150)],
        )
    plan = request(fixture, transition_ms=1000).json()['plans'][0]
    assert plan['state'] == 'ready'
    assert plan['duration_ms'] == 800


def test_missing_profile_table_does_not_create_it(fixture):
    with fixture.database.connect() as db:
        db.execute('DROP TABLE dj_profiles')
    assert request(fixture).json()['tracks'][0]['status'] == 'missing'
    with fixture.database.connect() as db:
        assert (
            db.execute(
                "SELECT name FROM sqlite_master WHERE name='dj_profiles'"
            ).fetchone()
            is None
        )


def test_database_error_is_safe_service_unavailability(fixture, monkeypatch):
    def unavailable(*args):
        raise sqlite3.OperationalError('PRIVATE_PATH/database')

    monkeypatch.setattr(local_plans, 'cached', unavailable)
    result = request(fixture)
    assert result.status_code == 503
    assert 'PRIVATE_PATH' not in result.text


def test_request_only_reads_indexed_selected_records(fixture, monkeypatch):
    statements = []
    connect = fixture.database.connect

    @contextmanager
    def traced():
        with connect() as db:
            db.set_trace_callback(statements.append)
            yield db

    monkeypatch.setattr(fixture.database, 'connect', traced)
    result = request(fixture, ['one', 'two', 'three', 'one'])
    assert result.status_code == 200
    assert all(
        sql.split()[0] in {'SELECT', 'BEGIN', 'COMMIT'} for sql in statements
    )
    profiles = [sql for sql in statements if 'FROM dj_profiles' in sql]
    assert len(profiles) == 1
    assert "p.track IN ('one','two','three')" in profiles[0]
    assert (
        'LIMIT' not in profiles[0]
    )  # Point lookups, not a truncated full scan.
    with connect() as db:
        query_plan = db.execute('EXPLAIN QUERY PLAN ' + profiles[0]).fetchall()
    assert all('SCAN ' not in row[3] for row in query_plan)


def test_corrupt_json_or_oversized_payload_never_reaches_client(fixture):
    for payload in ('{', 'x' * (local_plans.MAX_PROFILE_BYTES + 1)):
        with fixture.database.connect() as db:
            db.execute(
                "UPDATE dj_profiles SET value=? WHERE track='one'", (payload,)
            )
        result = request(fixture).json()
        assert result['tracks'][0]['status'] == 'unreliable'
        assert 'downbeats_ms' not in result['tracks'][0]


def test_module_change_during_lookup_is_rechecked(fixture, monkeypatch):
    lookup = local_plans.lookup

    def turn_off(*args):
        result = lookup(*args)
        fixture.database.set_preferences(1, {'dj_interactive': False})
        return result

    monkeypatch.setattr(local_plans, 'lookup', turn_off)
    assert request(fixture).status_code == 409


def test_capability_advertises_cached_plans_without_live_renderer(fixture):
    response = fixture.http.get(
        '/api/v1/music-ai/capabilities', headers={'x-test-user': '1'}
    )
    assert response.status_code == 200
    assert response.json()['dj']['local_plans_version'] == 1
    assert response.json()['dj']['interactive_ready'] is False


@pytest.mark.parametrize('mutation', ['missing', 'replaced'])
def test_real_source_change_is_detected_without_catalog_refresh(
    fixture, mutation
):
    original = fixture.files['one']
    if mutation == 'missing':
        original.unlink()
        reason = 'source_unavailable'
    else:
        previous = original.stat()
        replacement = original.with_suffix('.replacement')
        replacement.write_bytes(b'replaced audio')
        os.utime(replacement, ns=(previous.st_atime_ns, previous.st_mtime_ns))
        replacement.replace(original)
        assert list(signature(original)) != fixture.sources['one']
        reason = 'source_changed'
    result = request(fixture).json()
    assert result['tracks'][0]['status'] == 'stale'
    assert result['tracks'][0]['validity'] == reason
    assert 'bpm' not in result['tracks'][0]
    assert result['plans'][0]['state'] == 'unavailable'
    assert result['plans'][0]['reason'] == reason
    assert result['tracks'][1]['validity'] == 'source_verified'


def test_slow_source_io_times_out_and_cannot_spawn_more_workers(monkeypatch):
    guard = local_sources.SourceGuard()
    entered, release, exited = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    calls = []

    def slow(rows, context, expected):
        calls.append(threading.current_thread())
        entered.set()
        try:
            release.wait(5)
            return dict.fromkeys(expected, 'source_verified')
        finally:
            exited.set()

    monkeypatch.setattr(guard, '_verify', slow)
    rows, expected = [{'id': 'one'}], {'one': [1, 2, 3, 4, 5]}
    start = time.monotonic()
    try:
        assert guard.check(rows, None, expected, timeout=0.01) == {
            'one': 'source_timeout'
        }
        assert time.monotonic() - start < 0.5
        assert entered.is_set()
        for _ in range(20):
            assert guard.check(rows, None, expected, timeout=0.01) == {
                'one': 'source_busy'
            }
        assert len(calls) == 1
        assert calls[0].daemon is True
    finally:
        release.set()
        assert exited.wait(1)
        calls[0].join(1)
    assert not calls[0].is_alive()
    assert guard.check(rows, None, expected, timeout=1) == {
        'one': 'source_verified'
    }


def test_source_checks_are_unique_and_at_most_four(fixture, monkeypatch):
    calls = []
    actual = local_sources.signature

    def counted(path):
        calls.append(path)
        return actual(path)

    monkeypatch.setattr(local_sources, 'signature', counted)
    assert request(fixture, ['one', 'two', 'one', 'three']).status_code == 200
    assert calls == [
        fixture.files[identity] for identity in ('one', 'two', 'three')
    ]


@pytest.mark.parametrize('reason', ['source_timeout', 'source_busy'])
def test_source_delay_never_leaves_a_ready_plan(fixture, monkeypatch, reason):
    monkeypatch.setattr(
        local_sources.guard,
        'check',
        lambda rows, context, expected: dict.fromkeys(expected, reason),
    )
    result = request(fixture).json()
    assert all(item['status'] != 'ready' for item in result['tracks'])
    assert result['plans'][0]['reason'] == reason
    assert result['plans'][0]['state'] == 'unavailable'


@pytest.mark.parametrize(
    'payload',
    [
        {'ids': []},
        {'ids': ['one']},
        {'ids': ['one'] * 5},
        {'ids': ['', 'two']},
        {'ids': [1, 'two']},
        {'ids': ['x' * 81, 'two']},
        *(
            {'ids': ['one', 'two'], 'transition_ms': value}
            for value in (999, 12001, True, 2000.5, '2000')
        ),
        {'ids': ['one', 'two'], 'extra': True},
    ],
)
def test_strict_bounded_request(fixture, payload):
    assert (
        fixture.http.post(
            URL, headers={'x-test-user': '1'}, json=payload
        ).status_code
        == 422
    )
    assert fixture.calls == []
