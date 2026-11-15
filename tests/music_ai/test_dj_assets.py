import pytest
from ai_test_support import opted_in_store

from downtify.music_ai import compute_budget
from downtify.music_ai.dj_assets import Assets
from downtify.music_ai.dj_audio import AudioError
from downtify.music_ai.dj_store import DjStore


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    database = opted_in_store(tmp_path / 'state/derived.db')
    for owner in (-1, 1, 2):
        database.set_preferences(owner, {'dj_prepared': True})
    monkeypatch.setattr(compute_budget, 'pressure_high', lambda: False)
    dj = DjStore(database)
    assets = Assets(database, budget=1024, min_free=0, margin=0)
    return database, dj, assets


def ready(fixture, *, owner=1, data=b'accepted-audio', immutable=False):
    _, dj, assets = fixture
    sources = {
        identity: {
            'path': f'/native/{identity}',
            'source_version': [],
            'fingerprint': identity,
        }
        for identity in ('one', 'two')
    }
    session = dj.create(
        owner,
        'prepared',
        'energie',
        list(sources),
        sources,
    )
    job = dj.claim()
    assert job['id'] == session['id']
    directory = assets.directory(session['id'])
    directory.mkdir(mode=0o700)
    (directory / 'set.m4a').write_bytes(data)
    assert dj.publish(
        session['id'],
        job['lease_token'],
        'ready',
        {
            'duration': 10,
            'immutable_copy': immutable,
            'timeline': [{'id': 'one', 'start': 0, 'end': 10}],
        },
    )
    return dj.get(owner, session['id'])


def test_copy_is_exact_idempotent_and_survives_source_expiration(fixture):
    _, dj, assets = fixture
    source = ready(fixture)
    copied = assets.copy(1, source['id'], 'Mon rock / semaine', 'copy-one')
    assert copied['immutable_copy']
    assert copied['title'] == 'Mon rock / semaine'
    assert copied['ids'] == source['ids']
    assert copied['timeline'] == source['timeline']
    assert assets.media(copied).read_bytes() == b'accepted-audio'
    assert (
        assets.copy(1, source['id'], 'Mon rock / semaine', 'copy-one')['id']
        == copied['id']
    )
    assert assets.expire(source['id'])
    assert assets.media(copied).read_bytes() == b'accepted-audio'
    assert dj.get(1, source['id'])['state'] == 'expired'
    assert not assets.expire(copied['id'])


def test_copy_cannot_cross_owner_or_change_a_replayed_intent(fixture):
    _, _, assets = fixture
    source = ready(fixture)
    with pytest.raises(LookupError):
        assets.copy(2, source['id'], 'Other', 'other')
    assets.copy(1, source['id'], 'Mine', 'same')
    with pytest.raises(ValueError):
        assets.copy(1, source['id'], 'Changed', 'same')


def test_cache_reclaims_an_inactive_set_but_keeps_readers_and_copies(fixture):
    _, _, assets = fixture
    oldest = ready(fixture, data=b'A' * 100)
    playing = ready(fixture, data=b'B' * 100)
    saved = ready(fixture, data=b'C' * 100, immutable=True)
    assets.pin(1, playing['id'], 'device-one')
    assets.budget = 350
    assets.reserve(100)
    assert not assets.directory(oldest['id']).exists()
    assert assets.media(playing).read_bytes() == b'B' * 100
    assert assets.media(saved).read_bytes() == b'C' * 100
    with pytest.raises(AudioError, match='dj_cache_full'):
        assets.reserve(200)


def test_pins_are_separate_for_each_consumer_and_owner(fixture):
    _, _, assets = fixture
    source = ready(fixture)
    assets.pin(1, source['id'], 'first')
    assets.pin(1, source['id'], 'second')
    assets.release(2, source['id'], 'first')
    assets.release(1, source['id'], 'first')
    assert assets.pinned(source['id'])
    assert not assets.expire(source['id'])
    assets.release(1, source['id'], 'second')
    assert assets.expire(source['id'])


def test_budget_failure_keeps_the_source_and_releases_the_copy_pin(fixture):
    _, _, assets = fixture
    source = ready(fixture, data=b'A' * 100)
    assets.budget = 150
    with pytest.raises(AudioError, match='dj_cache_full'):
        assets.copy(1, source['id'], 'No room', 'retry')
    assert assets.media(source).read_bytes() == b'A' * 100
    assert not assets.pinned(source['id'])
    assets.budget = 300
    assert assets.copy(1, source['id'], 'No room', 'retry')['state'] == 'ready'


@pytest.mark.parametrize('name', ['', 'x' * 161, 'bad\nname'])
def test_invalid_names_do_not_create_a_copy(fixture, name):
    database, _, assets = fixture
    source = ready(fixture)
    with pytest.raises(ValueError):
        assets.copy(1, source['id'], name, 'invalid')
    with database.connect() as db:
        assert (
            db.execute('SELECT count(*) FROM dj_sessions').fetchone()[0] == 1
        )


def test_native_work_defers_copy_without_creating_a_request(fixture):
    database, _, assets = fixture
    source = ready(fixture)
    database.set_metadata('native_busy', True)
    with pytest.raises(AudioError, match='dj_cache_busy'):
        assets.copy(1, source['id'], 'Later', 'later')
    with database.connect() as db:
        assert (
            db.execute('SELECT count(*) FROM dj_requests').fetchone()[0] == 0
        )


def test_cache_rejects_symlinks_without_touching_their_target(
    fixture, tmp_path
):
    _, _, assets = fixture
    original = tmp_path / 'original'
    original.write_bytes(b'untouched')
    (assets.root / 'link').symlink_to(original)
    with pytest.raises(AudioError, match='unsafe_cache_entry'):
        assets.used()
    assert original.read_bytes() == b'untouched'


def test_stopping_an_accepted_prepared_set_keeps_it_replayable(fixture):
    _, dj, assets = fixture
    source = ready(fixture)
    assets.pin(1, source['id'], 'one')
    assets.pin(1, source['id'], 'two')
    dj.stop(1, source['id'])
    assets.release(1, source['id'], 'one')
    assert dj.get(1, source['id'])['state'] == 'ready'
    with pytest.raises(RuntimeError):
        assets.discard(1, source['id'])
    assets.release(1, source['id'], 'two')
    assets.discard(1, source['id'])
    assert dj.get(1, source['id'])['state'] == 'deleting'


def test_completed_audio_can_resume_after_failed_commit_without_original(
    fixture, monkeypatch
):
    import os

    _, dj, assets = fixture
    source = ready(fixture)
    replace = os.replace

    def interrupted(src, dst):
        replace(src, dst)
        raise OSError('interrupted after audio publication')

    with monkeypatch.context() as patch:
        patch.setattr(os, 'replace', interrupted)
        with pytest.raises(OSError):
            assets.copy(1, source['id'], 'Keep', 'commit-retry')
    assert assets.expire(source['id'])
    copied = assets.copy(1, source['id'], 'Keep', 'commit-retry')
    assert copied['state'] == 'ready'
    assert assets.media(copied).read_bytes() == b'accepted-audio'


def test_copies_keep_the_current_permission_gate_on_retry(fixture):
    database, _, assets = fixture
    source = ready(fixture)
    assets.copy(1, source['id'], 'Keep', 'permission-retry')
    database.set_preferences(1, {'dj_prepared': False})
    with pytest.raises(PermissionError):
        assets.copy(1, source['id'], 'Keep', 'permission-retry')


def test_orphan_reclamation_keeps_referenced_and_recent_workspaces(fixture):
    import os
    import time

    _, _, assets = fixture
    source = ready(fixture, immutable=True)
    old = assets.directory('b' * 32)
    old.mkdir()
    (old / 'partial.audio').write_bytes(b'O' * 200)
    recent = assets.directory('c' * 32)
    recent.mkdir()
    (recent / 'partial.audio').write_bytes(b'R' * 100)
    os.utime(old, (time.time() - 7200, time.time() - 7200))
    os.utime(
        assets.directory(source['id']),
        (time.time() - 7200, time.time() - 7200),
    )
    assets.budget = 200
    assets.reserve(50)
    assert not old.exists()
    assert recent.exists()
    assert assets.media(source).read_bytes() == b'accepted-audio'


def test_orphan_cleanup_stops_on_lost_lease_before_unlinking(fixture):
    import os
    import time

    _, _, assets = fixture
    old = assets.directory('b' * 32)
    old.mkdir()
    original = old / 'partial.audio'
    original.write_bytes(b'keep')
    os.utime(old, (time.time() - 7200, time.time() - 7200))

    def cancelled():
        raise PermissionError('lease lost')

    with pytest.raises(PermissionError):
        assets.prune_orphans(cancelled)
    assert original.read_bytes() == b'keep'


def test_orphan_cleanup_can_renew_a_compute_lease_without_nested_writers(
    fixture,
):
    import os
    import time

    database, _, assets = fixture
    old = assets.directory('d' * 32)
    old.mkdir()
    (old / 'partial.audio').write_bytes(b'old')
    os.utime(old, (time.time() - 7200, time.time() - 7200))

    def checkpoint():
        database.set_metadata(
            'test_checkpoint', database.metadata('test_checkpoint', 0) + 1
        )

    assert assets.prune_orphans(checkpoint) == 1
    assert database.metadata('test_checkpoint') >= 2
    assert not old.exists()
