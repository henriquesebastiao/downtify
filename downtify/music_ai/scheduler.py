"""Catch-up scheduler. A missed morning run is generated on the next pass."""

from __future__ import annotations

import json
import time

from .playlists import generate, period, themes


def refresh_due(
    database,
    identity,
    user_for,
    rows_for,
    *,
    now=None,
    checkpoint=lambda: True,
):
    with database.connect() as db:
        users = [
            row[0]
            for row in db.execute(
                'SELECT owner FROM preferences WHERE owner>0 UNION SELECT owner FROM listens'
            )
        ]
    created = 0
    for uid in users:
        if not user_for(uid):
            continue
        flags = database.effective(uid)
        rows = None
        for cadence in ('daily', 'weekly'):
            if not flags[cadence]:
                continue
            current = period(cadence, now)
            with database.connect() as db:
                existing = {
                    row[0]
                    for row in db.execute(
                        'SELECT mood FROM playlists WHERE owner=? AND cadence=? AND period=?',
                        (uid, cadence, current),
                    )
                }
            missing = set(themes(cadence)) - existing
            if not missing:
                continue
            if rows is None:
                rows = rows_for(uid)
            if not rows:
                continue
            for mood in sorted(missing):
                if not checkpoint():
                    return created
                try:
                    generate(
                        database, uid, cadence, mood, rows, identity, now=now
                    )
                except (RuntimeError, PermissionError):
                    continue  # Do not freeze an empty playlist during initial indexing.
                created += 1
    return created


def dj_owns_compute(database, *, now=None):
    """True while a DJ request waits for or holds the shared compute lease."""
    now = time.time() if now is None else now
    with database.connect() as db:
        waiting = db.execute(
            "SELECT value FROM metadata WHERE key='compute_dj_waiting'"
        ).fetchone()
        if waiting and json.loads(waiting[0]) > now:
            return True
        lease = db.execute(
            'SELECT kind FROM compute_lease WHERE id=1 AND expires>?', (now,)
        ).fetchone()
    return bool(lease) and lease[0] == 'dj'


def native_sweep():
    from fastapi import HTTPException, Request

    from .. import api
    from ..auth import ADMIN, USER, Principal
    from .routes import catalog, favorite_ids, store

    status = store().metadata('model', {})
    if not status.get('ready') or store().metadata('native_busy', False):
        return
    if api.state.auth is None:
        return
    # Ranking is a bounded read, not model inference: it no longer waits for the
    # analysis worker's long lease, which used to starve the morning mixes for
    # hours. A DJ request still keeps priority; the next minute retries.
    if dj_owns_compute(store()):
        return

    def user_for(uid):
        return api.state.auth.users.get(uid)

    def request_for(uid):
        user = user_for(uid)
        if user is None:
            return None
        role = str(user.get('role') or 'user')
        principal = Principal(
            'internal',
            ADMIN if role == 'admin' else USER,
            '',
            uid,
            user.get('username', ''),
            role,
        )
        request = Request({
            'type': 'http',
            'method': 'GET',
            'path': '/internal/music-ai',
            'headers': [],
            'state': {'principal': principal},
        })
        return request

    def rows_for(uid):
        request = request_for(uid)
        if request is None:
            return []
        rows = catalog(request)
        favorites = favorite_ids(request, rows)
        return [{**row, 'favorite': row['id'] in favorites} for row in rows]

    refresh_due(store(), status['id'], user_for, rows_for)

    from .dj_routes import visible
    from .dj_weekly import enqueue_due

    def sources_for(uid, ids):
        request = request_for(uid)
        if request is None:
            return {}
        try:
            return visible(request, ids, sources=True)
        except HTTPException:
            return {}

    enqueue_due(store(), user_for, rows_for, sources_for)
