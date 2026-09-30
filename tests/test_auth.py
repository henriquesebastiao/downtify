"""Sign-in, paired devices, pairing codes, signed URLs and the middleware
that enforces them (downtify/auth.py, downtify/auth_routes.py). Accounts
themselves are tests/test_users.py."""

from __future__ import annotations

import re
import time
from ipaddress import ip_network
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute, APIWebSocketRoute
from starlette.routing import Mount, Route
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import main
from downtify import account_routes, api, auth_routes, mobile_routes
from downtify.auth import (
    ADMIN,
    CLIENT,
    PUBLIC,
    SESSION_COOKIE,
    USER,
    AuthStore,
    PairingStore,
    Principal,
    RateLimiter,
    TicketStore,
    allows,
    classify,
    client_ip,
    normalize_pairing_code,
    rule_for,
)
from downtify.server_identity import ServerIdentity
from downtify.users import hash_password, verify_password

PASSWORD = 'correct horse battery'
DEFAULT = {'username': 'admin', 'password': 'downtify'}


def _store(tmp_path: Path, **kw: Any) -> AuthStore:
    return AuthStore(tmp_path / 'auth.db', tmp_path / '.secret', **kw)


def _admin_id(store: AuthStore) -> int:
    return store.users.by_username('admin')['id']


# ── passwords ───────────────────────────────────────────────────────────


def test_password_hash_round_trip_and_salt():
    first = hash_password(PASSWORD)
    second = hash_password(PASSWORD)

    assert first != second  # salted
    assert first.startswith('scrypt$')
    assert verify_password(PASSWORD, first)
    assert not verify_password('wrong password', first)
    assert not verify_password(PASSWORD, 'garbage')


# ── sessions ────────────────────────────────────────────────────────────


def test_sessions_belong_to_a_user(tmp_path):
    store = _store(tmp_path)
    admin = _admin_id(store)
    token = store.create_session(admin, '1.2.3.4', 'Firefox')

    assert store.session_user(token)['username'] == 'admin'
    assert store.session_user(token + 'x') is None
    assert store.session_user('') is None
    store.end_session(token)
    assert store.session_user(token) is None


def test_an_expired_session_is_gone(tmp_path):
    store = _store(tmp_path)
    token = store.create_session(_admin_id(store))
    with store._connect() as conn:
        conn.execute(
            "UPDATE auth_sessions SET expires_at = '2000-01-01T00:00:00+00:00'"
        )
    assert store.session_user(token) is None


def test_a_deleted_users_session_is_gone(tmp_path):
    store = _store(tmp_path)
    user = store.users.create('maria', PASSWORD)
    token = store.create_session(user['id'])
    store.users.delete(user['id'])
    assert store.session_user(token) is None


def test_end_user_sessions_can_keep_one(tmp_path):
    store = _store(tmp_path)
    admin = _admin_id(store)
    keep = store.create_session(admin)
    other = store.create_session(admin)
    user = store.users.create('maria', PASSWORD)
    theirs = store.create_session(user['id'])

    assert store.end_user_sessions(admin, keep) == 1
    assert store.session_user(keep)
    assert store.session_user(other) is None
    assert store.session_user(theirs)


def test_reset_restores_the_default_admin(tmp_path):
    store = _store(tmp_path)
    admin = _admin_id(store)
    store.users.set_password(admin, PASSWORD)
    session = store.create_session(admin)
    device, token = store.create_device('Pixel', user_id=admin)

    store.reset()

    assert store.users.authenticate('admin', 'downtify')['role'] == 'admin'
    assert store.users.get(admin)['default_password']
    assert store.session_user(session) is None
    assert store.verify_device_token(token)['id'] == device['id']


# ── devices ─────────────────────────────────────────────────────────────


def test_device_token_round_trip(tmp_path):
    store = _store(tmp_path)
    admin = _admin_id(store)
    device, token = store.create_device(
        '  Pixel   8 ', 'android', '10.0.0.5', admin
    )

    assert re.fullmatch(r'dtfy_[a-z2-9]{12}_[A-Za-z0-9_-]{43}', token)
    assert device['name'] == 'Pixel 8'
    assert device['username'] == 'admin'
    assert store.verify_device_token(token, '10.0.0.6') == {
        'id': device['id'],
        'name': 'Pixel 8',
        'user_id': admin,
        'username': 'admin',
        'role': 'admin',
    }
    # Only a hash is stored.
    with store._connect() as conn:
        stored = conn.execute('SELECT token_hash FROM auth_devices').fetchone()
    assert token.split('_')[-1] not in stored['token_hash']


def test_a_revoked_token_fails(tmp_path):
    store = _store(tmp_path)
    device, token = store.create_device('Pixel', user_id=1)

    assert store.revoke_device(device['id'])
    assert store.verify_device_token(token) is None
    assert store.list_devices() == []
    assert not store.revoke_device(device['id'])


@pytest.mark.parametrize(
    'bad',
    [
        '',
        'dtfy_',
        'Bearer x',
        'dtfy_aaaaaaaaaaaa_short',
        'dtfy_UPPERCASE12_x' * 3,
    ],
)
def test_malformed_tokens_fail(tmp_path, bad):
    assert _store(tmp_path).verify_device_token(bad) is None


def test_a_wrong_secret_for_a_real_device_fails(tmp_path):
    store = _store(tmp_path)
    _device, token = store.create_device('Pixel', user_id=1)
    forged = token[:-4] + ('AAAA' if not token.endswith('AAAA') else 'BBBB')
    assert store.verify_device_token(forged) is None


def test_a_deleted_users_devices_stop_working(tmp_path):
    store = _store(tmp_path)
    user = store.users.create('maria', PASSWORD)
    _device, token = store.create_device('Pixel', user_id=user['id'])
    assert store.verify_device_token(token)['username'] == 'maria'
    store.users.delete(user['id'])
    assert store.verify_device_token(token) is None


def test_devices_are_listed_per_user(tmp_path):
    store = _store(tmp_path)
    user = store.users.create('maria', PASSWORD)
    store.create_device('Admin phone', user_id=1)
    store.create_device('Maria phone', user_id=user['id'])

    assert [d['name'] for d in store.list_devices(user['id'])] == [
        'Maria phone'
    ]
    assert len(store.list_devices()) == 2


def test_revoke_user_signs_one_user_out_everywhere(tmp_path):
    store = _store(tmp_path)
    user = store.users.create('maria', PASSWORD)
    device, token = store.create_device('Pixel', user_id=user['id'])
    _other, admin_token = store.create_device('Admin', user_id=1)
    session = store.create_session(user['id'])

    assert store.revoke_user(user['id']) == [device['id']]
    assert store.verify_device_token(token) is None
    assert store.session_user(session) is None
    assert store.verify_device_token(admin_token)


def test_revoke_everything(tmp_path):
    store = _store(tmp_path)
    device, token = store.create_device('Pixel', user_id=1)
    session = store.create_session(1)
    url = store.signer.sign_url('/cover', device_id=device['id'])

    store.revoke_everything()

    assert store.verify_device_token(token) is None
    assert store.session_user(session) is None
    path, query = url.split('?')
    assert store.signer.verify_signed('GET', path, query) is None


# ── pairing ─────────────────────────────────────────────────────────────


def test_pairing_code_is_single_use():
    pairing = PairingStore()
    started = pairing.create(7)
    assert pairing.owner(started['pairing_id']) == 7

    assert re.fullmatch(r'[0-9A-Z]{4}-[0-9A-Z]{4}', started['code'])
    assert pairing.status(started['pairing_id'])['status'] == 'pending'
    assert pairing.claim(started['code'].lower()) == started['pairing_id']
    assert pairing.claim(started['code']) is None
    pairing.complete(started['pairing_id'], {'id': 'dev'})
    assert pairing.status(started['pairing_id']) == {
        'status': 'paired',
        'device': {'id': 'dev'},
    }


def test_pairing_code_expires():
    pairing = PairingStore(ttl_seconds=0)
    started = pairing.create()
    time.sleep(0.01)

    assert pairing.claim(started['code']) is None
    assert pairing.status(started['pairing_id'])['status'] == 'expired'


def test_pairing_code_typing_is_forgiving():
    assert normalize_pairing_code('k7qm-2xpd') == 'K7QM2XPD'
    assert normalize_pairing_code('K7QM 2XPO') == 'K7QM2XP0'
    assert not normalize_pairing_code('K7QM')
    assert not normalize_pairing_code(None)


def test_a_cancelled_pairing_cannot_be_claimed():
    pairing = PairingStore()
    started = pairing.create()
    pairing.cancel(started['pairing_id'])
    assert pairing.claim(started['code']) is None


# ── tickets and rate limits ─────────────────────────────────────────────


def test_ws_ticket_is_single_use_and_expires():
    tickets = TicketStore()
    principal = Principal('device', CLIENT, 'abc', 1, 'admin', 'admin')
    ticket = tickets.create(principal)
    assert tickets.claim(ticket) == principal
    assert tickets.claim(ticket) is None

    short = TicketStore(ttl_seconds=0)
    old = short.create(principal)
    time.sleep(0.01)
    assert short.claim(old) is None


def test_rate_limiting_kicks_in_and_resets():
    limiter = RateLimiter(limit=3, window=60)
    for _ in range(3):
        assert limiter.retry_after('ip') == 0
        limiter.fail('ip')
    assert limiter.retry_after('ip') > 0
    assert limiter.retry_after('other') == 0
    limiter.reset('ip')
    assert limiter.retry_after('ip') == 0


def test_x_forwarded_for_only_from_a_trusted_proxy():
    scope = {
        'client': ('10.0.0.2', 1234),
        'headers': [(b'x-forwarded-for', b'203.0.113.9, 10.0.0.2')],
    }
    assert client_ip(scope, []) == '10.0.0.2'
    assert client_ip(scope, [ip_network('10.0.0.0/8')]) == '203.0.113.9'
    scope['client'] = ('198.51.100.1', 1)
    assert client_ip(scope, [ip_network('10.0.0.0/8')]) == '198.51.100.1'


# ── signed URLs ─────────────────────────────────────────────────────────


def _signed(store, device_id, path='/api/v1/tracks/t1/stream', **kw):
    url = store.signer.sign_url(
        path,
        [('format', 'opus'), ('bitrate', '160')],
        device_id=device_id,
        **kw,
    )
    parts = urlsplit(url)
    return parts.path, parts.query


def test_signed_url_round_trip(tmp_path):
    store = _store(tmp_path)
    device, _token = store.create_device('Cast', user_id=1)
    path, query = _signed(store, device['id'])

    assert store.signer.verify_signed('GET', path, query) == device['id']
    assert store.signer.verify_signed('HEAD', path, query) == device['id']
    assert store.signer.verify_signed('POST', path, query) is None


@pytest.mark.parametrize(
    'tamper',
    [
        lambda p, q: (p.replace('t1', 't2'), q),
        lambda p, q: (p, q.replace('bitrate=160', 'bitrate=320')),
        lambda p, q: (p, q + '&extra=1'),
        lambda p, q: (p, re.sub(r'sig=[^&]+', 'sig=AAAA', q)),
        lambda p, q: (p, re.sub(r'exp=\d+', 'exp=9999999999', q)),
    ],
)
def test_signature_tampering_fails(tmp_path, tamper):
    store = _store(tmp_path)
    device, _token = store.create_device('Cast', user_id=1)
    path, query = tamper(*_signed(store, device['id']))

    assert store.signer.verify_signed('GET', path, query) is None


def test_an_expired_signed_url_fails(tmp_path):
    store = _store(tmp_path)
    device, _token = store.create_device('Cast', user_id=1)
    path, query = _signed(store, device['id'], ttl=1)
    query = re.sub(r'exp=\d+', f'exp={int(time.time()) - 5}', query)
    assert store.signer.verify_signed('GET', path, query) is None


def test_a_revoked_device_voids_its_signed_urls(tmp_path):
    store = _store(tmp_path)
    device, _token = store.create_device('Cast', user_id=1)
    path, query = _signed(store, device['id'])
    store.revoke_device(device['id'])
    assert store.signer.verify_signed('GET', path, query) is None


def test_the_signing_key_is_private_and_kept(tmp_path):
    store = _store(tmp_path)
    device, _token = store.create_device('Cast', user_id=1)
    path, query = _signed(store, device['id'])

    assert (tmp_path / '.secret').stat().st_mode & 0o077 == 0
    reopened = _store(tmp_path)
    assert reopened.signer.verify_signed('GET', path, query) == device['id']


# ── route classification ────────────────────────────────────────────────


@pytest.mark.parametrize(
    ('method', 'path', 'scope'),
    [
        ('GET', '/', PUBLIC),
        ('GET', '/library/albums', PUBLIC),
        ('GET', '/assets/index.js', PUBLIC),
        ('GET', '/api/server/info', PUBLIC),
        ('POST', '/api/auth/pair', PUBLIC),
        ('POST', '/api/auth/pairing', USER),
        ('GET', '/api/auth/devices', USER),
        ('DELETE', '/api/auth/devices/abc', USER),
        ('POST', '/api/auth/revoke-all', ADMIN),
        ('POST', '/api/auth/ws-ticket', CLIENT),
        ('GET', '/api/me', CLIENT),
        ('PUT', '/api/me/password', USER),
        ('PUT', '/api/me/preferences', USER),
        ('GET', '/api/users', ADMIN),
        ('DELETE', '/api/users/3', ADMIN),
        ('GET', '/api/activity', ADMIN),
        ('GET', '/api/activity/now', ADMIN),
        ('POST', '/api/activity/playback', CLIENT),
        ('GET', '/api/settings', ADMIN),
        ('POST', '/api/cookies', ADMIN),
        ('DELETE', '/delete', ADMIN),
        ('GET', '/openapi.json', ADMIN),
        ('GET', '/tracks', CLIENT),
        ('GET', '/downloads/Artist - Song.mp3', CLIENT),
        ('GET', '/media/slskd/x.flac', CLIENT),
        ('POST', '/api/download/url', CLIENT),
        ('GET', '/api/discover/chart', CLIENT),
        ('POST', '/api/discover/collections/deezer', CLIENT),
        ('POST', '/api/discover/collections/spotify', CLIENT),
        ('POST', '/api/discover/collections/other', ADMIN),
        ('GET', '/api/finder/search', CLIENT),
        ('GET', '/api/finder/albums/track_counts', CLIENT),
        ('GET', '/api/finder/artist/songs', CLIENT),
        ('POST', '/api/finder/search', ADMIN),
        ('PUT', '/api/likes', CLIENT),
        ('PUT', '/api/podcasts/episodes/12/playback', CLIENT),
        ('DELETE', '/api/podcasts/episodes/12', ADMIN),
        ('POST', '/api/monitor/playlists', ADMIN),
        ('GET', '/api/v1/library', CLIENT),
        ('GET', '/api/something-new', ADMIN),
    ],
)
def test_classify(method, path, scope):
    assert classify(method, path) == scope


def test_scopes_are_ranked():
    assert allows(ADMIN, USER)
    assert allows(USER, CLIENT)
    assert not allows(USER, ADMIN)
    assert not allows(CLIENT, USER)
    assert allows(CLIENT, PUBLIC)


@pytest.fixture
def app(tmp_path, monkeypatch):
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', tmp_path / 'downloads')
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    # build_app sets these on the shared state; put them back afterwards.
    for name in ('auth', 'activity', 'identity', 'downloader', 'settings'):
        monkeypatch.setattr(api.state, name, getattr(api.state, name))
    return main.build_app()


def _all_routes(app: FastAPI):
    # FastAPI keeps an included router's routes on the router itself.
    yield from app.routes
    yield from api.router.routes
    yield from auth_routes.router.routes
    yield from account_routes.router.routes
    yield from mobile_routes.router.routes


def _templates(app: FastAPI):
    for route in _all_routes(app):
        if isinstance(route, (APIRoute, Route)):
            for method in route.methods or ():
                yield method, route.path
        elif isinstance(route, APIWebSocketRoute):
            yield 'GET', route.path
        elif isinstance(route, Mount) and route.path:
            yield 'GET', route.path + '/x'


def test_every_route_is_classified_on_purpose(app):
    unlisted = []
    for method, template in _templates(app):
        # Fill path parameters with a plausible value.
        path = re.sub(r'\{[^}]+\}', '1', template)
        if method == 'HEAD' or classify(method, path) == PUBLIC:
            continue
        if rule_for(method, path) is None:
            unlisted.append(f'{method} {template}')
    assert unlisted == [], (
        'Add these routes to downtify.auth.RULES (admin if unsure): '
        + ', '.join(unlisted)
    )


# ── the middleware, end to end ──────────────────────────────────────────


@pytest.fixture
def client(app):
    # No `with`: the lifespan (monitor loops, update check) stays off.
    return TestClient(app, base_url='http://testserver')


def _sign_in(client, username='admin', password='downtify'):
    return client.post(
        '/api/auth/login', json={'username': username, 'password': password}
    )


def test_a_new_install_requires_sign_in(client):
    assert client.get('/api/queue').status_code == 401
    assert client.get('/api/server/info').status_code == 200
    assert client.get('/').status_code == 200  # the sign-in page loads
    assert client.get('/downloads/x.mp3').status_code == 401
    status = client.get('/api/auth/status').json()
    assert status['signed_in'] is False
    assert status['notice'] is None  # nothing to announce on a new install


def test_a_revoked_token_is_rejected(client):
    store = api.state.auth
    device, token = store.create_device('Pixel', user_id=1)
    headers = {'Authorization': f'Bearer {token}'}
    assert client.get('/api/queue', headers=headers).status_code == 200
    store.revoke_device(device['id'])
    assert client.get('/api/queue', headers=headers).status_code == 401


def test_a_device_is_a_client_not_an_admin(client):
    store = api.state.auth
    _device, token = store.create_device('Pixel', user_id=1)
    headers = {'Authorization': f'Bearer {token}'}

    assert client.get('/api/queue', headers=headers).status_code == 200
    assert client.get('/api/settings', headers=headers).status_code == 403
    assert client.get('/api/auth/devices', headers=headers).status_code == 403
    me = client.get('/api/me', headers=headers).json()
    assert me['user']['username'] == 'admin'


def test_login_with_the_default_admin(client):
    wrong = _sign_in(client, password='nope nope')
    assert wrong.status_code == 401
    unknown = _sign_in(client, username='nobody')
    assert unknown.status_code == 401
    ok = _sign_in(client)
    assert ok.status_code == 200
    assert ok.json()['user']['default_password'] is True
    cookie = ok.cookies.get(SESSION_COOKIE) or client.cookies.get(
        SESSION_COOKIE
    )
    assert cookie
    assert 'httponly' in ok.headers['set-cookie'].lower()
    assert 'samesite=lax' in ok.headers['set-cookie'].lower()
    assert client.get('/api/settings').status_code == 200
    status = client.get('/api/auth/status').json()
    assert status['via'] == 'session'
    assert status['user']['role'] == 'admin'
    client.post('/api/auth/logout')
    client.cookies.clear()
    assert client.get('/api/settings').status_code == 401


def test_usernames_are_case_insensitive_at_sign_in(client):
    assert _sign_in(client, username='ADMIN').status_code == 200


def test_a_normal_user_is_not_an_admin(client):
    api.state.auth.users.create('maria', PASSWORD)
    assert _sign_in(client, 'maria', PASSWORD).status_code == 200

    assert client.get('/api/queue').status_code == 200
    # Allowed (the like store isn't open without the lifespan).
    assert client.put(
        '/api/likes', json={'file': 'x.mp3', 'liked': False}
    ).status_code not in {401, 403}
    refused = client.get('/api/settings')
    assert refused.status_code == 403
    assert refused.json()['detail'] == 'This needs an admin'
    assert client.get('/api/users').status_code == 403
    assert client.get('/api/activity').status_code == 403
    assert client.delete('/delete', params={'file': 'x'}).status_code == 403
    assert client.get('/api/auth/devices').status_code == 200
    assert client.get('/api/me').json()['user']['role'] == 'user'


def test_a_cross_site_request_with_the_session_is_refused(client):
    _sign_in(client)

    evil = client.put(
        '/api/likes',
        json={'file': 'x.mp3', 'liked': False},
        headers={'Origin': 'https://evil.example'},
    )
    assert evil.status_code == 403
    same = client.get('/api/queue', headers={'Origin': 'https://evil.example'})
    assert same.status_code == 200  # reads aren't refused


def test_login_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(api.state, 'login_limiter', RateLimiter(limit=3))
    for _ in range(3):
        assert _sign_in(client, password='x').status_code == 401
    blocked = _sign_in(client)
    assert blocked.status_code == 429
    assert int(blocked.headers['retry-after']) > 0


def test_pairing_end_to_end(client, monkeypatch):
    monkeypatch.setattr(api.state, 'pairing', PairingStore())
    api.state.auth.users.create('maria', PASSWORD)
    _sign_in(client, 'maria', PASSWORD)
    started = client.post('/api/auth/pairing').json()

    paired = client.post(
        '/api/auth/pair',
        json={
            'code': started['code'],
            'device_name': 'Pixel 8',
            'platform': 'android',
        },
    )
    assert paired.status_code == 200
    body = paired.json()
    assert body['token'].startswith('dtfy_')
    assert body['device']['name'] == 'Pixel 8'
    assert body['server']['server_id'] == api.state.identity.server_id
    assert body['user'] == {'username': 'maria', 'role': 'user'}
    assert (
        client.get(f'/api/auth/pairing/{started["pairing_id"]}').json()[
            'status'
        ]
        == 'paired'
    )
    again = client.post('/api/auth/pair', json={'code': started['code']})
    assert again.status_code == 401
    status = client.get(
        '/api/auth/status',
        headers={'Authorization': f'Bearer {body["token"]}'},
    ).json()
    assert status['via'] == 'device'
    assert status['device']['name'] == 'Pixel 8'
    assert status['user']['username'] == 'maria'
    # The device is Maria's: hers to see, and the admin sees it too.
    assert [d['name'] for d in client.get('/api/auth/devices').json()] == [
        'Pixel 8'
    ]


def test_users_manage_only_their_own_devices(client):
    store = api.state.auth
    store.users.create('maria', PASSWORD)
    admin_device, _t = store.create_device('Admin phone', user_id=1)
    _sign_in(client, 'maria', PASSWORD)

    assert client.get('/api/auth/devices').json() == []
    gone = client.delete(f'/api/auth/devices/{admin_device["id"]}')
    assert gone.status_code == 404
    assert store.device_active(admin_device['id'])


def test_pairing_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(api.state, 'pair_limiter', RateLimiter(limit=2))
    for _ in range(2):
        assert (
            client.post(
                '/api/auth/pair', json={'code': 'AAAA-AAAA'}
            ).status_code
            == 401
        )
    assert (
        client.post('/api/auth/pair', json={'code': 'AAAA-AAAA'}).status_code
        == 429
    )


def test_signed_url_through_the_middleware(client):
    store = api.state.auth
    device, _token = store.create_device('Cast', user_id=1)
    url = store.signer.sign_url('/api/queue', device_id=device['id'])

    assert client.get(url).status_code == 200
    tampered = url.replace('kid=', 'kid=x')
    assert client.get(tampered).status_code == 401


def test_websocket_needs_credentials(client):
    store = api.state.auth
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect('/api/ws?client_id=a'),
    ):
        pass
    device, token = store.create_device('Pixel', user_id=1)
    with client.websocket_connect(
        '/api/ws?client_id=b', headers={'Authorization': f'Bearer {token}'}
    ):
        pass
    ticket = api.state.ws_tickets.create(
        Principal('device', CLIENT, device['id'], 1, 'admin', 'admin')
    )
    with client.websocket_connect(f'/api/ws?client_id=c&ticket={ticket}'):
        pass


def test_server_info_is_public_and_says_little(client):
    info = client.get('/api/server/info').json()
    assert set(info) == {
        'server_id',
        'name',
        'product',
        'version',
        'api_version',
        'require_sign_in',
        'capabilities',
    }
    assert info['api_version'] == 1
    assert info['require_sign_in'] is True


def test_renaming_the_server(client):
    _sign_in(client)
    renamed = client.patch('/api/server', json={'name': '  Living   room '})
    assert renamed.json()['name'] == 'Living room'
    assert client.patch('/api/server', json={'name': '   '}).status_code == 400
    assert ServerIdentity(main.DATABASE_DIR).name == 'Living room'


def test_server_id_is_stable(tmp_path):
    first = ServerIdentity(tmp_path)
    assert ServerIdentity(tmp_path).server_id == first.server_id
    assert len(first.server_id) == 32


def test_auth_routes_are_served(client):
    assert client.get('/api/auth/status').status_code == 200
    assert client.post('/api/auth/pair', json={}).status_code == 401


@pytest.mark.parametrize(
    ('method', 'path', 'scope'),
    [
        ('POST', '/api/podcasts/resolve', CLIENT),
        ('POST', '/api/podcasts/episodes/3/download', CLIENT),
        ('POST', '/api/podcasts/subscribe', ADMIN),
        ('POST', '/api/artists/art/bulk', CLIENT),
        ('POST', '/api/artists/profile/ensure', CLIENT),
        ('POST', '/api/artists/art/upload', ADMIN),
        ('PUT', '/api/artists/profile/bio', ADMIN),
        ('DELETE', '/api/queue/item', ADMIN),
        ('GET', '/api/queue', CLIENT),
    ],
)
def test_client_exceptions_win_over_admin_blocks(method, path, scope):
    assert classify(method, path) == scope
