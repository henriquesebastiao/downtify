from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from downtify.music_ai.dj_audio import FRAME_BYTES, RATE, AudioError, AudioIO
from downtify.music_ai.dj_prepared_deck import (
    DecodedDeck,
    PreparedAnalysis,
    decode_deck,
    discard_analysis,
    discard_decoded,
    prepare_analysis,
)
from downtify.music_ai.worker import signature


@pytest.fixture
def inputs(tmp_path):
    music = tmp_path / 'music'
    music.mkdir()
    original = music / 'original.audio'
    original.write_bytes(b'original music')
    io = AudioIO(tmp_path / 'dj', [music], workspace='a' * 32, min_free=0)
    source = {
        'path': str(original),
        'source_version': list(signature(original)),
        'fingerprint': 'original',
    }
    return io, source


def snapshot(io, slot):
    path = io.workspace / f'source-{slot}.audio'
    path.write_bytes(b'private snapshot')
    return {'path': str(path), 'source_version': list(signature(path))}


def test_analysis_owns_copies_and_an_isolated_audio_io(inputs):
    owner, source = inputs
    before = deepcopy(source)
    result = {'profile': {'duration': 5}, 'loudness': {'input_i': -18}}

    class Worker:
        def prepare_deck(self, track, io, **options):
            assert track == 'track'
            assert io is not owner
            assert io.snapshots is not owner.snapshots
            assert options['slot'] == 3
            assert options['report'] is False
            options['checkpoint']()
            copied = options['source']
            copied['source_version'][0] = -1
            copied['snapshot'] = snapshot(io, 3)
            io.allow_snapshot(**{
                'path': copied['snapshot']['path'],
                'expected': copied['snapshot']['source_version'],
            })
            return result

    prepared = prepare_analysis(
        Worker(), owner, 'track', source, 3, lambda: None
    )
    assert source == before
    assert owner.snapshots == {}
    assert prepared.created_snapshot
    assert prepared.source['source_version'][0] == -1
    result['profile']['duration'] = 99
    assert prepared.result['profile']['duration'] == 5
    with pytest.raises(FrozenInstanceError):
        prepared.track = 'changed'
    discard_analysis(prepared, owner)
    assert not (owner.workspace / 'source-3.audio').exists()
    assert Path(source['path']).read_bytes() == b'original music'


@pytest.mark.parametrize('borrowed', [False, True])
def test_failed_analysis_removes_only_a_new_snapshot(inputs, borrowed):
    owner, source = inputs
    if borrowed:
        source['snapshot'] = snapshot(owner, 2)
        owner.allow_snapshot(
            source['snapshot']['path'], source['snapshot']['source_version']
        )
    before = deepcopy(source)
    owner_snapshots = deepcopy(owner.snapshots)

    class Worker:
        def prepare_deck(self, track, io, **options):
            captured = options['source']
            if 'snapshot' not in captured:
                captured['snapshot'] = snapshot(io, options['slot'])
            raise PermissionError('cancelled')

    with pytest.raises(PermissionError, match='cancelled'):
        prepare_analysis(Worker(), owner, 'track', source, 2, lambda: None)
    assert source == before
    assert owner.snapshots == owner_snapshots
    assert (owner.workspace / 'source-2.audio').exists() == borrowed


def test_borrowed_snapshot_is_not_discarded(inputs):
    owner, source = inputs
    source['snapshot'] = snapshot(owner, 1)
    prepared = PreparedAnalysis('track', {}, source, False)
    discard_analysis(prepared, owner)
    assert Path(source['snapshot']['path']).exists()


def test_decode_copies_inputs_and_adds_fractional_rounding_guard(
    inputs, monkeypatch
):
    owner, source = inputs
    source['snapshot'] = snapshot(owner, 0)
    row = {'id': 'track', 'cue': 0, 'speed': 1, 'start': 0.4 / RATE}
    result = {
        'profile': {'duration': 2.2 / RATE},
        'loudness': {'input_i': -18, 'input_tp': -3},
    }
    before = deepcopy((row, result, source))
    target = owner.workspace / 'decoded-1.pcm'

    def decode(  # noqa: PLR0913, PLR0917 -- Match AudioIO.decode protocol.
        io, path, complete, loudness, destination, checkpoint, **options
    ):
        assert io is not owner
        assert io.snapshots is not owner.snapshots
        assert path == source['snapshot']['path']
        assert complete == {'cue': 0, 'speed': 1, 'source_end': 2.2 / RATE}
        assert options['expected'] == source['snapshot']['source_version']
        loudness['input_i'] = 0
        complete['cue'] = 99
        destination.write_bytes(b'X' * (2 * FRAME_BYTES))
        return destination

    monkeypatch.setattr(AudioIO, 'decode', decode)
    decoded = decode_deck(
        owner, row, result, source, ('track', 0, 1), target, lambda: None
    )
    assert (row, result, source) == before
    assert owner.snapshots == {}
    assert decoded.frames == 3
    assert decoded.frames >= round(2.6) - round(0.4)
    assert target.read_bytes() == b'X' * (2 * FRAME_BYTES) + bytes(FRAME_BYTES)
    discard_decoded(decoded, owner)
    assert not target.exists()
    assert Path(source['snapshot']['path']).exists()


def test_decode_cancellation_removes_output_but_preserves_snapshot(
    inputs, monkeypatch
):
    owner, source = inputs
    source['snapshot'] = snapshot(owner, 0)
    target = owner.workspace / 'decoded-2.pcm'

    def decode(  # noqa: PLR0913, PLR0917 -- Match AudioIO.decode protocol.
        io, path, complete, loudness, destination, checkpoint, **options
    ):
        destination.write_bytes(bytes(FRAME_BYTES))
        raise PermissionError('cancelled')

    monkeypatch.setattr(AudioIO, 'decode', decode)
    with pytest.raises(PermissionError, match='cancelled'):
        decode_deck(
            owner,
            {'cue': 0, 'speed': 1},
            {'profile': {'duration': 1}, 'loudness': {}},
            source,
            'key',
            target,
            lambda: None,
        )
    assert not target.exists()
    assert Path(source['snapshot']['path']).exists()


def test_discard_rejects_originals_and_unexpected_private_names(inputs):
    owner, source = inputs
    for path in [Path(source['path']), owner.workspace / 'index.m3u8']:
        with pytest.raises(AudioError, match='unsafe_prepared_deck_path'):
            discard_decoded(DecodedDeck('key', path, 0), owner)
        prepared = PreparedAnalysis(
            'track', {}, {'snapshot': {'path': str(path)}}, True
        )
        with pytest.raises(AudioError, match='unsafe_prepared_deck_path'):
            discard_analysis(prepared, owner)
    assert Path(source['path']).read_bytes() == b'original music'


def test_decode_rejects_existing_target_without_removing_it(inputs):
    owner, source = inputs
    target = owner.workspace / 'decoded-3.pcm'
    target.write_bytes(b'existing')
    with pytest.raises(AudioError, match='unsafe_cache_destination'):
        decode_deck(owner, {}, {}, source, 'key', target, lambda: None)
    assert target.read_bytes() == b'existing'


def test_discard_rejects_symlinks(inputs):
    owner, source = inputs
    target = owner.workspace / 'decoded-4.pcm'
    try:
        target.symlink_to(source['path'])
    except OSError:
        pytest.skip('Creating symlinks requires platform permission')
    with pytest.raises(AudioError, match='unsafe_prepared_deck_path'):
        discard_decoded(DecodedDeck('key', target, 0), owner)
    assert Path(source['path']).read_bytes() == b'original music'
