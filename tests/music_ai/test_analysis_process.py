import contextlib
import json
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from downtify.music_ai.analysis_process import (
    MAX_INPUT,
    MAX_OUTPUT,
    AnalysisProcess,
)
from downtify.music_ai.dj_audio import AudioError

ECHO = """
import json, os, sys
counter = 0
for line in sys.stdin:
    request = json.loads(line)
    counter += 1
    print(json.dumps({'request_id': request['request_id'],
                      'result': {'pid': os.getpid(), 'count': counter,
                                 'track': request['payload'].get('id')}}), flush=True)
"""


def client(code=ECHO, *args, timeout=3):
    return AnalysisProcess(
        [sys.executable, '-u', '-c', code, *args], timeout=timeout
    )


def test_two_tracks_reuse_one_analysis_process():
    process = client()
    try:
        first = process.analyze({'id': 'one'}, lambda: None)
        second = process.analyze({'id': 'two'}, lambda: None)
        assert first['pid'] == second['pid']
        assert [first['count'], second['count']] == [1, 2]
        assert [first['track'], second['track']] == ['one', 'two']
    finally:
        process.close()


def test_concurrent_preparations_cannot_swap_their_responses():
    process = client()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda key: process.analyze({'id': key}, lambda: None),
                    ['one', 'two'],
                )
            )
        assert [row['track'] for row in results] == ['one', 'two']
        assert len({row['pid'] for row in results}) == 1
        assert {row['count'] for row in results} == {1, 2}
    finally:
        process.close()


def test_wrong_generation_response_is_rejected_and_process_is_retired():
    process = client(
        "import json,sys; r=json.loads(sys.stdin.readline()); print(json.dumps({'request_id':'old','result':{}}),flush=True)"
    )
    try:
        with pytest.raises(AudioError, match='analysis_response_invalid'):
            process.analyze({'id': 'one'}, lambda: None)
        assert process._process is None
        process.arguments = [sys.executable, '-u', '-c', ECHO]
        assert process.analyze({'id': 'fresh'}, lambda: None)['count'] == 1
    finally:
        process.close()


def test_request_and_response_sizes_are_bounded():
    process = client()
    try:
        with pytest.raises(AudioError, match='unexpected_audio_input'):
            process.analyze({'id': 'x' * MAX_INPUT}, lambda: None)
        assert process._process is None
        process.arguments = [
            sys.executable,
            '-u',
            '-c',
            f"import sys;sys.stdin.readline();print('x'*{MAX_OUTPUT + 1},flush=True)",
        ]
        with pytest.raises(AudioError, match='unexpected_audio_output'):
            process.analyze({'id': 'one'}, lambda: None)
        assert process._process is None
    finally:
        process.close()


def test_timeout_cannot_deliver_a_late_result_into_a_fresh_request():
    process = client(
        'import sys,time;sys.stdin.readline();time.sleep(60)', timeout=0.1
    )
    try:
        with pytest.raises(AudioError, match='audio_timeout'):
            process.analyze({'id': 'old'}, lambda: None)
        assert process._process is None
        process.arguments = [sys.executable, '-u', '-c', ECHO]
        process.timeout = 3
        fresh = process.analyze({'id': 'fresh'}, lambda: None)
        assert fresh['track'] == 'fresh'
        assert fresh['count'] == 1
    finally:
        process.close()


@pytest.mark.parametrize('ignore_term', [False, True])
def test_cancellation_stops_the_analyzer_and_its_decoder(
    tmp_path, ignore_term
):
    marker = tmp_path / 'children.json'
    child_ready = tmp_path / 'decoder-ready'
    code = """
import json,os,subprocess,sys,time
from pathlib import Path
sys.stdin.readline()
child_code = "import signal,sys,time; from pathlib import Path; " + ("signal.signal(signal.SIGTERM,signal.SIG_IGN); " if sys.argv[3] == '1' else '') + "Path(sys.argv[1]).touch(); time.sleep(60)"
child = subprocess.Popen([sys.executable,'-c',child_code,sys.argv[2]])
while not Path(sys.argv[2]).exists():
    time.sleep(0.005)
Path(sys.argv[1]).write_text(json.dumps([os.getpid(), child.pid]))
time.sleep(60)
"""
    process = client(
        code, str(marker), str(child_ready), str(int(ignore_term))
    )

    def checkpoint():
        if marker.exists():
            try:
                json.loads(marker.read_text(encoding='utf-8'))
            except ValueError:
                return
            raise PermissionError('cancelled')

    try:
        with pytest.raises(PermissionError):
            process.analyze({'id': 'one'}, checkpoint)
        assert process._process is None
        for pid in json.loads(marker.read_text(encoding='utf-8')):
            status = Path(f'/proc/{pid}/stat')
            deadline = time.monotonic() + 2
            while True:
                try:
                    state = status.read_text(encoding='utf-8').split()[2]
                except (FileNotFoundError, ProcessLookupError):
                    break
                if state == 'Z':
                    break
                assert time.monotonic() < deadline, (
                    'Cancelled decoder is still running'
                )
                time.sleep(0.01)
    finally:
        process.close()
        if marker.exists():
            parent, child_pid = json.loads(marker.read_text(encoding='utf-8'))
            try:
                if os.getpgid(child_pid) == parent:
                    os.killpg(parent, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_model_instances_survive_across_tracks_without_loading_a_new_model(
    tmp_path, monkeypatch
):
    from downtify.music_ai import dj_analysis

    created = []

    class FakeTracker:
        def __call__(self, audio, rate):
            return np.array([0.0, 0.5, 1.0, 1.5]), np.array([0.0, 1.0])

    class FakeIO:
        def __init__(self, *args, **kwargs):
            pass

        def analyze(self, identity, path, tracker, checkpoint, **kwargs):
            beats, bars = tracker(np.ones(2 * 44100), 44100)
            return {'profile': {'id': identity}, 'beats': beats, 'bars': bars}

    engine = dj_analysis.AnalysisEngine.__new__(dj_analysis.AnalysisEngine)
    engine.options = SimpleNamespace(
        cache=tmp_path,
        root=[tmp_path],
        cache_bytes=1000,
        min_free=0,
        workspace=None,
        models=tmp_path,
    )
    engine.torch = SimpleNamespace(inference_mode=contextlib.nullcontext)
    engine.models = {}

    def factory(path, **kwargs):
        created.append(Path(path).stem)
        return FakeTracker()

    engine.factory = factory
    monkeypatch.setattr(dj_analysis, 'AudioIO', FakeIO)
    monkeypatch.setattr(
        dj_analysis,
        'profile_from_signal',
        lambda *args: SimpleNamespace(confidence=0.9),
    )
    payload = {
        'id': 'one',
        'path': 'synthetic',
        'source_version': [1, 2, 3, 4, 5],
    }
    assert engine.analyze(payload)['beat_model'] == 'small0'
    assert engine.analyze({**payload, 'id': 'two'})['beat_model'] == 'small0'
    assert created == ['small0']
    monkeypatch.setattr(
        dj_analysis,
        'profile_from_signal',
        lambda *args: SimpleNamespace(confidence=0.5),
    )
    engine.analyze({**payload, 'id': 'three'})
    engine.analyze({**payload, 'id': 'four'})
    assert created == ['small0', 'final0']
