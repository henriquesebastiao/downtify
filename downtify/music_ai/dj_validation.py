"""Local technical continuity proof, bound to exact code, models and runtime."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import sqlite3
import time
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def runtime_identity():
    binaries = (
        Path('/usr/bin/ffmpeg'),
        Path('/opt/sqlite/lib/libsqlite3.so.0'),
        Path('/usr/share/doc/music-dj/python-lock.txt'),
        Path('/usr/share/doc/music-dj/debian-packages.txt'),
    )
    if not all(path.is_file() for path in binaries):
        return None
    digest = hashlib.sha256(sqlite3.sqlite_version.encode())
    for path in binaries:
        with path.open('rb') as source:
            digest.update(hashlib.file_digest(source, 'sha256').digest())
    for package in ('numpy', 'scipy', 'torch', 'beat-this'):
        digest.update(
            (package + ':' + importlib.metadata.version(package)).encode()
        )
    return 'runtime:' + digest.hexdigest()


def proof_key(engine, runtime):
    return (
        'dj_validation:'
        + hashlib.sha256(json.dumps([engine, runtime]).encode()).hexdigest()
    )


def saved_proof(database, engine, runtime):
    return database.metadata(
        proof_key(engine, runtime), None
    ) or database.metadata('dj_interactive_validation', {})


def validated(proof, engine, runtime):
    if not runtime or not isinstance(proof, dict):
        return False
    values = [
        proof.get(key)
        for key in ('continuous_seconds', 'render_speed', 'interruptions')
    ]
    if not all(
        type(value) in (int, float) and math.isfinite(value)
        for value in values
    ):
        return False
    return bool(
        proof.get('engine') == engine
        and proof.get('runtime') == runtime
        and values[0] >= 3600
        and values[1] > 1.5
        and values[2] == 0
    )


def receive(store, session, position, sequence, *, interruptions=0, now=None):
    """Never trust client elapsed time: accumulate only continuous server-timed progress."""
    if (
        not math.isfinite(position)
        or position < 0
        or type(sequence) is not int
        or not 0 <= sequence <= 1_000_000
        or not session.get('validation')
        or type(interruptions) is not int
        or not 0 <= interruptions <= 1_000_000
    ):
        raise ValueError('Invalid continuity report')
    now = time.time() if now is None else now
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute(
            'SELECT state,document,lease_until FROM dj_sessions WHERE id=? AND owner=?',
            (session['id'], session['owner']),
        ).fetchone()
        if (
            not row
            or row['state'] not in ('playing', 'paused')
            or row['lease_until'] <= now
        ):
            raise PermissionError('Validation session is not active')
        current = json.loads(row['document'])
        from .dj_store import enabled

        if not enabled(db, session['owner'], 'interactive'):
            raise PermissionError('Validation module is disabled')
        if position > current.get('rendered', 0) + 0.25:
            raise ValueError('Playback exceeds rendered audio')
        old = db.execute(
            'SELECT value FROM dj_validation_receipts WHERE session=?',
            (session['id'],),
        ).fetchone()
        proof = (
            json.loads(old[0])
            if old
            else {
                'sequence': -1,
                'continuous_seconds': 0.0,
                'interruptions': 0,
                'first': now,
            }
        )
        if sequence <= proof['sequence']:
            return proof
        proof.setdefault('total_interruptions', proof['interruptions'])
        if old and 'window_seen' in proof:
            elapsed, movement = (
                now - proof['seen'],
                position - proof['position'],
            )
            window_elapsed = now - proof['window_seen']
            window_movement = position - proof['window_position']
            # HTTP queueing changes arrival time without changing playback.
            # Bound absolute phase drift over the whole window so a small
            # per-report acceleration cannot accumulate into a false hour.
            phase_error = window_movement - window_elapsed
            continuous = (
                0.25 <= elapsed <= 65
                and movement > 0
                and abs(phase_error) <= 2.0
                and interruptions == proof.get('client_interruptions', 0)
                and row['state'] == 'playing'
            )
            if continuous:
                proof['continuous_seconds'] = min(
                    window_elapsed, window_movement
                )
                # A new qualifying window starts after the last interruption.
                # Its duration must still be observed completely by this server.
                proof['interruptions'] = 0
            else:
                proof['continuous_seconds'] = 0.0
                proof['interruptions'] += 1
                proof['total_interruptions'] += 1
                proof['window_seen'] = now
                proof['window_position'] = position
                reason = (
                    'paused'
                    if row['state'] != 'playing'
                    else 'client_event'
                    if interruptions != proof.get('client_interruptions', 0)
                    else 'clock_gap'
                    if not 0.25 <= elapsed <= 65
                    else 'no_progress'
                    if movement <= 0
                    else 'clock_drift'
                )
                counts = proof.setdefault('reset_counts', {})
                counts[reason] = counts.get(reason, 0) + 1
            proof['clock_delta_seconds'] = round(phase_error, 3)
        else:
            # Receipts from the earlier interval clock start a fresh window.
            proof['continuous_seconds'] = 0.0
            proof['window_seen'] = now
            proof['window_position'] = position
        proof.update(
            sequence=sequence,
            seen=now,
            position=position,
            client_interruptions=interruptions,
            engine=current.get('engine'),
            runtime=current.get('runtime'),
            render_speed=current.get('render_speed', 0),
        )
        # Startup seeks and later controls reset the window; they cannot add elapsed time.
        db.execute(
            'INSERT OR REPLACE INTO dj_validation_receipts VALUES (?,?)',
            (session['id'], json.dumps(proof)),
        )
        if validated(proof, current.get('engine'), current.get('runtime')):
            verified = json.dumps({**proof, 'verified_at': now})
            db.execute(
                'INSERT OR REPLACE INTO metadata VALUES (?,?)',
                (
                    proof_key(current.get('engine'), current.get('runtime')),
                    verified,
                ),
            )
            # Keep the historical proof usable by the previous image on rollback.
            db.execute(
                'INSERT OR IGNORE INTO metadata VALUES (?,?)',
                ('dj_interactive_validation', verified),
            )
        return proof
