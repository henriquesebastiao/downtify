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
from .users import MIN_PASSWORD_LENGTH, ROLE_ADMIN

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


def _me(request: Request) -> Principal:
    """The signed-in user making *request* (the middleware made sure
    there is one)."""

    principal = _principal(request)
    if principal is None or not principal.user_id:
        raise HTTPException(status_code=401, detail='Sign in required')
    return principal


def _own_device(request: Request, device_id: str) -> dict[str, Any]:
    """*device_id*, when the user may manage it (theirs, or anyone's for
    an admin); else 404."""

    me = _me(request)
    device = _store().get_device(device_id)
    if (
        device is None
        or device.get('revoked_at')
        or (not me.is_admin and int(device['user_id']) != me.user_id)
    ):
        raise HTTPException(status_code=404, detail='Device not found')
    return device


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
        require_sign_in=True,
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
    """Who this request is signed in as.

    ``signed_in`` is what the web app checks before showing the sign-in
    page; ``via`` is ``session`` (a browser), ``device`` (a paired app) or
    ``null``; ``user`` is ``{id, username, role, default_password}``.
    ``notice`` (only while signed out) is the one-time "accounts are
    here" message for a server upgraded from a version without them:
    ``{username, password}`` - ``password`` is ``null`` when the old
    sign-in password was kept.
    """

    store = _store()
    principal, _bad = identify(request.scope, store, _ip(request))
    device = None
    user = None
    if principal is not None:
        user = store.users.get(principal.user_id)
        if principal.kind == 'device':
            found = store.get_device(principal.device_id)
            device = {
                'id': principal.device_id,
                'name': (found or {}).get('name'),
            }
    return {
        'require_sign_in': True,
        'min_password_length': MIN_PASSWORD_LENGTH,
        'signed_in': principal is not None,
        'via': principal.kind if principal else None,
        'user': user,
        'device': device,
        'notice': None if principal else store.users.notice(),
    }


@router.post('/api/auth/login')
async def login(request: Request, response: Response) -> dict[str, Any]:
    """Sign a browser in: ``{username, password}`` -> ``{signed_in,
    user}``. Rate-limited per address."""

    store = _store()
    ip = _ip(request)
    wait = api.state.login_limiter.retry_after(ip)
    if wait:
        raise _too_many(wait)
    payload = await _json(request)
    username = str(payload.get('username') or '').strip()[:64]
    password = str(payload.get('password') or '')
    user = await asyncio.to_thread(
        store.users.authenticate, username, password
    )
    log = api.state.activity
    if user is None:
        api.state.login_limiter.fail(ip)
        logger.warning('Sign-in: wrong username or password from {}', ip)
        if log is not None:
            await asyncio.to_thread(
                log.record,
                'login_failed',
                username=username,
                summary=username,
                client=api.client_label(request, None),
                ip=ip,
            )
        raise HTTPException(
            status_code=401, detail='Wrong username or password'
        )
    api.state.login_limiter.reset(ip)
    token = await asyncio.to_thread(
        store.create_session,
        user['id'],
        ip,
        request.headers.get('user-agent', ''),
    )
    await asyncio.to_thread(store.users.record_login, user['id'], ip)
    if user['role'] == ROLE_ADMIN:
        # An admin has seen the server with accounts: the notice is done.
        await asyncio.to_thread(store.users.clear_notice)
    if log is not None:
        await asyncio.to_thread(
            log.record,
            'login',
            user_id=user['id'],
            username=user['username'],
            client=api.client_label(request, None),
            ip=ip,
        )
    _set_session(response, request, token)
    return {'signed_in': True, 'user': user}


@router.post('/api/auth/logout')
async def logout(request: Request, response: Response) -> dict[str, Any]:
    """End this browser's session (a no-op for one that has none)."""

    token = session_cookie(request.scope)
    store = api.state.auth
    if token and store is not None:
        user = await asyncio.to_thread(store.session_user, token)
        await asyncio.to_thread(store.end_session, token)
        log = api.state.activity
        if user is not None and log is not None:
            await asyncio.to_thread(
                log.record,
                'logout',
                user_id=user['id'],
                username=user['username'],
                client=api.client_label(request, None),
                ip=_ip(request),
            )
    response.delete_cookie(SESSION_COOKIE, path='/')
    return {'signed_in': False}


# ── Paired devices ──────────────────────────────────────────────────────


@router.get('/api/auth/devices')
def list_devices(request: Request) -> list[dict[str, Any]]:
    """The user's paired devices - everyone's for an admin (each with
    ``user_id`` and ``username``)."""

    me = _me(request)
    return _store().list_devices(None if me.is_admin else me.user_id)


@router.patch('/api/auth/devices/{device_id}')
async def rename_device(device_id: str, request: Request) -> dict[str, Any]:
    store = _store()
    _own_device(request, device_id)
    payload = await _json(request)
    if not await asyncio.to_thread(
        store.rename_device, device_id, str(payload.get('name') or '')
    ):
        raise HTTPException(status_code=404, detail='Device not found')
    return store.get_device(device_id) or {}


@router.delete('/api/auth/devices/{device_id}')
async def revoke_device(device_id: str, request: Request) -> dict[str, Any]:
    """Unpair a device: its token and signed URLs stop working and its
    WebSocket is closed."""

    store = _store()
    device = _own_device(request, device_id)
    if not await asyncio.to_thread(store.revoke_device, device_id):
        raise HTTPException(status_code=404, detail='Device not found')
    await api.state.connections.close_device(device_id)
    await api.log_activity(
        request,
        'device_unpaired',
        str(device.get('name') or device_id),
        {'device_id': device_id, 'owner': device.get('username')},
    )
    logger.info('Unpaired device {}', device_id)
    return {'id': device_id, 'revoked': True}


@router.post('/api/auth/revoke-all')
async def revoke_all(response: Response) -> dict[str, Any]:
    """Sign out everything: every user's devices and browsers (this one
    too) and every signed URL. Admins only."""

    await asyncio.to_thread(_store().revoke_everything)
    await api.state.connections.close_device('')
    for user in await asyncio.to_thread(_store().users.list):
        await api.state.connections.close_user(user['id'])
    response.delete_cookie(SESSION_COOKIE, path='/')
    logger.warning('Signed out every device and browser')
    return {'revoked': True}


# ── Pairing ─────────────────────────────────────────────────────────────


def _own_pairing(request: Request, pairing_id: str) -> None:
    me = _me(request)
    owner = api.state.pairing.owner(pairing_id)
    if owner is not None and owner != me.user_id and not me.is_admin:
        raise HTTPException(status_code=404, detail='Pairing not found')


@router.post('/api/auth/pairing')
def start_pairing(request: Request) -> dict[str, Any]:
    """Start pairing an app to the signed-in user's account:
    ``{pairing_id, code, expires_in}``. The page shows the code (and a
    QR code carrying it) and follows the pairing with
    ``GET /api/auth/pairing/{pairing_id}`` or the ``device_paired``
    WebSocket message."""

    _store()
    return api.state.pairing.create(_me(request).user_id)


@router.get('/api/auth/pairing/{pairing_id}')
def pairing_status(pairing_id: str, request: Request) -> dict[str, Any]:
    _own_pairing(request, pairing_id)
    return api.state.pairing.status(pairing_id)


@router.delete('/api/auth/pairing/{pairing_id}')
def cancel_pairing(pairing_id: str, request: Request) -> dict[str, Any]:
    _own_pairing(request, pairing_id)
    api.state.pairing.cancel(pairing_id)
    return {'cancelled': True}


@router.post('/api/auth/pair')
async def pair(request: Request) -> dict[str, Any]:
    """An app trades a pairing code for its device token:
    ``{code, device_name, platform}`` -> ``{token, device, server,
    user}``. The device belongs to the user who showed the code.

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
    owner = (
        api.state.pairing.owner(pairing_id) if pairing_id is not None else None
    )
    user = store.users.get(owner) if owner else None
    if pairing_id is None or user is None:
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
        user['id'],
    )
    api.state.pairing.complete(pairing_id, device)
    await api.state.connections.send_user(
        user['id'],
        {'type': 'device_paired', 'pairing_id': pairing_id, 'device': device},
    )
    log = api.state.activity
    if log is not None:
        await asyncio.to_thread(
            log.record,
            'device_paired',
            user_id=user['id'],
            username=user['username'],
            summary=str(device.get('name') or ''),
            detail={'device_id': device.get('id')},
            client=str(device.get('name') or ''),
            ip=ip,
        )
    logger.info('Paired device {} ({})', device.get('name'), device.get('id'))
    identity = api.state.identity
    return {
        'token': token,
        'device': {'id': device.get('id'), 'name': device.get('name')},
        'server': {
            'server_id': identity.server_id if identity else '',
            'name': identity.name if identity else '',
        },
        'user': {'username': user['username'], 'role': user['role']},
    }


@router.post('/api/auth/ws-ticket')
def ws_ticket(request: Request) -> dict[str, Any]:
    """A single-use ticket (60 s) for opening the WebSocket as
    ``/api/ws?client_id=…&ticket=…``, for a client that can't send an
    ``Authorization`` header with the handshake."""

    return {'ticket': api.state.ws_tickets.create(_me(request))}
