"""Unit tests for the _sanitize() filesystem-name helper."""

from __future__ import annotations

import pytest

from downtify.downloader import _sanitize


@pytest.mark.parametrize('char', list(r'\/:*?"<>|'))
def test_sanitize_removes_filesystem_unsafe_chars(char):
    assert char not in _sanitize(f'name{char}test')


def test_sanitize_normal_string_unchanged():
    assert _sanitize('Arctic Monkeys') == 'Arctic Monkeys'


def test_sanitize_empty_string_returns_unknown():
    assert _sanitize('') == 'unknown'


def test_sanitize_none_treated_as_empty():
    assert _sanitize(None) == 'unknown'  # type: ignore[arg-type]


def test_sanitize_strips_leading_trailing_whitespace():
    assert _sanitize('  hello  ') == 'hello'


def test_sanitize_strips_leading_dot():
    assert _sanitize('.hidden') == 'hidden'


def test_sanitize_strips_trailing_dot():
    assert _sanitize('file.') == 'file'


def test_sanitize_all_unsafe_returns_unknown():
    assert _sanitize('???') == 'unknown'


def test_sanitize_control_chars_removed():
    assert _sanitize('title\x00\x1f') == 'title'


def test_sanitize_unicode_letters_kept():
    assert _sanitize('Sigur Rós') == 'Sigur Rós'


def test_sanitize_numbers_kept():
    assert _sanitize('2Pac') == '2Pac'


def test_sanitize_hyphen_kept():
    assert _sanitize('Post-Malone') == 'Post-Malone'
