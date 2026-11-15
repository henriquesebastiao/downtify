import hashlib
import json
import time
from datetime import datetime

import pytest
from ai_test_support import opted_in_store

from downtify.music_ai import compute_budget
from downtify.music_ai.dj_background import weekly_period
from downtify.music_ai.dj_store import DjStore
from downtify.music_ai.dj_weekly import enqueue_due
from downtify.music_ai.dj_worker import DjWorker


@pytest.fixture
def setup(tmp_path, monkeypatch):
    database = opted_in_store(tmp_path / 'state/derived.db')
    for owner in (-1, 1, 2):
        database.set_preferences(
            owner,
            {'dj_prepared': True, 'dj_weekly': True, 'dj_interactive': True},
        )
    music = tmp_path / 'music'
    music.mkdir()
    sources = {}
    for identity in ('one', 'two'):
        path = music / f'{identity}.audio'
        path.write_bytes(b'unchanged-original')
        sources[identity] = {
            'path': str(path),
            'fingerprint': identity,
            'source_version': [],
        }
    monkeypatch.setattr(compute_budget, 'pressure_high', lambda: False)
    database.set_metadata(
        'dj',
        {'prepared_ready': True, 'weekly_protocol': 1, 'seen': time.time()},
    )
    return database, DjStore(database), sources, music


def create_background(database, dj, sources, owner=1):
    background = dict(
        weekly_period=weekly_period(),
        weekly_theme='rock',
        profile_revision=database.metadata(f'profile_revision:{owner}', 0),
        selection_revision=database.metadata(f'selection_revision:{owner}', 0),
        analysis_generation=database.metadata('analysis_generation', 0),
    )
    return dj.create(
        owner,
        'prepared',
        'energie',
        list(sources),
        sources,
        background=background,
    )


@pytest.mark.parametrize(
    ('utc', 'expected'),
    [
        ('2026-10-26T03:29:00+00:00', '2026-10-19'),
        ('2026-10-26T03:30:00+00:00', '2026-10-26'),
        ('2026-03-30T02:30:00+00:00', '2026-03-30'),
        ('2026-11-13T10:00:00+00:00', '2026-11-09'),
    ],
)
def test_monday_0430_paris_and_catchup_across_dst(utc, expected):
    assert weekly_period(datetime.fromisoformat(utc)) == expected


def test_weekly_never_consumes_the_two_manual_queue_slots(setup):
    database, dj, sources, _ = setup
    background = create_background(database, dj, sources)
    manual = dj.create(1, 'prepared', 'fete', list(sources), sources)
    live = dj.create(1, 'interactive', 'fete', list(sources), sources)
    assert dj.claim()['id'] == live['id']
    assert dj.get(1, background['id'])['state'] == 'queued'
    assert {row['id'] for row in dj.list(1)} == {manual['id'], live['id']}


def test_background_waits_for_native_activity_without_cancelling(setup):
    database, dj, sources, _ = setup
    pending = create_background(database, dj, sources)
    database.set_metadata('native_busy', True)
    assert dj.claim() is None
    assert dj.get(1, pending['id'])['state'] == 'queued'
    assert compute_budget.acquire(database, 'dj-background') is None
    database.set_metadata('native_busy', False)
    assert dj.claim()['id'] == pending['id']


@pytest.mark.parametrize(
    'change', ['disable', 'forget', 'selection', 'analysis']
)
def test_obsolete_weekly_work_cannot_be_claimed(setup, change):
    database, dj, sources, _ = setup
    pending = create_background(database, dj, sources)
    if change == 'disable':
        database.set_preferences(1, {'dj_weekly': False})
    elif change == 'forget':
        database.forget(1)
    elif change == 'selection':
        database.set_metadata('selection_revision:1', 1)
    else:
        database.set_metadata('analysis_generation', 1)
    assert dj.claim() is None
    assert dj.get(1, pending['id'])['state'] == 'cancelled'


def test_expired_weekly_work_resumes_with_a_different_workspace_and_token(
    setup,
):
    database, dj, sources, _ = setup
    pending = create_background(database, dj, sources)
    first = dj.claim()
    second = dj.claim(now=time.time() + 46)
    assert second['id'] == pending['id']
    assert first['lease_token'] != second['lease_token']
    assert first['render_workspace'] != second['render_workspace']
    assert not dj.defer_background(pending['id'], first['lease_token'])
    assert not dj.publish(pending['id'], first['lease_token'], 'ready')
    assert dj.get(1, pending['id'])['state'] == 'preparing'


def test_low_priority_ticket_yields_without_marking_a_dj_waiter(setup):
    database, dj, sources, _ = setup
    ticket = compute_budget.acquire(database, 'dj-background')
    assert ticket is not None
    assert database.metadata('compute_dj_waiting', 0) == 0
    dj.create(1, 'interactive', 'fete', list(sources), sources)
    assert not ticket.renew()
    ticket.release()


def test_worker_defers_weekly_render_and_keeps_sources_unchanged(
    setup, tmp_path, monkeypatch
):
    database, dj, sources, music = setup
    pending = create_background(database, dj, sources)
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in music.iterdir()
    }
    worker = DjWorker(database, tmp_path / 'models', [music], min_free=0)
    monkeypatch.setattr(worker, 'capabilities', lambda: None)
    private = []

    def interrupted(io):
        assert io.workspace.name != pending['id']
        (io.workspace / 'partial.m4a').write_bytes(b'private-partial')
        private.append(io.workspace)
        dj.create(2, 'interactive', 'fete', list(sources), sources)
        worker.checked = 0
        worker.checkpoint()
        pytest.fail('Weekly render ignored foreground priority')

    monkeypatch.setattr(worker, 'prepared', interrupted)
    try:
        assert worker.step()
        assert dj.get(1, pending['id'])['state'] == 'queued'
        assert not private[0].exists()
        assert dj.claim()['mode'] == 'interactive'
        assert {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in music.iterdir()
        } == before
    finally:
        worker.close()


def test_stale_worker_cleanup_cannot_remove_a_new_render_attempt(
    setup, tmp_path, monkeypatch
):
    database, dj, sources, music = setup
    pending = create_background(database, dj, sources)
    worker = DjWorker(database, tmp_path / 'models', [music], min_free=0)
    monkeypatch.setattr(worker, 'capabilities', lambda: None)
    new_assets = []

    def replaced(io):
        (io.workspace / 'partial.m4a').write_bytes(b'old')
        new_job = dj.claim(now=time.time() + 46)
        destination = worker.cache / new_job['render_workspace']
        destination.mkdir(mode=0o700)
        target = destination / 'set.m4a'
        target.write_bytes(b'new-attempt')
        new_assets.append(target)
        worker.checked = 0
        worker.checkpoint()

    monkeypatch.setattr(worker, 'prepared', replaced)
    try:
        assert worker.step()
        assert new_assets[0].read_bytes() == b'new-attempt'
        assert dj.get(1, pending['id'])['state'] == 'preparing'
    finally:
        worker.close()


def seed(database, owner, ids):
    with database.connect() as db:
        db.execute(
            'INSERT INTO playlists VALUES (?,?,?,?,?,?)',
            (
                owner,
                'weekly',
                'rock',
                weekly_period(),
                json.dumps(ids),
                time.time(),
            ),
        )


def test_scheduler_is_idempotent_round_robins_and_filters_owner_catalog(setup):
    database, dj, sources, _ = setup
    for owner in (1, 2):
        seed(database, owner, ['one', 'two', 'foreign'])
    calls = []

    def rows_for(owner):
        return [{'id': 'one', 'duration': 180}, {'id': 'two', 'duration': 180}]

    def sources_for(owner, ids):
        assert ids == ['one', 'two']
        calls.append(owner)
        return sources

    assert enqueue_due(database, lambda uid: True, rows_for, sources_for) == 1
    assert enqueue_due(database, lambda uid: True, rows_for, sources_for) == 0
    with database.connect() as db:
        first = db.execute('SELECT id,owner FROM dj_sessions').fetchone()
        assert first['owner'] == 1
    dj.stop(1, first['id'])
    assert enqueue_due(database, lambda uid: True, rows_for, sources_for) == 1
    assert calls == [1, 2]
    with database.connect() as db:
        assert db.execute('SELECT count(*) FROM jobs').fetchone()[0] == 0


def test_scheduler_rechecks_profile_revision_after_source_resolution(setup):
    database, _, sources, _ = setup
    seed(database, 1, list(sources))

    def sources_for(owner, ids):
        database.forget(owner)
        return sources

    assert (
        enqueue_due(
            database,
            lambda uid: True,
            lambda uid: [{'id': tid} for tid in sources],
            sources_for,
        )
        == 0
    )
    with database.connect() as db:
        assert (
            db.execute('SELECT count(*) FROM dj_sessions').fetchone()[0] == 0
        )


def test_scheduler_is_default_off_without_reading_sources(tmp_path):
    from downtify.music_ai.store import Store

    database = Store(tmp_path / 'derived.db')

    def forbidden(*args):
        pytest.fail('Disabled weekly scheduler touched user or source data')

    assert enqueue_due(database, forbidden, forbidden, forbidden) == 0


@pytest.mark.parametrize('metrics_failure', [False, True])
def test_weekly_worker_publishes_real_audio_in_its_private_attempt_workspace(
    setup, tmp_path, monkeypatch, metrics_failure
):
    from dataclasses import asdict

    from test_dj_audio import tone

    from downtify.music_ai.dj_plan import Profile
    from downtify.music_ai.worker import signature

    database, dj, sources, music = setup
    results = {}
    rows = {}
    for index, identity in enumerate(sources):
        path = music / f'{identity}.wav'
        tone(path, 440 + index * 110)
        sources[identity].update(
            path=str(path), source_version=list(signature(path))
        )
        results[identity] = {
            'profile': asdict(
                Profile(identity, 8, 120, 0.95, (0, 2, 4, 6), 0.5)
            ),
            'loudness': {'input_i': -18, 'input_tp': -3},
        }
        rows[identity] = {'id': identity, 'title': identity, 'file': path.name}
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in music.iterdir()
    }
    pending = create_background(database, dj, sources)
    worker = DjWorker(database, tmp_path / 'models', [music], min_free=0)
    monkeypatch.setattr(worker, 'capabilities', lambda: None)
    if metrics_failure:

        def failed_metric(*args, **kwargs):
            raise RuntimeError('Synthetic metric write failure after commit')

        monkeypatch.setattr(
            'downtify.music_ai.dj_readiness.record', failed_metric
        )
    # Exercise the real prepared renderer without loading or qualifying a model.
    monkeypatch.setattr(worker, 'analyzed_sources', lambda io: results)
    try:
        assert worker.step()
    finally:
        worker.close()
    ready = dj.get(1, pending['id'])
    assert ready['state'] == 'ready'
    assert ready['asset_workspace'] != ready['id']
    asset = worker.cache / ready['asset_workspace'] / 'set.m4a'
    assert asset.is_file()
    assert asset.stat().st_size > 1000
    assert ready['duration'] > 8
    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in music.iterdir()
    } == before

    assert_private_audio(database, dj, ready, rows, asset, monkeypatch)


def assert_private_audio(database, dj, ready, rows, asset, monkeypatch):  # noqa: PLR0913, PLR0917 -- Verify one end-to-end private media response.
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient

    from downtify.music_ai import dj_routes, routes

    monkeypatch.setattr(routes, 'store', lambda: database)
    monkeypatch.setattr(dj_routes, 'database', lambda: dj)
    monkeypatch.setattr(
        dj_routes, 'visible_session', lambda request, session: rows
    )

    def owner(request):
        uid = int(request.headers.get('x-test-user', '0'))
        if not uid:
            raise HTTPException(401, 'Sign in required')
        return uid

    monkeypatch.setattr(routes, 'owner', owner)
    app = FastAPI()
    app.include_router(dj_routes.router, prefix='/api/v1/music-ai')
    with TestClient(app) as http:
        url = f'/api/v1/music-ai/dj/sessions/{ready["id"]}/media'
        assert http.get(url).status_code == 401
        assert http.get(url, headers={'x-test-user': '2'}).status_code == 404
        response = http.get(
            url, headers={'x-test-user': '1', 'Range': 'bytes=0-31'}
        )
        assert response.status_code == 206
        assert response.content == asset.read_bytes()[:32]
        assert response.headers['cache-control'] == 'private, no-store'
        public = dj_routes.public(ready, rows)
        assert 'asset_workspace' not in public
        assert 'render_workspace' not in public


@pytest.mark.parametrize(
    'change',
    ['disable', 'forget', 'selection', 'analysis', 'native', 'foreground'],
)
def test_weekly_publish_rechecks_permissions_and_priority_in_its_transaction(
    setup, change
):
    database, dj, sources, _ = setup
    pending = create_background(database, dj, sources)
    job = dj.claim()
    if change == 'disable':
        database.set_preferences(1, {'dj_weekly': False})
    elif change == 'forget':
        database.forget(1)
    elif change == 'selection':
        database.set_metadata('selection_revision:1', 1)
    elif change == 'analysis':
        database.set_metadata('analysis_generation', 1)
    elif change == 'native':
        database.set_metadata('native_busy', True)
    else:
        dj.create(2, 'interactive', 'fete', list(sources), sources)
    assert not dj.publish(
        pending['id'],
        job['lease_token'],
        'ready',
        {'asset_workspace': job['render_workspace']},
    )
    assert dj.get(1, pending['id'])['state'] != 'ready'


def test_legacy_worker_cannot_accept_new_weekly_jobs(setup):
    database, _, _, _ = setup
    database.set_metadata('dj', {'prepared_ready': True, 'seen': time.time()})

    def forbidden(*args):
        pytest.fail('Legacy worker caused catalog access')

    assert enqueue_due(database, forbidden, forbidden, forbidden) == 0


def test_deleted_automatic_set_is_not_regenerated_each_sweep(setup):
    database, dj, sources, _ = setup
    seed(database, 1, list(sources))

    def rows(owner):
        return [{'id': tid} for tid in sources]

    assert (
        enqueue_due(
            database, lambda owner: True, rows, lambda owner, ids: sources
        )
        == 1
    )
    with database.connect() as db:
        identity = db.execute('SELECT id FROM dj_sessions').fetchone()[0]
    dj.discard(1, identity)
    dj.deleted(identity)
    assert (
        enqueue_due(
            database, lambda owner: True, rows, lambda owner, ids: sources
        )
        == 0
    )
