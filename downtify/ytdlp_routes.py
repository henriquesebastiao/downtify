"""yt-dlp updates API (admins), for Settings > Sources > YouTube.

* ``GET /api/ytdlp`` - what :meth:`YtdlpUpdater.status` says, plus
  ``youtube`` (whether YouTube downloads keep failing) and
  ``can_restart``.
* ``PUT /api/ytdlp`` ``{enabled?, auto_restart?}`` - the two switches.
* ``POST /api/ytdlp/check`` - ask PyPI now (and install and test a newer
  version when switched on); answers once that is done.
* ``POST /api/ytdlp/use`` ``{version: 'previous' | 'image'}`` - go back;
  it applies at the next restart.
* ``POST /api/ytdlp/restart`` - restart Downtify now to load the chosen
  yt-dlp.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import api, server_port, ytdlp_health
from .admin_access import admin_user
from .ytdlp_update import UpdateError, YtdlpUpdater

router = APIRouter(prefix='/api/ytdlp', dependencies=[Depends(admin_user)])


class Switches(BaseModel):
    enabled: Optional[bool] = None
    auto_restart: Optional[bool] = None


class UseRequest(BaseModel):
    version: Literal['previous', 'image']


def _updater() -> YtdlpUpdater:
    updater = getattr(api.state, 'ytdlp_updater', None)
    if updater is None:
        raise HTTPException(status_code=503, detail='Not ready yet')
    return updater


def _status(updater: YtdlpUpdater) -> dict[str, Any]:
    return {
        **updater.status(),
        'youtube': ytdlp_health.monitor.status(),
        'can_restart': server_port.can_restart(),
    }


@router.get('')
async def ytdlp_status() -> dict[str, Any]:
    return await asyncio.to_thread(_status, _updater())


@router.put('')
async def ytdlp_switches(body: Switches) -> dict[str, Any]:
    updater = _updater()
    await asyncio.to_thread(
        updater.configure,
        enabled=body.enabled,
        auto_restart=body.auto_restart,
    )
    return await asyncio.to_thread(_status, updater)


@router.post('/check')
async def ytdlp_check() -> dict[str, Any]:
    updater = _updater()
    await asyncio.to_thread(updater.check_now)
    return await asyncio.to_thread(_status, updater)


@router.post('/use')
async def ytdlp_use(body: UseRequest) -> dict[str, Any]:
    updater = _updater()
    try:
        await asyncio.to_thread(updater.use, body.version)
    except UpdateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return await asyncio.to_thread(_status, updater)


@router.post('/restart')
async def ytdlp_restart() -> dict[str, Any]:
    updater = _updater()
    if not server_port.can_restart():
        raise HTTPException(
            status_code=409, detail='Downtify cannot restart itself here'
        )
    # Answer first: the restart closes this connection.
    asyncio.get_running_loop().call_later(0.5, updater.restart_now)
    return {'restarting': True}
