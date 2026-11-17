"""The Wanted list: what the artist watches still miss, across artists.

``GET /api/monitor/wanted`` gathers, per enabled artist watch (an admin's
view covers every watch, a user's only their own), the releases the watch
downloads that the library only partly has or lacks, with the tracks
missing in total. It reads what the last sweep and "Check what I have"
kept; nothing is fetched. A release whose tracklist isn't read yet counts
as unchecked: its size is unknown.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Request

from . import api, artist_catalogue
from .monitor import KIND_ARTIST, MonitoredPlaylist, PlaylistMonitorDB

router = APIRouter(prefix='/api/monitor/wanted')


def scoped_artist_watches(
    db: PlaylistMonitorDB, request: Request
) -> list[MonitoredPlaylist]:
    """The enabled artist watches *request* may see: all for an admin,
    their own otherwise."""

    scope = (
        None if api.request_is_admin(request) else api.request_user_id(request)
    )
    return [
        watch
        for watch in db.list_playlists(scope)
        if watch.kind == KIND_ARTIST and watch.enabled
    ]


def wanted_view(
    db: PlaylistMonitorDB, watches: list[MonitoredPlaylist]
) -> dict[str, Any]:
    """The wanted releases of *watches*, grouped by artist (by name).

    The library is read once for all of them. An artist with nothing
    wanted and nothing unread is left out."""

    artists: list[dict[str, Any]] = []
    if watches:
        index = api._library_songs()
        for watch in watches:
            view = api._artist_releases(db, watch, songs=index)
            releases = artist_catalogue.wanted_releases(view['releases'])
            missing = view['missing']
            if not releases and not missing['unread']:
                continue
            artists.append({
                'watch': view['watch'],
                'releases': releases,
                'missing': missing,
                'checking': bool(view['checking']),
            })
    artists.sort(key=lambda a: str(a['watch']['name']).casefold())
    return {
        'artists': artists,
        'totals': {
            'tracks': sum(a['missing']['tracks'] for a in artists),
            'releases': sum(a['missing']['releases'] for a in artists),
            'artists': len(artists),
            'unchecked': sum(1 for a in artists if a['missing']['unread']),
        },
    }


@router.get('')
async def wanted(request: Request) -> dict[str, Any]:
    """What the artist watches still miss; ``job`` is the running or last
    "download all" (``None`` when there is none)."""

    db = api._require_monitor_db()
    watches = await asyncio.to_thread(scoped_artist_watches, db, request)
    view = await asyncio.to_thread(wanted_view, db, watches)
    return {**view, 'job': None}
