"""Single CPU companion. Only allowlisted read-only music mounts are accepted."""

from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path

from .encoder import Encoder
from .sqlite_busy import is_busy, retry_busy
from .store import ANALYSIS_FEATURES, MOODS, Store


class Deferred(Exception):
    pass


def source_path(value, roots):
    path = Path(value).resolve(strict=True)
    if not path.is_file() or not any(
        path.is_relative_to(root) for root in roots
    ):
        raise ValueError('Source outside allowlisted roots')
    return path


def signature(path):
    stat = path.stat()
    return (
        stat.st_dev,
        stat.st_ino,
        stat.st_size,
        stat.st_mtime_ns,
        stat.st_ctime_ns,
    )


class Worker:
    def __init__(self, store, encoder, roots):
        self.store, self.encoder = store, encoder
        self.roots = [Path(root).resolve(strict=True) for root in roots]
        self.checked = self.renewed = 0.0
        self.active_token = None
        self.compute_ticket = None
        generation = store.metadata('analysis_generation', 0)
        vectors = {
            mood: encoder.encode_text(prompt) for mood, prompt in MOODS.items()
        }
        self.ready = store.publish_model(encoder.identity, vectors, generation)
        release = getattr(encoder, 'release_text', None)
        if release is not None:
            release()

    def checkpoint(self, job, *, force=False):
        if self.compute_ticket is not None and not self.compute_ticket.renew():
            raise Deferred()
        now = time.monotonic()
        if self.active_token != job['lease_token']:
            self.active_token = job['lease_token']
            self.checked = self.renewed = 0.0
            force = True
        if not force and now - self.checked < 0.25:
            return
        if self.store.metadata('analysis_paused', False):
            raise Deferred()
        flags = self.store.preferences(-1)
        if not any(flags[k] for k in ANALYSIS_FEATURES):
            raise Deferred()
        if self.store.metadata('native_busy', False):
            raise Deferred()
        if force or now - self.renewed >= 5 or not self.renewed:
            if not self.store.renew(job):
                raise Deferred()
            self.renewed = now
        self.checked = now

    def step(self):
        if not self.ready:
            return False
        flags = self.store.preferences(-1)
        if self.store.metadata(
            'analysis_paused', False
        ) or self.store.metadata('native_busy', False):
            return False
        if not any(flags[key] for key in ANALYSIS_FEATURES):
            return False
        job = self.store.claim(kind='analysis')
        if job is None:
            return False
        try:
            self.checkpoint(job, force=True)
            payload = job['payload']
            if (
                job['kind'] != 'analysis'
                or payload['model'] != self.encoder.identity
            ):
                raise ValueError('Unsupported analysis job')
            path = source_path(payload['path'], self.roots)
            before = signature(path)
            expected = payload.get('source_version')
            if expected is not None and list(before) != expected:
                raise ValueError('Source changed while queued')
            vector = self.encoder.encode_audio(
                path, checkpoint=lambda: self.checkpoint(job)
            )
            if before != signature(path):
                raise ValueError('Source changed during analysis')
            self.checkpoint(job, force=True)
            if not self.store.put_analysis(
                payload['track'],
                payload['fingerprint'],
                self.encoder.identity,
                vector,
                generation=payload.get('generation', 0),
                source_version=expected,
            ):
                raise ValueError('Catalog changed during analysis')
            self.store.finish(job)
        except Deferred:
            self.store.finish(job, 'queued')
            return False
        except sqlite3.OperationalError as error:
            if not is_busy(error):
                raise
            try:
                self.store.finish(job, 'queued')
            except sqlite3.OperationalError as pending:
                if not is_busy(pending):
                    raise
                # The existing lease will make it claimable again. Preserve
                # the loaded model and do not consume a failure retry.
            return False
        except (OSError, ValueError, RuntimeError, KeyError):
            self.store.finish(job, 'failed', 'analysis_unavailable')
        return True


class AnalysisService:
    def __init__(self, store, encoder_factory, roots):
        self.store, self.encoder_factory, self.roots = (
            store,
            encoder_factory,
            roots,
        )
        self.encoder = self.worker = None
        self.worker_generation = None
        self.compute_ticket = None

    def step(self):
        try:
            flags = self.store.preferences(-1)
            active = any(flags[key] for key in ANALYSIS_FEATURES)
            if not active or self.store.metadata('analysis_paused', False):
                if self.encoder is not None:
                    self.encoder = self.worker = None
                    import gc

                    gc.collect()
                    self.store.set_metadata(
                        'model', {'ready': False, 'state': 'disabled'}
                    )
                return False
            if self.encoder is None:
                self.encoder = self.encoder_factory()
            generation = self.store.metadata('analysis_generation', 0)
            if self.worker_generation != generation:
                self.worker = None
            if self.worker is None:
                candidate = Worker(self.store, self.encoder, self.roots)
                if not candidate.ready:
                    return False
                self.worker = candidate
                self.worker_generation = generation
            self.worker.compute_ticket = self.compute_ticket
            return self.worker.step()
        except sqlite3.OperationalError as error:
            if not is_busy(error):
                raise
            return False

    def run_cycle(self):
        from .compute_budget import acquire

        flags = self.store.preferences(-1)
        if self.store.metadata('analysis_paused', False) or not any(
            flags[key] for key in ANALYSIS_FEATURES
        ):
            return (
                self.step()
            )  # Release a loaded model without taking a compute lease.
        ticket = retry_busy(lambda: acquire(self.store, 'analysis'), seconds=3)
        if ticket is None:
            return False
        self.compute_ticket = ticket
        try:
            return self.step()
        finally:
            self.compute_ticket = None
            if self.worker is not None:
                self.worker.compute_ticket = None
            retry_busy(ticket.release, seconds=3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--root', action='append', type=Path, required=True)
    options = parser.parse_args()
    store = retry_busy(lambda: Store(options.database), seconds=30)
    # Previously verified vectors remain usable while a runtime loads or waits
    # for a write lock. Erasure/disablement still owns its explicit fences.
    service = AnalysisService(
        store, lambda: Encoder(options.models), options.root
    )
    while True:
        if not service.run_cycle():
            time.sleep(3)


if __name__ == '__main__':
    main()
