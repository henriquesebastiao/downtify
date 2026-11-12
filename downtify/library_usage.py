"""Library storage and download usage (``GET /api/library/usage``).

Pure functions over what the server already knows - the library listing
rows (their ``size`` and file date), which provider fetched each file
and when (:mod:`downtify.file_providers`), the download outcomes
(:mod:`downtify.download_log`) and the daily size snapshots kept here
(:class:`UsageSnapshots`). ``downtify/api.py`` does the I/O.

What counts as the library: every file the Library lists, minus the
*working copies* - transfers slskd left in its own folder after
Downtify copied them into the library (recorded since this was kept),
and, while slskd files aren't left in place, any other file in slskd's
folder nothing records as a library song. Those copies are listed apart
so a source copy is never taken for unique library content.

Growth comes from the snapshots; for the days before the first one, the
curve is *estimated* from the dates of the files still in the library
(when each was downloaded, else its modified time), so it never shows
what was deleted since. Duplicates are files holding the same song:
*exact* ones share a name and size, *likely* ones the same artist and
title (see :func:`downtify.library_catalog.song_key`) and a length
within :data:`DURATION_TOLERANCE` seconds.
"""

from __future__ import annotations

import bisect
import json
import math
import sqlite3
from collections import defaultdict
from collections.abc import Collection, Iterable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Optional

from .download_log import OUTCOME_COMPLETED, OUTCOMES
from .file_providers import guess_provider
from .library_catalog import entry_content_key, song_key
from .library_paths import EXTERNAL_LIBRARY_PREFIX, SLSKD_LIBRARY_PREFIX
from .sqlite_utils import connect_sqlite
from .watch_stats import (
    DEFAULT_DAYS,
    bucket_days_for,
    clamp_days,
    norm_path,
    parse_time,
)

#: Where a library file lives.
LOCATION_DOWNLOADS = 'downloads'
LOCATION_SLSKD = 'slskd'
LOCATION_FOLDERS = 'folders'

#: Provider of a file nothing recorded and its path doesn't give away.
UNKNOWN = 'unknown'

#: Two files of one song may differ this much in length (seconds).
DURATION_TOLERANCE = 3.0
#: How many duplicate groups / working copies are listed by name.
EXAMPLES = 50
#: The growth curve has a point per day up to this many days, then one a
#: week.
DAILY_POINTS_UP_TO = 90


def location_of(path: Any) -> str:
    """``downloads``, ``slskd`` or ``folders`` (extra music folders)."""

    name = norm_path(path)
    if name.startswith(SLSKD_LIBRARY_PREFIX):
        return LOCATION_SLSKD
    if name.startswith(EXTERNAL_LIBRARY_PREFIX):
        return LOCATION_FOLDERS
    return LOCATION_DOWNLOADS


def _size(entry: dict[str, Any]) -> int:
    try:
        return max(0, int(entry.get('size') or 0))
    except (TypeError, ValueError):
        return 0


def _format(path: str) -> str:
    return PurePosixPath(path).suffix.lstrip('.').lower() or UNKNOWN


def provider_of(path: str, providers: dict[str, str]) -> str:
    return providers.get(path) or guess_provider(path) or UNKNOWN


def split_working_copies(
    entries: Iterable[dict[str, Any]],
    *,
    sources: dict[str, int],
    slskd_in_place: bool,
    referenced: Collection[str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """``(library rows, {working copy: size})``.

    *sources* are the recorded transfers still on disk, ``{library path:
    size}`` (a path outside the library folders stays as given). While
    slskd files aren't left in place (*slskd_in_place* false), an
    ``slskd/`` file is a working copy too unless *referenced* - the
    track index or the provider records name it as a library song.
    """

    library: list[dict[str, Any]] = []
    working: dict[str, int] = {}
    for entry in entries:
        name = norm_path(entry.get('file'))
        if not name:
            continue
        if name in sources or (
            not slskd_in_place
            and name.startswith(SLSKD_LIBRARY_PREFIX)
            and name not in referenced
        ):
            working[name] = _size(entry)
        else:
            library.append(entry)
    for name, size in sources.items():
        working.setdefault(norm_path(name), max(0, int(size)))
    return library, working


def _breakdown(
    rows: Iterable[tuple[str, int]],
) -> list[dict[str, Any]]:
    """``[{id, files, bytes}]``, biggest first, from ``(id, size)``."""

    files: dict[str, int] = defaultdict(int)
    sizes: dict[str, int] = defaultdict(int)
    for key, size in rows:
        files[key] += 1
        sizes[key] += size
    return sorted(
        (
            {'id': key, 'files': files[key], 'bytes': sizes[key]}
            for key in files
        ),
        key=lambda row: (-row['bytes'], -row['files'], row['id']),
    )


def library_totals(
    entries: list[dict[str, Any]], providers: dict[str, str]
) -> dict[str, Any]:
    """Size of the library, by provider, location and format."""

    sized = [(norm_path(e.get('file')), _size(e)) for e in entries]
    return {
        'files': len(sized),
        'bytes': sum(size for _name, size in sized),
        'by_provider': _breakdown(
            (provider_of(name, providers), size) for name, size in sized
        ),
        'by_location': _breakdown(
            (location_of(name), size) for name, size in sized
        ),
        'by_format': _breakdown((_format(name), size) for name, size in sized),
    }


def added_times(
    entries: Iterable[dict[str, Any]], recorded: dict[str, str]
) -> dict[str, datetime]:
    """When each file came into the library: the download time the
    provider records keep, else the file's modified time."""

    times: dict[str, datetime] = {}
    for entry in entries:
        name = norm_path(entry.get('file'))
        moment = parse_time(recorded.get(name)) if name in recorded else None
        if moment is None:
            try:
                stamp = float(entry.get('added') or 0)
            except (TypeError, ValueError):
                stamp = 0.0
            if stamp > 0:
                moment = datetime.fromtimestamp(stamp, timezone.utc)
        if moment is not None:
            times[name] = moment
    return times


def _bucket(
    moment: datetime, now: datetime, span: timedelta, count: int
) -> Optional[int]:
    """Which of *count* buckets of *span* ending *now* holds *moment*
    (oldest first), or ``None``."""

    if moment > now:
        return None
    index = count - 1 - math.floor((now - moment) / span)
    return index if 0 <= index < count else None


def period_added(
    entries: list[dict[str, Any]],
    times: dict[str, datetime],
    providers: dict[str, str],
    *,
    now: datetime,
    days: int,
) -> dict[str, Any]:
    """Songs still in the library that came in during the last *days*:
    how many, their size, by provider and per day or week."""

    bucket_days = bucket_days_for(days)
    span = timedelta(days=bucket_days)
    count = math.ceil(days / bucket_days)
    series = [{'files': 0, 'bytes': 0} for _ in range(count)]
    start = now - timedelta(days=days)
    added: list[tuple[str, int]] = []
    for entry in entries:
        name = norm_path(entry.get('file'))
        moment = times.get(name)
        if moment is None or moment < start or moment > now:
            continue
        size = _size(entry)
        added.append((name, size))
        index = _bucket(moment, now, span, count)
        if index is not None:
            series[index]['files'] += 1
            series[index]['bytes'] += size
    return {
        'files': len(added),
        'bytes': sum(size for _name, size in added),
        'by_provider': _breakdown(
            (provider_of(name, providers), size) for name, size in added
        ),
        'bucket_days': bucket_days,
        'series': series,
    }


class _Estimate:
    """How big today's files added up to at a given moment."""

    def __init__(
        self, entries: list[dict[str, Any]], times: dict[str, datetime]
    ) -> None:
        dated = sorted(
            (moment, _size(entry))
            for entry in entries
            if (moment := times.get(norm_path(entry.get('file')))) is not None
        )
        self._moments = [moment for moment, _size_ in dated]
        self._running = [0]
        for _moment, size in dated:
            self._running.append(self._running[-1] + size)

    def before(self, end: datetime) -> tuple[int, int]:
        """``(files, bytes)`` of the files that came in before *end*."""

        count = bisect.bisect_left(self._moments, end)
        return count, self._running[count]


def _point(
    day: date, files: int, size: int, estimated: bool
) -> dict[str, Any]:
    return {
        'day': day.isoformat(),
        'files': int(files),
        'bytes': int(size),
        'estimated': estimated,
    }


def growth(
    snapshots: list[dict[str, Any]],
    entries: list[dict[str, Any]],
    times: dict[str, datetime],
    *,
    now: datetime,
    days: int,
    current: dict[str, int],
) -> dict[str, Any]:
    """The library's size at the end of each day (or week) of the last
    *days*, oldest first, ending with *current* (``{files, bytes}``).

    A day takes the latest snapshot up to it; a day before the first
    snapshot is ``estimated`` from the dates of today's files.
    """

    step = 1 if days <= DAILY_POINTS_UP_TO else 7
    count = days // step + 1
    today = now.date()
    by_day = sorted(
        (str(row['day']), row) for row in snapshots if row.get('day')
    )
    estimate = _Estimate(entries, times)
    points: list[dict[str, Any]] = []
    for index in range(count):
        day = today - timedelta(days=(count - 1 - index) * step)
        snapshot = _latest_on(by_day, day.isoformat())
        if day == today:
            points.append(
                _point(day, current['files'], current['bytes'], False)
            )
        elif snapshot is not None:
            points.append(
                _point(day, snapshot['files'], snapshot['bytes'], False)
            )
        else:
            end = datetime.combine(
                day + timedelta(days=1), datetime.min.time(), timezone.utc
            )
            points.append(_point(day, *estimate.before(end), True))
    first, last = points[0], points[-1]
    change = last['bytes'] - first['bytes']
    return {
        'step_days': step,
        'points': points,
        'change': {
            'files': last['files'] - first['files'],
            'bytes': change,
        },
        'per_day_bytes': round(change / max(1, (count - 1) * step)),
        'since': by_day[0][0] if by_day else None,
    }


def _latest_on(
    by_day: list[tuple[str, dict[str, Any]]], day: str
) -> Optional[dict[str, Any]]:
    found = None
    for key, row in by_day:
        if key > day:
            break
        found = row
    return found


def forecast_days(
    disk: Optional[dict[str, int]], per_day_bytes: int
) -> Optional[int]:
    """Days until the disk fills at *per_day_bytes*, if it grows."""

    if not disk or per_day_bytes <= 0:
        return None
    return int(max(0, int(disk.get('free') or 0)) // per_day_bytes)


class _Groups:
    """Union-find over file names."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def find(self, name: str) -> str:
        parent = self._parent.setdefault(name, name)
        while parent != self._parent[parent]:
            self._parent[parent] = self._parent[self._parent[parent]]
            parent = self._parent[parent]
        self._parent[name] = parent
        return parent

    def join(self, names: list[str]) -> None:
        roots = [self.find(name) for name in names]
        for root in roots[1:]:
            self._parent[root] = roots[0]


def _duration(entry: dict[str, Any]) -> float:
    try:
        return float(entry.get('duration') or 0)
    except (TypeError, ValueError):
        return 0.0


def _same_length_runs(rows: list[dict[str, Any]]) -> list[list[str]]:
    """Files of one artist/title whose lengths chain within the
    tolerance; files of unknown length never match on it."""

    timed = sorted(
        ((d, norm_path(r.get('file'))) for r in rows if (d := _duration(r))),
    )
    runs: list[list[str]] = []
    run: list[str] = []
    previous = 0.0
    for length, name in timed:
        if run and length - previous > DURATION_TOLERANCE:
            runs.append(run)
            run = []
        run.append(name)
        previous = length
    if run:
        runs.append(run)
    return [names for names in runs if len(names) > 1]


def duplicates(
    entries: list[dict[str, Any]], providers: dict[str, str]
) -> dict[str, Any]:
    """Library files holding the same song more than once.

    ``bytes`` is what keeping only the biggest file of each group would
    free. ``groups`` lists the :data:`EXAMPLES` that would free most.
    """

    by_file = {norm_path(e.get('file')): e for e in entries}
    by_file.pop('', None)
    groups = _Groups()
    by_key: dict[str, list[str]] = defaultdict(list)
    by_song: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for name, entry in by_file.items():
        key = entry_content_key(entry)
        if key:
            by_key[key].append(name)
        song = song_key(
            str(entry.get('artist') or ''), str(entry.get('title') or '')
        )
        if song != '|':
            by_song[song].append(entry)
    for names in by_key.values():
        if len(names) > 1:
            groups.join(names)
    for rows in by_song.values():
        if len(rows) > 1:
            for run in _same_length_runs(rows):
                groups.join(run)
    members: dict[str, list[str]] = defaultdict(list)
    for name in by_file:
        members[groups.find(name)].append(name)
    found = [
        _duplicate_group(sorted(names), by_file, providers)
        for names in members.values()
        if len(names) > 1
    ]
    found.sort(key=lambda g: (-g['bytes'], g['files'][0]['file']))
    totals = {
        kind: {
            'groups': sum(1 for g in found if g['kind'] == kind),
            'files': sum(
                len(g['files']) - 1 for g in found if g['kind'] == kind
            ),
            'bytes': sum(g['bytes'] for g in found if g['kind'] == kind),
        }
        for kind in ('exact', 'likely')
    }
    return {
        'groups': len(found),
        'files': sum(len(g['files']) - 1 for g in found),
        'bytes': sum(g['bytes'] for g in found),
        'exact': totals['exact'],
        'likely': totals['likely'],
        'examples': found[:EXAMPLES],
    }


def _duplicate_group(
    names: list[str],
    by_file: dict[str, dict[str, Any]],
    providers: dict[str, str],
) -> dict[str, Any]:
    rows = [by_file[name] for name in names]
    sizes = [_size(row) for row in rows]
    keys = {entry_content_key(row) for row in rows}
    first = rows[0]
    return {
        'kind': 'exact' if len(keys) == 1 and '' not in keys else 'likely',
        'title': str(first.get('title') or ''),
        'artist': str(first.get('artist') or ''),
        'bytes': sum(sizes) - max(sizes),
        'files': sorted(
            (
                {
                    'file': name,
                    'bytes': size,
                    'provider': provider_of(name, providers),
                    'codec': str(row.get('codec') or ''),
                    'bitrate': int(row.get('bitrate') or 0),
                }
                for name, row, size in zip(names, rows, sizes)
            ),
            key=lambda item: (-item['bytes'], item['file']),
        ),
    }


def download_totals(
    rows: list[dict[str, Any]],
    *,
    now: datetime,
    days: int,
    first_at: Optional[str] = None,
) -> dict[str, Any]:
    """How the downloads of the last *days* ended, per day or week."""

    bucket_days = bucket_days_for(days)
    span = timedelta(days=bucket_days)
    count = math.ceil(days / bucket_days)
    series = [dict.fromkeys(OUTCOMES, 0) for _ in range(count)]
    totals = dict.fromkeys(OUTCOMES, 0)
    completed: list[tuple[str, int]] = []
    start = now - timedelta(days=days)
    for row in rows:
        moment = parse_time(row.get('at'))
        outcome = row.get('outcome')
        if moment is None or outcome not in totals or moment < start:
            continue
        totals[outcome] += 1
        index = _bucket(moment, now, span, count)
        if index is not None:
            series[index][outcome] += 1
        if outcome == OUTCOME_COMPLETED:
            completed.append((
                str(row.get('provider') or '') or UNKNOWN,
                max(0, int(row.get('bytes') or 0)),
            ))
    return {
        **totals,
        'bytes': sum(size for _provider, size in completed),
        'by_provider': _breakdown(completed),
        'bucket_days': bucket_days,
        'series': series,
        'since': first_at,
    }


def usage_report(
    entries: list[dict[str, Any]],
    *,
    providers: dict[str, str],
    recorded: dict[str, str],
    sources: dict[str, int],
    slskd_in_place: bool,
    referenced: Collection[str],
    snapshots: list[dict[str, Any]],
    downloads: list[dict[str, Any]],
    downloads_since: Optional[str],
    disk: Optional[dict[str, int]],
    now: datetime,
    days: int = DEFAULT_DAYS,
) -> dict[str, Any]:
    """Everything the library usage page shows but the folder scan.

    *entries* are the listing rows, *providers* ``{path: provider}``,
    *recorded* ``{path: download time}``, *sources* the recorded slskd
    transfers still on disk (see :func:`split_working_copies`),
    *snapshots* the daily sizes kept (:class:`UsageSnapshots`),
    *downloads* the download log rows of the period and *disk* the
    downloads folder's volume (``{total, used, free}``).
    """

    days = clamp_days(days)
    library, working = split_working_copies(
        entries,
        sources=sources,
        slskd_in_place=slskd_in_place,
        referenced=referenced,
    )
    totals = library_totals(library, providers)
    times = added_times(library, recorded)
    grown = growth(
        snapshots,
        library,
        times,
        now=now,
        days=days,
        current={'files': totals['files'], 'bytes': totals['bytes']},
    )
    largest = sorted(working.items(), key=lambda item: (-item[1], item[0]))
    return {
        'days': days,
        'generated_at': now.isoformat(),
        'library': totals,
        'period': period_added(library, times, providers, now=now, days=days),
        'growth': grown,
        'downloads': download_totals(
            downloads, now=now, days=days, first_at=downloads_since
        ),
        'duplicates': duplicates(library, providers),
        'working': {
            'files': len(working),
            'bytes': sum(working.values()),
            'slskd_in_place': slskd_in_place,
            'examples': [
                {'file': name, 'bytes': size}
                for name, size in largest[:EXAMPLES]
            ],
        },
        'disk': (
            {**disk, 'days_left': forecast_days(disk, grown['per_day_bytes'])}
            if disk
            else None
        ),
    }


def snapshot_of(report: dict[str, Any]) -> dict[str, Any]:
    """What :class:`UsageSnapshots` keeps of a :func:`usage_report`."""

    library = report['library']
    return {
        'files': library['files'],
        'bytes': library['bytes'],
        'working_files': report['working']['files'],
        'working_bytes': report['working']['bytes'],
        'by_provider': library['by_provider'],
        'by_location': library['by_location'],
    }


def library_snapshot(
    entries: list[dict[str, Any]],
    *,
    providers: dict[str, str],
    sources: dict[str, int],
    slskd_in_place: bool,
    referenced: Collection[str],
) -> dict[str, Any]:
    """The same as :func:`snapshot_of`, without the rest of the report
    (what the hourly reading needs)."""

    library, working = split_working_copies(
        entries,
        sources=sources,
        slskd_in_place=slskd_in_place,
        referenced=referenced,
    )
    totals = library_totals(library, providers)
    return {
        'files': totals['files'],
        'bytes': totals['bytes'],
        'working_files': len(working),
        'working_bytes': sum(working.values()),
        'by_provider': totals['by_provider'],
        'by_location': totals['by_location'],
    }


class UsageSnapshots:
    """The library's size once a day (the last reading of the day wins)."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS library_usage_snapshots (
                    day TEXT PRIMARY KEY,
                    taken_at TEXT NOT NULL,
                    files INTEGER NOT NULL DEFAULT 0,
                    bytes INTEGER NOT NULL DEFAULT 0,
                    working_files INTEGER NOT NULL DEFAULT 0,
                    working_bytes INTEGER NOT NULL DEFAULT 0,
                    detail_json TEXT NOT NULL DEFAULT '{}'
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def record(self, snapshot: dict[str, Any], now: datetime) -> None:
        detail = {
            key: snapshot.get(key) or []
            for key in ('by_provider', 'by_location')
        }
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO library_usage_snapshots
                   (day, taken_at, files, bytes, working_files,
                    working_bytes, detail_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(day) DO UPDATE SET
                   taken_at = excluded.taken_at,
                   files = excluded.files,
                   bytes = excluded.bytes,
                   working_files = excluded.working_files,
                   working_bytes = excluded.working_bytes,
                   detail_json = excluded.detail_json""",
                (
                    now.date().isoformat(),
                    now.isoformat(),
                    int(snapshot.get('files') or 0),
                    int(snapshot.get('bytes') or 0),
                    int(snapshot.get('working_files') or 0),
                    int(snapshot.get('working_bytes') or 0),
                    json.dumps(detail),
                ),
            )

    def since(self, day: str) -> list[dict[str, Any]]:
        """Snapshots from *day* (``YYYY-MM-DD``) on, oldest first - plus
        the last one before it, which still stands for that day."""

        with self._connect() as conn:
            before = conn.execute(
                'SELECT day, files, bytes, working_files, working_bytes '
                'FROM library_usage_snapshots WHERE day < ? '
                'ORDER BY day DESC LIMIT 1',
                (day,),
            ).fetchall()
            rows = conn.execute(
                'SELECT day, files, bytes, working_files, working_bytes '
                'FROM library_usage_snapshots WHERE day >= ? ORDER BY day',
                (day,),
            ).fetchall()
        return [dict(row) for row in (*before, *rows)]
