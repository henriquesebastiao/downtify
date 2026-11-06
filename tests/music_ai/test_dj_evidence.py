import numpy as np
import pytest

from downtify.music_ai.dj_evidence import profile_from_signal, tonal_key


def clicks(beats_per_bar=4):
    rate, duration = 22050, 20
    signal = np.zeros(rate * duration, dtype=np.float32)
    beats = np.arange(0.5, duration, 0.5)
    for beat in beats:
        start = round(beat * rate)
        signal[start : start + 220] = 0.5 * np.hanning(440)[:220]
    return rate, signal, beats, beats[::beats_per_bar]


@pytest.mark.parametrize("bar", [3, 4])
def test_confident_grid_requires_both_real_attacks_and_consistent_measures(bar):
    rate, signal, beats, downbeats = clicks(bar)
    profile = profile_from_signal("one", signal, rate, beats, downbeats)
    assert profile.bpm == pytest.approx(120)
    assert profile.confidence >= 0.75
    assert profile.instrumental_confidence == 0  # rhythm never proves absence of vocals


def test_wrong_downbeat_grid_cannot_enable_a_long_transition():
    rate, signal, beats, _ = clicks()
    profile = profile_from_signal("one", signal, rate, beats, beats[::2])
    assert profile.confidence < 0.75


def test_regular_predictions_without_audio_evidence_are_not_confident():
    rate = 22050
    t = np.arange(rate * 20) / rate
    signal = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    beats = np.arange(0.5, 20, 0.5)
    profile = profile_from_signal("one", signal, rate, beats, beats[::4])
    assert profile.confidence < 0.75


def test_silence_has_no_fictional_beats_or_tonal_key():
    profile = profile_from_signal("one", np.zeros(22050), 22050, [], [])
    assert profile.bpm == 0 and profile.confidence == 0 and profile.key == -1


@pytest.mark.parametrize("beats", [[0.5, 0.5], [float("nan")], [-1], [20]])
def test_invalid_model_positions_are_rejected(beats):
    with pytest.raises(ValueError):
        profile_from_signal("one", np.ones(22050 * 20), 22050, beats, [])


def test_tonal_estimate_is_gain_invariant_and_reports_ambiguity():
    rate = 22050
    t = np.arange(rate * 4) / rate
    signal = sum(
        np.sin(2 * np.pi * frequency * t) for frequency in (261.626, 329.628, 391.995)
    ).astype(np.float32)
    key, confidence = tonal_key(signal, rate)
    quiet_key, quiet_confidence = tonal_key(signal * 0.05, rate)
    assert key == quiet_key
    assert quiet_confidence == pytest.approx(confidence, abs=0.01)
    assert 0 <= confidence <= 1
