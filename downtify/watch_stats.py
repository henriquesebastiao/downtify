"""Playlist Monitor provenance and per-watch statistics.

Pure functions over what the monitor database records - the
``downloaded_tracks`` each watch holds and its ``watch_events`` (see
:mod:`downtify.monitor`) - plus ``{library path: size}`` for the files
still on disk. ``GET /api/monitor/stats`` and
``GET /api/monitor/provenance`` (``downtify/api.py``) do the I/O.

A file several watches hold is still one file: each of them lists it,
but the totals count it once, and a watch's *unique* storage is only
what no other watch also holds (``share`` splits a shared file evenly).

Activity (rates and the trend) counts the tracks a watch actually
added: the ones it downloaded, not those it found already in the
library (``linked``), and never its first check's backfill
(``initial``). Tracks recorded before outcomes were kept are
``unknown`` and counted as added, flagged by ``period.unknown``.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Collection, Iterable, Optional

from .monitor import MonitoredPlaylist
from .watch_history import (
    OUTCOME_DOWNLOADED,
    OUTCOME_LINKED,
    OUTCOME_UNKNOWN,
)

DEFAULT_DAYS = 30
MAX_DAYS = 365
#: Periods up to this many days are bucketed per day, longer per week.
DAILY_BUCKETS_UP_TO = 14
#: A trend moves when the fitted line changes by more than this share of
#: the average bucket (and by at least one song) over the period.
TREND_THRESHOLD = 0.25
MIN_TREND_BUCKETS = 3

#: Outcomes that grew the library.
ADDED = frozenset({OUTCOME_DOWNLOADED, OUTCOME_UNKNOWN})


def parse_time(value: Any) -> Optional[datetime]:
    """An ISO timestamp as an aware datetime (UTC when it has no zone)."""

    try:
        moment = datetime.fromisoformat(str(value or ''))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def clamp_days(value: Any) -> int:
    """A requested period in days, kept between 1 and :data:`MAX_DAYS`."""

    try:
        days = int(value)
    except (TypeError, ValueError):
        return DEFAULT_DAYS
    return max(1, min(MAX_DAYS, days))


def bucket_days_for(days: int) -> int:
    return 1 if days <= DAILY_BUCKETS_UP_TO else 7


def norm_path(path: Any) -> str:
    return str(path or '').strip().replace('\\', '/')


def trend(series: list[int]) -> dict[str, Any]:
    """Which way *series* (added songs per bucket, oldest first) goes.

    ``direction`` is ``new`` (fewer than three buckets to tell from: a
    line through two points says little), ``idle`` (nothing added),
    ``up``, ``down`` or ``steady``; ``slope`` is the least-squares change
    in songs per bucket, per bucket.
    """

    count = len(series)
    if count < MIN_TREND_BUCKETS:
        return {'direction': 'new', 'slope': 0.0}
    total = sum(series)
    if not total:
        return {'direction': 'idle', 'slope': 0.0}
    mean_x = (count - 1) / 2
    mean_y = total / count
    spread = sum((x - mean_x) ** 2 for x in range(count))
    slope = (
        sum((x - mean_x) * (y - mean_y) for x, y in enumerate(series)) / spread
    )
    change = slope * (count - 1)
    threshold = max(1.0, TREND_THRESHOLD * mean_y)
    if change > threshold:
        direction = 'up'
    elif change < -threshold:
        direction = 'down'
    else:
        direction = 'steady'
    return {'direction': direction, 'slope': round(slope, 3)}


def activity_series(
    times: Iterable[datetime], now: datetime, start: datetime, days: int
) -> list[int]:
    """Songs per bucket over the whole buckets between *start* (the
    later of the period's start and when the watch began) and *now*,
    oldest first."""

    span = timedelta(days=bucket_days_for(days))
    first = max(start, now - timedelta(days=days))
    count = max(0, math.floor((now - first) / span))
    series = [0] * count
    for moment in times:
        if moment > now:
            continue
        index = count - 1 - math.floor((now - moment) / span)
        if 0 <= index < count:
            series[index] += 1
    return series


def holders_by_file(
    associations: Iterable[dict[str, Any]],
    on_disk: Optional[Collection[str]] = None,
) -> dict[str, set[int]]:
    """``{file: ids of the watches holding it}`` - only files *on_disk*
    when given."""

    holders: dict[str, set[int]] = {}
    for row in associations:
        name = norm_path(row.get('filename'))
        if name and (on_disk is None or name in on_disk):
            holders.setdefault(name, set()).add(int(row['playlist_id']))
    return holders


def providers_from_events(
    events: Iterable[dict[str, Any]],
) -> dict[str, str]:
    """``{file: provider}`` as the watches' downloads recorded it (the
    latest wins) - what fetched a file another watch only linked."""

    found: dict[str, str] = {}
    for event in events:
        name = norm_path(event.get('filename'))
        if (
            name
            and event['outcome'] == OUTCOME_DOWNLOADED
            and event['provider']
        ):
            found[name] = str(event['provider'])
    return found


def _event_key(event: dict[str, Any]) -> tuple[int, str, str]:
    return (
        int(event['playlist_id']),
        str(event['watch_key']),
        str(event['track_id']),
    )


def first_events(
    events: Iterable[dict[str, Any]],
) -> dict[tuple[int, str, str], dict[str, Any]]:
    """The earliest event per ``(watch id, watch key, track id)``: how
    the watch got each track. *events* come oldest first."""

    firsts: dict[tuple[int, str, str], dict[str, Any]] = {}
    for event in events:
        firsts.setdefault(_event_key(event), event)
    return firsts


@dataclass
class _WatchFacts:
    """What one watch holds and did, gathered in one pass."""

    watch: MonitoredPlaylist
    rows: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)


def _gather(
    watches: list[MonitoredPlaylist],
    associations: Iterable[dict[str, Any]],
    events: Iterable[dict[str, Any]],
) -> dict[int, _WatchFacts]:
    facts = {watch.id: _WatchFacts(watch) for watch in watches}
    for row in associations:
        fact = facts.get(int(row['playlist_id']))
        if fact is not None and norm_path(row.get('filename')):
            fact.rows.append(row)
    for event in events:
        fact = facts.get(int(event['playlist_id']))
        # A retargeted watch's events of its old target are history.
        if fact is not None and event['watch_key'] == fact.watch.spotify_id:
            fact.events.append(event)
    return facts


def _storage(
    fact: _WatchFacts,
    sizes: dict[str, int],
    holders: dict[str, set[int]],
) -> dict[str, Any]:
    files = {norm_path(row['filename']) for row in fact.rows}
    present = sorted(name for name in files if name in sizes)
    unique = [name for name in present if len(holders[name]) == 1]
    shared = [name for name in present if len(holders[name]) > 1]
    return {
        'files': len(present),
        'missing': len(files) - len(present),
        'unique_files': len(unique),
        'shared_files': len(shared),
        'bytes': sum(sizes[name] for name in present),
        'unique_bytes': sum(sizes[name] for name in unique),
        'shared_bytes': sum(sizes[name] for name in shared),
        'share_bytes': round(
            sum(sizes[name] / len(holders[name]) for name in present)
        ),
    }


def _status(
    fact: _WatchFacts,
    firsts: dict[tuple[int, str, str], dict[str, Any]],
    sizes: dict[str, int],
    providers: dict[str, str],
) -> tuple[dict[str, int], dict[str, int]]:
    """How the tracks on disk got into the watch, and which provider
    fetched their files."""

    outcomes: Counter[str] = Counter()
    by_provider: Counter[str] = Counter()
    seen: set[str] = set()
    for row in fact.rows:
        name = norm_path(row['filename'])
        if name not in sizes or name in seen:
            continue
        seen.add(name)
        first = firsts.get((
            fact.watch.id,
            fact.watch.spotify_id,
            str(row['track_spotify_id']),
        ))
        outcomes[first['outcome'] if first else OUTCOME_UNKNOWN] += 1
        provider = providers.get(name) or (first or {}).get('provider')
        by_provider[provider or 'unknown'] += 1
    status = {
        outcome: outcomes.get(outcome, 0)
        for outcome in (OUTCOME_DOWNLOADED, OUTCOME_LINKED, OUTCOME_UNKNOWN)
    }
    return status, dict(by_provider.most_common())


def _activity(
    fact: _WatchFacts,
    sizes: dict[str, int],
    now: datetime,
    days: int,
) -> dict[str, Any]:
    period_start = now - timedelta(days=days)
    counts: Counter[str] = Counter()
    added_times: list[datetime] = []
    added_files: set[str] = set()
    last_added: Optional[datetime] = None
    for event in fact.events:
        moment = parse_time(event['happened_at'])
        if moment is None:
            continue
        added = event['outcome'] in ADDED and not event['initial']
        if added:
            added_times.append(moment)
            last_added = (
                moment if last_added is None else max(last_added, moment)
            )
        if moment < period_start:
            continue
        if event['initial']:
            counts['initial'] += 1
            continue
        counts[event['outcome']] += 1
        if added:
            added_files.add(norm_path(event['filename']))

    # The watch began when its target was first checked (a retargeted
    # watch, at its new target), else when it was added.
    began = parse_time(fact.events[0]['happened_at']) if fact.events else None
    began = began or parse_time(fact.watch.created_at) or now
    series = activity_series(added_times, now, began, days)
    added_count = counts[OUTCOME_DOWNLOADED] + counts[OUTCOME_UNKNOWN]
    span_days = max(
        1.0, (now - max(began, period_start)).total_seconds() / 86400
    )
    per_day = added_count / span_days
    return {
        'period': {
            'added': added_count,
            'downloaded': counts[OUTCOME_DOWNLOADED],
            'linked': counts[OUTCOME_LINKED],
            'unknown': counts[OUTCOME_UNKNOWN],
            'initial': counts['initial'],
            'bytes': sum(sizes.get(name, 0) for name in added_files),
        },
        'rate': {
            'per_day': round(per_day, 3),
            'per_week': round(per_day * 7, 2),
            'per_month': round(per_day * 30, 2),
        },
        'series': series,
        'trend': trend(series),
        'last_added_at': last_added.isoformat() if last_added else None,
    }


def watch_stats(
    watches: list[MonitoredPlaylist],
    associations: list[dict[str, Any]],
    events: list[dict[str, Any]],
    sizes: dict[str, int],
    *,
    now: datetime,
    days: int = DEFAULT_DAYS,
    providers: Optional[dict[str, str]] = None,
    failures: Optional[dict[int, int]] = None,
) -> dict[str, Any]:
    """Storage, status and activity of each of *watches*.

    *associations* and *events* are every watch's rows (other watches'
    tell which files are shared); *sizes* has the library files on disk.
    """

    days = clamp_days(days)
    # What the library recorded for the file wins over the events.
    providers = {**providers_from_events(events), **(providers or {})}
    failures = failures or {}
    holders = holders_by_file(associations, sizes)
    firsts = first_events(events)
    facts = _gather(watches, associations, events)
    rows = []
    for watch in watches:
        fact = facts[watch.id]
        status, by_provider = _status(fact, firsts, sizes, providers)
        rows.append({
            'id': watch.id,
            'storage': _storage(fact, sizes, holders),
            'status': {**status, 'failing': int(failures.get(watch.id, 0))},
            'providers': by_provider,
            **_activity(fact, sizes, now, days),
        })
    files = {
        norm_path(row['filename'])
        for fact in facts.values()
        for row in fact.rows
        if norm_path(row['filename']) in sizes
    }
    return {
        'days': days,
        'bucket_days': bucket_days_for(days),
        'generated_at': now.isoformat(),
        'totals': {
            'watches': len(watches),
            'files': len(files),
            'bytes': sum(sizes[name] for name in files),
            'shared_files': sum(1 for name in files if len(holders[name]) > 1),
        },
        'watches': rows,
    }


def provenance(
    associations: list[dict[str, Any]],
    events: list[dict[str, Any]],
    watches_by_id: dict[int, MonitoredPlaylist],
) -> dict[str, Any]:
    """Where one library file came from.

    *associations* are the ``downloaded_tracks`` rows holding it and
    *events* every event about it, oldest first. ``origin`` is the first
    watch that downloaded it (``estimated`` when only an event recorded
    before outcomes were kept says so); ``holders`` every watch that
    holds it now, with how and when it got there.
    """

    firsts = first_events(events)
    holders: dict[int, dict[str, Any]] = {}
    for row in associations:
        watch = watches_by_id.get(int(row['playlist_id']))
        if watch is None:
            continue
        first = firsts.get((
            watch.id,
            watch.spotify_id,
            str(row['track_spotify_id']),
        ))
        entry = {
            'watch': watch,
            'added_at': first['happened_at']
            if first
            else row['downloaded_at'],
            'outcome': first['outcome'] if first else OUTCOME_UNKNOWN,
            'initial': bool(first and first['initial']),
        }
        known = holders.get(watch.id)
        if known is None or str(entry['added_at']) < str(known['added_at']):
            holders[watch.id] = entry
    return {
        'origin': _origin(events, watches_by_id),
        'holders': sorted(holders.values(), key=lambda h: str(h['added_at'])),
    }


def _origin(
    events: list[dict[str, Any]],
    watches_by_id: dict[int, MonitoredPlaylist],
) -> Optional[dict[str, Any]]:
    event = next(
        (e for e in events if e['outcome'] == OUTCOME_DOWNLOADED), None
    )
    estimated = event is None
    if event is None:
        event = next(
            (e for e in events if e['outcome'] == OUTCOME_UNKNOWN), None
        )
    if event is None:
        return None
    watch = watches_by_id.get(int(event['playlist_id']))
    # Gone, or since pointed at another playlist: only the name is left.
    current = watch is not None and watch.spotify_id == event['watch_key']
    return {
        'watch': watch if current else None,
        'watch_id': int(event['playlist_id']),
        'user_id': int(event.get('user_id') or 0),
        'name': str(event['watch_name']),
        'at': event['happened_at'],
        'provider': str(event['provider'] or ''),
        'initial': bool(event['initial']),
        'estimated': estimated,
    }
