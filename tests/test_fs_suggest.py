"""Directory suggestions for Settings path fields."""

from __future__ import annotations

from downtify.fs_suggest import suggest_directories


def test_suggest_matches_prefix(tmp_path):
    (tmp_path / 'music').mkdir()
    (tmp_path / 'misc').mkdir()
    (tmp_path / 'music' / 'collection').mkdir()
    hits = suggest_directories(str(tmp_path / 'mu'))
    assert str(tmp_path / 'music') in hits
    assert str(tmp_path / 'misc') not in hits


def test_suggest_trailing_slash_lists_children(tmp_path):
    nested = tmp_path / 'music' / 'collection'
    nested.mkdir(parents=True)
    (tmp_path / 'music' / 'other').mkdir()
    hits = suggest_directories(str(tmp_path / 'music') + '/')
    assert str(nested) in hits
    assert str(tmp_path / 'music' / 'other') in hits


def test_suggest_does_not_list_files(tmp_path):
    (tmp_path / 'music').mkdir()
    (tmp_path / 'readme.txt').write_text('x')
    hits = suggest_directories(str(tmp_path / 'r'))
    assert str(tmp_path / 'readme.txt') not in hits
