"""Tests for Last.fm similar-track lookup (downtify.lastfm) and the
``GET /api/similar/tracks`` endpoint. All HTTP is mocked - no network."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from downtify import api, lastfm


def _response(payload):
    resp = MagicMock()
    resp.raise_for_status = lambda: None
    resp.json = lambda: payload
    return resp


def _track_payload():
    return {
        'similartracks': {
            'track': [
                {
                    'name': 'Believe',
                    'match': '0.95',
                    'url': 'https://www.last.fm/music/Cher/_/Believe',
                    'artist': {'name': 'Cher'},
                    'image': [
                        {'#text': 'https://img/small', 'size': 'small'},
                        {'#text': 'https://img/xl', 'size': 'extralarge'},
                    ],
                },
                # No artist: skipped, not an error.
                {'name': 'No One', 'match': '0.5'},
                {'name': 'Strong Enough', 'artist': {'name': 'Cher'}},
            ]
        }
    }


def test_get_similar_tracks_shapes_entries():
    with patch(
        'downtify.lastfm.httpx.get',
        return_value=_response(_track_payload()),
    ):
        result = lastfm.get_similar_tracks('Cher', 'Believe', 'key')
    assert result['artist'] == 'Cher'
    assert result['track'] == 'Believe'
    assert [t['title'] for t in result['tracks']] == [
        'Believe',
        'Strong Enough',
    ]
    first = result['tracks'][0]
    assert first['artist'] == 'Cher'
    assert first['match'] == pytest.approx(0.95)
    assert first['image_url'] == 'https://img/xl'
    assert result['tracks'][1]['match'] == 0.0


def test_get_similar_tracks_accepts_a_single_track_dict():
    payload = {'similartracks': {'track': {'name': 'One', 'artist': 'U2'}}}
    with patch('downtify.lastfm.httpx.get', return_value=_response(payload)):
        result = lastfm.get_similar_tracks('U2', 'With or Without You', 'k')
    assert [(t['title'], t['artist']) for t in result['tracks']] == [
        ('One', 'U2')
    ]


def test_get_similar_tracks_requires_a_key():
    with pytest.raises(ValueError, match='API key'):
        lastfm.get_similar_tracks('Cher', 'Believe', '  ')


def test_get_similar_tracks_requires_artist_and_track():
    with pytest.raises(ValueError, match='artist and track'):
        lastfm.get_similar_tracks(' ', 'Believe', 'key')


def test_get_similar_tracks_reports_lastfm_errors():
    payload = {'error': 10, 'message': 'Invalid API key'}
    with (
        patch('downtify.lastfm.httpx.get', return_value=_response(payload)),
        pytest.raises(ValueError, match='Invalid API key'),
    ):
        lastfm.get_similar_tracks('Cher', 'Believe', 'bad')


def test_get_similar_tracks_reports_network_failures():
    with (
        patch('downtify.lastfm.httpx.get', side_effect=Exception('down')),
        pytest.raises(ValueError, match='did not answer'),
    ):
        lastfm.get_similar_tracks('Cher', 'Believe', 'key')


def test_similar_tracks_endpoint_needs_a_key(monkeypatch):
    monkeypatch.setitem(api.state.settings, 'lastfm_api_key', '')
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            api.similar_tracks_endpoint(artist='Cher', track='Believe')
        )
    assert exc.value.status_code == 400


def test_similar_tracks_endpoint(monkeypatch):
    monkeypatch.setitem(api.state.settings, 'lastfm_api_key', 'key')
    monkeypatch.setattr(
        api.lastfm,
        'get_similar_tracks',
        lambda a, t, k, limit=20: {
            'artist': a,
            'track': t,
            'tracks': [],
        },
    )
    assert asyncio.run(
        api.similar_tracks_endpoint(artist='Cher', track='Believe')
    ) == {'artist': 'Cher', 'track': 'Believe', 'tracks': []}


def test_similar_tracks_endpoint_maps_upstream_errors(monkeypatch):
    monkeypatch.setitem(api.state.settings, 'lastfm_api_key', 'key')

    def down(*_args, **_kwargs):
        raise ValueError('Last.fm did not answer: down')

    monkeypatch.setattr(api.lastfm, 'get_similar_tracks', down)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            api.similar_tracks_endpoint(artist='Cher', track='Believe')
        )
    assert exc.value.status_code == 502


def test_lastfm_api_key_is_a_default_setting():
    assert not api.DEFAULT_SETTINGS['lastfm_api_key']


def test_test_api_key_reports_a_missing_key():
    result = lastfm.test_api_key('  ')
    assert result == {
        'ok': False,
        'server': '',
        'checks': [
            {
                'id': 'auth',
                'status': 'fail',
                'code': 'missing_key',
                'detail': '',
            }
        ],
    }


def test_test_api_key_accepts_a_working_key():
    payload = {'similartracks': {'track': []}}
    with patch('downtify.lastfm.httpx.get', return_value=_response(payload)):
        result = lastfm.test_api_key('key')
    assert result['ok'] is True
    assert result['server'] == 'Last.fm'


def test_test_api_key_rejects_a_bad_key():
    payload = {'error': 10, 'message': 'Invalid API key'}
    with patch('downtify.lastfm.httpx.get', return_value=_response(payload)):
        result = lastfm.test_api_key('bad')
    assert result == {
        'ok': False,
        'server': '',
        'checks': [
            {
                'id': 'auth',
                'status': 'fail',
                'code': 'invalid_key',
                'detail': '',
            }
        ],
    }


def test_test_api_key_reports_other_api_errors_without_leaking():
    payload = {'error': 6, 'message': 'No track'}
    with patch('downtify.lastfm.httpx.get', return_value=_response(payload)):
        result = lastfm.test_api_key('key')
    assert result['ok'] is False
    (check,) = result['checks']
    assert (check['id'], check['status'], check['code']) == (
        'lastfm',
        'fail',
        'error',
    )


def test_test_api_key_reports_network_failures():
    with patch(
        'downtify.lastfm.httpx.get',
        side_effect=httpx.TimeoutException('slow'),
    ):
        result = lastfm.test_api_key('key')
    assert [c['code'] for c in result['checks']] == ['timeout']
    with patch(
        'downtify.lastfm.httpx.get', side_effect=httpx.ConnectError('down')
    ):
        result = lastfm.test_api_key('key')
    assert [c['code'] for c in result['checks']] == ['unreachable']


def test_similar_test_endpoint_prefers_the_given_key(monkeypatch):
    seen = {}
    monkeypatch.setitem(api.state.settings, 'lastfm_api_key', 'saved')

    def fake(key):
        seen['key'] = key
        return {'ok': True}

    monkeypatch.setattr(api.lastfm, 'test_api_key', fake)
    assert asyncio.run(
        api.test_similar_endpoint(_FakeRequest({'api_key': '  typed  '}))
    ) == {'ok': True}
    assert seen == {'key': 'typed'}


def test_similar_test_endpoint_falls_back_to_the_saved_key(monkeypatch):
    seen = {}
    monkeypatch.setitem(api.state.settings, 'lastfm_api_key', 'saved')
    monkeypatch.setattr(
        api.lastfm, 'test_api_key', lambda key: seen.setdefault('key', key)
    )
    asyncio.run(api.test_similar_endpoint(_FakeRequest({})))
    assert seen == {'key': 'saved'}


class _FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


def test_update_settings_trims_the_lastfm_key(monkeypatch):
    monkeypatch.setitem(api.state.settings, 'lastfm_api_key', '')
    monkeypatch.setattr(api.state, 'settings_path', None)
    result = asyncio.run(
        api.update_settings_endpoint(
            _FakeRequest({'lastfm_api_key': '  abc123  '})
        )
    )
    assert result['lastfm_api_key'] == 'abc123'
