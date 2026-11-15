import hashlib
import shutil
import subprocess
import wave

import numpy as np
import pytest

from downtify.music_ai.dj_audio import RATE, AudioError, AudioIO, run_audio
from downtify.music_ai.dj_plan import Profile, timeline

pytestmark = pytest.mark.skipif(
    not (shutil.which('ffmpeg') and shutil.which('ffprobe')),
    reason='Real FFmpeg tests run in the DJ Linux image',
)


def tone(path, frequency=440, amplitude=0.1, duration=8):
    rate = 44100
    t = np.arange(rate * duration) / rate
    signal = np.repeat(
        (amplitude * np.sin(2 * np.pi * frequency * t))[:, None], 2, axis=1
    )
    with wave.open(str(path), 'wb') as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes((signal * 32767).astype('<i2').tobytes())


@pytest.fixture
def audio(tmp_path):
    music = tmp_path / 'music'
    music.mkdir()
    one, two = music / 'one.wav', music / 'two.wav'
    tone(one)
    tone(two, 550, 0.025)
    io = AudioIO(tmp_path / 'dj', [music], min_free=0)
    return io, one, two


def noop():
    pass


def test_time_stretch_changes_duration_without_pitch_or_original_changes(
    audio,
):
    io, one, _ = audio
    before = hashlib.sha256(one.read_bytes()).hexdigest()
    levels = io.loudness(one, noop)
    row = {'cue': 0.5, 'source_end': 7.5, 'speed': 1.02}
    result = io.decode(one, row, levels, io.cache / 'stretched.pcm', noop)
    samples = np.fromfile(result, dtype='<f4').reshape(-1, 2)
    assert len(samples) == round(7 / 1.02 * RATE)
    mono = samples[RATE:-RATE, 0]
    spectrum = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
    frequency = np.fft.rfftfreq(len(mono), 1 / RATE)[np.argmax(spectrum)]
    assert frequency == pytest.approx(440, abs=2)
    assert hashlib.sha256(one.read_bytes()).hexdigest() == before


def test_prepared_set_has_markers_duration_consistent_level_and_safe_peak(
    audio,
):
    pytest.importorskip(
        'scipy', reason='Mixing requires the DJ renderer dependency'
    )
    io, one, two = audio
    before = [
        hashlib.sha256(path.read_bytes()).hexdigest() for path in (one, two)
    ]
    profiles = [
        Profile(str(index), 8, 120, 0.95, (0, 2, 4, 6), 0.5)
        for index in range(2)
    ]
    rows = timeline(profiles)
    decoded = {}
    for index, path in enumerate((one, two)):
        decoded[index] = io.decode(
            path,
            rows[index],
            io.loudness(path, noop),
            io.cache / f'{index}.pcm',
            noop,
        )
    result = io.prepared(rows, decoded, io.cache / 'set.m4a', noop)
    assert io.probe(result, noop) == pytest.approx(rows[-1]['end'], abs=0.1)
    assert rows[1]['start'] == 4
    levels = io.loudness(result, noop)
    assert levels['input_i'] == pytest.approx(-18, abs=2)
    assert levels['input_tp'] <= -0.8
    assert [
        hashlib.sha256(path.read_bytes()).hexdigest() for path in (one, two)
    ] == before
    assert not list(io.cache.glob('render-*.set.*'))


def test_source_replacement_during_analysis_discards_the_result(audio):
    io, one, _ = audio

    def tracker(signal, rate):
        tone(one, 660)
        beats = np.arange(0.5, len(signal) / rate, 0.5)
        return beats, beats[::4]

    with pytest.raises(AudioError, match='source_changed'):
        io.analyze('one', one, tracker, noop)
    assert not list(io.cache.glob('render-*.mono.pcm'))


def test_no_writes_to_music_or_outside_the_private_cache(audio):
    io, one, two = audio
    before = two.read_bytes()
    with pytest.raises(AudioError, match='unsafe_cache_destination'):
        io.decode(
            one,
            {'cue': 0, 'source_end': 8, 'speed': 1},
            {'input_i': -18, 'input_tp': -6},
            two,
            noop,
        )
    assert two.read_bytes() == before
    outside = io.cache / 'not-music.wav'
    shutil.copyfile(one, outside)
    with pytest.raises(ValueError, match='outside'):
        io.original(outside)


def test_cache_budget_is_enforced_before_allocating_audio(tmp_path):
    music = tmp_path / 'music'
    music.mkdir()
    io = AudioIO(tmp_path / 'dj', [music], budget=16 * 1024**2, min_free=0)
    with pytest.raises(AudioError, match='dj_cache_full'):
        io.check_space(16 * 1024**2 + 1)
    assert list(io.cache.iterdir()) == []


def test_disabled_module_terminates_and_reaps_an_audio_subprocess(monkeypatch):
    real = subprocess.Popen
    children, checks = [], []

    def launch(*args, **kwargs):
        child = real(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, 'Popen', launch)

    def checkpoint():
        checks.append(1)
        if len(checks) >= 2:
            raise PermissionError('module_disabled')

    with pytest.raises(PermissionError, match='module_disabled'):
        run_audio(
            [
                'ffmpeg',
                '-nostdin',
                '-v',
                'error',
                '-re',
                '-f',
                'lavfi',
                '-i',
                'sine=frequency=440',
                '-t',
                '10',
                '-f',
                'null',
                '-',
            ],
            checkpoint,
        )
    assert len(children) == 1
    assert children[0].poll() is not None


def test_timeout_does_not_leave_an_audio_process_running():
    with pytest.raises(AudioError, match='audio_timeout'):
        run_audio(
            [
                'ffmpeg',
                '-nostdin',
                '-v',
                'error',
                '-re',
                '-f',
                'lavfi',
                '-i',
                'sine=frequency=440',
                '-t',
                '10',
                '-f',
                'null',
                '-',
            ],
            noop,
            timeout=0.1,
        )


def test_streamed_prepared_render_keeps_only_the_current_two_decoded_tracks(
    audio,
):
    io, one, _ = audio
    profiles = [Profile(str(index), 8, 0, 0, (), 0.5) for index in range(6)]
    rows = timeline(profiles)
    levels = io.loudness(one, noop)
    counts = []

    def decode(index, row):
        result = io.decode(
            one, row, levels, io.cache / f'decoded-{index}.pcm', noop
        )
        counts.append(len(list(io.cache.glob('decoded-*.pcm'))))
        return result

    result = io.prepared(rows, decode, io.cache / 'set.m4a', noop)
    assert io.probe(result, noop) == pytest.approx(rows[-1]['end'], abs=0.1)
    assert max(counts) <= 2
    assert not list(io.cache.glob('decoded-*.pcm'))
    assert not list(io.cache.glob('render-*.set.pcm'))


def test_fractional_track_positions_share_the_absolute_sample_grid(audio):
    io, one, _ = audio
    # Deliberately make round(end)-round(start) one larger than round(duration).
    start = 5 + 0.49 / RATE
    duration = 7 + 0.49 / RATE
    rows = [
        {
            'id': 'one',
            'start': 0,
            'end': 6,
            'cue': 0,
            'source_end': 6,
            'speed': 1,
        },
        {
            'id': 'two',
            'start': start,
            'end': start + duration,
            'cue': 0,
            'source_end': duration,
            'speed': 1,
        },
    ]
    levels = io.loudness(one, noop)
    decoded = {
        index: io.decode(
            one, row, levels, io.cache / f'fraction-{index}.pcm', noop
        )
        for index, row in enumerate(rows)
    }
    assert decoded[1].stat().st_size // 8 == round(
        rows[1]['end'] * RATE
    ) - round(start * RATE)
    result = io.prepared(rows, decoded, io.cache / 'fractional.m4a', noop)
    assert io.probe(result, noop) == pytest.approx(rows[-1]['end'], abs=0.1)


def test_absolute_grid_cannot_extend_a_source_beyond_the_validated_plan(audio):
    io, one, _ = audio
    with pytest.raises(AudioError, match='unsafe_audio_plan'):
        io.decode(
            one,
            {'cue': 0, 'source_end': 7, 'speed': 1, 'start': 3, 'end': 13},
            {'input_i': -18, 'input_tp': -6},
            io.cache / 'unsafe.pcm',
            noop,
        )


def test_live_frozen_audio_survives_a_parallel_original_replacement(audio):
    from downtify.music_ai.worker import signature

    io, one, _ = audio
    snapshot = io.freeze(one, list(signature(one)), 0, noop)
    tone(one, 660)
    replacement_hash = hashlib.sha256(one.read_bytes()).hexdigest()
    levels = io.loudness(snapshot['path'], noop)
    result = io.decode(
        snapshot['path'],
        {'cue': 0, 'source_end': 8, 'speed': 1},
        levels,
        io.cache / 'frozen.pcm',
        noop,
        expected=snapshot['source_version'],
    )
    samples = np.fromfile(result, dtype='<f4').reshape(-1, 2)[RATE:-RATE, 0]
    frequency = np.fft.rfftfreq(len(samples), 1 / RATE)[
        np.argmax(np.abs(np.fft.rfft(samples * np.hanning(len(samples)))))
    ]
    assert frequency == pytest.approx(440, abs=2)
    io.release_snapshots()
    assert not list(io.workspace.glob('source-*.audio'))
    assert hashlib.sha256(one.read_bytes()).hexdigest() == replacement_hash


def test_cached_audio_cannot_be_registered_outside_its_exact_job_workspace(
    audio,
):
    from downtify.music_ai.worker import signature

    io, one, _ = audio
    with pytest.raises(AudioError, match='unsafe_snapshot_source'):
        io.allow_snapshot(one, list(signature(one)))


def test_progressive_decoder_matches_continuous_audio_across_buffer_boundaries(
    audio,
):
    import time

    io, one, _ = audio
    tone(one, duration=40)
    before = hashlib.sha256(one.read_bytes()).hexdigest()
    levels = {'input_i': -18, 'input_tp': -3}
    row = {'cue': 0.5, 'source_end': 39.5, 'speed': 1.02}
    complete = io.decode(one, row, levels, io.cache / 'reference.pcm', noop)
    expected = np.fromfile(complete, dtype='<f4').reshape(-1, 2)
    stream = io.stream(one, row, levels, noop)
    try:
        assert stream.buffered_frames <= 24 * RATE
        decoded = []
        for left in range(0, len(expected), RATE):
            right = min(len(expected), left + RATE)
            deadline = time.monotonic() + 5
            while not stream.ready(left, right):
                assert time.monotonic() < deadline
                time.sleep(0.001)
            decoded.append(stream[left:right])
            assert stream.buffered_frames <= 25 * RATE + 8192
        np.testing.assert_allclose(
            np.concatenate(decoded), expected, rtol=0, atol=2e-7
        )
    finally:
        stream.close()
    assert hashlib.sha256(one.read_bytes()).hexdigest() == before
    assert set(io.cache.glob('*.pcm')) == {complete}
