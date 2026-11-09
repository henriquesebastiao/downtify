import io

import numpy as np
import pytest

from downtify.music_ai import encoder


@pytest.mark.parametrize('seconds', [1, 9, 10, 11, 12, 15, 16, 20, 21])
def test_audio_windows_preserve_chronological_samples(monkeypatch, seconds):
    samples = np.arange(1, seconds * 48000 + 1, dtype=np.float32)

    class Process:
        stdout = io.BytesIO(samples.astype('<f4').tobytes())

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0

    monkeypatch.setattr(
        encoder.subprocess, 'Popen', lambda *args, **kwargs: Process()
    )
    chunks = list(encoder.audio_segments('synthetic'))
    assert all(chunk.shape == (480000,) for chunk in chunks)
    if seconds < 10:
        np.testing.assert_array_equal(chunks[0][: len(samples)], samples)
        assert not chunks[0][len(samples) :].any()
    else:
        np.testing.assert_array_equal(chunks[0], samples[:480000])
        np.testing.assert_array_equal(chunks[-1], samples[-480000:])
        assert all(np.all(np.diff(chunk) == 1) for chunk in chunks)
