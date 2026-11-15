import pytest
from ai_test_support import opted_in_store

from downtify.music_ai.dj_store import DjStore


@pytest.fixture
def database(tmp_path):
    store = opted_in_store(tmp_path / 'derived.db')
    store.set_preferences(-1, {'dj_prepared': True, 'dj_interactive': True})
    store.set_preferences(1, {'dj_prepared': True, 'dj_interactive': True})
    store.set_preferences(2, {'dj_prepared': True, 'dj_interactive': True})
    return DjStore(store)


def create(database, owner=1, mode='prepared'):
    return database.create(
        owner,
        mode,
        'fete',
        ['one', 'two'],
        {
            'one': {'path': '/music/existing/synthetic.wav'},
            'two': {'path': '/downloads/synthetic.wav'},
        },
    )


def test_session_ownership_is_not_administrative_visibility(database):
    session = create(database)
    with pytest.raises(LookupError):
        database.get(2, session['id'])
    with pytest.raises(LookupError):
        database.stop(2, session['id'])
    assert database.list(2) == []


def test_ordered_queue_keeps_occurrences_with_unique_private_sources(database):
    sources = {'one': {'path': '/music/a'}, 'two': {'path': '/music/b'}}
    value = database.create(
        1,
        'interactive',
        'fete',
        ['two', 'one', 'two'],
        sources,
        queue_order=True,
    )
    job = database.claim()
    assert job['ids'] == ['two', 'one', 'two']
    assert set(job['sources']) == {'one', 'two'}
    database.consumer(1, value['id'])
    assert database.get(1, value['id'])['listener_seen'] > 0
    with pytest.raises(LookupError):
        database.consumer(2, value['id'])


def test_only_one_renderer_can_claim_a_session_and_ready_releases_it(database):
    first, second = create(database), create(database, 2)
    job = database.claim(now=10)
    assert job['id'] == first['id']
    assert database.claim(now=11) is None
    assert database.publish(job['id'], job['lease_token'], 'ready', now=12)
    assert database.claim(now=13)['id'] == second['id']


def test_expired_renderer_cannot_publish_over_a_new_session(database):
    first = create(database)
    job = database.claim(now=10)
    second = create(database, 2)
    assert database.claim(now=60)['id'] == second['id']
    assert not database.publish(
        first['id'], job['lease_token'], 'ready', now=61
    )
    assert database.get(1, first['id'])['state'] == 'failed'


def test_disabling_module_refuses_new_work_and_late_publication(database):
    session = create(database)
    job = database.claim(now=10)
    database.database.set_preferences(-1, {'dj_prepared': False})
    with pytest.raises(PermissionError):
        create(database)
    assert not database.publish(
        session['id'], job['lease_token'], 'ready', now=11
    )
    assert database.get(1, session['id'])['state'] == 'cancelled'


def test_queued_jobs_are_cancelled_before_claim_when_user_turns_module_off(
    database,
):
    session = create(database)
    database.database.set_preferences(1, {'dj_prepared': False})
    assert database.claim() is None
    assert database.get(1, session['id'])['state'] == 'cancelled'


def test_stop_fences_a_renderer_without_deleting_derived_profiles(database):
    session = create(database)
    job = database.claim(now=10)
    database.put_profile('one', 'm', 'fp', [1, 2], {'bpm': 120})
    database.stop(1, session['id'])
    assert not database.publish(
        session['id'], job['lease_token'], 'ready', now=11
    )
    assert database.profile('one', 'm', 'fp', [1, 2]) == {'bpm': 120}


def test_profile_cache_invalidates_replacements_and_model_changes(database):
    database.put_profile('one', 'm', 'fp', [1, 2], {'bpm': 120})
    assert database.profile('one', 'm', 'fp', [1, 3]) is None
    assert database.profile('one', 'new-model', 'fp', [1, 2]) is None
    assert database.profile('one', 'm', 'new-fingerprint', [1, 2]) is None


def test_commands_are_owned_idempotent_and_report_the_committed_horizon(
    database,
):
    session = create(database, mode='interactive')
    job = database.claim(now=10)
    assert database.publish(
        session['id'],
        job['lease_token'],
        'playing',
        {'position': 10, 'rendered': 34, 'next_mutable_at': 36},
        now=11,
    )
    with pytest.raises(LookupError):
        database.command(2, session['id'], 'n', 'next', {}, now=12)
    first = database.command(1, session['id'], 'n', 'next', {}, now=12)
    assert first == database.command(1, session['id'], 'n', 'next', {}, now=12)
    assert first['effective_after_seconds'] == 26
    with pytest.raises(ValueError):
        database.command(
            1, session['id'], 'n', 'theme', {'theme': 'calme'}, now=12
        )
    with database.database.connect() as db:
        assert (
            db.execute('SELECT count(*) FROM dj_commands').fetchone()[0] == 1
        )


def test_pausing_the_analysis_never_blocks_a_live_set(database):
    session = create(database, mode='interactive')
    job = database.claim(now=10)
    assert database.publish(
        session['id'],
        job['lease_token'],
        'playing',
        {'position': 10, 'rendered': 34, 'next_mutable_at': 36},
        now=11,
    )
    with database.database.connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO metadata VALUES ('analysis_paused','true')"
        )
    result = database.command(1, session['id'], 'n', 'next', {}, now=12)
    assert result['effective_after_seconds'] == 26


@pytest.mark.parametrize('action', ['pause', 'resume'])
def test_playback_controls_do_not_report_the_musical_transition_delay(
    database, action
):
    session = create(database, mode='interactive')
    job = database.claim(now=10)
    assert database.publish(
        session['id'],
        job['lease_token'],
        'playing',
        {'position': 10, 'rendered': 34, 'next_mutable_at': 236},
        now=11,
    )
    result = database.command(1, session['id'], action, action, {}, now=12)
    assert result['effective_after_seconds'] == 0


def test_command_receipts_require_current_lease_and_retries_return_the_actual_result(
    database,
):
    session = create(database, mode='interactive')
    job = database.claim(now=10)
    database.command(1, session['id'], 'one', 'replace', {'id': 'two'}, now=12)
    assert (
        database.pending_commands(session['id'], job['lease_token'], now=13)[
            0
        ]['nonce']
        == 'one'
    )
    result = {'accepted': True, 'effective_after_seconds': 30, 'revision': 1}
    assert not database.complete_command(
        session['id'], 'stale', 'one', result, now=13
    )
    assert database.complete_command(
        session['id'], job['lease_token'], 'one', result, now=13
    )
    assert not database.complete_command(
        session['id'], job['lease_token'], 'one', result, now=13
    )
    assert (
        database.command(
            1, session['id'], 'one', 'replace', {'id': 'two'}, now=14
        )
        == result
    )
    assert (
        database.pending_commands(session['id'], job['lease_token'], now=14)
        == []
    )
    with pytest.raises(RuntimeError):
        database.command(1, session['id'], 'two', 'next', {}, now=55)
    for action, payload in [
        ('pause', {'extra': True}),
        ('theme', {'theme': 'unknown'}),
        ('replace', {'id': 'outside'}),
    ]:
        with pytest.raises(ValueError):
            database.command(1, session['id'], 'bad', action, payload, now=14)


def test_worker_metadata_cannot_replace_identity(database):
    session = create(database)
    job = database.claim(now=10)
    with pytest.raises(ValueError):
        database.publish(
            session['id'], job['lease_token'], 'playing', {'owner': 2}, now=11
        )
    assert database.get(1, session['id'])['owner'] == 1


def test_erasure_cancels_render_and_blocks_old_profiles_even_after_resume(
    database,
):
    session = create(database)
    job = database.claim(now=10)
    options = {
        'generation': 0,
        'session': session['id'],
        'token': job['lease_token'],
        'now': 11,
    }
    assert database.put_profile(
        'one', 'm', 'fp', [1, 2], {'bpm': 120}, **options
    )
    database.database.clear_analyses()
    assert database.profile('one', 'm', 'fp', [1, 2]) is None
    assert database.get(1, session['id'])['state'] == 'cancelled'
    assert not database.alive(session['id'], job['lease_token'], now=12)
    assert not database.put_profile(
        'one', 'm', 'fp', [1, 2], {'bpm': 120}, **options
    )
    database.database.set_metadata('analysis_paused', False)
    assert not database.put_profile(
        'one', 'm', 'fp', [1, 2], {'bpm': 120}, generation=0
    )


def test_profile_publication_checks_module_and_current_lease(database):
    session = create(database)
    job = database.claim(now=10)
    assert database.alive(session['id'], job['lease_token'], now=11)
    assert not database.alive(session['id'], job['lease_token'], now=55)
    database.database.set_preferences(1, {'dj_prepared': False})
    assert not database.put_profile(
        'one',
        'm',
        'fp',
        [1, 2],
        {'bpm': 120},
        generation=0,
        session=session['id'],
        token=job['lease_token'],
        now=12,
    )


def test_creation_retry_returns_same_job_and_nonce_is_owner_scoped(database):
    sources = {'one': {}, 'two': {}}
    first = database.create(
        1, 'prepared', 'calme', ['one', 'two'], sources, nonce='retry'
    )
    second = database.create(
        1, 'prepared', 'calme', ['one', 'two'], sources, nonce='retry'
    )
    assert first['id'] == second['id']
    assert len(database.list(1)) == 1
    assert (
        database.create(
            2, 'prepared', 'calme', ['one', 'two'], sources, nonce='retry'
        )['id']
        != first['id']
    )
    with pytest.raises(ValueError):
        database.create(
            1, 'prepared', 'energie', ['one', 'two'], sources, nonce='retry'
        )
    # Pre-HLS receipts used exactly this intent representation.
    with database.database.connect() as db:
        assert (
            db.execute(
                'SELECT intent FROM dj_requests WHERE owner=1 AND nonce=?',
                ('retry',),
            ).fetchone()[0]
            == '["prepared","calme",["one","two"]]'
        )


def test_discard_is_owned_fences_work_and_waits_for_renderer_cleanup(database):
    session = create(database)
    job = database.claim(now=10)
    with pytest.raises(LookupError):
        database.discard(2, session['id'])
    database.discard(1, session['id'])
    assert not database.alive(session['id'], job['lease_token'], now=11)
    assert not database.publish(
        session['id'], job['lease_token'], 'ready', now=11
    )
    assert database.deletion_requests() == [session['id']]
    database.deleted(session['id'])
    assert database.deletion_requests() == []
    assert database.list(1) == []
    with database.database.connect() as db:
        assert db.execute('SELECT count(*) FROM dj_sources').fetchone()[0] == 0
