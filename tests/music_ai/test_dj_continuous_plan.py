import copy

import numpy as np
import pytest

from downtify.music_ai.dj_live_plan import LivePlan
from downtify.music_ai.dj_mix import StereoMixer
from downtify.music_ai.dj_plan import Profile


def profiles():
    return [
        Profile(
            str(i), 40, 120, 0.95, tuple(range(0, 40, 2)), 0.5, artist=str(i)
        )
        for i in range(6)
    ]


def test_queue_mode_retains_order_and_repeated_occurrences():
    values = profiles()
    plan = LivePlan(values, 'fete', order=['4', '1', '4', '0'])
    assert [row['id'] for row in plan.rows] == ['4', '1', '4', '0']
    assert plan.rows[0]['start'] == 0


def test_continuation_cannot_rewrite_a_committed_transition():
    values = profiles()
    plan = LivePlan(values, 'fete')
    before = copy.deepcopy(plan.rows)
    with pytest.raises(ValueError, match='committed'):
        plan.append(values[:2], before[-1]['end'] - 1)
    assert plan.rows == before
    plan.append(values[:2], 0)
    assert plan.rows[:-3] == before[:-1]
    assert plan.renewals == 1


def test_many_continuations_keep_absolute_positions_and_bounded_history():
    values = profiles()
    plan = LivePlan(values, 'energie', order=['0', '1', '2', '3'])
    last_end = plan.rows[-1]['end']
    for cycle in range(1000):
        rendered = plan.rows[-3]['start']
        plan.append(
            [values[(cycle + 4) % 6], values[(cycle + 5) % 6]], rendered
        )
        plan.trim(rendered)
        assert len(plan.rows) <= 8
        assert plan.rows[-1]['end'] > last_end
        assert all(
            right['start'] <= left['end']
            for left, right in zip(plan.rows, plan.rows[1:])
        )
        last_end = plan.rows[-1]['end']
    assert last_end > 12 * 3600


def test_pruning_history_preserves_current_samples_and_running_filters():
    values = profiles()
    plan = LivePlan(values, 'fete', order=['0', '1', '2', '3', '4', '5'])
    rate = 8000
    signals = {
        p.id: np.full((40 * rate, 2), 0.01 * (int(p.id) + 1), np.float32)
        for p in values
    }
    mixer = StereoMixer(
        plan.rows, lambda _, row: signals[row['id']], rate=rate
    )
    reference = StereoMixer(
        copy.deepcopy(plan.rows), lambda _, row: signals[row['id']], rate=rate
    )
    while mixer.position < round(plan.rows[3]['start'] * rate):
        count = min(rate, round(plan.rows[3]['start'] * rate) - mixer.position)
        mixer.read(count)
        reference.read(count)
    plan.trim(mixer.position / rate, keep=0)
    mixer.replan(plan.rows)
    np.testing.assert_array_equal(mixer.read(rate), reference.read(rate))
