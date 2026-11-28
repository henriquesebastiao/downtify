"""Spotify query codes repaired from its player (downtify/spotify_hashes.py)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from downtify import spotify, spotify_hashes
from downtify.spotify_hashes import HashStore

OLD = 'a' * 64
NEW = 'b' * 64
MAIN = 'https://cdn.example/cdn/build/web-player/web-player.1234abcd.js'
PAGE = f'<html><script src="https://cdn.example/x/gtm.js"></script><script src="{MAIN}"></script></html>'


def _main(op='fetchPlaylist', code=NEW, extra=''):
    return f'xx new tz.l("{op}","query","{code}",null) yy {extra}'


class _Web:
    def __init__(self, files):
        self.files = files
        self.asked = []

    def get(self, url, **_kw):
        self.asked.append(url)
        if url not in self.files:
            raise httpx.HTTPStatusError(
                '404',
                request=httpx.Request('GET', url),
                response=httpx.Response(404),
            )
        return SimpleNamespace(
            text=self.files[url], raise_for_status=lambda: None
        )


def _store(files, now=None):
    sent = []
    clock = now or {'t': 1000.0}
    web = _Web(files)
    s = HashStore(
        http_get=web.get,
        emit=lambda *a: sent.append(a),
        clock=lambda: clock['t'],
    )
    return s, web, sent, clock


def test_is_stale():
    assert spotify_hashes.is_stale({
        'errors': [{'message': 'PersistedQueryNotFound'}]
    })
    assert not spotify_hashes.is_stale({'errors': [{'message': 'other'}]})
    assert not spotify_hashes.is_stale({'data': {}})
    assert not spotify_hashes.is_stale(None)


def test_find_hash():
    assert spotify_hashes.find_hash(_main(), 'fetchPlaylist') == NEW
    assert spotify_hashes.find_hash(_main(), 'searchSuggestions') is None


def test_chunk_urls_try_every_file_of_the_part():
    script = (
        '{7161:"xpui-routes-artist",770:"home"}'
        '{7161:"380c5c3e",770:"11111111"}{7161:"8ce056c1"}'
    )
    urls = spotify_hashes.chunk_urls(
        script, 'https://cdn/web-player', 'xpui-routes-artist'
    )
    assert urls == [
        'https://cdn/web-player/xpui-routes-artist.380c5c3e.js',
        'https://cdn/web-player/xpui-routes-artist.8ce056c1.js',
    ]


def test_repair_learns_the_new_code_and_keeps_it(tmp_path):
    s, _web, sent, _ = _store({spotify_hashes.PLAYER_URL: PAGE, MAIN: _main()})
    path = tmp_path / 'spotify_hashes.json'
    s.configure(path)

    assert s.repair('fetchPlaylist', OLD) == NEW
    assert s.current('fetchPlaylist', OLD) == NEW
    assert json.loads(path.read_text())['hashes'] == {
        'fetchPlaylist': {'code': NEW, 'replaces': OLD}
    }
    assert sent[0][:2] == ('spotify', 'Fixed by itself')

    again = HashStore()
    again.configure(path)
    assert again.current('fetchPlaylist', OLD) == NEW
    assert again.current('searchSuggestions', OLD) == OLD
    # A Downtify update with another built-in code uses that one again.
    assert again.current('fetchPlaylist', 'c' * 64) == 'c' * 64


def test_repair_reads_a_lazily_loaded_part():
    disco = 'queryArtistDiscographyAll'
    main = (
        _main()
        + '{7161:"xpui-routes-artist"}{7161:"deadbeef"}{7161:"380c5c3e"}'
    )
    chunk = 'https://cdn.example/cdn/build/web-player/xpui-routes-artist.380c5c3e.js'
    s, _web, _sent, _ = _store({
        spotify_hashes.PLAYER_URL: PAGE,
        MAIN: main,
        chunk: _main(disco),
    })

    assert s.repair(disco, OLD) == NEW


def test_nothing_found_reports_broken_once():
    s, web, sent, clock = _store({
        spotify_hashes.PLAYER_URL: PAGE,
        MAIN: 'no codes here',
    })

    assert s.repair('fetchPlaylist', OLD) is None
    assert sent[0][1] == 'Reading Spotify is broken'
    assert 'fetchPlaylist' in sent[0][2]
    # Not looked up again within the gap.
    clock['t'] += 60
    assert s.repair('fetchPlaylist', OLD) is None
    assert web.asked.count(MAIN) == 1
    # Looked up again later, but the message isn't repeated yet.
    clock['t'] += spotify_hashes.MIN_LOOKUP_GAP
    assert s.repair('fetchPlaylist', OLD) is None
    assert web.asked.count(MAIN) == 2
    assert len(sent) == 1


def test_the_player_still_using_the_refused_code_is_broken():
    s, _web, sent, _ = _store({
        spotify_hashes.PLAYER_URL: PAGE,
        MAIN: _main(code=OLD),
    })

    assert s.repair('fetchPlaylist', OLD) is None
    assert sent[0][1] == 'Reading Spotify is broken'


def test_a_code_another_request_repaired_is_reused_without_lookup():
    s, web, _sent, _ = _store({spotify_hashes.PLAYER_URL: PAGE, MAIN: _main()})
    s.repair('fetchPlaylist', OLD)
    web.asked.clear()

    assert s.repair('fetchPlaylist', OLD) == NEW
    assert web.asked == []


def test_page_without_the_player_script_is_broken():
    s, _web, sent, _ = _store({spotify_hashes.PLAYER_URL: '<html></html>'})

    assert s.repair('fetchPlaylist', OLD) is None
    assert 'web-player' in sent[0][2]


# -- the requests in downtify/spotify.py ----------------------------------


def _answer(payload):
    return SimpleNamespace(json=lambda: payload, raise_for_status=lambda: None)


@pytest.fixture
def fresh_store(monkeypatch):
    s = HashStore(emit=lambda *a: None)
    monkeypatch.setattr(spotify_hashes, 'store', s)
    return s


def test_a_stale_answer_is_repaired_and_sent_again(fresh_store, monkeypatch):
    monkeypatch.setattr(
        fresh_store,
        'repair',
        lambda op, stale, builtin=None: NEW if stale == OLD else None,
    )
    sent_hashes = []

    def get(_url, params, **_kw):
        code = json.loads(params['extensions'])['persistedQuery']['sha256Hash']
        sent_hashes.append(code)
        if code == OLD:
            return _answer({'errors': [{'message': 'PersistedQueryNotFound'}]})
        return _answer({'data': {'ok': True}})

    with patch('downtify.spotify.httpx.get', side_effect=get):
        data = spotify._persisted_query('fetchPlaylist', {}, OLD, 'tok')

    assert data == {'data': {'ok': True}}
    assert sent_hashes == [OLD, NEW]


def test_no_repair_means_the_stale_answer_comes_back(fresh_store, monkeypatch):
    monkeypatch.setattr(fresh_store, 'repair', lambda *_a: None)
    stale = {'errors': [{'message': 'PersistedQueryNotFound'}]}

    with patch('downtify.spotify.httpx.get', return_value=_answer(stale)) as g:
        data = spotify._persisted_query('fetchPlaylist', {}, OLD, 'tok')

    assert data == stale
    assert g.call_count == 1


def test_a_learnt_code_is_used_first(fresh_store):
    fresh_store._learnt['searchSuggestions'] = {'code': NEW, 'replaces': OLD}
    sent = []

    def get(_url, params, **_kw):
        sent.append(
            json.loads(params['extensions'])['persistedQuery']['sha256Hash']
        )
        return _answer({'data': {}})

    with patch('downtify.spotify.httpx.get', side_effect=get):
        spotify._persisted_query('searchSuggestions', {}, OLD, 'tok')

    assert sent == [NEW]


def test_spotify_event_reaches_channels_saved_before_it():
    from downtify import notifications  # noqa: PLC0415

    saved = {'channels': {'discord': {'events': ['download_failed']}}}
    events = notifications.effective(saved)['channels']['discord']['events']
    assert 'spotify' in events
