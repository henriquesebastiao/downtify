"""What the playlist page filters its songs by: which provider fetched each
file (``downtify/file_providers.py``) and which ones Navidrome hasn't
matched (``GET /api/library/playlists/details``). Offline."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from starlette.requests import Request

from downtify import api
from downtify import downloader as downloader_mod
from downtify.auth import USER, Principal, classify
from downtify.downloader import Downloader
from downtify.file_providers import (
    FOLDER,
    FileProviders,
    guess_provider,
    providers_for,
)
from downtify.library_cache_keys import file_content_key
from downtify.library_catalog import LibraryContext, entry_content_key
from downtify.library_paths_cache import invalidate_library_paths_cache
from downtify.navidrome_index import NavidromeIndex

# ── The store ───────────────────────────────────────────────────────────


def test_a_provider_is_found_by_content_key_or_path(tmp_path):
    store = FileProviders(tmp_path / 'lib.db')
    store.record('k1', 'a.mp3', 'youtube-music')
    store.record('k2', 'b.flac', 'slskd')
    store.record('', 'c.mp3', 'youtube')  # nothing to key it by
    store.record('k3', 'c.mp3', '')  # nothing to record

    found = store.lookup({
        'moved/a.mp3': 'k1',  # moved: found by its content key
        'b.flac': 'rewritten',  # rewritten in place: found by its path
        'c.mp3': 'k3',
        '': 'k1',
    })

    assert found == {'moved/a.mp3': 'youtube-music', 'b.flac': 'slskd'}
    assert store.lookup({}) == {}


def test_the_latest_download_of_a_file_wins(tmp_path):
    store = FileProviders(tmp_path / 'lib.db')
    store.record('k1', 'a.mp3', 'youtube')
    store.record('k1', 'a.mp3', 'youtube-music')

    assert store.lookup({'a.mp3': 'k1'}) == {'a.mp3': 'youtube-music'}


def test_a_provider_follows_a_rewritten_file_and_goes_with_it(tmp_path):
    store = FileProviders(tmp_path / 'lib.db')
    store.record('old', 'a.mp3', 'slskd')

    assert store.rekey('old', 'new', 'a.flac') == 1
    assert store.lookup({'a.flac': 'new'}) == {'a.flac': 'slskd'}
    assert store.lookup({'x.mp3': 'old'}) == {}
    store.drop('new')
    assert store.lookup({'a.flac': 'new'}) == {}


def test_older_files_are_recognised_by_their_path(tmp_path):
    assert guess_provider('slskd/Artist/a.flac') == 'slskd'
    assert guess_provider('ext/ab12/a.mp3') == FOLDER
    assert not guess_provider('Artist/a.mp3')
    store = FileProviders(tmp_path / 'lib.db')
    store.record('k1', 'slskd/x.flac', 'deemix')

    assert providers_for(
        store,
        {'slskd/x.flac': 'k1', 'slskd/y.flac': '', 'z.mp3': ''},
    ) == {'slskd/x.flac': 'deemix', 'slskd/y.flac': 'slskd'}
    assert providers_for(None, {'ext/1/a.mp3': ''}) == {'ext/1/a.mp3': FOLDER}


# ── Recording a download ────────────────────────────────────────────────

SONG = {
    'source': 'youtube',
    'song_id': 'vid',
    'name': 'Thunderstruck',
    'artists': ['AC/DC'],
    'album_name': 'The Razors Edge',
    'cover_url': 'https://img.test/c.jpg',
}


def test_the_hook_hears_which_provider_fetched_the_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        downloader_mod, 'enrich_from_match', lambda song, match: song
    )
    monkeypatch.setattr(Downloader, '_fetch_and_tag', lambda self, *a: 'f.mp3')
    heard: list[tuple[str, str]] = []
    dl = Downloader(tmp_path)
    dl.on_downloaded = lambda song, name: heard.append((
        song['download_provider'],
        name,
    ))

    dl.download(SONG)

    assert heard == [('youtube-music', 'f.mp3')]


@pytest.fixture
def library(tmp_path, monkeypatch):
    root = tmp_path / 'downloads'
    root.mkdir()
    ctx = LibraryContext(download_dir=root)
    store = FileProviders(tmp_path / 'lib.db')
    monkeypatch.setattr(api, 'library_context', lambda: ctx)
    monkeypatch.setattr(api.state, 'file_providers', store)
    invalidate_library_paths_cache()
    yield root, store
    invalidate_library_paths_cache()


def test_a_finished_download_records_its_provider(library, monkeypatch):
    root, store = library
    (root / 'f.mp3').write_bytes(b'audio')
    seeded: list[str] = []
    monkeypatch.setattr(
        api,
        'enrich_artist_after_download',
        lambda song, name: seeded.append(name),
    )

    api.after_download({**SONG, 'download_provider': 'slskd'}, 'f.mp3')
    api.after_download(SONG, 'g.mp3')  # no provider: nothing recorded

    key = file_content_key(root / 'f.mp3')
    assert store.lookup({'f.mp3': key}) == {'f.mp3': 'slskd'}
    assert seeded == ['f.mp3', 'g.mp3']
    api.rekey_file_owners(key, 'rewritten', 'f.mp3')
    assert store.lookup({'f.mp3': 'rewritten'}) == {'f.mp3': 'slskd'}
    api.drop_file_owners('rewritten')
    assert store.lookup({'other.mp3': 'rewritten'}) == {}


# ── Navidrome ───────────────────────────────────────────────────────────


def test_navidrome_matches_are_read_in_bulk(tmp_path):
    index = NavidromeIndex(tmp_path / 'lib.db')
    song = tmp_path / 'a.mp3'
    song.write_bytes(b'audio')
    index.store('a.mp3', 'nd-1', full_path=song)
    key = file_content_key(song)

    assert index.matched_files({
        'a.mp3': key,  # by path and key
        'moved/a.mp3': key,  # by key
        'b.mp3': 'other',
    }) == {'a.mp3', 'moved/a.mp3'}
    assert index.matched_files({}) == set()


# ── The endpoint ────────────────────────────────────────────────────────


def _admin() -> Request:
    scope: dict[str, Any] = {
        'type': 'http',
        'headers': [],
        'query_string': b'',
    }
    scope['state'] = {
        'principal': Principal('session', 'admin', '', 1, 'admin', 'admin')
    }
    return Request(scope)


def _entry(file: str, size: int) -> dict[str, Any]:
    return {'file': file, 'size': size, 'title': Path(file).stem}


@pytest.fixture
def playlist(library, monkeypatch, tmp_path):
    _root, store = library
    files = ['Road/a.mp3', 'Road/b.flac', 'slskd/c.flac', 'Road/d.mp3']
    entries = [_entry(f, 100 + n) for n, f in enumerate(files)]
    keys = {e['file']: entry_content_key(e) for e in entries}
    store.record(keys['Road/a.mp3'], 'Road/a.mp3', 'youtube-music')
    store.record(keys['Road/b.flac'], 'Road/b.flac', 'deemix')
    row = {
        'name': 'Road',
        'files': files,
        'count': len(files),
        'added': 1,
        'cover': '',
        'liked': False,
        'manual': False,
    }
    monkeypatch.setattr(api, 'list_library_playlists', lambda *a, **k: [row])
    monkeypatch.setattr(api, 'listing_for_request', lambda ctx: entries)
    monkeypatch.setattr(api.state, 'likes', None)
    index = NavidromeIndex(tmp_path / 'lib.db')
    with index._connect() as conn:
        conn.execute(
            'INSERT INTO navidrome_tracks (content_key, filename, '
            'navidrome_song_id, resolved_at) VALUES (?, ?, ?, ?)',
            (keys['Road/a.mp3'], 'Road/a.mp3', 'nd-1', 'now'),
        )
    monkeypatch.setattr(api.state, 'navidrome_index', index)
    return files


def _details() -> dict[str, Any]:
    return asyncio.run(api.playlist_details_endpoint(_admin(), name='Road'))


def test_the_page_learns_providers_and_navidrome_misses(playlist, monkeypatch):
    monkeypatch.setattr(api, '_navidrome_playlist_sync_on', lambda: True)

    result = _details()

    assert result['name'] == 'Road'
    assert result['providers'] == {
        'Road/a.mp3': 'youtube-music',
        'Road/b.flac': 'deemix',
        'slskd/c.flac': 'slskd',
    }
    assert result['navidrome'] == {
        'enabled': True,
        'unmatched': ['Road/b.flac', 'slskd/c.flac', 'Road/d.mp3'],
    }


def test_without_navidrome_sync_nothing_is_unmatched(playlist, monkeypatch):
    monkeypatch.setattr(api, '_navidrome_playlist_sync_on', lambda: False)

    assert _details()['navidrome'] == {'enabled': False, 'unmatched': []}


def test_the_route_is_for_signed_in_browsers():
    assert classify('GET', '/api/library/playlists/details') == USER
