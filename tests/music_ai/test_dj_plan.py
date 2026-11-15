import math
from dataclasses import replace

import pytest

from downtify.music_ai.dj_plan import (
    Profile,
    energy_target,
    harmonic_cost,
    order_tracks,
    tempo_factor,
    timeline,
    transition,
)


def profile(identity='one', **changes):
    original = Profile(
        identity, 180, 120, 0.95, tuple(range(0, 180, 2)), 0.5, 0, 0.9, 0.95
    )
    return replace(original, **changes)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1])
def test_invalid_audio_evidence_is_rejected(value):
    with pytest.raises(ValueError):
        profile(duration=value)


def test_tempo_matching_preserves_pitch_and_bounds_the_time_change():
    assert tempo_factor(120, 60) == 1
    assert tempo_factor(120, 122) == pytest.approx(120 / 122)
    assert tempo_factor(120, 135) is None
    assert tempo_factor(0, 120) is None


def test_reliable_instrumental_transition_spans_complete_bars():
    mix = transition(profile(), profile('two', bpm=122))
    assert mix.aligned
    assert mix.overlap == 16
    assert mix.incoming_speed == pytest.approx(120 / 122)
    assert mix.source_end in profile().downbeats


def test_uncertain_vocals_never_produce_long_overlaps():
    mix = transition(profile(instrumental_confidence=0), profile('two'))
    assert mix.aligned
    assert mix.overlap == 2
    slow = profile(
        bpm=70, downbeats=tuple(range(0, 180, 4)), instrumental_confidence=0
    )
    assert transition(slow, replace(slow, id='two')).overlap <= 2


def test_uncertain_or_irregular_evidence_has_short_safe_fallback():
    mix = transition(profile(confidence=0.1), profile('two'))
    assert not mix.aligned
    assert mix.overlap == 2
    assert mix.incoming_speed == 1
    assert not transition(profile(), profile('two', bpm=135)).aligned


def test_key_compatibility_handles_relative_minor_and_unknown_keys():
    major = profile()
    assert harmonic_cost(major, profile('two', key=21)) == 0.1
    assert harmonic_cost(major, profile('two', key=7)) == 0.15
    assert harmonic_cost(major, profile('two', key=-1)) == 0.5


def test_musical_order_is_reproducible_diverse_and_theme_dependent():
    tracks = [
        profile(str(i), energy=i / 19, artist=f'artist{i // 4}')
        for i in range(20)
    ]
    calm = order_tracks(tracks, 'calme', limit=8)
    assert calm == order_tracks(tracks, 'calme', limit=8)
    assert len(calm) == 8
    assert len({item.id for item in calm}) == 8
    assert all(
        sum(other.artist == item.artist for other in calm) <= 2
        for item in calm
    )
    energetic = order_tracks(tracks, 'energie', seed='0', limit=8)
    assert energetic[0].id == '0'
    assert energetic[-1].energy > energetic[0].energy
    assert energy_target('fete', 1) > energy_target('calme', 1)


def test_timeline_accounts_for_cues_stretch_and_overlap_without_invalid_offsets():
    tracks = [profile(str(i), bpm=120 + i) for i in range(5)]
    result = timeline(tracks)
    assert result[0]['start'] == 0
    for index, row in enumerate(result):
        assert 0.96 <= row['speed'] <= 1.04
        assert row['end'] > row['start']
        assert math.isfinite(row['end'])
        if index:
            previous = result[index - 1]
            assert row['start'] == pytest.approx(
                previous['end'] - previous['transition']['overlap']
            )
    assert result[-1]['transition'] is None
