"""Incremental rhythmic profiles, independent of DCLAP and native library files."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def active(database):
    flags = database.preferences(-1)
    return any(flags[key] for key in ('dj_prepared', 'dj_interactive'))


def enqueue(database, model, row, path, version, *, priority=0):
    with database.connect() as db:
        cached = db.execute(
            """SELECT 1 FROM dj_profiles WHERE track=? AND model=?
                               AND fingerprint=? AND json(source_version)=json(?)""",
            (row['id'], model, row['fingerprint'], json.dumps(version)),
        ).fetchone()
    if cached:
        return False
    generation = database.metadata('analysis_generation', 0)
    identity = hashlib.sha256(
        json.dumps([
            'rhythm',
            model,
            row['id'],
            row['fingerprint'],
            version,
            generation,
        ]).encode()
    ).hexdigest()
    return database.enqueue(
        identity,
        'rhythm',
        {
            'track': row['id'],
            'model': model,
            'path': str(path),
            'fingerprint': row['fingerprint'],
            'source_version': version,
            'generation': generation,
            'artist': row.get('artist', ''),
        },
        priority=priority,
    )


def seed_missing(database, model, *, limit=200):
    """Queue bounded native source checks; never walk files or reanalyse a valid profile."""
    generation = database.metadata('analysis_generation', 0)
    with database.connect() as db:
        rows = db.execute(
            """
            SELECT t.id FROM tracks t JOIN catalog_live l ON l.id=t.id
            LEFT JOIN source_versions s ON s.id=t.id
            WHERE NOT EXISTS (
                SELECT 1 FROM dj_profiles p WHERE p.track=t.id AND p.model=?
                AND p.fingerprint=t.fingerprint AND json(p.source_version)=json(s.signature)
            ) AND NOT EXISTS (
                SELECT 1 FROM jobs j WHERE j.kind='rhythm'
                AND json_extract(j.payload,'$.track')=t.id
                AND json_extract(j.payload,'$.model')=?
                AND json_extract(j.payload,'$.fingerprint')=t.fingerprint
                AND json_extract(j.payload,'$.generation')=?
                AND json_extract(j.payload,'$.source_version')=json(s.signature)
            ) ORDER BY t.observed DESC,t.id LIMIT ?
        """,
            (model, model, generation, limit),
        ).fetchall()
        db.executemany(
            'INSERT OR IGNORE INTO catalog_pending(id,priority) VALUES (?,0)',
            [(row['id'],) for row in rows],
        )
    return len(rows)


def weekly_check(database, model, *, now=None):
    """Sunday 02:00 Paris catch-up retries failures, retaining all successful analyses."""
    shifted = (now or datetime.now(ZoneInfo('Europe/Paris'))).astimezone(
        ZoneInfo('Europe/Paris')
    ) - timedelta(hours=2)
    key = (
        shifted.date() - timedelta(days=(shifted.weekday() + 1) % 7)
    ).isoformat()
    with database.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        old = db.execute(
            "SELECT value FROM metadata WHERE key='rhythm_weekly_check'"
        ).fetchone()
        if old and json.loads(old[0]) == [model, key]:
            return False
        db.execute(
            """UPDATE jobs SET state='queued',attempts=0,ready_at=0
                      WHERE kind='rhythm' AND state='failed'
                      AND json_extract(payload,'$.model')=?""",
            (model,),
        )
        db.execute(
            'INSERT OR REPLACE INTO metadata VALUES (?,?)',
            ('rhythm_weekly_check', json.dumps([model, key])),
        )
    return True


def coverage(database):
    """Observed catalogue coverage only: no source I/O, model load or inference."""
    clap = database.metadata('model', {}).get('id', '')
    rhythm = database.metadata('rhythm', {}).get('model', '')
    with database.connect() as db:
        total = db.execute(
            'SELECT count(*) FROM tracks t JOIN catalog_live l ON l.id=t.id'
        ).fetchone()[0]
        vectors = db.execute(
            """SELECT count(*) FROM analyses a JOIN tracks t ON t.id=a.id
                               JOIN catalog_live l ON l.id=t.id
                               WHERE a.model=? AND a.fingerprint=t.fingerprint""",
            (clap,),
        ).fetchone()[0]
        result = db.execute(
            """
            WITH current AS (
                SELECT CASE WHEN json_valid(p.value) THEN p.value ELSE '{}' END AS value
                FROM dj_profiles p JOIN tracks t ON t.id=p.track
                JOIN catalog_live l ON l.id=t.id
                JOIN source_versions s ON s.id=t.id
                WHERE p.model=? AND p.fingerprint=t.fingerprint
                AND json(p.source_version)=json(s.signature)
            ) SELECT count(*) AS profiles,
                coalesce(sum(json_extract(value,'$.profile.bpm')>0),0) AS tempo,
                coalesce(sum(json_array_length(json_extract(value,'$.beats'))>0),0) AS beats,
                coalesce(sum(json_array_length(json_extract(value,'$.profile.downbeats'))>0),0) AS bars,
                coalesce(sum(json_extract(value,'$.profile.key')>=0
                    AND json_extract(value,'$.profile.key_confidence')>=.65),0) AS tonal_key,
                coalesce(sum(json_type(value,'$.loudness.input_i') IN ('integer','real')
                    AND json_type(value,'$.loudness.input_tp') IN ('integer','real')),0) AS level,
                coalesce(sum(json_extract(value,'$.profile.energy') BETWEEN 0 AND 1),0) AS energy,
                coalesce(sum(json_extract(value,'$.profile.confidence') BETWEEN 0 AND 1),0) AS confidence,
                coalesce(sum(json_array_length(json_extract(value,'$.transition_points'))>0),0) AS candidate_points
            FROM current
        """,
            (rhythm,),
        ).fetchone()
        jobs = {
            row[0]: row[1]
            for row in db.execute(
                """
            SELECT state,count(*) FROM jobs WHERE kind='rhythm'
            AND json_extract(payload,'$.model')=? GROUP BY state
        """,
                (rhythm,),
            )
        }
    fields = dict(result)
    profiles = fields.pop('profiles')
    return {
        'observed_tracks': total,
        'clap': {'model': clap, 'analyzed': vectors},
        'rhythm': {
            'model': rhythm,
            'profiles': profiles,
            'missing': max(0, total - profiles),
            'fields': fields,
            'jobs': jobs,
        },
        'measurement': 'observed_catalogue',
        'source_scan': False,
    }
