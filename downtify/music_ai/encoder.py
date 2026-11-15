"""Pinned DCLAP CPU inference, with bounded audio decoding and no network I/O."""

from __future__ import annotations

import hashlib
import json
import os
import selectors
import subprocess
from pathlib import Path

PIPELINE = 'dclap-logmel-48k-128-10s-hop5-chronological-v1'


def verify_manifest(directory: Path):
    directory = directory.resolve(strict=True)
    raw = (directory / 'manifest.json').read_bytes()
    manifest = json.loads(raw)
    if manifest.get('format') not in {1, 2} or not manifest.get('files'):
        raise ValueError('Unsupported model manifest')
    for relative, expected in manifest['files'].items():
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise ValueError('Invalid model path')
        path = (directory / relative).resolve(strict=True)
        if not path.is_relative_to(directory) or not path.is_file():
            raise ValueError('Model file escapes model directory')
        if len(expected) != 64:
            raise ValueError('Invalid SHA256')
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != expected:
            raise ValueError('Model checksum mismatch')
    audio_files = {'model_epoch_36.onnx', 'model_epoch_36.onnx.data'}
    if manifest['format'] == 2:
        if (
            set(manifest['files']) != audio_files | {'moods.json'}
            or manifest.get('preprocessing') != PIPELINE
        ):
            raise ValueError('Unsupported audio bundle')
        cache = json.loads((directory / 'moods.json').read_bytes())
        from .store import MOODS

        if cache.get('source_model') != manifest.get('source_model') or set(
            cache.get('vectors', {})
        ) != set(MOODS.values()):
            raise ValueError('Mood bundle and reference release disagree')
        identity = {
            'preprocessing': PIPELINE,
            'audio': {
                key: manifest['files'][key] for key in sorted(audio_files)
            },
        }
        return (
            'dclap-audio:'
            + hashlib.sha256(
                json.dumps(identity, sort_keys=True).encode()
            ).hexdigest()
        )
    required = {
        'model_epoch_36.onnx',
        'model_epoch_36.onnx.data',
        'clap_text_model.onnx',
    }
    if not required.issubset(manifest['files']):
        raise ValueError('Incomplete DCLAP release')
    tokenizer = directory / 'tokenizer'
    if not tokenizer.is_dir() or not any(
        name.startswith('tokenizer/') for name in manifest['files']
    ):
        raise ValueError('Pinned tokenizer is missing')
    return 'dclap:' + hashlib.sha256(raw).hexdigest()


def audio_segments(path: Path, *, ffmpeg='ffmpeg', checkpoint=lambda: None):
    import numpy as np

    window, hop = 480000, 240000
    proc = subprocess.Popen(
        [
            ffmpeg,
            '-v',
            'error',
            '-nostdin',
            '-threads',
            '1',
            '-i',
            str(path),
            '-f',
            'f32le',
            '-ac',
            '1',
            '-ar',
            '48000',
            '-threads',
            '1',
            'pipe:1',
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )
    pending = b''
    last = None
    count = 0
    selector = None
    try:
        if os.name == 'posix':
            try:
                selector = selectors.DefaultSelector()
                selector.register(proc.stdout, selectors.EVENT_READ)
            except (OSError, ValueError):
                selector.close()
                selector = None
        while True:
            if selector is not None and not selector.select(timeout=1):
                checkpoint()
                continue
            chunk = proc.stdout.read(hop * 4)
            if not chunk:
                break
            pending += chunk
            if len(pending) >= window * 4:
                segment = np.frombuffer(
                    pending[: window * 4], dtype='<f4'
                ).copy()
                yield segment
                last = segment
                count += 1
                pending = pending[hop * 4 :]
        if proc.wait(timeout=10):
            raise ValueError('Audio decoding failed')
        tail = np.frombuffer(pending, dtype='<f4')
        if count == 0:
            if not len(tail):
                raise ValueError('Empty audio')
            yield np.pad(tail, (0, window - len(tail)))
        elif len(tail) > hop:
            # Tail ends exactly at EOF; do not count the last half-window twice.
            missing = window - len(tail)
            yield np.concatenate((last[hop - missing : hop], tail))
    finally:
        if selector is not None:
            selector.close()
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        proc.stdout.close()


class Encoder:
    def __init__(self, directory: Path, *, ffmpeg='ffmpeg'):
        import onnxruntime as ort

        ort.disable_telemetry_events()

        self.identity = verify_manifest(directory)
        self.ffmpeg = ffmpeg
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.audio = ort.InferenceSession(
            str(directory / 'model_epoch_36.onnx'),
            sess_options=options,
            providers=['CPUExecutionProvider'],
        )
        self.text = None
        self.tokenizer = None
        self.cached_moods = None
        manifest = json.loads((directory / 'manifest.json').read_bytes())
        if manifest['format'] == 2:
            self.cached_moods = json.loads(
                (directory / 'moods.json').read_bytes()
            )['vectors']
            return
        from transformers import AutoTokenizer

        self.text = ort.InferenceSession(
            str(directory / 'clap_text_model.onnx'),
            sess_options=options,
            providers=['CPUExecutionProvider'],
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(directory / 'tokenizer'), local_files_only=True
        )

    def release_text(self):
        # The six fixed moods are encoded once. Do not retain the large text
        # tower while the small audio tower processes the library for hours.
        self.text = None
        self.tokenizer = None

    def encode_text(self, prompt):
        import numpy as np

        if self.cached_moods is not None:
            if prompt not in self.cached_moods:
                raise ValueError(
                    'Only the pinned mood descriptions are supported'
                )
            vector = np.asarray(self.cached_moods[prompt], dtype=np.float32)
            if vector.shape != (512,) or not np.isfinite(vector).all():
                raise ValueError('Invalid cached mood vector')
            return vector

        if self.text is None:
            raise RuntimeError('Text encoder has been unloaded')

        tokens = self.tokenizer(
            prompt,
            padding='max_length',
            truncation=True,
            max_length=77,
            return_tensors='np',
        )
        values = {
            entry.name: np.asarray(tokens[entry.name], dtype=np.int64)
            for entry in self.text.get_inputs()
        }
        return self.text.run(None, values)[0].reshape(-1)

    def encode_audio(self, path: Path, *, checkpoint=lambda: None):
        import librosa
        import numpy as np

        total = np.zeros(512, dtype=np.float64)
        count = 0
        for audio in audio_segments(
            path, ffmpeg=self.ffmpeg, checkpoint=checkpoint
        ):
            checkpoint()
            quantized = (np.clip(audio, -1, 1) * 32767).astype(
                np.int16
            ).astype(np.float32) / 32767
            mel = librosa.feature.melspectrogram(
                y=quantized,
                sr=48000,
                n_fft=2048,
                hop_length=480,
                win_length=2048,
                window='hann',
                center=True,
                pad_mode='reflect',
                power=2.0,
                n_mels=128,
                fmin=0,
                fmax=14000,
            )
            logmel = librosa.power_to_db(mel, ref=1.0, amin=1e-10, top_db=None)
            embedding = self.audio.run(
                None,
                {
                    self.audio.get_inputs()[0].name: logmel[
                        None, None, :, :
                    ].astype(np.float32)
                },
            )[0]
            total += embedding.reshape(-1)
            count += 1
        if not count:
            raise ValueError('Empty audio')
        return total / count
