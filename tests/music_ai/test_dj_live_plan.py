import copy

import numpy as np
import pytest

from downtify.music_ai.dj_live_plan import LivePlan
from downtify.music_ai.dj_mix import StereoMixer
from downtify.music_ai.dj_plan import Profile


def profiles():
    return [
        Profile(
            str(index),
            120,
            120,
            0.95,
            tuple(range(0, 120, 2)),
            0.2 + 0.1 * index,
            artist=str(index),
        )
        for index in range(6)
    ]


def test_skip_is_quantized_beyond_the_rendered_horizon_and_keeps_the_past():
    plan = LivePlan(profiles(), 'fete')
    first = copy.deepcopy(plan.rows[0])
    result = plan.change('next', {}, rendered=24, playhead=0)
    assert 30 <= result['effective_at'] <= 34
    assert plan.rows[0]['start'] == first['start']
    assert plan.rows[0]['cue'] == first['cue']
    assert plan.rows[1]['start'] < first['end']


def test_committed_overlap_is_kept_when_changing_theme_or_replacing_next():
    plan = LivePlan(profiles(), 'fete')
    old = copy.deepcopy(plan.rows)
    rendered = old[1]['start'] + 0.5
    replacement = old[-1]['id']
    result = plan.change(
        'replace', {'id': replacement}, rendered, rendered - 24
    )
    assert plan.rows[0] == old[0]
    assert plan.rows[1]['start'] == old[1]['start']
    assert plan.rows[2]['id'] == replacement
    assert result['effective_at'] >= rendered + 6


def test_rendered_or_unknown_tracks_cannot_be_injected_as_a_replacement():
    plan = LivePlan(profiles(), 'fete')
    for identity in ('missing', plan.rows[0]['id']):
        with pytest.raises(ValueError):
            plan.change('replace', {'id': identity}, 24, 0)
    with pytest.raises(ValueError):
        plan.change('theme', {'theme': 'unknown'}, 24, 0)


def test_mixer_replan_preserves_samples_and_filter_state_before_next_transition():
    plan = LivePlan(profiles(), 'fete')
    audio = {
        row['id']: np.full(
            (120 * 8000, 2), 0.01 * (int(row['id']) + 1), dtype=np.float32
        )
        for row in plan.rows
    }
    mixer = StereoMixer(plan.rows, lambda _, row: audio[row['id']], rate=8000)
    prefix = mixer.read(8000 * 10)
    old_states = copy.deepcopy(mixer.states)
    plan.change(
        'replace', {'id': plan.rows[-1]['id']}, rendered=10, playhead=0
    )
    mixer.replan(plan.rows)
    assert mixer.position == len(prefix)
    for key, value in old_states.items():
        np.testing.assert_array_equal(mixer.states[key], value)
    assert np.all(np.isfinite(mixer.read(8000)))
    invalid = copy.deepcopy(plan.rows)
    invalid[0]['cue'] += 1
    with pytest.raises(ValueError, match='cannot be changed'):
        mixer.replan(invalid)
