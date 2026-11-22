"""AcoustID settings API (admins): the feature's state, the key, a test.

``acoustid_enabled`` itself is an ordinary setting (``POST
/api/settings/update``). The application key is not: it is kept in
``<data>/.acoustid_key`` (:class:`downtify.acoustid.KeyStore`) and these
routes never send it back, only its last four characters.

* ``GET /api/acoustid`` - ``{enabled, key_set, key_hint, fingerprinter,
  ready}`` (``fingerprinter``: ``fpcalc``, ``ffmpeg`` or ``''``).
* ``PUT /api/acoustid/key`` ``{key}`` - save the key (``''`` removes it).
* ``POST /api/acoustid/test`` - ask AcoustID whether the saved key works:
  ``{ok, detail}``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import acoustid, api
from .admin_access import admin_user

router = APIRouter(prefix='/api/acoustid', dependencies=[Depends(admin_user)])

KEY_FILE = '.acoustid_key'


class KeyRequest(BaseModel):
    key: str = ''


def key_store() -> acoustid.KeyStore:
    path = api.state.settings_path
    data = Path(path).parent if path else Path('/data')
    return acoustid.KeyStore(data / KEY_FILE)


def current_key() -> str:
    """The saved key, ``''`` without one (for the library upgrade)."""

    return key_store().get()


def _status() -> dict[str, Any]:
    return acoustid.status(
        bool((api.state.settings or {}).get('acoustid_enabled')),
        key_store(),
    )


@router.get('')
async def acoustid_status() -> dict[str, Any]:
    return await asyncio.to_thread(_status)


@router.put('/key')
async def acoustid_set_key(body: KeyRequest) -> dict[str, Any]:
    raw = body.key.strip()
    key = acoustid.clean_key(raw)
    if raw and not key:
        raise HTTPException(
            status_code=400, detail='That does not look like an API key'
        )
    try:
        await asyncio.to_thread(key_store().set, key)
    except OSError as exc:
        raise HTTPException(
            status_code=500, detail='Could not save the key'
        ) from exc
    return await asyncio.to_thread(_status)


@router.post('/test')
async def acoustid_test() -> dict[str, Any]:
    key = await asyncio.to_thread(current_key)
    if not key:
        return {'ok': False, 'detail': 'No API key is saved'}
    try:
        await asyncio.to_thread(acoustid.check_key, key)
    except acoustid.InvalidKey:
        return {'ok': False, 'detail': 'AcoustID refused the API key'}
    except acoustid.AcoustIDError as exc:
        return {'ok': False, 'detail': str(exc)}
    return {'ok': True, 'detail': 'AcoustID accepted the key'}
