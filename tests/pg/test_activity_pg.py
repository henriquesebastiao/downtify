"""ActivityLog on both backends: the same results on SQLite and PostgreSQL."""

from __future__ import annotations

from downtify.activity import RETENTION_DAYS, ActivityLog


def _backdate(log: ActivityLog, at: str) -> None:
    with log.db.connect() as conn:
        conn.execute('UPDATE activity SET at = ?', (at,))
        conn.commit()


def test_record_and_read_back(backend_db) -> None:
    log = ActivityLog(backend_db)
    log.record(
        'playback',
        user_id=1,
        username='admin',
        summary='Roads',
        detail={'file': 'a.mp3', 'n': 2},
        client='Web',
        ip='10.0.0.1',
    )
    log.record('login', user_id=2, username='maria', summary='x' * 400)

    page = log.entries()
    assert [e['kind'] for e in page['entries']] == ['login', 'playback']
    assert page['next'] == 0
    newest, oldest = page['entries']
    assert newest['username'] == 'maria'
    assert newest['summary'] == 'x' * 300
    assert newest['detail'] == {}
    assert oldest['id'] == int(oldest['id'])
    assert oldest['user_id'] == 1
    assert oldest['detail'] == {'file': 'a.mp3', 'n': 2}
    assert oldest['client'] == 'Web'
    assert oldest['ip'] == '10.0.0.1'


def test_paging_and_filters(backend_db) -> None:
    log = ActivityLog(backend_db)
    for index in range(5):
        log.record('playback', user_id=1, username='admin', summary=str(index))
    log.record('login', user_id=2, username='maria')

    first = log.entries(limit=3)
    assert [e['summary'] for e in first['entries']] == ['', '4', '3']
    second = log.entries(limit=3, before=first['next'])
    assert [e['summary'] for e in second['entries']] == ['2', '1', '0']
    assert second['next'] == 0
    assert [e['kind'] for e in log.entries(user_id=2)['entries']] == ['login']
    assert len(log.entries(kinds=['playback'])['entries']) == 5
    assert log.entries(limit=0)['entries'][0]['kind'] == 'login'
    assert len(log.entries(limit=10_000)['entries']) == 6


def test_prune_drops_old_entries(backend_db) -> None:
    log = ActivityLog(backend_db)
    log.record('login', user_id=1)
    log.record('logout', user_id=1)
    _backdate(log, '2000-01-01T00:00:00+00:00')
    log.record('settings_changed', user_id=1)

    assert log.prune() == 2
    assert [e['kind'] for e in log.entries()['entries']] == [
        'settings_changed'
    ]
    assert log.prune(days=RETENTION_DAYS) == 0


def test_prune_runs_every_500_inserts(backend_db) -> None:
    log = ActivityLog(backend_db)
    log.record('login', user_id=1)
    _backdate(log, '2000-01-01T00:00:00+00:00')
    log._since_prune = 499
    log.record('logout', user_id=1)

    assert [e['kind'] for e in log.entries()['entries']] == ['logout']
    assert log._since_prune == 0
