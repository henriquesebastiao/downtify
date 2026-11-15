import pytest
from ai_test_support import opted_in_store

from downtify.music_ai import dj_readiness
from downtify.music_ai.dj_store import DjStore


@pytest.fixture
def store(tmp_path):
    value = opted_in_store(tmp_path / 'derived.db')
    value.set_preferences(-1, {'dj_prepared': True, 'dj_interactive': True})
    value.set_preferences(1, {'dj_prepared': True, 'dj_interactive': True})
    return value


def create(database, mode='interactive'):
    return DjStore(database).create(
        1,
        mode,
        'fete',
        ['one', 'two'],
        {
            'one': {'path': '/music/synthetic.wav'},
            'two': {'path': '/music/synthetic-two.wav'},
        },
    )


def test_percentiles_are_distinct_and_bounded():
    assert dj_readiness.stats([]) == {
        'samples': 0,
        'p50_seconds': None,
        'p95_seconds': None,
        'worst_seconds': None,
        'over_target': 0,
        'target_seconds': 10.0,
    }
    values = [1, 2, 3, 4, 20]
    result = dj_readiness.stats(values)
    assert result['samples'] == 5
    assert result['p50_seconds'] == 3
    assert result['p95_seconds'] == 20
    assert result['worst_seconds'] == 20
    assert result['over_target'] == 1
    assert dj_readiness.stats([0, 0])['p50_seconds'] == 0


def test_rolling_history_is_bounded_and_split_by_mode(store):
    for index in range(dj_readiness.HISTORY + 40):
        dj_readiness.record(store, 'interactive', 1.0 + index)
    dj_readiness.record(store, 'prepared', 2.5)
    history = store.metadata('dj_readiness', [])
    assert len(history) == dj_readiness.HISTORY
    result = dj_readiness.summary(store)
    assert result['prepared']['samples'] == 1
    assert result['prepared']['p95_seconds'] == 2.5
    assert result['interactive']['samples'] == dj_readiness.HISTORY - 1
    assert result['history'] == dj_readiness.HISTORY
    with pytest.raises(ValueError):
        dj_readiness.record(store, 'interactive', -1)
    with pytest.raises(ValueError):
        dj_readiness.record(store, 'prepared', float('nan'))
    with pytest.raises(ValueError):
        dj_readiness.record(store, 'other', 1)


def test_first_manifest_read_records_the_delay_once(store):
    session = create(store)
    database = DjStore(store)
    job = database.claim()
    assert database.publish(
        session['id'], job['lease_token'], 'playing', {'rendered': 6}
    )
    created = database.get(1, session['id'])['created']
    assert database.record_ready(1, session['id'], now=created + 4.2) == 4.2
    assert database.get(1, session['id'])['ready_seconds'] == 4.2
    assert database.record_ready(1, session['id'], now=created + 90) is None
    assert database.get(1, session['id'])['ready_seconds'] == 4.2
    # Another owner, an unknown session and a non-ready render never record.
    assert database.record_ready(2, session['id']) is None
    assert database.record_ready(1, 'unknown') is None


def test_ready_delay_is_neither_negative_nor_recorded_before_playback(store):
    session = create(store)
    database = DjStore(store)
    assert database.record_ready(1, session['id']) is None
    job = database.claim()
    database.publish(session['id'], job['lease_token'], 'playing')
    created = database.get(1, session['id'])['created']
    assert database.record_ready(1, session['id'], now=created - 5) == 0
