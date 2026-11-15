"""Real decoder regression tests; also runnable without pytest in the DJ image."""

import hashlib
import shutil
import subprocess
import tempfile
import time
import unittest
import wave
from pathlib import Path

import numpy as np

from downtify.music_ai.dj_audio import RATE, AudioIO


@unittest.skipUnless(
    shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Requires real FFmpeg'
)
class UnityDecodeTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.music = root / 'music'
        self.music.mkdir()
        self.io = AudioIO(root / 'dj', [self.music], min_free=0)
        signal = 0.1 * np.sin(2 * np.pi * 440 * np.arange(44100 * 8) / 44100)
        wave_path = self.music / 'tone.wav'
        with wave.open(str(wave_path), 'wb') as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(44100)
            output.writeframes(
                np.repeat(
                    (signal * 32767).astype('<i2')[:, None], 2, axis=1
                ).tobytes()
            )
        self.mp3 = self.music / 'tone.mp3'
        subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', str(wave_path), str(self.mp3)],
            check=True,
            capture_output=True,
        )

    def test_unity_mp3_complete_and_progressive_preserve_reference(self):
        before = hashlib.sha256(self.mp3.read_bytes()).hexdigest()
        frames = 7 * RATE
        reference = subprocess.run(
            [
                'ffmpeg',
                '-v',
                'error',
                '-ss',
                '0.5',
                '-i',
                str(self.mp3),
                '-t',
                '7',
                '-ar',
                str(RATE),
                '-ac',
                '2',
                '-f',
                'f32le',
                '-',
            ],
            check=True,
            capture_output=True,
        ).stdout
        assert len(reference) == frames * 8
        row = {'cue': 0.5, 'source_end': 7.5, 'speed': 1.0}
        levels = {'input_i': -18, 'input_tp': -3}

        def checkpoint():
            pass

        result = self.io.decode(
            self.mp3, row, levels, self.io.cache / 'unity.pcm', checkpoint
        )
        expected = np.frombuffer(reference, dtype='<f4').reshape(-1, 2)
        np.testing.assert_allclose(
            np.fromfile(result, dtype='<f4').reshape(-1, 2),
            expected,
            rtol=0,
            atol=2e-7,
        )
        stream = self.io.stream(self.mp3, row, levels, checkpoint)
        try:
            deadline = time.monotonic() + 5
            while not stream.ready(0, frames):
                assert time.monotonic() < deadline
                time.sleep(0.001)
            np.testing.assert_allclose(
                stream[0:frames], expected, rtol=0, atol=2e-7
            )
        finally:
            stream.close()
        assert hashlib.sha256(self.mp3.read_bytes()).hexdigest() == before

    def test_non_unity_still_changes_duration_without_changing_pitch(self):
        before = hashlib.sha256(self.mp3.read_bytes()).hexdigest()
        row = {'cue': 0.5, 'source_end': 7.5, 'speed': 1.02}
        result = self.io.decode(
            self.mp3,
            row,
            {'input_i': -18, 'input_tp': -3},
            self.io.cache / 'stretched.pcm',
            lambda: None,
        )
        samples = np.fromfile(result, dtype='<f4').reshape(-1, 2)
        assert len(samples) == round(7 / 1.02 * RATE)
        mono = samples[RATE:-RATE, 0]
        spectrum = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
        frequency = np.fft.rfftfreq(len(mono), 1 / RATE)[np.argmax(spectrum)]
        assert abs(frequency - 440) <= 2
        assert hashlib.sha256(self.mp3.read_bytes()).hexdigest() == before


if __name__ == '__main__':
    unittest.main(verbosity=2)
