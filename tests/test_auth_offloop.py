"""Credential checks never block the event loop.

The auth middleware checks every request's session or device token. A
sign-in cache hit is answered in place; a miss reads the database on a
worker thread (``asyncio.to_thread``), so a slow database cannot stall
the other requests on the loop.
"""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from downtify import api, auth_routes
from downtify.auth import (
    CLIENT,
    MISS,
    SESSION_COOKIE,
    USER,
    AuthMiddleware,
    AuthStore,
    identify,
    identify_offloop,
)
from downtify.users import ROLE_ADMIN, ROLE_USER


def _store(tmp_path: Path) -> AuthStore:
    return AuthStore(tmp_path / 'auth.db', tmp_path / '.secret')


def _scope(
    *, token: str = '', session: str = '', ip: str = '127.0.0.1'
) -> dict[str, Any]:
    headers: list[tuple[bytes, bytes]] = []
    if token:
        headers.append((b'authorization', f'Bearer {token}'.encode()))
    if session:
        headers.append((b'cookie', f'{SESSION_COOKIE}={session}'.encode()))
    return {
        'type': 'http',
        'method': 'GET',
        'path': '/api/probe',
        'headers': headers,
        'client': (ip, 1234),
    }


def _summary(result: tuple[Any, bool]) -> tuple[Any, ...]:
    principal, bad_token = result
    if principal is None:
        return (None, bad_token)
    return (
        principal.kind,
        principal.scope,
        principal.device_id,
        principal.user_id,
        principal.username,
        principal.role,
        bad_token,
    )


def _forbid(monkeypatch: pytest.MonkeyPatch, store: AuthStore) -> None:
    def no_db(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('the database was asked')

    monkeypatch.setattr(store, '_connect', no_db)


def _no_thread_hop(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_thread(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('a worker thread was used')

    monkeypatch.setattr(asyncio, 'to_thread', no_thread)


@pytest.fixture
def maria(tmp_path: Path) -> tuple[AuthStore, int]:
    store = _store(tmp_path)
    user = store.users.create('maria', 'password123', role=ROLE_USER)
    return store, int(user['id'])


@pytest.fixture
def boss(tmp_path: Path) -> tuple[AuthStore, int]:
    store = _store(tmp_path)
    user = store.users.create('boss', 'password123', role=ROLE_ADMIN)
    return store, int(user['id'])


# (a) A cache hit: no database, no worker thread.


def test_a_cached_session_is_answered_without_a_thread_or_database(
    maria, monkeypatch
):
    store, uid = maria
    token = store.create_session(uid)
    store.session_user(token)  # warms the sign-in cache

    _forbid(monkeypatch, store)
    _no_thread_hop(monkeypatch)
    principal, bad = asyncio.run(
        identify_offloop(_scope(session=token), store)
    )

    assert principal is not None
    assert principal.user_id == uid
    assert bad is False


def test_a_cached_device_token_is_answered_without_a_thread_or_database(
    maria, monkeypatch
):
    store, uid = maria
    _device, token = store.create_device('Phone', user_id=uid)
    store.verify_device_token(token)  # warms the sign-in cache

    _forbid(monkeypatch, store)
    _no_thread_hop(monkeypatch)
    principal, bad = asyncio.run(identify_offloop(_scope(token=token), store))

    assert principal is not None
    assert principal.kind == 'device'
    assert principal.username == 'maria'
    assert bad is False


def test_peek_never_reads_the_database(maria, monkeypatch):
    store, uid = maria
    _device, token = store.create_device('Phone', user_id=uid)
    _forbid(monkeypatch, store)

    # Malformed tokens are answered as "no" straight away...
    assert store.peek_session('') is None
    assert store.peek_session('x' * 129) is None
    assert store.peek_device('nonsense') is None
    # ...and a well-formed one that isn't cached is a miss.
    assert store.peek_session('abc') is MISS
    assert store.peek_device(token) is MISS


# (b) A miss: the lookup runs on a worker thread; the loop keeps going.


def test_a_cache_miss_is_looked_up_off_the_event_loop(boss, monkeypatch):
    store, uid = boss
    token = store.create_session(uid)
    app = _probe_app(store)

    seen_threads: list[threading.Thread] = []
    real_session_user = store.session_user

    def slow_session_user(value: str) -> Any:
        seen_threads.append(threading.current_thread())
        time.sleep(0.3)  # a slow database
        return real_session_user(value)

    monkeypatch.setattr(store, 'session_user', slow_session_user)

    async def scenario() -> tuple[httpx.Response, int]:
        ticks = 0
        done = asyncio.Event()

        async def ticker() -> None:
            nonlocal ticks
            while not done.is_set():
                ticks += 1
                await asyncio.sleep(0.02)

        ticker_task = asyncio.create_task(ticker())
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url='http://testserver'
        ) as client:
            response = await client.get(
                '/api/probe',
                headers={'cookie': f'{SESSION_COOKIE}={token}'},
            )
        done.set()
        await ticker_task
        return response, ticks

    response, ticks = asyncio.run(scenario())

    assert response.status_code == 200
    assert response.json() == {'user': uid, 'kind': 'session'}
    assert len(seen_threads) == 1
    assert seen_threads[0] is not threading.main_thread()
    # The loop ticked about every 20 ms during the 300 ms lookup; a
    # blocking lookup would have let it tick once or twice.
    assert ticks >= 5


def _probe_app(store: AuthStore) -> Starlette:
    async def probe(request: Request) -> JSONResponse:
        principal = request.scope['state']['principal']
        return JSONResponse({
            'user': principal.user_id,
            'kind': principal.kind,
        })

    app = Starlette(routes=[Route('/api/probe', probe)])
    app.add_middleware(
        AuthMiddleware,
        get_store=lambda: store,
        get_tickets=lambda: None,
        trusted_proxies=[],
    )
    return app


# (c) The same answers as the synchronous path.


def _both(
    store: AuthStore, scope: dict[str, Any]
) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    """The synchronous and the event-loop answers, each from a cold cache
    (so the event-loop one takes the database path)."""

    store._signed_in.clear()
    sync = _summary(identify(scope, store, '127.0.0.1'))
    store._signed_in.clear()
    offloop = _summary(
        asyncio.run(identify_offloop(scope, store, '127.0.0.1'))
    )
    return sync, offloop


def test_a_valid_session_gives_the_same_answer(maria):
    store, uid = maria
    token = store.create_session(uid)

    sync, offloop = _both(store, _scope(session=token))

    assert sync == offloop
    assert sync == ('session', USER, '', uid, 'maria', ROLE_USER, False)


def test_an_expired_session_gives_the_same_answer(maria):
    store, uid = maria
    token = store.create_session(uid)
    with store._connect() as conn:
        conn.execute(
            'UPDATE auth_sessions SET expires_at = ?',
            ('2000-01-01T00:00:00+00:00',),
        )

    sync, offloop = _both(store, _scope(session=token))

    assert sync == offloop == (None, False)


def test_a_bad_token_gives_the_same_answer(maria):
    store, uid = maria
    _device, token = store.create_device('Phone', user_id=uid)
    wrong = token[:-1] + ('y' if token.endswith('x') else 'x')

    sync, offloop = _both(store, _scope(token=wrong))

    assert sync == offloop == (None, True)


def test_a_valid_device_token_gives_the_same_answer(maria):
    store, uid = maria
    device, token = store.create_device('Phone', user_id=uid)

    sync, offloop = _both(store, _scope(token=token))

    assert sync == offloop
    assert sync == (
        'device',
        CLIENT,
        device['id'],
        uid,
        'maria',
        ROLE_USER,
        False,
    )


def test_no_credentials_gives_the_same_answer(maria):
    store, _uid = maria

    sync, offloop = _both(store, _scope())

    assert sync == offloop == (None, False)


# (d) GET /api/auth/status: its database reads run off the loop too.


def _status_app(store: AuthStore, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(api.state, 'auth', store)
    app = FastAPI()
    app.include_router(auth_routes.router)
    return app


def _get_status(app: Any, **headers: str) -> httpx.Response:
    async def call() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url='http://testserver'
        ) as client:
            return await client.get('/api/auth/status', headers=headers)

    return asyncio.run(call())


def test_a_cold_status_lookup_runs_off_the_loop(
    boss, monkeypatch: pytest.MonkeyPatch
):
    store, uid = boss
    token = store.create_session(uid)
    store._signed_in.clear()
    app = _status_app(store, monkeypatch)

    seen_threads: list[threading.Thread] = []
    real_session_user = store.session_user

    def slow_session_user(value: str) -> Any:
        seen_threads.append(threading.current_thread())
        time.sleep(0.3)  # a slow database
        return real_session_user(value)

    monkeypatch.setattr(store, 'session_user', slow_session_user)

    async def scenario() -> tuple[httpx.Response, int]:
        ticks = 0
        done = asyncio.Event()

        async def ticker() -> None:
            nonlocal ticks
            while not done.is_set():
                ticks += 1
                await asyncio.sleep(0.02)

        ticker_task = asyncio.create_task(ticker())
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url='http://testserver'
        ) as client:
            response = await client.get(
                '/api/auth/status',
                headers={'cookie': f'{SESSION_COOKIE}={token}'},
            )
        done.set()
        await ticker_task
        return response, ticks

    response, ticks = asyncio.run(scenario())

    assert response.status_code == 200
    assert response.json()['signed_in'] is True
    assert len(seen_threads) == 1
    assert seen_threads[0] is not threading.main_thread()
    assert ticks >= 5


def test_status_without_credentials_is_unchanged(
    maria, monkeypatch: pytest.MonkeyPatch
):
    store, _uid = maria
    app = _status_app(store, monkeypatch)

    response = _get_status(app)

    assert response.status_code == 200
    body = response.json()
    assert body['signed_in'] is False
    assert body['via'] is None
    assert body['user'] is None
    assert body['device'] is None
    assert body['require_sign_in'] is True
    assert body['auth_disabled'] is False
    assert body['notice'] == store.users.notice()


def test_status_with_a_valid_session_is_unchanged(
    maria, monkeypatch: pytest.MonkeyPatch
):
    store, uid = maria
    token = store.create_session(uid)
    app = _status_app(store, monkeypatch)

    cold = _get_status(app, cookie=f'{SESSION_COOKIE}={token}')
    store._signed_in.clear()
    warm = _get_status(app, cookie=f'{SESSION_COOKIE}={token}')

    assert cold.status_code == warm.status_code == 200
    assert cold.json() == warm.json()
    body = cold.json()
    assert body['signed_in'] is True
    assert body['via'] == 'session'
    assert body['user'] == store.users.get(uid)
    assert body['device'] is None
    assert body['notice'] is None


def test_status_with_a_valid_device_token_is_unchanged(
    maria, monkeypatch: pytest.MonkeyPatch
):
    store, uid = maria
    device, token = store.create_device('Phone', user_id=uid)
    app = _status_app(store, monkeypatch)

    cold = _get_status(app, authorization=f'Bearer {token}')
    store._signed_in.clear()
    warm = _get_status(app, authorization=f'Bearer {token}')

    assert cold.status_code == warm.status_code == 200
    assert cold.json() == warm.json()
    body = cold.json()
    assert body['signed_in'] is True
    assert body['via'] == 'device'
    assert body['user'] == store.users.get(uid)
    assert body['device'] == {'id': device['id'], 'name': 'Phone'}
