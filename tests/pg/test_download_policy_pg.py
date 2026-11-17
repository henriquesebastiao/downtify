"""DownloadPolicy on both backends (SQLite file, migrated PostgreSQL)."""

from __future__ import annotations

import threading
import time

import pytest

from downtify.download_policy import DownloadPolicy, DownloadPolicyBlocked
from tests.db.helpers import query

SONG = {
    'song_id': 'TrackABC',
    'name': 'Home (Jedi Knights Remix)',
    'artist': 'Depeche Mode',
    'album': 'Ultra',
    'duration': 424,
}


class Clock:
    """A test clock the policy reads instead of ``time.monotonic``."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _run_threads(count: int, work) -> None:
    """Start ``count`` threads that begin together and run ``work(index)``."""
    barrier = threading.Barrier(count)
    failures: list[BaseException] = []

    def target(index: int) -> None:
        try:
            barrier.wait(timeout=30)
            work(index)
        except BaseException as exc:  # re-raised below, after join
            failures.append(exc)

    threads = [
        threading.Thread(target=target, args=(i,)) for i in range(count)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    assert not any(thread.is_alive() for thread in threads)
    assert not failures, failures


def test_suppress_blocks_and_resume_unblocks(backend_db) -> None:
    policy = DownloadPolicy(backend_db.connect)
    result = policy.suppress(SONG, user_id=7)
    ident = result['id']
    assert result == {'id': ident, 'reason': 'manual'}
    assert policy.blocked(SONG)
    assert (
        query(
            backend_db,
            'SELECT requested_by FROM download_policy WHERE id=?',
            ident,
        )[0][0]
        == 7
    )

    exclusions = policy.exclusions()
    assert len(exclusions) == 1
    assert exclusions[0]['id'] == ident
    assert exclusions[0]['title'] == 'Home (Jedi Knights Remix)'
    assert exclusions[0]['artist'] == 'Depeche Mode'
    assert exclusions[0]['album'] == 'Ultra'
    assert exclusions[0]['duration'] == 424
    assert exclusions[0]['reason'] == 'manual'

    with pytest.raises(DownloadPolicyBlocked) as excinfo:
        policy.begin(SONG, 3600)
    assert excinfo.value.reason == 'download_excluded'

    policy.resume(ident)
    assert not policy.blocked(SONG)
    assert policy.exclusions() == []


def test_resume_rejects_unknown_item(backend_db) -> None:
    policy = DownloadPolicy(backend_db.connect)
    with pytest.raises(ValueError, match='item_not_found'):
        policy.resume('missing')


def test_resume_rejects_attempt_still_stopping(backend_db) -> None:
    policy = DownloadPolicy(backend_db.connect, clock=Clock())
    attempt = policy.begin(SONG, 3600)
    ident = policy.suppress(SONG, user_id=1)['id']
    with pytest.raises(ValueError, match='attempt_still_stopping'):
        policy.resume(ident)
    attempt.finish(successful=False)
    policy.resume(ident)
    assert not policy.blocked(SONG)


def test_identity_uses_metadata_when_track_id_missing(backend_db) -> None:
    policy = DownloadPolicy(backend_db.connect)
    no_id = dict(SONG, song_id='')
    policy.suppress(no_id, user_id=1)
    # Same recording, same metadata, different collaborator suffix.
    variant = dict(no_id, name='Home (Jedi Knights Remix) (feat. Someone)')
    assert policy.blocked(variant)
    assert not policy.blocked(dict(no_id, name='Home (Live)'))


def test_unidentifiable_song_is_rejected(backend_db) -> None:
    policy = DownloadPolicy(backend_db.connect)
    unknown = dict(SONG, song_id='', duration=0)
    with pytest.raises(ValueError, match='identity_uncertain'):
        policy.suppress(unknown, user_id=1)
    assert not policy.blocked(unknown)


def test_url_is_never_stored_as_track_id(backend_db) -> None:
    policy = DownloadPolicy(backend_db.connect)
    song = dict(
        SONG,
        song_id='https://example.test/?token=secret',
        name='Other song',
    )
    policy.suppress(song, user_id=1)
    rows = query(backend_db, 'SELECT track_id FROM download_policy')
    assert [row[0] for row in rows] == ['']
    assert 'secret' not in str([
        tuple(row)
        for row in query(backend_db, 'SELECT * FROM download_policy')
    ])


def test_budget_accumulates_across_attempts_until_timeout(backend_db) -> None:
    clock = Clock()
    policy = DownloadPolicy(backend_db.connect, clock=clock)

    attempt = policy.begin(SONG, 100)
    assert attempt.base == 0
    clock.now = 60
    attempt.finish(successful=False)
    stored = query(backend_db, 'SELECT elapsed, blocked FROM download_policy')
    assert stored[0][0] == 60
    assert stored[0][1] == 0

    # Time between attempts is not charged to the budget.
    clock.now = 1000
    attempt = policy.begin(SONG, 100)
    assert attempt.base == 60
    clock.now += 30
    attempt.check(force=True)
    clock.now += 10
    with pytest.raises(DownloadPolicyBlocked):
        attempt.check(force=True)
    attempt.finish(successful=False)

    assert policy.blocked(SONG)
    assert policy.exclusions()[0]['reason'] == 'timeout'
    assert policy.exclusions()[0]['elapsed'] == 100


def test_success_resets_budget(backend_db) -> None:
    clock = Clock()
    policy = DownloadPolicy(backend_db.connect, clock=clock)
    attempt = policy.begin(SONG, 3600)
    clock.now = 50
    attempt.finish(successful=False)
    policy.succeeded(SONG)
    assert query(backend_db, 'SELECT elapsed FROM download_policy')[0][0] == 0


def test_succeeded_ignores_unknown_song(backend_db) -> None:
    policy = DownloadPolicy(backend_db.connect)
    policy.succeeded(SONG)
    assert query(backend_db, 'SELECT COUNT(*) FROM download_policy')[0][0] == 0


def test_succeeded_does_not_clear_exclusion(backend_db) -> None:
    policy = DownloadPolicy(backend_db.connect)
    ident = policy.suppress(SONG, user_id=1)['id']
    policy.succeeded(SONG)
    assert policy.blocked(SONG)
    assert [row['id'] for row in policy.exclusions()] == [ident]


def test_concurrent_attempts_never_overlap(backend_db) -> None:
    """Eight threads share one policy: at most one attempt may be open."""
    policy = DownloadPolicy(backend_db.connect)
    guard = threading.Lock()
    running = 0
    peak = 0
    accepted: list[bool] = []
    rejected: list[str] = []

    def work(_index: int) -> None:
        nonlocal running, peak
        for _ in range(5):
            try:
                attempt = policy.begin(SONG, 3600)
            except DownloadPolicyBlocked as exc:
                rejected.append(exc.reason)
                continue
            # Counted from the accepted begin until after finish returns,
            # so two open attempts would show up as a peak above one.
            with guard:
                running += 1
                peak = max(peak, running)
            time.sleep(0.005)
            attempt.finish(successful=True)
            with guard:
                running -= 1
            accepted.append(True)

    _run_threads(8, work)
    assert peak == 1
    assert accepted
    assert len(accepted) + len(rejected) == 40
    assert set(rejected) <= {'download_already_active'}
    assert query(backend_db, 'SELECT COUNT(*) FROM download_policy')[0][0] == 1
    assert query(backend_db, 'SELECT elapsed FROM download_policy')[0][0] == 0


def test_concurrent_find_or_create_yields_one_row(backend_db) -> None:
    """Separate policy instances (like separate workers) must not insert
    duplicate rows for the same recording."""
    policies = [DownloadPolicy(backend_db.connect) for _ in range(4)]
    finished: list[bool] = []

    def work(index: int) -> None:
        policy = policies[index % len(policies)]
        for _ in range(3):
            try:
                attempt = policy.begin(SONG, 3600)
            except DownloadPolicyBlocked:
                continue
            attempt.finish(successful=False)
            finished.append(True)

    _run_threads(8, work)
    assert finished
    rows = query(
        backend_db,
        'SELECT COUNT(*) FROM download_policy WHERE track_id=?',
        'TrackABC',
    )
    assert rows[0][0] == 1


def test_manual_exclusion_and_attempt_share_one_row(backend_db) -> None:
    """Suppression during a running attempt must not create a second row."""
    policy = DownloadPolicy(backend_db.connect, clock=Clock())
    attempt = policy.begin(SONG, 3600)
    ident = policy.suppress(SONG, user_id=1)['id']
    attempt.finish(successful=False)
    assert query(backend_db, 'SELECT COUNT(*) FROM download_policy')[0][0] == 1
    assert policy.exclusions()[0]['id'] == ident
