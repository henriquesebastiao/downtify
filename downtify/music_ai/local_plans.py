"""Bounded cached analysis for device playback; never schedules audio work."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from .dj_plan import Profile, tempo_factor, transition
from .store import Store

VERSION = 1
MAX_DOWNBEATS = 20_000
MAX_PROFILE_BYTES = 2 * 1024 * 1024
MIN_CONFIDENCE = 0.75
TrackId = Annotated[str, Field(strict=True, min_length=1, max_length=80)]


class LocalPlansRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ids: list[TrackId] = Field(min_length=2, max_length=4)
    transition_ms: int = Field(default=5000, strict=True, ge=1000, le=12000)


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def cached(
    database: Store, identities: list[str]
) -> tuple[str, Any, dict[str, sqlite3.Row]]:
    """One snapshot and at most four indexed profile lookups, without DDL."""
    with database.connect() as db:
        db.execute('BEGIN')
        metadata = {
            row[0]: json.loads(row[1])
            for row in db.execute(
                "SELECT key,value FROM metadata WHERE key IN ('rhythm','analysis_generation')"
            )
        }
        rhythm = metadata.get('rhythm', {})
        model = rhythm.get('model', '') if isinstance(rhythm, dict) else ''
        if not isinstance(model, str) or not model or len(model) > 512:
            return '', metadata.get('analysis_generation', 0), {}
        placeholders = ','.join('?' for _ in identities)
        try:
            records = db.execute(
                'SELECT p.track,p.fingerprint,p.source_version,'
                'CASE WHEN length(CAST(p.value AS BLOB))<=? THEN p.value END AS value,'
                't.fingerprint AS current_fingerprint,'
                's.signature AS current_source_version '
                'FROM dj_profiles p LEFT JOIN tracks t ON t.id=p.track '
                'LEFT JOIN source_versions s ON s.id=p.track '
                f'WHERE p.model=? AND p.track IN ({placeholders})',
                (MAX_PROFILE_BYTES, model, *identities),
            ).fetchall()
        except sqlite3.OperationalError as error:
            if 'no such table: dj_profiles' not in str(error):
                raise
            records = []
    return (
        model,
        metadata.get('analysis_generation', 0),
        {row['track']: row for row in records},
    )


def profile(value: str, identity: str) -> Profile:
    if not isinstance(value, str) or len(value.encode()) > MAX_PROFILE_BYTES:
        raise ValueError('Invalid cached profile')
    item = json.loads(value)['profile']
    beats = item['downbeats']
    if (
        item['id'] != identity
        or not isinstance(beats, list)
        or not 3 <= len(beats) <= MAX_DOWNBEATS
        or type(item.get('key', -1)) is not int
    ):
        raise ValueError('Invalid cached profile')
    numbers = [
        item[key] for key in ('duration', 'bpm', 'confidence', 'energy')
    ] + [
        item.get('key_confidence', 0),
        item.get('instrumental_confidence', 0),
        *beats,
    ]
    if not all(
        type(number) in {int, float}
        and abs(number) <= 3600
        and math.isfinite(number)
        for number in numbers
    ):
        raise ValueError('Invalid cached profile')
    result = Profile(
        id=identity,
        duration=item['duration'],
        bpm=item['bpm'],
        confidence=item['confidence'],
        downbeats=tuple(beats),
        energy=item['energy'],
        key=item.get('key', -1),
        key_confidence=item.get('key_confidence', 0),
        instrumental_confidence=item.get('instrumental_confidence', 0),
    )
    if not 30 <= result.bpm <= 300 or result.confidence < MIN_CONFIDENCE:
        raise ValueError('Unreliable cached profile')
    return result


def track(
    native: dict[str, Any], record: sqlite3.Row | None, model: str
) -> tuple[dict[str, Any], Profile | None]:
    result = {
        'id': native['id'],
        'revision': digest((
            model,
            native.get('revision'),
            native['fingerprint'],
            record['value'] if record else None,
        )),
        'status': 'missing',
    }
    if record is None:
        return result, None
    try:
        source = json.loads(record['source_version'])
        current = json.loads(record['current_source_version'])
        valid = (
            isinstance(source, list)
            and len(source) == 5
            and all(type(part) is int for part in source)
            and source == current
            and record['fingerprint']
            == record['current_fingerprint']
            == native['fingerprint']
        )
    except (TypeError, ValueError):
        valid = False
    if not valid:
        result['status'] = 'stale'
        return result, None
    try:
        parsed = profile(record['value'], native['id'])
        beats = sorted({round(beat * 1000) for beat in parsed.downbeats})
        if len(beats) < 3:
            raise ValueError('Insufficient distinct millisecond downbeats')
    except (ValueError, TypeError, KeyError):
        result['status'] = 'unreliable'
        return result, None
    result.update(
        status='ready',
        bpm=parsed.bpm,
        confidence=parsed.confidence,
        downbeats_ms=beats,
    )
    return result, parsed


def plan(
    first: dict[str, Any],
    second: dict[str, Any],
    profiles: dict[str, Profile],
    requested: int,
) -> dict[str, Any]:
    result = {
        'from_index': first['index'],
        'to_index': second['index'],
        'state': 'unavailable',
        'aligned': False,
    }
    for item in (first, second):
        if item['status'] != 'ready':
            return {**result, 'reason': item['status'] + '_analysis'}
    outgoing, incoming = profiles[first['id']], profiles[second['id']]
    candidate = transition(outgoing, incoming)
    if not candidate.aligned:
        reason = (
            'tempo_mismatch'
            if tempo_factor(outgoing.bpm, incoming.bpm) is None
            else 'alignment_unavailable'
        )
        return {**result, 'reason': reason}
    end = round(candidate.source_end * 1000)
    limit = min(requested, round(candidate.overlap * 1000))
    starts = [
        round(beat * 1000)
        for beat in outgoing.downbeats
        if 0 < end - round(beat * 1000) <= limit
    ]
    if not starts:
        return {**result, 'reason': 'duration_too_short'}
    start = min(starts)
    return {
        **result,
        'state': 'ready',
        'aligned': True,
        'outgoing_start_ms': start,
        'source_end_ms': end,
        'incoming_cue_ms': round(candidate.incoming_cue * 1000),
        'duration_ms': end - start,
        'speed': candidate.incoming_speed,
        'reason': 'bars_aligned',
    }


def lookup(
    database: Store,
    rows: list[dict[str, Any]],
    ids: list[str],
    transition_ms: int,
    owner: int,
) -> tuple[dict[str, Any], dict[str, list[int]]]:
    model, generation, records = cached(database, list(dict.fromkeys(ids)))
    native = {row['id']: row for row in rows}
    tracks, profiles = [], {}
    for index, identity in enumerate(ids):
        item, parsed = track(native[identity], records.get(identity), model)
        tracks.append({**item, 'index': index})
        if parsed is not None:
            profiles[identity] = parsed
    result = {
        'version': VERSION,
        'analysis_model': digest(model),
        'tracks': tracks,
        'plans': [
            plan(first, second, profiles, transition_ms)
            for first, second in zip(tracks, tracks[1:])
        ],
    }
    sources = {
        identity: json.loads(records[identity]['source_version'])
        for identity in profiles
    }
    return {
        **result,
        'revision': digest((owner, generation, transition_ms, result)),
    }, sources
