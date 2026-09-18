"""Picking the best cover art available for a track already on disk."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from downtify import cover_sources, itunes


def _png(size: int) -> bytes:
    return (
        b'\x89PNG\r\n\x1a\n'
        + struct.pack('>I', 13)
        + b'IHDR'
        + struct.pack('>II', size, size)
        + b'\x08\x06\x00\x00\x00'
    )


def _candidate(source: str, width: int) -> cover_sources.CoverCandidate:
    return cover_sources.CoverCandidate(
        source=source, data=_png(width), width=width
    )


def _stub_sources(
    monkeypatch: Any, sizes: dict[str, int]
) -> list[tuple[str, ...]]:
    """Replace the network with fixed sizes; record what was asked for."""

    asked: list[tuple[str, ...]] = []

    def _collect(
        song: dict[str, Any], *, sources: tuple[str, ...]
    ) -> list[cover_sources.CoverCandidate]:
        asked.append(tuple(sources))
        return [
            _candidate(name, sizes[name]) for name in sources if name in sizes
        ]

    monkeypatch.setattr(cover_sources, 'collect_candidates', _collect)
    return asked


SONG = {'name': 'Track', 'artists': ['Artist'], 'album_name': 'Album'}


# ── URL rewriting ──────────────────────────────────────────────────
def test_spotify_small_image_url_is_pointed_at_the_largest_size() -> None:
    small = 'https://i.scdn.co/image/ab67616d00001e02abc123'
    assert cover_sources.spotify_upgrade_url(small) == (
        'https://i.scdn.co/image/ab67616d0000b273abc123'
    )


def test_spotify_thumbnail_url_is_upgraded_too() -> None:
    tiny = 'https://i.scdn.co/image/ab67616d00004851abc123'
    assert 'ab67616d0000b273' in cover_sources.spotify_upgrade_url(tiny)


def test_spotify_url_that_is_already_largest_is_left_alone() -> None:
    big = 'https://i.scdn.co/image/ab67616d0000b273abc123'
    assert cover_sources.spotify_upgrade_url(big) == big


def test_non_spotify_urls_are_not_rewritten() -> None:
    other = 'https://example.com/ab67616d00001e02.jpg'
    assert cover_sources.spotify_upgrade_url(other) == other
    assert not cover_sources.spotify_upgrade_url('')


def test_itunes_artwork_url_is_resized() -> None:
    url = 'https://is1-ssl.mzstatic.com/image/thumb/x/y/100x100bb.jpg'
    assert itunes.artwork_url_at(url, 1200).endswith('/1200x1200bb.jpg')


def test_itunes_artwork_url_keeps_png_extension() -> None:
    url = 'https://is1-ssl.mzstatic.com/image/thumb/x/y/60x60bb.png'
    assert itunes.artwork_url_at(url, 1400).endswith('/1400x1400bb.png')


def test_itunes_artwork_url_without_a_size_suffix_is_unchanged() -> None:
    url = 'https://example.com/cover.jpg'
    assert itunes.artwork_url_at(url, 1200) == url


# ── Reading what the file already has ──────────────────────────────
def test_current_cover_measures_a_folder_image(tmp_path: Path) -> None:
    track = tmp_path / 'track.mp3'
    track.write_bytes(b'\x00' * 32)
    (tmp_path / 'cover.jpg').write_bytes(_png(300))

    current = cover_sources.current_cover(track)
    assert current is not None
    assert current.width == 300
    assert current.source == cover_sources.SOURCE_FILE


def test_current_cover_is_none_without_artwork(tmp_path: Path) -> None:
    track = tmp_path / 'bare.mp3'
    track.write_bytes(b'\x00' * 32)
    assert cover_sources.current_cover(track) is None


# ── Choosing between sources ───────────────────────────────────────
def test_highest_wins_across_every_source(monkeypatch: Any) -> None:
    asked = _stub_sources(
        monkeypatch, {'spotify': 640, 'itunes': 1400, 'youtube-music': 1200}
    )

    best = cover_sources.best_cover(
        SONG,
        current=_candidate('file', 300),
        preference=cover_sources.PREFERENCE_HIGHEST,
    )

    assert best is not None
    assert (best.source, best.width) == ('itunes', 1400)
    # One pass over all three, not one call per source.
    assert asked == [('spotify', 'itunes', 'youtube-music')]


def test_a_named_preference_wins_even_when_it_is_smaller(
    monkeypatch: Any,
) -> None:
    _stub_sources(monkeypatch, {'spotify': 640, 'itunes': 1400})

    best = cover_sources.best_cover(
        SONG,
        current=_candidate('file', 300),
        preference=cover_sources.SOURCE_SPOTIFY,
    )

    assert best is not None
    assert (best.source, best.width) == ('spotify', 640)


def test_a_named_preference_falls_back_when_it_has_nothing(
    monkeypatch: Any,
) -> None:
    asked = _stub_sources(monkeypatch, {'itunes': 1400})

    best = cover_sources.best_cover(
        SONG, current=None, preference=cover_sources.SOURCE_SPOTIFY
    )

    assert best is not None
    assert best.source == 'itunes'
    # Asked for the preferred source first, then the next one.
    assert asked == [('spotify',), ('itunes',)]


def test_nothing_is_returned_when_the_file_already_has_the_best(
    monkeypatch: Any,
) -> None:
    _stub_sources(monkeypatch, {'spotify': 640, 'itunes': 640})

    assert (
        cover_sources.best_cover(SONG, current=_candidate('file', 1200))
        is None
    )


def test_an_equal_size_is_not_worth_rewriting_the_file_for(
    monkeypatch: Any,
) -> None:
    _stub_sources(monkeypatch, {'itunes': 600})

    assert (
        cover_sources.best_cover(SONG, current=_candidate('file', 600)) is None
    )


def test_no_source_has_anything(monkeypatch: Any) -> None:
    _stub_sources(monkeypatch, {})
    assert cover_sources.best_cover(SONG, current=None) is None


def test_a_file_without_artwork_takes_whatever_is_found(
    monkeypatch: Any,
) -> None:
    _stub_sources(monkeypatch, {'youtube-music': 544})

    best = cover_sources.best_cover(SONG, current=None)
    assert best is not None
    assert best.width == 544
