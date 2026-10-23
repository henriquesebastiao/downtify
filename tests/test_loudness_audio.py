"""Real FFmpeg measurements against synthetic files, never a user's audio."""

import hashlib
import math
import shutil
import struct
import subprocess
import wave

import pytest

from downtify.library_catalog import LibraryContext
from downtify.loudness import LoudnessAnalyzer


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='FFmpeg unavailable')
def test_real_quiet_loud_and_silent_files_have_safe_playback_gains(tmp_path):
    runner = LoudnessAnalyzer(
        tmp_path / 'test.db', lambda: LibraryContext(download_dir=tmp_path)
    )
    profiles = []
    for name, amplitude in [('quiet', 0.06), ('loud', 0.6), ('silent', 0)]:
        source = tmp_path / f'{name}.wav'
        with wave.open(str(source), 'wb') as out:
            out.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
            out.writeframes(
                b''.join(
                    struct.pack(
                        '<h',
                        int(
                            32767
                            * amplitude
                            * math.sin(2 * math.pi * 440 * i / 48000)
                        ),
                    )
                    for i in range(144000)
                )
            )
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        profile = runner._measure(source)
        assert hashlib.sha256(source.read_bytes()).hexdigest() == before
        if amplitude:
            assert profile['state'] == 'ready'
            assert profile['gain_db'] <= 12
            assert profile['true_peak_dbtp'] + profile['gain_db'] <= -0.99
            output = tmp_path / f'{name}-played.wav'
            subprocess.run(
                [
                    'ffmpeg',
                    '-hide_banner',
                    '-loglevel',
                    'error',
                    '-i',
                    str(source),
                    '-af',
                    f'volume={profile["gain_db"]}dB',
                    str(output),
                ],
                check=True,
            )
            measured = runner._measure(output)
            profiles.append(measured['integrated_lufs'])
        else:
            assert profile['state'] == 'silent'
            assert profile['gain_db'] == 0
    assert abs(profiles[0] - profiles[1]) < 4
    runner.close()
