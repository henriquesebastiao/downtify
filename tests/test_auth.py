"""Sign-in, paired devices, pairing codes, signed URLs and the middleware
that enforces them (downtify/auth.py, downtify/auth_routes.py)."""

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
from downtify import api, auth_routes, mobile_routes
from downtify.auth import (
    ADMIN,
    CLIENT,
    PUBLIC,
    SESSION_COOKIE,
    AuthStore,
    PairingStore,
    Principal,
    RateLimiter,
    TicketStore,
    classify,
    client_ip,
    hash_password,
    normalize_pairing_code,
    rule_for,
    verify_password,
)
from downtify.server_identity import ServerIdentity

PASSWORD = 'correct horse battery'


def _store(tmp_path: Path, **kw: Any) -> AuthStore:
    return AuthStore(tmp_path / 'auth.db', tmp_path / '.secret', **kw)


# ── passwords ───────────────────────────────────────────────────────────


def test_password_hash_round_trip_and_salt():
    first = hash_password(PASSWORD)
    second = hash_password(PASSWORD)

    assert first != second  # salted
    assert first.startswith('scrypt$')
    assert verify_password(PASSWORD, first)
    assert not verify_password('wrong password', first)
    assert not verify_password(PASSWORD, 'garbage')


def test_password_rules(tmp_path):
    store = _store(tmp_path)
    assert not store.has_password()
    assert not store.check_password('')
    with pytest.raises(ValueError, match='at least'):
        store.set_password('short')
    store.set_password(PASSWORD)
    assert store.check_password(PASSWORD)
    assert not store.check_password(PASSWORD + '!')


# ── require sign-in ─────────────────────────────────────────────────────


def test_require_sign_in_is_off_by_default_and_needs_a_password(tmp_path):
    store = _store(tmp_path)
    assert store.require_sign_in is False
    with pytest.raises(ValueError, match='password'):
        store.set_require_sign_in(True)
    store.set_password(PASSWORD)
    store.set_require_sign_in(True)
    assert _store(tmp_path).require_sign_in is True  # persisted


def test_the_environment_pins_require_sign_in(tmp_path):
    store = _store(tmp_path, forced_require=True)
    assert store.require_sign_in is True
    assert store.forced_by_env
    with pytest.raises(ValueError, match='DOWNTIFY_REQUIRE_SIGN_IN'):
        store.set_require_sign_in(False)


def test_reset_clears_password_and_sessions_but_keeps_devices(tmp_path):
    store = _store(tmp_path)
    store.set_password(PASSWORD)
    store.set_require_sign_in(True)
    session = store.create_session()
    device, token = store.create_device('Pixel')

    store.reset()

    assert not store.require_sign_in
    assert not store.has_password()
    assert not store.session_valid(session)
    assert store.verify_device_token(token)['id'] == device['id']


# ── sessions ────────────────────────────────────────────────────────────


def test_sessions(tmp_path):
    store = _store(tmp_path)
    token = store.create_session('1.2.3.4', 'Firefox')

    assert store.session_valid(token)
    assert not store.session_valid(token + 'x')
    assert not store.session_valid('')
    store.end_session(token)
    assert not store.session_valid(token)


def test_an_expired_session_is_gone(tmp_path):
    store = _store(tmp_path)
    token = store.create_session()
    with store._connect() as conn:
        conn.execute(
            "UPDATE auth_sessions SET expires_at = '2000-01-01T00:00:00+00:00'"
        )
    assert not store.session_valid(token)


# ── devices ─────────────────────────────────────────────────────────────


def test_device_token_round_trip(tmp_path):
    store = _store(tmp_path)
    device, token = store.create_device('  Pixel   8 ', 'android', '10.0.0.5')

    assert re.fullmatch(r'dtfy_[a-z2-9]{12}_[A-Za-z0-9_-]{43}', token)
    assert device['name'] == 'Pixel 8'
    assert store.verify_device_token(token, '10.0.0.6') == {
        'id': device['id'],
        'name': 'Pixel 8',
    }
    # Only a hash is stored.
    with store._connect() as conn:
        stored = conn.execute('SELECT token_hash FROM auth_devices').fetchone()
    assert token.split('_')[-1] not in stored['token_hash']


def test_a_revoked_token_fails(tmp_path):
    store = _store(tmp_path)
    device, token = store.create_device('Pixel')

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
    _device, token = store.create_device('Pixel')
    forged = token[:-4] + ('AAAA' if not token.endswith('AAAA') else 'BBBB')
    assert store.verify_device_token(forged) is None


def test_revoke_everything(tmp_path):
    store = _store(tmp_path)
    device, token = store.create_device('Pixel')
    session = store.create_session()
    url = store.signer.sign_url('/cover', device_id=device['id'])

    store.revoke_everything()

    assert store.verify_device_token(token) is None
    assert not store.session_valid(session)
    path, query = url.split('?')
    assert store.signer.verify_signed('GET', path, query) is None


# ── pairing ─────────────────────────────────────────────────────────────


def test_pairing_code_is_single_use():
    pairing = PairingStore()
    started = pairing.create()

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
    principal = Principal('device', CLIENT, 'abc')
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
    device, _token = store.create_device('Cast')
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
    device, _token = store.create_device('Cast')
    path, query = tamper(*_signed(store, device['id']))

    assert store.signer.verify_signed('GET', path, query) is None


def test_an_expired_signed_url_fails(tmp_path):
    store = _store(tmp_path)
    device, _token = store.create_device('Cast')
    path, query = _signed(store, device['id'], ttl=1)
    query = re.sub(r'exp=\d+', f'exp={int(time.time()) - 5}', query)
    assert store.signer.verify_signed('GET', path, query) is None


def test_a_revoked_device_voids_its_signed_urls(tmp_path):
    store = _store(tmp_path)
    device, _token = store.create_device('Cast')
    path, query = _signed(store, device['id'])
    store.revoke_device(device['id'])
    assert store.signer.verify_signed('GET', path, query) is None


def test_the_signing_key_is_private_and_kept(tmp_path):
    store = _store(tmp_path)
    device, _token = store.create_device('Cast')
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
        ('POST', '/api/auth/pairing', ADMIN),
        ('GET', '/api/auth/devices', ADMIN),
        ('GET', '/api/settings', ADMIN),
        ('POST', '/api/cookies', ADMIN),
        ('DELETE', '/delete', ADMIN),
        ('GET', '/openapi.json', ADMIN),
        ('GET', '/tracks', CLIENT),
        ('GET', '/downloads/Artist - Song.mp3', CLIENT),
        ('GET', '/media/slskd/x.flac', CLIENT),
        ('POST', '/api/download/url', CLIENT),
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


@pytest.fixture
def app(tmp_path, monkeypatch):
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', tmp_path / 'downloads')
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    # build_app sets these on the shared state; put them back afterwards.
    for name in ('auth', 'identity', 'downloader', 'settings'):
        monkeypatch.setattr(api.state, name, getattr(api.state, name))
    return main.build_app()


def _all_routes(app: FastAPI):
    # FastAPI keeps an included router's routes on the router itself.
    yield from app.routes
    yield from api.router.routes
    yield from auth_routes.router.routes
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


def _enable_sign_in(store: AuthStore) -> None:
    store.set_password(PASSWORD)
    store.set_require_sign_in(True)


def test_off_keeps_current_behaviour(client):
    assert client.get('/api/queue').status_code == 200
    assert client.get('/api/settings').status_code == 200
    assert client.get('/').status_code == 200


def test_off_still_rejects_a_revoked_token(client):
    store = api.state.auth
    device, token = store.create_device('Pixel')
    headers = {'Authorization': f'Bearer {token}'}
    assert client.get('/api/queue', headers=headers).status_code == 200
    store.revoke_device(device['id'])
    assert client.get('/api/queue', headers=headers).status_code == 401


def test_on_requires_credentials(client):
    _enable_sign_in(api.state.auth)

    assert client.get('/api/queue').status_code == 401
    assert client.get('/api/server/info').status_code == 200
    assert client.get('/').status_code == 200  # the sign-in page loads
    assert client.get('/downloads/x.mp3').status_code == 401


def test_on_a_device_is_a_client_not_an_admin(client):
    store = api.state.auth
    _enable_sign_in(store)
    _device, token = store.create_device('Pixel')
    headers = {'Authorization': f'Bearer {token}'}

    assert client.get('/api/queue', headers=headers).status_code == 200
    assert client.get('/api/settings', headers=headers).status_code == 403
    assert client.get('/api/auth/devices', headers=headers).status_code == 403


def test_login_sets_an_admin_session(client):
    _enable_sign_in(api.state.auth)

    wrong = client.post('/api/auth/login', json={'password': 'nope nope'})
    assert wrong.status_code == 401
    ok = client.post('/api/auth/login', json={'password': PASSWORD})
    assert ok.status_code == 200
    cookie = ok.cookies.get(SESSION_COOKIE) or client.cookies.get(
        SESSION_COOKIE
    )
    assert cookie
    assert 'httponly' in ok.headers['set-cookie'].lower()
    assert 'samesite=lax' in ok.headers['set-cookie'].lower()
    assert client.get('/api/settings').status_code == 200
    assert client.get('/api/auth/status').json()['via'] == 'session'
    client.post('/api/auth/logout')
    client.cookies.clear()
    assert client.get('/api/settings').status_code == 401


def test_a_cross_site_request_with_the_session_is_refused(client):
    _enable_sign_in(api.state.auth)
    client.post('/api/auth/login', json={'password': PASSWORD})

    evil = client.put(
        '/api/likes',
        json={'file': 'x.mp3', 'liked': False},
        headers={'Origin': 'https://evil.example'},
    )
    assert evil.status_code == 403
    same = client.get('/api/queue', headers={'Origin': 'https://evil.example'})
    assert same.status_code == 200  # reads aren't refused


def test_login_is_rate_limited(client, monkeypatch):
    _enable_sign_in(api.state.auth)
    monkeypatch.setattr(api.state, 'login_limiter', RateLimiter(limit=3))
    for _ in range(3):
        assert (
            client.post('/api/auth/login', json={'password': 'x'}).status_code
            == 401
        )
    blocked = client.post('/api/auth/login', json={'password': PASSWORD})
    assert blocked.status_code == 429
    assert int(blocked.headers['retry-after']) > 0


def test_pairing_end_to_end(client, monkeypatch):
    monkeypatch.setattr(api.state, 'pairing', PairingStore())
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


def test_enabling_sign_in_needs_the_password_and_signs_this_browser_in(client):
    store = api.state.auth
    client.put('/api/auth/password', json={'new_password': PASSWORD})

    refused = client.put(
        '/api/auth/require', json={'enabled': True, 'password': 'x'}
    )
    assert refused.status_code == 403
    ok = client.put(
        '/api/auth/require', json={'enabled': True, 'password': PASSWORD}
    )
    assert ok.status_code == 200
    assert store.require_sign_in
    assert client.get('/api/settings').status_code == 200  # still signed in


def test_changing_the_password_needs_the_current_one(client):
    client.put('/api/auth/password', json={'new_password': PASSWORD})
    bad = client.put(
        '/api/auth/password',
        json={'current_password': 'nope nope', 'new_password': 'another one!'},
    )
    assert bad.status_code == 403
    good = client.put(
        '/api/auth/password',
        json={'current_password': PASSWORD, 'new_password': 'another one!'},
    )
    assert good.status_code == 200


def test_signed_url_through_the_middleware(client):
    store = api.state.auth
    _enable_sign_in(store)
    device, _token = store.create_device('Cast')
    url = store.signer.sign_url('/api/queue', device_id=device['id'])

    assert client.get(url).status_code == 200
    tampered = url.replace('kid=', 'kid=x')
    assert client.get(tampered).status_code == 401


def test_websocket_needs_credentials_when_required(client):
    store = api.state.auth
    _enable_sign_in(store)
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect('/api/ws?client_id=a'),
    ):
        pass
    device, token = store.create_device('Pixel')
    with client.websocket_connect(
        '/api/ws?client_id=b', headers={'Authorization': f'Bearer {token}'}
    ):
        pass
    ticket = api.state.ws_tickets.create(
        Principal('device', CLIENT, device['id'])
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
    assert info['require_sign_in'] is False


def test_renaming_the_server(client):
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
