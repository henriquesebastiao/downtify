import sqlite3
from contextlib import contextmanager

import pytest
from ai_test_support import opted_in_store

from downtify.music_ai import sqlite_busy
from downtify.music_ai.dj_worker import DjWorker
from downtify.music_ai.worker import AnalysisService, Worker


class Encoder:
    identity = 'synthetic'

    def encode_text(self, _):
        return [1] + [0] * 511


def test_unchanged_catalog_remains_readable_while_another_writer_holds_the_database(
    tmp_path, monkeypatch
):
    store = opted_in_store(tmp_path / 'derived.db')
    rows = [
        {'id': str(index), 'fingerprint': str(index), 'title': f'Item{index}'}
        for index in range(600)
    ]
    store.observe(rows)
    original = store.connect

    @contextmanager
    def bounded():
        with original() as db:
            db.execute('PRAGMA busy_timeout=50')
            yield db

    monkeypatch.setattr(store, 'connect', bounded)
    with sqlite3.connect(store.path) as writer:
        writer.execute('BEGIN IMMEDIATE')
        writer.execute("INSERT INTO metadata VALUES ('writer','true')")
        store.observe(rows)  # No writer reservation for an unchanged snapshot.
    assert store.metadata('writer') is True
    rows[-1]['fingerprint'] = 'replacement'
    store.observe(rows)
    with store.connect() as db:
        assert (
            db.execute(
                "SELECT fingerprint FROM tracks WHERE id='599'"
            ).fetchone()[0]
            == 'replacement'
        )


def test_analysis_lease_writes_are_bounded_and_shutdown_is_still_checked_at_publication(
    tmp_path, monkeypatch
):
    root = tmp_path / 'music'
    root.mkdir()
    (root / 'source.wav').write_bytes(b'synthetic')
    store = opted_in_store(tmp_path / 'derived.db')
    store.observe([{'id': 'one', 'fingerprint': 'first'}])
    store.enqueue(
        'job',
        'analysis',
        {
            'track': 'one',
            'fingerprint': 'first',
            'model': 'synthetic',
            'path': str(root / 'source.wav'),
        },
    )
    renewals = []
    original = store.renew
    monkeypatch.setattr(
        store, 'renew', lambda job: renewals.append(1) or original(job)
    )

    class BusyCallbacks(Encoder):
        def encode_audio(self, path, checkpoint):
            for _ in range(500):
                checkpoint()
            store.set_preferences(
                -1,
                {
                    'similarity': False,
                    'personalization': False,
                    'daily': False,
                    'weekly': False,
                },
            )
            return [1] + [0] * 511

    assert not Worker(store, BusyCallbacks(), [root]).step()
    assert len(renewals) <= 2
    assert not store.vectors('synthetic', {'one'})


def test_transient_lock_does_not_discard_the_loaded_encoder_or_cached_model(
    tmp_path, monkeypatch
):
    store = opted_in_store(tmp_path / 'derived.db')
    loads = []
    service = AnalysisService(
        store, lambda: loads.append(1) or Encoder(), [tmp_path]
    )
    assert not service.step()
    original = service.worker
    monkeypatch.setattr(
        original,
        'step',
        lambda: (_ for _ in ()).throw(
            sqlite3.OperationalError('database is locked')
        ),
    )
    assert not service.step()
    assert service.worker is original
    assert len(loads) == 1
    assert store.metadata('model')['ready']


def test_erasure_then_immediate_resume_reinitializes_moods_at_the_new_generation(
    tmp_path,
):
    store = opted_in_store(tmp_path / 'derived.db')
    service = AnalysisService(store, Encoder, [tmp_path])
    assert not service.step()
    previous = service.worker
    store.clear_analyses()
    store.set_metadata('analysis_paused', False)
    assert not service.step()
    assert service.worker is not previous
    assert store.metadata('model')['ready']
    assert service.worker_generation == 1


def test_busy_retry_does_not_hide_other_operational_errors(monkeypatch):
    calls = []
    monkeypatch.setattr(sqlite_busy.time, 'sleep', lambda _: None)

    def work():
        calls.append(1)
        if len(calls) == 1:
            raise sqlite3.OperationalError('database is locked')
        return 'ready'

    assert sqlite_busy.retry_busy(work) == 'ready'
    assert len(calls) == 2
    with pytest.raises(sqlite3.OperationalError, match='malformed'):
        sqlite_busy.retry_busy(
            lambda: (_ for _ in ()).throw(
                sqlite3.OperationalError('database disk image is malformed')
            )
        )


def test_dj_supervision_waits_on_contention_without_restarting_or_claiming_health(
    tmp_path, monkeypatch
):
    worker = DjWorker(
        opted_in_store(tmp_path / 'derived.db'), tmp_path, [tmp_path]
    )
    monkeypatch.setattr(
        worker,
        'step',
        lambda: (_ for _ in ()).throw(
            sqlite3.OperationalError('database is locked')
        ),
    )
    assert not worker.run_cycle()
    assert worker.database.metadata('dj') is None
