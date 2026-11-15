from __future__ import annotations

import json
import re
import struct
import time
from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import covers
from .ranking import rank
from .store import GENRE_THEMES, MOODS

PARIS = ZoneInfo('Europe/Paris')

# Weekly mixes include genre themes; daily mixes keep the six mood prompts.
GENRES = {
    'pop': r'\b(pop|k[ -]?pop|j[ -]?pop|synth[ -]?pop|britpop)\b',
    'rap': r'\b(rap|hip[ -]?hop|trap)\b',
    'rock': r'\b(rock|metal|punk|grunge)\b',
    'electro': r'\b(electro\w*|house|techno|trance|dance|edm|dubstep)\b',
}
WEEKLY_SIZE = 25
DAILY_SIZE = 40


def themes(cadence):
    if cadence == 'daily':
        return [mood for mood in MOODS if mood not in GENRE_THEMES]
    if cadence == 'weekly':
        return list(MOODS) + list(GENRE_THEMES)
    raise ValueError('Invalid cadence')


def genre_rows(theme, rows):
    """A genre theme never falls back to another style when its tag is missing."""
    pattern = GENRES.get(theme)
    if pattern is None:
        return rows
    matcher = re.compile(pattern, re.I)
    return [row for row in rows if matcher.search(str(row.get('genre') or ''))]


def period(cadence, now=None):
    now = (now or datetime.now(PARIS)).astimezone(PARIS)
    if cadence == 'daily':
        return (now - timedelta(hours=4)).date().isoformat()
    if cadence != 'weekly':
        raise ValueError('Invalid cadence')
    shifted = now - timedelta(hours=4, minutes=15)
    return (shifted.date() - timedelta(days=shifted.weekday())).isoformat()


def generate(store, owner, cadence, mood, rows, model, *, now=None):
    if mood not in MOODS and mood not in GENRE_THEMES:
        raise ValueError('Unknown mood')
    features = store.effective(owner)
    if not features.get(cadence, False):
        raise PermissionError('Feature disabled')
    profile_revision = store.metadata(f'profile_revision:{owner}', 0)
    analysis_generation = store.metadata('analysis_generation', 0)
    selection_revision = store.metadata(f'selection_revision:{owner}', 0)
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
        if mood in GENRE_THEMES:
            target = None
        else:
            prompt = db.execute(
                'SELECT vector FROM mood_vectors WHERE mood=? AND model=?',
                (mood, model),
            ).fetchone()
            target = struct.unpack('<512f', prompt[0]) if prompt else None
        proposed = recent_proposals(db, owner)
    candidates = genre_rows(mood, rows)
    target_size = DAILY_SIZE if cadence == 'daily' else WEEKLY_SIZE
    if mood in GENRES and len(candidates) < min(target_size, 8):
        raise RuntimeError(
            'Not enough local tracks tagged in this genre; fill their metadata '
            'or pick a mood'
        )
    vectors = store.vectors(model, set(allowed))
    analyzed_rows = [row for row in candidates if row['id'] in vectors]
    if not analyzed_rows or len(analyzed_rows) < min(
        target_size, len(candidates)
    ):
        raise RuntimeError('The initial catalog analysis is still in progress')
    if mood in GENRE_THEMES:
        # A genre theme ranks against the centroid of its analysed tracks,
        # never against a mood prompt (the bundled CLAP release pins only the
        # six mood vectors, so there is no genre mood_vector to look up).
        import numpy as np

        target = np.mean([vectors[row['id']] for row in analyzed_rows], axis=0)
    elif target is None:
        # Mood playlists must not silently masquerade as AI when the model is absent.
        raise RuntimeError('Mood analysis is not ready')
    result = rank(
        analyzed_rows,
        vectors,
        target=target,
        history=store.history(owner) if features['personalization'] else (),
        favorites=[row['id'] for row in rows if row.get('favorite')]
        if features['personalization']
        else (),
        proposed_artists=Counter(
            str(allowed[tid].get('artist') or '').casefold().strip()
            for tid, count in proposed.items()
            if tid in allowed
            for _ in range(count)
        ),
        limit=target_size,
        rotation=f'{owner}:{mood}:{key}:{selection_revision}',
        proposed=proposed,
    )
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        revisions = {
            row[0]: json.loads(row[1])
            for row in db.execute(
                'SELECT key,value FROM metadata WHERE key IN (?,?,?,?)',
                (
                    f'profile_revision:{owner}',
                    'analysis_generation',
                    'analysis_paused',
                    f'selection_revision:{owner}',
                ),
            )
        }
        if (
            revisions.get(f'profile_revision:{owner}', 0) != profile_revision
            or revisions.get('analysis_generation', 0) != analysis_generation
            or revisions.get('analysis_paused', False)
            or revisions.get(f'selection_revision:{owner}', 0)
            != selection_revision
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


def _previous_period(cadence, key):
    """The period just before `key`, the only fallback a card may show."""
    day = datetime.fromisoformat(key).date()
    return (day - timedelta(days=1 if cadence == 'daily' else 7)).isoformat()


def _latest(store, owner, cadence, key):
    """Current mix per mood, or yesterday's while this morning's is not ready.

    A fresh period starts at 04:00 Paris. Until today's mix exists the previous
    one stays playable, so an early morning open never lands on an empty
    "preparing" card. Older periods are never resurrected.
    """
    with store.connect() as db:
        found = db.execute(
            'SELECT mood,period,ids,created FROM playlists '
            'WHERE owner=? AND cadence=? AND period IN (?,?) '
            'ORDER BY period DESC, created DESC',
            (owner, cadence, key, _previous_period(cadence, key)),
        ).fetchall()
    latest = {}
    for mood, stored_period, ids, created in found:
        if (mood in MOODS or mood in GENRE_THEMES) and mood not in latest:
            latest[mood] = (stored_period, ids, created)
    return latest


def summaries(store, owner, rows, *, now=None):
    """List current mixes, falling back to the previous one until it is ready."""
    flags = store.effective(owner)
    keys = {
        cadence: period(cadence, now)
        for cadence in ('daily', 'weekly')
        if flags[cadence]
    }
    if not keys:
        return []
    allowed = {row['id'] for row in rows}
    result = []
    for cadence, key in keys.items():
        for mood, (stored, ids, created) in sorted(
            _latest(store, owner, cadence, key).items()
        ):
            identities = json.loads(ids)
            count = len(set(identities) & allowed)
            if not count:
                continue
            result.append({
                'cadence': cadence,
                'mood': mood,
                'period': stored,
                'created': created,
                'count': count,
                'cover_track_ids': [
                    identity for identity in identities if identity in allowed
                ][:4],
                'cover_url': covers.url(cadence, mood, stored),
                'state': 'ready' if stored == key else 'previous',
            })
    return result


def stored_selections(store, owner, *, now=None):
    flags = store.effective(owner)
    selections = []
    for cadence in ('daily', 'weekly'):
        if not flags.get(cadence):
            continue
        key = period(cadence, now)
        for mood, (stored, ids, created) in sorted(
            _latest(store, owner, cadence, key).items()
        ):
            selections.append(
                dict(
                    cadence=cadence,
                    mood=mood,
                    period=stored,
                    ids=json.loads(ids),
                    created=created,
                )
            )
    return selections


def recent_proposals(db, owner):
    """Current and explicitly renewed selections share a bounded rotation window."""
    cutoff = time.time() - 7 * 86400
    identities = [
        identity
        for row in db.execute(
            'SELECT ids FROM playlists WHERE owner=? AND created>? '
            'ORDER BY created DESC LIMIT 84',
            (owner, cutoff),
        )
        for identity in json.loads(row[0])
    ]
    archived = db.execute(
        'SELECT value FROM metadata WHERE key=?',
        (f'playlist_rotation_history:{owner}',),
    ).fetchone()
    if archived:
        identities.extend(
            identity
            for cohort in json.loads(archived[0])[-84:]
            if cohort['created'] > cutoff
            for identity in cohort['ids']
        )
    return Counter(identities)


def refresh(store, owner, request_id, *, now=None):
    """Invalidate this owner's current automatic mixes, without audio work."""
    from .store import DEFAULTS

    keys = {cadence: period(cadence, now) for cadence in ('daily', 'weekly')}
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')

        def read(key, default):
            row = db.execute(
                'SELECT value FROM metadata WHERE key=?', (key,)
            ).fetchone()
            return json.loads(row[0]) if row else default

        def write(key, value):
            db.execute(
                'INSERT OR REPLACE INTO metadata VALUES (?,?)',
                (key, json.dumps(value)),
            )

        preferences = {
            row[0]: {**DEFAULTS, **json.loads(row[1])}
            for row in db.execute(
                'SELECT owner,value FROM preferences WHERE owner IN (-1,?)',
                (owner,),
            )
        }
        enabled = [
            cadence
            for cadence in keys
            if all(
                preferences.get(uid, DEFAULTS)[cadence] for uid in (-1, owner)
            )
        ]
        if not enabled:
            raise PermissionError('Feature disabled')
        receipts_key = f'playlist_refresh_receipts:{owner}'
        receipts = read(receipts_key, [])
        previous = next(
            (r for r in receipts if r['request_id'] == request_id), None
        )
        if previous:
            return previous['result']
        archived = read(f'playlist_rotation_history:{owner}', [])
        removed = 0
        for cadence in enabled:
            archived.extend(
                dict(ids=json.loads(row['ids']), created=row['created'])
                for row in db.execute(
                    'SELECT ids,created FROM playlists '
                    'WHERE owner=? AND cadence=? AND period=?',
                    (owner, cadence, keys[cadence]),
                )
            )
            removed += db.execute(
                'DELETE FROM playlists WHERE owner=? AND cadence=? AND period=?',
                (owner, cadence, keys[cadence]),
            ).rowcount
        archived = sorted(
            (
                item
                for item in archived
                if item['created'] > time.time() - 7 * 86400
            ),
            key=lambda item: item['created'],
        )[-84:]
        write(f'playlist_rotation_history:{owner}', archived)
        revision = read(f'selection_revision:{owner}', 0) + 1
        write(f'selection_revision:{owner}', revision)
        result = dict(accepted=True, revision=revision, removed=removed)
        receipts.append(dict(request_id=request_id, result=result))
        write(receipts_key, receipts[-32:])
        return result
