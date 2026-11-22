"""Spotify covers are always taken at the largest size Spotify publishes.

Spotify serves an album cover at 640, 300 and 64 px under one image id,
the size picked by a fixed prefix. Its embeds now link the covers on
``image-cdn-<region>.spotifycdn.com`` as well as the older ``i.scdn.co``,
and sometimes list only the 300 and 64 px variants - a download then
carried a 300 px cover.
"""

from __future__ import annotations

from typing import Any

import pytest

from downtify import cover_sources, downloader, spotify

IMAGE_ID = '322b8ded39dc108536090089'
HOSTS = (
    'https://i.scdn.co/image/',
    'https://image-cdn-fa.spotifycdn.com/image/',
    'https://image-cdn-ak.spotifycdn.com/image/',
)
# conftest stubs _download_cover out for every test; these test the real one.
_download_cover = downloader._download_cover


@pytest.mark.parametrize('host', HOSTS)
@pytest.mark.parametrize('prefix', ['ab67616d00001e02', 'ab67616d00004851'])
def test_small_cover_on_any_spotify_host_is_pointed_at_640(
    host: str, prefix: str
) -> None:
    small = f'{host}{prefix}{IMAGE_ID}'
    largest = f'{host}ab67616d0000b273{IMAGE_ID}'
    assert spotify.largest_cover_url(small) == largest
    assert cover_sources.spotify_upgrade_url(small) == largest


def test_other_images_are_left_alone() -> None:
    for url in (
        f'https://i.scdn.co/image/ab67616d0000b273{IMAGE_ID}',
        # An artist photo or a playlist mosaic has its own prefixes.
        'https://image-cdn-fa.spotifycdn.com/image/ab6761610000e5eb1234',
        'https://example.com/image/ab67616d00001e02abc',
        'https://yt3.googleusercontent.com/x=w1000-h1000-l90-rj',
        '',
    ):
        assert spotify.largest_cover_url(url) == url


def test_embed_listing_only_small_covers_still_gives_640() -> None:
    entity = {
        'visualIdentity': {
            'image': [
                {
                    'url': f'{HOSTS[1]}ab67616d00001e02{IMAGE_ID}',
                    'maxWidth': 300,
                },
                {
                    'url': f'{HOSTS[1]}ab67616d00004851{IMAGE_ID}',
                    'maxWidth': 64,
                },
            ]
        }
    }
    assert spotify._cover_url(entity) == (
        f'{HOSTS[1]}ab67616d0000b273{IMAGE_ID}'
    )


def test_download_asks_for_the_640_cover_first(monkeypatch) -> None:
    asked: list[str] = []

    def fetch(url: str) -> Any:
        asked.append(url)
        return b'big'

    monkeypatch.setattr(downloader, '_fetch_cover', fetch)
    data = _download_cover(f'{HOSTS[1]}ab67616d00001e02{IMAGE_ID}')
    assert data == b'big'
    assert asked == [f'{HOSTS[1]}ab67616d0000b273{IMAGE_ID}']


def test_download_falls_back_to_the_given_cover(monkeypatch) -> None:
    small = f'{HOSTS[0]}ab67616d00001e02{IMAGE_ID}'
    asked: list[str] = []

    def fetch(url: str) -> Any:
        asked.append(url)
        return b'small' if url == small else None

    monkeypatch.setattr(downloader, '_fetch_cover', fetch)
    assert _download_cover(small) == b'small'
    assert asked[-1] == small
    assert len(asked) == 2


def test_other_covers_are_fetched_once_as_given(monkeypatch) -> None:
    asked: list[str] = []
    monkeypatch.setattr(
        downloader, '_fetch_cover', lambda url: asked.append(url) or b'x'
    )
    url = 'https://yt3.googleusercontent.com/x=w1000-h1000-l90-rj'
    _download_cover(url)
    assert asked == [url]
