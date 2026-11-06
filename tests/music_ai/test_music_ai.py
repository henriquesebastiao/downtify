import concurrent.futures
import math
from datetime import datetime

import pytest
from ai_test_support import opted_in_store

from downtify.music_ai.playlists import PARIS, generate, period
from downtify.music_ai.ranking import rank
from downtify.music_ai.store import DEFAULTS, Store


def vector(axis=0):
    result = [0.0] * 512
    result[axis] = 1.0
    return result


@pytest.fixture
def store(tmp_path):
    result = opted_in_store(tmp_path / 'derived.db')
    result.observe([
        {'id': str(i), 'fingerprint': f'v{i}', 'artist': f'artist{i // 3}'}
        for i in range(12)
    ])
    return result


@pytest.mark.parametrize('feature', DEFAULTS)
def test_admin_disable_dominates_user(store, feature):
    store.set_preferences(1, {feature: True})
    store.set_preferences(-1, {feature: False})
    assert not store.effective(1)[feature]
    assert store.preferences(1)[feature]


@pytest.mark.parametrize(
    'changes', [{'daily': 1}, {'unknown': True}, {'similarity': 'false'}]
)
def test_settings_reject_non_boolean_without_mutation(store, changes):
    before = store.preferences(1)
    with pytest.raises(ValueError):
        store.set_preferences(1, changes)
    assert store.preferences(1) == before


def test_replayed_listen_not_double_counted_and_users_isolated(store):
    assert store.listen(1, 'session-1', '0', 110, 'complete')
    assert not store.listen(1, 'session-1', '0', 110, 'complete')
    assert store.listen(2, 'session-1', '1', 110, 'complete')
    assert [x['track'] for x in store.history(1)] == ['0']
    store.forget(1)
    assert not store.history(1)
    assert len(store.history(2)) == 1


def test_disabling_collection_actually_stops_writes(store):
    store.set_preferences(1, {'personalization': False})
    assert not store.listen(1, 'ignored', '0', 50, 'complete')
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM listens').fetchone()[0] == 0


def test_changed_file_invalidates_analysis_and_rejects_stale_worker(store):
    assert store.put_analysis('0', 'v0', 'model1', vector())
    store.observe([{'id': '0', 'fingerprint': 'v2'}])
    assert not store.vectors('model1', {'0'})
    assert not store.put_analysis('0', 'v0', 'model1', vector())
    assert store.put_analysis('0', 'v2', 'model2', vector())
    assert not store.vectors('model1', {'0'})
    assert store.vectors('model2', {'0'})


@pytest.mark.parametrize(
    'bad', [[0] * 512, [math.nan] * 512, [math.inf] * 512, [1] * 511]
)
def test_invalid_vectors_never_enter_index(store, bad):
    with pytest.raises(ValueError):
        store.put_analysis('0', 'v0', 'm', bad)


def test_hidden_tracks_never_leak_through_seed_or_history(store):
    rows = [{'id': '0', 'artist': 'A'}, {'id': '1', 'artist': 'B'}]
    vectors = {'0': vector(), '1': vector(), 'secret': vector()}
    history = [
        {'track': 'secret', 'seconds': 300, 'outcome': 'complete', 'at': 0}
    ]
    assert {r['id'] for r in rank(rows, vectors, history=history)} <= {
        '0',
        '1',
    }
    with pytest.raises(ValueError):
        rank(rows, vectors, seed='secret')


def test_content_similarity_and_artist_diversity():
    rows = [
        {'id': str(i), 'artist': 'same' if i < 5 else str(i)} for i in range(8)
    ]
    vectors = {str(i): vector(0 if i < 6 else 1) for i in range(8)}
    result = rank(rows, vectors, seed='0', limit=5)
    assert all(r['id'] != '0' for r in result)
    assert sum(r['artist'] == 'same' for r in result) <= 2
    assert result[0]['analyzed']
    assert result[0]['id'] not in {'6', '7'}


def test_only_one_worker_claims_a_job_and_expired_lease_is_recoverable(store):
    store.enqueue('one', 'analysis', {'track': '0'})
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs = list(
            pool.map(lambda _: store.claim(now=100, lease=10), range(4))
        )
    assert sum(job is not None for job in jobs) == 1
    assert store.claim(now=109) is None
    assert store.claim(now=111)['id'] == 'one'


@pytest.mark.parametrize(
    ('stamp', 'expected'),
    [
        ('2026-10-25T03:59:00+01:00', '2026-10-24'),
        ('2026-10-25T04:00:00+01:00', '2026-10-25'),
        ('2026-03-29T04:00:00+02:00', '2026-03-29'),
    ],
)
def test_daily_boundary_across_dst(stamp, expected):
    assert period('daily', datetime.fromisoformat(stamp)) == expected


def test_weekly_boundary():
    assert (
        period('weekly', datetime(2026, 11, 2, 4, 14, tzinfo=PARIS))
        == '2026-10-26'
    )
    assert (
        period('weekly', datetime(2026, 11, 2, 4, 15, tzinfo=PARIS))
        == '2026-11-02'
    )


def test_moods_require_real_model_and_generation_is_idempotent(store):
    rows = [{'id': str(i), 'artist': str(i)} for i in range(12)]
    with pytest.raises(RuntimeError):
        generate(store, 1, 'daily', 'calme', rows, 'm')
    with store.connect() as db:
        db.execute(
            'INSERT INTO mood_vectors VALUES (?,?,?)',
            ('calme', 'm', Store.pack(vector())),
        )
    for i in range(12):
        store.put_analysis(str(i), f'v{i}', 'm', vector())
    now = datetime(2026, 11, 5, 12, tzinfo=PARIS)
    first = generate(store, 1, 'daily', 'calme', rows, 'm', now=now)
    second = generate(
        store, 1, 'daily', 'calme', list(reversed(rows)), 'm', now=now
    )
    assert [r['id'] for r in first] == [r['id'] for r in second]
    # Visibility is checked again even for an already-generated playlist.
    remaining = generate(store, 1, 'daily', 'calme', rows[:1], 'm', now=now)
    assert {r['id'] for r in remaining} <= {'0'}


def test_duplicate_recordings_excluded_but_live_versions_preserved():
    rows = [
        {'id': 'seed', 'title': 'Track', 'artist': 'Artist', 'duration': 180},
        {'id': 'copy', 'title': 'TRACK', 'artist': 'Artist', 'duration': 181},
        {
            'id': 'live',
            'title': 'Track (Live)',
            'artist': 'Artist',
            'duration': 200,
        },
        {
            'id': 'other',
            'title': 'Other',
            'artist': 'Another',
            'duration': 180,
        },
    ]
    found = rank(rows, {row['id']: vector() for row in rows}, seed='seed')
    assert {row['id'] for row in found} == {'live', 'other'}


def test_cached_mood_snapshot_excludes_replaced_audio_until_reanalysis(store):
    rows = [{'id': str(i), 'artist': str(i)} for i in range(12)]
    with store.connect() as db:
        db.execute(
            'INSERT INTO mood_vectors VALUES (?,?,?)',
            ('calme', 'm', Store.pack(vector())),
        )
    for i in range(12):
        store.put_analysis(str(i), f'v{i}', 'm', vector())
    now = datetime(2026, 11, 5, 12, tzinfo=PARIS)
    initial = generate(store, 1, 'daily', 'calme', rows, 'm', now=now)
    chosen = initial[0]['id']
    store.observe([
        {'id': chosen, 'fingerprint': 'new-version', 'artist': 'Replacement'}
    ])
    filtered = generate(store, 1, 'daily', 'calme', rows, 'm', now=now)
    assert chosen not in {row['id'] for row in filtered}
    assert len(filtered) == len(initial) - 1
    store.put_analysis(chosen, 'new-version', 'm', vector())
    restored = generate(store, 1, 'daily', 'calme', rows, 'm', now=now)
    assert [row['id'] for row in restored] == [row['id'] for row in initial]


@pytest.mark.parametrize('operation', ['disable', 'forget', 'clear'])
def test_playlist_cannot_reappear_after_concurrent_shutdown(
    store, monkeypatch, operation
):
    from downtify.music_ai import playlists

    rows = [{'id': '0', 'artist': 'A'}]
    store.put_analysis('0', 'v0', 'm', vector())
    with store.connect() as db:
        db.execute(
            'INSERT INTO mood_vectors VALUES (?,?,?)',
            ('calme', 'm', Store.pack(vector())),
        )
    original = playlists.rank

    def changed(*args, **kwargs):
        if operation == 'disable':
            store.set_preferences(1, {'daily': False})
        elif operation == 'forget':
            store.forget(1)
        else:
            store.clear_analyses()
        return original(*args, **kwargs)

    monkeypatch.setattr(playlists, 'rank', changed)
    with pytest.raises((PermissionError, RuntimeError)):
        generate(store, 1, 'daily', 'calme', rows, 'm')
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM playlists').fetchone()[0] == 0
