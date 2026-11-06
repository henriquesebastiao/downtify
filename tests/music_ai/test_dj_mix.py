import numpy as np
import pytest

pytest.importorskip("scipy", reason="DJ DSP runs in the optional renderer image")

from downtify.music_ai.dj_mix import StereoMixer


RATE = 8000


def sources():
    random = np.random.default_rng(32)
    return [(random.normal(0, 0.1, (RATE * 4, 2))).astype(np.float32) for _ in range(2)]


def plan():
    return [{"id": "one", "start": 0, "end": 4}, {"id": "two", "start": 3, "end": 7}]


def test_chunk_boundaries_do_not_change_the_mix_or_drop_samples():
    audio = sources()
    whole = StereoMixer(plan(), lambda index, _: audio[index], rate=RATE).read(RATE * 7)
    mixer = StereoMixer(plan(), lambda index, _: audio[index], rate=RATE)
    chunks = []
    while mixer.position < mixer.total_frames:
        chunks.append(mixer.read(997))
    streamed = np.concatenate(chunks)
    assert streamed.shape == (RATE * 7, 2)
    np.testing.assert_allclose(whole, streamed, atol=1e-7)
    assert mixer.read(100).shape == (0, 2)


def test_audio_outside_a_transition_is_reconstructed_without_an_eq_change():
    audio = sources()
    result = StereoMixer(plan(), lambda index, _: audio[index], rate=RATE).read(
        RATE * 7
    )
    np.testing.assert_allclose(result[: RATE * 3], audio[0][: RATE * 3], atol=1e-7)
    np.testing.assert_allclose(result[RATE * 4 :], audio[1][RATE:], atol=1e-7)


def test_correlated_bass_is_swapped_instead_of_doubled():
    t = np.arange(RATE * 4) / RATE
    tone = np.repeat((0.2 * np.sin(2 * np.pi * 60 * t))[:, None], 2, axis=1).astype(
        np.float32
    )
    result = StereoMixer(plan(), lambda *_: tone, rate=RATE).read(RATE * 7)
    assert np.max(np.abs(result)) < 0.25
    assert np.all(np.isfinite(result))


def test_short_or_invalid_audio_is_rejected_before_publication():
    with pytest.raises(ValueError, match="shorter"):
        StereoMixer(plan(), lambda *_: np.zeros((10, 2)), rate=RATE).read(100)
    audio = sources()
    audio[0][5, 0] = np.nan
    with pytest.raises(ValueError, match="invalid samples"):
        StereoMixer(plan(), lambda index, _: audio[index], rate=RATE).read(100)


def test_invalid_timeline_or_unbounded_request_is_rejected():
    with pytest.raises(ValueError, match="gap"):
        StereoMixer([{"start": 0, "end": 1}, {"start": 2, "end": 3}], None, rate=RATE)
    mixer = StereoMixer(plan(), lambda *_: None, rate=RATE)
    with pytest.raises(ValueError, match="bounded"):
        mixer.read(RATE * 11)


def test_future_transition_can_change_after_a_finished_track_without_changing_past_audio():
    rows = [
        {"id": str(index), "start": index * 3, "end": index * 3 + 4}
        for index in range(3)
    ]
    audio = np.zeros((RATE * 8, 2), dtype=np.float32)
    audio[:, 0] = 0.1
    mixer = StereoMixer(rows, lambda *_: audio, rate=RATE)
    before = mixer.read(RATE * 5)
    changed = [
        rows[0],
        {**rows[1], "end": 7.2},
        {**rows[2], "id": "replacement", "start": 6.2, "end": 10.2},
    ]
    mixer.replan(changed)
    assert mixer.position == RATE * 5 and mixer.rows[0] == rows[0]
    after = mixer.read(RATE * 6)
    assert len(before) + len(after) == round(10.2 * RATE)
    assert np.isfinite(after).all()
    with pytest.raises(ValueError, match="Rendered transitions"):
        mixer.replan([{**changed[0], "end": 3.9}, *changed[1:]])


def test_replanning_cannot_shorten_current_audio_behind_the_rendered_position():
    rows = [
        {"id": str(index), "start": index * 3, "end": index * 3 + 4}
        for index in range(3)
    ]
    mixer = StereoMixer(
        rows, lambda *_: np.zeros((RATE * 8, 2), dtype=np.float32), rate=RATE
    )
    mixer.read(RATE * 5)
    with pytest.raises(ValueError, match="shortened"):
        mixer.replan(
            [rows[0], {**rows[1], "end": 4.9}, {**rows[2], "start": 4.5, "end": 8.5}]
        )
