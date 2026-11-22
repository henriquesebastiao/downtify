"""Write-contention benchmark for the server's stores.

Builds real store objects, then runs worker threads that perform "finished
download" write bundles plus one monitor thread that drives DownloadPolicy
begin/finish. Runs on SQLite (a temporary directory) or on PostgreSQL (a
fresh throwaway schema, dropped afterwards). Prints a plain-text summary.
Synthetic data only; never touches a user's library or configuration.
"""

from __future__ import annotations

import argparse
import math
import shutil
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import psycopg  # noqa: E402
from psycopg import sql  # noqa: E402

from downtify.activity import ActivityLog  # noqa: E402
from downtify.db.core import Database  # noqa: E402
from downtify.db.errors import SerializationRetry  # noqa: E402
from downtify.db.migrations.runner import run_migrations  # noqa: E402
from downtify.download_log import DownloadLog  # noqa: E402
from downtify.download_policy import DownloadPolicy  # noqa: E402
from downtify.file_providers import FileProviders  # noqa: E402
from downtify.library_sync import LibrarySync  # noqa: E402
from downtify.sqlite_utils import connect_sqlite  # noqa: E402
from downtify.track_owners import TrackOwners  # noqa: E402

LOCKED_MARKER = 'database is locked'
OpFn = Callable[..., Any]
Run = tuple[list['Recorder'], float, int]


@dataclass
class Recorder:
    """Per-thread measurements; merged after the threads stop."""

    latencies: list[float] = field(default_factory=list)
    errors: int = 0
    locked: int = 0
    conflicts: int = 0


@dataclass
class Summary:
    """Merged measurements for one backend run."""

    backend: str
    stores: list[str]
    skipped: list[str]
    threads: int
    elapsed: float
    total: int
    ops_per_s: float
    p50_ms: float
    p95_ms: float
    errors: int
    locked: int
    conflicts: int


def _timed(rec: Recorder, fn: OpFn, *args: Any, **kwargs: Any) -> Any:
    """Run one operation, record its latency and any failure."""
    start = time.perf_counter()
    try:
        result = fn(*args, **kwargs)
    except Exception as exc:
        rec.latencies.append(time.perf_counter() - start)
        rec.errors += 1
        if LOCKED_MARKER in str(exc):
            rec.locked += 1
        elif isinstance(exc, SerializationRetry):
            # PostgreSQL deadlocks (40P01) and serialization failures (40001).
            rec.conflicts += 1
        return None
    rec.latencies.append(time.perf_counter() - start)
    return result


def _sqlite_connector(path: Path) -> Callable[[], Any]:
    """Connection factory matching the server's monitor-side wiring."""

    def connect() -> Any:
        conn = connect_sqlite(str(path), row_factory=True)
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    return connect


def _build_stores(
    source: Callable[[str], Any], connect: Callable[[], Any]
) -> tuple[dict[str, Any], list[str]]:
    """Construct each store; *source* maps a file name to its store input.

    On SQLite the input is a path under a temporary directory; on PostgreSQL
    every store shares one Database object. Collects skip reasons.
    """
    builders: list[tuple[str, Callable[[], Any]]] = [
        ('TrackOwners', lambda: TrackOwners(source('track_owners.db'))),
        ('LibrarySync', lambda: LibrarySync(source('library_sync.db'))),
        ('DownloadLog', lambda: DownloadLog(source('download_log.db'))),
        ('FileProviders', lambda: FileProviders(source('file_providers.db'))),
        ('ActivityLog', lambda: ActivityLog(source('activity.db'))),
        ('DownloadPolicy', lambda: DownloadPolicy(connect)),
    ]
    stores: dict[str, Any] = {}
    skipped: list[str] = []
    for name, build in builders:
        try:
            stores[name] = build()
        except Exception as exc:
            skipped.append(f'{name} ({type(exc).__name__}: {exc})')
    return stores, skipped


def _bundle_ops(stores: dict[str, Any]) -> list[OpFn]:
    """One write per store for a finished download; args are (tid, key)."""
    ops: list[OpFn] = []
    owners = stores.get('TrackOwners')
    if owners is not None:
        ops.append(
            lambda tid, key: owners.add(key, tid + 1, f'/synthetic/{key}')
        )
    sync = stores.get('LibrarySync')
    if sync is not None:
        ops.append(lambda tid, key: sync.touch(f'/synthetic/{key}'))
    log = stores.get('DownloadLog')
    if log is not None:
        ops.append(
            lambda tid, key: log.record(
                'completed', provider='bench', size=tid, filename=key
            )
        )
    providers = stores.get('FileProviders')
    if providers is not None:
        ops.append(
            lambda tid, key: providers.record(
                key, f'/synthetic/{key}', 'bench'
            )
        )
    activity = stores.get('ActivityLog')
    if activity is not None:
        ops.append(
            lambda tid, key: activity.record(
                'bench', user_id=tid + 1, summary=key
            )
        )
    return ops


def _writer(
    tid: int, ops: list[OpFn], stop: threading.Event, rec: Recorder
) -> None:
    i = 0
    while not stop.is_set():
        key = f't{tid}-{i}'
        for op in ops:
            _timed(rec, op, tid, key)
        i += 1


def _monitor(policy: Any, stop: threading.Event, rec: Recorder) -> None:
    """Begin and finish download attempts on DownloadPolicy in a loop."""
    i = 0
    while not stop.is_set():
        song = {
            'song_id': f'mon-{i}',
            'name': f'Monitor {i}',
            'artists': ['Bench'],
            'duration': 1,
        }
        attempt = _timed(rec, policy.begin, song, 60)
        if attempt is not None:
            _timed(rec, attempt.finish, successful=True)
        i += 1


def _percentile(sorted_vals: list[float], p: float) -> float:
    """Nearest-rank percentile; 0.0 when there are no samples."""
    if not sorted_vals:
        return 0.0
    rank = max(1, math.ceil(p * len(sorted_vals)))
    return sorted_vals[rank - 1]


def _run(stores: dict[str, Any], seconds: float, threads: int) -> Run:
    """Run writer and monitor threads for *seconds*; return measurements."""
    ops = _bundle_ops(stores)
    policy = stores.get('DownloadPolicy')
    stop = threading.Event()
    workers: list[threading.Thread] = []
    recs: list[Recorder] = []

    for tid in range(threads if ops else 0):
        rec = Recorder()
        recs.append(rec)
        workers.append(
            threading.Thread(
                target=_writer, args=(tid, ops, stop, rec), daemon=True
            )
        )
    if policy is not None:
        rec = Recorder()
        recs.append(rec)
        workers.append(
            threading.Thread(
                target=_monitor, args=(policy, stop, rec), daemon=True
            )
        )

    start = time.perf_counter()
    for thread in workers:
        thread.start()
    time.sleep(seconds)
    stop.set()
    for thread in workers:
        thread.join()
    elapsed = time.perf_counter() - start
    return recs, elapsed, len(workers)


def _summarize(
    backend: str,
    stores: dict[str, Any],
    skipped: list[str],
    run: Run,
) -> Summary:
    recs, elapsed, nthreads = run
    latencies = sorted(lat for rec in recs for lat in rec.latencies)
    total = len(latencies)
    return Summary(
        backend=backend,
        stores=sorted(stores),
        skipped=skipped,
        threads=nthreads,
        elapsed=elapsed,
        total=total,
        ops_per_s=total / elapsed if elapsed > 0 else 0.0,
        p50_ms=_percentile(latencies, 0.50) * 1000,
        p95_ms=_percentile(latencies, 0.95) * 1000,
        errors=sum(rec.errors for rec in recs),
        locked=sum(rec.locked for rec in recs),
        conflicts=sum(rec.conflicts for rec in recs),
    )


def _bench_sqlite(seconds: float, threads: int) -> Summary:
    root = Path(tempfile.mkdtemp(prefix='db_contention_'))
    try:
        stores, skipped = _build_stores(
            lambda name: root / name,
            _sqlite_connector(root / 'download_policy.db'),
        )
        run = _run(stores, seconds, threads)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return _summarize('sqlite', stores, skipped, run)


def _bench_postgres(
    seconds: float, threads: int, database_url: str
) -> Summary:
    """Run on a fresh schema; the schema is always dropped afterwards."""
    schema = f'bench_{uuid.uuid4().hex[:8]}'
    max_size = max(20, threads + 4)
    with psycopg.connect(database_url, autocommit=True) as admin:
        admin.execute(
            sql.SQL('create schema {}').format(sql.Identifier(schema))
        )
        db: Database | None = None
        try:
            db = Database.postgres(
                database_url, max_size=max_size, search_path=schema
            )
            run_migrations(db)
            stores, skipped = _build_stores(lambda _name: db, db.connect)
            run = _run(stores, seconds, threads)
        finally:
            if db is not None:
                db.close()
            admin.execute(
                sql.SQL('drop schema {} cascade').format(
                    sql.Identifier(schema)
                )
            )
    return _summarize('postgresql', stores, skipped, run)


def _print_summary(s: Summary) -> None:
    for name in s.skipped:
        print(f'skipped: {name}')
    print(f'stores: {", ".join(s.stores) or "none"}')
    print(f'backend: {s.backend}')
    print(f'threads: {s.threads}')
    print(f'elapsed_s: {s.elapsed:.2f}')
    print(f'total_ops: {s.total}')
    print(f'ops_per_s: {s.ops_per_s:.1f}')
    print(f'p50_ms: {s.p50_ms:.3f}')
    print(f'p95_ms: {s.p95_ms:.3f}')
    print(f'errors: {s.errors}')
    print(f'database_is_locked: {s.locked}')
    if s.backend == 'postgresql':
        print(f'pg_conflicts: {s.conflicts}')
    print(f'skipped_stores: {len(s.skipped)}')
    for name in s.skipped:
        print(f'  - {name}')


def _print_compare(a: Summary, b: Summary) -> None:
    rows = [
        ('threads', str(a.threads), str(b.threads)),
        ('total_ops', str(a.total), str(b.total)),
        ('ops_per_s', f'{a.ops_per_s:.1f}', f'{b.ops_per_s:.1f}'),
        ('p50_ms', f'{a.p50_ms:.3f}', f'{b.p50_ms:.3f}'),
        ('p95_ms', f'{a.p95_ms:.3f}', f'{b.p95_ms:.3f}'),
        ('errors', str(a.errors), str(b.errors)),
        ('database_is_locked', str(a.locked), str(b.locked)),
        ('pg_conflicts', 'n/a', str(b.conflicts)),
        ('skipped_stores', str(len(a.skipped)), str(len(b.skipped))),
    ]
    print(f'{"metric":<20}{a.backend:>14}{b.backend:>14}')
    for label, left, right in rows:
        print(f'{label:<20}{left:>14}{right:>14}')
    ratio = b.ops_per_s / a.ops_per_s if a.ops_per_s > 0 else 0.0
    winner = b.backend if b.ops_per_s >= a.ops_per_s else a.backend
    print(
        f'verdict: {winner} had higher ops/s ({b.backend}/{a.backend} '
        f'{ratio:.2f}x); p95 {b.p95_ms:.3f} vs {a.p95_ms:.3f} ms; '
        f'errors {b.errors} vs {a.errors}; pg_conflicts {b.conflicts}'
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Measure write contention on the stores.'
    )
    parser.add_argument('--seconds', type=float, default=10.0)
    parser.add_argument('--threads', type=int, default=6)
    parser.add_argument(
        '--database-url',
        default=None,
        help='PostgreSQL URL; runs on a fresh schema that is then dropped.',
    )
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Run SQLite, then PostgreSQL (needs --database-url); compare.',
    )
    args = parser.parse_args(argv)

    if args.seconds <= 0 or args.threads < 1:
        parser.error('--seconds must be > 0 and --threads must be >= 1')
    if args.compare:
        if not args.database_url:
            parser.error('--compare needs --database-url')
        sqlite = _bench_sqlite(args.seconds, args.threads)
        postgres = _bench_postgres(
            args.seconds, args.threads, args.database_url
        )
        _print_compare(sqlite, postgres)
        return 0
    if args.database_url:
        _print_summary(
            _bench_postgres(args.seconds, args.threads, args.database_url)
        )
    else:
        _print_summary(_bench_sqlite(args.seconds, args.threads))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
