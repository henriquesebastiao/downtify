"""Normalization policy, durable queue and source replacement behavior."""

import threading
import time

import pytest

from downtify.library_catalog import LibraryContext
from downtify.loudness import LoudnessAnalyzer, normalization_gain


@pytest.mark.parametrize(
    ('integrated', 'peak', 'expected'),
    [
        (-30, -20, 12),
        (-8, -0.5, -10),
        (-40, -5, 4),
        (-80, -90, 12),
        (float('-inf'), float('-inf'), 0),
    ],
)
def test_gain_respects_target_boost_limit_and_peak(integrated, peak, expected):
    assert normalization_gain(integrated, peak) == expected


def wait_idle(runner):
    deadline = time.monotonic() + 5
    while runner.status()['active']:
        assert time.monotonic() < deadline
        time.sleep(0.01)


def test_cache_reuse_and_replacement_never_modify_audio(tmp_path, monkeypatch):
    root = tmp_path / 'music'
    root.mkdir()
    audio = root / 'song.mp3'
    audio.write_bytes(b'original audio')
    ctx = LibraryContext(download_dir=root)
    runner = LoudnessAnalyzer(tmp_path / 'library.db', lambda: ctx)
    calls = []

    def measure(path):
        calls.append(path)
        return {
            'state': 'ready',
            'gain_db': 6,
            'integrated_lufs': -24,
            'true_peak_dbtp': -10,
            'algorithm_version': 1,
        }

    monkeypatch.setattr(runner, '_measure', measure)
    assert runner.status()['total'] == 0
    assert not runner.status()['active']
    assert runner.info('song.mp3', audio) is None
    runner.start(['song.mp3'])
    wait_idle(runner)
    assert runner.info('song.mp3', audio)['gain_db'] == 6
    assert audio.read_bytes() == b'original audio'
    runner.start(['song.mp3'])
    wait_idle(runner)
    assert len(calls) == 1
    audio.write_bytes(b'replacement audio with a new size')
    assert runner.info('song.mp3', audio) is None
    runner.close()


def test_pause_and_restart_preserve_pending_work_without_auto_resume(
    tmp_path, monkeypatch
):
    root = tmp_path / 'music'
    root.mkdir()
    for name in ['one.mp3', 'two.mp3']:
        (root / name).write_bytes(b'audio')
    ctx = LibraryContext(download_dir=root)
    db = tmp_path / 'library.db'
    runner = LoudnessAnalyzer(db, lambda: ctx)
    started, release = threading.Event(), threading.Event()

    def measure(path):
        started.set()
        assert release.wait(5)
        return {'state': 'silent', 'gain_db': 0, 'algorithm_version': 1}

    monkeypatch.setattr(runner, '_measure', measure)
    runner.start(['one.mp3', 'two.mp3'])
    assert started.wait(5)
    runner.pause()
    release.set()
    wait_idle(runner)
    assert runner.status()['done'] == 1
    assert runner.status()['pending'] == 1
    runner.close()
    restarted = LoudnessAnalyzer(db, lambda: ctx)
    assert not restarted.status()['active']
    assert restarted.status()['pending'] == 1
    monkeypatch.setattr(restarted, '_measure', measure)
    restarted.resume()
    wait_idle(restarted)
    assert restarted.status()['done'] == 2
    restarted.close()
