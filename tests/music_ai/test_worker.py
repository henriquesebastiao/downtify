from ai_test_support import opted_in_store
import pytest
from downtify.music_ai.store import Store
from downtify.music_ai.worker import Worker, source_path, signature


def vector():
    return [1.0] + [0.0] * 511


class FakeEncoder:
    identity = "synthetic-model"

    def encode_text(self, prompt):
        return vector()

    def encode_audio(self, path, checkpoint):
        checkpoint()
        return vector()


@pytest.fixture
def setup(tmp_path):
    root = tmp_path / "music"
    root.mkdir()
    source = root / "sound.wav"
    source.write_bytes(b"synthetic")
    store = opted_in_store(tmp_path / "derived.db")
    store.observe([{"id": "one", "fingerprint": "first"}])
    store.enqueue(
        "job",
        "analysis",
        {
            "track": "one",
            "path": str(source),
            "fingerprint": "first",
            "model": "synthetic-model",
        },
    )
    return store, root, source


def test_source_must_be_inside_allowlist(tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    outside = tmp_path / "outside.wav"
    outside.write_bytes(b"data")
    with pytest.raises(ValueError, match="allowlisted"):
        source_path(outside, [root])


def test_worker_publishes_only_current_analysis(setup):
    store, root, _ = setup
    worker = Worker(store, FakeEncoder(), [root])
    assert worker.step()
    assert store.vectors("synthetic-model", {"one"})
    with store.connect() as db:
        assert db.execute("SELECT state FROM jobs").fetchone()[0] == "done"


def test_worker_rejects_source_changed_during_inference(setup):
    store, root, source = setup

    class ChangingEncoder(FakeEncoder):
        def encode_audio(self, path, checkpoint):
            path.write_bytes(b"changed contents")
            return vector()

    worker = Worker(store, ChangingEncoder(), [root])
    assert worker.step()
    assert not store.vectors("synthetic-model", {"one"})
    with store.connect() as db:
        assert (
            db.execute("SELECT error FROM jobs").fetchone()[0] == "analysis_unavailable"
        )


def test_disabled_modules_defer_work_without_decoding(setup):
    store, root, _ = setup

    class NoDecodeEncoder(FakeEncoder):
        def encode_audio(self, path, checkpoint):
            pytest.fail("Must not decode while disabled")

    worker = Worker(store, NoDecodeEncoder(), [root])
    store.set_preferences(
        -1,
        {
            "similarity": False,
            "personalization": False,
            "daily": False,
            "weekly": False,
        },
    )
    assert not worker.step()
    with store.connect() as db:
        assert db.execute("SELECT state FROM jobs").fetchone()[0] == "queued"


@pytest.mark.parametrize("feature", ["similarity", "personalization", "daily", "weekly"])
def test_each_shared_analysis_feature_can_run_independently(setup, feature):
    from downtify.music_ai.store import DEFAULTS

    store, root, _ = setup
    flags = {key: False for key in DEFAULTS}
    flags[feature] = True
    store.set_preferences(-1, flags)
    worker = Worker(store, FakeEncoder(), [root])
    assert worker.step()
    assert "one" in store.vectors("synthetic-model", {"one"})


def test_old_lease_cannot_finish_reclaimed_job(setup):
    store, _, _ = setup
    old = store.claim(now=10, lease=1)
    new = store.claim(now=12, lease=1)
    assert old["lease_token"] != new["lease_token"]
    assert not store.finish(old)
    assert store.finish(new)


def test_reclaimed_lease_is_rechecked_even_for_a_fast_decode(setup):
    store, root, _ = setup

    class Reclaimed(FakeEncoder):
        def encode_audio(self, path, checkpoint):
            checkpoint()
            assert store.claim(kind="analysis", now=10**12) is not None
            return vector()

    assert not Worker(store, Reclaimed(), [root]).step()
    assert not store.vectors("synthetic-model", {"one"})


def test_clear_prevents_stale_worker_from_republishing(setup):
    store, root, _ = setup

    class ClearingEncoder(FakeEncoder):
        def encode_audio(self, path, checkpoint):
            store.clear_analyses()
            return vector()

    worker = Worker(store, ClearingEncoder(), [root])
    assert not worker.step()
    assert not store.vectors("synthetic-model", {"one"})
    assert not store.metadata("model")["ready"]
    assert not store.put_analysis(
        "one", "first", "synthetic-model", vector(), generation=0
    )


def test_clear_during_model_load_cannot_resurrect_moods(setup):
    store, root, _ = setup

    class ClearingTextEncoder(FakeEncoder):
        def encode_text(self, prompt):
            store.clear_analyses()
            return vector()

    worker = Worker(store, ClearingTextEncoder(), [root])
    assert not worker.ready
    assert not worker.step()
    assert not store.metadata("model")["ready"]
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM mood_vectors").fetchone()[0] == 0


def test_replacement_before_claim_is_rejected_without_decode(setup):
    store, root, source = setup
    version = list(signature(source))
    store.observe_source("one", version)
    with store.connect() as db:
        import json

        row = db.execute("SELECT payload FROM jobs").fetchone()
        payload = json.loads(row[0])
        payload["source_version"] = version
        db.execute("UPDATE jobs SET payload=?", (json.dumps(payload),))
    source.write_bytes(b"replacement")

    class NoDecodeEncoder(FakeEncoder):
        def encode_audio(self, path, checkpoint):
            pytest.fail("Queued obsolete source must not be decoded")

    assert Worker(store, NoDecodeEncoder(), [root]).step()
    assert not store.vectors("synthetic-model", {"one"})


def test_retry_backoff_and_limit_and_job_kind(setup):
    store, _, _ = setup
    store.enqueue("dj", "dj", {})
    for attempt in range(1, 4):
        job = store.claim(kind="analysis", now=10**12)
        assert job["id"] == "job" and job["attempts"] == attempt
        assert store.finish(job, "failed", "transient")
        assert store.claim(kind="analysis", now=0) is None
    assert store.claim(kind="analysis", now=10**12) is None
    assert store.claim(kind="dj")["id"] == "dj"


def test_physical_signature_fences_completed_vectors(setup):
    store, _, source = setup
    first = list(signature(source))
    assert not store.observe_source("one", first)
    assert store.put_analysis("one", "first", "m", vector(), source_version=first)
    source.write_bytes(b"replaced!")
    second = list(signature(source))
    assert not store.observe_source("one", second)
    assert not store.vectors("m", {"one"})
    assert not store.put_analysis("one", "first", "m", vector(), source_version=first)
    assert store.put_analysis("one", "first", "m", vector(), source_version=second)
