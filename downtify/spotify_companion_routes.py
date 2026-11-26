"""``/api/companion``: the Spotify companion (downtify/spotify_companion.py).

The companion is a browser extension, signed in to Downtify with a
paired-app key; your Spotify sign-in stays in its browser.

* ``GET  /api/companion`` - admins: settings, health, slots, mixes.
* ``PUT  /api/companion`` - admins: change the settings.
* ``POST /api/companion/account`` - admins: read for the Spotify account
  the companion is signed in to now (after "another account").
* ``POST /api/companion/extension`` - admins: the extension as a ZIP,
  with a new key and this server's address filled in.
* ``GET  /api/companion/watches`` - which watches it reads, and how they
  stand (the Monitor page's badges).
* ``POST /api/companion/poll`` - the companion: "here is how I am, what
  should I read?" -> ``{job}`` or ``{wait_seconds}``.
* ``POST /api/companion/result`` - the companion: the songs it read (raw
  ``fetchPlaylist`` items) or why it couldn't.
"""

from __future__ import annotations

import asyncio
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import Response
from loguru import logger

from . import (
    api,
    auth_routes,
    notifications,
    spotify,
    spotify_companion,
    spotify_companion_agent,
)
from .monitor import (
    KIND_PLAYLIST,
    SOURCE_SPOTIFY,
    MonitoredPlaylist,
    check_watch,
)
from .spotify_companion import Store, Watch

router = APIRouter(prefix='/api/companion')

EXTENSION_DIR = Path(__file__).parent / 'companion_extension'
#: Seconds between two looks at the companion's health.
TICK_SECONDS = 60
#: Songs one result may carry (a mix has 50; Discover Weekly 30).
MAX_ITEMS = 2000


def _now() -> datetime:
    return datetime.now(timezone.utc)


def store() -> Store:
    """The companion's store, made on first use beside ``settings.json``."""

    found = spotify_companion.current()
    if found is None:
        path = api.state.settings_path
        root = (
            Path(path).parent / spotify_companion.FOLDER_NAME
            if path is not None
            else Path('data') / spotify_companion.FOLDER_NAME
        )
        found = Store(root)
        spotify_companion.set_current(found)
    return found


def _watches() -> list[tuple[MonitoredPlaylist, Watch]]:
    db = api.state.monitor_db
    if db is None:
        return []
    found = []
    for playlist in db.list_playlists():
        if (
            playlist.kind != KIND_PLAYLIST
            or playlist.source != SOURCE_SPOTIFY
            or not spotify_companion.is_personal_mix(playlist.spotify_id)
        ):
            continue
        found.append((
            playlist,
            Watch(
                id=playlist.id,
                playlist_id=playlist.spotify_id,
                name=playlist.name,
                interval_minutes=playlist.interval_minutes,
                last_checked=playlist.last_checked,
                enabled=playlist.enabled,
            ),
        ))
    return found


def _send(notices: list[tuple[str, str]]) -> None:
    for title, text in notices:
        notifications.emit('spotify_companion', title, text)


def _start_check(playlist: MonitoredPlaylist) -> None:
    """Check *playlist* now that the companion has read it: its songs
    come from the companion's copy (see spotify.playlist_tracks_from_id)."""

    downloader = api.state.downloader
    db = api.state.monitor_db
    if downloader is None or db is None:
        return
    loop = api.state.loop or asyncio.get_running_loop()

    async def _run() -> None:
        try:
            count = await check_watch(
                playlist,
                db,
                downloader,
                api.state.connections.broadcast,
                loop,
                api.state.settings,
                api.library_stores(),
                api.state.podcasts,
            )
            if count > 0:
                notifications.emit(
                    'watch_done', playlist.name, f'{count} new song(s)'
                )
        except Exception:
            logger.exception(
                'Spotify companion: check of "{}" failed', playlist.name
            )

    api.spawn_task(_run(), name='companion-check')


# ── The admin's page ────────────────────────────────────────────────


@router.get('')
async def status() -> dict[str, Any]:
    found = store()
    watches = await asyncio.to_thread(_watches)
    summary = await asyncio.to_thread(
        found.summary, _now(), [w for _p, w in watches]
    )
    names = {p.id: p.name for p, _w in watches}
    for watch_id, info in summary['watches'].items():
        info['name'] = names.get(watch_id, '')
    return {'config': found.config, **summary}


@router.put('')
async def save(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    found = store()
    await asyncio.to_thread(found.set_config, body)
    return await status()


@router.post('/account')
async def accept_account() -> dict[str, Any]:
    found = store()
    await asyncio.to_thread(found.accept_account)
    _send(await asyncio.to_thread(found.tick, _now()))
    return await status()


def _extension_zip(config: dict[str, str]) -> bytes:
    """The extension's files at the top of the ZIP: unzipping it (Windows'
    "Extract All" makes a folder named after it) gives the very folder to
    choose in "Load unpacked". Its manifest lets it reach the Downtify
    address in ``config.json`` from the start, so it works without anyone
    clicking Save (a headless browser has nobody to click)."""

    buffer = io.BytesIO()
    origin = spotify_companion_agent.origin_of(config.get('downtify_url', ''))
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(EXTENSION_DIR.rglob('*')):
            if not path.is_file() or path.name == 'config.json':
                continue
            name = path.relative_to(EXTENSION_DIR).as_posix()
            if name == 'manifest.json' and origin:
                manifest = json.loads(path.read_text(encoding='utf-8'))
                manifest['host_permissions'] = [
                    *manifest.get('host_permissions', []),
                    f'{origin}/*',
                ]
                archive.writestr(name, json.dumps(manifest, indent=2))
            else:
                archive.write(path, name)
        archive.writestr('config.json', json.dumps(config, indent=2))
    return buffer.getvalue()


def _zip_response(data: bytes) -> Response:
    return Response(
        content=data,
        media_type='application/zip',
        headers={
            'Content-Disposition': (
                'attachment; filename="downtify-companion.zip"'
            ),
            'Cache-Control': 'no-store',
        },
    )


@router.post('/extension')
async def extension(request: Request) -> Response:
    """The extension, ready to load: a new key (listed under Paired apps
    as "Spotify companion", where it can be revoked) and this server's
    address are in its ``config.json``."""

    auth = auth_routes._store()
    me = auth_routes._me(request)
    user = await asyncio.to_thread(auth.users.get, me.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail='Sign in required')
    made = await auth_routes._new_device(
        {'device_name': 'Spotify companion', 'platform': 'spotify-companion'},
        user,
        auth_routes._ip(request),
        None,
    )
    address = str(request.base_url).rstrip('/')
    data = await asyncio.to_thread(
        _extension_zip, {'downtify_url': address, 'key': made['token']}
    )
    return _zip_response(data)


# ── Setting up with an AI agent ─────────────────────────────────────

agent_tickets = spotify_companion_agent.Tickets()


@router.post('/agent')
async def agent_setup(request: Request) -> dict[str, Any]:
    """A setup link (a day) and instructions for an AI agent on the server
    (see downtify/spotify_companion_agent.py)."""

    me = auth_routes._me(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    base = str(request.base_url).rstrip('/')
    address = (
        spotify_companion_agent.origin_of(
            (body or {}).get('address') if isinstance(body, dict) else ''
        )
        or base
    )
    now = _now()
    token, ticket = agent_tickets.make(me.user_id, address, now)
    return {
        'instructions': spotify_companion_agent.instructions(
            base, address, token, ticket.expires
        ),
        'expires_at': ticket.expires.isoformat(),
    }


def _ticket(token: str) -> spotify_companion_agent.Ticket:
    found = agent_tickets.get(token, _now())
    if found is None:
        raise HTTPException(
            status_code=404,
            detail='This setup link has expired: make a new one in Downtify',
        )
    return found


@router.get('/agent/{token}/extension.zip')
async def agent_extension(
    token: str, request: Request, address: str = ''
) -> Response:
    ticket = _ticket(token)
    target = spotify_companion_agent.origin_of(address) or ticket.address
    if not ticket.key:
        auth = auth_routes._store()
        user = await asyncio.to_thread(auth.users.get, ticket.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail='No such account')
        made = await auth_routes._new_device(
            {
                'device_name': 'Spotify companion (AI setup)',
                'platform': 'spotify-companion',
            },
            user,
            auth_routes._ip(request),
            None,
        )
        ticket.key = made['token']
    ticket.downloads += 1
    data = await asyncio.to_thread(
        _extension_zip, {'downtify_url': target, 'key': ticket.key}
    )
    return _zip_response(data)


@router.get('/agent/{token}/status')
async def agent_status(token: str) -> dict[str, Any]:
    """How the companion is doing, for the agent: no names, no keys."""

    _ticket(token)
    found = store()
    pairs = await asyncio.to_thread(_watches)
    summary = await asyncio.to_thread(
        found.summary, _now(), [w for _p, w in pairs]
    )
    health = summary['health']
    return {
        'status': health['status'],
        'message': health['message'],
        'last_check_in': health['seen_at'],
        'extension_version': health['version'],
        'personal_mixes': summary['mixes'],
        'read_today': summary['reads_today'],
    }


# ── The Monitor page ────────────────────────────────────────────────


@router.get('/watches')
async def watches() -> dict[str, Any]:
    found = store()
    if not found.enabled:
        return {
            'enabled': False,
            'status': spotify_companion.OFF,
            'watches': {},
        }
    pairs = await asyncio.to_thread(_watches)
    summary = await asyncio.to_thread(
        found.summary, _now(), [w for _p, w in pairs]
    )
    return {
        'enabled': True,
        'status': summary['health']['status'],
        'watches': {
            str(k): {
                'due': v['due'],
                'last_read': v['last_read'],
                'requested': v['requested'],
                'failed': bool(v['error']),
            }
            for k, v in summary['watches'].items()
        },
    }


# ── The companion itself ────────────────────────────────────────────


@router.post('/poll')
async def poll(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    found = store()
    now = _now()
    _send(await asyncio.to_thread(found.report, now, body))
    pairs = await asyncio.to_thread(_watches)
    decision = await asyncio.to_thread(
        found.plan, now, [w for _p, w in pairs], spotify._GRAPHQL_HASH
    )
    return {**decision, 'enabled': found.enabled}


@router.post('/result')
async def result(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    found = store()
    job_id = str(body.get('job_id') or '')
    error = str(body.get('error') or '')[:300]
    items = body.get('items')
    tracks: Optional[list[dict[str, Any]]] = None
    if not error:
        if not isinstance(items, list) or len(items) > MAX_ITEMS:
            error = 'The companion sent no usable song list'
        else:
            tracks = spotify.tracks_from_graphql_items(items)
            if not tracks:
                # A personal mix is never empty: an empty answer is a
                # glitch, and taking it would empty the playlist here.
                error = 'Spotify sent no songs it could read'
                tracks = None
    try:
        flight, notices = await asyncio.to_thread(
            found.finish,
            _now(),
            job_id,
            tracks=tracks,
            name=str(body.get('name') or '')[:200],
            error=error,
        )
    except spotify_companion.UnknownJob:
        raise HTTPException(
            status_code=409, detail='That read is not the one asked for'
        ) from None
    _send(notices)
    if tracks is not None:
        db = api.state.monitor_db
        playlist = (
            await asyncio.to_thread(db.get_playlist, flight['watch_id'])
            if db is not None
            else None
        )
        if playlist is not None and playlist.enabled:
            _start_check(playlist)
    return {'ok': tracks is not None, 'songs': len(tracks or [])}


# ── Startup ─────────────────────────────────────────────────────────


async def run() -> None:
    """Load the store (so the monitor and the Spotify reader know about
    the companion from the start) and look at its health now and then."""

    found = store()
    while True:
        try:
            _send(await asyncio.to_thread(found.tick, _now()))
        except Exception:
            logger.opt(exception=True).warning('Spotify companion tick failed')
        await asyncio.sleep(TICK_SECONDS)
