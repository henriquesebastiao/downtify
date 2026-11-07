"""Owner-scoped DJ API; original files and render paths stay on the server."""

from __future__ import annotations

import hashlib
import json
import re
import time
from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from .dj_store import CancelledDjRequest, DjStore
from .ranking import rank
from .worker import signature

router = APIRouter(prefix='/dj')


def database():
    from . import routes as base

    return _open_dj(base.store())


@lru_cache(maxsize=1)
def _open_dj(store):
    return DjStore(store)


def service(mode, *, trial=False):
    from . import routes as base

    status = base.store().metadata('dj', {})
    age = time.time() - status.get('seen', 0)
    if not 0 <= age <= 20 or not status.get(
        'prepared_ready' if trial else f'{mode}_ready'
    ):
        raise HTTPException(
            503, 'Le moteur DJ est indisponible ou encore en validation.'
        )


def local_pool(rows, count, rotation):
    """A bounded native selection for the DJ's own analysis, without starting a recommender."""
    ordered = sorted(
        rows,
        key=lambda row: hashlib.sha256(
            f'{rotation}:{row["id"]}'.encode()
        ).hexdigest(),
    )
    selected, seen, artists = [], set(), {}
    for row in ordered:
        artist = str(row.get('artist') or '').casefold()
        if row['id'] in seen or (artist and artists.get(artist, 0) >= 2):
            continue
        selected.append(row)
        seen.add(row['id'])
        artists[artist] = artists.get(artist, 0) + 1
        if len(selected) == count:
            break
    return selected


def visible(request, ids, *, sources=False, known_paths=None):
    """Check current native ACLs; rendered audio does not need original NAS I/O."""
    from .. import api, mobile_routes
    from ..library_catalog import entry_content_key, resolve_library_file
    from . import routes as base

    base.owner(request)
    context, sync = api.library_context(), mobile_routes._sync()
    rows, snapshots = {}, {}
    # One native connection for a window, rather than one connection per title.
    bulk = (
        {row['id']: row for row in sync.rows_for(ids)}
        if hasattr(sync, 'rows_for')
        else {identity: sync.row_for(identity) for identity in ids}
    )
    allowed = api.allowed_entry_keys(
        request, entries=[row for row in bulk.values() if row is not None]
    )
    for identity in ids:
        row = bulk.get(identity)
        if (
            not row
            or row.get('file') in context.hidden_files
            or (allowed is not None and entry_content_key(row) not in allowed)
        ):
            raise HTTPException(
                404, 'Un titre de ce set n’est plus accessible.'
            )
        path = (
            resolve_library_file(row['file'], context)
            if sources or known_paths is None
            else known_paths.get(identity)
        )
        if path is None or str(path) in getattr(
            context, 'hidden_resolved', ()
        ):
            raise HTTPException(
                404, 'Un titre de ce set n’est plus accessible.'
            )
        rows[identity] = row
        if sources:
            try:
                version = list(signature(path))
            except OSError:
                raise HTTPException(
                    404, 'Un titre de ce set n’est plus accessible.'
                ) from None
            fingerprint = hashlib.sha256(
                json.dumps(
                    tuple(
                        row.get(key)
                        for key in (
                            'file',
                            'size',
                            'modified',
                            'added',
                            'duration',
                        )
                    )
                ).encode()
            ).hexdigest()
            snapshots[identity] = {
                'path': str(path),
                'source_version': version,
                'fingerprint': fingerprint,
                'artist': row.get('artist', ''),
            }
    return snapshots if sources else rows


def visible_session(request, session):
    from . import routes as base

    paths = database().source_paths(base.owner(request), session['id'])
    return visible(request, session['ids'], known_paths=paths)


def owned(request, identity):
    from . import routes as base

    if not re.fullmatch('[a-f0-9]{32}', identity):
        raise HTTPException(404, 'Set DJ indisponible.')
    try:
        session = database().get(base.owner(request), identity)
    except LookupError:
        raise HTTPException(404, 'Set DJ indisponible.') from None
    if session['state'] == 'deleted':
        raise HTTPException(404, 'Set DJ indisponible.')
    base.require(request, 'dj_' + session['mode'])
    return session


def public(session, rows):
    keys = (
        'id',
        'mode',
        'state',
        'theme',
        'created',
        'updated',
        'progress',
        'phase',
        'duration',
        'position',
        'rendered',
        'next_mutable_at',
        'revision',
        'error',
        'preparation_seconds',
        'render_speed',
        'validation',
        'selection_basis',
        'queue_order',
        'continuous',
        'renewals',
        'media_origin',
    )
    result = {key: session[key] for key in keys if key in session}
    result['tracks'] = [
        {
            'id': identity,
            'title': rows[identity].get('title', ''),
            'artist': rows[identity].get('artist', ''),
            'file': rows[identity].get('file', ''),
            'duration': rows[identity].get('duration', 0),
        }
        for identity in session.get('ids', [])
    ]
    result['timeline'] = session.get('timeline', [])
    if session['mode'] == 'interactive':
        result['commands'] = database().command_results(session['id'])
        if session['state'] in {'playing', 'paused', 'ready'}:
            result['media_url'] = (
                f'/api/v1/music-ai/dj/sessions/{session["id"]}/hls/index.m3u8'
            )
    if session['mode'] == 'prepared' and session['state'] == 'ready':
        result['media_url'] = (
            f'/api/v1/music-ai/dj/sessions/{session["id"]}/media'
        )
    return result


class Selection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str = Field(min_length=1, max_length=128)
    mode: Literal['prepared', 'interactive'] = 'prepared'
    theme: Literal[
        'calme', 'concentration', 'energie', 'fete', 'melancolie', 'detente'
    ]
    ids: list[str] = Field(default_factory=list, max_length=40)
    count: int = Field(default=12, ge=2, le=40)
    queue_order: bool = False
    continuous: bool = False
    queue_files: list[str] = Field(default_factory=list, max_length=40)
    style: Literal['library', 'rap', 'rock', 'electro'] = 'library'
    seed_id: str = Field(default='', max_length=80)
    seed_file: str = Field(default='', max_length=4096)
    trial: bool = False
    skip_seed: bool = False


@router.post('/sessions', status_code=202)
def create(payload: Selection, request: Request):
    return create_session(payload, request)


@router.post('/admin/validation-sessions', status_code=202)
def create_validation(payload: Selection, request: Request):
    from . import routes as base

    base.admin(request)
    if payload.mode != 'interactive':
        raise HTTPException(
            422, 'Choisissez le mode interactif pour la validation.'
        )
    return create_session(payload, request, validation=True)


def create_session(payload, request, *, validation=False):
    from . import routes as base

    uid = base.require(request, 'dj_' + payload.mode)
    if payload.trial:
        base.require(request, 'dj_trial')
        if payload.mode != 'interactive' or validation:
            raise HTTPException(422, 'L’essai bêta concerne le DJ interactif.')
    if database().request_cancelled(uid, payload.request_id):
        raise HTTPException(410, 'Cette création DJ a été annulée.')
    if (
        (
            (payload.queue_order or payload.continuous)
            and payload.mode != 'interactive'
        )
        or (payload.queue_order and not (payload.ids or payload.queue_files))
        or (payload.ids and payload.queue_files)
        or (payload.queue_files and not payload.queue_order)
    ):
        raise HTTPException(
            422,
            'Le mode file nécessite une sélection locale et le DJ interactif.',
        )
    intention = [
        payload.mode,
        payload.theme,
        payload.ids
        if payload.ids
        else {'queue_files': payload.queue_files}
        if payload.queue_files
        else {'automatic_count': payload.count},
    ]
    if validation:
        intention.append({'validation': True})
    if payload.queue_order or payload.continuous:
        intention.append({
            'queue_order': payload.queue_order,
            'continuous': payload.continuous,
        })
    if payload.style != 'library':
        if payload.ids or payload.queue_files:
            raise HTTPException(
                422, 'Le filtre de genre nécessite une sélection automatique.'
            )
        intention.append({'style': payload.style})
    if payload.seed_id or payload.seed_file:
        if (
            payload.ids
            or payload.queue_files
            or payload.style != 'library'
            or (payload.seed_id and payload.seed_file)
        ):
            raise HTTPException(422, 'Choisissez un seul titre de départ.')
        intention.append({
            'seed_id': payload.seed_id,
            'seed_file': payload.seed_file,
            'skip_seed': payload.skip_seed,
        })
    elif payload.skip_seed:
        raise HTTPException(422, 'Un titre de départ est requis.')
    if payload.trial:
        intention.append({'trial': True})
    request_intent = json.dumps(intention, separators=(',', ':'))
    try:
        previous = database().find_request(
            uid, payload.request_id, request_intent
        )
    except ValueError:
        raise HTTPException(
            422,
            'Identifiant de demande déjà utilisé pour une autre sélection.',
        ) from None
    if previous is not None:
        if previous['state'] == 'deleted':
            raise HTTPException(
                410, 'Ce set a été supprimé. Créez une nouvelle demande.'
            )
        return public(previous, visible_session(request, previous))
    service('prepared' if validation else payload.mode, trial=payload.trial)
    ids = payload.ids
    seed_id = payload.seed_id
    if payload.seed_file:
        from .. import mobile_routes

        seed_id = (
            mobile_routes
            ._sync()
            .ids_for_paths([payload.seed_file])
            .get(payload.seed_file, '')
        )
        if not seed_id:
            raise HTTPException(404, 'Ce titre n’est plus disponible.')
    if payload.queue_files:
        from .. import mobile_routes

        by_file = mobile_routes._sync().ids_for_paths(payload.queue_files)
        if any(file not in by_file for file in payload.queue_files):
            raise HTTPException(
                404,
                'Cette file contient un titre qui n’est plus accessible localement.',
            )
        ids = [by_file[file] for file in payload.queue_files]
    basis = 'explicit'
    if not ids:
        rows = base.catalog(request)
        if payload.style != 'library':
            patterns = {
                'rap': r'\b(rap|hip[ -]?hop|trap)\b',
                'rock': r'\b(rock|metal|punk|grunge)\b',
                'electro': r'\b(electro\w*|house|techno|trance|dance|edm|dubstep)\b',
            }
            rows = [
                row
                for row in rows
                if re.search(
                    patterns[payload.style], str(row.get('genre') or ''), re.I
                )
            ]
            if len(rows) < 2:
                raise HTTPException(
                    422,
                    'Pas encore assez de titres locaux identifiés dans ce genre. Complétez leurs métadonnées ou choisissez une humeur.',
                )
        model = base.store().metadata('model', {}).get('id')
        vectors = (
            base.store().vectors(model, {row['id'] for row in rows})
            if model
            else {}
        )
        with base.store().connect() as db:
            prompt = db.execute(
                'SELECT vector FROM mood_vectors WHERE mood=? AND model=?',
                (payload.theme, model),
            ).fetchone()
        candidates = [
            row
            for row in rows
            if 10 <= float(row.get('duration') or 0) <= 1200
        ]
        analyzed = [row for row in candidates if row['id'] in vectors]
        selected = []
        if seed_id:
            base.require(request, 'similarity')
            seed = next(
                (row for row in candidates if row['id'] == seed_id), None
            )
            if seed is None:
                raise HTTPException(404, 'Ce titre n’est plus accessible.')
            if seed_id not in vectors:
                raise HTTPException(
                    503, 'L’analyse de ce titre est en préparation.'
                )
            selected = (
                [] if payload.skip_seed else [seed]
            ) + base.current_sources(
                rank(
                    [row for row in analyzed if row['id'] != seed_id],
                    vectors,
                    target=vectors[seed_id],
                    limit=payload.count
                    if payload.skip_seed
                    else payload.count - 1,
                    rotation=payload.request_id,
                )
            )
            if len(selected) < 2:
                raise HTTPException(
                    503,
                    'Pas encore assez de titres analysés pour cette similarité.',
                )
        elif prompt and len(analyzed) >= 2:
            import numpy as np

            selected = base.current_sources(
                rank(
                    analyzed,
                    vectors,
                    target=np.frombuffer(prompt['vector'], dtype='<f4'),
                    limit=payload.count,
                    rotation=payload.request_id,
                )
            )
        if len(selected) >= 2:
            basis = 'audio_similarity'
        else:
            selected = local_pool(
                candidates, payload.count, payload.request_id
            )
            basis = 'dj_analysis'
        ids = [row['id'] for row in selected]
    if len(set(ids)) < 2 or (
        not payload.queue_order and len(set(ids)) != len(ids)
    ):
        raise HTTPException(
            422, 'Choisissez au moins deux titres locaux distincts.'
        )
    sources = visible(request, ids, sources=True)
    try:
        session = database().create(
            uid,
            payload.mode,
            payload.theme,
            ids,
            sources,
            nonce=payload.request_id,
            validation=validation,
            request_intent=request_intent,
            selection_basis=basis,
            queue_order=payload.queue_order,
            continuous=payload.continuous,
            seed_id='' if payload.skip_seed else seed_id,
            trial=payload.trial,
            style=payload.style,
        )
    except CancelledDjRequest:
        raise HTTPException(410, 'Cette création DJ a été annulée.') from None
    except PermissionError:
        raise HTTPException(409, 'Cette fonction est désactivée.') from None
    except ValueError:
        raise HTTPException(
            422, 'Sélection ou identifiant de demande invalide.'
        ) from None
    except RuntimeError:
        raise HTTPException(429, 'Deux sets sont déjà en attente.') from None
    if session['state'] == 'deleted':
        raise HTTPException(
            410, 'Ce set a été supprimé. Créez une nouvelle demande.'
        )
    return public(session, visible_session(request, session))


class Command(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str = Field(min_length=1, max_length=128)
    action: Literal['pause', 'resume', 'next', 'replace', 'theme']
    payload: dict[str, str] = Field(default_factory=dict, max_length=1)


@router.delete('/requests/{nonce}')
def cancel_creation(nonce: str, request: Request):
    from . import routes as base

    uid = base.owner(request)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', nonce):
        raise HTTPException(422, 'Identifiant de création invalide.')
    database().cancel_request(uid, nonce)
    return {'ok': True}


@router.post('/sessions/{identity}/commands', status_code=202)
def command(identity: str, payload: Command, request: Request):
    session = owned(request, identity)
    visible_session(request, session)
    try:
        return database().command(
            session['owner'],
            identity,
            payload.request_id,
            payload.action,
            payload.payload,
        )
    except PermissionError:
        raise HTTPException(
            409, 'Le module interactif est désactivé.'
        ) from None
    except RuntimeError:
        raise HTTPException(
            409, 'Le rendu interactif n’est pas actif.'
        ) from None
    except ValueError:
        raise HTTPException(422, 'Commande ou titre invalide.') from None


class Continuity(BaseModel):
    model_config = ConfigDict(extra='forbid')
    position: float = Field(ge=0, le=1_000_000, allow_inf_nan=False)
    sequence: int = Field(ge=0, le=1_000_000, strict=True)
    interruptions: int = Field(default=0, ge=0, le=1_000_000, strict=True)


@router.post('/sessions/{identity}/validation')
def continuity(identity: str, payload: Continuity, request: Request):
    from . import routes as base
    from .dj_validation import receive

    base.admin(request)
    session = owned(request, identity)
    visible_session(request, session)
    try:
        proof = receive(
            base.store(),
            session,
            payload.position,
            payload.sequence,
            interruptions=payload.interruptions,
        )
    except ValueError:
        raise HTTPException(422, 'Position de validation invalide.') from None
    except PermissionError:
        raise HTTPException(
            409, 'Cette validation n’est pas active.'
        ) from None
    return {
        key: proof.get(key, 0)
        for key in (
            'continuous_seconds',
            'interruptions',
            'total_interruptions',
            'render_speed',
            'reset_counts',
        )
    }


@router.get('/sessions/{identity}/hls/{filename}')
def hls(identity: str, filename: str, request: Request):
    from . import routes as base

    session = owned(request, identity)
    visible_session(request, session)
    if session['mode'] != 'interactive' or session['state'] not in {
        'playing',
        'paused',
        'ready',
    }:
        raise HTTPException(409, 'Le flux interactif n’est pas prêt.')
    if filename != 'index.m3u8' and not re.fullmatch(
        r'segment-[0-9]{8}\.ts', filename
    ):
        raise HTTPException(404, 'Segment indisponible.')
    cache = base.store().path.resolve().parent / 'dj'
    workspace, target = cache / identity, cache / identity / filename
    if (
        cache.is_symlink()
        or workspace.is_symlink()
        or target.is_symlink()
        or not target.is_file()
        or not target.resolve().is_relative_to(cache.resolve())
    ):
        raise HTTPException(404, 'Segment indisponible.')
    headers = {
        'Cache-Control': 'private, no-store',
        'X-Content-Type-Options': 'nosniff',
    }
    if filename == 'index.m3u8':
        if target.stat().st_size > 32768:
            raise HTTPException(503, 'Manifeste indisponible.')
        content = target.read_text(encoding='utf-8')
        for line in content.splitlines():
            if (
                line
                and not line.startswith('#')
                and not re.fullmatch(r'segment-[0-9]{8}\.ts', line)
            ) or 'URI=' in line:
                raise HTTPException(503, 'Manifeste indisponible.')
        database().consumer(session['owner'], identity)
        return Response(
            content,
            media_type='application/vnd.apple.mpegurl',
            headers=headers,
        )
    if target.stat().st_size > 1024**2:
        raise HTTPException(503, 'Segment indisponible.')
    return FileResponse(target, media_type='video/mp2t', headers=headers)


@router.get('/sessions')
def sessions(request: Request, summary: bool = False):
    from . import routes as base

    uid = base.owner(request)
    flags = base.store().effective(uid)
    result = []
    for session in database().list(uid):
        if not flags['dj_' + session['mode']]:
            continue
        if summary:
            item = public({**session, 'ids': [], 'timeline': []}, {})
            item['track_count'] = len(session.get('ids', []))
            result.append(item)
            continue
        try:
            result.append(public(session, visible_session(request, session)))
        except HTTPException as error:
            if error.status_code != 404:
                raise
    return {'sessions': result}


@router.get('/sessions/{identity}')
def status(
    identity: str,
    request: Request,
    view: Literal['full', 'playback'] = 'full',
    position: float | None = None,
):
    session = owned(request, identity)
    from .dj_refill import schedule

    schedule(request, session)
    if view == 'full':
        return public(session, visible_session(request, session))
    import math

    if position is not None and (
        not math.isfinite(position) or not 0 <= position <= 1_000_000
    ):
        raise HTTPException(422, 'Position de lecture invalide.')
    timeline = session.get('timeline', [])
    clock = position if position is not None else session.get('position', 0)
    index = max(
        (i for i, row in enumerate(timeline) if row.get('start', 0) <= clock),
        default=0,
    )
    window = timeline[max(0, index - 1) : index + 4]
    ids = list(dict.fromkeys(row['id'] for row in window))
    if not timeline:
        ids = session.get('ids', [])[:4]
    slim = {**session, 'ids': ids, 'timeline': window}
    value = public(
        slim,
        visible(
            request,
            ids,
            known_paths=database().source_paths(session['owner'], identity),
        ),
    )
    # Running wall clocks do not invalidate an otherwise identical playback plan.
    stable = {
        key: item
        for key, item in value.items()
        if key
        not in {'updated', 'position', 'rendered', 'progress', 'render_speed'}
    }
    etag = (
        '"'
        + hashlib.sha256(
            json.dumps(stable, sort_keys=True).encode()
        ).hexdigest()
        + '"'
    )
    headers = {
        'ETag': etag,
        'Cache-Control': 'private, no-cache',
        'Vary': 'Authorization, Cookie',
    }
    if request.headers.get('if-none-match') == etag:
        return Response(status_code=304, headers=headers)
    from fastapi.responses import JSONResponse

    return JSONResponse(value, headers=headers)


@router.delete('/sessions/{identity}')
def stop(identity: str, request: Request):
    from . import routes as base

    # Stopping remains available even after a module has been switched off.
    uid = base.owner(request)
    try:
        database().stop(uid, identity)
    except LookupError:
        raise HTTPException(404, 'Set DJ indisponible.') from None
    return {'ok': True}


@router.get('/sessions/{identity}/media')
def media(identity: str, request: Request):
    from . import routes as base

    session = owned(request, identity)
    visible_session(request, session)
    if session['mode'] != 'prepared' or session['state'] != 'ready':
        raise HTTPException(409, 'Le set n’est pas prêt.')
    cache = base.store().path.resolve().parent / 'dj'
    workspace = cache / identity
    target = workspace / 'set.m4a'
    if (
        cache.is_symlink()
        or workspace.is_symlink()
        or target.is_symlink()
        or not target.is_file()
        or not target.resolve().is_relative_to(cache.resolve())
    ):
        raise HTTPException(404, 'Le fichier de ce set n’est plus disponible.')
    return FileResponse(
        target,
        media_type='audio/mp4',
        headers={
            'Cache-Control': 'private, no-store',
            'X-Content-Type-Options': 'nosniff',
        },
    )


@router.delete('/sessions/{identity}/cache', status_code=202)
def discard(identity: str, request: Request):
    from . import routes as base

    try:
        database().discard(base.owner(request), identity)
    except LookupError:
        raise HTTPException(404, 'Set DJ indisponible.') from None
    return {'state': 'deleting'}
