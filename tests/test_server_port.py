"""Choosing the port from Settings (downtify/server_port.py and
GET|PUT /api/server/port)."""

from __future__ import annotations

import socket

import pytest
from starlette.testclient import TestClient

import main
from downtify import api, server_port
from downtify.server_identity import ServerIdentity
from downtify.server_port import (
    PortError,
    clean_port,
    locked_by,
    port_available,
    resolve_port,
)


@pytest.mark.parametrize(
    ('cli', 'saved', 'env', 'expected'),
    [
        (None, None, {}, (8000, 'default')),
        (None, 9000, {}, (9000, 'settings')),
        (None, 9000, {'DOWNTIFY_PORT': '30321'}, (30321, 'DOWNTIFY_PORT')),
        (None, 9000, {'PORT': '5000'}, (5000, 'PORT')),
        (None, 9000, {'DOWNTIFY_PORT': ''}, (9000, 'settings')),
        (7000, 9000, {'DOWNTIFY_PORT': '30321'}, (7000, '--port')),
    ],
)
def test_where_the_port_comes_from(cli, saved, env, expected):
    assert resolve_port(cli, saved, env) == expected


def test_only_settings_and_the_default_can_be_changed():
    assert not locked_by('settings')
    assert not locked_by('default')
    assert locked_by('DOWNTIFY_PORT') == 'DOWNTIFY_PORT'


def test_port_rules():
    assert clean_port(' 8080 ') == 8080
    for bad in ('80', '70000', 'x', None):
        with pytest.raises(PortError):
            clean_port(bad)


def test_a_port_in_use_is_not_available():
    with socket.socket() as busy:
        busy.bind(('127.0.0.1', 0))
        busy.listen()
        taken = busy.getsockname()[1]
        assert not port_available('127.0.0.1', taken)


def test_the_saved_port_survives_a_reload(tmp_path):
    identity = ServerIdentity(tmp_path)
    assert identity.port is None
    identity.set_port(9100)
    reloaded = ServerIdentity(tmp_path)
    assert reloaded.port == 9100
    assert reloaded.server_id == identity.server_id


@pytest.fixture
def client(tmp_path, monkeypatch):
    for name in ('DOWNTIFY_PORT', 'PORT'):
        monkeypatch.delenv(name, raising=False)
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', tmp_path / 'downloads')
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    monkeypatch.setattr(
        main,
        '_LISTEN',
        {'host': '127.0.0.1', 'port': 8000, 'source': 'default'},
    )
    for name in ('auth', 'activity', 'identity', 'downloader', 'settings'):
        monkeypatch.setattr(api.state, name, getattr(api.state, name))
    monkeypatch.setattr(api.state, 'listen', {})
    restarts = []
    server_port.set_restart_handler(lambda: restarts.append(True))
    app = TestClient(main.build_app(), base_url='http://testserver')
    app.post(
        '/api/auth/login', json={'username': 'admin', 'password': 'downtify'}
    )
    app.restarts = restarts
    yield app
    server_port.set_restart_handler(None)
    server_port._restart['wanted'] = False


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def test_saving_a_port_for_the_next_start(client):
    status = client.get('/api/server/port').json()
    assert status['port'] == 8000
    assert not status['locked_by']
    port = _free_port()

    saved = client.put('/api/server/port', json={'port': port}).json()
    assert saved['next'] == port
    assert saved['saved'] == port
    assert saved['restarting'] is False
    assert client.restarts == []
    assert ServerIdentity(main.DATABASE_DIR).port == port


def test_save_and_restart(client):
    port = _free_port()
    response = client.put(
        '/api/server/port', json={'port': port, 'restart': True}
    )
    assert response.json()['restarting'] is True


def test_bad_or_taken_ports_are_refused(client):
    assert client.put('/api/server/port', json={'port': 80}).status_code == 400
    with socket.socket() as busy:
        busy.bind(('127.0.0.1', 0))
        busy.listen()
        taken = busy.getsockname()[1]
        refused = client.put('/api/server/port', json={'port': taken})
    assert refused.status_code == 409
    assert 'in use' in refused.json()['detail']


def test_the_environment_locks_the_port(client, monkeypatch):
    monkeypatch.setenv('DOWNTIFY_PORT', '30321')
    status = client.get('/api/server/port').json()
    assert status['locked_by'] == 'DOWNTIFY_PORT'
    assert status['next'] == 30321
    refused = client.put('/api/server/port', json={'port': 9000})
    assert refused.status_code == 409


def test_only_admins_change_the_port(client):
    api.state.auth.users.create('maria', 'correct horse battery')
    client.cookies.clear()
    client.post(
        '/api/auth/login',
        json={'username': 'maria', 'password': 'correct horse battery'},
    )
    assert client.get('/api/server/port').status_code == 403
