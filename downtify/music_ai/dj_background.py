"""Low-priority weekly renders share the lease without preempting native work."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

from .playlists import PARIS, period
from .store import DEFAULTS


class BackgroundDeferred(RuntimeError):
    pass


def weekly_period(now=None):
    now = now or datetime.now(PARIS)
    if now.tzinfo is None:
        raise ValueError('An aware weekly clock is required')
    return period('weekly', now - timedelta(minutes=15))


def workspace(identity, token):
    return hashlib.sha256(f'{identity}:{token}'.encode()).hexdigest()[:32]


def allowed(db, owner, document, *, now):
    if document.get('weekly_period') != weekly_period(
        datetime.fromtimestamp(now, PARIS)
    ):
        return False
    flags = {
        row[0]: {**DEFAULTS, **json.loads(row[1])}
        for row in db.execute(
            'SELECT owner,value FROM preferences WHERE owner IN (-1,?)',
            (owner,),
        )
    }
    if not all(
        flags.get(uid, DEFAULTS)[key]
        for uid in (-1, owner)
        for key in ('dj_prepared', 'dj_weekly', 'weekly')
    ):
        return False
    revisions = {
        row[0]: json.loads(row[1])
        for row in db.execute(
            'SELECT key,value FROM metadata WHERE key IN (?,?,?)',
            (
                f'profile_revision:{owner}',
                f'selection_revision:{owner}',
                'analysis_generation',
            ),
        )
    }
    return document.get('analysis_generation', 0) == revisions.get(
        'analysis_generation', 0
    ) and all(
        document.get(key, 0) == revisions.get(f'{key}:{owner}', 0)
        for key in ('profile_revision', 'selection_revision')
    )


def blocked(db):
    values = db.execute(
        "SELECT value FROM metadata WHERE key IN ('native_busy','analysis_paused')"
    )
    if any(json.loads(row[0]) for row in values):
        return True
    return (
        db.execute(
            "SELECT 1 FROM dj_sessions WHERE state='queued' AND COALESCE(json_extract(document,'$.background'),0)!=1 LIMIT 1"
        ).fetchone()
        is not None
    )
