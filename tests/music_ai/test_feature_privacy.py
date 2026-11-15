from datetime import datetime

import pytest
from ai_test_support import opted_in_store

from downtify.music_ai.playlists import PARIS, generate
from downtify.music_ai.store import MOODS


@pytest.mark.parametrize('scope', [-1, 1])
def test_disabled_personalization_retires_inflight_events_without_erasing_history(
    tmp_path, scope
):
    store = opted_in_store(tmp_path / 'derived.db')
    store.observe([{'id': 'one', 'file': 'one.wav', 'fingerprint': '1'}])
    assert store.listen(1, 'old', 'one', 20, 'pause', sequence=1)
    assert store.listen(2, 'other', 'one', 20, 'pause', sequence=1)
    store.set_preferences(scope, {'personalization': False})
    store.set_preferences(scope, {'personalization': True})
    assert not store.listen(
        1, 'old', 'one', 40, 'complete', sequence=2, generation=0
    )
    assert store.history(1)[0]['seconds'] == 20
    assert store.listen(1, 'fresh', 'one', 5, 'pause', generation=1)
    assert store.metadata('profile_revision:2', 0) == (1 if scope == -1 else 0)


def test_mood_generation_does_not_use_retained_history_when_personalization_is_off(
    tmp_path,
):
    rows = [
        {
            'id': str(i),
            'file': f'{i}.wav',
            'title': str(i),
            'artist': f'Artist{i}',
            'fingerprint': str(i),
            'added': 0,
        }
        for i in range(4)
    ]
    vector = [1] + [0] * 511

    def prepare(name):
        database = opted_in_store(tmp_path / name / 'derived.db')
        database.observe(rows)
        assert database.publish_model('m', {mood: vector for mood in MOODS}, 0)
        for row in rows:
            assert database.put_analysis(
                row['id'], row['fingerprint'], 'm', vector
            )
        return database

    now = datetime(2026, 11, 5, 6, tzinfo=PARIS)
    baseline = prepare('neutral')
    baseline.set_preferences(1, {'personalization': False})
    expected = [
        row['id']
        for row in generate(baseline, 1, 'daily', 'calme', rows, 'm', now=now)
    ]
    biased = prepare('retained')
    for index in range(10):
        assert biased.listen(1, str(index), expected[-1], 200, 'complete')
    biased.set_preferences(1, {'personalization': False})
    assert biased.history(1) == []
    with biased.connect() as db:
        assert (
            db.execute(
                'SELECT count(*) FROM listens WHERE owner=1'
            ).fetchone()[0]
            == 10
        )
    actual = [
        row['id']
        for row in generate(biased, 1, 'daily', 'calme', rows, 'm', now=now)
    ]
    assert actual == expected
