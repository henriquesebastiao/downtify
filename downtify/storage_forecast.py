"""How long until the disk that holds the library is full.

Part of ``GET /api/library/usage`` (see :mod:`downtify.library_usage`):
pure functions over the library's day-by-day size, what the Playlist
Monitor added, what is still waiting to be downloaded and the disk's
free space.

The library rarely grows evenly. A new watch's first check downloads a
whole playlist or discography in a day or two, and a big hand-queued
batch can do the same; dividing the free space by a week like that
would say the disk is full next month when it fills in two years. So:

* **One-off downloads** - the songs a watch fetched on its first check
  (its backfill, ``initial`` in :mod:`downtify.watch_history`) - are
  taken out of each day's growth before any rate is worked out.
* The **usual pace** is the *median* week of the last
  :data:`WINDOW_DAYS` days, so one busy week (a batch queued by hand)
  doesn't set it; weeks well above it are listed as ``spikes``.
* The **recent pace** is the last :data:`RECENT_DAYS` days. The forecast
  gives the date at the usual pace, and a range from the slower to the
  faster of the two.
* What is **still to come** - the queue, and the songs watched
  playlists hold but haven't downloaded yet - is taken off the free
  space first, at the library's average song size.
* What **drives** the usual pace: each watch's own downloads after its
  first check, and everything else (downloads by hand, minus what was
  deleted) as one more row.

Every figure is net of deletions: the growth comes from the library's
size, not from the download count.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from statistics import median
from typing import Any, Optional

from .watch_history import OUTCOME_DOWNLOADED, OUTCOME_UNKNOWN
from .watch_stats import norm_path, parse_time

#: How far back the pace is read (twelve whole weeks).
WINDOW_DAYS = 84
#: What "lately" means for the recent pace.
RECENT_DAYS = 14
#: A week this many times the usual one (and over :data:`SPIKE_MIN_BYTES`)
#: is listed as a spike.
SPIKE_FACTOR = 3.0
SPIKE_MIN_BYTES = 1024**3
#: Fewer days of history than this make the forecast a rough one.
MIN_HISTORY_DAYS = 14
#: Watches listed by name as what drives the growth; the rest are summed.
TOP_DRIVERS = 8
#: Past this many days the forecast says "more than ten years".
MAX_DAYS = 3650

#: Watch event outcomes that grew the library.
_ADDED = frozenset({OUTCOME_DOWNLOADED, OUTCOME_UNKNOWN})

#: ``status`` values.
STATUS_OK = 'ok'
#: The library isn't growing at its usual pace (or is shrinking).
STATUS_NOT_GROWING = 'not_growing'
#: What is still to come doesn't fit in the free space.
STATUS_BACKLOG_TOO_BIG = 'backlog_too_big'
#: The disk's free space couldn't be read.
STATUS_NO_DISK = 'no_disk'


def daily_growth(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """``[{day, bytes, estimated}]``: how much the library grew each day,
    from :func:`downtify.library_usage.growth`'s daily points (each day's
    end size). ``estimated`` when either end of the day is.

    The days before the library held anything are left out, so a young
    library isn't taken for one that stood still for weeks.
    """

    days: list[dict[str, Any]] = []
    started = False
    for before, after in zip(points, points[1:]):
        if not started:
            if not before.get('bytes') and not after.get('bytes'):
                continue
            started = True
        days.append({
            'day': str(after['day']),
            'bytes': int(after.get('bytes') or 0)
            - int(before.get('bytes') or 0),
            'estimated': bool(
                after.get('estimated') or before.get('estimated')
            ),
        })
    return days


def watch_additions(
    events: Iterable[dict[str, Any]],
    sizes: dict[str, int],
    *,
    since: datetime,
) -> list[dict[str, Any]]:
    """``[{watch, name, day, bytes, initial}]``: each file a watch
    downloaded since *since* and still in the library (``sizes``:
    ``{library path: size}``), once - the first watch to fetch a file
    gets it."""

    seen: set[str] = set()
    found: list[dict[str, Any]] = []
    for event in events:
        if event.get('outcome') not in _ADDED:
            continue
        name = norm_path(event.get('filename'))
        if not name or name in seen or name not in sizes:
            continue
        seen.add(name)
        moment = parse_time(event.get('happened_at'))
        if moment is None or moment < since:
            continue
        found.append({
            'watch': int(event.get('playlist_id') or 0),
            'name': str(event.get('watch_name') or ''),
            'day': moment.date().isoformat(),
            'bytes': int(sizes[name]),
            'initial': bool(event.get('initial')),
        })
    return found


def _weeks(values: list[int]) -> list[int]:
    """Sums of whole weeks, counted back from the last day (the oldest
    days that don't fill a week are left out)."""

    whole = len(values) // 7
    start = len(values) - whole * 7
    return [
        sum(values[start + i * 7 : start + (i + 1) * 7]) for i in range(whole)
    ]


def _pace(steady: list[int]) -> tuple[float, list[int]]:
    """``(usual bytes a day, weekly sums)``: the median week once there
    are three, else the average day."""

    weeks = _weeks(steady)
    if len(weeks) >= 3:
        return median(weeks) / 7, weeks
    return (sum(steady) / len(steady) if steady else 0.0), weeks


def _when(now: datetime, days: Optional[float]) -> Optional[dict[str, Any]]:
    if days is None:
        return None
    if days >= MAX_DAYS:
        return {'days': MAX_DAYS, 'date': None, 'beyond': True}
    whole = max(0, math.floor(days))
    return {
        'days': whole,
        'date': (now.date() + timedelta(days=whole)).isoformat(),
        'beyond': False,
    }


def _days_to_fill(room: int, per_day: float) -> Optional[float]:
    if per_day <= 0:
        return None
    return max(0, room) / per_day


def backlog(
    *,
    queued: int,
    watches: Iterable[dict[str, Any]],
    average_bytes: int,
) -> dict[str, Any]:
    """What is still to come: *queued* songs waiting in the queue, and
    for each watched playlist (``{id, name, expected, held, failing}``)
    the songs it lists but neither holds nor keeps failing on - all at
    *average_bytes* a song."""

    waiting: list[dict[str, Any]] = []
    for watch in watches:
        missing = (
            int(watch.get('expected') or 0)
            - int(watch.get('held') or 0)
            - int(watch.get('failing') or 0)
        )
        if missing > 0:
            waiting.append({
                'id': int(watch['id']),
                'name': str(watch.get('name') or ''),
                'songs': missing,
                'bytes': missing * average_bytes,
            })
    waiting.sort(key=lambda row: (-row['songs'], row['name']))
    watch_songs = sum(row['songs'] for row in waiting)
    songs = max(0, int(queued)) + watch_songs
    return {
        'songs': songs,
        'bytes': songs * average_bytes,
        'queued': max(0, int(queued)),
        'watch_songs': watch_songs,
        'average_bytes': average_bytes,
        'watches': waiting[:TOP_DRIVERS],
    }


def _split_additions(
    days: list[dict[str, Any]], additions: list[dict[str, Any]]
) -> tuple[list[int], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
    """``(one-off bytes per day, one-off per watch, after-the-first-check
    per watch)`` of the *additions* that fall on one of *days*."""

    order = {row['day']: index for index, row in enumerate(days)}
    one_off = [0] * len(days)
    by_watch: dict[bool, dict[int, dict[str, Any]]] = {True: {}, False: {}}
    for row in additions:
        index = order.get(row['day'])
        if index is None:
            continue
        entry = by_watch[row['initial']].setdefault(
            row['watch'],
            {'id': row['watch'], 'name': row['name'], 'bytes': 0, 'songs': 0},
        )
        entry['bytes'] += row['bytes']
        entry['songs'] += 1
        if row['initial']:
            one_off[index] += row['bytes']
    return one_off, by_watch[True], by_watch[False]


def _biggest(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (-row['bytes'], row['name']))


def _spikes(
    days: list[dict[str, Any]], weeks: list[int], usual: float
) -> list[dict[str, Any]]:
    """The weeks well above the usual one: ``[{from, to, bytes}]``."""

    if len(weeks) < 3:
        return []
    start = len(days) - len(weeks) * 7
    return [
        {
            'from': days[start + i * 7]['day'],
            'to': days[start + i * 7 + 6]['day'],
            'bytes': size,
        }
        for i, size in enumerate(weeks)
        if size > SPIKE_MIN_BYTES and size > SPIKE_FACTOR * max(usual * 7, 0)
    ]


def _drivers(
    steady: list[int], by_watch: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    """Each watch's share of the steady growth, and everything else."""

    window = max(1, len(steady))
    rows = _biggest(
        {**row, 'per_week_bytes': round(row['bytes'] / window * 7)}
        for row in by_watch.values()
    )
    others = sum(steady) - sum(row['bytes'] for row in rows)
    return {
        'watches': rows[:TOP_DRIVERS],
        'more_watches': max(0, len(rows) - TOP_DRIVERS),
        'more_watches_bytes': sum(row['bytes'] for row in rows[TOP_DRIVERS:]),
        'other_bytes': others,
        'other_per_week_bytes': round(others / window * 7),
    }


def _fill(
    report: dict[str, Any],
    *,
    disk: Optional[dict[str, int]],
    usual: float,
    recent: float,
    now: datetime,
) -> dict[str, Any]:
    """*report* with its ``status``, ``room_bytes`` and dates."""

    if not disk:
        return report
    room = int(disk.get('free') or 0) - int(
        report['still_to_come'].get('bytes') or 0
    )
    report['room_bytes'] = room
    if room <= 0:
        report['status'] = STATUS_BACKLOG_TOO_BIG
        return report
    report['status'] = STATUS_OK if usual > 0 else STATUS_NOT_GROWING
    paces = [pace for pace in (usual, recent) if pace > 0]
    if not paces:
        return report
    report['full'] = _when(now, _days_to_fill(room, usual))
    report['soonest'] = _when(now, _days_to_fill(room, max(paces)))
    report['latest'] = _when(now, _days_to_fill(room, min(paces)))
    return report


def storage_forecast(
    *,
    points: list[dict[str, Any]],
    additions: list[dict[str, Any]],
    disk: Optional[dict[str, int]],
    still_to_come: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """When the disk is full at the library's usual pace.

    *points* are the library's daily sizes over :data:`WINDOW_DAYS`
    (oldest first, ending today), *additions* what watches downloaded in
    that time (:func:`watch_additions`), *still_to_come* the
    :func:`backlog` and *disk* the volume's ``{total, used, free}``.
    """

    days = daily_growth(points)
    one_off, one_off_by_watch, steady_by_watch = _split_additions(
        days, additions
    )
    steady = [row['bytes'] - one_off[i] for i, row in enumerate(days)]
    usual, weeks = _pace(steady)
    recent_days = steady[-RECENT_DAYS:]
    recent = sum(recent_days) / len(recent_days) if recent_days else 0.0
    report: dict[str, Any] = {
        'window_days': WINDOW_DAYS,
        'history_days': len(days),
        'estimated_days': sum(1 for row in days if row['estimated']),
        'rough': len(days) < MIN_HISTORY_DAYS,
        'usual_per_day_bytes': round(usual),
        'recent_per_day_bytes': round(recent),
        'recent_days': len(recent_days),
        'one_off': {
            'bytes': sum(one_off),
            'watches': _biggest(one_off_by_watch.values())[:TOP_DRIVERS],
        },
        'spikes': _spikes(days, weeks, usual),
        'drivers': _drivers(steady, steady_by_watch),
        'still_to_come': still_to_come,
        'room_bytes': None,
        'status': STATUS_NO_DISK,
        'full': None,
        'soonest': None,
        'latest': None,
    }
    return _fill(report, disk=disk, usual=usual, recent=recent, now=now)


def window_start(now: datetime) -> date:
    """The first day :func:`storage_forecast` reads."""

    return now.date() - timedelta(days=WINDOW_DAYS)


def held_counts(associations: Iterable[dict[str, Any]]) -> dict[int, int]:
    """``{watch id: tracks it holds}`` from ``downloaded_tracks`` rows."""

    counts: dict[int, int] = defaultdict(int)
    for row in associations:
        if norm_path(row.get('filename')):
            counts[int(row['playlist_id'])] += 1
    return dict(counts)
