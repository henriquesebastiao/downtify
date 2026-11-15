"""Private derived DJ state and a single leased renderer, independent of playback."""

from __future__ import annotations

import hashlib
import json
import math
import secrets
import time
from datetime import date

from .store import DEFAULTS, GENRE_THEMES, MOODS, Store

ACTIVE = ('preparing', 'rendering', 'playing', 'paused')
MODES = {'prepared': 'dj_prepared', 'interactive': 'dj_interactive'}


def permitted(db, owner, mode):
    """Feature flags only: a paused analysis never blocks a live set."""
    feature = MODES[mode]
    flags = {}
    for identity in (-1, owner):
        row = db.execute(
            'SELECT value FROM preferences WHERE owner=?', (identity,)
        ).fetchone()
        flags[identity] = {**DEFAULTS, **(json.loads(row[0]) if row else {})}
    return flags[-1][feature] and flags[owner][feature]


def enabled(db, owner, mode):
    paused = db.execute(
        "SELECT value FROM metadata WHERE key='analysis_paused'"
    ).fetchone()
    if paused and json.loads(paused[0]):
        return False
    return permitted(db, owner, mode)


class CancelledDjRequest(Exception):
    pass


class DjStore:
    def __init__(self, database: Store):
        self.database = database
        with database.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS dj_sessions (
                    id TEXT PRIMARY KEY, owner INTEGER NOT NULL, mode TEXT NOT NULL,
                    state TEXT NOT NULL, document TEXT NOT NULL,
                    created REAL NOT NULL, updated REAL NOT NULL,
                    lease_token TEXT NOT NULL DEFAULT '', lease_until REAL NOT NULL DEFAULT 0);
                CREATE INDEX IF NOT EXISTS dj_sessions_owner ON dj_sessions(owner,created);
                CREATE TABLE IF NOT EXISTS dj_sources (
                    session TEXT NOT NULL REFERENCES dj_sessions(id) ON DELETE CASCADE,
                    track TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(session,track));
                CREATE TABLE IF NOT EXISTS dj_profiles (
                    track TEXT NOT NULL, model TEXT NOT NULL,
                    fingerprint TEXT NOT NULL, source_version TEXT NOT NULL,
                    value TEXT NOT NULL, PRIMARY KEY(track,model));
                CREATE TABLE IF NOT EXISTS dj_commands (
                    session TEXT NOT NULL REFERENCES dj_sessions(id) ON DELETE CASCADE,
                    nonce TEXT NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL,
                    queued REAL NOT NULL, state TEXT NOT NULL DEFAULT 'queued',
                    PRIMARY KEY(session,nonce));
                CREATE TABLE IF NOT EXISTS dj_requests (
                    owner INTEGER NOT NULL, nonce TEXT NOT NULL, intent TEXT NOT NULL,
                    session TEXT NOT NULL REFERENCES dj_sessions(id) ON DELETE CASCADE,
                    PRIMARY KEY(owner,nonce));
                CREATE TABLE IF NOT EXISTS dj_command_results (
                    session TEXT NOT NULL REFERENCES dj_sessions(id) ON DELETE CASCADE,
                    nonce TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(session,nonce));
                CREATE TABLE IF NOT EXISTS dj_validation_receipts (
                    session TEXT PRIMARY KEY REFERENCES dj_sessions(id) ON DELETE CASCADE,
                    value TEXT NOT NULL);
            """)

    @staticmethod
    def unpack(row):
        return {
            **json.loads(row['document']),
            'id': row['id'],
            'owner': row['owner'],
            'mode': row['mode'],
            'state': row['state'],
            'created': row['created'],
            'updated': row['updated'],
        }

    def create(
        self,
        owner,
        mode,
        theme,
        ids,
        sources,
        *,
        nonce=None,
        validation=False,
        request_intent=None,
        selection_basis='explicit',
        queue_order=False,
        continuous=False,
        seed_id='',
        trial=False,
        style='library',
        background=None,
    ):
        if type(validation) is not bool or (
            validation and mode != 'interactive'
        ):
            raise ValueError('Invalid validation mode')
        if (
            type(owner) is not int
            or owner <= 0
            or mode not in MODES
            or theme not in MOODS
            or not 2 <= len(ids) <= 40
            or (not queue_order and len(set(ids)) != len(ids))
            or len(set(ids)) < 2
            or set(sources) != set(ids)
            or any(
                not isinstance(identity, str) or not 1 <= len(identity) <= 80
                for identity in ids
            )
        ):
            raise ValueError(
                'Choose a bounded selection of distinct local tracks'
            )
        if (
            type(queue_order) is not bool
            or type(continuous) is not bool
            or ((queue_order or continuous) and mode != 'interactive')
        ):
            raise ValueError('Invalid live queue mode')
        if nonce is not None and (
            not isinstance(nonce, str) or not 1 <= len(nonce) <= 128
        ):
            raise ValueError('Invalid request identifier')
        intent_data = [mode, theme, ids]
        if validation:
            intent_data.append({'validation': True})
        intent = request_intent or json.dumps(
            intent_data, separators=(',', ':')
        )
        if (
            not isinstance(intent, str)
            or not 1 <= len(intent) <= 8192
            or selection_basis
            not in {'explicit', 'audio_similarity', 'dj_analysis'}
        ):
            raise ValueError('Invalid selection intent')
        if background is not None:
            required = {
                'weekly_period',
                'weekly_theme',
                'profile_revision',
                'selection_revision',
                'analysis_generation',
            }
            if (
                mode != 'prepared'
                or not isinstance(background, dict)
                or set(background) != required
                or background['weekly_theme'] not in {*MOODS, *GENRE_THEMES}
                or any(
                    type(background[key]) is not int or background[key] < 0
                    for key in (
                        'profile_revision',
                        'selection_revision',
                        'analysis_generation',
                    )
                )
                or not isinstance(background['weekly_period'], str)
                or date.fromisoformat(background['weekly_period']).weekday()
                != 0
            ):
                raise ValueError('Invalid weekly render')
        identity, now = secrets.token_hex(16), time.time()
        document = {
            'theme': theme,
            'ids': ids,
            'position': 0.0,
            'rendered': 0.0,
            'next_mutable_at': 0.0,
            'revision': 0,
            'error': '',
            'selection_basis': selection_basis,
        }
        if background is not None:
            document.update(background, background=True)
        if validation:
            document['validation'] = True
        if queue_order:
            document['queue_order'] = True
        if continuous:
            document['continuous'] = True
            document['style'] = style
        if seed_id:
            if seed_id != ids[0]:
                raise ValueError('Seed must start the selection')
            document['seed_id'] = seed_id
        if trial:
            document['trial'] = True
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not enabled(db, owner, mode):
                raise PermissionError('DJ module disabled')
            if background is not None:
                from .dj_background import allowed

                if not allowed(db, owner, document, now=now):
                    raise PermissionError(
                        'Weekly module disabled or invalidated'
                    )
            if nonce:
                cancelled = db.execute(
                    'SELECT value FROM metadata WHERE key=?',
                    (self.cancellation_key(owner, nonce),),
                ).fetchone()
                if cancelled and json.loads(cancelled[0]) > now:
                    raise CancelledDjRequest('DJ creation was cancelled')
            previous = (
                db.execute(
                    'SELECT intent,session FROM dj_requests WHERE owner=? AND nonce=?',
                    (owner, nonce),
                ).fetchone()
                if nonce
                else None
            )
            if previous:
                if previous['intent'] != intent:
                    raise ValueError('Request identifier already used')
                return self.unpack(
                    db.execute(
                        'SELECT * FROM dj_sessions WHERE id=?',
                        (previous['session'],),
                    ).fetchone()
                )
            count = db.execute(
                "SELECT count(*) FROM dj_sessions WHERE owner=? AND state='queued' AND COALESCE(json_extract(document,'$.background'),0)!=1",
                (owner,),
            ).fetchone()[0]
            if count >= 2:
                raise RuntimeError('Two DJ requests are already waiting')
            if (
                background is not None
                and db.execute(
                    "SELECT 1 FROM dj_sessions WHERE COALESCE(json_extract(document,'$.background'),0)=1 AND state IN ('queued','preparing','rendering') LIMIT 1"
                ).fetchone()
            ):
                raise RuntimeError('A weekly render is already waiting')
            db.execute(
                'INSERT INTO dj_sessions(id,owner,mode,state,document,created,updated) VALUES (?,?,?,?,?,?,?)',
                (
                    identity,
                    owner,
                    mode,
                    'queued',
                    json.dumps(document),
                    now,
                    now,
                ),
            )
            db.executemany(
                'INSERT INTO dj_sources VALUES (?,?,?)',
                [
                    (identity, track, json.dumps(sources[track]))
                    for track in dict.fromkeys(ids)
                ],
            )
            if nonce:
                db.execute(
                    'INSERT INTO dj_requests VALUES (?,?,?,?)',
                    (owner, nonce, intent, identity),
                )
        return self.get(owner, identity)

    def find_request(self, owner, nonce, intent):
        with self.database.connect() as db:
            row = db.execute(
                'SELECT r.intent,s.* FROM dj_requests r JOIN dj_sessions s ON r.session=s.id WHERE r.owner=? AND r.nonce=?',
                (owner, nonce),
            ).fetchone()
        if row is None:
            return None
        if row['intent'] != intent:
            raise ValueError('Request identifier already used')
        return self.unpack(row)

    @staticmethod
    def cancellation_key(owner, nonce):
        return (
            f'dj_cancel:{owner}:' + hashlib.sha256(nonce.encode()).hexdigest()
        )

    def request_cancelled(self, owner, nonce):
        return (
            self.database.metadata(self.cancellation_key(owner, nonce), 0)
            > time.time()
        )

    def cancel_request(self, owner, nonce):
        now = time.time()
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute(
                'INSERT OR REPLACE INTO metadata VALUES (?,?)',
                (self.cancellation_key(owner, nonce), json.dumps(now + 900)),
            )
            db.execute(
                "UPDATE dj_sessions SET state='cancelled',lease_token='',lease_until=0,updated=? WHERE owner=? AND id IN (SELECT session FROM dj_requests WHERE owner=? AND nonce=?) AND state NOT IN ('deleted','deleting','cancelled','stopped','failed')",
                (now, owner, owner, nonce),
            )
            db.execute(
                "DELETE FROM metadata WHERE key LIKE 'dj_cancel:%' AND CAST(value AS REAL)<?",
                (now,),
            )

    def get(self, owner, identity):
        with self.database.connect() as db:
            row = db.execute(
                'SELECT * FROM dj_sessions WHERE id=? AND owner=?',
                (identity, owner),
            ).fetchone()
        if row is None:
            raise LookupError('DJ session unavailable')
        return self.unpack(row)

    def list(self, owner):
        with self.database.connect() as db:
            rows = db.execute(
                "SELECT * FROM dj_sessions WHERE owner=? AND state!='deleted' AND COALESCE(json_extract(document,'$.background'),0)!=1 ORDER BY created DESC LIMIT 20",
                (owner,),
            ).fetchall()
        return [self.unpack(row) for row in rows]

    def source_paths(self, owner, identity):
        with self.database.connect() as db:
            rows = db.execute(
                'SELECT s.track,s.value FROM dj_sources s JOIN dj_sessions j ON j.id=s.session WHERE j.id=? AND j.owner=?',
                (identity, owner),
            ).fetchall()
        return {
            row['track']: json.loads(row['value']).get('path') for row in rows
        }

    def sources(self, owner, identity):
        with self.database.connect() as db:
            return {
                row[0]: json.loads(row[1])
                for row in db.execute(
                    'SELECT s.track,s.value FROM dj_sources s JOIN dj_sessions j ON j.id=s.session WHERE j.owner=? AND j.id=?',
                    (owner, identity),
                )
            }

    def replenish(self, owner, identity, ids, sources):
        """Accept a small currently authorized continuation, never revive a retired render."""
        if not 1 <= len(ids) <= 4 or set(ids) != set(sources):
            raise ValueError('Invalid continuation')
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                'SELECT * FROM dj_sessions WHERE owner=? AND id=?',
                (owner, identity),
            ).fetchone()
            if (
                row is None
                or row['state'] not in ACTIVE
                or not enabled(db, owner, 'interactive')
            ):
                return False
            document = json.loads(row['document'])
            if not document.get('continuous') or document.get('queue_order'):
                return False
            fresh = [track for track in ids if track not in document['ids']]
            if not fresh:
                return False
            document['ids'] = (document['ids'] + fresh)[-80:]
            document['refill_revision'] = (
                document.get('refill_revision', 0) + 1
            )
            document['refilled_at'] = time.time()
            db.executemany(
                'INSERT OR REPLACE INTO dj_sources VALUES (?,?,?)',
                [
                    (identity, track, json.dumps(sources[track]))
                    for track in fresh
                ],
            )
            db.execute(
                'UPDATE dj_sessions SET document=? WHERE id=?',
                (json.dumps(document), identity),
            )
            return True

    def claim(self, *, now=None, seconds=45):
        now = time.time() if now is None else now
        token = secrets.token_hex(24)
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            active = db.execute(
                "SELECT * FROM dj_sessions WHERE state IN ('preparing','rendering','playing','paused')"
            ).fetchall()
            for row in active:
                document = json.loads(row['document'])
                if document.get('background'):
                    from .dj_background import allowed

                    if not allowed(db, row['owner'], document, now=now):
                        db.execute(
                            "UPDATE dj_sessions SET state='cancelled',lease_token='',lease_until=0,updated=? WHERE id=?",
                            (now, row['id']),
                        )
                    elif row['lease_until'] > now:
                        return None
                    else:
                        document.update(phase='queued', progress=0.0, error='')
                        db.execute(
                            "UPDATE dj_sessions SET state='queued',document=?,lease_token='',lease_until=0,updated=? WHERE id=?",
                            (json.dumps(document), now, row['id']),
                        )
                    continue
                if not enabled(db, row['owner'], row['mode']):
                    db.execute(
                        "UPDATE dj_sessions SET state='cancelled',lease_token='',lease_until=0,updated=? WHERE id=?",
                        (now, row['id']),
                    )
                elif row['lease_until'] > now:
                    return None
                else:
                    document = json.loads(row['document'])
                    document['error'] = (
                        'Le rendu a été interrompu. Relancez une session.'
                    )
                    db.execute(
                        "UPDATE dj_sessions SET state='failed',document=?,lease_token='',lease_until=0,updated=? WHERE id=?",
                        (json.dumps(document), now, row['id']),
                    )
            queued = db.execute(
                "SELECT * FROM dj_sessions WHERE state='queued' ORDER BY COALESCE(json_extract(document,'$.background'),0),CASE WHEN mode='interactive' THEN 0 ELSE 1 END,created,id"
            ).fetchall()
            for row in queued:
                document = json.loads(row['document'])
                if document.get('background'):
                    from .dj_background import allowed, blocked, workspace

                    if not allowed(db, row['owner'], document, now=now):
                        db.execute(
                            "UPDATE dj_sessions SET state='cancelled',updated=? WHERE id=?",
                            (now, row['id']),
                        )
                        continue
                    if document.get('retry_at', 0) > now or blocked(db):
                        continue
                    document['render_workspace'] = workspace(row['id'], token)
                    db.execute(
                        'UPDATE dj_sessions SET document=? WHERE id=?',
                        (json.dumps(document), row['id']),
                    )
                if not enabled(db, row['owner'], row['mode']):
                    db.execute(
                        "UPDATE dj_sessions SET state='cancelled',updated=? WHERE id=?",
                        (now, row['id']),
                    )
                    continue
                db.execute(
                    "UPDATE dj_sessions SET state='preparing',lease_token=?,lease_until=?,updated=? WHERE id=?",
                    (token, now + seconds, now, row['id']),
                )
                sources = {
                    item['track']: json.loads(item['value'])
                    for item in db.execute(
                        'SELECT track,value FROM dj_sources WHERE session=?',
                        (row['id'],),
                    )
                }
                return {
                    **self.unpack(row),
                    **document,
                    'state': 'preparing',
                    'lease_token': token,
                    'sources': sources,
                }
        return None

    def defer_background(self, identity, token, *, now=None):
        from .dj_background import allowed

        now = time.time() if now is None else now
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                'SELECT * FROM dj_sessions WHERE id=? AND lease_token=?',
                (identity, token),
            ).fetchone()
            if row is None or row['state'] not in ACTIVE:
                return False
            document = json.loads(row['document'])
            if not document.get('background'):
                return False
            state = (
                'queued'
                if allowed(db, row['owner'], document, now=now)
                else 'cancelled'
            )
            document.update(
                phase=state, progress=0.0, error='', retry_at=now + 5
            )
            for key in ('timeline', 'duration', 'asset_workspace'):
                document.pop(key, None)
            db.execute(
                "UPDATE dj_sessions SET state=?,document=?,lease_token='',lease_until=0,updated=? WHERE id=? AND lease_token=?",
                (state, json.dumps(document), now, identity, token),
            )
            return True

    def workspace(self, identity):
        with self.database.connect() as db:
            row = db.execute(
                'SELECT document FROM dj_sessions WHERE id=?', (identity,)
            ).fetchone()
        document = json.loads(row[0]) if row else {}
        return document.get(
            'asset_workspace', document.get('render_workspace', identity)
        )

    def publish(self, identity, token, state, changes=None, *, now=None):
        if state not in {*ACTIVE, 'ready', 'stopped', 'failed'}:
            raise ValueError('Invalid render state')
        now = time.time() if now is None else now
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                'SELECT * FROM dj_sessions WHERE id=? AND lease_token=? AND lease_until>?',
                (identity, token, now),
            ).fetchone()
            if row is None or row['state'] not in ACTIVE:
                return False
            captured = json.loads(row['document'])
            if captured.get('background'):
                from .dj_background import allowed, blocked

                if not allowed(db, row['owner'], captured, now=now):
                    db.execute(
                        "UPDATE dj_sessions SET state='cancelled',lease_token='',lease_until=0,updated=? WHERE id=?",
                        (now, identity),
                    )
                    return False
                if blocked(db):
                    return False
                if changes and any(
                    key in changes and changes[key] != captured.get(key)
                    for key in (
                        'background',
                        'weekly_period',
                        'weekly_theme',
                        'profile_revision',
                        'selection_revision',
                        'analysis_generation',
                        'render_workspace',
                    )
                ):
                    raise ValueError('Weekly render identity cannot change')
                if (
                    changes
                    and 'asset_workspace' in changes
                    and changes['asset_workspace']
                    != captured['render_workspace']
                ):
                    raise ValueError('Invalid weekly audio workspace')
            if not enabled(db, row['owner'], row['mode']):
                db.execute(
                    "UPDATE dj_sessions SET state='cancelled',lease_token='',lease_until=0,updated=? WHERE id=?",
                    (now, identity),
                )
                return False
            document = {**json.loads(row['document']), **(changes or {})}
            # Identity and ownership always come from columns, never mutable metadata.
            if any(
                key in document
                for key in ('id', 'owner', 'mode', 'lease_token')
            ):
                raise ValueError(
                    'Render metadata cannot replace session identity'
                )
            active = state in ACTIVE
            db.execute(
                'UPDATE dj_sessions SET state=?,document=?,updated=?,lease_token=?,lease_until=? WHERE id=?',
                (
                    state,
                    json.dumps(document),
                    now,
                    token if active else '',
                    now + 45 if active else 0,
                    identity,
                ),
            )
        return True

    def record_ready(self, owner, identity, *, now=None):
        """First manifest read: store the delay the listener actually waited for."""
        now = time.time() if now is None else now
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                'SELECT document,state,created FROM dj_sessions WHERE id=? AND owner=?',
                (identity, owner),
            ).fetchone()
            if row is None or row['state'] not in {
                'playing',
                'paused',
                'ready',
            }:
                return None
            document = json.loads(row['document'])
            if 'ready_seconds' in document:
                return None
            seconds = round(max(0.0, now - row['created']), 3)
            document.update(ready_seconds=seconds, ready_at=now)
            db.execute(
                'UPDATE dj_sessions SET document=? WHERE id=? AND owner=?',
                (json.dumps(document), identity, owner),
            )
        return seconds

    def consumer(self, owner, identity):
        """Record only an authenticated, ACL-checked HLS reader; no client identity."""
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                'SELECT document FROM dj_sessions WHERE owner=? AND id=?',
                (owner, identity),
            ).fetchone()
            if row is None:
                raise LookupError('DJ session unavailable')
            document = json.loads(row['document'])
            now = time.time()
            if now - document.get('listener_seen', 0) >= 5:
                document['listener_seen'] = now
                db.execute(
                    'UPDATE dj_sessions SET document=? WHERE id=?',
                    (json.dumps(document), identity),
                )

    def stop(self, owner, identity):
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                "SELECT id,mode,state FROM dj_sessions WHERE id=? AND owner=? AND state!='deleted'",
                (identity, owner),
            ).fetchone()
            if row is None:
                raise LookupError('DJ session unavailable')
            if row['mode'] == 'prepared' and row['state'] == 'ready':
                return  # Transport stop does not discard accepted immutable audio.
            db.execute(
                "UPDATE dj_sessions SET state='stopped',lease_token='',lease_until=0,updated=? WHERE id=?",
                (time.time(), identity),
            )

    def alive(self, identity, token, *, now=None):
        now = time.time() if now is None else now
        with self.database.connect() as db:
            row = db.execute(
                'SELECT * FROM dj_sessions WHERE id=? AND lease_token=? AND lease_until>?',
                (identity, token, now),
            ).fetchone()
            return bool(
                row
                and row['state'] in ACTIVE
                and enabled(db, row['owner'], row['mode'])
            )

    def discard(self, owner, identity):
        with self.database.connect() as db:
            cursor = db.execute(
                "UPDATE dj_sessions SET state='deleting',lease_token='',lease_until=0,updated=? WHERE id=? AND owner=?",
                (time.time(), identity, owner),
            )
            if not cursor.rowcount:
                raise LookupError('DJ session unavailable')

    def deletion_requests(self):
        with self.database.connect() as db:
            return [
                row[0]
                for row in db.execute(
                    "SELECT id FROM dj_sessions WHERE state='deleting'"
                )
            ]

    def deleted(self, identity):
        with self.database.connect() as db:
            db.execute(
                "UPDATE dj_sessions SET state='deleted',document='{}',updated=? WHERE id=? AND state='deleting'",
                (time.time(), identity),
            )
            db.execute('DELETE FROM dj_sources WHERE session=?', (identity,))

    def command(
        self,
        owner,
        identity,
        nonce,
        action,
        payload,
        *,
        now=None,
        navigation=None,
    ):
        now = time.time() if now is None else now
        if (
            not isinstance(nonce, str)
            or not 1 <= len(nonce) <= 128
            or action
            not in {'pause', 'resume', 'next', 'previous', 'replace', 'theme'}
            or not isinstance(payload, dict)
        ):
            raise ValueError('Invalid DJ command')
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                'SELECT * FROM dj_sessions WHERE id=? AND owner=?',
                (identity, owner),
            ).fetchone()
            if row is None:
                raise LookupError('DJ session unavailable')
            # Playback commands follow the user's choice: pausing the library
            # analysis must never interrupt a live set already rendered.
            if row['mode'] != 'interactive' or not permitted(
                db, owner, 'interactive'
            ):
                raise PermissionError('Interactive DJ unavailable')
            cached_navigation = navigation is not None and row['state'] in {
                'playing',
                'paused',
                'ready',
            }
            if not cached_navigation and (
                row['state'] not in ACTIVE or row['lease_until'] <= now
            ):
                raise RuntimeError('DJ session is not rendering')
            document = json.loads(row['document'])
            if action in {'pause', 'resume'} and payload:
                raise ValueError('This command has no payload')
            if action in {'next', 'previous'} and payload:
                if set(payload) != {'position'}:
                    raise ValueError('Invalid navigation payload')
                position = float(payload['position'])
                if (
                    not math.isfinite(position)
                    or not 0 <= position <= 1_000_000
                ):
                    raise ValueError('Invalid playback position')
            if action == 'previous' and navigation is None:
                raise ValueError('Previous requires a published marker')
            if action == 'theme' and (
                set(payload) != {'theme'}
                or not isinstance(payload['theme'], str)
                or payload['theme'] not in MOODS
            ):
                raise ValueError('Unknown musical theme')
            if action == 'replace' and (
                set(payload) != {'id'}
                or not isinstance(payload['id'], str)
                or payload['id'] not in document['ids']
            ):
                raise ValueError(
                    'Replacement must belong to this analyzed set'
                )
            previous = db.execute(
                'SELECT action,payload FROM dj_commands WHERE session=? AND nonce=?',
                (identity, nonce),
            ).fetchone()
            encoded = json.dumps(payload, sort_keys=True)
            if previous and (
                previous['action'] != action or previous['payload'] != encoded
            ):
                raise ValueError('Command identifier already used')
            db.execute(
                'INSERT OR IGNORE INTO dj_commands(session,nonce,action,payload,queued) VALUES (?,?,?,?,?)',
                (identity, nonce, action, encoded, now),
            )
            result = db.execute(
                'SELECT result FROM dj_command_results WHERE session=? AND nonce=?',
                (identity, nonce),
            ).fetchone()
            if result:
                return json.loads(result[0])
            if navigation is not None:
                db.execute(
                    'INSERT INTO dj_command_results VALUES (?,?,?)',
                    (identity, nonce, json.dumps(navigation)),
                )
                db.execute(
                    'UPDATE dj_commands SET state=? WHERE session=? AND nonce=?',
                    (
                        ('queued' if row['state'] in ACTIVE else 'applied')
                        if navigation['accepted']
                        else 'rejected',
                        identity,
                        nonce,
                    ),
                )
                return navigation
            delay = (
                0.0
                if action in {'pause', 'resume'}
                else max(
                    0.0,
                    float(document.get('next_mutable_at', 0))
                    - float(document.get('position', 0)),
                )
            )
            return {'accepted': True, 'effective_after_seconds': delay}

    def pending_commands(self, identity, token, *, now=None):
        now = time.time() if now is None else now
        with self.database.connect() as db:
            row = db.execute(
                'SELECT * FROM dj_sessions WHERE id=? AND lease_token=? AND lease_until>?',
                (identity, token, now),
            ).fetchone()
            if (
                not row
                or row['state'] not in ACTIVE
                or not enabled(db, row['owner'], row['mode'])
            ):
                raise PermissionError('DJ session stopped')
            return [
                {
                    'nonce': command[0],
                    'action': command[1],
                    'payload': json.loads(command[2]),
                    'navigation': json.loads(command[3])
                    if command[3]
                    else None,
                }
                for command in db.execute(
                    "SELECT c.nonce,c.action,c.payload,r.result FROM dj_commands c LEFT JOIN dj_command_results r ON c.session=r.session AND c.nonce=r.nonce WHERE c.session=? AND c.state='queued' ORDER BY c.queued,c.nonce LIMIT 32",
                    (identity,),
                )
            ]

    def complete_command(self, identity, token, nonce, result, *, now=None):
        now = time.time() if now is None else now
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                'SELECT * FROM dj_sessions WHERE id=? AND lease_token=? AND lease_until>?',
                (identity, token, now),
            ).fetchone()
            if (
                not row
                or row['state'] not in ACTIVE
                or not enabled(db, row['owner'], row['mode'])
            ):
                return False
            found = db.execute(
                "UPDATE dj_commands SET state=? WHERE session=? AND nonce=? AND state='queued'",
                (
                    'applied' if result.get('accepted') else 'rejected',
                    identity,
                    nonce,
                ),
            )
            if found.rowcount:
                db.execute(
                    'INSERT OR IGNORE INTO dj_command_results VALUES (?,?,?)',
                    (identity, nonce, json.dumps(result)),
                )
            return bool(found.rowcount)

    def command_results(self, identity):
        with self.database.connect() as db:
            return [
                {'request_id': row[0], **json.loads(row[1])}
                for row in db.execute(
                    'SELECT r.nonce,r.result FROM dj_command_results r JOIN dj_commands c ON r.session=c.session AND r.nonce=c.nonce WHERE r.session=? ORDER BY c.queued DESC LIMIT 10',
                    (identity,),
                )
            ]

    def profile(self, track, model, fingerprint, source_version):
        with self.database.connect() as db:
            row = db.execute(
                'SELECT value FROM dj_profiles WHERE track=? AND model=? AND fingerprint=? AND source_version=?',
                (track, model, fingerprint, json.dumps(source_version)),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def put_profile(
        self,
        track,
        model,
        fingerprint,
        source_version,
        value,
        *,
        generation=None,
        session=None,
        token=None,
        now=None,
    ):
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if generation is not None:
                metadata = {
                    row[0]: json.loads(row[1])
                    for row in db.execute(
                        "SELECT key,value FROM metadata WHERE key IN ('analysis_generation','analysis_paused')"
                    )
                }
                if metadata.get(
                    'analysis_paused', False
                ) or generation != metadata.get('analysis_generation', 0):
                    return False
            if session is not None:
                now = time.time() if now is None else now
                job = db.execute(
                    'SELECT * FROM dj_sessions WHERE id=? AND lease_token=? AND lease_until>?',
                    (session, token, now),
                ).fetchone()
                if (
                    not job
                    or job['state'] not in ACTIVE
                    or not enabled(db, job['owner'], job['mode'])
                ):
                    return False
            db.execute(
                'INSERT OR REPLACE INTO dj_profiles VALUES (?,?,?,?,?)',
                (
                    track,
                    model,
                    fingerprint,
                    json.dumps(source_version),
                    json.dumps(value),
                ),
            )
        return True
