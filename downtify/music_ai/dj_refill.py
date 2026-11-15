"""Bounded background renewal. Interactive status requests never rank a catalogue."""

import re
import time
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore

_executor = ThreadPoolExecutor(
    max_workers=1, thread_name_prefix='dj-selection'
)
_slot = BoundedSemaphore(1)


def schedule(request, session):
    if (
        not session.get('continuous')
        or session.get('queue_order')
        or session['state'] not in {'playing', 'paused'}
        or session.get('remaining_decks', 100) > 4
        or time.time() - session.get('refilled_at', 0) < 60
    ):
        return
    if not _slot.acquire(blocking=False):
        return
    try:
        _executor.submit(_run, request, session)
    except RuntimeError:
        _slot.release()


def _run(request, session):
    try:
        replenish(request, session)
    except (OSError, ValueError, RuntimeError):
        # The current buffer and native playback remain usable. A later status
        # retries; neither paths nor provider output is logged.
        pass
    finally:
        _slot.release()


def replenish(request, session):
    from . import dj_routes as dj
    from . import routes as base
    from .ranking import rank

    base.require(request, 'dj_interactive')
    rows = [
        row
        for row in base.catalog(request)
        if row['id'] not in session['ids']
        and 10 <= float(row.get('duration') or 0) <= 1200
    ]
    pattern = {
        'rap': r'\b(rap|hip[ -]?hop|trap)\b',
        'rock': r'\b(rock|metal|punk|grunge)\b',
        'electro': r'\b(electro\w*|house|techno|trance|dance|edm|dubstep)\b',
    }.get(session.get('style'))
    if pattern:
        rows = [
            row
            for row in rows
            if re.search(pattern, str(row.get('genre') or ''), re.I)
        ]
    model = base.store().metadata('model', {}).get('id')
    vectors = (
        base.store().vectors(model, {row['id'] for row in rows})
        if model
        else {}
    )
    with base.store().connect() as db:
        prompt = db.execute(
            'SELECT vector FROM mood_vectors WHERE mood=? AND model=?',
            (session['theme'], model),
        ).fetchone()
    selected = []
    if prompt and vectors:
        import numpy as np

        selected = rank(
            [row for row in rows if row['id'] in vectors],
            vectors,
            target=np.frombuffer(prompt[0], dtype='<f4'),
            limit=4,
            rotation=str(session.get('refill_revision', 0)),
        )
    if not selected:
        selected = dj.local_pool(
            rows, 4, str(session.get('refill_revision', 0))
        )
    if selected:
        ids = [row['id'] for row in selected]
        sources = dj.visible(request, ids, sources=True)
        return dj.database().replenish(
            session['owner'], session['id'], ids, sources
        )
    return False
