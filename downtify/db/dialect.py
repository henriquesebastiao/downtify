"""Small helpers that hide SQLite and PostgreSQL differences.

Each helper takes a ``Connection`` (which carries its ``dialect``) or a
``Dialect`` directly. SQL placeholders are ``?`` on both backends, as
elsewhere in ``downtify.db``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from downtify.db.config import Dialect

if TYPE_CHECKING:
    from downtify.db.core import Connection

_IDENT_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
_TRAILING_RE = re.compile(r'[\s;]+$')


def _check_identifier(name: str) -> str:
    """Return ``name`` if it is a plain SQL identifier, else raise."""
    if not _IDENT_RE.fullmatch(name):
        raise ValueError(f'invalid SQL identifier: {name!r}')
    return name


def _check_column(col: str) -> str:
    """Return ``col`` if it is ``name`` or ``table.name``, else raise."""
    parts = col.split('.')
    if len(parts) > 2:
        raise ValueError(f'invalid SQL column reference: {col!r}')
    for part in parts:
        _check_identifier(part)
    return col


def insert_returning_id(
    conn: Connection,
    sql: str,
    params: tuple | list = (),
    id_column: str = 'id',
) -> int:
    """Run an INSERT and return the new row's integer id.

    ``sql`` must be a plain INSERT without a RETURNING clause.
    """
    _check_identifier(id_column)
    if conn.dialect is Dialect.SQLITE:
        cursor = conn.execute(sql, params)
        new_id = cursor.lastrowid
        if new_id is None:
            raise RuntimeError('INSERT did not report a rowid')
        return int(new_id)

    statement = f'{_TRAILING_RE.sub("", sql)} RETURNING {id_column}'
    row = conn.execute(statement, params).fetchone()
    return int(row[0])


def table_exists(conn: Connection, name: str) -> bool:
    """Return True if a table called ``name`` exists in the current schema."""
    if conn.dialect is Dialect.SQLITE:
        row = conn.execute(
            "select 1 from sqlite_master where type='table' and name=?",
            (name,),
        ).fetchone()
    else:
        row = conn.execute(
            'select 1 from information_schema.tables '
            'where table_schema = current_schema() and table_name = ?',
            (name,),
        ).fetchone()
    return row is not None


def column_names(conn: Connection, table: str) -> list[str]:
    """Return the column names of ``table`` in declaration order."""
    _check_identifier(table)
    if conn.dialect is Dialect.SQLITE:
        # PRAGMA cannot take bound parameters; the name is validated above.
        rows = conn.execute(f'PRAGMA table_info({table})').fetchall()
        return [row[1] for row in rows]
    rows = conn.execute(
        'select column_name from information_schema.columns '
        'where table_schema = current_schema() and table_name = ? '
        'order by ordinal_position',
        (table,),
    ).fetchall()
    return [row[0] for row in rows]


def insertion_order_col(dialect: Dialect) -> str:
    """Column that orders rows by insertion on each backend."""
    if dialect is Dialect.SQLITE:
        return 'rowid'
    return 'id'


def ci_eq(col: str) -> str:
    """Case-insensitive equality: ``lower(col) = lower(?)``."""
    _check_column(col)
    return f'lower({col}) = lower(?)'


def days_between_sql(a: str, b: str, dialect: Dialect) -> str:
    """SQL yielding the fractional days from timestamp ``b`` to ``a``.

    ``a`` and ``b`` are SQL expressions producing ISO-8601 text timestamps.
    Both are trusted SQL fragments, not user input.
    """
    if dialect is Dialect.SQLITE:
        return f'(julianday({a}) - julianday({b}))'
    return (
        f'((EXTRACT(EPOCH FROM (({a})::timestamptz)) '
        f'- EXTRACT(EPOCH FROM (({b})::timestamptz))) / 86400.0)'
    )
