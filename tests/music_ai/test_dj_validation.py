import pytest
from ai_test_support import opted_in_store

from downtify.music_ai.dj_store import DjStore
from downtify.music_ai.dj_validation import receive, validated


@pytest.fixture
def validation(tmp_path):
    store = opted_in_store(tmp_path / 'derived.db')
    for owner in (-1, 1):
        store.set_preferences(owner, {'dj_interactive': True})
    dj = DjStore(store)
    session = dj.create(
        1, 'interactive', 'fete', ['a', 'b'], {'a': {}, 'b': {}}
    )
    job = dj.claim(now=10)
    state = {
        'validation': True,
        'engine': 'engine',
        'runtime': 'runtime',
        'render_speed': 2.1,
        'rendered': 10000,
    }
    assert dj.publish(
        session['id'], job['lease_token'], 'playing', state, now=11
    )
    return (
        store,
        dj,
        {**dj.get(1, session['id']), 'lease_token': job['lease_token']},
    )


def test_proof_requires_an_hour_exact_engine_runtime_and_sufficient_render_speed():
    proof = {
        'engine': 'e',
        'runtime': 'r',
        'continuous_seconds': 3600,
        'render_speed': 1.51,
        'interruptions': 0,
    }
    assert validated(proof, 'e', 'r')
    for changes in (
        {'continuous_seconds': 3599},
        {'engine': 'old'},
        {'runtime': 'old'},
        {'render_speed': 1.5},
        {'interruptions': 1},
        {'render_speed': 'fast'},
        {'continuous_seconds': float('inf')},
    ):
        assert not validated({**proof, **changes}, 'e', 'r')


def test_client_cannot_claim_an_hour_by_seeking_or_forging_elapsed(validation):
    store, _, session = validation
    receive(store, session, 0, 0, now=12)
    proof = receive(store, session, 3600, 1, now=13)
    assert proof['continuous_seconds'] == 0
    assert proof['interruptions'] == 1
    assert not store.metadata('dj_interactive_validation', None)
    repeated = receive(store, session, 3601, 1, now=14)
    assert repeated == proof


def test_paused_and_disabled_sessions_cannot_prove_continuity(validation):
    store, dj, session = validation
    receive(store, session, 0, 0, now=12)
    dj.publish(session['id'], session['lease_token'], 'paused', now=13)
    assert receive(store, session, 1, 1, now=14)['interruptions'] == 1
    store.set_preferences(1, {'dj_interactive': False})
    with pytest.raises(PermissionError):
        receive(store, session, 2, 2, now=15)


def test_delayed_background_report_is_allowed_only_with_continuous_audio_and_no_events(
    validation,
):
    store, dj, session = validation
    receive(store, session, 0, 0, now=12)
    dj.publish(session['id'], session['lease_token'], 'playing', now=40)
    dj.publish(session['id'], session['lease_token'], 'playing', now=65)
    proof = receive(store, session, 60, 1, now=72)
    assert proof['continuous_seconds'] == 60
    assert proof['interruptions'] == 0
    proof = receive(store, session, 61, 2, interruptions=1, now=73)
    assert proof['continuous_seconds'] == 0
    assert proof['interruptions'] == 1


def test_request_arrival_jitter_does_not_misclassify_continuous_audio(
    validation,
):
    store, _, session = validation
    receive(store, session, 0, 0, now=12)
    for index, arrival in enumerate((17.1, 23, 27.1, 33, 37.1), 1):
        proof = receive(store, session, index * 5, index, now=arrival)
        assert proof['interruptions'] == 0
    assert proof['continuous_seconds'] == 25


def test_small_per_report_acceleration_cannot_accumulate_a_false_hour(
    validation,
):
    store, _, session = validation
    receive(store, session, 0, 0, now=12)
    for index in range(1, 7):
        proof = receive(store, session, index * 5.4, index, now=12 + index * 5)
    assert proof['continuous_seconds'] == 0
    assert proof['total_interruptions'] == 1
    assert proof['reset_counts']['clock_drift'] == 1
    assert not store.metadata('dj_interactive_validation', None)


def test_audio_ahead_by_network_jitter_cannot_qualify_before_server_hour(
    validation,
):
    store, dj, session = validation
    receive(store, session, 0, 0, now=12)
    for index in range(1, 3601):
        if index % 20 == 0:
            assert dj.publish(
                session['id'],
                session['lease_token'],
                'playing',
                now=12 + index,
            )
        proof = receive(store, session, index + 1, index, now=12 + index)
        if index == 3599:
            assert proof['continuous_seconds'] == 3599
            assert not store.metadata('dj_interactive_validation', None)
    assert validated(
        store.metadata('dj_interactive_validation', {}), 'engine', 'runtime'
    )


def test_server_timed_uninterrupted_hour_publishes_only_bound_technical_proof(
    validation,
):
    store, dj, session = validation
    for index in range(3601):
        clock = 12 + index
        if index % 20 == 0:
            assert dj.publish(
                session['id'], session['lease_token'], 'playing', now=clock
            )
        receive(store, session, index, index, now=clock)
    proof = store.metadata('dj_interactive_validation', {})
    assert validated(proof, 'engine', 'runtime')
    assert 'owner' not in proof
    assert 'id' not in proof


def test_startup_interruption_requires_a_new_complete_hour_without_restarting_render(
    validation,
):
    store, dj, session = validation
    receive(store, session, 0, 0, now=12)
    broken = receive(store, session, 3600, 1, interruptions=1, now=13)
    assert broken['continuous_seconds'] == 0
    assert broken['total_interruptions'] == 1
    for index in range(1, 3601):
        clock = 13 + index
        if index % 20 == 0:
            assert dj.publish(
                session['id'], session['lease_token'], 'playing', now=clock
            )
        receive(
            store, session, 3600 + index, index + 1, interruptions=1, now=clock
        )
        if index == 3599:
            assert not store.metadata('dj_interactive_validation', None)
    proof = store.metadata('dj_interactive_validation', {})
    assert validated(proof, 'engine', 'runtime')
    assert proof['continuous_seconds'] == 3600
    assert proof['interruptions'] == 0
    assert proof['total_interruptions'] == 1
