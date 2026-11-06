"""Native snapshot producer; no model or full directory walk in the web process."""

import asyncio
import hashlib
import json
from itertools import islice

from .routes import store
from .store import ANALYSIS_FEATURES
from .worker import signature


def index_pass():
    from .. import api, mobile_routes
    from ..library_catalog import resolve_library_file
    from ..library_paths_cache import peek_cached_track_entries

    flags = store().preferences(-1)
    if store().metadata('analysis_paused', False):
        return
    if not any(flags[key] for key in ANALYSIS_FEATURES):
        return
    identity = store().metadata('model', {}).get('id')
    if not identity:
        return
    busy = any(
        job.get('status') == 'downloading'
        for job in api.state.download_jobs.values()
    )
    runner = api.state.upgrade_runner
    if runner is not None:
        busy = busy or runner.busy()
    store().set_metadata('native_busy', bool(busy))
    if busy:
        return
    context = api.library_context()
    cached = peek_cached_track_entries(context)
    if cached is not None:
        # Reuse the native refresh pipeline's snapshot, including provisional
        # download updates. AI never walks the music tree itself.
        mobile_routes._sync().refresh([
            row
            for row in cached
            if row.get('file') not in getattr(context, 'hidden_files', ())
        ])
    rows = mobile_routes._sync().changes(0)['tracks']
    for row in rows:
        identity_fields = (
            row.get('file'),
            row.get('size'),
            row.get('modified'),
            row.get('added'),
            row.get('duration'),
        )
        row['fingerprint'] = hashlib.sha256(
            json.dumps(identity_fields).encode()
        ).hexdigest()
    store().observe(rows)
    with store().connect() as db:
        measured = {
            row[0]
            for row in db.execute(
                'SELECT id FROM analyses WHERE model=?', (identity,)
            )
        }
        pending = {row[0] for row in db.execute('SELECT id FROM jobs')}
        recently_listened = {
            row[0]: row[1]
            for row in db.execute(
                'SELECT track,MAX(at) FROM listens GROUP BY track'
            )
        }
    generation = store().metadata('analysis_generation', 0)
    favorites = (
        set(api.state.likes.paths()) if api.state.likes is not None else set()
    )
    # Bound NAS stat calls, while revisiting every already-analyzed file.
    ordered = sorted(rows, key=lambda item: item['id'])
    cursor = store().metadata('source_scan_cursor', 0) % max(1, len(ordered))
    scan = (ordered[cursor:] + ordered[:cursor])[:100]
    store().set_metadata('source_scan_cursor', cursor + len(scan))
    priority = sorted(
        rows,
        key=lambda item: (
            -recently_listened.get(item['id'], 0),
            item.get('file') not in favorites,
            -float(item.get('added') or 0),
        ),
    )
    candidates = {
        row['id']: row
        for row in islice(
            (row for row in priority if row['id'] not in measured), 100
        )
    }
    candidates.update({row['id']: row for row in scan})
    for row in candidates.values():
        full = resolve_library_file(row['file'], context)
        if full is None:
            continue
        try:
            version = list(signature(full))
        except OSError:
            continue
        unchanged = store().observe_source(row['id'], version)
        if unchanged and row['id'] in measured:
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
        if key in pending:
            continue
        store().enqueue(
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
            priority=recently_listened.get(row['id'], 0)
            or (1 if row.get('file') in favorites else 0),
        )


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
