import sys
import time
from pathlib import Path

import numpy as np
import pytest

from downtify.music_ai.dj_audio import RATE, AudioError
from downtify.music_ai.dj_pcm_stream import ProgressivePcm


def producer(tmp_path, frames):
    samples = (np.arange(frames * 2, dtype='<f4') / 1000000).reshape(-1, 2)
    path = tmp_path / 'stereo.pcm'
    path.write_bytes(samples.tobytes())
    return samples, [
        sys.executable,
        '-c',
        (
            "import shutil,sys; shutil.copyfileobj(open(sys.argv[1],'rb'),sys.stdout.buffer,65536)"
        ),
        str(path),
    ]


def await_ready(stream, left, right):
    deadline = time.monotonic() + 5
    while not stream.ready(left, right):
        assert time.monotonic() < deadline, (
            'Decoder did not supply the requested range'
        )
        time.sleep(0.001)


def test_bounded_read_ahead_and_bit_exact_sequential_audio(tmp_path):
    expected, command = producer(tmp_path, 8 * RATE)
    stream = ProgressivePcm(command, len(expected), lambda: None, ahead=RATE)
    try:
        stream.warm(lambda: None)
        assert stream.buffered_frames == RATE
        assert not stream.ready(RATE, RATE + 1)
        decoded = []
        for left in range(0, len(expected), RATE // 5):
            right = min(len(expected), left + RATE // 5)
            await_ready(stream, left, right)
            decoded.append(stream[left:right])
            assert stream.buffered_frames <= 2 * RATE + 8192
        np.testing.assert_array_equal(np.concatenate(decoded), expected)
        with pytest.raises(AudioError, match='expired'):
            stream[0:1]
    finally:
        stream.close()
    assert not stream._thread.is_alive()
    assert stream._process.poll() is not None
    assert stream.buffered_frames == 0


def test_unread_audio_is_refused_instead_of_returning_silence(tmp_path):
    _, command = producer(tmp_path, 3 * RATE)
    stream = ProgressivePcm(command, 3 * RATE, lambda: None, ahead=RATE)
    try:
        stream.warm(lambda: None)
        with pytest.raises(AudioError, match='not_ready'):
            stream[RATE : RATE + 1]
    finally:
        stream.close()


@pytest.mark.parametrize('extra', [-3000, 3000])
def test_truncated_and_overlong_audio_fail_without_fabricating_a_deck(
    tmp_path, extra
):
    _, command = producer(tmp_path, RATE + extra)
    stream = ProgressivePcm(command, RATE, lambda: None)
    try:
        stream._thread.join(timeout=5)
        assert not stream._thread.is_alive()
        with pytest.raises(AudioError, match='length_mismatch'):
            stream.warm(lambda: None)
    finally:
        stream.close()


def test_source_invalidation_stops_the_decoder(tmp_path):
    _, command = producer(tmp_path, RATE)

    def changed():
        raise PermissionError('source_changed')

    stream = ProgressivePcm(command, RATE, changed)
    try:
        with pytest.raises(PermissionError, match='source_changed'):
            stream.warm(lambda: None)
    finally:
        stream.close()
    assert stream._process.poll() is not None


def test_close_kills_a_descendant_even_when_the_group_leader_exits(tmp_path):
    pidfile = tmp_path / 'child.pid'
    command = [
        sys.executable,
        '-c',
        (
            'import subprocess,sys; from pathlib import Path; '
            "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
            'Path(sys.argv[1]).write_text(str(p.pid))'
        ),
        str(pidfile),
    ]
    stream = ProgressivePcm(command, RATE, lambda: None)
    try:
        deadline = time.monotonic() + 5
        while not pidfile.exists():
            assert time.monotonic() < deadline
            time.sleep(0.01)
        child = int(pidfile.read_text())
        stream._process.wait(timeout=5)
    finally:
        stream.close()
    state = Path(f'/proc/{child}/stat')
    deadline = time.monotonic() + 2
    while True:
        try:
            status = state.read_text(encoding='utf-8').split()[2]
        except (FileNotFoundError, ProcessLookupError):
            break
        if status == 'Z':
            break
        assert time.monotonic() < deadline, (
            'Decoder descendant is still running'
        )
        time.sleep(0.01)
    assert not stream._thread.is_alive()


def test_warmup_remains_cancellable_without_waiting_for_audio():
    stream = ProgressivePcm(
        [sys.executable, '-c', 'import time; time.sleep(60)'],
        RATE,
        lambda: None,
    )
    started = time.monotonic()

    def cancelled():
        raise PermissionError('cancelled')

    try:
        with pytest.raises(PermissionError, match='cancelled'):
            stream.warm(cancelled)
    finally:
        stream.close()
    assert time.monotonic() - started < 3
    assert stream._process.poll() is not None
