"""LibraryUpgradeDB on both backends: the same results on SQLite and PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from downtify.library_upgrade_db import (
    JOB_DONE,
    JOB_FAILED,
    JOB_RUNNING,
    JOB_SKIPPED,
    STATE_CANCELLED,
    STATE_DONE,
    STATE_READY,
    LibraryUpgradeDB,
    check_is_fresh,
)


def test_runs_are_created_read_and_updated(backend_db) -> None:
    store = LibraryUpgradeDB(backend_db)
    assert store.latest_run() is None
    assert store.get_run(999) is None

    first = store.create_run(['artwork', 'lyrics'], {'force': False})
    second = store.create_run(['metadata'], {'force': True})
    assert second > first

    run = store.get_run(first)
    assert run['id'] == first
    assert run['state'] == 'scanning'
    assert run['categories'] == ['artwork', 'lyrics']
    assert run['options'] == {'force': False}
    assert run['total_tracks'] == 0
    assert run['total_bytes'] == 0
    assert run['summary'] == {}
    assert not run['finished_at']

    store.set_categories(first, ['artwork'])
    store.set_totals(first, 12, 3400)
    store.set_summary(first, {'artwork': 4})
    store.set_state(first, STATE_READY)
    run = store.get_run(first)
    assert run['categories'] == ['artwork']
    assert run['total_tracks'] == 12
    assert run['total_bytes'] == 3400
    assert run['summary'] == {'artwork': 4}
    assert run['state'] == STATE_READY
    assert not run['finished_at']

    store.set_state(first, STATE_DONE)
    assert store.get_run(first)['finished_at']

    assert store.latest_run()['id'] == second
    store.set_state(second, STATE_CANCELLED)
    assert store.latest_run()['state'] == STATE_CANCELLED


def test_queue_is_claimed_progressed_and_counted(backend_db) -> None:
    store = LibraryUpgradeDB(backend_db)
    run = store.create_run(['artwork'], {})
    assert store.add_jobs(run, []) == 0
    assert store.take_next(run) is None

    assert (
        store.add_jobs(
            run,
            [
                {
                    'file': 'b/two.mp3',
                    'categories': ['artwork'],
                    'size': 200,
                    'title': 'Two',
                    'artist': 'B',
                },
                {
                    'file': 'a/one.mp3',
                    'categories': ['artwork', 'lyrics'],
                    'size': 100,
                    'title': 'One',
                    'artist': 'A',
                },
                {'file': 'c/three.mp3', 'size': 300},
            ],
        )
        == 3
    )
    # A path already queued for the run is ignored, not duplicated.
    assert store.add_jobs(run, [{'file': 'a/one.mp3', 'size': 999}]) == 1
    counts = store.counts(run)
    assert counts['total'] == 3
    assert counts['queued'] == 3
    assert counts['processed_bytes'] == 0

    claimed = store.take_next(run)
    assert claimed['file'] == 'a/one.mp3'
    assert claimed['status'] == JOB_RUNNING
    assert claimed['categories'] == ['artwork', 'lyrics']
    assert claimed['size'] == 100
    assert claimed['title'] == 'One'
    assert claimed['artist'] == 'A'
    assert not claimed['stage']
    assert claimed['changed'] == []

    store.set_stage(run, 'a/one.mp3', 'tags')
    running = store.jobs(run, status=JOB_RUNNING)
    assert [(j['file'], j['stage']) for j in running] == [
        ('a/one.mp3', 'tags')
    ]

    store.finish_job(
        run,
        'a/one.mp3',
        JOB_DONE,
        detail='x' * 600,
        changed=['artwork'],
    )
    done = store.jobs(run, status=JOB_DONE)
    assert len(done) == 1
    assert done[0]['detail'] == 'x' * 500
    assert done[0]['changed'] == ['artwork']
    assert not done[0]['stage']

    second = store.take_next(run)
    assert second['file'] == 'b/two.mp3'
    store.finish_job(run, second['file'], JOB_SKIPPED, detail='nothing')
    third = store.take_next(run)
    assert third['file'] == 'c/three.mp3'
    store.finish_job(run, third['file'], JOB_FAILED, detail='boom')
    assert store.take_next(run) is None

    assert store.counts(run) == {
        'total': 3,
        'queued': 0,
        'running': 0,
        'completed': 1,
        'skipped': 1,
        'failed': 1,
        'finished': 3,
        'processed_bytes': 600,
    }
    assert len(store.jobs(run, limit=2)) == 2
    assert len(store.jobs(run)) == 3


def test_interrupted_jobs_are_requeued_and_deleted(backend_db) -> None:
    store = LibraryUpgradeDB(backend_db)
    run = store.create_run([], {})
    other = store.create_run([], {})
    store.add_jobs(run, [{'file': 'keep.mp3', 'size': 1}])
    store.add_jobs(
        other,
        [{'file': 'x.mp3', 'size': 5}, {'file': 'y.mp3', 'size': 7}],
    )
    assert store.take_next(other)['file'] == 'x.mp3'

    assert store.requeue_running(other) == 1
    counts = store.counts(other)
    assert counts['queued'] == 2
    assert counts['running'] == 0
    assert store.requeue_running(other) == 0

    assert len(store.jobs(other, limit=1)) == 1
    store.delete_run_jobs(other)
    assert store.counts(other)['total'] == 0
    assert store.counts(run)['total'] == 1


def test_checks_are_recorded_per_category_and_keep_best_artwork(
    backend_db,
) -> None:
    store = LibraryUpgradeDB(backend_db)
    store.record_check(
        'a.mp3',
        ['artwork', 'lyrics'],
        app_version='1.0',
        artwork_px=600,
        artwork_source='itunes',
    )
    store.record_check(
        'a.mp3',
        ['artwork'],
        app_version='1.1',
        artwork_px=300,
        artwork_source='spotify',
    )
    store.record_check('empty.mp3', [], app_version='1.0')

    found = store.checks_for(['a.mp3', 'missing.mp3'])
    assert set(found) == {'a.mp3'}
    artwork = found['a.mp3']['artwork']
    assert artwork['app_version'] == '1.1'
    assert artwork['artwork_px'] == 600
    assert artwork['artwork_source'] == 'spotify'
    assert artwork['checked_at']
    lyrics = found['a.mp3']['lyrics']
    assert lyrics['app_version'] == '1.0'
    assert lyrics['artwork_px'] == 600
    assert lyrics['artwork_source'] == 'itunes'
    assert store.checks_for([]) == {}


def test_bulk_checks_and_chunked_lookup(backend_db) -> None:
    store = LibraryUpgradeDB(backend_db)
    assert store.record_checks([], app_version='1.0') == 0
    assert (
        store.record_checks(
            [('b.mp3', ['artwork', 'lyrics']), ('c.mp3', [])],
            app_version='1.0',
        )
        == 2
    )
    found = store.checks_for(['b.mp3', 'c.mp3'])
    assert set(found['b.mp3']) == {'artwork', 'lyrics'}
    assert found['b.mp3']['artwork']['app_version'] == '1.0'
    assert found['b.mp3']['artwork']['artwork_px'] == 0
    assert 'c.mp3' not in found

    # A re-check by a newer version replaces the version and keeps the
    # cover size the earlier check recorded.
    store.record_check('b.mp3', ['artwork'], app_version='1.0', artwork_px=640)
    store.record_checks([('b.mp3', ['artwork'])], app_version='2.0')
    artwork = store.checks_for(['b.mp3'])['b.mp3']['artwork']
    assert artwork['app_version'] == '2.0'
    assert artwork['artwork_px'] == 640

    paths = [f'bulk/{n:04d}.mp3' for n in range(450)]
    store.record_checks(
        [(path, ['artwork']) for path in paths], app_version='1.0'
    )
    assert len(store.checks_for(paths)) == 450


def test_checks_expire_by_version_and_age(backend_db) -> None:
    store = LibraryUpgradeDB(backend_db)
    store.record_check('fresh.mp3', ['artwork'], app_version='1.0')
    check = store.checks_for(['fresh.mp3'])['fresh.mp3']['artwork']

    assert check_is_fresh(check, app_version='1.0', max_age_days=7)
    assert not check_is_fresh(check, app_version='1.1', max_age_days=7)
    assert not check_is_fresh(check, app_version='1.0', max_age_days=0)
    assert not check_is_fresh(None, app_version='1.0', max_age_days=7)

    old = dict(check)
    old['checked_at'] = (
        datetime.now(timezone.utc) - timedelta(days=10)
    ).isoformat()
    assert not check_is_fresh(old, app_version='1.0', max_age_days=7)


def test_forget_checks_empties_the_history(backend_db) -> None:
    store = LibraryUpgradeDB(backend_db)
    store.record_checks(
        [('a.mp3', ['artwork', 'lyrics']), ('b.mp3', ['artwork'])],
        app_version='1.0',
    )
    assert store.forget_checks() == 3
    assert store.checks_for(['a.mp3', 'b.mp3']) == {}
    assert store.forget_checks() == 0
