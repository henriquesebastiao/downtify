"""Translate SQLite-style SQL into psycopg3 pyformat SQL."""

from __future__ import annotations

import functools


def _double(text: str) -> str:
    """Escape literal percent signs for psycopg's pyformat parser."""
    return text.replace('%', '%%')


def _copy_quoted(sql: str, start: int, quote: str, out: list[str]) -> int:
    """Copy a quoted run beginning at ``start``; return the index after it.

    A doubled quote character inside the run is an escaped quote. An
    unterminated run is copied to the end of the string.
    """
    out.append(quote)
    i = start + 1
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch == quote:
            if i + 1 < n and sql[i + 1] == quote:
                out.append(quote * 2)
                i += 2
                continue
            out.append(quote)
            return i + 1
        out.append(_double(ch))
        i += 1
    return i


def _copy_line_comment(sql: str, start: int, out: list[str]) -> int:
    """Copy a ``--`` comment up to (not including) the newline."""
    end = sql.find('\n', start)
    if end == -1:
        end = len(sql)
    out.append(_double(sql[start:end]))
    return end


def _copy_block_comment(sql: str, start: int, out: list[str]) -> int:
    """Copy a ``/* ... */`` comment; an unterminated one runs to the end."""
    end = sql.find('*/', start + 2)
    end = len(sql) if end == -1 else end + 2
    out.append(_double(sql[start:end]))
    return end


@functools.lru_cache(maxsize=2048)
def to_pyformat(sql: str) -> str:
    """Convert SQLite qmark SQL to psycopg3 pyformat SQL.

    Every literal ``%`` becomes ``%%`` (psycopg parses placeholders
    everywhere, including inside literals and comments). Outside string
    literals, quoted identifiers and comments, each ``?`` becomes ``%s``.
    Everything else is copied unchanged. An unterminated quote or comment
    is copied through to the end of the string without raising.

    Apply this only when parameters are passed (even an empty tuple). A
    no-parameter script (for example ``executescript``) must NOT be
    translated: psycopg does not unescape ``%%`` when no params are given.
    """
    out: list[str] = []
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch in {"'", '"'}:
            i = _copy_quoted(sql, i, ch, out)
        elif ch == '-' and sql.startswith('--', i):
            i = _copy_line_comment(sql, i, out)
        elif ch == '/' and sql.startswith('/*', i):
            i = _copy_block_comment(sql, i, out)
        elif ch == '?':
            out.append('%s')
            i += 1
        else:
            out.append(_double(ch))
            i += 1
    return ''.join(out)
