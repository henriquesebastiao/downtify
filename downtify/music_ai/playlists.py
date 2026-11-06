from __future__ import annotations

import json
import struct
from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .ranking import rank
from .store import MOODS

PARIS = ZoneInfo('Europe/Paris')


def period(cadence, now=None):
    now = (now or datetime.now(PARIS)).astimezone(PARIS)
    if cadence == 'daily':
        return (now - timedelta(hours=4)).date().isoformat()
    if cadence != 'weekly':
        raise ValueError('Invalid cadence')
    shifted = now - timedelta(hours=4, minutes=15)
    return (shifted.date() - timedelta(days=shifted.weekday())).isoformat()


def generate(store, owner, cadence, mood, rows, model, *, now=None):
    if mood not in MOODS:
        raise ValueError('Unknown mood')
    features = store.effective(owner)
    if not features.get(cadence, False):
        raise PermissionError('Feature disabled')
    profile_revision = store.metadata(f'profile_revision:{owner}', 0)
    analysis_generation = store.metadata('analysis_generation', 0)
    key = period(cadence, now)
    allowed = {row['id']: row for row in rows}
    with store.connect() as db:
        old = db.execute(
            'SELECT ids FROM playlists WHERE owner=? AND cadence=? AND mood=? AND period=?',
            (owner, cadence, mood, key),
        ).fetchone()
        if old:
            identities = json.loads(old[0])
            current = store.vectors(model, set(identities) & set(allowed))
            return [
                {**allowed[tid], 'reason': 'Correspond à cette humeur'}
                for tid in identities
                if tid in allowed and tid in current
            ]
        prompt = db.execute(
            'SELECT vector FROM mood_vectors WHERE mood=? AND model=?',
            (mood, model),
        ).fetchone()
        target = struct.unpack('<512f', prompt[0]) if prompt else None
        import time

        proposed = Counter(
            identity
            for row in db.execute(
                'SELECT ids FROM playlists WHERE owner=? AND created>? ORDER BY created DESC LIMIT 84',
                (owner, time.time() - 7 * 86400),
            )
            for identity in json.loads(row[0])
        )
    # Mood playlists must not silently masquerade as AI when the model is absent.
    if target is None:
        raise RuntimeError('Mood analysis is not ready')
    vectors = store.vectors(model, set(allowed))
    analyzed_rows = [row for row in rows if row['id'] in vectors]
    target_size = 40 if cadence == 'daily' else 50
    if not analyzed_rows or len(analyzed_rows) < min(target_size, len(rows)):
        raise RuntimeError('The initial catalog analysis is still in progress')
    result = rank(
        analyzed_rows,
        vectors,
        target=target,
        history=store.history(owner) if features['personalization'] else (),
        limit=40 if cadence == 'daily' else 50,
        rotation=f'{owner}:{mood}:{key}',
        proposed=proposed,
    )
    import time

    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        revisions = {
            row[0]: json.loads(row[1])
            for row in db.execute(
                'SELECT key,value FROM metadata WHERE key IN (?,?,?)',
                (
                    f'profile_revision:{owner}',
                    'analysis_generation',
                    'analysis_paused',
                ),
            )
        }
        if (
            revisions.get(f'profile_revision:{owner}', 0) != profile_revision
            or revisions.get('analysis_generation', 0) != analysis_generation
            or revisions.get('analysis_paused', False)
        ):
            raise RuntimeError('Generation invalidated')
        from .store import DEFAULTS

        preferences = {
            row[0]: {**DEFAULTS, **json.loads(row[1])}
            for row in db.execute(
                'SELECT owner,value FROM preferences WHERE owner IN (-1,?)',
                (owner,),
            )
        }
        if not all(
            preferences.get(uid, DEFAULTS)[cadence] for uid in (-1, owner)
        ):
            raise PermissionError('Feature disabled')
        db.execute(
            'INSERT OR IGNORE INTO playlists VALUES (?,?,?,?,?,?)',
            (
                owner,
                cadence,
                mood,
                key,
                json.dumps([row['id'] for row in result]),
                time.time(),
            ),
        )
        chosen = db.execute(
            'SELECT ids FROM playlists WHERE owner=? AND cadence=? AND mood=? AND period=?',
            (owner, cadence, mood, key),
        ).fetchone()
    return [
        {**allowed[tid], 'reason': 'Correspond à cette humeur'}
        for tid in json.loads(chosen[0])
        if tid in allowed
    ]


def summaries(store, owner, rows, *, now=None):
    """List existing current mixes only; never generate or expose hidden tracks."""
    flags = store.effective(owner)
    keys = {
        cadence: period(cadence, now)
        for cadence in ('daily', 'weekly')
        if flags[cadence]
    }
    if not keys:
        return []
    allowed = {row['id'] for row in rows}
    with store.connect() as db:
        found = db.execute(
            'SELECT cadence,mood,period,ids,created FROM playlists WHERE owner=? AND period IN (?,?) ORDER BY cadence,mood',
            (owner, period('daily', now), period('weekly', now)),
        ).fetchall()
    result = []
    for cadence, mood, key, ids, created in found:
        if keys.get(cadence) != key or mood not in MOODS:
            continue
        count = len(set(json.loads(ids)) & allowed)
        if count:
            result.append({
                'cadence': cadence,
                'mood': mood,
                'period': key,
                'created': created,
                'count': count,
            })
    return result
