"""HTTP routes for accounts: your own, everyone's (admins), and activity.

* ``/api/me...`` - the signed-in user: who they are, their username,
  password, preferences (Settings > General) and signing out everywhere.
* ``/api/users...`` - admins manage every account.
* ``/api/activity...`` - admins read the activity log and see what is
  playing; every player reports what it plays to
  ``POST /api/activity/playback``.

Who may call what is in :data:`downtify.auth.RULES`; the routes here
only check *whose* data it is. Stores: :mod:`downtify.users`,
:mod:`downtify.activity`.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from loguru import logger

from . import api
from .activity import KINDS, clean_track, track_label
from .auth import SESSION_COOKIE, AuthStore, Principal, session_cookie
from .users import ROLE_USER, UserError, UserStore

router = APIRouter()


def _store() -> AuthStore:
    if api.state.auth is None:
        raise HTTPException(status_code=500, detail='Sign-in is not ready')
    return api.state.auth


def _users() -> UserStore:
    return _store().users


def _accounts_on() -> None:
    """409 when accounts are turned off (``DOWNTIFY_DISABLE_AUTH``):
    there is one user and no password to manage."""

    if _store().auth_disabled:
        raise HTTPException(
            status_code=409,
            detail='Accounts are turned off (DOWNTIFY_DISABLE_AUTH)',
        )


def _me(request: Request) -> Principal:
    principal = api.principal_of(request)
    if principal is None or not principal.user_id:
        raise HTTPException(status_code=401, detail='Sign in required')
    return principal


async def _json(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _bad(exc: UserError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


async def _sign_out_user(user_id: int, keep_session: str = '') -> None:
    """Unpair *user_id*'s devices and end their sessions but
    *keep_session*, closing their sockets."""

    devices = await asyncio.to_thread(
        _store().revoke_user, user_id, keep_session
    )
    for device_id in devices:
        await api.state.connections.close_device(device_id)
    if not keep_session:
        await api.state.connections.close_user(user_id)


# ── You ─────────────────────────────────────────────────────────────────


@router.get('/api/me')
def get_me(request: Request) -> dict[str, Any]:
    """``{user, preferences}`` for whoever is signed in (a browser or a
    paired app)."""

    me = _me(request)
    user = _users().get(me.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail='Sign in required')
    return {'user': user, 'preferences': _users().preferences(me.user_id)}


@router.patch('/api/me')
async def update_me(request: Request) -> dict[str, Any]:
    """Change your own username: ``{username}``."""

    _accounts_on()
    me = _me(request)
    payload = await _json(request)
    try:
        user = await asyncio.to_thread(
            _users().update, me.user_id, username=payload.get('username')
        )
    except UserError as exc:
        raise _bad(exc) from exc
    if user['username'] != me.username:
        await api.log_activity(
            request,
            'user_updated',
            user['username'],
            {'from': me.username, 'to': user['username']},
        )
    return {'user': user}


@router.put('/api/me/password')
async def change_my_password(request: Request) -> dict[str, Any]:
    """Change your password: ``{current_password, new_password}``. Every
    other browser and app of yours stays signed in; use
    ``POST /api/me/sign-out-everywhere`` for that."""

    _accounts_on()
    me = _me(request)
    ip = api.request_ip(request)
    limiter = api.state.login_limiter
    wait = limiter.retry_after(ip)
    if wait:
        raise HTTPException(
            status_code=429,
            detail='Too many attempts. Try again later.',
            headers={'Retry-After': str(wait)},
        )
    payload = await _json(request)
    current = str(payload.get('current_password') or '')
    if not await asyncio.to_thread(
        _users().check_password, me.user_id, current
    ):
        limiter.fail(ip)
        raise HTTPException(
            status_code=403, detail='The current password is wrong'
        )
    try:
        await asyncio.to_thread(
            _users().set_password,
            me.user_id,
            payload.get('new_password'),
        )
    except UserError as exc:
        raise _bad(exc) from exc
    await api.log_activity(request, 'password_changed', me.username)
    return {'user': _users().get(me.user_id)}


@router.get('/api/me/preferences')
def get_my_preferences(request: Request) -> dict[str, Any]:
    return _users().preferences(_me(request).user_id)


@router.put('/api/me/preferences')
async def set_my_preferences(request: Request) -> dict[str, Any]:
    """Merge ``{theme, locale, show_lyrics, search_albums}`` (any of them)
    into your preferences; the result. Yours only - nobody else's
    Downtify changes."""

    me = _me(request)
    payload = await _json(request)
    return await asyncio.to_thread(
        _users().set_preferences, me.user_id, payload
    )


@router.post('/api/me/sign-out-everywhere')
async def sign_out_everywhere(
    request: Request, response: Response
) -> dict[str, Any]:
    """Unpair every app of yours and sign out every browser of yours,
    this one included."""

    _accounts_on()
    me = _me(request)
    await _sign_out_user(me.user_id)
    api.state.now_playing.forget_user(me.user_id)
    response.delete_cookie(SESSION_COOKIE, path='/')
    logger.info('User {} signed out everywhere', me.username)
    return {'revoked': True}


# ── Everyone (admins) ───────────────────────────────────────────────────


def _with_devices(users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[int, int] = {}
    for device in _store().list_devices():
        uid = int(device['user_id'])
        counts[uid] = counts.get(uid, 0) + 1
    return [{**u, 'devices': counts.get(u['id'], 0)} for u in users]


@router.get('/api/users')
def list_users() -> list[dict[str, Any]]:
    """Every account, with how many apps each has paired."""

    _accounts_on()
    return _with_devices(_users().list())


@router.post('/api/users')
async def create_user(request: Request) -> dict[str, Any]:
    """Add an account: ``{username, password, role}`` (``admin`` or
    ``user``, default ``user``)."""

    _accounts_on()
    payload = await _json(request)
    try:
        user = await asyncio.to_thread(
            _users().create,
            payload.get('username'),
            payload.get('password'),
            str(payload.get('role') or ROLE_USER),
        )
    except UserError as exc:
        raise _bad(exc) from exc
    await api.log_activity(
        request, 'user_created', user['username'], {'role': user['role']}
    )
    logger.info('Created user {} ({})', user['username'], user['role'])
    return user


@router.patch('/api/users/{user_id}')
async def update_user(user_id: int, request: Request) -> dict[str, Any]:
    """Change an account: any of ``{username, role, password}``. A new
    password signs that user out of every browser (but this one, when
    it's your own) - their paired apps stay paired."""

    _accounts_on()
    me = _me(request)
    payload = await _json(request)
    before = _users().get(user_id)
    if before is None:
        raise HTTPException(status_code=404, detail='User not found')
    try:
        user = await asyncio.to_thread(
            _users().update,
            user_id,
            username=payload.get('username'),
            role=payload.get('role'),
        )
        if payload.get('password'):
            await asyncio.to_thread(
                _users().set_password, user_id, payload.get('password')
            )
            keep = (
                session_cookie(request.scope) if user_id == me.user_id else ''
            )
            await asyncio.to_thread(_store().end_user_sessions, user_id, keep)
            await api.log_activity(
                request, 'password_changed', user['username']
            )
    except UserError as exc:
        raise _bad(exc) from exc
    changes = {
        key: {'from': before[key], 'to': user[key]}
        for key in ('username', 'role')
        if before[key] != user[key]
    }
    if changes:
        await api.log_activity(
            request, 'user_updated', user['username'], changes
        )
    return _users().get(user_id) or user


@router.delete('/api/users/{user_id}')
async def delete_user(user_id: int, request: Request) -> dict[str, Any]:
    """Delete an account: its apps are unpaired and its browsers signed
    out. Not your own, and not the last admin."""

    _accounts_on()
    me = _me(request)
    if user_id == me.user_id:
        raise HTTPException(
            status_code=400, detail='You cannot delete your own account'
        )
    try:
        user = await asyncio.to_thread(_users().delete, user_id)
    except UserError as exc:
        status = 404 if 'not found' in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    await _sign_out_user(user_id)
    api.state.now_playing.forget_user(user_id)
    await api.log_activity(request, 'user_deleted', user['username'])
    logger.info('Deleted user {}', user['username'])
    return {'id': user_id, 'deleted': True}


# ── Activity ────────────────────────────────────────────────────────────


@router.get('/api/activity')
def get_activity(
    limit: int = Query(100, ge=1, le=200),
    before: int = Query(0, ge=0),
    user_id: int = Query(0, ge=0),
    kind: str = Query(''),
) -> dict[str, Any]:
    """The activity log, newest first: ``{entries, next}``. ``kind`` is
    one kind or several, comma-separated; ``next`` goes in ``before``
    for the next page (``0``: there is none)."""

    log = api.state.activity
    if log is None:
        raise HTTPException(status_code=503, detail='Starting up')
    kinds = [k for k in kind.split(',') if k in KINDS] if kind else None
    return log.entries(
        limit=limit, before=before, user_id=user_id, kinds=kinds
    )


@router.get('/api/activity/now')
def now_playing() -> list[dict[str, Any]]:
    """What every browser and app is playing now (heard from in the last
    90 seconds), playing ones first."""

    return api.state.now_playing.active()


@router.post('/api/activity/playback')
async def report_playback(request: Request) -> dict[str, Any]:
    """A player says what it's playing: ``{player, state, track,
    position}`` - ``player`` any id stable for this player (a browser
    tab, an app install), ``state`` ``playing``, ``paused`` or
    ``stopped``, ``track`` ``{title, artist, album, file | track_id,
    duration, cover}``. Send it when a song starts, on pause/resume and
    stop, and about every 30 s while playing."""

    me = _me(request)
    payload = await _json(request)
    state = str(payload.get('state') or 'playing')
    if state not in {'playing', 'paused', 'stopped'}:
        raise HTTPException(status_code=400, detail='Unknown state')
    track = clean_track(payload.get('track'))
    if state != 'stopped' and not (track.get('file') or track.get('track_id')):
        raise HTTPException(status_code=400, detail='track is required')
    try:
        position = float(payload.get('position') or 0)
    except (TypeError, ValueError):
        position = 0.0
    client = await asyncio.to_thread(api.client_label, request, me)
    player = str(payload.get('player') or me.device_id or 'web')[:64]
    started = api.state.now_playing.report(
        user_id=me.user_id,
        username=me.username,
        player=f'{me.device_id}:{player}',
        client=client,
        state=state,
        track=track,
        position=position,
        ip=api.request_ip(request),
    )
    if started:
        await api.log_activity(
            request, 'playback', track_label(track), {'track': track}
        )
    return {'ok': True}
