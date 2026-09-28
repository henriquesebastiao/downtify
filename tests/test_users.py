"""Accounts, per-user preferences and the activity log (downtify/users.py,
downtify/account_routes.py, downtify/activity.py)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from starlette.testclient import TestClient

import main
from downtify import api
from downtify.activity import (
    ActivityLog,
    NowPlaying,
    clean_track,
    describe_user_agent,
)
from downtify.auth import AuthStore
from downtify.users import (
    DEFAULT_PASSWORD,
    DEFAULT_USERNAME,
    UserError,
    UserStore,
    hash_password,
)

PASSWORD = 'correct horse battery'
DEFAULT_LOGIN = {'username': 'admin', 'password': 'downtify'}


def _users(tmp_path: Path, **kw) -> UserStore:
    store = UserStore(tmp_path / 'auth.db')
    store.ensure_default_admin(existing_install=kw.get('existing', False))
    return store


# ── the store ───────────────────────────────────────────────────────────


def test_a_new_install_gets_the_default_admin_and_no_notice(tmp_path):
    users = _users(tmp_path)

    admin = users.authenticate(DEFAULT_USERNAME, DEFAULT_PASSWORD)
    assert admin['role'] == 'admin'
    assert admin['default_password'] is True
    assert users.notice() is None
    # Only once.
    assert not users.ensure_default_admin(existing_install=True)
    assert users.notice() is None


def test_an_upgraded_install_gets_the_notice(tmp_path):
    users = _users(tmp_path, existing=True)

    assert users.notice() == {'username': 'admin', 'password': 'downtify'}
    users.clear_notice()
    assert users.notice() is None


def test_the_old_sign_in_password_becomes_the_admins(tmp_path):
    # A database from the version with a single password and devices
    # that belonged to nobody.
    db = tmp_path / 'auth.db'
    with sqlite3.connect(db) as conn:
        conn.execute(
            'CREATE TABLE auth_config (key TEXT PRIMARY KEY, value TEXT)'
        )
        conn.execute(
            "INSERT INTO auth_config VALUES ('password_hash', ?)",
            (hash_password(PASSWORD),),
        )
        conn.execute("INSERT INTO auth_config VALUES ('require_sign_in', '1')")
        conn.execute(
            'CREATE TABLE auth_devices (id TEXT PRIMARY KEY, name TEXT NOT '
            "NULL, platform TEXT NOT NULL DEFAULT '', token_hash TEXT NOT "
            'NULL, created_at TEXT NOT NULL, last_seen_at TEXT, last_ip '
            "TEXT NOT NULL DEFAULT '', revoked_at TEXT)"
        )
        conn.execute(
            "INSERT INTO auth_devices VALUES ('dev', 'Pixel', '', 'x', "
            "'2026-01-01', NULL, '', NULL)"
        )
        conn.execute(
            'CREATE TABLE auth_sessions (id_hash TEXT PRIMARY KEY, '
            'created_at TEXT NOT NULL, expires_at TEXT NOT NULL, touched_at '
            "TEXT NOT NULL, ip TEXT NOT NULL DEFAULT '', user_agent TEXT NOT "
            "NULL DEFAULT '')"
        )
        conn.execute(
            "INSERT INTO auth_sessions VALUES ('s', '2026-01-01', "
            "'2099-01-01', '2026-01-01', '', '')"
        )
    conn.close()

    store = AuthStore(db, tmp_path / '.secret', existing_install=True)

    admin = store.users.authenticate('admin', PASSWORD)
    assert admin is not None
    assert admin['default_password'] is False
    assert store.users.authenticate('admin', DEFAULT_PASSWORD) is None
    assert store.users.notice() == {'username': 'admin', 'password': None}
    assert store.get_device('dev')['user_id'] == admin['id']
    with store._connect() as conn:
        assert conn.execute('SELECT * FROM auth_sessions').fetchall() == []
        left = conn.execute(
            "SELECT * FROM auth_config WHERE key IN ('password_hash', "
            "'require_sign_in')"
        ).fetchall()
    assert left == []


def test_creating_users(tmp_path):
    users = _users(tmp_path)
    maria = users.create('maria', PASSWORD)

    assert maria['role'] == 'user'
    assert maria['default_password'] is False
    assert users.authenticate('Maria', PASSWORD)['id'] == maria['id']
    with pytest.raises(UserError, match='taken'):
        users.create('MARIA', PASSWORD)
    with pytest.raises(UserError, match='3 to 32'):
        users.create('a b', PASSWORD)
    with pytest.raises(UserError, match='at least'):
        users.create('joao', 'short')
    with pytest.raises(UserError, match='role'):
        users.create('joao', PASSWORD, 'root')
    assert [u['username'] for u in users.list()] == ['admin', 'maria']


def test_the_last_admin_stays(tmp_path):
    users = _users(tmp_path)
    admin = users.by_username('admin')

    with pytest.raises(UserError, match='last admin'):
        users.update(admin['id'], role='user')
    with pytest.raises(UserError, match='last admin'):
        users.delete(admin['id'])
    second = users.create('boss', PASSWORD, 'admin')
    users.update(admin['id'], role='user')
    assert users.get(admin['id'])['role'] == 'user'
    with pytest.raises(UserError, match='last admin'):
        users.delete(second['id'])


def test_renaming_and_passwords(tmp_path):
    users = _users(tmp_path)
    admin = users.by_username('admin')
    users.create('maria', PASSWORD)

    with pytest.raises(UserError, match='taken'):
        users.update(admin['id'], username='maria')
    users.update(admin['id'], username='root')
    users.set_password(admin['id'], 'another password')
    renamed = users.authenticate('root', 'another password')
    assert renamed['default_password'] is False
    assert users.check_password(admin['id'], 'another password')
    assert not users.check_password(admin['id'], DEFAULT_PASSWORD)


def test_reset_brings_the_admin_back(tmp_path):
    users = _users(tmp_path)
    admin = users.by_username('admin')
    users.create('boss', PASSWORD, 'admin')
    users.update(admin['id'], username='root', role='user')

    restored = users.reset_admin()
    assert restored['username'] == 'admin'
    assert restored['role'] == 'admin'
    assert users.authenticate('admin', DEFAULT_PASSWORD)


def test_preferences_are_per_user_and_typed(tmp_path):
    users = _users(tmp_path)
    admin = users.by_username('admin')
    maria = users.create('maria', PASSWORD)

    users.set_preferences(
        maria['id'],
        {'theme': 'light', 'search_albums': 0, 'password': 'x'},
    )
    users.set_preferences(maria['id'], {'locale': 'pt-BR'})
    assert users.preferences(maria['id']) == {
        'theme': 'light',
        'search_albums': False,
        'locale': 'pt-BR',
    }
    assert users.preferences(admin['id']) == {}


# ── the activity log ────────────────────────────────────────────────────


def test_activity_pages_and_filters(tmp_path):
    log = ActivityLog(tmp_path / 'activity.db')
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


def test_old_activity_is_pruned(tmp_path):
    log = ActivityLog(tmp_path / 'activity.db')
    log.record('login', user_id=1)
    with log._connect() as conn:
        conn.execute("UPDATE activity SET at = '2000-01-01T00:00:00+00:00'")
    log.record('logout', user_id=1)
    assert log.prune() == 1
    assert [e['kind'] for e in log.entries()['entries']] == ['logout']


def test_now_playing():
    now = NowPlaying()
    track = {'title': 'Roads', 'artist': 'Portishead', 'file': 'a.mp3'}
    common = {
        'user_id': 1,
        'username': 'admin',
        'player': 'tab',
        'client': 'Web',
    }

    assert now.report(state='playing', track=track, **common) is True
    assert now.report(state='paused', track=track, **common) is False
    assert now.active()[0]['paused'] is True
    other = {**track, 'file': 'b.mp3'}
    assert now.report(state='playing', track=other, **common) is True
    now.report(state='stopped', track={}, **common)
    assert now.active() == []

    stale = NowPlaying(timeout=-1)
    stale.report(state='playing', track=track, **common)
    assert stale.active() == []


def test_track_and_client_labels():
    assert clean_track({'title': 'x' * 400, 'duration': '12.34', 'no': 1}) == {
        'title': 'x' * 300,
        'duration': 12.3,
    }
    assert clean_track('nope') == {}
    firefox = 'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Firefox/128.0'
    assert describe_user_agent(firefox) == 'Firefox on Linux'
    assert not describe_user_agent('')


# ── over HTTP ───────────────────────────────────────────────────────────


@pytest.fixture
def client(tmp_path, monkeypatch):
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', tmp_path / 'downloads')
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    for name in ('auth', 'activity', 'identity', 'downloader', 'settings'):
        monkeypatch.setattr(api.state, name, getattr(api.state, name))
    monkeypatch.setattr(api.state, 'now_playing', NowPlaying())
    return TestClient(main.build_app(), base_url='http://testserver')


def _sign_in(client, username='admin', password=DEFAULT_PASSWORD):
    response = client.post(
        '/api/auth/login', json={'username': username, 'password': password}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _kinds(client) -> list[str]:
    return [e['kind'] for e in client.get('/api/activity').json()['entries']]


def test_an_upgraded_server_shows_the_notice_until_an_admin_signs_in(
    tmp_path, monkeypatch
):
    # Files from a version without accounts.
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'settings.json').write_text('{}')
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', tmp_path / 'downloads')
    monkeypatch.setattr(main, 'DATABASE_DIR', data)
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    for name in ('auth', 'activity', 'identity', 'downloader', 'settings'):
        monkeypatch.setattr(api.state, name, getattr(api.state, name))
    app = TestClient(main.build_app(), base_url='http://testserver')

    notice = app.get('/api/auth/status').json()['notice']
    assert notice == {'username': 'admin', 'password': 'downtify'}
    _sign_in(app)
    app.cookies.clear()
    assert app.get('/api/auth/status').json()['notice'] is None


def test_admins_manage_users(client):
    _sign_in(client)

    created = client.post(
        '/api/users',
        json={'username': 'maria', 'password': PASSWORD, 'role': 'user'},
    )
    assert created.status_code == 200
    maria = created.json()
    taken = client.post(
        '/api/users', json={'username': 'maria', 'password': PASSWORD}
    )
    assert taken.status_code == 400
    listed = {u['username']: u for u in client.get('/api/users').json()}
    assert listed['maria']['devices'] == 0
    assert 'password_hash' not in listed['maria']

    renamed = client.patch(
        f'/api/users/{maria["id"]}',
        json={'username': 'mariana', 'role': 'admin'},
    ).json()
    assert (renamed['username'], renamed['role']) == ('mariana', 'admin')
    admin_id = listed['admin']['id']
    assert client.delete(f'/api/users/{admin_id}').status_code == 400  # self
    assert client.delete(f'/api/users/{maria["id"]}').json()['deleted']
    assert client.delete(f'/api/users/{maria["id"]}').status_code == 404
    assert {'user_created', 'user_updated', 'user_deleted'} <= set(
        _kinds(client)
    )


def test_a_new_password_from_an_admin_signs_the_user_out(client):
    api.state.auth.users.create('maria', PASSWORD)
    maria = TestClient(client.app, base_url='http://testserver')
    user = _sign_in(maria, 'maria', PASSWORD)['user']
    _sign_in(client)

    client.patch(
        f'/api/users/{user["id"]}', json={'password': 'brand new one'}
    )
    assert maria.get('/api/me').status_code == 401
    _sign_in(maria, 'maria', 'brand new one')


def test_changing_your_own_password(client):
    _sign_in(client)
    wrong = client.put(
        '/api/me/password',
        json={'current_password': 'nope nope', 'new_password': PASSWORD},
    )
    assert wrong.status_code == 403
    short = client.put(
        '/api/me/password',
        json={'current_password': DEFAULT_PASSWORD, 'new_password': 'x'},
    )
    assert short.status_code == 400
    ok = client.put(
        '/api/me/password',
        json={'current_password': DEFAULT_PASSWORD, 'new_password': PASSWORD},
    )
    assert ok.json()['user']['default_password'] is False
    assert client.get('/api/me').status_code == 200  # still signed in
    assert 'password_changed' in _kinds(client)


def test_a_user_changes_only_their_own_things(client):
    api.state.auth.users.create('maria', PASSWORD)
    _sign_in(client, 'maria', PASSWORD)

    prefs = client.put(
        '/api/me/preferences', json={'theme': 'light', 'search_albums': False}
    ).json()
    assert prefs == {'theme': 'light', 'search_albums': False}
    renamed = client.patch('/api/me', json={'username': 'mariana'})
    assert renamed.json()['user']['username'] == 'mariana'
    admin = api.state.auth.users.by_username('admin')
    assert api.state.auth.users.preferences(admin['id']) == {}
    refused = client.patch(f'/api/users/{admin["id"]}', json={'role': 'user'})
    assert refused.status_code == 403


def test_a_users_own_search_albums_choice_wins(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        api.providers,
        'search_albums',
        lambda q, limit: calls.append(q) or [{'name': q}],
    )
    api.state.auth.users.create('maria', PASSWORD)
    _sign_in(client, 'maria', PASSWORD)
    client.put('/api/me/preferences', json={'search_albums': False})

    assert client.get('/api/albums/search', params={'query': 'x'}).json() == []
    client.put('/api/me/preferences', json={'search_albums': True})
    assert client.get('/api/albums/search', params={'query': 'x'}).json()
    assert calls == ['x']


def test_sign_out_everywhere(client):
    store = api.state.auth
    maria = store.users.create('maria', PASSWORD)
    _device, token = store.create_device('Pixel', user_id=maria['id'])
    _sign_in(client, 'maria', PASSWORD)

    assert client.post('/api/me/sign-out-everywhere').json()['revoked']
    assert store.verify_device_token(token) is None
    client.cookies.clear()
    assert client.get('/api/me').status_code == 401


def test_playback_reports_show_up_for_admins(client):
    store = api.state.auth
    maria = store.users.create('maria', PASSWORD)
    _device, token = store.create_device('Pixel 8', user_id=maria['id'])
    phone = {'Authorization': f'Bearer {token}'}
    track = {'title': 'Roads', 'artist': 'Portishead', 'track_id': 't1'}

    for state in ('playing', 'playing', 'paused'):
        response = client.post(
            '/api/activity/playback',
            json={'player': 'app', 'state': state, 'track': track},
            headers=phone,
        )
        assert response.status_code == 200
    bad = client.post(
        '/api/activity/playback',
        json={'state': 'playing', 'track': {}},
        headers=phone,
    )
    assert bad.status_code == 400
    assert client.get('/api/activity/now', headers=phone).status_code == 403

    _sign_in(client)
    now = client.get('/api/activity/now').json()
    assert len(now) == 1
    assert now[0]['username'] == 'maria'
    assert now[0]['client'] == 'Pixel 8'
    assert now[0]['paused'] is True
    entries = client.get('/api/activity', params={'kind': 'playback'}).json()[
        'entries'
    ]
    assert len(entries) == 1  # one song started, however many reports
    assert entries[0]['summary'] == 'Portishead - Roads'
    assert entries[0]['username'] == 'maria'


def test_sign_ins_are_logged(client):
    client.post('/api/auth/login', json={'username': 'admin', 'password': 'x'})
    _sign_in(client)
    client.post('/api/auth/logout')
    _sign_in(client)

    entries = client.get('/api/activity').json()['entries']
    assert [e['kind'] for e in entries][:4] == [
        'login',
        'logout',
        'login',
        'login_failed',
    ]
    assert entries[-1]['summary'] == 'admin'


def test_saved_settings_are_logged_by_name_only(client):
    _sign_in(client)
    client.post(
        '/api/settings/update',
        json={'search_albums': False, 'ui_language': 'en'},
    )
    entry = client.get('/api/activity').json()['entries'][0]
    assert entry['kind'] == 'settings_changed'
    assert entry['detail'] == {'keys': ['search_albums']}


# ── DOWNTIFY_DISABLE_AUTH ───────────────────────────────────────────────


@pytest.fixture
def open_client(tmp_path, monkeypatch):
    monkeypatch.setenv('DOWNTIFY_DISABLE_AUTH', 'true')
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', tmp_path / 'downloads')
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    for name in ('auth', 'activity', 'identity', 'downloader', 'settings'):
        monkeypatch.setattr(api.state, name, getattr(api.state, name))
    return TestClient(main.build_app(), base_url='http://testserver')


def test_with_auth_disabled_everyone_is_the_admin(open_client):
    status = open_client.get('/api/auth/status').json()
    assert status['auth_disabled'] is True
    assert status['signed_in'] is True
    assert status['require_sign_in'] is False
    assert status['user']['username'] == 'admin'
    assert open_client.get('/api/settings').status_code == 200
    assert open_client.get('/api/activity').status_code == 200
    info = open_client.get('/api/server/info').json()
    assert info['require_sign_in'] is False


def test_with_auth_disabled_accounts_cannot_be_managed(open_client):
    assert (
        open_client.post('/api/auth/login', json=DEFAULT_LOGIN).status_code
        == 409
    )
    assert open_client.get('/api/users').status_code == 409
    assert (
        open_client.post(
            '/api/users', json={'username': 'maria', 'password': PASSWORD}
        ).status_code
        == 409
    )
    assert (
        open_client.put(
            '/api/me/password',
            json={'current_password': 'x', 'new_password': PASSWORD},
        ).status_code
        == 409
    )
    # Preferences still work: they're the admin's.
    prefs = open_client.put('/api/me/preferences', json={'theme': 'light'})
    assert prefs.json() == {'theme': 'light'}


def test_with_auth_disabled_apps_and_the_same_site_check_still_apply(
    open_client,
):
    store = api.state.auth
    device, token = store.create_device('Pixel', user_id=1)
    headers = {'Authorization': f'Bearer {token}'}
    assert open_client.get('/api/settings', headers=headers).status_code == 403
    store.revoke_device(device['id'])
    assert open_client.get('/api/queue', headers=headers).status_code == 401
    evil = open_client.put(
        '/api/likes',
        json={'file': 'x.mp3', 'liked': False},
        headers={'Origin': 'https://evil.example'},
    )
    assert evil.status_code == 403
