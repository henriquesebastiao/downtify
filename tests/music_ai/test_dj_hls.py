import shutil
import subprocess

import numpy as np
import pytest

from downtify.music_ai.dj_audio import AudioError, AudioIO, RATE
from downtify.music_ai.dj_hls import HlsEncoder

pytestmark = pytest.mark.skipif(
    not shutil.which("ffmpeg"), reason="HLS runs in the real Linux renderer image"
)


def test_single_encoder_publishes_atomic_bounded_segments_with_continuous_timestamps(
    tmp_path,
):
    music = tmp_path / "music"
    music.mkdir()
    io = AudioIO(tmp_path / "dj", [music], min_free=0)
    encoder = HlsEncoder(io, lambda: None)
    signal = np.repeat(
        (0.05 * np.sin(2 * np.pi * 440 * np.arange(RATE) / RATE))[:, None], 2, axis=1
    )
    try:
        for _ in range(100):
            encoder.write(signal)
        encoder.finish()
        text = encoder.manifest.read_text()
        names = [
            line for line in text.splitlines() if line and not line.startswith("#")
        ]
        assert 1 <= len(names) <= 12
        assert all(
            name.startswith("segment-") and name.endswith(".ts") and "/" not in name
            for name in names
        )
        assert "#EXT-X-ENDLIST" in text
        assert len(list(io.workspace.glob("segment-*.ts"))) <= 17
        assert not list(io.workspace.glob("*.tmp"))
        # The demuxer would report discontinuities or malformed timestamps with -xerror.
        result = subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-xerror",
                "-i",
                str(encoder.manifest),
                "-map",
                "0:a:0",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
        )
        assert result.returncode == 0
    finally:
        encoder.close()


def test_hls_cancellation_reaps_the_single_encoder(tmp_path):
    music = tmp_path / "music"
    music.mkdir()
    io = AudioIO(tmp_path / "dj", [music], min_free=0)

    def cancelled():
        raise PermissionError("disabled")

    encoder = HlsEncoder(io, cancelled)
    try:
        with pytest.raises(PermissionError):
            encoder.write(np.zeros((RATE, 2), dtype=np.float32))
        with pytest.raises(AudioError):
            encoder.write(np.zeros((RATE + 1, 2), dtype=np.float32))
    finally:
        encoder.close()
    assert encoder.process.poll() is not None
