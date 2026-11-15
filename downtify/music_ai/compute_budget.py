"""One cooperative heavy-compute lease, with DJ priority over indexing."""

from __future__ import annotations

import json
import secrets
import time
from pathlib import Path


def pressure_high():
    try:
        for name, threshold in [('memory', 1.0), ('io', 5.0)]:
            line = (
                Path('/proc/pressure', name)
                .read_text(encoding='utf-8')
                .splitlines()[0]
            )
            average = float(
                next(
                    value.split('=')[1]
                    for value in line.split()
                    if value.startswith('avg10=')
                )
            )
            if average > threshold:
                return True
        available = next(
            line
            for line in Path('/proc/meminfo')
            .read_text(encoding='utf-8')
            .splitlines()
            if line.startswith('MemAvailable:')
        )
        return int(available.split()[1]) < 1536 * 1024
    except (OSError, ValueError, StopIteration):
        return False


class ComputeTicket:
    def __init__(self, database, token, kind, clock):
        self.database, self.token, self.kind, self.clock = (
            database,
            token,
            kind,
            clock,
        )
        self.renewed = 0.0

    def renew(self):
        now = self.clock()
        if now - self.renewed < 1:
            return True
        if self.kind in {'analysis', 'dj-background'} and pressure_high():
            return False
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if self.kind == 'dj-background':
                from .dj_background import blocked

                if blocked(db):
                    return False
            if self.kind in {'analysis', 'dj-background'}:
                waiting = db.execute(
                    "SELECT value FROM metadata WHERE key='compute_dj_waiting'"
                ).fetchone()
                if waiting and json.loads(waiting[0]) > now:
                    return False
            changed = db.execute(
                'UPDATE compute_lease SET expires=? WHERE id=1 AND token=? AND expires>?',
                (now + 45, self.token, now),
            ).rowcount
        self.renewed = now
        return bool(changed)

    def release(self):
        with self.database.connect() as db:
            db.execute(
                'DELETE FROM compute_lease WHERE id=1 AND token=?',
                (self.token,),
            )


def acquire(database, kind, *, clock=time.time):
    if kind not in {'analysis', 'dj', 'dj-background'}:
        raise ValueError('Unknown compute task')
    if kind in {'analysis', 'dj-background'} and pressure_high():
        return None
    now, token = clock(), secrets.token_hex(16)
    with database.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if kind == 'dj-background':
            from .dj_background import blocked

            if blocked(db):
                return None
        if kind == 'dj':
            db.execute(
                "INSERT OR REPLACE INTO metadata VALUES ('compute_dj_waiting',?)",
                (json.dumps(now + 10),),
            )
        else:
            waiting = db.execute(
                "SELECT value FROM metadata WHERE key='compute_dj_waiting'"
            ).fetchone()
            if waiting and json.loads(waiting[0]) > now:
                return None
        current = db.execute(
            'SELECT expires FROM compute_lease WHERE id=1'
        ).fetchone()
        if current and current[0] > now:
            return None
        db.execute(
            'INSERT OR REPLACE INTO compute_lease VALUES (1,?,?,?)',
            (token, kind, now + 45),
        )
    return ComputeTicket(database, token, kind, clock)
