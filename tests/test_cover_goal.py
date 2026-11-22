"""Every download aims for the "Cover size" setting (1200px by default).

A track whose own cover is smaller - every Spotify track, whose largest
is 640px - gets the largest cover Spotify, iTunes, YouTube Music and
Deezer have for the same song, all asked at once and each at the goal
size. A cover found for another song or another artist is never taken.
"""

from __future__ import annotations

import struct
import time
from typing import Any

import httpx
import pytest

from downtify import cover_sources, deezer, downloader, itunes, providers

# conftest keeps the cover sources offline; these tests stub them their way.
_SOURCE_URL = cover_sources._source_url

SONG = {
    'name': 'Last Thing You Need (from GTAVI: The Album)',
    'artists': ['Morgan Wallen', 'Grand Theft Auto VI'],
    'album_name': 'Last Thing You Need (from GTAVI: The Album)',
}


def _png(size: int) -> bytes:
    return (
        b'\x89PNG\r\n\x1a\n'
        + struct.pack('>I', 13)
        + b'IHDR'
        + struct.pack('>II', size, size)
        + b'\x08\x06\x00\x00\x00'
    )


# ── the goal ───────────────────────────────────────────────────────
def test_default_cover_size_is_1200() -> None:
    assert providers.DEFAULT_COVER_RESOLUTION == 1200


def test_goal_is_the_cover_size_or_the_minimum_when_larger(
    monkeypatch,
) -> None:
    monkeypatch.setattr(providers, '_cover_resolution', 1200)
    monkeypatch.setattr(providers, '_cover_minimum', 0)
    assert downloader.cover_goal(0) == 1200
    assert downloader.cover_goal(600) == 1200
    assert downloader.cover_goal(1500) == 1500


def test_a_spotify_cover_is_swapped_with_no_minimum_set(monkeypatch) -> None:
    # Before, "Minimum cover size: off" kept Spotify's 640px (or 300px).
    monkeypatch.setattr(providers, '_cover_resolution', 1200)
    monkeypatch.setattr(providers, '_cover_minimum', 0)
    monkeypatch.setattr(downloader, '_download_cover', lambda url: _png(640))
    monkeypatch.setattr(
        cover_sources,
        'best_cover',
        lambda song, current: cover_sources.CoverCandidate(
            source='itunes', data=_png(1200), width=1200
        ),
    )
    data = downloader._download_cover_meeting(SONG, downloader.cover_goal(0))
    assert data == _png(1200)


# ── same song only ─────────────────────────────────────────────────
@pytest.mark.parametrize(
    ('artists', 'title', 'same'),
    [
        (
            ['Morgan Wallen'],
            'Last Thing You Need (from GTAVI: The Album)',
            True,
        ),
        (['Morgan Wallen', 'Other'], 'Last Thing You Need', True),
        (['Morgan Wallen'], 'Last Thing You Need - Live', True),
        (['Morgan Wallen'], 'Been By Now', False),
        (['Somebody Else'], 'Last Thing You Need', False),
        ([], 'Last Thing You Need', False),
    ],
)
def test_same_song(artists: list[str], title: str, same: bool) -> None:
    assert cover_sources.same_song(SONG, artists, title) is same


def test_youtube_music_cover_is_the_matching_result_at_the_goal(
    monkeypatch,
) -> None:
    rows = [
        {
            'name': 'Been By Now',
            'artists': ['Morgan Wallen'],
            'cover_url': 'https://yt3.googleusercontent.com/wrong=w600-h600',
        },
        {
            'name': 'Last Thing You Need (from GTAVI: The Album)',
            'artists': ['Morgan Wallen', 'Grand Theft Auto VI'],
            'cover_url': 'https://yt3.googleusercontent.com/right=w600-h600',
        },
    ]
    monkeypatch.setattr(providers, 'search_songs', lambda q, limit: rows)
    url = cover_sources._youtube_cover_url(SONG, 1400)
    assert url == 'https://yt3.googleusercontent.com/right=w1400-h1400-l90-rj'


def test_youtube_music_cover_of_another_song_is_not_taken(monkeypatch) -> None:
    rows = [
        {
            'name': 'disco tits',
            'artists': ['Tove Lo'],
            'cover_url': 'https://yt3.googleusercontent.com/x=w600-h600',
        }
    ]
    monkeypatch.setattr(providers, 'search_songs', lambda q, limit: rows)
    assert not cover_sources._youtube_cover_url(SONG, 1200)


class _Resp:
    def __init__(self, payload: Any, status: int = 200) -> None:
        self.payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                str(self.status_code), request=None, response=self
            )

    def json(self) -> Any:
        return self.payload


def _deezer_row(title: str, artist: str) -> dict[str, Any]:
    base = 'https://cdn-images.dzcdn.net/images/cover/abc/'
    return {
        'title': title,
        'title_short': title,
        'artist': {'name': artist},
        'album': {
            'cover_medium': f'{base}250x250.jpg',
            'cover_big': f'{base}500x500.jpg',
            'cover_xl': f'{base}1000x1000.jpg',
        },
    }


def test_deezer_cover_is_the_matching_row(monkeypatch) -> None:
    rows = [
        _deezer_row('Been By Now', 'Morgan Wallen'),
        _deezer_row(
            'Last Thing You Need (from GTAVI: The Album)', 'Morgan Wallen'
        ),
    ]
    monkeypatch.setattr(
        deezer.httpx, 'get', lambda *a, **k: _Resp({'data': rows})
    )
    url = deezer.find_track_cover('Morgan Wallen', SONG['name'], 1200)
    assert url.endswith('/1000x1000.jpg')
    assert deezer.find_track_cover(
        'Morgan Wallen', SONG['name'], 400
    ).endswith('/500x500.jpg')
    assert not deezer.find_track_cover('Tove Lo', SONG['name'], 1200)


def test_deezer_refusal_is_an_error_not_no_cover(monkeypatch) -> None:
    monkeypatch.setattr(
        deezer.httpx,
        'get',
        lambda *a, **k: _Resp({'error': {'code': 4, 'message': 'Quota'}}),
    )
    with pytest.raises(ValueError, match='refused'):
        deezer.find_track_cover('Morgan Wallen', SONG['name'], 1200)


# ── all sources at once ────────────────────────────────────────────
def test_every_source_is_asked_at_once_at_the_goal(monkeypatch) -> None:
    asked: list[tuple[str, int]] = []
    sizes = {
        'spotify': 640,
        'itunes': 1200,
        'youtube-music': 1200,
        'deezer': 1000,
    }

    def source_url(source: str, song: dict[str, Any], px: int) -> str:
        asked.append((source, px))
        time.sleep(0.3)
        return f'https://cover/{source}'

    monkeypatch.setattr(cover_sources, '_source_url', source_url)
    monkeypatch.setattr(
        cover_sources,
        '_fetch',
        lambda url: _png(sizes[url.rsplit('/', 1)[1]]),
    )
    started = time.monotonic()
    found = cover_sources.collect_candidates(
        SONG, sources=tuple(sizes), px=1200
    )
    # Four sleeping sources in parallel, not one after another.
    assert time.monotonic() - started < 1.0
    assert sorted(asked) == sorted((s, 1200) for s in sizes)
    assert [(c.source, c.width) for c in found] == list(sizes.items())


def test_a_failing_source_does_not_stop_the_others(monkeypatch) -> None:
    def source_url(source: str, song: dict[str, Any], px: int) -> str:
        if source == 'itunes':
            raise RuntimeError('boom')
        return f'https://cover/{source}'

    monkeypatch.setattr(cover_sources, '_source_url', source_url)
    monkeypatch.setattr(cover_sources, '_fetch', lambda url: _png(1000))
    found = cover_sources.collect_candidates(
        SONG, sources=('itunes', 'deezer'), px=1200
    )
    assert [c.source for c in found] == ['deezer']


def test_itunes_is_asked_at_the_goal_size(monkeypatch) -> None:
    sizes: list[int] = []
    monkeypatch.setattr(
        itunes,
        'fetch_artwork_url',
        lambda song, size: sizes.append(size) or '',
    )
    monkeypatch.setattr(cover_sources, '_source_url', _SOURCE_URL)
    cover_sources.collect_candidates(SONG, sources=('itunes',), px=1400)
    assert sizes == [1400]


# ── iTunes rate limit ──────────────────────────────────────────────
def test_itunes_rate_limit_is_waited_out(monkeypatch) -> None:
    answers = [_Resp({}, 429), _Resp({'results': [{'trackName': 'x'}]})]
    waits: list[float] = []
    monkeypatch.setattr(itunes, '_rate_wait', lambda: None)
    monkeypatch.setattr(itunes.time, 'sleep', waits.append)
    monkeypatch.setattr(itunes.httpx, 'get', lambda *a, **k: answers.pop(0))
    assert itunes._search_or_none('q') == [{'trackName': 'x'}]
    assert waits == [itunes._RETRY_WAITS[0]]


def test_itunes_gives_up_after_its_retries(monkeypatch) -> None:
    monkeypatch.setattr(itunes, '_rate_wait', lambda: None)
    monkeypatch.setattr(itunes.time, 'sleep', lambda s: None)
    monkeypatch.setattr(itunes.httpx, 'get', lambda *a, **k: _Resp({}, 429))
    assert itunes._search_or_none('q') is None
