from __future__ import annotations

import pytest

from downtify.db.sql import to_pyformat


def test_plain_placeholder() -> None:
    assert to_pyformat('SELECT * FROM t WHERE id = ?') == (
        'SELECT * FROM t WHERE id = %s'
    )


def test_many_placeholders() -> None:
    sql = 'INSERT INTO t (a, b, c, d) VALUES (?, ?, ?, ?)'
    assert to_pyformat(sql) == (
        'INSERT INTO t (a, b, c, d) VALUES (%s, %s, %s, %s)'
    )


def test_question_mark_in_single_quotes_untouched() -> None:
    assert to_pyformat("SELECT 'a?b' FROM t WHERE x = ?") == (
        "SELECT 'a?b' FROM t WHERE x = %s"
    )


def test_escaped_single_quote() -> None:
    assert to_pyformat("SELECT 'it''s ?' FROM t") == (
        "SELECT 'it''s ?' FROM t"
    )


def test_double_quoted_identifier_untouched() -> None:
    assert to_pyformat('SELECT "quoted ?" FROM t WHERE a = ?') == (
        'SELECT "quoted ?" FROM t WHERE a = %s'
    )


def test_escaped_double_quote_in_identifier() -> None:
    assert to_pyformat('SELECT "a""?" FROM t') == 'SELECT "a""?" FROM t'


def test_line_comment_untouched() -> None:
    sql = 'SELECT 1 -- comment ?\nFROM t WHERE a = ?'
    assert to_pyformat(sql) == 'SELECT 1 -- comment ?\nFROM t WHERE a = %s'


def test_block_comment_untouched() -> None:
    assert to_pyformat('SELECT /* ? */ ? FROM t') == (
        'SELECT /* ? */ %s FROM t'
    )


def test_percent_in_literal_doubled() -> None:
    assert to_pyformat("SELECT * FROM t WHERE n LIKE '%a'") == (
        "SELECT * FROM t WHERE n LIKE '%%a'"
    )


def test_like_placeholder_with_percent_elsewhere() -> None:
    sql = 'SELECT 100% FROM t WHERE name LIKE ?'
    assert to_pyformat(sql) == 'SELECT 100%% FROM t WHERE name LIKE %s'


def test_in_list_placeholders() -> None:
    assert to_pyformat('x IN (?,?,?)') == 'x IN (%s,%s,%s)'


def test_no_placeholders_only_percent_doubled() -> None:
    assert to_pyformat('SELECT a, b FROM t') == 'SELECT a, b FROM t'
    assert to_pyformat('SELECT a % b FROM t') == 'SELECT a %% b FROM t'


def test_empty_string() -> None:
    assert not to_pyformat('')


@pytest.mark.parametrize(
    ('sql', 'expected'),
    [
        ("SELECT 'unterminated ? %", "SELECT 'unterminated ? %%"),
        ('SELECT "unterminated ? %', 'SELECT "unterminated ? %%'),
        ('SELECT /* unterminated ? %', 'SELECT /* unterminated ? %%'),
        ('SELECT 1 -- ? %', 'SELECT 1 -- ? %%'),
    ],
)
def test_unterminated_does_not_raise(sql: str, expected: str) -> None:
    assert to_pyformat(sql) == expected


def test_unterminated_quote_no_placeholder_swap() -> None:
    assert to_pyformat("SELECT 'a ? b") == "SELECT 'a ? b"


def test_caching_returns_equal_results() -> None:
    sql = 'SELECT * FROM t WHERE a = ? AND b LIKE ?'
    first = to_pyformat(sql)
    second = to_pyformat(sql)
    assert first == second == 'SELECT * FROM t WHERE a = %s AND b LIKE %s'
    assert to_pyformat.cache_info().hits >= 1
