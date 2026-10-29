"""CPU budgets, concurrent pause/restart and incremental analysis."""

import threading
import time
from collections import Counter
from pathlib import Path

from downtify import loudness
from downtify.library_catalog import LibraryContext
from downtify.loudness import LoudnessAnalyzer


def wait_idle(runner):
    deadline = time.monotonic() + 5
    while runner.status()['active']:
        assert time.monotonic() < deadline
        time.sleep(0.01)


def test_worker_budget_uses_quota_and_never_all_host_cpus(monkeypatch):
    monkeypatch.setattr(loudness.os, 'cpu_count', lambda: 6)
    monkeypatch.setattr(
        loudness.os,
        'sched_getaffinity',
        lambda _: set(range(6)),
        raising=False,
    )
    original = Path.read_text
    quota = ['200000 100000']

    def read(path, *args, **kwargs):
        if path.as_posix() == '/sys/fs/cgroup/cpu.max':
            return quota[0]
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', read)
    assert loudness.analysis_workers() == 2
    quota[0] = '50000 100000'
    assert loudness.analysis_workers() == 1
    quota[0] = 'max 100000'
    assert loudness.analysis_workers() == 2


def test_two_workers_claim_distinct_jobs_and_pause_without_losing_queue(
    tmp_path, monkeypatch
):
    for name in ['a.mp3', 'b.mp3', 'c.mp3', 'd.mp3']:
        (tmp_path / name).write_bytes(b'fixture audio')
    runner = LoudnessAnalyzer(
        tmp_path / 'test.db',
        lambda: LibraryContext(download_dir=tmp_path),
        workers=2,
    )
    started, release = threading.Event(), threading.Event()
    lock = threading.Lock()
    calls = []

    def measure(path):
        with lock:
            calls.append(path.name)
            if len(calls) == 2:
                started.set()
        assert release.wait(5)
        return {'state': 'silent', 'gain_db': 0, 'algorithm_version': 1}

    monkeypatch.setattr(runner, '_measure', measure)
    try:
        runner.start(['a.mp3', 'b.mp3', 'c.mp3', 'd.mp3'])
        assert started.wait(5)
        assert runner.status()['running'] == 2
        assert len(set(calls)) == 2
        runner.pause()
        release.set()
        wait_idle(runner)
        assert runner.status()['done'] == 2
        assert runner.status()['pending'] == 2
        runner.resume()
        wait_idle(runner)
        assert runner.status()['done'] == 4
        assert Counter(calls) == Counter(['a.mp3', 'b.mp3', 'c.mp3', 'd.mp3'])
    finally:
        release.set()
        runner.close()


def test_new_downloads_only_analyze_new_or_replaced_files(
    tmp_path, monkeypatch
):
    (tmp_path / 'old.mp3').write_bytes(b'unchanged fixture')
    runner = LoudnessAnalyzer(
        tmp_path / 'test.db',
        lambda: LibraryContext(download_dir=tmp_path),
        workers=1,
    )
    calls = []

    def measure(path):
        calls.append(path.name)
        return {'state': 'silent', 'gain_db': 0, 'algorithm_version': 1}

    monkeypatch.setattr(runner, '_measure', measure)
    try:
        runner.start(['old.mp3'])
        wait_idle(runner)
        (tmp_path / 'new.mp3').write_bytes(b'new fixture')
        runner.start(['old.mp3', 'new.mp3'])
        wait_idle(runner)
        assert Counter(calls) == Counter(['old.mp3', 'new.mp3'])
        (tmp_path / 'old.mp3').write_bytes(
            b'replaced fixture with a changed size'
        )
        runner.start(['old.mp3', 'new.mp3'])
        wait_idle(runner)
        assert Counter(calls) == Counter(['old.mp3', 'old.mp3', 'new.mp3'])
        assert (tmp_path / 'new.mp3').read_bytes() == b'new fixture'
    finally:
        runner.close()
