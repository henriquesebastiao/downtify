"""Incremental rhythmic profiles, independent of DCLAP and native library files."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import time

from .compute_budget import acquire
from .dj_audio import AudioIO
from .dj_worker import DjWorker
from .rhythm_queue import active
from .sqlite_busy import is_busy
from .store import DEFAULTS
from .worker import Deferred, signature, source_path


class RhythmWorker:
    def __init__(
        self,
        database,
        models,
        roots,
        *,
        cache_bytes=5 * 1024**3,
        min_free=2 * 1024**3,
    ):
        self.database = database
        self.runner = DjWorker(
            database, models, roots, cache_bytes=cache_bytes, min_free=min_free
        )
        self.ticket = None
        self.job = None
        self.checked = 0.0

    def close(self):
        self.runner.close()

    def checkpoint(self, *, force=False):
        if self.ticket is None or not self.ticket.renew():
            raise Deferred()
        clock = time.monotonic()
        if not force and clock - self.checked < 0.25:
            return
        database, payload = self.database, self.job['payload']
        if (
            not active(database)
            or database.metadata('native_busy', False)
            or database.metadata('analysis_paused', False)
            or database.metadata('analysis_generation', 0)
            != payload['generation']
            or not database.renew(self.job)
        ):
            raise Deferred()
        self.checked = clock

    def publish(self, result):
        payload = self.job['payload']
        with self.database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            track = db.execute(
                """SELECT t.fingerprint,s.signature FROM tracks t
                                  JOIN source_versions s ON s.id=t.id
                                  JOIN catalog_live l ON l.id=t.id WHERE t.id=?""",
                (payload['track'],),
            ).fetchone()
            lease = db.execute(
                "SELECT 1 FROM jobs WHERE id=? AND lease_token=? AND state='running' AND lease_until>?",
                (self.job['id'], self.job['lease_token'], time.time()),
            ).fetchone()
            metadata = {
                row[0]: json.loads(row[1])
                for row in db.execute(
                    "SELECT key,value FROM metadata WHERE key IN ('analysis_generation','analysis_paused','native_busy')"
                )
            }
            preferences = db.execute(
                'SELECT value FROM preferences WHERE owner=-1'
            ).fetchone()
            flags = {
                **DEFAULTS,
                **(json.loads(preferences[0]) if preferences else {}),
            }
            if (
                not lease
                or not track
                or track['fingerprint'] != payload['fingerprint']
                or json.loads(track['signature']) != payload['source_version']
                or metadata.get('analysis_generation', 0)
                != payload['generation']
                or metadata.get('analysis_paused', False)
                or metadata.get('native_busy', False)
                or not any(
                    flags[key] for key in ('dj_prepared', 'dj_interactive')
                )
            ):
                return False
            db.execute(
                'INSERT OR REPLACE INTO dj_profiles VALUES (?,?,?,?,?)',
                (
                    payload['track'],
                    payload['model'],
                    payload['fingerprint'],
                    json.dumps(payload['source_version']),
                    json.dumps(result),
                ),
            )
        return True

    def step(self):
        database = self.database
        database.set_metadata(
            'rhythm',
            {
                'model': self.runner.analysis,
                'seen': time.time(),
                'enabled': active(database),
            },
        )
        if (
            not active(database)
            or database.metadata('analysis_paused', False)
            or database.metadata('native_busy', False)
        ):
            self.close()
            return False
        self.ticket = acquire(database, 'analysis')
        if self.ticket is None:
            return False
        io = None
        try:
            self.job = database.claim(kind='rhythm')
            if self.job is None:
                return False
            self.checked = 0
            payload = self.job['payload']
            if payload['model'] != self.runner.analysis or payload[
                'generation'
            ] != database.metadata('analysis_generation', 0):
                database.finish(self.job)
                return True
            self.checkpoint(force=True)
            path = source_path(payload['path'], self.runner.roots)
            if list(signature(path)) != payload['source_version']:
                raise ValueError('Source changed')
            io = AudioIO(
                self.runner.cache,
                self.runner.roots,
                budget=self.runner.cache_bytes,
                min_free=self.runner.min_free,
                workspace=hashlib.sha256(
                    (self.job['id'] + self.job['lease_token']).encode()
                ).hexdigest()[:32],
            )
            result = self.runner.analysis_result(
                payload['track'], payload, io, self.checkpoint
            )
            self.checkpoint(force=True)
            if list(signature(path)) != payload[
                'source_version'
            ] or not self.publish(result):
                raise ValueError('Analysis changed')
            database.finish(self.job)
            return True
        except Deferred:
            if self.job is not None:
                database.finish(self.job, 'queued')
            return False
        except sqlite3.OperationalError as error:
            if not is_busy(error):
                raise
            if self.job is not None:
                database.finish(self.job, 'queued')
            return False
        except (OSError, ValueError, RuntimeError, KeyError):
            if self.job is not None:
                database.finish(
                    self.job, 'failed', 'rhythm_analysis_unavailable'
                )
            return False
        finally:
            if io is not None and not io.workspace.is_symlink():
                shutil.rmtree(io.workspace)
            self.job = None
            self.ticket.release()
            self.ticket = None

    def run_cycle(self):
        try:
            return self.step()
        except sqlite3.OperationalError as error:
            if not is_busy(error):
                raise
            return False
