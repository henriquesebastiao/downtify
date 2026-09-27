"""HTTP routes for signing in, pairing apps and the server's identity.

The rules for who may call what live in :mod:`downtify.auth`
(:data:`downtify.auth.RULES`); these routes only do the work. Listed in
:mod:`downtify.api`'s module docstring with the rest of the API.
"""

from __future__ import annotations

import asyncio
from ipaddress import ip_address
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from loguru import logger

from . import api
from .auth import (
    MIN_PASSWORD_LENGTH,
    SESSION_COOKIE,
    SESSION_TTL,
    AuthStore,
    Principal,
    client_ip,
    identify,
    session_cookie,
    trusted_proxies_from_env,
)
from .server_identity import server_info

router = APIRouter()

_TRUSTED = trusted_proxies_from_env()


def _store() -> AuthStore:
    if api.state.auth is None:
        raise HTTPException(status_code=500, detail='Sign-in is not ready')
    return api.state.auth


def _ip(request: Request) -> str:
    return client_ip(request.scope, _TRUSTED)


def _principal(request: Request) -> Optional[Principal]:
    return (request.scope.get('state') or {}).get('principal')


def _is_https(request: Request) -> bool:
    if request.url.scheme == 'https':
        return True
    peer = request.client.host if request.client else ''
    forwarded = request.headers.get('x-forwarded-proto', '')
    return bool(
        _TRUSTED
        and forwarded.lower() == 'https'
        and any(_in(peer, net) for net in _TRUSTED)
    )


def _in(address: str, network: Any) -> bool:
    try:
        return ip_address(address) in network
    except ValueError:
        return False


def _set_session(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite='lax',
        secure=_is_https(request),
        path='/',
    )


def _too_many(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail='Too many attempts. Try again later.',
        headers={'Retry-After': str(retry_after)},
    )


async def _json(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


# ── Server identity ─────────────────────────────────────────────────────


@router.get('/api/server/info')
def get_server_info() -> dict[str, Any]:
    """Who this server is and what it can do - public, for an app to
    check an address before it has credentials."""

    identity = api.state.identity
    if identity is None:
        raise HTTPException(status_code=503, detail='Starting up')
    transcoder = getattr(api.state, 'transcoder', None)
    return server_info(
        identity,
        version=api.state.version,
        require_sign_in=bool(
            api.state.auth and api.state.auth.require_sign_in
        ),
        transcoding=transcoder.capability() if transcoder else None,
    )


@router.patch('/api/server')
async def update_server(request: Request) -> dict[str, Any]:
    """Rename the server (``{name}``) - what apps and LAN discovery show."""

    identity = api.state.identity
    if identity is None:
        raise HTTPException(status_code=503, detail='Starting up')
    payload = await _json(request)
    try:
        await asyncio.to_thread(identity.set_name, payload.get('name'))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    announcer = getattr(api.state, 'discovery', None)
    if announcer is not None:
        await announcer.update(identity.name)
    return get_server_info()


# ── Status, sign in and out ─────────────────────────────────────────────


@router.get('/api/auth/status')
def auth_status(request: Request) -> dict[str, Any]:
    """Whether sign-in is required, and who this request is signed in as.

    ``signed_in`` is what the web app checks before showing the sign-in
    page; ``via`` is ``session`` (a browser), ``device`` (a paired app) or
    ``null``.
    """

    store = _store()
    principal, _bad = identify(request.scope, store, _ip(request))
    device = None
    if principal is not None and principal.kind == 'device':
        found = store.get_device(principal.device_id)
        device = {'id': principal.device_id, 'name': (found or {}).get('name')}
    return {
        'require_sign_in': store.require_sign_in,
        'forced_by_env': store.forced_by_env,
        'has_password': store.has_password(),
        'min_password_length': MIN_PASSWORD_LENGTH,
        'signed_in': principal is not None,
        'via': principal.kind if principal else None,
        'device': device,
    }


@router.post('/api/auth/login')
async def login(request: Request, response: Response) -> dict[str, Any]:
    """Sign a browser in with the password (``{password}``)."""

    store = _store()
    ip = _ip(request)
    wait = api.state.login_limiter.retry_after(ip)
    if wait:
        raise _too_many(wait)
    payload = await _json(request)
    password = str(payload.get('password') or '')
    ok = await asyncio.to_thread(store.check_password, password)
    if not ok:
        api.state.login_limiter.fail(ip)
        logger.warning('Sign-in: wrong password from {}', ip)
        raise HTTPException(status_code=401, detail='Wrong password')
    api.state.login_limiter.reset(ip)
    token = await asyncio.to_thread(
        store.create_session, ip, request.headers.get('user-agent', '')
    )
    _set_session(response, request, token)
    return {'signed_in': True}


@router.post('/api/auth/logout')
async def logout(request: Request, response: Response) -> dict[str, Any]:
    """End this browser's session (a no-op for one that has none)."""

    token = session_cookie(request.scope)
    if token and api.state.auth is not None:
        await asyncio.to_thread(api.state.auth.end_session, token)
    response.delete_cookie(SESSION_COOKIE, path='/')
    return {'signed_in': False}


@router.put('/api/auth/password')
async def change_password(request: Request) -> dict[str, Any]:
    """Set or change the web password: ``{new_password,
    current_password}`` (the current one only once a password exists)."""

    store = _store()
    payload = await _json(request)
    if store.has_password():
        ip = _ip(request)
        wait = api.state.login_limiter.retry_after(ip)
        if wait:
            raise _too_many(wait)
        current = str(payload.get('current_password') or '')
        if not await asyncio.to_thread(store.check_password, current):
            api.state.login_limiter.fail(ip)
            raise HTTPException(
                status_code=403, detail='The current password is wrong'
            )
    try:
        await asyncio.to_thread(
            store.set_password, str(payload.get('new_password') or '')
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {'has_password': True}


@router.put('/api/auth/require')
async def set_require_sign_in(
    request: Request, response: Response
) -> dict[str, Any]:
    """Turn "Require sign-in" on (``{enabled: true, password}``) or off.

    Turning it on also signs this browser in, with the password it has
    to send - otherwise the page doing it would lock itself out.
    """

    store = _store()
    payload = await _json(request)
    enabled = bool(payload.get('enabled'))
    token = ''
    if enabled:
        ip = _ip(request)
        wait = api.state.login_limiter.retry_after(ip)
        if wait:
            raise _too_many(wait)
        password = str(payload.get('password') or '')
        if not await asyncio.to_thread(store.check_password, password):
            api.state.login_limiter.fail(ip)
            raise HTTPException(status_code=403, detail='Wrong password')
        token = await asyncio.to_thread(
            store.create_session, ip, request.headers.get('user-agent', '')
        )
    try:
        await asyncio.to_thread(store.set_require_sign_in, enabled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if token:
        _set_session(response, request, token)
    logger.info('Require sign-in turned {}', 'on' if enabled else 'off')
    return {'require_sign_in': store.require_sign_in}


# ── Paired devices ──────────────────────────────────────────────────────


@router.get('/api/auth/devices')
def list_devices() -> list[dict[str, Any]]:
    return _store().list_devices()


@router.patch('/api/auth/devices/{device_id}')
async def rename_device(device_id: str, request: Request) -> dict[str, Any]:
    store = _store()
    payload = await _json(request)
    if not await asyncio.to_thread(
        store.rename_device, device_id, str(payload.get('name') or '')
    ):
        raise HTTPException(status_code=404, detail='Device not found')
    return store.get_device(device_id) or {}


@router.delete('/api/auth/devices/{device_id}')
async def revoke_device(device_id: str) -> dict[str, Any]:
    """Unpair a device: its token and signed URLs stop working and its
    WebSocket is closed."""

    store = _store()
    if not await asyncio.to_thread(store.revoke_device, device_id):
        raise HTTPException(status_code=404, detail='Device not found')
    await api.state.connections.close_device(device_id)
    logger.info('Unpaired device {}', device_id)
    return {'id': device_id, 'revoked': True}


@router.post('/api/auth/revoke-all')
async def revoke_all(response: Response) -> dict[str, Any]:
    """Sign out everything: every device, every browser (this one too)
    and every signed URL."""

    await asyncio.to_thread(_store().revoke_everything)
    await api.state.connections.close_device('')
    response.delete_cookie(SESSION_COOKIE, path='/')
    logger.warning('Signed out every device and browser')
    return {'revoked': True}


# ── Pairing ─────────────────────────────────────────────────────────────


@router.post('/api/auth/pairing')
def start_pairing() -> dict[str, Any]:
    """Start pairing an app: ``{pairing_id, code, expires_in}``. The page
    shows the code (and a QR code carrying it) and follows the pairing
    with ``GET /api/auth/pairing/{pairing_id}`` or the ``device_paired``
    WebSocket message."""

    _store()
    return api.state.pairing.create()


@router.get('/api/auth/pairing/{pairing_id}')
def pairing_status(pairing_id: str) -> dict[str, Any]:
    return api.state.pairing.status(pairing_id)


@router.delete('/api/auth/pairing/{pairing_id}')
def cancel_pairing(pairing_id: str) -> dict[str, Any]:
    api.state.pairing.cancel(pairing_id)
    return {'cancelled': True}


@router.post('/api/auth/pair')
async def pair(request: Request) -> dict[str, Any]:
    """An app trades a pairing code for its device token:
    ``{code, device_name, platform}`` -> ``{token, device, server}``.

    Public and rate-limited per address; a code works once and for five
    minutes. The token is shown here once and never stored.
    """

    store = _store()
    ip = _ip(request)
    wait = api.state.pair_limiter.retry_after(ip)
    if wait:
        raise _too_many(wait)
    payload = await _json(request)
    pairing_id = api.state.pairing.claim(payload.get('code'))
    if pairing_id is None:
        api.state.pair_limiter.fail(ip)
        logger.warning('Pairing: wrong or expired code from {}', ip)
        raise HTTPException(
            status_code=401, detail='Wrong or expired pairing code'
        )
    device, token = await asyncio.to_thread(
        store.create_device,
        str(payload.get('device_name') or ''),
        str(payload.get('platform') or ''),
        ip,
    )
    api.state.pairing.complete(pairing_id, device)
    await api.state.connections.broadcast({
        'type': 'device_paired',
        'pairing_id': pairing_id,
        'device': device,
    })
    logger.info('Paired device {} ({})', device.get('name'), device.get('id'))
    identity = api.state.identity
    return {
        'token': token,
        'device': {'id': device.get('id'), 'name': device.get('name')},
        'server': {
            'server_id': identity.server_id if identity else '',
            'name': identity.name if identity else '',
        },
    }


@router.post('/api/auth/ws-ticket')
def ws_ticket(request: Request) -> dict[str, Any]:
    """A single-use ticket (60 s) for opening the WebSocket as
    ``/api/ws?client_id=…&ticket=…``, for a client that can't send an
    ``Authorization`` header with the handshake."""

    principal = _principal(request)
    if principal is None:
        # Sign-in isn't required: the WebSocket needs no ticket at all.
        raise HTTPException(status_code=400, detail='Not signed in')
    return {'ticket': api.state.ws_tickets.create(principal)}
