"""Catch-up scheduler. A missed morning run is generated on the next pass."""

from __future__ import annotations

from .playlists import generate, period
from .store import MOODS


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
            missing = set(MOODS) - existing
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


def native_sweep():
    from fastapi import Request

    from .. import api
    from ..auth import ADMIN, USER, Principal
    from .routes import catalog, store

    status = store().metadata('model', {})
    if not status.get('ready') or store().metadata('native_busy', False):
        return
    if api.state.auth is None:
        return

    def user_for(uid):
        return api.state.auth.users.get(uid)

    ticket = None

    def rows_for(uid):
        nonlocal ticket
        from .compute_budget import acquire

        if ticket is None:
            ticket = acquire(store(), 'analysis')
            if ticket is None:
                return []
        user = user_for(uid)
        if user is None:
            return []
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
        return catalog(request)

    try:
        refresh_due(
            store(),
            status['id'],
            user_for,
            rows_for,
            checkpoint=lambda: ticket is None or ticket.renew(),
        )
    finally:
        if ticket is not None:
            ticket.release()
