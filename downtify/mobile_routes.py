"""The API the Downtify apps use: ``/api/v1``.

Separate from the web app's routes (whose shapes the web app depends on
and which don't change) so this surface can be versioned on its own -
``api_version`` in ``GET /api/server/info`` says which one a server
speaks. Everything is addressed by **track id** (see
:mod:`downtify.library_sync`), never by file path. The full contract,
from discovery to reporting plays, is ``docs/mobile-client-contract.md``.
"""

from __future__ import annotations

import asyncio
import mimetypes
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from loguru import logger

from . import api
from .auth import SIGNED_URL_DEFAULT_TTL, SIGNED_URL_MAX_TTL, Principal
from .cover_thumbs import normalize_size
from .library_catalog import list_library_entries, resolve_library_file
from .library_paths_cache import invalidate_library_paths_cache
from .lyrics import read_track_lyrics
from .transcode import (
    FORMATS,
    TranscodeError,
    normalize_bitrate,
    serve_original,
)

router = APIRouter(prefix='/api/v1')

#: How long a phone may keep an audio file or cover without asking again.
_PRIVATE_CACHE = 'private, max-age=604800'


def _sync():
    if api.state.library_sync is None:
        raise HTTPException(status_code=503, detail='Starting up')
    return api.state.library_sync


def _refresh() -> int:
    """Bring the track ids in line with what's on disk; the new cursor."""

    return _sync().refresh(list_library_entries(api.library_context()))


def _track_path(track_id: str) -> tuple[dict[str, Any], Path]:
    """A track's row and file, or 404."""

    sync = _sync()
    row = sync.row_for(track_id)
    if row is None:
        _refresh()
        row = sync.row_for(track_id)
    if row is None:
        raise HTTPException(status_code=404, detail='Track not found')
    full = resolve_library_file(row['file'], api.library_context())
    if full is None:
        raise HTTPException(status_code=404, detail='File not found')
    return row, full


# ── The library ─────────────────────────────────────────────────────────


@router.get('/library')
async def library(
    request: Request,
    response: Response,
    since: int = Query(0, ge=0),
    refresh: bool = Query(False),
) -> Any:
    """Tracks added or changed since *since*, and ids of tracks removed.

    ``{cursor, full, tracks, deleted}``; keep ``cursor`` for next time.
    ``full: true`` means ``tracks`` is the whole library (a first sync, or
    a cursor too old to answer): replace everything you have with it.
    The folder scan behind it is cached for a minute or so;
    ``refresh=true`` (pull to refresh) rescans now - for files added to
    the folder by something other than Downtify.
    """

    if refresh:
        invalidate_library_paths_cache(notify=False, drop_entries=True)
    before = await asyncio.to_thread(_sync().cursor)
    cursor = await asyncio.to_thread(_refresh)
    if cursor != before:
        # Found something new on disk: other apps should sync too.
        api.announce_library_changed()
    allowed = api.allowed_entry_keys(request)
    scope = 'a' if allowed is None else api.request_user_id(request)
    etag = f'"lib-{cursor}-{since}-{scope}"'
    if request.headers.get('if-none-match') == etag:
        return Response(status_code=304, headers={'ETag': etag})
    response.headers['ETag'] = etag
    response.headers['Cache-Control'] = 'private, no-cache'
    return await asyncio.to_thread(
        _sync().changes, since, allowed_keys=allowed
    )


@router.get('/tracks/{track_id}')
def track(track_id: str) -> dict[str, Any]:
    row, _full = _track_path(track_id)
    return row


@router.get('/tracks/{track_id}/lyrics')
def track_lyrics(track_id: str) -> dict[str, Any]:
    """``{synced, plain}``: the ``.lrc`` sidecar and the embedded lyrics."""

    _row, full = _track_path(track_id)
    return read_track_lyrics(full)


@router.get('/playlists')
async def playlists(request: Request) -> list[dict[str, Any]]:
    """Downloaded playlists as ``{name, liked, manual, count, track_ids,
    cover, owner, visibility, mine, followed, shared_with_me, new,
    hidden_count}`` - ``cover`` is a path for ``GET /playlist-cover?file=``
    or ``''``; ``hidden_count`` is how many songs the owner hid from an
    imported playlist (``0`` for everything else).

    A user sees their own playlists (and their own liked songs as the
    liked one), those shared with them (``shared_with_me``; ``new`` until
    opened) and public ones: the ones they follow, and - unless they
    switched *Show public playlists* off - the rest. ``mine`` says whether
    it is theirs to change, ``owner`` is the owner's username and
    ``visibility`` is ``private``, ``shared`` or ``public``. Own playlists
    also list ``shared_with`` (usernames).
    """

    await asyncio.to_thread(_refresh)
    found = await asyncio.to_thread(api.playlists_for_request, request)
    paths = [f for p in found for f in p['files']]
    ids = await asyncio.to_thread(_sync().ids_for_paths, paths)
    return [
        {
            'name': p['name'],
            'display_name': p.get('display_name', p['name']),
            'liked': p['liked'],
            'manual': bool(p.get('manual')),
            'count': p['count'],
            'cover': p['cover'],
            'track_ids': [ids[f] for f in p['files'] if f in ids],
            'owner': p.get('owner', ''),
            'visibility': p.get('visibility', 'private'),
            'mine': bool(p.get('mine', True)),
            'followed': bool(p.get('followed')),
            'favorite': bool(p.get('favorite')),
            'shared_with_me': bool(p.get('shared_with_me')),
            'new': bool(p.get('new')),
            'hidden_count': int(p.get('hidden_count') or 0),
            **(
                {'shared_with': p['shared_with']}
                if p.get('shared_with')
                else {}
            ),
        }
        for p in found
    ]


@router.get('/usernames')
async def usernames(request: Request) -> dict[str, Any]:
    """``{enabled, usernames}``: who a playlist can be shared with
    (everyone but you) - names only, since users can't list accounts.
    ``enabled`` is the admin's *Allow users to share playlists*."""

    me = api.request_user_id(request)
    enabled = api.sharing_enabled()
    names = sorted(
        (name for uid, name in api._usernames().items() if uid != me),
        key=str.casefold,
    )
    return {'enabled': enabled, 'usernames': names if enabled else []}


@router.get('/tracks/{track_id}/loudness')
async def track_loudness(track_id: str, request: Request) -> dict[str, Any]:
    """The track's playback loudness profile (see downtify/loudness.py)."""

    row, _ = await asyncio.to_thread(_track_path, track_id)
    return await api.track_loudness(request, str(row['file']))


@router.put('/playlists/favorite')
async def favorite_playlist(request: Request) -> dict[str, Any]:
    """Set the same account preference as the web player."""
    return await api.set_playlist_favorite_endpoint(request)


async def _playlist_name(request: Request) -> str:
    name = request.query_params.get('name', '')
    if not name:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        name = str((payload or {}).get('name') or '')
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail='name is required')
    return name


def _shares():
    if api.state.playlist_shares is None:
        raise HTTPException(status_code=503, detail='Starting up')
    return api.state.playlist_shares


@router.post('/playlists/follow')
async def follow_playlist(request: Request) -> dict[str, Any]:
    """Follow a public playlist (``{name}``): it stays in your list and
    follows its owner's changes, until they make it private."""

    name = await _playlist_name(request)
    user_id = api.request_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail='Sign in required')
    entry = api.require_playlist_visible(name, request)
    if entry.get('mine') or entry.get('visibility') != 'public':
        raise HTTPException(
            status_code=400, detail='Only public playlists can be followed'
        )
    await asyncio.to_thread(_shares().follow, user_id, entry['name'], True)
    await api.announce_playlists_changed()
    return {'name': entry['name'], 'followed': True}


@router.delete('/playlists/follow')
async def unfollow_playlist(request: Request) -> dict[str, Any]:
    """Stop following a playlist (``?name=``). Idempotent."""

    name = await _playlist_name(request)
    user_id = api.request_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail='Sign in required')
    await asyncio.to_thread(_shares().follow, user_id, name, False)
    await api.announce_playlists_changed()
    return {'name': name, 'followed': False}


@router.post('/playlists/seen')
async def playlist_seen(request: Request) -> dict[str, Any]:
    """Clear the *new* marker of a playlist shared with you (``{name}``)."""

    name = await _playlist_name(request)
    user_id = api.request_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail='Sign in required')
    await asyncio.to_thread(_shares().mark_seen, name, user_id)
    return {'name': name, 'new': False}


@router.get('/playlists/hidden')
async def hidden_songs(request: Request) -> dict[str, Any]:
    """The songs hidden from an imported playlist of yours (``?name=``),
    most recently hidden first: ``{name, songs: [{key, label, track_id,
    hidden_at}]}``. ``track_id`` is ``''`` once the song's file is no
    longer in the library; ``key`` is what ``show`` takes."""

    name = await _playlist_name(request)
    found = await asyncio.to_thread(api.hidden_playlist_songs, name, request)
    files = [song['file'] for song in found['songs'] if song['present']]
    ids = await asyncio.to_thread(_sync().ids_for_paths, files)
    return {
        'name': found['name'],
        'songs': [
            {
                'key': song['key'],
                'label': song['label'],
                'track_id': ids.get(song['file'], '')
                if song['present']
                else '',
                'hidden_at': song['hidden_at'],
            }
            for song in found['songs']
        ],
    }


@router.post('/playlists/hidden')
async def change_hidden_songs(request: Request) -> dict[str, Any]:
    """Hide tracks from an imported playlist of yours, or show hidden
    songs again: ``{name, hide: [track_ids], show: [keys]}``. A hidden
    song leaves the playlist and stays out when its watch or link brings
    it back; the track itself stays in the library. Answers ``{name,
    hidden, keys, shown, restored, count, track_ids}``: ``keys`` undo the
    hide (pass them as ``show``), ``track_ids`` are the playlist's tracks
    after the change."""

    try:
        payload = await request.json()
    except Exception:
        payload = {}
    payload = payload if isinstance(payload, dict) else {}
    name = str(payload.get('name') or '').strip()
    if not name:
        raise HTTPException(status_code=400, detail='name is required')
    paths = [
        (await asyncio.to_thread(_track_path, str(track_id)))[0]['file']
        for track_id in _strings(payload.get('hide'))
    ]
    result = await api.change_hidden_playlist_songs(
        request, name, paths, _strings(payload.get('show'))
    )
    files = list(result.get('files') or [])
    ids = await asyncio.to_thread(_sync().ids_for_paths, files)
    return {
        'name': result['name'],
        'hidden': result['hidden'],
        'keys': result['keys'],
        'shown': result['shown'],
        'restored': result['restored'],
        'count': len(files),
        'track_ids': [ids[f] for f in files if f in ids],
    }


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or '').strip()]


@router.get('/likes')
async def likes(request: Request) -> dict[str, Any]:
    """The liked tracks, most recently liked first: ``{track_ids}``."""

    store = api.state.likes
    if store is None:
        raise HTTPException(status_code=503, detail='Starting up')
    paths = await asyncio.to_thread(store.paths, api.likes_scope(request))
    ids = await asyncio.to_thread(_sync().ids_for_paths, paths)
    return {'track_ids': [ids[p] for p in paths if p in ids]}


@router.put('/likes')
async def set_like(request: Request) -> dict[str, Any]:
    """Like or unlike a track: ``{track_id, liked}``. Idempotent."""

    try:
        payload = await request.json()
    except Exception:
        payload = {}
    track_id = str((payload or {}).get('track_id') or '')
    if not track_id:
        raise HTTPException(status_code=400, detail='track_id is required')
    row = await asyncio.to_thread(_sync().row_for, track_id)
    if row is None:
        raise HTTPException(status_code=404, detail='Track not found')
    liked = bool(payload.get('liked', True))
    result = await api.apply_like(
        row['file'], liked, user_id=api.request_user_id(request)
    )
    await api.log_activity(request, 'like' if liked else 'unlike', row['file'])
    return {'track_id': track_id, 'liked': result['liked']}


# ── Streaming ───────────────────────────────────────────────────────────

# Players (Android's included) want the registered types, not the
# ``audio/x-flac`` some systems' mime tables give.
_AUDIO_TYPES = {
    '.mp3': 'audio/mpeg',
    '.flac': 'audio/flac',
    '.m4a': 'audio/mp4',
    '.mp4': 'audio/mp4',
    '.ogg': 'audio/ogg',
    '.opus': 'audio/ogg',
    '.wav': 'audio/wav',
}


def audio_media_type(path: Path) -> str:
    return (
        _AUDIO_TYPES.get(path.suffix.lower())
        or mimetypes.guess_type(path.name)[0]
        or 'application/octet-stream'
    )


def _download_name(row: dict[str, Any], extension: str) -> str:
    base = Path(row['file']).stem
    return f"attachment; filename*=UTF-8''{quote(base + extension)}"


async def _wait_or_disconnect(
    request: Request, job: asyncio.Future[Path]
) -> Optional[Path]:
    """The job's result, or ``None`` when the client went away first (the
    job is then cancelled, which stops ffmpeg if nobody else waits)."""

    while True:
        done, _pending = await asyncio.wait({job}, timeout=0.5)
        if done:
            return job.result()
        if await request.is_disconnected():
            job.cancel()
            return None


@router.api_route('/tracks/{track_id}/stream', methods=['GET', 'HEAD'])
async def stream(
    track_id: str,
    request: Request,
    fmt: str = Query('original', alias='format'),
    bitrate: int = Query(0),
    download: bool = Query(False),
) -> Response:
    """The track's audio, with HTTP Range support.

    ``format=original`` (default) is the file as it is. ``opus``, ``aac``
    or ``mp3`` with a ``bitrate`` (kbps) is a transcoded copy - unless the
    original is already lossy and no bigger than that, in which case the
    original comes back (``X-Downtify-Transcoded: no``). ``download=true``
    adds a ``Content-Disposition`` for saving the file.
    """

    row, full = _track_path(track_id)
    fmt = fmt.lower()
    headers = {'Cache-Control': _PRIVATE_CACHE}
    if fmt != 'original':
        transcoder = api.state.transcoder
        kbps = normalize_bitrate(bitrate) or 160
        if fmt not in FORMATS:
            raise HTTPException(status_code=400, detail='Unknown format')
        if transcoder is None or not transcoder.available:
            raise HTTPException(
                status_code=501, detail='Transcoding is not available'
            )
        if not serve_original(row['codec'], int(row['bitrate']), kbps):
            job = asyncio.ensure_future(transcoder.get(full, fmt, kbps))
            try:
                target = await _wait_or_disconnect(request, job)
            except TranscodeError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc
            if target is None:
                logger.debug(
                    'Stream {}: client left during transcode', track_id
                )
                return Response(status_code=499)
            headers['X-Downtify-Transcoded'] = f'{fmt}/{kbps}'
            if download:
                headers['Content-Disposition'] = _download_name(
                    row, FORMATS[fmt].extension
                )
            return FileResponse(
                target, media_type=FORMATS[fmt].media_type, headers=headers
            )
        headers['X-Downtify-Transcoded'] = 'no'
    if download:
        headers['Content-Disposition'] = _download_name(row, full.suffix)
    return FileResponse(
        full, media_type=audio_media_type(full), headers=headers
    )


@router.api_route('/tracks/{track_id}/cover', methods=['GET', 'HEAD'])
async def cover(
    track_id: str, request: Request, size: str = Query('')
) -> Response:
    """The track's cover: ``size=150|300|600`` (longest side, px) or full
    size when omitted. Cached on the server, ETag for conditional GETs."""

    _row, full = _track_path(track_id)
    thumbs = api.state.cover_thumbs
    if thumbs is None:
        raise HTTPException(status_code=503, detail='Starting up')
    found = await asyncio.to_thread(thumbs.get, full, normalize_size(size))
    if found is None:
        raise HTTPException(status_code=404, detail='No cover')
    data, mime, etag = found
    headers = {'ETag': etag, 'Cache-Control': _PRIVATE_CACHE}
    if request.headers.get('if-none-match') == etag:
        return Response(status_code=304, headers=headers)
    return Response(content=data, media_type=mime, headers=headers)


# ── Signed URLs ─────────────────────────────────────────────────────────

_SIGNABLE = (
    '/api/v1/tracks/',
    '/downloads/',
    '/media/',
    '/cover',
    '/playlist-cover',
)


@router.post('/sign')
async def sign(request: Request) -> dict[str, Any]:
    """Signed URLs for players that can't send the device token (a Cast
    receiver): ``{items: [{path, params}], ttl}`` ->
    ``{urls: [...], expires_at}``. Only for a paired app, and only for
    audio and cover paths; ``ttl`` is seconds (default 1 h, at most 24 h).
    """

    principal: Optional[Principal] = (request.scope.get('state') or {}).get(
        'principal'
    )
    if principal is None or not principal.device_id:
        raise HTTPException(
            status_code=400, detail='Only a paired app can sign URLs'
        )
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    items = (payload or {}).get('items')
    if not isinstance(items, list) or not items or len(items) > 500:
        raise HTTPException(status_code=400, detail='items is required')
    try:
        ttl = int(payload.get('ttl') or SIGNED_URL_DEFAULT_TTL)
    except (TypeError, ValueError):
        ttl = SIGNED_URL_DEFAULT_TTL
    ttl = max(60, min(ttl, SIGNED_URL_MAX_TTL))
    signer = api.state.auth.signer if api.state.auth else None
    if signer is None:
        raise HTTPException(status_code=503, detail='Starting up')
    urls = []
    for item in items:
        path = str((item or {}).get('path') or '')
        params = (item or {}).get('params') or {}
        if not path.startswith(_SIGNABLE) or '..' in path:
            raise HTTPException(
                status_code=400, detail=f'Cannot sign {path!r}'
            )
        if not isinstance(params, dict):
            raise HTTPException(status_code=400, detail='Bad params')
        urls.append(
            signer.sign_url(
                path,
                [(str(k), str(v)) for k, v in params.items()],
                device_id=principal.device_id,
                ttl=ttl,
            )
        )
    return {'urls': urls, 'expires_at': int(time.time()) + ttl}
