"""Metadata-only catch-up scheduler; audio belongs to the low-priority worker."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from .dj_background import blocked, weekly_period
from .dj_store import DjStore
from .playlists import PARIS
from .store import GENRE_THEMES, MOODS

THEMES = (*GENRE_THEMES, *MOODS)
DJ_THEME = {
    'rap': 'energie',
    'rock': 'energie',
    'electro': 'fete',
    'pop': 'energie',
}


def enqueue_due(database, user_for, rows_for, sources_for, *, now=None):
    now = now or datetime.now(PARIS)
    timestamp = now.timestamp()
    flags = database.preferences(-1)
    if not all(flags[key] for key in ('dj_weekly', 'dj_prepared', 'weekly')):
        return 0
    status = database.metadata('dj', {})
    if (
        status.get('weekly_protocol') != 1
        or not status.get('prepared_ready')
        or not 0 <= timestamp - status.get('seen', 0) <= 20
    ):
        return 0
    dj = DjStore(database)
    with database.connect() as db:
        if (
            blocked(db)
            or db.execute(
                "SELECT 1 FROM dj_sessions WHERE COALESCE(json_extract(document,'$.background'),0)=1 AND state IN ('queued','preparing','rendering') LIMIT 1"
            ).fetchone()
        ):
            return 0
        users = [
            row[0]
            for row in db.execute(
                'SELECT owner FROM preferences WHERE owner>0 ORDER BY owner'
            )
        ]
    last = database.metadata('weekly_last_owner', 0)
    users.sort(key=lambda uid: (uid <= last, uid))
    week = weekly_period(now)
    for uid in users:
        if not user_for(uid) or not all(
            database.effective(uid)[key]
            for key in ('dj_weekly', 'dj_prepared', 'weekly')
        ):
            continue
        revision = {
            'profile_revision': database.metadata(
                f'profile_revision:{uid}', 0
            ),
            'selection_revision': database.metadata(
                f'selection_revision:{uid}', 0
            ),
            'analysis_generation': database.metadata('analysis_generation', 0),
        }
        with database.connect() as db:
            documents = [
                json.loads(row[0])
                for row in db.execute(
                    "SELECT document FROM dj_sessions WHERE owner=? AND COALESCE(json_extract(document,'$.background'),0)=1 AND state!='deleted'",
                    (uid,),
                )
            ]
            existing = {
                item['weekly_theme']
                for item in documents
                if item.get('weekly_period') == week
                and all(
                    item.get(key, 0) == value
                    for key, value in revision.items()
                )
            }
            # Deleted documents are intentionally erased, but request receipts remain.
            # Never regenerate an automatically evicted/deleted set in a tight loop.
            for theme in THEMES:
                _, nonce = weekly_request(uid, week, theme, revision)
                if db.execute(
                    'SELECT 1 FROM dj_requests WHERE owner=? AND nonce=?',
                    (uid, nonce),
                ).fetchone():
                    existing.add(theme)
            selections = {
                row['mood']: json.loads(row['ids'])
                for row in db.execute(
                    "SELECT mood,ids FROM playlists WHERE owner=? AND cadence='weekly' AND period=?",
                    (uid, week),
                )
            }
        missing = [
            theme
            for theme in THEMES
            if theme not in existing and theme in selections
        ]
        if not missing:
            continue
        visible = {row['id']: row for row in rows_for(uid)}
        for theme in missing:
            ids = [
                identity
                for identity in dict.fromkeys(selections[theme])
                if identity in visible
                and 0 <= float(visible[identity].get('duration') or 0) <= 1200
            ][:25]
            if len(ids) < 2:
                continue
            sources = sources_for(uid, ids)
            if set(sources) != set(ids):
                continue
            background = dict(
                weekly_period=week, weekly_theme=theme, **revision
            )
            intent, nonce = weekly_request(uid, week, theme, revision)
            try:
                dj.create(
                    uid,
                    'prepared',
                    DJ_THEME.get(theme, theme),
                    ids,
                    sources,
                    nonce=nonce,
                    request_intent=intent,
                    background=background,
                )
            except (PermissionError, RuntimeError):
                return 0  # A preference, lease, revision or foreground request changed.
            database.set_metadata('weekly_last_owner', uid)
            return 1
    return 0


def weekly_request(owner, week, theme, revision):
    background = dict(weekly_period=week, weekly_theme=theme, **revision)
    intent = json.dumps(
        ['weekly', owner, background], sort_keys=True, separators=(',', ':')
    )
    return intent, 'weekly:' + hashlib.sha256(intent.encode()).hexdigest()
