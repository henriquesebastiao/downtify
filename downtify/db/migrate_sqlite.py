"""One-shot copy of an existing SQLite install into the PostgreSQL schema.

``migrate`` reads the six SQLite files under a data directory (read-only,
they are never modified), copies every table into the same-named table of
the baseline PostgreSQL schema, fixes the identity sequences, and checks
each table against its source: row counts and an order-independent digest
over every column, streamed in batches. ``verify`` runs the same check on
an already migrated install.

Tables are loaded parents first, in the order the PostgreSQL foreign keys
require. The whole load is one transaction: a failure rolls it back and
leaves the target as it was. A verification mismatch does not raise; it is
recorded in the returned :class:`Report`, whose ``ok`` is then False.
"""

from __future__ import annotations

import contextlib
import hashlib
import sqlite3
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql

from downtify.db.config import GROUP_FILES, Dialect
from downtify.db.core import Database
from downtify.db.migrations.runner import run_migrations

MARKER_NAME = 'MIGRATED_TO_POSTGRES'
BATCH_SIZE = 5000
_MIGRATION_TABLE = 'schema_migrations'

# child table -> (parent table, child column, parent column). SQLite never
# enforced these foreign keys, so old installs may hold orphan child rows;
# they are skipped (and counted) instead of failing the load.
_ORPHAN_RULES: dict[str, tuple[str, str, str]] = {
    'playlist_tracks': ('playlists', 'playlist_name', 'name'),
}


class MigrationError(RuntimeError):
    """The migration cannot start, or the load failed and was rolled back."""


@dataclass(frozen=True)
class TableReport:
    name: str
    source_file: str
    source_rows: int
    skipped: int
    copied: int
    target_rows: int
    checksum_ok: bool


@dataclass(frozen=True)
class Report:
    files_found: list[str]
    tables: list[TableReport]
    ok: bool
    problems: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _Source:
    file_name: str
    table: str
    columns: tuple[str, ...]
    pk: tuple[str, ...]
    rowid: bool


@dataclass(frozen=True)
class _Plan:
    source: _Source
    where: str
    source_rows: int
    matched: int

    @property
    def skipped(self) -> int:
        return self.source_rows - self.matched


@dataclass(frozen=True)
class _Target:
    columns: dict[str, set[str]]
    identity: tuple[tuple[str, str], ...]
    fk_edges: frozenset[tuple[str, str]]


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _found_files(data_dir: Path) -> list[tuple[str, Path]]:
    found = []
    for name in GROUP_FILES.values():
        path = data_dir / name
        if path.is_file():
            found.append((name, path))
    return found


@contextlib.contextmanager
def _open_source(path: Path) -> Iterator[sqlite3.Connection]:
    uri = f'{path.resolve().as_uri()}?mode=ro'
    conn = sqlite3.connect(uri, uri=True)
    try:
        yield conn
    finally:
        conn.close()


def _sqlite_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND substr(name, 1, 7) <> 'sqlite_' ORDER BY name"
    ).fetchall()
    return [str(row[0]) for row in rows]


def _sqlite_source(
    file_name: str, conn: sqlite3.Connection, table: str
) -> _Source:
    info = conn.execute(f'PRAGMA table_info({_quote(table)})').fetchall()
    columns = tuple(str(row[1]) for row in info)
    pk = tuple(str(r[1]) for r in sorted(info, key=lambda r: r[5]) if r[5] > 0)
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    rowid = not (row and row[0] and 'WITHOUT ROWID' in row[0].upper())
    return _Source(file_name, table, columns, pk, rowid)


def _introspect(raw: psycopg.Connection) -> _Target:
    cur = raw.cursor()
    cur.execute(
        'SELECT table_name, column_name, is_identity '
        'FROM information_schema.columns '
        'WHERE table_schema = current_schema() '
        'ORDER BY table_name, ordinal_position'
    )
    columns: dict[str, set[str]] = {}
    identity: list[tuple[str, str]] = []
    for table, column, is_identity in cur.fetchall():
        if table == _MIGRATION_TABLE:
            continue
        columns.setdefault(table, set()).add(column)
        if is_identity == 'YES':
            identity.append((table, column))
    cur.execute(
        'SELECT parent.relname, child.relname '
        'FROM pg_constraint k '
        'JOIN pg_class child ON child.oid = k.conrelid '
        'JOIN pg_class parent ON parent.oid = k.confrelid '
        'JOIN pg_namespace n ON n.oid = child.relnamespace '
        "WHERE k.contype = 'f' AND n.nspname = current_schema()"
    )
    edges = frozenset((str(p), str(c)) for p, c in cur.fetchall())
    return _Target(columns, tuple(identity), edges)


def _populated_tables(
    raw: psycopg.Connection, tables: Iterable[str]
) -> list[str]:
    cur = raw.cursor()
    full = []
    for table in sorted(tables):
        cur.execute(
            sql.SQL('SELECT EXISTS (SELECT 1 FROM {})').format(
                sql.Identifier(table)
            )
        )
        if cur.fetchone()[0]:
            full.append(table)
    return full


def _fk_order(
    tables: Iterable[str], edges: frozenset[tuple[str, str]]
) -> list[str]:
    """Parents before children; ties broken by name, so runs are repeatable."""
    names = set(tables)
    parents = {
        table: {
            p for p, c in edges if c == table and p in names and p != table
        }
        for table in names
    }
    remaining = set(names)
    order: list[str] = []
    while remaining:
        ready = sorted(t for t in remaining if not (parents[t] & remaining))
        if not ready:
            raise MigrationError(
                'foreign-key cycle among tables: '
                + ', '.join(sorted(remaining))
            )
        order.extend(ready)
        remaining.difference_update(ready)
    return order


def _plan(
    sources: list[_Source], handles: dict[str, sqlite3.Connection]
) -> dict[str, _Plan]:
    tables_in_file: dict[str, set[str]] = {}
    for source in sources:
        tables_in_file.setdefault(source.file_name, set()).add(source.table)

    plans: dict[str, _Plan] = {}
    for source in sources:
        conn = handles[source.file_name]
        where = ''
        rule = _ORPHAN_RULES.get(source.table)
        if (
            rule is not None
            and rule[0] in tables_in_file[source.file_name]
            and rule[1] in source.columns
        ):
            parent, child_col, parent_col = rule
            col = _quote(child_col)
            where = (
                f' WHERE {col} IS NULL OR {col} IN '
                f'(SELECT {_quote(parent_col)} FROM {_quote(parent)})'
            )
        table = _quote(source.table)
        total = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        matched = conn.execute(
            f'SELECT COUNT(*) FROM {table}{where}'
        ).fetchone()[0]
        plans[source.table] = _Plan(source, where, int(total), int(matched))
    return plans


def _select_cols(columns: tuple[str, ...]) -> str:
    return ', '.join(_quote(c) for c in columns)


def _load(
    raw: psycopg.Connection,
    plans: dict[str, _Plan],
    handles: dict[str, sqlite3.Connection],
    order: list[str],
    target: _Target,
    truncate: list[str],
) -> dict[str, int]:
    cur = raw.cursor()
    if truncate:
        cur.execute(
            sql.SQL('TRUNCATE {} RESTART IDENTITY CASCADE').format(
                sql.SQL(', ').join(sql.Identifier(t) for t in truncate)
            )
        )

    copied: dict[str, int] = {}
    for table in order:
        plan = plans[table]
        source = plan.source
        select = (
            f'SELECT {_select_cols(source.columns)} '
            f'FROM {_quote(table)}{plan.where}'
        )
        if source.rowid:
            # Postgres assigns identity ids in this order, keeping them
            # in the order the rows were inserted.
            select += ' ORDER BY rowid'
        copy_sql = sql.SQL('COPY {} ({}) FROM STDIN').format(
            sql.Identifier(table),
            sql.SQL(', ').join(sql.Identifier(c) for c in source.columns),
        )
        count = 0
        reader = handles[source.file_name].execute(select)
        with cur.copy(copy_sql) as copy:
            while True:
                batch = reader.fetchmany(BATCH_SIZE)
                if not batch:
                    break
                for row in batch:
                    copy.write_row(row)
                    count += 1
        copied[table] = count

    for table, column in target.identity:
        cur.execute(
            sql.SQL(
                'SELECT setval(pg_get_serial_sequence({t}, {c}), '
                'GREATEST(COALESCE(MAX({col}), 0), 1), '
                'COALESCE(MAX({col}), 0) >= 1) FROM {tbl}'
            ).format(
                t=sql.Literal(table),
                c=sql.Literal(column),
                col=sql.Identifier(column),
                tbl=sql.Identifier(table),
            )
        )

    if 'sync_meta' in target.columns and 'library_sync_seq' in _sequences(cur):
        cur.execute("SELECT value FROM sync_meta WHERE key = 'seq'")
        row = cur.fetchone()
        if row is not None:
            value = int(row[0])
            cur.execute(
                "SELECT setval('library_sync_seq', %s, %s)",
                (max(value, 1), value >= 1),
            )
    return copied


def _sequences(cur: psycopg.Cursor[Any]) -> set[str]:
    cur.execute(
        'SELECT sequence_name FROM information_schema.sequences '
        'WHERE sequence_schema = current_schema()'
    )
    return {str(row[0]) for row in cur.fetchall()}


_MODULUS = 1 << 256


def _normalize(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return float(value)
    return value


def _digest_of(value: Any) -> int:
    raw = hashlib.sha256(repr(value).encode('utf-8')).digest()
    return int.from_bytes(raw, 'big')


@dataclass
class _Digest:
    """Row count and the sum of the per-row digests, mod 2**256.

    A sum is order-independent, so the two sides need not agree on a sort
    order (SQLite sorts binary, PostgreSQL by locale).
    """

    count: int = 0
    total: int = 0

    def add(self, row: Iterable[Any]) -> None:
        self.count += 1
        normalised = tuple(_normalize(v) for v in row)
        self.total = (self.total + _digest_of(normalised)) % _MODULUS


def _fold(rows: Iterable[Iterable[Any]]) -> _Digest:
    digest = _Digest()
    for row in rows:
        digest.add(row)
    return digest


def _source_rows(
    conn: sqlite3.Connection, select: str
) -> Iterator[tuple[Any, ...]]:
    cursor = conn.execute(select)
    while True:
        batch = cursor.fetchmany(BATCH_SIZE)
        if not batch:
            return
        yield from batch


def _target_rows(
    raw: psycopg.Connection, select: str
) -> Iterator[tuple[Any, ...]]:
    with raw.transaction(), raw.cursor(name='verify_digest') as cur:
        cur.execute(select)
        while True:
            batch = cur.fetchmany(BATCH_SIZE)
            if not batch:
                return
            yield from batch


def _column_sums(rows: Iterable[Iterable[Any]], width: int) -> list[int]:
    sums = [0] * width
    for row in rows:
        for i, value in enumerate(row):
            sums[i] = (sums[i] + _digest_of(_normalize(value))) % _MODULUS
    return sums


def _first_bad_column(
    names: tuple[str, ...],
    src_rows: Iterable[Iterable[Any]],
    tgt_rows: Iterable[Iterable[Any]],
) -> str | None:
    """Name the first column whose per-column digest sums disagree.

    Only run after a mismatch with equal row counts, to add detail.
    """
    src = _column_sums(src_rows, len(names))
    tgt = _column_sums(tgt_rows, len(names))
    for name, left, right in zip(names, src, tgt):
        if left != right:
            return name
    return None


def _verify(
    db: Database,
    plans: dict[str, _Plan],
    handles: dict[str, sqlite3.Connection],
    order: list[str],
    copied: dict[str, int],
) -> tuple[list[TableReport], list[str]]:
    reports: list[TableReport] = []
    problems: list[str] = []
    with db.connect() as conn:
        raw = conn.raw
        for table in order:
            plan = plans[table]
            source = plan.source
            cols = _select_cols(source.columns)
            src_select = f'SELECT {cols} FROM {_quote(table)}{plan.where}'
            tgt_select = f'SELECT {cols} FROM {_quote(table)}'
            conn_src = handles[source.file_name]
            src = _fold(_source_rows(conn_src, src_select))
            tgt = _fold(_target_rows(raw, tgt_select))

            checksum_ok = src == tgt
            if tgt.count != plan.matched or copied[table] != plan.matched:
                problems.append(
                    f'{table}: source {plan.matched} rows after skipping '
                    f'{plan.skipped} orphans, target {tgt.count}'
                )
            if not checksum_ok:
                detail = ''
                if src.count == tgt.count:
                    column = _first_bad_column(
                        source.columns,
                        _source_rows(conn_src, src_select),
                        _target_rows(raw, tgt_select),
                    )
                    if column is not None:
                        detail = f' in column {column}'
                problems.append(f'{table}: checksum mismatch{detail}')
            reports.append(
                TableReport(
                    name=table,
                    source_file=source.file_name,
                    source_rows=plan.source_rows,
                    skipped=plan.skipped,
                    copied=copied[table],
                    target_rows=tgt.count,
                    checksum_ok=checksum_ok,
                )
            )
    return reports, problems


def _collect_sources(
    found: list[tuple[str, Path]],
    handles: dict[str, sqlite3.Connection],
) -> tuple[list[_Source], dict[str, str]]:
    sources: list[_Source] = []
    seen: dict[str, str] = {}
    for name, _path in found:
        conn = handles[name]
        for table in _sqlite_tables(conn):
            if table in seen:
                raise MigrationError(
                    f'table {table} is in both {seen[table]} and {name}'
                )
            seen[table] = name
            sources.append(_sqlite_source(name, conn, table))
    return sources, seen


def _check_target(sources: list[_Source], target: _Target) -> None:
    for source in sources:
        if source.table not in target.columns:
            raise MigrationError(
                f'SQLite table {source.table} has no PostgreSQL table'
            )
        missing = set(source.columns) - target.columns[source.table]
        if missing:
            raise MigrationError(
                f'{source.table} lacks columns {sorted(missing)}'
            )


def verify(data_dir: Path, db: Database) -> Report:
    """Re-check a migrated install: the SQLite files under *data_dir*
    against the PostgreSQL *db*. Read-only on both sides; the marker is
    neither read nor written. ``TableReport.copied`` reports the expected
    count here, since nothing is copied.
    """

    if db.dialect is not Dialect.POSTGRES:
        raise MigrationError('the migration needs a PostgreSQL target')
    found = _found_files(data_dir)
    if not found:
        raise MigrationError(f'no SQLite database files under {data_dir}')

    with contextlib.ExitStack() as stack:
        handles = {
            name: stack.enter_context(_open_source(path))
            for name, path in found
        }
        sources, seen = _collect_sources(found, handles)
        with db.connect() as conn:
            target = _introspect(conn.raw)
        _check_target(sources, target)
        order = _fk_order(seen, target.fk_edges)
        plans = _plan(sources, handles)
        tables, problems = _verify(
            db,
            plans,
            handles,
            order,
            {table: plans[table].matched for table in order},
        )
    return Report(
        files_found=[name for name, _path in found],
        tables=tables,
        ok=not problems,
        problems=problems,
    )


def migrate(data_dir: Path, db: Database, *, force: bool = False) -> Report:
    """Copy the SQLite files under *data_dir* into the PostgreSQL *db*.

    Raises :class:`MigrationError` when the copy cannot start (already
    migrated, target not empty, no SQLite files) or when the load fails.
    With ``force`` the target's tables are truncated first and the copy
    is redone.
    """

    if db.dialect is not Dialect.POSTGRES:
        raise MigrationError('the migration needs a PostgreSQL target')
    marker = data_dir / MARKER_NAME
    if marker.exists() and not force:
        raise MigrationError(
            f'{marker} exists: this install was already migrated '
            '(force=True repeats the copy)'
        )
    found = _found_files(data_dir)
    if not found:
        raise MigrationError(f'no SQLite database files under {data_dir}')

    run_migrations(db)
    with db.connect() as conn:
        target = _introspect(conn.raw)
        populated = _populated_tables(conn.raw, target.columns)
    if populated and not force:
        raise MigrationError(
            'target already has rows in: '
            + ', '.join(populated)
            + ' (force=True replaces them)'
        )

    with contextlib.ExitStack() as stack:
        handles = {
            name: stack.enter_context(_open_source(path))
            for name, path in found
        }
        sources, seen = _collect_sources(found, handles)
        _check_target(sources, target)

        order = _fk_order(seen, target.fk_edges)
        plans = _plan(sources, handles)
        try:
            with db.transaction() as conn:
                copied = _load(
                    conn.raw,
                    plans,
                    handles,
                    order,
                    target,
                    sorted(target.columns) if populated else [],
                )
        except psycopg.Error as exc:
            raise MigrationError(
                f'load failed and was rolled back: {exc}'
            ) from exc

        tables, problems = _verify(db, plans, handles, order, copied)

    report = Report(
        files_found=[name for name, _path in found],
        tables=tables,
        ok=not problems,
        problems=problems,
    )
    if report.ok:
        marker.write_text(
            datetime.now(timezone.utc).isoformat() + '\n', encoding='utf-8'
        )
    return report


def format_report(report: Report) -> str:
    lines = [
        'Files: ' + (', '.join(report.files_found) or 'none'),
        f'{"table":<28}{"source":>10}{"skipped":>9}{"target":>10}  checksum',
    ]
    for t in report.tables:
        check = 'ok' if t.checksum_ok else 'MISMATCH'
        lines.append(
            f'{t.name:<28}{t.source_rows:>10}{t.skipped:>9}'
            f'{t.target_rows:>10}  {check}'
        )
    if report.ok:
        lines.append('Result: OK')
    else:
        lines.append('Result: FAILED')
        lines.extend(f'  - {problem}' for problem in report.problems)
    return '\n'.join(lines)
