"""Administrative controls for reversible automatic-download exclusions."""

import asyncio

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import api
from .admin_access import admin_user

router = APIRouter(prefix='/api/v1/download-policy')


class Track(BaseModel):
    song_id: str = Field(default='', max_length=100)
    name: str = Field(min_length=1, max_length=500)
    artist: str = Field(default='', max_length=300)
    artists: list[str] = Field(default_factory=list, max_length=20)
    album_name: str = Field(default='', max_length=500)
    duration: float = Field(default=0, ge=0, le=86400)


def policy():
    db = api.state.monitor_db
    if db is None:
        raise HTTPException(503, detail={'code': 'monitor_unavailable'})
    return db.download_policy


@router.get('/exclusions')
async def exclusions(request: Request):
    admin_user(request)
    return {'items': await asyncio.to_thread(policy().exclusions)}


@router.post('/exclusions')
async def suppress(request: Request, track: Track):
    user = admin_user(request)
    try:
        return await asyncio.to_thread(
            policy().suppress, track.model_dump(), user_id=user
        )
    except ValueError:
        raise HTTPException(
            422, detail={'code': 'identity_uncertain'}
        ) from None


@router.delete('/exclusions/{ident}')
async def resume(request: Request, ident: str):
    admin_user(request)
    try:
        await asyncio.to_thread(policy().resume, ident)
    except ValueError as exc:
        if str(exc) == 'attempt_still_stopping':
            raise HTTPException(409, detail={'code': str(exc)}) from None
        raise HTTPException(404, detail={'code': 'item_not_found'}) from None
    return {'ok': True}
