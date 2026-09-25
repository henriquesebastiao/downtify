"""Tests for downtify/file_naming.py: the one rule for turning a name into a
file name, and for deciding two names are the same on disk."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from downtify import file_naming
from downtify.downloader import _sanitize
from downtify.file_naming import file_name_key, sanitize_file_name


@pytest.mark.parametrize(
    ('name', 'expected'),
    [
        ('AC/DC', 'ACDC'),
        ('*NSYNC', 'NSYNC'),
        ('M.I.A.', 'M.I.A'),
        ('T.I.', 'T.I'),
        ('?uestlove', 'uestlove'),
        ("Guns N' Roses", "Guns N' Roses"),
        ('  padded  ', 'padded'),
        ('.hidden', 'hidden'),
        ('title\x00\x1f', 'title'),
        ('Sólfar', 'Sólfar'),
    ],
)
def test_sanitize_file_name_drops_what_a_file_name_cant_hold(name, expected):
    assert sanitize_file_name(name) == expected


@pytest.mark.parametrize('name', ['', None, '???', '...', '  '])
def test_sanitize_file_name_falls_back_to_unknown(name):
    assert sanitize_file_name(name) == 'unknown'  # type: ignore[arg-type]


@pytest.mark.parametrize(
    'name',
    ['AC/DC', 'Some: Name', 'a|b', '*NSYNC', 'M.I.A.', '', None, ' x ', '???'],
)
def test_downloaders_sanitize_is_the_same_rule(name):
    assert _sanitize(name) == sanitize_file_name(name)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ('a', 'b'),
    [
        ('AC/DC', 'ACDC'),
        ('AC/DC', 'ac/dc'),
        ('*NSYNC', 'NSYNC'),
        ('M.I.A.', 'M.I.A'),
        ('Paramore', ' paramore '),
        ('Simple   Plan', 'simple plan'),
        ('Sunn O)))', 'SUNN O)))'),
    ],
)
def test_names_that_are_the_same_on_disk_share_a_key(a, b):
    assert file_name_key(a) == file_name_key(b)


@pytest.mark.parametrize(
    ('a', 'b'),
    [
        ('Paramore', 'Paramore Tribute'),
        ('AC/DC', 'ACD'),
        ('Linkin Park', 'Linkin Park Band'),
        ('Blink', 'Blink-182'),
        ('MIA', 'M.I.A.'),
    ],
)
def test_different_names_keep_different_keys(a, b):
    """Only what the disk itself drops is forgiven: a different name - or
    a dot inside it, which the disk keeps - is still a different name."""

    assert file_name_key(a) != file_name_key(b)


def test_the_key_of_an_unusable_name_is_empty_not_unknown():
    for name in ('', None, '???', '///', '  ', '...'):
        assert not file_name_key(name)  # type: ignore[arg-type]
    assert file_name_key('unknown') == 'unknown'
    assert file_name_key('???') != file_name_key('unknown')


def test_the_key_ignores_case_with_casefold():
    assert file_name_key('STRASSE') == file_name_key('straße')


def test_the_module_is_a_leaf():
    """It imports only the standard library: if it imported Downtify code,
    the downloader and the streaming clients could not share it without an
    import cycle."""

    tree = ast.parse(Path(file_naming.__file__).read_text(encoding='utf-8'))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            imported.add(node.module)
    assert imported == {'__future__', 're'}
