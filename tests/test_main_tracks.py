"""Tests for ``main._extract_track_tags``, which powers the player's
"play only this artist" / "play only this album" filters (``GET
/tracks``).

The ``/tracks`` route itself lives inside ``main.build_app()`` alongside
``/list``, ``/playlists``, ``/cover`` and ``/delete`` — none of which
have route-level tests today (there's no TestClient/build_app fixture
in this suite yet). ``_extract_track_tags`` is the actual new logic and
is a plain module-level function, so it's tested directly here instead.
"""

from __future__ import annotations

from pathlib import Path

import main


class _FakeEasyTags(dict):
    """Mimics a mutagen "easy" wrapper: dict-like, list-valued fields."""


def test_extract_track_tags_reads_artist_and_album(monkeypatch):
    monkeypatch.setattr(
        main,
        'MutagenFile',
        lambda *a, **kw: _FakeEasyTags(
            artist=['Sleeping At Last'], album=['Atlas: Enneagram']
        ),
    )
    artist, album = main._extract_track_tags(Path('song.mp3'))
    assert artist == 'Sleeping At Last'
    assert album == 'Atlas: Enneagram'


def test_extract_track_tags_missing_fields_are_empty(monkeypatch):
    monkeypatch.setattr(main, 'MutagenFile', lambda *a, **kw: _FakeEasyTags())
    artist, album = main._extract_track_tags(Path('song.mp3'))
    assert not artist
    assert not album


def test_extract_track_tags_no_tags_object(monkeypatch):
    # e.g. a file mutagen can't identify at all.
    monkeypatch.setattr(main, 'MutagenFile', lambda *a, **kw: None)
    artist, album = main._extract_track_tags(Path('song.mp3'))
    assert not artist
    assert not album


def test_extract_track_tags_unreadable_file_does_not_raise(monkeypatch):
    def _raise(*a, **kw):
        raise OSError('corrupt file')

    monkeypatch.setattr(main, 'MutagenFile', _raise)
    artist, album = main._extract_track_tags(Path('song.mp3'))
    assert not artist
    assert not album
