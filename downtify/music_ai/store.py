"""Independent derived database; never migrates the native library database."""

from __future__ import annotations

import json
import math
import secrets
import sqlite3
import struct
import time
from contextlib import contextmanager
from pathlib import Path

ANALYSIS_FEATURES = (
    'similarity',
    'personalization',
    'daily',
    'weekly',
)

DEFAULTS = {
    'personalization': False,
    'similarity': False,
    'daily': False,
    'weekly': False,
    'external_beta': False,
    'dj_prepared': False,
    'dj_weekly': False,
    'dj_interactive': False,
    'dj_trial': False,
}
MOODS = {
    'calme': 'Calm gentle music with soft dynamics',
    'concentration': 'Instrumental focused music with steady rhythm',
    'energie': 'Energetic upbeat music with a driving rhythm',
    'fete': 'Upbeat dance party music with a strong beat',
    'melancolie': 'Melancholic emotional music with a sad reflective mood',
    'detente': 'Relaxed warm soothing music for unwinding',
}

# Weekly genre themes narrow the catalog by its native tag and rank against
# the centroid of the genre's analysed tracks. They live outside MOODS so the
# analysis worker keeps publishing exactly the six pinned mood vectors that the
# bundled CLAP release supports (see encoder.verify_manifest / publish_model).
GENRE_THEMES = ('rap', 'rock', 'electro', 'pop')


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS preferences (
                    owner INTEGER PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tracks (
                    id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                    row_json TEXT NOT NULL, observed REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY REFERENCES tracks(id) ON DELETE CASCADE,
                    fingerprint TEXT NOT NULL, model TEXT NOT NULL,
                    vector BLOB NOT NULL, measured REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS mood_vectors (
                    mood TEXT NOT NULL, model TEXT NOT NULL, vector BLOB NOT NULL,
                    PRIMARY KEY(mood,model));
                CREATE TABLE IF NOT EXISTS listens (
                    owner INTEGER NOT NULL, event_id TEXT NOT NULL,
                    track TEXT NOT NULL, seconds REAL NOT NULL,
                    outcome TEXT NOT NULL, at REAL NOT NULL,
                    PRIMARY KEY(owner,event_id));
                CREATE INDEX IF NOT EXISTS listen_owner_time ON listens(owner,at);
                CREATE TABLE IF NOT EXISTS playlists (
                    owner INTEGER NOT NULL, cadence TEXT NOT NULL,
                    mood TEXT NOT NULL, period TEXT NOT NULL, ids TEXT NOT NULL,
                    created REAL NOT NULL,
                    PRIMARY KEY(owner,cadence,mood,period));
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                    payload TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'queued',
                    lease_until REAL NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT '');
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS source_versions (
                    id TEXT PRIMARY KEY REFERENCES tracks(id) ON DELETE CASCADE,
                    signature TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS catalog_live (id TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS catalog_pending (id TEXT PRIMARY KEY, priority REAL NOT NULL DEFAULT 0);
                CREATE INDEX IF NOT EXISTS catalog_pending_priority ON catalog_pending(priority DESC,id);
                CREATE TABLE IF NOT EXISTS compute_lease (id INTEGER PRIMARY KEY, token TEXT NOT NULL, kind TEXT NOT NULL, expires REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS listen_track_time ON listens(track,at);
            """)
            columns = {row[1] for row in db.execute('PRAGMA table_info(jobs)')}
            if 'lease_token' not in columns:
                db.execute(
                    "ALTER TABLE jobs ADD COLUMN lease_token TEXT NOT NULL DEFAULT ''"
                )
            for name, declaration in (
                ('attempts', 'INTEGER NOT NULL DEFAULT 0'),
                ('ready_at', 'REAL NOT NULL DEFAULT 0'),
                ('priority', 'REAL NOT NULL DEFAULT 0'),
            ):
                if name not in columns:
                    db.execute(
                        f'ALTER TABLE jobs ADD COLUMN {name} {declaration}'
                    )
            listen_columns = {
                row[1] for row in db.execute('PRAGMA table_info(listens)')
            }
            if 'sequence' not in listen_columns:
                db.execute(
                    'ALTER TABLE listens ADD COLUMN sequence INTEGER NOT NULL DEFAULT 0'
                )
            # Track-level retry lookup for the reconciliation pass; bounded to analysis jobs.
            db.execute(
                "CREATE INDEX IF NOT EXISTS jobs_analysis_track ON jobs(json_extract(payload,'$.track')) WHERE kind='analysis'"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS jobs_rhythm_track ON jobs(json_extract(payload,'$.track'),json_extract(payload,'$.model'),json_extract(payload,'$.fingerprint')) WHERE kind='rhythm'"
            )
            self._freeze_existing_preferences(db)

    @staticmethod
    def _freeze_existing_preferences(db):
        """Preserve deployed choices; all new accounts/installations opt in."""
        db.execute('BEGIN IMMEDIATE')
        if db.execute(
            "SELECT 1 FROM metadata WHERE key='beta_defaults_v2'"
        ).fetchone():
            return
        rows = db.execute('SELECT owner,value FROM preferences').fetchall()
        legacy = {**DEFAULTS, **dict.fromkeys(ANALYSIS_FEATURES, True)}
        for row in rows:
            value = {**legacy, **json.loads(row['value'])}
            db.execute(
                'UPDATE preferences SET value=? WHERE owner=?',
                (json.dumps(value), row['owner']),
            )
        global_flags = legacy if rows else DEFAULTS
        db.execute(
            'INSERT OR IGNORE INTO preferences VALUES (-1,?)',
            (json.dumps(global_flags),),
        )
        db.execute("INSERT INTO metadata VALUES ('beta_defaults_v2','true')")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=15000')
        try:
            with db:
                yield db
        finally:
            db.close()

    def preferences(self, owner: int) -> dict[str, bool]:
        with self.connect() as db:
            row = db.execute(
                'SELECT value FROM preferences WHERE owner=?', (owner,)
            ).fetchone()
        merged = {**DEFAULTS, **(json.loads(row[0]) if row else {})}
        # Always emit booleans: the API contract is features/preferences as
        # {key: bool}. Stored values can drift to truthy ints (e.g. 1) via other
        # writers, which would break the clients' Map<String,Boolean> decoding.
        return {key: bool(value) for key, value in merged.items()}

    def effective(self, owner: int) -> dict[str, bool]:
        global_flags = self.preferences(-1)
        own = self.preferences(owner)
        return {key: bool(global_flags[key] and own[key]) for key in DEFAULTS}

    def ensure_user(self, owner: int):
        if owner <= 0:
            raise ValueError('A user identity is required')
        with self.connect() as db:
            if db.execute(
                'SELECT 1 FROM preferences WHERE owner=?', (owner,)
            ).fetchone():
                return
            db.execute(
                'INSERT OR IGNORE INTO preferences VALUES (?,?)',
                (owner, json.dumps(DEFAULTS)),
            )

    def set_preferences(self, owner: int, changes: dict):
        if not isinstance(changes, dict) or any(
            key not in DEFAULTS or type(value) is not bool
            for key, value in changes.items()
        ):
            raise ValueError('Unknown feature or non-boolean value')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                'SELECT value FROM preferences WHERE owner=?', (owner,)
            ).fetchone()
            prior = {
                **DEFAULTS,
                **(json.loads(row[0]) if row else {}),
            }
            flags = {**prior, **changes}
            db.execute(
                'INSERT OR REPLACE INTO preferences VALUES (?,?)',
                (owner, json.dumps(flags)),
            )
            if prior['personalization'] and not flags['personalization']:
                users = (
                    [owner]
                    if owner > 0
                    else [
                        row[0]
                        for row in db.execute(
                            'SELECT owner FROM preferences WHERE owner>0 UNION SELECT owner FROM listens WHERE owner>0'
                        )
                    ]
                )
                for uid in users:
                    key = f'profile_revision:{uid}'
                    old = db.execute(
                        'SELECT value FROM metadata WHERE key=?', (key,)
                    ).fetchone()
                    db.execute(
                        'INSERT OR REPLACE INTO metadata VALUES (?,?)',
                        (
                            key,
                            json.dumps((json.loads(old[0]) if old else 0) + 1),
                        ),
                    )
        return self.effective(owner) if owner != -1 else flags

    def observe(self, rows: list[dict]):
        if any(
            not row.get('id') or not row.get('fingerprint') for row in rows
        ):
            raise ValueError('Stable id and fingerprint required')
        for offset in range(0, len(rows), 256):
            chunk = rows[offset : offset + 256]
            # Serialize outside the write transaction. Most interactive reads
            # observe an unchanged catalog and must never acquire a writer lock.
            values = [
                (row['id'], row['fingerprint'], json.dumps(row), time.time())
                for row in chunk
            ]
            with self.connect() as db:
                current = {
                    row['id']: (row['fingerprint'], row['row_json'])
                    for row in db.execute(
                        'SELECT id,fingerprint,row_json FROM tracks WHERE id IN ('
                        + ','.join('?' for _ in chunk)
                        + ')',
                        [row['id'] for row in chunk],
                    )
                }
            changed = [
                value
                for value in values
                if current.get(value[0]) != (value[1], value[2])
            ]
            if not changed:
                continue
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                db.executemany(
                    """INSERT INTO tracks VALUES (?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET fingerprint=excluded.fingerprint,
                    row_json=excluded.row_json, observed=excluded.observed
                    WHERE tracks.fingerprint!=excluded.fingerprint
                    OR tracks.row_json!=excluded.row_json""",
                    changed,
                )
                db.executemany(
                    'DELETE FROM analyses WHERE id=? AND fingerprint!=?',
                    [(value[0], value[1]) for value in changed],
                )

    @staticmethod
    def pack(vector):
        values = [float(v) for v in vector]
        if len(values) != 512 or not all(math.isfinite(v) for v in values):
            raise ValueError('Expected 512 finite components')
        norm = math.sqrt(sum(v * v for v in values))
        if norm < 1e-12:
            raise ValueError('Empty embedding')
        return struct.pack('<512f', *(v / norm for v in values))

    def observe_source(self, track, signature):
        """Invalidate derived audio even for equal-size, same-second replacements."""
        value = json.dumps(signature)
        with self.connect() as db:
            previous = db.execute(
                'SELECT signature FROM source_versions WHERE id=?', (track,)
            ).fetchone()
            if previous is not None and previous[0] == value:
                return True
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute(
                'SELECT signature FROM source_versions WHERE id=?', (track,)
            ).fetchone()
            if previous is None or previous[0] != value:
                db.execute('DELETE FROM analyses WHERE id=?', (track,))
                db.execute(
                    'INSERT OR IGNORE INTO catalog_pending(id) SELECT id FROM tracks WHERE id=?',
                    (track,),
                )
                db.execute(
                    'INSERT OR REPLACE INTO source_versions VALUES (?,?)',
                    (track, value),
                )
                return False
            return True

    def put_analysis(
        self,
        track: str,
        fingerprint: str,
        model: str,
        vector,
        *,
        generation=None,
        source_version=None,
    ):
        blob = self.pack(vector)
        with self.connect() as db:
            # Recheck inside the transaction: the worker may have analyzed an
            # old file while a download replaced it.
            db.execute('BEGIN IMMEDIATE')
            if generation is not None:
                paused = db.execute(
                    "SELECT value FROM metadata WHERE key='analysis_paused'"
                ).fetchone()
                flags_row = db.execute(
                    'SELECT value FROM preferences WHERE owner=-1'
                ).fetchone()
                flags = {
                    **DEFAULTS,
                    **(json.loads(flags_row[0]) if flags_row else {}),
                }
                if (paused and json.loads(paused[0])) or not any(
                    flags[k] for k in ANALYSIS_FEATURES
                ):
                    return False
                current = db.execute(
                    "SELECT value FROM metadata WHERE key='analysis_generation'"
                ).fetchone()
                if generation != (json.loads(current[0]) if current else 0):
                    return False
            row = db.execute(
                'SELECT fingerprint FROM tracks WHERE id=?', (track,)
            ).fetchone()
            if row is None or row[0] != fingerprint:
                return False
            if source_version is not None:
                source = db.execute(
                    'SELECT signature FROM source_versions WHERE id=?',
                    (track,),
                ).fetchone()
                if source is None or source[0] != json.dumps(source_version):
                    return False
            db.execute(
                'INSERT OR REPLACE INTO analyses VALUES (?,?,?,?,?)',
                (track, fingerprint, model, blob, time.time()),
            )
        return True

    def vectors(self, model: str, allowed: set[str]):
        import numpy as np

        result = {}
        identities = list(allowed)
        if not identities:
            return result
        with self.connect() as db:
            for offset in range(0, len(identities), 500):
                chunk = identities[offset : offset + 500]
                marks = ','.join('?' for _ in chunk)
                cursor = db.execute(
                    'SELECT a.id,a.vector FROM analyses a JOIN tracks t '
                    f'ON a.id=t.id AND a.fingerprint=t.fingerprint WHERE a.model=? AND a.id IN ({marks})',
                    (model, *chunk),
                )
                result.update({
                    row['id']: np.frombuffer(row['vector'], dtype='<f4')
                    for row in cursor
                })
        return result

    def listen(
        self,
        owner: int,
        event_id: str,
        track: str,
        seconds: float,
        outcome: str,
        *,
        at: float | None = None,
        sequence: int = 0,
        generation: int = 0,
    ):
        if not self.effective(owner)['personalization']:
            return False
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
            raise ValueError('Invalid event id')
        if outcome not in {'complete', 'skip', 'error', 'pause'}:
            raise ValueError('Invalid playback outcome')
        if not math.isfinite(seconds) or not 0 <= seconds <= 86400:
            raise ValueError('Invalid listened duration')
        if type(sequence) is not int or not 0 <= sequence <= 1000000:
            raise ValueError('Invalid event revision')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            revision = db.execute(
                'SELECT value FROM metadata WHERE key=?',
                (f'profile_revision:{owner}',),
            ).fetchone()
            if generation != (json.loads(revision[0]) if revision else 0):
                return False
            preferences = {
                row[0]: {**DEFAULTS, **json.loads(row[1])}
                for row in db.execute(
                    'SELECT owner,value FROM preferences WHERE owner IN (-1,?)',
                    (owner,),
                )
            }
            if not all(
                preferences.get(uid, DEFAULTS)['personalization']
                for uid in (-1, owner)
            ):
                return False
            if not db.execute(
                'SELECT 1 FROM tracks WHERE id=?', (track,)
            ).fetchone():
                raise ValueError('Unknown track')
            return bool(
                db.execute(
                    """INSERT INTO listens(owner,event_id,track,seconds,outcome,at,sequence)
                    VALUES (?,?,?,?,?,?,?) ON CONFLICT(owner,event_id) DO UPDATE SET
                    seconds=MAX(listens.seconds,excluded.seconds),outcome=excluded.outcome,
                    sequence=excluded.sequence
                    WHERE excluded.sequence>listens.sequence AND excluded.track=listens.track""",
                    (
                        owner,
                        event_id,
                        track,
                        seconds,
                        outcome,
                        at if at is not None else time.time(),
                        sequence,
                    ),
                ).rowcount
            )

    def history(self, owner: int):
        if not self.effective(owner)['personalization']:
            return []
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    'SELECT * FROM listens WHERE owner=? AND at>? ORDER BY at DESC LIMIT 2000',
                    (owner, time.time() - 180 * 86400),
                )
            ]

    def forget(self, owner: int):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            revision = db.execute(
                'SELECT value FROM metadata WHERE key=?',
                (f'profile_revision:{owner}',),
            ).fetchone()
            db.execute(
                'INSERT OR REPLACE INTO metadata VALUES (?,?)',
                (
                    f'profile_revision:{owner}',
                    json.dumps(
                        (json.loads(revision[0]) if revision else 0) + 1
                    ),
                ),
            )
            db.execute('DELETE FROM listens WHERE owner=?', (owner,))
            db.execute('DELETE FROM playlists WHERE owner=?', (owner,))
            db.execute(
                'DELETE FROM metadata WHERE key IN (?,?,?)',
                (
                    f'playlist_rotation_history:{owner}',
                    f'playlist_refresh_receipts:{owner}',
                    f'selection_revision:{owner}',
                ),
            )

    def enqueue(self, identity: str, kind: str, payload: dict, *, priority=0):
        with self.connect() as db:
            return bool(
                db.execute(
                    'INSERT OR IGNORE INTO jobs(id,kind,payload,priority) VALUES (?,?,?,?)',
                    (identity, kind, json.dumps(payload), priority),
                ).rowcount
            )

    def claim(self, *, now=None, lease=300, kind=None):
        now = time.time() if now is None else now
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                """SELECT * FROM jobs WHERE (? IS NULL OR kind=?) AND (
                (state='queued' AND ready_at<=?)
                OR (state='failed' AND attempts<3 AND ready_at<=?)
                OR (state='running' AND lease_until<?))
                ORDER BY priority DESC,rowid LIMIT 1""",
                (kind, kind, now, now, now),
            ).fetchone()
            if row is None:
                return None
            token = secrets.token_hex(16)
            db.execute(
                "UPDATE jobs SET state='running',lease_until=?,lease_token=?,attempts=attempts+1 WHERE id=?",
                (now + lease, token, row['id']),
            )
            return {
                **dict(row),
                'attempts': row['attempts'] + 1,
                'lease_token': token,
                'payload': json.loads(row['payload']),
            }

    def finish(self, job, state='done', error=''):
        if state not in {'done', 'failed', 'queued'}:
            raise ValueError('Invalid job state')
        with self.connect() as db:
            return bool(
                db.execute(
                    'UPDATE jobs SET state=?,error=?,lease_until=0,ready_at=?, '
                    'attempts=MAX(0,attempts-?) '
                    "WHERE id=? AND lease_token=? AND state='running'",
                    (
                        state,
                        error,
                        time.time()
                        + min(3600, 60 * 2 ** min(job['attempts'], 5))
                        if state == 'failed'
                        else 0,
                        int(state == 'queued'),
                        job['id'],
                        job['lease_token'],
                    ),
                ).rowcount
            )

    def renew(self, job, lease=300):
        with self.connect() as db:
            return bool(
                db.execute(
                    'UPDATE jobs SET lease_until=? WHERE id=? '
                    "AND lease_token=? AND state='running'",
                    (time.time() + lease, job['id'], job['lease_token']),
                ).rowcount
            )

    def retry_analyses(self):
        with self.connect() as db:
            return db.execute(
                "UPDATE jobs SET state='queued',attempts=0,ready_at=0,error='' "
                "WHERE kind='analysis' AND state='failed'"
            ).rowcount

    def analysis_status(self):
        identity = self.metadata('model', {}).get('id', '')
        with self.connect() as db:
            known = db.execute('SELECT COUNT(*) FROM tracks').fetchone()[0]
            analyzed = db.execute(
                'SELECT COUNT(*) FROM analyses a JOIN tracks t '
                'ON a.id=t.id AND a.fingerprint=t.fingerprint WHERE a.model=?',
                (identity,),
            ).fetchone()[0]
            jobs = {
                row[0]: row[1]
                for row in db.execute(
                    "SELECT state,COUNT(*) FROM jobs WHERE kind='analysis' GROUP BY state"
                )
            }
        return {
            'known': known,
            'analyzed': analyzed,
            'jobs': jobs,
            'paused': self.metadata('analysis_paused', False),
        }

    def clear_analyses(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                "SELECT value FROM metadata WHERE key='analysis_generation'"
            ).fetchone()
            generation = (json.loads(row[0]) if row else 0) + 1
            for key, value in [
                ('analysis_generation', generation),
                ('analysis_paused', True),
                ('model', {'ready': False, 'state': 'paused'}),
                ('dj', {'ready': False, 'state': 'paused'}),
            ]:
                db.execute(
                    'INSERT OR REPLACE INTO metadata VALUES (?,?)',
                    (key, json.dumps(value)),
                )
            db.execute('DELETE FROM analyses')
            db.execute('DELETE FROM mood_vectors')
            db.execute('DELETE FROM playlists')
            db.execute(
                "UPDATE jobs SET state='cancelled' WHERE kind='analysis'"
            )
            tables = {
                row[0]
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('dj_profiles','dj_sessions')"
                )
            }
            if 'dj_profiles' in tables:
                db.execute('DELETE FROM dj_profiles')
            if 'dj_sessions' in tables:
                db.execute(
                    "UPDATE dj_sessions SET state='cancelled',lease_token='',lease_until=0 WHERE state IN ('queued','preparing','rendering','playing','paused')"
                )

    def publish_model(self, model, vectors, generation):
        """Fence model initialization against deletion and module shutdown."""
        blobs = {mood: self.pack(vector) for mood, vector in vectors.items()}
        if set(blobs) != set(MOODS):
            raise ValueError('All mood vectors are required')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            metadata = {
                row[0]: json.loads(row[1])
                for row in db.execute('SELECT key,value FROM metadata')
            }
            row = db.execute(
                'SELECT value FROM preferences WHERE owner=-1'
            ).fetchone()
            flags = {**DEFAULTS, **(json.loads(row[0]) if row else {})}
            if (
                generation != metadata.get('analysis_generation', 0)
                or metadata.get('analysis_paused', False)
                or not any(flags[k] for k in ANALYSIS_FEATURES)
            ):
                return False
            db.executemany(
                'INSERT OR REPLACE INTO mood_vectors VALUES (?,?,?)',
                [(mood, model, blob) for mood, blob in blobs.items()],
            )
            db.execute(
                'INSERT OR REPLACE INTO metadata VALUES (?,?)',
                ('model', json.dumps({'id': model, 'ready': True})),
            )
        return True

    def metadata(self, key, default=None):
        with self.connect() as db:
            row = db.execute(
                'SELECT value FROM metadata WHERE key=?', (key,)
            ).fetchone()
        return json.loads(row[0]) if row else default

    def set_metadata(self, key, value):
        with self.connect() as db:
            db.execute(
                'INSERT OR REPLACE INTO metadata VALUES (?,?)',
                (key, json.dumps(value)),
            )
