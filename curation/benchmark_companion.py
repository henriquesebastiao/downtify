"""Offline, synthetic-only CPU benchmark. Never opens the music mounts."""

from __future__ import annotations

import gc
import hashlib
import importlib.metadata
import json
import resource
import tempfile
import time
import wave
from pathlib import Path

import numpy as np

from downtify.music_ai.encoder import Encoder
from downtify.music_ai.ranking import rank
from downtify.music_ai.store import MOODS


def rss_mib():
    for line in (
        Path('/proc/self/status').read_text(encoding='utf-8').splitlines()
    ):
        if line.startswith('VmRSS:'):
            return round(int(line.split()[1]) / 1024, 2)


def version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


report = {
    'synthetic_only': True,
    'versions': {
        name: version(name)
        for name in ('numpy', 'onnxruntime', 'librosa', 'transformers')
    },
}
started = time.perf_counter()
encoder = Encoder(Path('/models'))
report['load_seconds'] = round(time.perf_counter() - started, 4)
assert encoder.audio.get_providers() == ['CPUExecutionProvider']
report['text_runtime_loaded'] = encoder.text is not None
if encoder.text is not None:
    assert encoder.text.get_providers() == ['CPUExecutionProvider']
prompt_vectors = []
for prompt in MOODS.values():
    vector = encoder.encode_text(prompt)
    assert vector.shape == (512,)
    assert np.isfinite(vector).all()
    from downtify.music_ai.store import Store

    prompt_vectors.append(Store.pack(vector))
report['mood_embeddings_sha256'] = hashlib.sha256(
    b''.join(prompt_vectors)
).hexdigest()
report['rss_with_text_mib'] = rss_mib()
encoder.release_text()
gc.collect()
report['rss_after_text_release_mib'] = rss_mib()
report['model_id'] = encoder.identity
with tempfile.TemporaryDirectory() as temporary:
    audio = Path(temporary) / 'synthetic.wav'
    timeline = np.arange(48000 * 12, dtype=np.float32) / 48000
    signal = (
        np.sin(timeline * (2 * np.pi * 440))
        * 0.15
        * (0.7 + 0.3 * np.cos(timeline * 4 * np.pi))
    )
    with wave.open(str(audio), 'wb') as output:
        output.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
        output.writeframes((signal * 32767).astype('<i2').tobytes())
    for phase in ('cold', 'warm'):
        started = time.perf_counter()
        vector = encoder.encode_audio(audio)
        assert vector.shape == (512,)
        assert np.isfinite(vector).all()
        report[f'audio_12s_{phase}_seconds'] = round(
            time.perf_counter() - started, 4
        )
    report['synthetic_embedding_sha256'] = hashlib.sha256(
        vector.astype('<f4').tobytes()
    ).hexdigest()
generator = np.random.default_rng(42)
matrix = generator.standard_normal((100000, 512), dtype=np.float32)
matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
vectors = {str(i): matrix[i] for i in range(len(matrix))}
rows = [
    {'id': str(i), 'artist': f'artist-{i // 3}'} for i in range(len(matrix))
]
started = time.perf_counter()
chosen = rank(rows, vectors, seed='0', limit=40)
assert len(chosen) == 40
report['ranking_100000_seconds'] = round(time.perf_counter() - started, 4)
report['peak_rss_mib'] = round(
    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2
)
print(json.dumps(report, indent=2), flush=True)
