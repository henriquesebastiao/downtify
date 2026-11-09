"""Consume native revisions in the background; bound all source-file checks."""

import asyncio
import hashlib
import json

from .catalog import (
    candidates,
    ensure_analysis_queue,
    recent_addition,
    scheduled,
    synchronize,
)
from .routes import store
from .store import ANALYSIS_FEATURES
from .worker import signature


def index_pass():
    from .. import api, mobile_routes
    from ..library_catalog import resolve_library_file

    database = store()
    flags = database.preferences(-1)
    if database.metadata('analysis_paused', False) or not any(
        flags[key] for key in ANALYSIS_FEATURES
    ):
        return
    identity = database.metadata('model', {}).get('id')
    if not identity:
        return
    busy = any(
        job.get('status') == 'downloading'
        for job in api.state.download_jobs.values()
    )
    runner = api.state.upgrade_runner
    busy = busy or (runner is not None and runner.busy())
    if database.metadata('native_busy', False) != bool(busy):
        database.set_metadata('native_busy', bool(busy))
    if busy:
        return
    synchronize(database, mobile_routes._sync())
    ensure_analysis_queue(database, identity)
    context = api.library_context()
    generation = database.metadata('analysis_generation', 0)
    favorites = (
        set(api.state.likes.paths()) if api.state.likes is not None else set()
    )
    favorite_ids = mobile_routes._sync().ids_for_paths(favorites)
    with database.connect() as db:
        db.executemany(
            'UPDATE catalog_pending SET priority=2 WHERE id=? AND priority<2',
            [(value,) for value in favorite_ids.values()],
        )
        recent = db.execute(
            'SELECT track,MAX(at) AS at FROM listens GROUP BY track ORDER BY at DESC LIMIT 1000'
        ).fetchall()
        db.executemany(
            'UPDATE catalog_pending SET priority=? WHERE id=? AND priority<?',
            [(row['at'], row['track'], row['at']) for row in recent],
        )
    recent_ids = {row['track'] for row in recent}
    after = database.metadata('source_scan_after', '')
    scan = candidates(database, identity, after=after, limit=100)
    if not scan and after:
        scan = candidates(database, identity, limit=100)
    if scan:
        database.set_metadata('source_scan_after', scan[-1]['id'])
    pending = candidates(database, identity, limit=100, unmeasured=True)
    selected = {row['id']: row for row in [*pending, *scan]}
    with database.connect() as db:
        marks = ','.join('?' for _ in selected)
        measured = (
            {
                row[0]
                for row in db.execute(
                    'SELECT id FROM analyses WHERE model=? AND id IN ('
                    + marks
                    + ')',
                    (identity, *selected),
                )
            }
            if selected
            else set()
        )
    for row in selected.values():
        full = resolve_library_file(row['file'], context)
        if full is None:
            continue
        try:
            version = list(signature(full))
        except OSError:
            continue
        if (
            database.observe_source(row['id'], version)
            and row['id'] in measured
        ):
            scheduled(database, row['id'])
            continue
        key = hashlib.sha256(
            json.dumps([
                identity,
                row['id'],
                row['fingerprint'],
                version,
                generation,
            ]).encode()
        ).hexdigest()
        database.enqueue(
            key,
            'analysis',
            {
                'track': row['id'],
                'path': str(full),
                'fingerprint': row['fingerprint'],
                'model': identity,
                'generation': generation,
                'source_version': version,
            },
            priority=3
            if row['id'] in recent_ids
            else 2
            if row.get('file') in favorites
            else int(recent_addition(row)),
        )
        scheduled(database, row['id'])


async def loop():
    from loguru import logger

    while True:
        try:
            await asyncio.to_thread(index_pass)
            from .scheduler import native_sweep

            await asyncio.to_thread(native_sweep)
        except Exception as error:
            logger.warning(
                'Music analysis indexing deferred ({})', type(error).__name__
            )
        await asyncio.sleep(60)
