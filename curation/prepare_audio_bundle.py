"""Build a public, reproducible audio-only DCLAP bundle. No music input."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from downtify.music_ai.encoder import Encoder
from downtify.music_ai.store import MOODS

EXPECTED_SOURCE = (
    'dclap:c52c1238f9199e3095c7bcfb56492e9bad30d1d6882a87b650ea6c13463b750c'
)
PIPELINE = 'dclap-logmel-48k-128-10s-hop5-chronological-v1'
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, default=Path('/models'))
parser.add_argument('--output', type=Path, default=Path('/bundle'))
args = parser.parse_args()
encoder = Encoder(args.source)
if encoder.identity != EXPECTED_SOURCE:
    raise RuntimeError('Unexpected reference release')
args.output.mkdir(parents=True, exist_ok=True)
cached = {'source_model': encoder.identity, 'vectors': {}}
for prompt in MOODS.values():
    vector = encoder.encode_text(prompt)
    if vector.shape != (512,) or not np.isfinite(vector).all():
        raise RuntimeError('Invalid reference mood vector')
    cached['vectors'][prompt] = [float(value) for value in vector]
cache = json.dumps(cached, sort_keys=True, allow_nan=False).encode('utf-8')
(args.output / 'moods.json').write_bytes(cache)
files = {'moods.json': hashlib.sha256(cache).hexdigest()}
for name in ('model_epoch_36.onnx', 'model_epoch_36.onnx.data'):
    source, target = args.source / name, args.output / name
    shutil.copyfile(source, target)
    with target.open('rb') as stream:
        files[name] = hashlib.file_digest(stream, 'sha256').hexdigest()
manifest = {
    'format': 2,
    'source_model': encoder.identity,
    'preprocessing': PIPELINE,
    'files': files,
}
raw = json.dumps(manifest, sort_keys=True, indent=2).encode('utf-8')
(args.output / 'manifest.json').write_bytes(raw)
print(
    json.dumps({
        'source_model': encoder.identity,
        'moods': len(cached['vectors']),
        'bundle_manifest_sha256': hashlib.sha256(raw).hexdigest(),
        'files': files,
    }),
    flush=True,
)
