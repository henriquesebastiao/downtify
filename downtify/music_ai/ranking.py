"""ACL-first content ranking. Import numpy only when ranking is requested."""

from __future__ import annotations

import math
import time
import unicodedata


def recording(row):
    # Keep version labels (live, remix, etc.). Only fold typography and case.
    def clean(value):
        return ' '.join(
            unicodedata.normalize('NFKC', str(value or '')).casefold().split()
        )

    title, artist = clean(row.get('title')), clean(row.get('artist'))
    return (artist, title) if title and artist else ('id', row['id'])


def rank(
    rows,
    vectors,
    *,
    seed=None,
    target=None,
    history=(),
    favorites=(),
    limit=40,
    rotation='',
    proposed=None,
    proposed_artists=None,
):
    import hashlib

    import numpy as np

    # Callers provide the current visible catalog, never the global database.
    visible = {row['id']: row for row in rows}
    ids = [key for key in visible if key in vectors]
    recent = {}
    for event in history:
        if event['track'] not in visible or event['outcome'] == 'error':
            continue
        age = max(0, time.time() - event['at'])
        value = min(1.0, event['seconds'] / 120) * math.exp(
            -age / (30 * 86400)
        )
        if event['outcome'] == 'skip' and event['seconds'] < 30:
            value = -0.5 * math.exp(-age / (7 * 86400))
        recent[event['track']] = recent.get(event['track'], 0) + value
    if seed is not None and seed not in visible:
        raise ValueError('Seed unavailable')
    if target is None and seed in vectors:
        target = vectors[seed]
    # Personal taste also guides mood mixes, rather than rewarding only the
    # exact tracks already heard. The mood remains the dominant component.
    mood_target = target is not None and seed is None
    personal = None
    favorites = set(favorites) & set(visible)
    if ids and seed is None:
        weights = np.asarray(
            [
                min(3.0, max(0, recent.get(key, 0)))
                + (2 if key in favorites else 0)
                for key in ids
            ],
            dtype=np.float32,
        )
        if weights.sum() > 0:
            personal = np.average(
                np.asarray([vectors[key] for key in ids], dtype=np.float32),
                axis=0,
                weights=weights,
            )
            personal /= max(float(np.linalg.norm(personal)), 1e-12)
    if personal is not None:
        if target is None:
            target = personal
        else:
            mood = np.array(target, dtype=np.float32, copy=True)
            mood /= max(float(np.linalg.norm(mood)), 1e-12)
            target = 0.75 * mood + 0.25 * personal
    scores = {}
    if ids and target is not None:
        matrix = np.asarray([vectors[key] for key in ids], dtype=np.float32)
        query = np.array(target, dtype=np.float32, copy=True)
        query /= max(float(np.linalg.norm(query)), 1e-12)
        scores = dict(zip(ids, (matrix @ query).tolist()))
    candidates = []
    proposed = proposed or {}
    proposed_artists = proposed_artists or {}
    for key, row in visible.items():
        if key == seed:
            continue
        if seed is not None and key not in vectors:
            continue
        jitter = (
            int.from_bytes(
                hashlib.sha256(f'{rotation}:{key}'.encode()).digest()[:4],
                'big',
            )
            / 2**32
        )
        content = scores.get(key)
        score = (0.8 * content if content is not None else 0) + 0.08 * jitter
        score += min(
            0.1,
            max(
                -0.3,
                recent.get(key, 0) * (0.3 if recent.get(key, 0) < 0 else 0.03),
            ),
        )
        added = float(row.get('added') or 0)
        if added > 0:
            score += 0.06 * math.exp(
                -max(0, time.time() - added) / (14 * 86400)
            )
        score -= min(0.3, 0.04 * proposed.get(key, 0))
        artist = str(row.get('artist') or '').casefold().strip()
        score -= min(0.2, 0.015 * proposed_artists.get(artist, 0))
        candidates.append((score, key, row, content))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    selected, artists = [], {}
    recordings = [visible[seed]] if seed is not None else []
    while candidates and len(selected) < limit:
        # Re-score after every choice: a second track from an artist is less
        # useful than an equally suitable new artist, even before the cap.
        index = max(
            range(len(candidates)),
            key=lambda i: (
                candidates[i][0]
                - 0.16
                * artists.get(
                    str(candidates[i][2].get('artist') or '')
                    .casefold()
                    .strip(),
                    0,
                ),
                -i,
            ),
        )
        score, key, row, content = candidates.pop(index)
        duration = float(row.get('duration') or 0)
        if any(
            recording(old) == recording(row)
            and (
                not duration
                or not old.get('duration')
                or abs(float(old['duration']) - duration) <= 3
            )
            for old in recordings
        ):
            continue
        artist = str(row.get('artist', '')).casefold().strip()
        if artist and artists.get(artist, 0) >= 2:
            continue
        artists[artist] = artists.get(artist, 0) + 1
        recordings.append(row)
        selected.append({
            **row,
            'score': round(score, 5),
            'reason': (
                'Sonorités proches'
                if seed
                else 'Correspond à cette humeur'
                if mood_target
                else 'Proche de vos écoutes'
            )
            if content is not None
            else 'À découvrir dans votre bibliothèque',
            'analyzed': content is not None,
        })
        if len(selected) >= limit:
            break
    return selected
