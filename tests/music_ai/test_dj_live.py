import hashlib
import shutil
import wave
from dataclasses import asdict

import numpy as np
import pytest
from ai_test_support import opted_in_store

from downtify.music_ai.dj_audio import AudioIO
from downtify.music_ai.dj_live import LiveRenderer
from downtify.music_ai.dj_plan import Profile
from downtify.music_ai.dj_store import DjStore
from downtify.music_ai.worker import signature

pytestmark = pytest.mark.skipif(
    not shutil.which('ffmpeg'),
    reason='Live integration uses the Linux renderer',
)


def fixture(tmp_path):
    music = tmp_path / 'music'
    music.mkdir()
    results, sources = {}, {}
    for index in range(4):
        identity = str(index)
        path = music / f'{index}.wav'
        rate = 8000
        t = np.arange(rate * 36) / rate
        signal = 0.05 * np.sin(2 * np.pi * (220 + 110 * index) * t)
        with wave.open(str(path), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(rate)
            output.writeframes((signal * 32767).astype('<i2').tobytes())
        source = {
            'path': str(path),
            'source_version': list(signature(path)),
            'fingerprint': identity,
        }
        sources[identity] = source
        results[identity] = {
            'profile': asdict(
                Profile(
                    identity,
                    36,
                    120,
                    0.95,
                    tuple(range(0, 36, 2)),
                    0.3 + 0.1 * index,
                )
            ),
            'loudness': {'input_i': -18, 'input_tp': -3},
        }
    store = opted_in_store(tmp_path / 'state' / 'derived.db')
    for owner in (-1, 1):
        store.set_preferences(owner, {'dj_interactive': True})
    dj = DjStore(store)
    dj.create(1, 'interactive', 'fete', list(sources), sources)
    job = dj.claim()
    io = AudioIO(
        store.path.parent / 'dj', [music], workspace=job['id'], min_free=0
    )

    class Worker:
        engine = 'synthetic-engine'
        stage = 'rendering'

        def checkpoint(self):
            if not dj.alive(job['id'], job['lease_token']):
                raise PermissionError('disabled')

        def publish(self, **changes):
            assert dj.publish(
                job['id'], job['lease_token'], self.stage, changes
            )

    worker = Worker()
    worker.job, worker.dj = job, dj
    return worker, io, results, music, store


def test_real_hls_encoder_handles_live_controls_without_rewriting_originals(
    tmp_path,
):
    worker, io, results, music, _ = fixture(tmp_path)
    original = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in music.iterdir()
    }
    clock = [0.0]
    sent = set()
    renderer = None

    def sleep(seconds):
        clock[0] += seconds
        commands = [
            (2, 'pause', {}),
            (3, 'resume', {}),
            (4, 'next', {}),
            (5, 'theme', {'theme': 'calme'}),
        ]
        for deadline, action, payload in commands:
            if clock[0] >= deadline and action not in sent:
                worker.dj.command(1, worker.job['id'], action, action, payload)
                sent.add(action)
        if clock[0] >= 6 and 'replace' not in sent:
            worker.dj.command(
                1,
                worker.job['id'],
                'replace',
                'replace',
                {'id': renderer.plan.rows[-1]['id']},
            )
            sent.add('replace')

    renderer = LiveRenderer(
        worker, io, results, clock=lambda: clock[0], sleep=sleep
    )
    output = renderer.render()
    assert output.is_file()
    assert '#EXT-X-ENDLIST' in output.read_text()
    assert sent == {'pause', 'resume', 'next', 'theme', 'replace'}
    receipts = worker.dj.command_results(worker.job['id'])
    assert len(receipts) == 5
    assert all(row['accepted'] for row in receipts)
    assert all(row.get('effective_after_seconds', 0) >= 0 for row in receipts)
    assert worker.dj.get(1, worker.job['id'])['state'] == 'ready'
    assert not list(io.workspace.glob('decoded-*.pcm'))
    assert original == {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in music.iterdir()
    }


def test_live_module_disable_stops_encoder_and_cleans_decoded_audio(tmp_path):
    worker, io, results, _, store = fixture(tmp_path)
    clock = [0.0]

    def sleep(seconds):
        clock[0] += seconds
        if clock[0] > 0.2:
            store.set_preferences(1, {'dj_interactive': False})

    renderer = LiveRenderer(
        worker, io, results, clock=lambda: clock[0], sleep=sleep
    )
    with pytest.raises(PermissionError):
        renderer.render()
    assert not list(io.workspace.glob('decoded-*.pcm'))


def test_continuous_hls_renews_without_restarting_encoder_and_bounds_history(
    tmp_path,
):
    worker, io, results, music, _ = fixture(tmp_path)
    worker.job['continuous'] = True
    original = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in music.iterdir()
    }
    clock = [0.0]

    def sleep(seconds):
        clock[0] += seconds
        if clock[0] >= 250:
            worker.dj.stop(1, worker.job['id'])

    renderer = LiveRenderer(
        worker, io, results, clock=lambda: clock[0], sleep=sleep
    )
    with pytest.raises(PermissionError):
        renderer.render()
    assert renderer.plan.renewals >= 3
    assert renderer.mixer.position / 48000 > 200
    assert len(renderer.plan.rows) <= 10
    assert len(list(io.workspace.glob('segment-*.ts'))) <= 17
    assert (
        '#EXT-X-PROGRAM-DATE-TIME:'
        in (io.workspace / 'index.m3u8').read_text()
    )
    assert renderer.media_origin > 0
    assert not list(io.workspace.glob('decoded-*.pcm'))
    assert original == {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in music.iterdir()
    }
