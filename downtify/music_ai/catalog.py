"""Incremental derived snapshot. Only the background indexer consumes the feed."""

from __future__ import annotations

import hashlib
import json
import math
import time


def recent_addition(row, *, now=None):
    try:
        added = float(row.get('added') or 0)
    except (ValueError, TypeError):
        return False
    return (
        math.isfinite(added)
        and added >= (time.time() if now is None else now) - 7 * 86400
    )


def fingerprint(row):
    return hashlib.sha256(
        json.dumps(
            tuple(
                row.get(key)
                for key in ('file', 'size', 'modified', 'added', 'duration')
            )
        ).encode()
    ).hexdigest()


def synchronize(database, native):
    previous = database.metadata('native_catalog_cursor', 0)
    initialized = database.metadata('native_catalog_initialized', False)
    if initialized and previous == native.cursor():
        return 0
    feed = native.changes(previous if initialized else 0)
    changed = [
        {**row, 'fingerprint': fingerprint(row)} for row in feed['tracks']
    ]
    database.observe(changed)
    with database.connect() as db:
        if feed['full']:
            db.execute('DELETE FROM catalog_live')
            db.execute('DELETE FROM catalog_pending')
        db.executemany(
            'INSERT OR IGNORE INTO catalog_live VALUES (?)',
            [(row['id'],) for row in changed],
        )
        now = time.time()
        db.executemany(
            'INSERT OR IGNORE INTO catalog_pending(id,priority) VALUES (?,?)',
            [
                (row['id'], int(recent_addition(row, now=now)))
                for row in changed
            ],
        )
        db.executemany(
            'DELETE FROM catalog_live WHERE id=?',
            [(identity,) for identity in feed['deleted']],
        )
        db.executemany(
            'DELETE FROM catalog_pending WHERE id=?',
            [(identity,) for identity in feed['deleted']],
        )
        # Derived audio from removed native rows must not remain usable.
        if feed['full']:
            db.execute(
                'DELETE FROM analyses WHERE id NOT IN (SELECT id FROM catalog_live)'
            )
        else:
            db.executemany(
                'DELETE FROM analyses WHERE id=?',
                [(identity,) for identity in feed['deleted']],
            )
        for key, value in [
            ('native_catalog_cursor', feed['cursor']),
            ('native_catalog_initialized', True),
        ]:
            db.execute(
                'INSERT OR REPLACE INTO metadata VALUES (?,?)',
                (key, json.dumps(value)),
            )
    return len(changed) + len(feed['deleted'])


def snapshot(database):
    with database.connect() as db:
        restriction = (
            ' JOIN catalog_live l ON l.id=t.id'
            if database.metadata('native_catalog_initialized', False)
            else ''
        )
        return [
            json.loads(row[0])
            for row in db.execute(
                'SELECT t.row_json FROM tracks t' + restriction
            )
        ]


def candidates(database, model, *, after='', limit=100, unmeasured=False):
    restriction = (
        ' JOIN catalog_live l ON l.id=t.id'
        if database.metadata('native_catalog_initialized', False)
        else ''
    )
    with database.connect() as db:
        if unmeasured:
            rows = db.execute(
                'SELECT t.row_json FROM catalog_pending p JOIN tracks t ON t.id=p.id'
                + restriction
                + ' ORDER BY p.priority DESC,p.id LIMIT ?',
                (limit,),
            )
        else:
            rows = db.execute(
                'SELECT t.row_json FROM tracks t'
                + restriction
                + ' WHERE t.id>? ORDER BY t.id LIMIT ?',
                (after, limit),
            )
        return [json.loads(row[0]) for row in rows]


def ensure_analysis_queue(database, model):
    marker = [model, database.metadata('analysis_generation', 0)]
    if database.metadata('catalog_scheduling_generation', None) == marker:
        return
    with database.connect() as db:
        db.execute(
            'INSERT OR IGNORE INTO catalog_pending(id) SELECT l.id FROM catalog_live l JOIN tracks t ON t.id=l.id LEFT JOIN analyses a ON a.id=t.id AND a.model=? AND a.fingerprint=t.fingerprint WHERE a.id IS NULL',
            (model,),
        )
        db.execute(
            'DELETE FROM catalog_pending WHERE id IN (SELECT a.id FROM analyses a JOIN tracks t ON a.id=t.id AND a.fingerprint=t.fingerprint WHERE a.model=?)',
            (model,),
        )
        db.execute(
            "INSERT OR REPLACE INTO metadata VALUES ('catalog_scheduling_generation',?)",
            (json.dumps(marker),),
        )


def unanalysed(database, model, *, limit=25):
    """Live tracks with no current analysis and no queued or exhausted retry.

    A track whose analysis row vanished without a catalog change (a full native
    resync, a lost write) used to stay invisible forever: it was neither
    analysed nor pending. This bounded query is the only way back in, and it
    skips tracks whose analysis job already used its retries so a broken file
    never becomes an endless queue. The exhausted set is read once instead of a
    correlated subquery, which kept the plan slow on a full library.
    """
    restriction = (
        ' JOIN catalog_live l ON l.id=t.id'
        if database.metadata('native_catalog_initialized', False)
        else ''
    )
    with database.connect() as db:
        rows = [
            row[0]
            for row in db.execute(
                'SELECT t.id FROM tracks t'
                + restriction
                + ' LEFT JOIN analyses a ON a.id=t.id AND a.model=? AND a.fingerprint=t.fingerprint'
                + ' LEFT JOIN catalog_pending p ON p.id=t.id'
                + ' WHERE a.id IS NULL AND p.id IS NULL ORDER BY t.id LIMIT ?',
                (model, limit * 4),
            )
        ]
        exhausted = {
            row[0]
            for row in db.execute(
                "SELECT DISTINCT json_extract(payload,'$.track') FROM jobs"
                " WHERE kind='analysis' AND state='failed' AND attempts>=3"
            )
        }
    return [value for value in rows if value not in exhausted][:limit]


def scheduled(database, identity):
    with database.connect() as db:
        db.execute('DELETE FROM catalog_pending WHERE id=?', (identity,))
