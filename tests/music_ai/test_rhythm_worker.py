from datetime import datetime

import pytest
from ai_test_support import opted_in_store

from downtify.music_ai import compute_budget
from downtify.music_ai.rhythm_queue import enqueue, seed_missing, weekly_check
from downtify.music_ai.rhythm_worker import RhythmWorker
from downtify.music_ai.worker import signature


@pytest.fixture
def rhythm(tmp_path, monkeypatch):
    music = tmp_path / 'music'
    music.mkdir()
    path = music / 'one.audio'
    path.write_bytes(b'original, never an analysis output')
    database = opted_in_store(tmp_path / 'derived.db')
    database.set_preferences(-1, {'dj_prepared': True})
    row = {
        'id': 'one',
        'file': 'one.audio',
        'fingerprint': 'fp',
        'artist': 'Artist',
    }
    database.observe([row])
    with database.connect() as db:
        db.execute('INSERT INTO catalog_live VALUES (?)', ('one',))
    version = list(signature(path))
    database.observe_source('one', version)
    worker = RhythmWorker(database, tmp_path / 'models', [music], min_free=0)
    monkeypatch.setattr(compute_budget, 'pressure_high', lambda: False)
    calls = []

    def analyze(track, source, io, checkpoint):
        checkpoint()
        calls.append(track)
        return {
            'profile': dict(
                id=track,
                duration=120,
                bpm=120,
                confidence=0.9,
                downbeats=[0, 2, 4],
                energy=0.5,
            ),
            'loudness': {'input_i': -18, 'input_tp': -3},
            'source_version': version,
        }

    monkeypatch.setattr(worker.runner, 'analysis_result', analyze)
    return database, worker, row, path, version, calls


def test_initial_queue_is_bounded_and_does_not_reschedule_queued_or_valid_profiles(
    rhythm,
):
    database, worker, row, path, version, calls = rhythm
    assert seed_missing(database, worker.runner.analysis, limit=1) == 1
    assert enqueue(database, worker.runner.analysis, row, path, version)
    assert not enqueue(database, worker.runner.analysis, row, path, version)
    assert seed_missing(database, worker.runner.analysis, limit=1) == 0
    before = path.read_bytes()
    assert worker.step()
    assert calls == ['one']
    assert path.read_bytes() == before
    assert worker.runner.dj.profile(
        'one', worker.runner.analysis, 'fp', version
    )
    assert not enqueue(database, worker.runner.analysis, row, path, version)
    assert seed_missing(database, worker.runner.analysis) == 0
    assert not worker.step()
    assert calls == ['one']


def test_native_work_preempts_and_requeues_without_consuming_an_attempt(
    rhythm, monkeypatch
):
    database, worker, row, path, version, calls = rhythm
    enqueue(database, worker.runner.analysis, row, path, version)

    def yield_to_native(*args):
        database.set_metadata('native_busy', True)
        args[-1]()

    monkeypatch.setattr(worker.runner, 'analysis_result', yield_to_native)
    assert not worker.step()
    with database.connect() as db:
        job = db.execute(
            "SELECT state,attempts FROM jobs WHERE kind='rhythm'"
        ).fetchone()
        assert tuple(job) == ('queued', 0)
        assert (
            db.execute('SELECT count(*) FROM dj_profiles').fetchone()[0] == 0
        )
        assert (
            db.execute('SELECT count(*) FROM compute_lease').fetchone()[0] == 0
        )
    assert not list(worker.runner.cache.iterdir())


def test_dj_waiting_prevents_background_admission(rhythm):
    import time

    database, worker, row, path, version, calls = rhythm
    enqueue(database, worker.runner.analysis, row, path, version)
    database.set_metadata('compute_dj_waiting', time.time() + 30)
    assert not worker.step()
    assert calls == []
    with database.connect() as db:
        assert (
            db.execute(
                "SELECT state FROM jobs WHERE kind='rhythm'"
            ).fetchone()[0]
            == 'queued'
        )


def test_changed_fingerprint_cannot_publish_a_late_profile(
    rhythm, monkeypatch
):
    database, worker, row, path, version, calls = rhythm
    enqueue(database, worker.runner.analysis, row, path, version)
    original = worker.runner.analysis_result

    def late(*args):
        result = original(*args)
        database.observe([{**row, 'fingerprint': 'changed'}])
        return result

    monkeypatch.setattr(worker.runner, 'analysis_result', late)
    assert not worker.step()
    with database.connect() as db:
        assert (
            db.execute('SELECT count(*) FROM dj_profiles').fetchone()[0] == 0
        )


def test_changed_source_queues_only_its_new_version(rhythm):
    database, worker, row, path, version, calls = rhythm
    enqueue(database, worker.runner.analysis, row, path, version)
    assert worker.step()
    path.write_bytes(path.read_bytes() + b'new version')
    changed = list(signature(path))
    database.observe_source('one', changed)
    assert seed_missing(database, worker.runner.analysis) == 1
    assert enqueue(database, worker.runner.analysis, row, path, changed)
    with database.connect() as db:
        assert (
            db.execute(
                "SELECT count(*) FROM jobs WHERE kind='rhythm'"
            ).fetchone()[0]
            == 2
        )


def test_sunday_retry_has_catchup_dst_idempotence_and_keeps_completed_analyses(
    rhythm,
):
    database, worker, row, path, version, calls = rhythm
    model = worker.runner.analysis
    assert weekly_check(
        database,
        model,
        now=datetime.fromisoformat('2026-10-19T12:00:00+02:00'),
    )
    enqueue(database, model, row, path, version)
    job = database.claim(kind='rhythm')
    database.finish(job, 'failed', 'temporary')
    assert not weekly_check(
        database,
        model,
        now=datetime.fromisoformat('2026-10-25T01:59:00+02:00'),
    )
    assert weekly_check(
        database,
        model,
        now=datetime.fromisoformat('2026-10-25T02:00:00+02:00'),
    )
    assert not weekly_check(
        database,
        model,
        now=datetime.fromisoformat('2026-10-25T02:00:00+01:00'),
    )
    assert worker.step()
    assert weekly_check(
        database,
        model,
        now=datetime.fromisoformat('2026-11-02T12:00:00+01:00'),
    )
    assert not enqueue(database, model, row, path, version)
    assert calls == ['one']


def test_disabled_modules_do_not_claim_rhythmic_work(rhythm):
    database, worker, row, path, version, calls = rhythm
    enqueue(database, worker.runner.analysis, row, path, version)
    database.set_preferences(
        -1, {'dj_prepared': False, 'dj_interactive': False}
    )
    assert not worker.step()
    assert calls == []
    with database.connect() as db:
        assert (
            db.execute(
                "SELECT state FROM jobs WHERE kind='rhythm'"
            ).fetchone()[0]
            == 'queued'
        )


def test_inventory_separates_vectors_from_current_rhythmic_profiles(rhythm):
    from downtify.music_ai.rhythm_queue import coverage

    database, worker, row, path, version, calls = rhythm
    database.set_metadata('model', {'id': 'clap-model', 'ready': True})
    assert database.put_analysis(
        'one', 'fp', 'clap-model', [1.0] + [0.0] * 511
    )
    enqueue(database, worker.runner.analysis, row, path, version)
    before = coverage(database)
    assert before['clap']['analyzed'] == 1
    assert before['rhythm']['profiles'] == 0
    assert before['rhythm']['fields']['tempo'] == 0
    assert worker.step()
    measured = coverage(database)
    assert measured['observed_tracks'] == 1
    assert measured['clap']['analyzed'] == 1
    assert measured['rhythm']['profiles'] == 1
    assert measured['rhythm']['fields']['tempo'] == 1
    assert measured['rhythm']['fields']['bars'] == 1
    assert measured['rhythm']['fields']['beats'] == 0
    assert measured['source_scan'] is False
    database.observe([{**row, 'fingerprint': 'changed'}])
    assert coverage(database)['rhythm']['profiles'] == 0


def test_changed_generation_is_retired_and_cannot_block_new_work(
    rhythm, monkeypatch
):
    database, worker, row, path, version, calls = rhythm
    enqueue(database, worker.runner.analysis, row, path, version)
    original = worker.runner.analysis_result

    def invalidate(*args):
        result = original(*args)
        database.set_metadata('analysis_generation', 1)
        return result

    monkeypatch.setattr(worker.runner, 'analysis_result', invalidate)
    assert not worker.step()
    assert worker.step()
    with database.connect() as db:
        assert (
            db.execute(
                "SELECT state FROM jobs WHERE kind='rhythm'"
            ).fetchone()[0]
            == 'done'
        )
        assert (
            db.execute('SELECT count(*) FROM dj_profiles').fetchone()[0] == 0
        )
    assert enqueue(database, worker.runner.analysis, row, path, version)
    assert worker.step()
    assert worker.runner.dj.profile(
        'one', worker.runner.analysis, 'fp', version
    )
