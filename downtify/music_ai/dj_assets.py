"""Private immutable audio copies and lease-aware cache reclamation."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import shutil
import time

from .dj_audio import AudioError
from .dj_store import ACTIVE, DjStore, permitted


class Assets:
    def __init__(
        self,
        database,
        *,
        budget=5 * 1024**3,
        min_free=2 * 1024**3,
        margin=16 * 1024**2,
    ):
        self.database = database
        self.dj = DjStore(database)
        self.root = database.path.resolve().parent / 'dj'
        if self.root.is_symlink():
            raise AudioError('unsafe_cache_entry')
        self.root.mkdir(mode=0o700, exist_ok=True)
        self.budget, self.min_free, self.margin = budget, min_free, margin
        if not 0 < budget <= 5 * 1024**3 or min_free < 0 or margin < 0:
            raise ValueError('Invalid asset budget')
        with database.connect() as db:
            db.execute(
                'CREATE TABLE IF NOT EXISTS dj_asset_pins (session TEXT NOT NULL REFERENCES dj_sessions(id), consumer TEXT NOT NULL, expires REAL NOT NULL, PRIMARY KEY(session,consumer))'
            )

    def directory(self, name):
        if (
            not isinstance(name, str)
            or re.fullmatch('[a-f0-9]{32}', name) is None
        ):
            raise AudioError('unsafe_cache_entry')
        result = self.root / name
        if (
            self.root.is_symlink()
            or result.is_symlink()
            or result.resolve().parent != self.root.resolve()
        ):
            raise AudioError('unsafe_cache_entry')
        return result

    def media(self, session):
        target = (
            self.directory(session.get('asset_workspace', session['id']))
            / 'set.m4a'
        )
        if target.is_symlink() or not target.is_file():
            raise AudioError('dj_asset_unavailable')
        return target

    def used(self):
        if self.root.is_symlink():
            raise AudioError('unsafe_cache_entry')
        total = 0
        for path in self.root.rglob('*'):
            if path.is_symlink():
                raise AudioError('unsafe_cache_entry')
            try:
                if path.is_file():
                    total += path.stat().st_size
            except FileNotFoundError:
                continue
        return total

    def pin(self, owner, identity, consumer, *, now=None, seconds=None):
        now = time.time() if now is None else now
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                'SELECT * FROM dj_sessions WHERE id=? AND owner=?',
                (identity, owner),
            ).fetchone()
            if row is None or row['state'] not in {*ACTIVE, 'ready'}:
                raise LookupError('DJ asset unavailable')
            if not permitted(db, owner, row['mode']):
                raise PermissionError('DJ module disabled')
            document = json.loads(row['document'])
            duration = document.get('duration', 0)
            if not isinstance(duration, (int, float)) or not math.isfinite(
                duration
            ):
                duration = 0
            ttl = (
                min(43200, max(600, duration + 3600))
                if seconds is None
                else min(43200, max(60, seconds))
            )
            db.execute(
                'INSERT INTO dj_asset_pins VALUES (?,?,?) ON CONFLICT(session,consumer) DO UPDATE SET expires=max(expires,excluded.expires)',
                (identity, consumer, now + ttl),
            )
            document['last_access'] = now
            db.execute(
                'UPDATE dj_sessions SET document=? WHERE id=?',
                (json.dumps(document), identity),
            )

    def release(self, owner, identity, consumer):
        with self.database.connect() as db:
            db.execute(
                'DELETE FROM dj_asset_pins WHERE session=? AND consumer=? AND EXISTS(SELECT 1 FROM dj_sessions WHERE id=? AND owner=?)',
                (identity, consumer, identity, owner),
            )

    def discard(self, owner, identity):
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                'SELECT id FROM dj_sessions WHERE id=? AND owner=?',
                (identity, owner),
            ).fetchone()
            if row is None:
                raise LookupError('DJ asset unavailable')
            if db.execute(
                'SELECT 1 FROM dj_asset_pins WHERE session=? AND expires>?',
                (identity, time.time()),
            ).fetchone():
                raise RuntimeError('DJ asset in use')
            db.execute(
                "UPDATE dj_sessions SET state='deleting',lease_token='',lease_until=0,updated=? WHERE id=?",
                (time.time(), identity),
            )

    def pinned(self, identity, *, now=None):
        with self.database.connect() as db:
            return (
                db.execute(
                    'SELECT 1 FROM dj_asset_pins WHERE session=? AND expires>? LIMIT 1',
                    (identity, time.time() if now is None else now),
                ).fetchone()
                is not None
            )

    def expire(self, identity, *, now=None):
        now = time.time() if now is None else now
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute(
                'SELECT * FROM dj_sessions WHERE id=?', (identity,)
            ).fetchone()
            if row is None or row['state'] in {
                *ACTIVE,
                'queued',
                'deleting',
                'deleted',
                'expired',
            }:
                return False
            document = json.loads(row['document'])
            if document.get('immutable_copy') and row['state'] in {
                'ready',
                'stopped',
            }:
                return False
            if row['state'] == 'copying' and now - row['updated'] < 900:
                return False
            if db.execute(
                'SELECT 1 FROM dj_asset_pins WHERE session=? AND expires>?',
                (identity, now),
            ).fetchone():
                return False
            directory = self.directory(
                document.get(
                    'asset_workspace',
                    document.get('render_workspace', identity),
                )
            )
            document.update(phase='expired', error='dj_cache_expired')
            db.execute(
                "UPDATE dj_sessions SET state='expired',document=?,updated=? WHERE id=?",
                (json.dumps(document), now, identity),
            )
        if directory.exists():
            shutil.rmtree(directory)
        return True

    def prune_orphans(self, checkpoint=lambda: None, *, now=None):
        """Caller holds the shared compute lease; only stale private attempt dirs."""
        now = time.time() if now is None else now
        with self.database.connect() as db:
            rows = db.execute(
                "SELECT id,document FROM dj_sessions WHERE state NOT IN ('deleted','expired')"
            ).fetchall()
        referenced = set()
        for row in rows:
            document = json.loads(row['document'])
            referenced.add(row['id'])
            referenced.update(
                document.get(key)
                for key in ('asset_workspace', 'render_workspace')
            )
        removed = 0
        for entry in self.root.iterdir():
            checkpoint()
            if (
                entry.name in referenced
                or re.fullmatch('[a-f0-9]{32}', entry.name) is None
            ):
                continue
            directory = self.directory(entry.name)
            try:
                if (
                    not directory.is_dir()
                    or now - directory.stat().st_mtime < 3600
                ):
                    continue
            except FileNotFoundError:
                continue
            checkpoint()
            # Re-read under the writer transaction before removing a stale attempt.
            # Accepted publication, reader pins, and explicit copy creation use this lock.
            with self.database.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if db.execute(
                    "SELECT 1 FROM dj_sessions WHERE state NOT IN ('deleted','expired') AND (id=? OR json_extract(document,'$.asset_workspace')=? OR json_extract(document,'$.render_workspace')=?) LIMIT 1",
                    (directory.name, directory.name, directory.name),
                ).fetchone():
                    continue
                shutil.rmtree(directory)
            removed += 1
            if removed >= 32:
                break
        return removed

    def reserve(self, requested, checkpoint=lambda: None):
        if requested < 0 or requested + self.margin > self.budget:
            raise AudioError('dj_cache_full')

        def enough():
            return (
                self.used() + requested + self.margin <= self.budget
                and shutil.disk_usage(self.root).free
                >= requested + self.margin + self.min_free
            )

        if enough():
            return
        self.prune_orphans(checkpoint)
        if enough():
            return
        with self.database.connect() as db:
            rows = db.execute(
                "SELECT id,document,updated FROM dj_sessions WHERE state NOT IN ('queued','preparing','rendering','playing','paused','deleted','deleting','expired')"
            ).fetchall()
        rows = sorted(
            rows,
            key=lambda row: json.loads(row['document']).get(
                'last_access', row['updated']
            ),
        )
        for row in rows:
            checkpoint()
            if self.expire(row['id']) and enough():
                return
        raise AudioError(
            'dj_cache_full'
            if self.used() + requested + self.margin > self.budget
            else 'dj_storage_reserve'
        )

    @staticmethod
    def _digest(path, checkpoint):
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            while data := stream.read(1024 * 1024):
                checkpoint()
                digest.update(data)
        return digest.hexdigest()

    def _copy_request(self, owner, source, name, nonce):
        intent = json.dumps(
            ['immutable-copy', source, name], separators=(',', ':')
        )
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not permitted(db, owner, 'prepared'):
                raise PermissionError('DJ module disabled')
            previous = db.execute(
                'SELECT intent,session FROM dj_requests WHERE owner=? AND nonce=?',
                (owner, nonce),
            ).fetchone()
            if previous:
                if previous['intent'] != intent:
                    raise ValueError('Request identifier already used')
                return previous['session']
            original = db.execute(
                "SELECT * FROM dj_sessions WHERE id=? AND owner=? AND mode='prepared' AND state='ready'",
                (source, owner),
            ).fetchone()
            if original is None:
                raise LookupError('DJ asset unavailable')
            count = db.execute(
                "SELECT count(*) FROM dj_sessions WHERE owner=? AND json_extract(document,'$.immutable_copy')=1 AND state IN ('ready','copying','stopped')",
                (owner,),
            ).fetchone()[0]
            if count >= 20:
                raise AudioError('dj_copy_limit')
            identity, now = secrets.token_hex(16), time.time()
            document = json.loads(original['document'])
            for key in (
                'background',
                'render_workspace',
                'retry_at',
                'listener_seen',
                'ready_seconds',
                'ready_at',
            ):
                document.pop(key, None)
            document.update(
                immutable_copy=True,
                title=name,
                copy_of=source,
                asset_workspace=identity,
                phase='copying',
                progress=0.0,
            )
            db.execute(
                "INSERT INTO dj_sessions(id,owner,mode,state,document,created,updated) VALUES (?,?,'prepared','copying',?,?,?)",
                (identity, owner, json.dumps(document), now, now),
            )
            db.execute(
                'INSERT INTO dj_sources SELECT ?,track,value FROM dj_sources WHERE session=?',
                (identity, source),
            )
            db.execute(
                'INSERT INTO dj_requests VALUES (?,?,?,?)',
                (owner, nonce, intent, identity),
            )
            db.execute(
                'INSERT INTO dj_asset_pins VALUES (?,?,?) ON CONFLICT(session,consumer) DO UPDATE SET expires=excluded.expires',
                (source, 'copy:' + nonce, now + 900),
            )
            return identity

    def copy(self, owner, source, name, nonce):
        from .compute_budget import acquire

        if (
            not isinstance(name, str)
            or not 1 <= len(name.strip()) <= 160
            or any(ord(char) < 32 for char in name)
        ):
            raise ValueError('Invalid copy name')
        if not isinstance(nonce, str) or not 1 <= len(nonce) <= 128:
            raise ValueError('Invalid request identifier')
        name = name.strip()
        intent = json.dumps(
            ['immutable-copy', source, name], separators=(',', ':')
        )
        previous = self.dj.find_request(owner, nonce, intent)
        if previous and previous['state'] == 'ready':
            if not self.database.effective(owner)['dj_prepared']:
                raise PermissionError('DJ module disabled')
            self.media(previous)
            return previous
        if previous and previous['state'] not in {'copying', 'failed'}:
            raise LookupError('DJ copy unavailable')
        if self.database.metadata('native_busy', False):
            raise AudioError('dj_cache_busy')
        ticket = acquire(self.database, 'analysis')
        if ticket is None:
            raise AudioError('dj_cache_busy')
        identity = None

        def checkpoint():
            if (
                self.database.metadata('native_busy', False)
                or not ticket.renew()
            ):
                raise AudioError('dj_cache_busy')

        try:
            identity = self._copy_request(owner, source, name, nonce)
            copied = self.dj.get(owner, identity)
            directory = self.directory(identity)
            directory.mkdir(mode=0o700, exist_ok=True)
            target = directory / 'set.m4a'
            if target.is_symlink():
                raise AudioError('unsafe_cache_entry')
            expected = copied.get('copy_sha256')
            if not (
                target.is_file()
                and expected
                and self._digest(target, checkpoint) == expected
            ):
                original = self.dj.get(owner, source)
                self.pin(owner, source, 'copy:' + nonce, seconds=900)
                path = self.media(original)
                self.reserve(path.stat().st_size, checkpoint)
                expected = self._digest(path, checkpoint)
                with self.database.connect() as db:
                    row = db.execute(
                        'SELECT document FROM dj_sessions WHERE id=? AND owner=?',
                        (identity, owner),
                    ).fetchone()
                    document = json.loads(row[0])
                    document['copy_sha256'] = expected
                    db.execute(
                        'UPDATE dj_sessions SET document=? WHERE id=? AND owner=?',
                        (json.dumps(document), identity, owner),
                    )
                temporary = directory / (
                    'copy-' + secrets.token_hex(8) + '.part'
                )
                try:
                    os.link(path, temporary, follow_symlinks=False)
                    if (
                        temporary.is_symlink()
                        or self._digest(temporary, checkpoint) != expected
                    ):
                        raise AudioError('dj_asset_changed')
                    checkpoint()
                    os.replace(temporary, target)
                finally:
                    temporary.unlink(missing_ok=True)
            with self.database.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if not permitted(db, owner, 'prepared'):
                    raise PermissionError('DJ module disabled')
                row = db.execute(
                    'SELECT state,document FROM dj_sessions WHERE id=? AND owner=?',
                    (identity, owner),
                ).fetchone()
                if row is None or row['state'] not in {'copying', 'failed'}:
                    raise LookupError('DJ copy unavailable')
                document = json.loads(row['document'])
                document.update(
                    phase='ready',
                    progress=1.0,
                    output_bytes=target.stat().st_size,
                    copy_sha256=expected,
                )
                db.execute(
                    "UPDATE dj_sessions SET state='ready',document=?,updated=? WHERE id=? AND owner=?",
                    (json.dumps(document), time.time(), identity, owner),
                )
            return self.dj.get(owner, identity)
        except BaseException:
            if identity is not None:
                with self.database.connect() as db:
                    db.execute(
                        "UPDATE dj_sessions SET state='failed',updated=? WHERE id=? AND owner=? AND state='copying'",
                        (time.time(), identity, owner),
                    )
            raise
        finally:
            if identity is not None:
                self.release(owner, source, 'copy:' + nonce)
            ticket.release()
