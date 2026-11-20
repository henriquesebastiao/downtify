"""A failed iTunes request isn't remembered as "iTunes has no cover"."""

from __future__ import annotations

from typing import Any

import httpx

from downtify import itunes

SONG = {
    'name': 'Last Thing You Need',
    'artists': ['Morgan Wallen'],
    'album_name': 'GTAVI: The Album',
}
ROW = {
    'wrapperType': 'track',
    'kind': 'song',
    'artistName': 'Morgan Wallen',
    'trackName': 'Last Thing You Need',
    'artworkUrl100': 'https://is1-ssl.mzstatic.com/image/thumb/a/100x100bb.jpg',
}


class _Resp:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    @staticmethod
    def raise_for_status() -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {'results': self.rows}


def _setup(monkeypatch, answers: list[Any]) -> None:
    itunes._artwork_cache.clear()
    monkeypatch.setattr(itunes, '_rate_wait', lambda: None)

    def get(*_a, **_k):
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(itunes.httpx, 'get', get)


def test_rate_limited_lookup_is_tried_again(monkeypatch) -> None:
    limited = httpx.HTTPError('429 Too Many Requests')
    _setup(monkeypatch, [limited, limited, _Resp([ROW])])
    assert not itunes.fetch_artwork_url(SONG)
    assert itunes.fetch_artwork_url(SONG).endswith('1200x1200bb.jpg')


def test_no_match_is_still_remembered(monkeypatch) -> None:
    _setup(monkeypatch, [_Resp([]), _Resp([])])
    assert not itunes.fetch_artwork_url(SONG)
    # Cached: a second call makes no request (none are left to answer).
    assert not itunes.fetch_artwork_url(SONG)
