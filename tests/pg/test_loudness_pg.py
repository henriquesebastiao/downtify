"""LoudnessAnalyzer on both backends: the job queue, the measurement cache
and crash recovery. FFmpeg never runs here: ``_measure`` is replaced."""

from __future__ import annotations

import threading
import time

from downtify.library_catalog import LibraryContext
from downtify.loudness import LoudnessAnalyzer
from tests.db.helpers import execute, query


def _rows(db, sql, *params):
    return [tuple(row) for row in query(db, sql, *params)]


def _library(root, names):
    root.mkdir(parents=True, exist_ok=True)
    for name in names:
        (root / name).write_bytes(b'audio ' + name.encode())
    return LibraryContext(download_dir=root)


def _wait_idle(runner):
    deadline = time.monotonic() + 5
    while runner.status()['active']:
        assert time.monotonic() < deadline
        time.sleep(0.01)


def _measurement(path):
    return {
        'state': 'ready',
        'gain_db': 6.0,
        'integrated_lufs': -24.0,
        'true_peak_dbtp': -10.0,
        'algorithm_version': 1,
    }


def _recording_measure(calls):
    def measure(path):
        calls.append(path.name)
        return _measurement(path)

    return measure


def test_status_of_an_empty_queue(backend_db, tmp_path):
    ctx = _library(tmp_path / 'music', [])
    runner = LoudnessAnalyzer(backend_db, lambda: ctx, workers=1)
    try:
        assert runner.status() == {
            'active': False,
            'pause_requested': False,
            'paused': False,
            'total': 0,
            'done': 0,
            'failed': 0,
            'pending': 0,
            'running': 0,
            'workers': 1,
        }
        assert runner.info('missing.mp3', tmp_path / 'missing.mp3') is None
    finally:
        runner.close()


def test_start_measures_in_position_order_and_ignores_duplicates(
    backend_db, tmp_path, monkeypatch
):
    ctx = _library(tmp_path / 'music', ['a.mp3', 'b.mp3'])
    runner = LoudnessAnalyzer(backend_db, lambda: ctx, workers=1)
    calls = []
    monkeypatch.setattr(runner, '_measure', _recording_measure(calls))
    try:
        runner.start(['a.mp3', 'b.mp3', 'a.mp3'])
        _wait_idle(runner)

        assert calls == ['a.mp3', 'b.mp3']
        assert _rows(
            backend_db,
            'SELECT file, position, status FROM loudness_jobs '
            'ORDER BY position',
        ) == [('a.mp3', 0, 'done'), ('b.mp3', 1, 'done')]
        status = runner.status()
        assert status['total'] == 2
        assert status['done'] == 2
        assert status['pending'] == 0
        assert status['failed'] == 0
        assert status['running'] == 0
        assert not status['paused']
    finally:
        runner.close()


def test_start_replaces_the_previous_queue(backend_db, tmp_path, monkeypatch):
    ctx = _library(tmp_path / 'music', ['a.mp3', 'c.mp3'])
    runner = LoudnessAnalyzer(backend_db, lambda: ctx, workers=1)
    monkeypatch.setattr(runner, '_measure', _recording_measure([]))
    try:
        runner.start(['a.mp3'])
        _wait_idle(runner)
        runner.start(['c.mp3'])
        _wait_idle(runner)

        assert _rows(backend_db, 'SELECT file, status FROM loudness_jobs') == [
            ('c.mp3', 'done')
        ]
    finally:
        runner.close()


def test_measurement_is_stored_and_reused_until_the_file_changes(
    backend_db, tmp_path, monkeypatch
):
    root = tmp_path / 'music'
    ctx = _library(root, ['song.mp3'])
    audio = root / 'song.mp3'
    runner = LoudnessAnalyzer(backend_db, lambda: ctx, workers=1)
    calls = []
    monkeypatch.setattr(runner, '_measure', _recording_measure(calls))
    try:
        assert runner.info('song.mp3', audio) is None
        runner.start(['song.mp3'])
        _wait_idle(runner)

        profile = runner.info('song.mp3', audio)
        assert profile['gain_db'] == 6.0
        assert profile['integrated_lufs'] == -24.0
        assert profile['true_peak_dbtp'] == -10.0
        assert profile['source_size'] == audio.stat().st_size
        assert {'fingerprint', 'source_etag'} <= set(profile)
        assert audio.read_bytes() == b'audio song.mp3'

        # Same file: the stored measurement answers, FFmpeg is not run.
        runner.start(['song.mp3'])
        _wait_idle(runner)
        assert calls == ['song.mp3']
        assert runner.status()['done'] == 1

        # A replaced file no longer matches the stored signature.
        audio.write_bytes(b'replacement audio with a new size')
        assert runner.info('song.mp3', audio) is None
    finally:
        runner.close()


def test_a_failed_job_is_counted_and_the_queue_continues(
    backend_db, tmp_path, monkeypatch
):
    ctx = _library(tmp_path / 'music', ['ok.mp3'])
    runner = LoudnessAnalyzer(backend_db, lambda: ctx, workers=1)
    calls = []
    monkeypatch.setattr(runner, '_measure', _recording_measure(calls))
    try:
        runner.start(['missing.mp3', 'ok.mp3'])
        _wait_idle(runner)

        assert calls == ['ok.mp3']
        status = runner.status()
        assert status['failed'] == 1
        assert status['done'] == 1
        assert status['pending'] == 0
        assert _rows(
            backend_db,
            'SELECT file, status FROM loudness_jobs ORDER BY position',
        ) == [('missing.mp3', 'failed'), ('ok.mp3', 'done')]
        assert (
            runner.info('missing.mp3', tmp_path / 'music' / 'missing.mp3')
            is None
        )
    finally:
        runner.close()


def test_pause_keeps_pending_jobs_and_a_restart_recovers_running_ones(
    backend_db, tmp_path, monkeypatch
):
    ctx = _library(tmp_path / 'music', ['one.mp3', 'two.mp3'])
    runner = LoudnessAnalyzer(backend_db, lambda: ctx, workers=1)
    started, release = threading.Event(), threading.Event()

    def measure(path):
        started.set()
        assert release.wait(5)
        return _measurement(path)

    monkeypatch.setattr(runner, '_measure', measure)
    runner.start(['one.mp3', 'two.mp3'])
    try:
        assert started.wait(5)
        runner.pause()
        release.set()
        _wait_idle(runner)
        status = runner.status()
        assert status['done'] == 1
        assert status['pending'] == 1
        assert status['pause_requested']
        assert status['paused']
    finally:
        runner.close()

    # A crash while "two.mp3" was running leaves it marked running.
    execute(
        backend_db,
        "UPDATE loudness_jobs SET status='running' WHERE file=?",
        'two.mp3',
    )
    restarted = LoudnessAnalyzer(backend_db, lambda: ctx, workers=1)
    try:
        status = restarted.status()
        assert not status['active']
        assert status['running'] == 0
        assert status['pending'] == 1
        assert status['done'] == 1

        calls = []
        monkeypatch.setattr(restarted, '_measure', _recording_measure(calls))
        restarted.resume()
        _wait_idle(restarted)
        assert calls == ['two.mp3']
        assert restarted.status()['done'] == 2
    finally:
        restarted.close()
