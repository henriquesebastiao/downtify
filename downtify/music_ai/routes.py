"""Authenticated native adapter. Heavy work is delegated to the companion."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from functools import lru_cache, wraps
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .playlists import generate, summaries
from .ranking import rank
from .store import MOODS, Store

router = APIRouter(prefix='/api/v1/music-ai', tags=['Optional music AI'])


_queries = asyncio.Semaphore(1)


def bounded_query(function):
    @wraps(function)
    async def run(*args, **kwargs):
        async with _queries:
            return await function(*args, **kwargs)

    return run


@lru_cache(maxsize=1)
def _open_store(path):
    return Store(path)


def store():
    from .. import api

    return _open_store(
        api.state.settings_path.parent / 'music-ai' / 'derived.db'
    )


def owner(request):
    from .. import api

    value = api.request_user_id(request)
    if not value:
        raise HTTPException(401, 'Sign in required')
    return value


def admin(request):
    from .. import api

    owner(request)
    if not api.request_is_admin(request):
        raise HTTPException(403, 'Administrator required')


def catalog(request):
    from .. import api, mobile_routes

    owner(request)
    # Native startup and background indexing maintain the ids. An interactive
    # request must never start a full NAS walk or metadata reconciliation.
    rows = mobile_routes._sync().changes(
        0, allowed_keys=api.allowed_entry_keys(request)
    )['tracks']
    hidden = api.library_context().hidden_files
    rows = [row for row in rows if row.get('file') not in hidden]
    for row in rows:
        identity = (
            row.get('file'),
            row.get('size'),
            row.get('modified'),
            row.get('added'),
            row.get('duration'),
        )
        row['fingerprint'] = hashlib.sha256(
            json.dumps(identity).encode()
        ).hexdigest()
    store().observe(rows)
    return rows


def listening_track(request, identity, library_file):
    from .. import api, mobile_routes

    owner(request)
    sync = mobile_routes._sync()
    if not identity and library_file:
        identity = sync.ids_for_paths([library_file]).get(library_file, '')
    row = sync.row_for(identity) if identity else None
    if row is None:
        return None
    if row['file'] not in api.filter_paths_for_request([row['file']], request):
        return None
    row['fingerprint'] = hashlib.sha256(
        json.dumps((
            row.get('file'),
            row.get('size'),
            row.get('modified'),
            row.get('added'),
            row.get('duration'),
        )).encode()
    ).hexdigest()
    store().observe([row])
    return row


def require(request, feature):
    uid = owner(request)
    if not store().effective(uid)[feature]:
        raise HTTPException(409, 'Feature disabled')
    return uid


def favorite_ids(request, rows):
    from .. import api

    if api.state.likes is None:
        return set()
    # An administrator's recommendations use their own hearts as well.
    files = set(api.state.likes.paths(owner(request)))
    return {row['id'] for row in rows if row['file'] in files}


def current_sources(rows):
    """Stat only selected results; never walk or decode the full library here."""
    from .. import api
    from ..library_catalog import resolve_library_file
    from .worker import signature

    current = []
    context = api.library_context()
    for row in rows:
        full = resolve_library_file(row['file'], context)
        try:
            version = (
                list(signature(full)) if full is not None else ['missing']
            )
        except OSError:
            version = ['missing']
        if store().observe_source(row['id'], version) and version != [
            'missing'
        ]:
            current.append(row)
    return current


def model():
    status = store().metadata('model', {})
    if not status.get('ready') or not status.get('id'):
        raise HTTPException(503, 'Local audio analysis is not ready')
    return status['id']


def public(row):
    # Native rows contain library-relative paths. The new API only exposes ids
    # and authenticated relative stream URLs, never machine filesystem paths.
    keys = (
        'id',
        'title',
        'artist',
        'album',
        'duration',
        'cover',
        'score',
        'reason',
        'analyzed',
    )
    return {
        **{key: row[key] for key in keys if key in row},
        'stream_url': f'/api/v1/tracks/{row["id"]}/stream',
    }


@router.get('/similar')
@bounded_query
async def similar(
    request: Request,
    artist: str = Query('', max_length=200),
    track: str = Query('', max_length=200),
    seed: str = Query('', max_length=80),
    library_file: str = Query('', max_length=4096),
    limit: int = Query(20, ge=1, le=50),
):
    require(request, 'similarity')
    from ..library_only import text

    rows = await asyncio.to_thread(catalog, request)
    candidates = [
        row
        for row in rows
        if (not seed or row['id'] == seed)
        and (not library_file or row['file'] == library_file)
        and (not track or text(row.get('title', '')) == text(track))
        and (not artist or text(row.get('artist', '')) == text(artist))
    ]
    if not (artist or track or seed or library_file) or not candidates:
        raise HTTPException(404, 'Choose a track in your local library')
    if len(candidates) > 1:
        raise HTTPException(
            409, 'Several versions match; choose a specific library track'
        )
    if not await asyncio.to_thread(current_sources, candidates):
        raise HTTPException(503, 'This file needs a new audio analysis')
    seed = sorted(candidates, key=lambda row: row['id'])[0]['id']
    identity = model()
    vectors = await asyncio.to_thread(
        store().vectors, identity, {row['id'] for row in rows}
    )
    if seed not in vectors:
        raise HTTPException(503, 'This track has not been analyzed yet')
    result = await asyncio.to_thread(
        rank, rows, vectors, seed=seed, limit=limit
    )
    result = await asyncio.to_thread(current_sources, result)
    require(request, 'similarity')
    # Existing Similar clients already understand these library-relative paths.
    # Paths come only from the native visible catalog, never from the caller.
    return {
        'source': 'local',
        'tracks': [
            {
                'song_id': row['id'],
                'file': row['file'],
                'name': row.get('title', ''),
                'artist': row.get('artist', ''),
                'artists': [row.get('artist', '')],
                'album_name': row.get('album', ''),
                'duration': row.get('duration', 0),
                'reason': row['reason'],
                'source': 'library',
            }
            for row in result
        ],
    }


@router.get('/external-similar')
async def external_similar(
    request: Request,
    artist: str = Query('', max_length=200),
    track: str = Query('', max_length=200),
    limit: int = Query(20, ge=1, le=50),
):
    require(request, 'external_beta')
    from .. import api, library_only

    if library_only.enabled(api.state.settings):
        raise HTTPException(
            409, 'External discovery is disabled by library-only mode'
        )
    result = await api._external_similar_tracks(artist, track, limit, request)
    require(request, 'external_beta')
    # Reuse native local handles if an external suggestion already exists.
    from .ranking import recording

    rows = await asyncio.to_thread(catalog, request)
    local = {recording(row): row for row in rows}
    for suggestion in result.get('tracks', []):
        candidate = local.get(
            recording({
                'id': suggestion.get('song_id', ''),
                'title': suggestion.get('name', ''),
                'artist': suggestion.get('artist')
                or next(iter(suggestion.get('artists') or []), ''),
            })
        )
        if candidate is not None:
            suggestion.update(
                file=candidate['file'],
                song_id=candidate['id'],
                source='library',
            )
    return result


@router.get('/capabilities')
def capabilities(request: Request):
    from .. import api

    uid = owner(request)
    store().ensure_user(uid)
    dj = store().metadata('dj', {'ready': False})
    if not 0 <= time.time() - dj.get('seen', 0) <= 20:
        dj = {
            **dj,
            'ready': False,
            'prepared_ready': False,
            'interactive_ready': False,
            'state': 'unavailable',
        }
    return {
        'version': 1,
        'administrator': api.request_is_admin(request),
        'profile_revision': store().metadata(f'profile_revision:{uid}', 0),
        'features': store().effective(uid),
        'model': store().metadata('model', {'ready': False}),
        'moods': list(MOODS),
        'dj': dj,
        'source_available': Path('/downtify/music-ai-source.tar.gz').is_file(),
    }


@router.get('/source', response_class=FileResponse)
def corresponding_source(request: Request):
    owner(request)
    path = Path('/downtify/music-ai-source.tar.gz')
    if not path.is_file():
        raise HTTPException(503, 'Corresponding source bundle is unavailable')
    return FileResponse(
        path,
        filename='downtify-music-ai-source.tar.gz',
        media_type='application/gzip',
    )


@router.get('/preferences')
def preferences(request: Request):
    uid = owner(request)
    return {
        'preferences': store().preferences(uid),
        'effective': store().effective(uid),
    }


@router.put('/preferences')
def update_preferences(changes: dict, request: Request):
    try:
        return {'effective': store().set_preferences(owner(request), changes)}
    except ValueError as error:
        raise HTTPException(422, str(error)) from None


@router.get('/admin/features')
def admin_features(request: Request):
    admin(request)
    return store().preferences(-1)


@router.put('/admin/features')
def update_admin_features(changes: dict, request: Request):
    admin(request)
    try:
        return store().set_preferences(-1, changes)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None


@router.get('/recommendations')
@bounded_query
async def recommendations(
    request: Request, seed: str = '', limit: int = Query(40, ge=1, le=50)
):
    uid = require(request, 'similarity' if seed else 'personalization')
    rows = await asyncio.to_thread(catalog, request)
    if not rows and not seed:
        return {'source': 'local', 'tracks': []}
    identity = model()
    allowed = {row['id'] for row in rows}
    if seed and seed not in allowed:
        raise HTTPException(404, 'Track unavailable')
    if seed and not await asyncio.to_thread(
        current_sources, [row for row in rows if row['id'] == seed]
    ):
        raise HTTPException(503, 'This file needs a new audio analysis')
    vectors = await asyncio.to_thread(store().vectors, identity, allowed)
    if seed and seed not in vectors:
        raise HTTPException(503, 'This track has not been analyzed yet')
    result = await asyncio.to_thread(
        rank,
        rows,
        vectors,
        seed=seed or None,
        history=store().history(uid),
        favorites=await asyncio.to_thread(favorite_ids, request, rows),
        limit=limit,
    )
    result = await asyncio.to_thread(current_sources, result)
    require(request, 'similarity' if seed else 'personalization')
    return {'source': 'local', 'tracks': [public(row) for row in result]}


@router.get('/playlists')
@bounded_query
async def playlist_index(request: Request):
    uid = owner(request)
    flags = store().effective(uid)
    if not flags['daily'] and not flags['weekly']:
        return {'playlists': []}
    rows = await asyncio.to_thread(catalog, request)
    result = await asyncio.to_thread(summaries, store(), uid, rows)
    flags = store().effective(uid)
    return {'playlists': [item for item in result if flags[item['cadence']]]}


@router.get('/playlists/{cadence}/{mood}')
@bounded_query
async def mood_playlist(
    cadence: Literal['daily', 'weekly'], mood: str, request: Request
):
    uid = require(request, cadence)
    if mood not in MOODS:
        raise HTTPException(404, 'Unknown mood')
    rows = await asyncio.to_thread(catalog, request)
    try:
        result = await asyncio.to_thread(
            generate, store(), uid, cadence, mood, rows, model()
        )
    except RuntimeError:
        raise HTTPException(503, 'Mood analysis is not ready') from None
    except PermissionError:
        raise HTTPException(409, 'Feature disabled') from None
    result = await asyncio.to_thread(current_sources, result)
    require(request, cadence)
    return {
        'cadence': cadence,
        'mood': mood,
        'tracks': [public(row) for row in result],
    }


class SavedSelection(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    ids: list[str] = Field(min_length=1, max_length=50)
    source: Literal['personalization', 'similarity', 'daily', 'weekly']


class PlaybackSelection(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=50)


@router.post('/playback')
async def playback_selection(payload: PlaybackSelection, request: Request):
    # The existing web player consumes library-relative file handles. Resolve
    # them only from the current native ACL-filtered catalog, never client paths.
    visible = {
        row['id']: row for row in await asyncio.to_thread(catalog, request)
    }
    if any(identity not in visible for identity in payload.ids):
        raise HTTPException(404, 'A selected track is no longer available')
    keys = ('id', 'file', 'title', 'artist', 'album', 'duration', 'has_cover')
    return {
        'tracks': [
            {
                key: visible[identity][key]
                for key in keys
                if key in visible[identity]
            }
            for identity in dict.fromkeys(payload.ids)
        ]
    }


@router.post('/playlists/save')
async def save_selection(payload: SavedSelection, request: Request):
    require(request, payload.source)
    from .. import api
    from ..manual_playlists import ManualPlaylistError, copy_playlist

    visible = {
        row['id']: row for row in await asyncio.to_thread(catalog, request)
    }
    if any(identity not in visible for identity in payload.ids):
        raise HTTPException(404, 'A selected track is no longer available')
    files = list(
        dict.fromkeys(visible[identity]['file'] for identity in payload.ids)
    )
    try:
        result = await asyncio.to_thread(
            copy_playlist, api.library_context(), files, payload.name
        )
    except ManualPlaylistError as error:
        raise HTTPException(error.status_code, str(error)) from None
    api.claim_manual_playlist(result['name'], request)
    api.invalidate_library_paths_cache()
    await api.announce_playlists_changed()
    return {'name': result['name'], 'count': result['count']}


class Listen(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    track_id: str = Field(default='', max_length=80)
    library_file: str = Field(default='', max_length=4096)
    sequence: int = Field(default=0, ge=0, le=1000000)
    generation: int = Field(default=0, ge=0)
    seconds: float = Field(ge=0, le=86400, allow_inf_nan=False)
    outcome: Literal['complete', 'skip', 'error', 'pause']


@router.post('/listens')
async def listen(payload: Listen, request: Request):
    uid = require(request, 'personalization')
    row = await asyncio.to_thread(
        listening_track, request, payload.track_id, payload.library_file
    )
    if row is None:
        raise HTTPException(404, 'Track unavailable')
    seconds = min(
        payload.seconds, float(row.get('duration') or payload.seconds)
    )
    recorded = await asyncio.to_thread(
        store().listen,
        uid,
        payload.event_id,
        row['id'],
        seconds,
        payload.outcome,
        sequence=payload.sequence,
        generation=payload.generation,
    )
    return {'recorded': recorded}


@router.delete('/profile')
def forget_profile(request: Request):
    from .. import api

    uid = owner(request)
    store().forget(uid)
    if api.state.discover is not None:
        # Always the authenticated owner, including for administrators.
        api.state.discover.clear_listens(uid)
    return {'ok': True}


@router.delete('/admin/analyses')
def forget_analyses(request: Request):
    admin(request)
    store().clear_analyses()
    return {'ok': True}


@router.get('/admin/analyses')
def analysis_status(request: Request):
    admin(request)
    return store().analysis_status()


@router.post('/admin/analysis/retry')
def retry_analyses(request: Request):
    admin(request)
    if store().metadata('analysis_paused', False):
        raise HTTPException(409, 'Resume analysis before retrying')
    if not any(
        store().preferences(-1)[key]
        for key in ('similarity', 'personalization', 'daily', 'weekly')
    ):
        raise HTTPException(409, 'Local analysis is disabled')
    return {'queued': store().retry_analyses()}


@router.post('/admin/analysis')
def resume_analysis(request: Request):
    admin(request)
    store().set_metadata('analysis_paused', False)
    return {'queued': True}


# Register DJ after shared route adapters exist, avoiding a circular import.
from .dj_routes import router as dj_router  # noqa: E402

router.include_router(dj_router)
