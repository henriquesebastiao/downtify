import hashlib
import os
import shutil
import threading
from pathlib import Path

import pytest
from ai_test_support import opted_in_store
from test_dj_audio import tone

from downtify.music_ai import dj_worker
from downtify.music_ai.dj_store import DjStore
from downtify.music_ai.worker import signature

MODELS = Path(os.environ.get('DOWNTIFY_TEST_DJ_MODELS', '/models'))

pytestmark = pytest.mark.skipif(
    not (shutil.which('ffmpeg') and (MODELS / 'small0.ckpt').is_file()),
    reason='Real model integration runs in the isolated DJ image',
)


@pytest.fixture
def prepared(tmp_path):
    music = tmp_path / 'music'
    music.mkdir()
    paths = [music / 'one.wav', music / 'two.wav']
    for index, path in enumerate(paths):
        tone(path, 440 + index * 110)
    database = opted_in_store(tmp_path / 'derived.db')
    database.set_preferences(-1, {'dj_prepared': True})
    database.set_preferences(1, {'dj_prepared': True})
    dj = DjStore(database)
    sources = {
        str(index): {
            'path': str(path),
            'fingerprint': str(index),
            'source_version': list(signature(path)),
            'artist': f'Synthetic{index}',
        }
        for index, path in enumerate(paths)
    }
    worker = dj_worker.DjWorker(database, MODELS, [music], min_free=0)
    yield dj, worker, sources, paths
    worker.close()


def test_real_prepared_worker_reuses_unchanged_profiles_without_new_model_processes(
    prepared, monkeypatch
):
    dj, worker, sources, paths = prepared
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    launched = []
    from downtify.music_ai.analysis_process import AnalysisProcess

    real = AnalysisProcess._start

    def observe(process):
        real(process)
        launched.append(process._process.pid)

    monkeypatch.setattr(AnalysisProcess, '_start', observe)
    first = dj.create(1, 'prepared', 'fete', list(sources), sources)
    assert worker.step()
    ready = dj.get(1, first['id'])
    assert ready['state'] == 'ready'
    assert ready['duration'] > 8
    assert (worker.cache / first['id'] / 'set.m4a').is_file()
    assert len(launched) == 1
    launched.clear()
    second = dj.create(1, 'prepared', 'fete', list(sources), sources)
    assert worker.step()
    assert dj.get(1, second['id'])['state'] == 'ready'
    assert launched == []
    assert [
        hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    ] == hashes
    assert not list(worker.cache.glob('*/decoded-*.pcm'))


def test_disabling_prepared_work_cancels_before_any_set_is_published(prepared):
    dj, worker, sources, paths = prepared
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    session = dj.create(1, 'prepared', 'calme', list(sources), sources)
    timer = threading.Timer(
        0.2,
        lambda: worker.database.set_preferences(-1, {'dj_prepared': False}),
    )
    timer.start()
    try:
        worker.step()
    finally:
        timer.join()
    assert dj.get(1, session['id'])['state'] in {'cancelled', 'stopped'}
    assert not (worker.cache / session['id'] / 'set.m4a').exists()
    assert [
        hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    ] == hashes
