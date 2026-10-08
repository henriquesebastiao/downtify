"""Tests for the YouTube similar-track source
(``providers.youtube_similar_tracks``) and the ``source=`` dispatch of
``GET /api/similar/tracks``. All YouTube Music calls are faked."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from downtify import api, providers


def _hit(video_id, title, artist):
    return {
        'videoId': video_id,
        'title': title,
        'artists': [{'name': artist}],
        'thumbnails': [{'url': 'https://img=w60-h60'}],
        'duration_seconds': 200,
    }


def _watch(video_id, title, artist, length='3:44'):
    return {
        'videoId': video_id,
        'title': title,
        'artists': [{'name': artist}],
        'thumbnail': [{'url': 'https://img=w60-h60'}],
        'length': length,
        'album': {'name': 'Believe'},
    }


class _FakeYTM:
    def __init__(self, hits, watch_tracks=None, boom=False):
        self._hits = hits
        self._watch_tracks = watch_tracks or []
        self._boom = boom
        self.watch_kwargs = None

    def search(self, query, filter=None, limit=None):  # noqa: A002
        return self._hits

    def get_watch_playlist(self, videoId=None, limit=25, radio=False, **_):
        self.watch_kwargs = {
            'videoId': videoId,
            'limit': limit,
            'radio': radio,
        }
        if self._boom:
            raise Exception('down')
        return {'tracks': self._watch_tracks}


def _ytm(monkeypatch, hits, watch_tracks=None, boom=False):
    fake = _FakeYTM(hits, watch_tracks, boom)
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    return fake


def test_youtube_similar_shapes_downloadable_rows(monkeypatch):
    fake = _ytm(
        monkeypatch,
        [_hit('seed1', 'Believe', 'Cher')],
        [
            _watch('seed1', 'Believe', 'Cher'),
            _watch('v1', 'Strong Enough', 'Cher'),
            {'title': 'No video id', 'artists': [{'name': 'Cher'}]},
            _watch('v2', 'All or Nothing', 'Cher'),
        ],
    )
    result = providers.youtube_similar_tracks('Cher', 'Believe', limit=20)
    assert result['source'] == 'youtube'
    assert [t['song_id'] for t in result['tracks']] == ['v1', 'v2']
    first = result['tracks'][0]
    assert first['name'] == 'Strong Enough'
    assert first['artists'] == ['Cher']
    assert first['url'] == 'https://music.youtube.com/watch?v=v1'
    assert first['cover_url']
    # Ranked by relevance: earlier rows score higher.
    assert result['tracks'][0]['match'] > result['tracks'][1]['match'] > 0
    assert fake.watch_kwargs['radio'] is True
    assert fake.watch_kwargs['videoId'] == 'seed1'


def test_youtube_similar_prefers_the_seeds_artist(monkeypatch):
    fake = _ytm(
        monkeypatch,
        [
            _hit('other1', 'Believe', 'Someone Else'),
            _hit('seed9', 'Believe (Cher)', 'Cher'),
        ],
        [_watch('v1', 'Strong Enough', 'Cher')],
    )
    providers.youtube_similar_tracks('Cher', 'Believe')
    assert fake.watch_kwargs['videoId'] == 'seed9'


def test_youtube_similar_needs_a_seed_match(monkeypatch):
    _ytm(monkeypatch, [], [])
    with pytest.raises(ValueError, match='No match'):
        providers.youtube_similar_tracks('Nobody', 'Nothing')


def test_youtube_similar_reports_watch_failures(monkeypatch):
    _ytm(monkeypatch, [_hit('seed1', 'Believe', 'Cher')], boom=True)
    with pytest.raises(ValueError, match='did not answer'):
        providers.youtube_similar_tracks('Cher', 'Believe')


def test_youtube_similar_needs_artist_and_track():
    with pytest.raises(ValueError, match='artist and track'):
        providers.youtube_similar_tracks(' ', 'Believe')


def test_similar_endpoint(monkeypatch):
    monkeypatch.setattr(
        providers,
        'youtube_similar_tracks',
        lambda a, t, limit=20: {'tracks': []},
    )
    assert asyncio.run(
        api.similar_tracks_endpoint(artist='Cher', track='Believe')
    ) == {'tracks': []}


def test_similar_endpoint_maps_failures(monkeypatch):
    def down(*_args, **_kwargs):
        raise ValueError('YouTube Music did not answer: down')

    monkeypatch.setattr(providers, 'youtube_similar_tracks', down)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            api.similar_tracks_endpoint(artist='Cher', track='Believe')
        )
    assert exc.value.status_code == 502
