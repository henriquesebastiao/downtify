"""Conservative DSP evidence for DJ planning; confidence is never a quality score."""

from __future__ import annotations

import numpy as np

from .dj_plan import Profile


def _positions(values, duration):
    result = np.asarray(values, dtype=np.float64)
    if (
        result.ndim != 1
        or not np.all(np.isfinite(result))
        or np.any(result < 0)
        or np.any(result >= duration)
        or np.any(np.diff(result) <= 0)
    ):
        raise ValueError('Invalid beat evidence')
    return result


def tonal_key(signal, rate):
    """Chromagram correlation with tonal profiles, with an ambiguity margin.

    These conventional profiles describe pitch-class distributions, not an
    audio model. Ambiguous keys are retained with low confidence and ignored
    by the musical planner.
    """
    size = 16384
    if len(signal) < size or np.max(np.abs(signal)) < 1e-5:
        return -1, 0.0
    frequencies = np.fft.rfftfreq(size, 1 / rate)
    keep = (frequencies >= 65) & (frequencies <= min(4000, rate / 2))
    pitches = (
        np.rint(69 + 12 * np.log2(frequencies[keep] / 440)).astype(int) % 12
    )
    chroma = np.zeros(12)
    window = np.hanning(size)
    starts = np.linspace(
        0, len(signal) - size, min(120, max(1, len(signal) // rate)), dtype=int
    )
    for start in starts:
        power = (
            np.abs(np.fft.rfft(signal[start : start + size] * window))[keep]
            ** 0.6
        )
        chroma += np.bincount(
            pitches, weights=power / np.sqrt(frequencies[keep]), minlength=12
        )
    chroma -= chroma.mean()
    norm = np.linalg.norm(chroma)
    if norm < 1e-9:
        return -1, 0.0
    chroma /= norm
    major = np.asarray([
        6.35,
        2.23,
        3.48,
        2.33,
        4.38,
        4.09,
        2.52,
        5.19,
        2.39,
        3.66,
        2.29,
        2.88,
    ])
    minor = np.asarray([
        6.33,
        2.68,
        3.52,
        5.38,
        2.60,
        3.53,
        2.54,
        4.75,
        3.98,
        2.69,
        3.34,
        3.17,
    ])
    scores = []
    for template in (major, minor):
        template = template - template.mean()
        template /= np.linalg.norm(template)
        scores.extend(
            float(chroma @ np.roll(template, pitch)) for pitch in range(12)
        )
    ordered = np.argsort(scores)
    best, runner = int(ordered[-1]), int(ordered[-2])
    confidence = max(0, scores[best]) * min(
        1, max(0, scores[best] - scores[runner]) / 0.12
    )
    return best, float(confidence)


def profile_from_signal(
    identity, signal, rate, beats, downbeats, *, artist=''
):
    signal = np.asarray(signal, dtype=np.float32)
    if (
        signal.ndim != 1
        or not 8000 <= rate <= 192000
        or not rate <= len(signal) <= 3600 * rate
        or not np.all(np.isfinite(signal))
    ):
        raise ValueError('Expected bounded finite mono audio')
    duration = len(signal) / rate
    beats, downbeats = (
        _positions(beats, duration),
        _positions(downbeats, duration),
    )
    rms = float(
        np.sqrt(
            np.einsum('i,i->', signal, signal, dtype=np.float64) / len(signal)
        )
    )
    if rms < 1e-5:
        return Profile(identity, duration, 0.0, 0.0, (), 0.0, artist=artist)
    intervals = np.diff(beats)
    bpm, confidence = 0.0, 0.0
    hop = max(1, round(rate * 0.01))
    frames = signal[: len(signal) // hop * hop].reshape(-1, hop)
    envelope = np.sqrt(
        np.einsum('ij,ij->i', frames, frames, dtype=np.float64) / hop
    )
    onset = np.maximum(0, np.diff(envelope, prepend=envelope[0]))
    if len(intervals) >= 3:
        median = float(np.median(intervals))
        if 0.15 <= median <= 2:
            bpm = 60 / median
            spread = (
                float(np.quantile(np.abs(intervals - median), 0.8)) / median
            )
            regularity = max(0, 1 - spread / 0.15)
            threshold = max(
                1e-5, rms * 0.05, float(np.quantile(onset, 0.9)) * 0.4
            )
            supported = []
            for beat in beats:
                center = round(beat * rate / hop)
                region = onset[
                    max(0, center - 7) : min(len(onset), center + 8)
                ]
                supported.append(
                    bool(len(region) and np.max(region) > threshold)
                )
            attack_support = sum(supported) / len(supported)
            bar_support = 0.0
            if len(downbeats) >= 3:
                indices = np.searchsorted(beats, downbeats)
                indices = np.minimum(indices, len(beats) - 1)
                previous = np.maximum(0, indices - 1)
                indices = np.where(
                    np.abs(beats[previous] - downbeats)
                    < np.abs(beats[indices] - downbeats),
                    previous,
                    indices,
                )
                distances = np.abs(beats[indices] - downbeats)
                lengths = np.diff(indices)
                bar_support = float(np.mean(np.isin(lengths, (3, 4)))) * float(
                    np.mean(distances < 0.07)
                )
            confidence = regularity * attack_support * bar_support
    # A bounded relative intensity estimate, not a genre or mood classifier.
    loudness = float(np.clip((20 * np.log10(max(rms, 1e-9)) + 50) / 40, 0, 1))
    pulse = float(np.clip(bpm / 180, 0, 1)) * confidence
    transients = float(
        np.clip(np.quantile(onset, 0.98) / max(rms, 1e-6), 0, 1)
    )
    energy = 0.3 * loudness + 0.4 * pulse + 0.3 * transients
    key, key_confidence = tonal_key(signal, rate)
    return Profile(
        identity,
        duration,
        float(bpm),
        float(confidence),
        tuple(float(value) for value in downbeats),
        float(energy),
        key,
        key_confidence,
        0.0,
        artist,
    )
