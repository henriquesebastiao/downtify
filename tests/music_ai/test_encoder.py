import hashlib
import json

import pytest
from downtify.music_ai.encoder import verify_manifest
from downtify.music_ai.encoder import PIPELINE
from downtify.music_ai.store import MOODS


def manifest(tmp_path):
    files = {}
    for name in [
        "model_epoch_36.onnx",
        "model_epoch_36.onnx.data",
        "clap_text_model.onnx",
        "tokenizer/tokenizer.json",
    ]:
        target = tmp_path / name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(b"synthetic model fixture")
        files[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (tmp_path / "manifest.json").write_text(json.dumps({"format": 1, "files": files}))


def test_model_bytes_must_match_manifest(tmp_path):
    manifest(tmp_path)
    first = verify_manifest(tmp_path)
    assert first.startswith("dclap:")
    (tmp_path / "model_epoch_36.onnx.data").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        verify_manifest(tmp_path)


def test_manifest_cannot_read_outside_model_directory(tmp_path):
    models = tmp_path / "models"
    models.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"private")
    (models / "manifest.json").write_text(
        json.dumps(
            {
                "format": 1,
                "files": {"../outside": hashlib.sha256(b"private").hexdigest()},
            }
        )
    )
    with pytest.raises(ValueError, match="escapes"):
        verify_manifest(models)


def test_compact_bundle_keeps_audio_identity_when_only_moods_change(tmp_path):
    files = {}
    for name in ["model_epoch_36.onnx", "model_epoch_36.onnx.data"]:
        (tmp_path / name).write_bytes(b"synthetic audio model")
        files[name] = hashlib.sha256(b"synthetic audio model").hexdigest()
    cache = {
        "source_model": "reference",
        "vectors": {prompt: [1.0] + [0.0] * 511 for prompt in MOODS.values()},
    }

    def write_cache():
        raw = json.dumps(cache).encode()
        (tmp_path / "moods.json").write_bytes(raw)
        files["moods.json"] = hashlib.sha256(raw).hexdigest()
        (tmp_path / "manifest.json").write_text(
            json.dumps(
                {
                    "format": 2,
                    "source_model": "reference",
                    "preprocessing": PIPELINE,
                    "files": files,
                }
            )
        )

    write_cache()
    first = verify_manifest(tmp_path)
    cache["vectors"][next(iter(MOODS.values()))][0] = 0.9
    write_cache()
    assert verify_manifest(tmp_path) == first
    (tmp_path / "moods.json").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        verify_manifest(tmp_path)


def test_compact_bundle_rejects_mismatched_prompt_definitions(tmp_path):
    files = {}
    for name in ["model_epoch_36.onnx", "model_epoch_36.onnx.data", "moods.json"]:
        raw = (
            json.dumps({"source_model": "reference", "vectors": {}}).encode()
            if name == "moods.json"
            else b"synthetic"
        )
        (tmp_path / name).write_bytes(raw)
        files[name] = hashlib.sha256(raw).hexdigest()
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "format": 2,
                "source_model": "reference",
                "preprocessing": PIPELINE,
                "files": files,
            }
        )
    )
    with pytest.raises(ValueError, match="disagree"):
        verify_manifest(tmp_path)
