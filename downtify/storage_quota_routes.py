"""HTTP routes for storage quotas (issue #677).

* ``GET /api/me/storage`` - the signed-in account's usage and quota
  (a browser or a paired app).
* ``GET /api/users/storage`` - every account's usage and quota, and the
  default (admins).
* ``PUT /api/users/storage/default`` - ``{quota_bytes}``: the default
  quota, ``null`` for none (admins).
* ``PUT /api/users/{id}/storage`` - ``{quota_bytes}``: an account's own
  quota, ``-1`` for unlimited, ``null`` to follow the default (admins).
* ``POST /api/users/{id}/storage/reset`` - forget what an account
  downloaded, so it counts nothing again; no file is deleted (admins).

Rules and storage: :mod:`downtify.storage_quota`; enforcement:
``downtify/api.py`` (:func:`downtify.api.storage_quota_refusal`).
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from . import api
from .storage_quota import QuotaError, StorageQuotas, format_bytes
from .users import ROLE_ADMIN, UserStore

router = APIRouter()


def _quotas() -> StorageQuotas:
    if api.state.storage_quotas is None:
        raise HTTPException(status_code=500, detail='Quotas are not ready')
    return api.state.storage_quotas


def _users() -> UserStore:
    if api.state.auth is None:
        raise HTTPException(status_code=500, detail='Sign-in is not ready')
    return api.state.auth.users


async def _json(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _user_or_404(user_id: int) -> dict[str, Any]:
    user = _users().get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    return user


def _label(value: Any) -> str:
    if value is None:
        return 'default'
    if int(value) < 0:
        return 'unlimited'
    return format_bytes(int(value))


@router.get('/api/me/storage')
def my_storage(request: Request) -> dict[str, Any]:
    """``{used, limit, remaining, unlimited, exceeded, source, own}`` for
    whoever is signed in (see :func:`downtify.storage_quota.quota_status`).
    """

    principal = api.principal_of(request)
    if principal is None or not principal.user_id:
        raise HTTPException(status_code=401, detail='Sign in required')
    return api.storage_status(
        principal.user_id, is_admin=bool(principal.is_admin)
    )


def _everyone() -> dict[str, Any]:
    quotas = _quotas()
    sizes = api.library_live_sizes()
    rows = []
    for user in _users().list():
        status = api.storage_status(
            user['id'],
            is_admin=user['role'] == ROLE_ADMIN,
            sizes=sizes,
        )
        rows.append({
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
            **status,
        })
    return {'default': quotas.default(), 'users': rows}


@router.get('/api/users/storage')
async def everyone_storage() -> dict[str, Any]:
    """``{default, users: [{id, username, role, used, limit, remaining,
    unlimited, exceeded, source, own}]}``; ``default`` is ``null`` when
    there is none."""

    return await asyncio.to_thread(_everyone)


@router.put('/api/users/storage/default')
async def set_default_quota(request: Request) -> dict[str, Any]:
    """``{quota_bytes}``: the quota of every user without one of their
    own; ``null`` (or ``-1``) for none."""

    payload = await _json(request)
    quotas = _quotas()
    before = await asyncio.to_thread(quotas.default)
    try:
        await asyncio.to_thread(quotas.set_default, payload.get('quota_bytes'))
    except QuotaError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    after = await asyncio.to_thread(quotas.default)
    if before != after:
        await api.log_activity(
            request,
            'settings_changed',
            'Default storage quota',
            {
                'storage_quota_default': {
                    'from': _label(before),
                    'to': _label(after),
                }
            },
        )
        logger.info('Default storage quota: {}', _label(after))
    return await asyncio.to_thread(_everyone)


@router.put('/api/users/{user_id}/storage')
async def set_user_quota(user_id: int, request: Request) -> dict[str, Any]:
    """``{quota_bytes}``: *user_id*'s own quota in bytes, ``-1`` for
    unlimited, ``null`` to follow the default. Returns their status."""

    user = await asyncio.to_thread(_user_or_404, user_id)
    payload = await _json(request)
    quotas = _quotas()
    before = await asyncio.to_thread(quotas.get, user_id)
    try:
        after = await asyncio.to_thread(
            quotas.set, user_id, payload.get('quota_bytes')
        )
    except QuotaError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if before != after:
        await api.log_activity(
            request,
            'user_updated',
            user['username'],
            {'storage_quota': {'from': _label(before), 'to': _label(after)}},
        )
    return await asyncio.to_thread(
        api.storage_status, user_id, is_admin=user['role'] == ROLE_ADMIN
    )


def _reset_usage(user_id: int) -> int:
    owners = api.state.track_owners
    if owners is None:
        return 0
    paths = owners.owned_paths(user_id)
    removed = owners.remove_user(user_id)
    # Their own library (per_user_library) may have shrunk: the apps
    # learn it from the feed.
    if api.state.library_sync is not None:
        for path in sorted(paths):
            try:
                api.state.library_sync.touch(path)
            except Exception:
                logger.opt(exception=True).debug('Could not touch {}', path)
    return removed


@router.post('/api/users/{user_id}/storage/reset')
async def reset_user_usage(user_id: int, request: Request) -> dict[str, Any]:
    """Forget which files *user_id* downloaded, so their usage starts
    from zero. The files stay in the library; the account just no
    longer counts as their downloader (nor may delete them as such).
    Returns their status."""

    user = await asyncio.to_thread(_user_or_404, user_id)
    removed = await asyncio.to_thread(_reset_usage, user_id)
    await api.log_activity(
        request,
        'user_updated',
        user['username'],
        {'storage_usage_reset': {'from': removed, 'to': 0}},
    )
    logger.info(
        'Storage usage of {} reset ({} file(s) forgotten)',
        user['username'],
        removed,
    )
    return await asyncio.to_thread(
        api.storage_status, user_id, is_admin=user['role'] == ROLE_ADMIN
    )
