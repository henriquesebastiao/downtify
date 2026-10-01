"""Tests for downtify.deezer._cover_from_images: Deezer only offers four
fixed image sizes (56/250/500/1000px, unlike a YouTube Music thumbnail,
whose URL can be resized freely - see providers._resize_thumbnail), so
picking a "cover size" here means picking the smallest of those four that
still meets the same ``cover_resolution`` setting YouTube Music covers
already use, not resizing anything."""

from __future__ import annotations

import pytest

from downtify import deezer

_ALL_SIZES = {
    'cover_small': 'https://example.test/56.jpg',
    'cover_medium': 'https://example.test/250.jpg',
    'cover_big': 'https://example.test/500.jpg',
    'cover_xl': 'https://example.test/1000.jpg',
}


@pytest.mark.parametrize(
    ('wanted', 'expected'),
    [
        (56, 'https://example.test/56.jpg'),
        (100, 'https://example.test/250.jpg'),
        (250, 'https://example.test/250.jpg'),
        (300, 'https://example.test/500.jpg'),
        (500, 'https://example.test/500.jpg'),
        (600, 'https://example.test/1000.jpg'),
        (1000, 'https://example.test/1000.jpg'),
        # Bigger than anything Deezer offers: falls back to the largest.
        (1200, 'https://example.test/1000.jpg'),
    ],
)
def test_cover_from_images_picks_smallest_that_meets_the_target(
    monkeypatch, wanted, expected
):
    monkeypatch.setattr(deezer.providers, 'cover_resolution', lambda: wanted)
    assert deezer._cover_from_images(_ALL_SIZES) == expected


def test_cover_from_images_skips_missing_sizes(monkeypatch):
    # No 'big': asking for 300 (which would normally land on 'big', 500px)
    # should skip straight to 'xl' rather than giving up.
    sizes = {
        'cover_small': 'https://example.test/56.jpg',
        'cover_medium': 'https://example.test/250.jpg',
        'cover_xl': 'https://example.test/1000.jpg',
    }
    monkeypatch.setattr(deezer.providers, 'cover_resolution', lambda: 300)
    assert deezer._cover_from_images(sizes) == 'https://example.test/1000.jpg'


def test_cover_from_images_uses_picture_prefix_for_artists(monkeypatch):
    monkeypatch.setattr(deezer.providers, 'cover_resolution', lambda: 300)
    row = {
        'picture_medium': 'https://example.test/artist-250.jpg',
        'picture_big': 'https://example.test/artist-500.jpg',
    }
    assert (
        deezer._cover_from_images(row, prefix='picture')
        == 'https://example.test/artist-500.jpg'
    )


def test_cover_from_images_empty_when_nothing_present(monkeypatch):
    monkeypatch.setattr(deezer.providers, 'cover_resolution', lambda: 300)
    assert not deezer._cover_from_images({})


# ── Chart rows respect the same setting ─────────────────────────────────


def test_chart_track_song_respects_cover_resolution(monkeypatch):
    monkeypatch.setattr(deezer.providers, 'cover_resolution', lambda: 300)
    row = {
        'id': 1,
        'title': 'Track',
        'artist': {'name': 'Someone'},
        'album': dict(_ALL_SIZES, title='Album'),
    }
    song = deezer._chart_track_song(row)
    assert song['cover_url'] == 'https://example.test/500.jpg'


def test_chart_album_release_respects_cover_resolution(monkeypatch):
    monkeypatch.setattr(deezer.providers, 'cover_resolution', lambda: 1000)
    row = dict(_ALL_SIZES, id=1, title='Album', artist={'name': 'Someone'})
    release = deezer._chart_album_release(row)
    assert release['cover_url'] == 'https://example.test/1000.jpg'


def test_chart_artist_release_respects_cover_resolution(monkeypatch):
    monkeypatch.setattr(deezer.providers, 'cover_resolution', lambda: 300)
    row = {
        'id': 1,
        'name': 'Someone',
        'picture_medium': 'https://example.test/artist-250.jpg',
        'picture_big': 'https://example.test/artist-500.jpg',
        'picture_xl': 'https://example.test/artist-1000.jpg',
    }
    release = deezer._chart_artist_release(row)
    assert release['cover_url'] == 'https://example.test/artist-500.jpg'


def test_chart_playlist_release_respects_cover_resolution(monkeypatch):
    monkeypatch.setattr(deezer.providers, 'cover_resolution', lambda: 600)
    row = {
        'id': 1,
        'title': 'Playlist',
        'picture_big': 'https://example.test/pl-500.jpg',
        'picture_xl': 'https://example.test/pl-1000.jpg',
    }
    release = deezer._chart_playlist_release(row)
    assert release['cover_url'] == 'https://example.test/pl-1000.jpg'
