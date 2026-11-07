"""Deterministic musical planning; no filesystem, model or web dependencies."""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass

from .store import MOODS


@dataclass(frozen=True)
class Profile:
    id: str
    duration: float
    bpm: float
    confidence: float
    downbeats: tuple[float, ...]
    energy: float
    key: int = -1  # pitch class, 0..11 major, 12..23 minor; -1 unknown
    key_confidence: float = 0.0
    instrumental_confidence: float = 0.0
    artist: str = ''

    def __post_init__(self):
        values = (
            self.duration,
            self.bpm,
            self.confidence,
            self.energy,
            self.key_confidence,
            self.instrumental_confidence,
            *self.downbeats,
        )
        if (
            not self.id
            or not all(math.isfinite(value) for value in values)
            or not 1 <= self.duration <= 3600
            or not 0 <= self.bpm <= 400
            or not all(
                0 <= value <= 1
                for value in (
                    self.confidence,
                    self.energy,
                    self.key_confidence,
                    self.instrumental_confidence,
                )
            )
            or self.key not in range(-1, 24)
            or any(not 0 <= beat < self.duration for beat in self.downbeats)
            or any(b <= a for a, b in zip(self.downbeats, self.downbeats[1:]))
        ):
            raise ValueError('Invalid audio profile')


def energy_target(theme: str, fraction: float) -> float:
    if theme not in MOODS:
        raise ValueError('Unknown musical theme')
    position = max(0.0, min(1.0, fraction))
    targets = {
        'calme': 0.22,
        'concentration': 0.4,
        'energie': 0.45 + 0.45 * position,
        'fete': 0.62 + 0.3 * math.sin(math.pi * position / 2),
        'melancolie': 0.38 - 0.13 * position,
        'detente': 0.3 - 0.08 * position,
    }
    return targets[theme]


def harmonic_cost(a: Profile, b: Profile) -> float:
    if min(a.key_confidence, b.key_confidence) < 0.65 or min(a.key, b.key) < 0:
        return 0.5
    pitch_a, pitch_b = a.key % 12, b.key % 12
    same_mode = a.key // 12 == b.key // 12
    interval = (pitch_b - pitch_a) % 12
    if same_mode and interval == 0:
        return 0.0
    if same_mode and interval in {5, 7}:
        return 0.15
    major, minor = (pitch_a, pitch_b) if a.key < 12 else (pitch_b, pitch_a)
    if not same_mode and (minor - major) % 12 == 9:
        return 0.1  # relative major/minor
    return 1.0


def tempo_factor(current: float, incoming: float) -> float | None:
    if current <= 0 or incoming <= 0:
        return None
    # Compare half/double-time interpretations without actually pitching audio.
    choices = [current / (incoming * scale) for scale in (0.5, 1.0, 2.0)]
    permitted = [factor for factor in choices if 0.96 <= factor <= 1.04]
    return (
        min(permitted, key=lambda factor: abs(math.log(factor)))
        if permitted
        else None
    )


def order_tracks(
    profiles: list[Profile], theme: str, *, seed: str = '', limit: int = 20
) -> list[Profile]:
    if not 2 <= limit <= 40 or len({item.id for item in profiles}) != len(
        profiles
    ):
        raise ValueError('Choose distinct local tracks and a bounded set size')
    energy_target(theme, 0)
    remaining = list(profiles)
    selected: list[Profile] = []
    artists: dict[str, int] = {}
    size = min(limit, len(remaining))
    if seed:
        first = next((item for item in remaining if item.id == seed), None)
        if first is None:
            raise ValueError('Seed unavailable')
        selected.append(first)
        remaining.remove(first)
        if first.artist:
            artists[first.artist.casefold()] = 1
    while remaining and len(selected) < size:
        target = energy_target(theme, len(selected) / max(1, size - 1))
        previous = selected[-1] if selected else None

        def cost(item):
            score = 0.65 * abs(item.energy - target)
            if previous is not None:
                score += 0.2 * harmonic_cost(previous, item)
                factor = tempo_factor(previous.bpm, item.bpm)
                score += 0.15 * (abs(math.log(factor)) if factor else 1.0)
            tie = hashlib.sha256(
                f'{theme}:{seed}:{item.id}'.encode()
            ).hexdigest()
            return score, tie

        eligible = [
            item
            for item in remaining
            if not item.artist or artists.get(item.artist.casefold(), 0) < 2
        ]
        if not eligible:
            break
        chosen = min(eligible, key=cost)
        selected.append(chosen)
        remaining.remove(chosen)
        if chosen.artist:
            artists[chosen.artist.casefold()] = (
                artists.get(chosen.artist.casefold(), 0) + 1
            )
    if len(selected) < 2:
        raise ValueError('At least two suitable local tracks are required')
    return selected


@dataclass(frozen=True)
class Transition:
    source_end: float
    incoming_cue: float
    incoming_speed: float
    overlap: float
    aligned: bool
    reason: str


def transition(
    outgoing: Profile, incoming: Profile, outgoing_speed: float = 1.0
) -> Transition:
    if not 0.96 <= outgoing_speed <= 1.04:
        raise ValueError('Unsafe tempo change')
    speed = tempo_factor(outgoing.bpm * outgoing_speed, incoming.bpm)
    reliable = min(outgoing.confidence, incoming.confidence) >= 0.75
    if (
        reliable
        and speed is not None
        and len(outgoing.downbeats) >= 3
        and len(incoming.downbeats) >= 3
    ):
        # Use a complete outgoing measure, never extrapolate a grid past evidence.
        end = outgoing.downbeats[-1]
        cue = incoming.downbeats[0]
        bar = outgoing.downbeats[-1] - outgoing.downbeats[-2]
        if (
            min(
                outgoing.instrumental_confidence,
                incoming.instrumental_confidence,
            )
            >= 0.85
        ):
            bars = min(
                8, len(outgoing.downbeats) - 1, len(incoming.downbeats) - 1
            )
        else:
            bars = 1  # unknown or potentially vocal: avoid a long overlap
        start = outgoing.downbeats[-1 - bars]
        overlap = (end - start) / outgoing_speed
        available = min(
            end / outgoing_speed, (incoming.duration - cue) / speed
        )
        # Irregular grids or excessive vocal overlap use the short fallback.
        if (
            0.5 <= bar <= 12
            and overlap < available / 2
            and (bars > 1 or overlap <= 3.0)
        ):
            return Transition(
                end,
                cue,
                speed,
                overlap,
                True,
                'Mesures alignées · basses échangées'
                if bars > 1
                else 'Mesure alignée · transition courte, voix incertaines',
            )
    overlap = min(
        2.0, outgoing.duration / outgoing_speed / 5, incoming.duration / 5
    )
    return Transition(
        outgoing.duration,
        0.0,
        1.0,
        overlap,
        False,
        'Enchaînement court · tempo ou grille incertains',
    )


def timeline(profiles: list[Profile]) -> list[dict]:
    if len(profiles) < 2:
        raise ValueError('A set requires at least two tracks')
    result = []
    start, cue, speed = 0.0, 0.0, 1.0
    for index, item in enumerate(profiles):
        next_mix = (
            transition(item, profiles[index + 1], speed)
            if index + 1 < len(profiles)
            else None
        )
        source_end = next_mix.source_end if next_mix else item.duration
        if source_end <= cue:
            raise ValueError('Insufficient audio after the incoming cue')
        end = start + (source_end - cue) / speed
        result.append({
            'id': item.id,
            'start': start,
            'end': end,
            'cue': cue,
            'source_end': source_end,
            'speed': speed,
            'transition': asdict(next_mix) if next_mix else None,
        })
        if next_mix:
            if next_mix.overlap >= end - start:
                raise ValueError('Transition consumes the current track')
            start, cue, speed = (
                end - next_mix.overlap,
                next_mix.incoming_cue,
                next_mix.incoming_speed,
            )
    return result
