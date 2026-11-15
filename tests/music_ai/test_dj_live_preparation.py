
"""Deterministic blocked-task checks for the live preparation pipeline."""

import sys
from collections import deque
from dataclasses import asdict
from threading import Event, Thread
from time import monotonic

import numpy as np
import pytest

from downtify.music_ai import dj_live
from downtify.music_ai.dj_audio import FRAME_BYTES, RATE, AudioIO
from downtify.music_ai.dj_pcm_stream import ProgressivePcm
from downtify.music_ai.dj_plan import Profile
from downtify.music_ai.dj_prepared_deck import DecodedDeck
from downtify.music_ai.worker import signature


class FakeDj:
    def __init__(self):
        self.commands = deque()
        self.receipts = {}
        self.completed = {'pause': Event(), 'resume': Event()}

    def pending_commands(self, *args):
        pending = list(self.commands)
        self.commands.clear()
        return pending

    def complete_command(self, session, token, nonce, result):
        self.receipts[nonce] = result
        self.completed[nonce].set()
        return True

    def publish(self, *args):
        return True

    def get(self, *args):
        return {}

    def command(self, action):
        self.commands.append({
            'action': action,
            'nonce': action,
            'payload': {},
        })


class FakeWorker:
    engine = 'test-engine'
    stage = 'rendering'

    def __init__(self, job):
        self.job, self.dj = job, FakeDj()
        self.stop = Event()
        self.published = Event()
        self.publications = []
        self.compute_ticket = None
        self.yields = []
        self.releases = []
        self.renderer = None
        self.task_started = Event()
        self.task_cleaned = Event()

    def checkpoint(self):
        if self.stop.is_set():
            raise PermissionError('test-stopped')

    def publish(self, **changes):
        self.publications.append(changes)
        self.published.set()

    def require_compute(self, *args, **kwargs):
        self.compute_ticket = object()
        return True

    def try_require_compute(self):
        return self.require_compute()

    def yield_compute(self):
        assert not self.renderer.preparation.busy, (
            'Released an active task lease'
        )
        self.yields.append(monotonic())
        self.compute_ticket = None

    def release_decks(self, io, keep):
        if not keep and self.task_started.is_set():
            assert self.task_cleaned.is_set(), (
                'Released sources before task cleanup'
            )
        self.releases.append(set(keep))


class FakeEncoder:
    def __init__(self, io, checkpoint):
        self.manifest = io.workspace / 'index.m3u8'
        self.origin = 1.0
        self.writes = 0
        self.closed = False

    def write(self, block):
        assert len(block)
        self.writes += 1

    def ready(self):
        return bool(self.writes)

    def finish(self):
        pass

    def close(self):
        self.closed = True


@pytest.fixture
def live(tmp_path, monkeypatch):
    music = tmp_path / 'music'
    music.mkdir()
    io = AudioIO(tmp_path / 'dj', [music], workspace='b' * 32, min_free=0)
    sources, results = {}, {}
    for index in range(4):
        identity = str(index)
        original = music / f'{index}.audio'
        original.write_bytes(b'original')
        snapshot = io.workspace / f'source-{index}.audio'
        snapshot.write_bytes(b'private snapshot')
        version = list(signature(snapshot))
        io.allow_snapshot(snapshot, version)
        sources[identity] = {
            'path': str(original),
            'source_version': list(signature(original)),
            'fingerprint': identity,
            'snapshot': {'path': str(snapshot), 'source_version': version},
        }
        results[identity] = {
            'profile': asdict(
                Profile(identity, 120, 120, 0.95, tuple(range(0, 120, 2)), 0.5)
            ),
            'loudness': {'input_i': -18, 'input_tp': -3},
        }
    worker = FakeWorker({
        'id': 'b' * 32,
        'owner': 1,
        'lease_token': 'test-token',
        'theme': 'fete',
        'ids': list(sources),
        'sources': sources,
        'queue_order': True,
    })
    monkeypatch.setattr(dj_live, 'HlsEncoder', FakeEncoder)
    renderer = dj_live.LiveRenderer(worker, io, results)
    worker.renderer = renderer
    yield renderer, worker, io
    worker.stop.set()
    if hasattr(renderer, 'preparation'):
        renderer.preparation.close()
        renderer.preparation.poll()
    renderer.release_unused(all_sources=True)


def install_pcm(renderer, io, row, number):
    frames = (
        round(
            (renderer.results[row['id']]['profile']['duration'] - row['cue'])
            / row['speed']
            * RATE
        )
        + 1
    )
    path = io.workspace / f'decoded-{number}.pcm'
    with path.open('wb') as stream:
        stream.truncate(frames * FRAME_BYTES)
    key = renderer.key(row)
    renderer.sources[key] = np.memmap(
        path, mode='r', dtype='<f4', shape=(frames, 2)
    )
    renderer.files[key] = path
    return key


def blocked_work(worker):
    def work(checkpoint):
        worker.task_started.set()
        try:
            while not worker.stop.wait(0.01):
                checkpoint()
            checkpoint()
            # Let renderer cancellation, rather than the fake worker's stop,
            # terminate the preparation and exercise join-before-cleanup.
            while True:
                checkpoint()
                Event().wait(0.01)
        finally:
            worker.task_cleaned.set()

    return work


def blocked_decode(worker):
    def decode(  # noqa: PLR0913, PLR0917 -- Match the preparation task protocol.
        owner_io,
        row,
        result,
        source,
        key,
        target,
        checkpoint,
        *,
        progressive=False,
    ):
        assert progressive is True
        return blocked_work(worker)(checkpoint)

    return decode


def blocked_analysis(worker):
    def analyze(task_worker, owner_io, track, source, slot, checkpoint):  # noqa: PLR0913, PLR0917 -- Match the preparation task protocol.
        assert task_worker is worker
        return blocked_work(worker)(checkpoint)

    return analyze


def start_render(renderer):
    failures = []

    def run():
        try:
            renderer.render()
        except BaseException as error:
            failures.append(error)

    thread = Thread(target=run)
    thread.start()
    return thread, failures


def stop_render(worker, thread, failures):
    worker.stop.set()
    thread.join(5)
    assert not thread.is_alive(), (
        'Renderer failed to cancel and join preparation'
    )
    assert len(failures) == 1
    assert isinstance(failures[0], PermissionError), repr(failures)


def test_source_lookup_never_decodes_missing_pcm(live, monkeypatch):
    renderer, _, io = live

    def unexpected(*args, **kwargs):
        pytest.fail('Audio decoding ran in source_for')

    monkeypatch.setattr(io, 'decode', unexpected)
    with pytest.raises(RuntimeError, match='dj_deck_not_prepared'):
        renderer.source_for(0, renderer.plan.rows[0])


def test_block_preflight_keeps_cursor_and_eq_unchanged(live):
    renderer, _, io = live
    first, second = renderer.plan.rows[:2]
    install_pcm(renderer, io, first, 100)
    renderer.mixer.position = round(second['start'] * RATE) - RATE // 2
    position = renderer.mixer.position
    states = renderer.mixer.states.copy()
    assert not renderer.block_ready()
    assert renderer.mixer.position == position
    assert renderer.mixer.states == states


def test_release_retains_current_and_three_future_pcm(live):
    renderer, _, io = live
    keys = {
        install_pcm(renderer, io, row, 100 + index)
        for index, row in enumerate(renderer.plan.rows[:4])
    }
    renderer.release_unused()
    assert keys <= renderer.sources.keys()
    assert all(renderer.files[key].exists() for key in keys)


def test_continuous_extension_adds_only_one_occurrence(live, monkeypatch):
    renderer, worker, _ = live
    renderer.continuous = True
    renderer.mixer.position = round(renderer.plan.rows[0]['end'] * RATE)
    scheduled = []
    monkeypatch.setattr(
        renderer,
        'schedule',
        lambda row, **options: scheduled.append((row, options)),
    )
    renderer.extend()
    assert len(scheduled) == 1
    assert scheduled[0][0]['id'] in worker.job['sources']
    assert scheduled[0][1] == {'append': True}


@pytest.mark.parametrize('stage', ['decode', 'analysis'])
def test_blocked_preparation_keeps_transport_and_publication_available(
    live, monkeypatch, stage
):
    renderer, worker, io = live
    install_pcm(renderer, io, renderer.plan.rows[0], 100)
    if stage == 'decode':
        monkeypatch.setattr(dj_live, 'decode_deck', blocked_decode(worker))
    else:
        following = renderer.plan.rows[1]['id']
        worker.job['sources'][following].pop('snapshot')
        monkeypatch.setattr(
            dj_live, 'prepare_analysis', blocked_analysis(worker)
        )
    thread, failures = start_render(renderer)
    try:
        assert worker.task_started.wait(3)
        worker.dj.command('pause')
        assert worker.dj.completed['pause'].wait(2)
        assert worker.dj.receipts['pause']['accepted']
        worker.dj.command('resume')
        assert worker.dj.completed['resume'].wait(2)
        assert worker.dj.receipts['resume']['accepted']
        assert worker.published.is_set()
        assert renderer.mixer.position > 0
        assert renderer.preparation.busy
        assert not worker.task_cleaned.is_set()
    finally:
        stop_render(worker, thread, failures)


def test_paused_loop_prepares_and_holds_lease_until_task_cleanup(
    live, monkeypatch
):
    renderer, worker, _ = live
    renderer.paused = True
    monkeypatch.setattr(dj_live, 'decode_deck', blocked_decode(worker))
    thread, failures = start_render(renderer)
    try:
        assert worker.task_started.wait(3), (
            'Preparation was skipped while paused'
        )
        assert worker.published.wait(3)
        assert worker.compute_ticket is not None
        assert renderer.preparation.busy
        assert not worker.yields
    finally:
        stop_render(worker, thread, failures)
    assert worker.task_cleaned.is_set()


@pytest.mark.parametrize('streaming', [False, True])
@pytest.mark.parametrize('invalidation', ['source', 'plan', 'cancel'])
def test_late_decoded_result_is_discarded_after_invalidation(
    live, monkeypatch, invalidation, streaming
):
    renderer, worker, io = live
    release = Event()
    paths = []
    streams = []
    row = renderer.plan.rows[0]
    key = renderer.key(row)

    def late_decode(  # noqa: PLR0913, PLR0917 -- Match the preparation task protocol.
        owner_io,
        captured,
        result,
        source,
        decoded_key,
        target,
        checkpoint,
        *,
        progressive=False,
    ):
        assert progressive is True
        worker.task_started.set()
        try:
            assert release.wait(3)
            # Deliberately model work completing just before observing cancel.
            target.write_bytes(bytes(FRAME_BYTES))
            paths.append(target)
            buffer = None
            if streaming:
                buffer = ProgressivePcm(
                    [
                        sys.executable,
                        '-c',
                        'import sys; sys.stdout.buffer.write(bytes(8))',
                    ],
                    1,
                    lambda: None,
                )
                streams.append(buffer)
                buffer.warm(lambda: None)
            return DecodedDeck(decoded_key, target, 1, buffer)
        finally:
            worker.task_cleaned.set()

    monkeypatch.setattr(dj_live, 'decode_deck', late_decode)
    try:
        renderer.schedule(row)
        assert worker.task_started.wait(3)
        if invalidation == 'source':
            worker.job['sources'][row['id']]['fingerprint'] = 'new-source'
        elif invalidation == 'plan':
            renderer.plan.rows[0] = {**row, 'cue': row['cue'] + 0.5}
        else:
            renderer.preparation.cancel()
        release.set()
        renderer.preparation._future.result(timeout=3)
        renderer.reap()
        assert not renderer.preparation.busy
        assert renderer.preparing is None
        assert key not in renderer.sources
        assert len(paths) == 1
        assert not paths[0].exists()
        for buffer in streams:
            assert buffer._closed
            assert buffer._process.poll() is not None
            assert not buffer._thread.is_alive()
    finally:
        release.set()
        for buffer in streams:
            buffer.close()


def test_two_initial_profiles_keep_the_rest_of_the_queue_pending(live):
    original, worker, io = live
    initial = {key: original.results[key] for key in worker.job['ids'][:2]}
    renderer = dj_live.LiveRenderer(worker, io, initial)
    try:
        assert [row['id'] for row in renderer.plan.rows] == ['0', '1']
        assert renderer.pending_ids == ['2', '3']
        assert len(renderer.window()) == 2
        assert set(renderer.results) == {'0', '1'}
        assert worker.job['ids'] == ['0', '1', '2', '3']
    finally:
        renderer.preparation.close()
        renderer.preparation.poll()
