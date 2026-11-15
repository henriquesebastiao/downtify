"""How long a DJ session takes to become playable, measured where the client sees it.

An interactive set is ready when its first manifest is actually served. A
prepared set is ready when the renderer publishes its completed file. Both
latencies land in the session document, so the app can show them and this
module can answer the objective (ten seconds at p95, warm library) without
reading raw request logs.
"""

from __future__ import annotations

import math
import time

TARGET_SECONDS = 10.0
HISTORY = 200


def percentile(values, fraction):
    """Nearest-rank percentile over a sorted list; deterministic and bounded."""
    if not values:
        return None
    rank = max(1, math.ceil(fraction * len(values)))
    return values[min(rank, len(values)) - 1]


def stats(values, *, target=TARGET_SECONDS):
    samples = sorted(
        value
        for value in values
        if type(value) in {int, float} and math.isfinite(value) and value >= 0
    )
    if not samples:
        return {
            'samples': 0,
            'p50_seconds': None,
            'p95_seconds': None,
            'worst_seconds': None,
            'over_target': 0,
            'target_seconds': target,
        }
    return {
        'samples': len(samples),
        'p50_seconds': round(percentile(samples, 0.5), 3),
        'p95_seconds': round(percentile(samples, 0.95), 3),
        'worst_seconds': round(samples[-1], 3),
        'over_target': sum(value > target for value in samples),
        'target_seconds': target,
    }


def record(database, mode, seconds, *, now=None):
    """Keep a short rolling history; it never grows with the library or users."""
    if mode not in {'prepared', 'interactive'}:
        raise ValueError('Unknown DJ mode')
    if (
        type(seconds) not in {int, float}
        or not math.isfinite(seconds)
        or seconds < 0
    ):
        raise ValueError('Invalid readiness delay')
    now = time.time() if now is None else now
    history = database.metadata('dj_readiness', [])
    if not isinstance(history, list):
        history = []
    history = [row for row in history if isinstance(row, dict)][
        -(HISTORY - 1) :
    ] + [{'mode': mode, 'seconds': round(seconds, 3), 'at': now}]
    database.set_metadata('dj_readiness', history)


def summary(database):
    history = database.metadata('dj_readiness', [])
    if not isinstance(history, list):
        history = []
    result = {}
    for mode in ('prepared', 'interactive'):
        result[mode] = stats([
            row.get('seconds')
            for row in history
            if isinstance(row, dict) and row.get('mode') == mode
        ])
    result['history'] = len(history)
    return result
