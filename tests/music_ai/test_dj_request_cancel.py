import pytest

from downtify.music_ai.dj_store import CancelledDjRequest


def make(database, owner=1, nonce='intent-one'):
    return database.create(
        owner,
        'interactive',
        'fete',
        ['one', 'two'],
        {'one': {'path': '/music/one.wav'}, 'two': {'path': '/music/two.wav'}},
        nonce=nonce,
    )


def test_cancel_before_a_late_create_prevents_all_work(database):
    database.cancel_request(1, 'intent-one')
    assert database.request_cancelled(1, 'intent-one')
    with pytest.raises(CancelledDjRequest):
        make(database)
    assert database.list(1) == []
    assert database.claim() is None


def test_cancel_after_creation_invalidates_lease_and_is_idempotent(database):
    session = make(database)
    job = database.claim()
    database.cancel_request(1, 'intent-one')
    database.cancel_request(1, 'intent-one')
    assert database.get(1, session['id'])['state'] == 'cancelled'
    assert not database.publish(job['id'], job['lease_token'], 'playing')


def test_identical_nonce_on_another_account_cannot_cancel_owner(database):
    session = make(database)
    database.cancel_request(2, 'intent-one')
    assert database.get(1, session['id'])['state'] == 'queued'
    assert not database.request_cancelled(1, 'intent-one')
    assert database.request_cancelled(2, 'intent-one')
