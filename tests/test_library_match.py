"""Skipping songs the library already has, on request (issue #636).
Offline."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from downtify import api, library_match
from downtify.download_sources import DownloadSources
from downtify.library_catalog import LibraryContext
from downtify.library_match import (
    CATALOG_ID,
    SONG_KEY,
    build_matcher,
    request_sources,
    youtube_id,
)

SPOTIFY_ID = '4uLU6hMCjMI75M1A2tKUQC'
VIDEO_ID = 'dQw4w9WgXcQ'

ROWS = [
    {
        'file': 'Mica/Held Together.mp3',
        'artist': 'Mica Ferreira',
        'title': 'Held Together',
        'isrc': 'USAAA0000001',
    },
    {
        'file': 'Tomas/Quiet Static.mp3',
        'artist': 'Tomas Vale',
        'title': 'Quiet Static',
        'isrc': '',
    },
    {
        'file': 'Solenne/Driftlight.mp3',
        'artist': 'Solenne',
        'title': 'Driftlight',
        'isrc': '',
    },
]


class _Index:
    @staticmethod
    def filenames_by_spotify_id() -> dict[str, str]:
        return {SPOTIFY_ID: 'Tomas/Quiet Static.mp3', 'x' * 22: 'gone.mp3'}


@pytest.fixture
def library(tmp_path, monkeypatch):
    rows = [dict(row) for row in ROWS]

    def listing(_ctx, *, allowed_keys=None):
        if allowed_keys is None:
            return rows
        return [r for r in rows if r['file'] in allowed_keys]

    sources = DownloadSources(tmp_path / 'lib.db')
    sources.record('Solenne/Driftlight.mp3', None, VIDEO_ID, [])
    monkeypatch.setattr(library_match, 'listing_for_request', listing)
    return SimpleNamespace(
        ctx=LibraryContext(download_dir=tmp_path),
        index=_Index(),
        sources=sources,
    )


def _matcher(library, songs, allowed=None):
    return build_matcher(
        library.ctx,
        allowed_keys=allowed,
        track_index=library.index,
        download_sources=library.sources,
        sources=request_sources(songs),
    )


def _match(library, song, allowed=None):
    hit = _matcher(library, [song], allowed).match(song)
    return None if hit is None else (hit[0]['file'], hit[1])


def test_a_catalog_id_matches_even_when_the_title_differs(library):
    # Spotify track id, through the track index.
    assert _match(
        library,
        {'song_id': SPOTIFY_ID, 'name': 'Quiet Static (2024 Mix)'},
    ) == ('Tomas/Quiet Static.mp3', CATALOG_ID)
    # The video a file was downloaded from.
    assert _match(
        library,
        {
            'url': f'https://music.youtube.com/watch?v={VIDEO_ID}',
            'name': 'Something else',
            'artists': ['Nobody'],
        },
    ) == ('Solenne/Driftlight.mp3', CATALOG_ID)
    # ISRC.
    assert _match(library, {'isrc': 'usaaa0000001', 'name': 'Other'}) == (
        'Mica/Held Together.mp3',
        CATALOG_ID,
    )


def test_another_version_matches_by_song_key_but_a_live_one_does_not(
    library,
):
    assert _match(
        library,
        {
            'song_id': 'otherid',
            'name': 'Held Together - Remastered 2011',
            'artists': ['Mica Ferreira', 'Guest'],
        },
    ) == ('Mica/Held Together.mp3', SONG_KEY)
    assert (
        _match(
            library,
            {'name': 'Held Together (Live)', 'artists': ['Mica Ferreira']},
        )
        is None
    )


def test_only_rows_the_caller_may_see_count(library):
    song = {'name': 'Held Together', 'artists': ['Mica Ferreira']}
    assert _match(library, song, allowed={'Tomas/Quiet Static.mp3'}) is None


def test_youtube_id_reads_every_shape():
    assert youtube_id({'youtube_id': VIDEO_ID}) == VIDEO_ID
    assert youtube_id({'source': 'youtube', 'song_id': VIDEO_ID}) == VIDEO_ID
    assert youtube_id({'url': f'https://youtu.be/{VIDEO_ID}'}) == VIDEO_ID
    assert not youtube_id({'song_id': SPOTIFY_ID})


def test_files_for_sources_finds_only_the_asked_ones(tmp_path: Path):
    sources = DownloadSources(tmp_path / 'lib.db')
    sources.record('a.mp3', None, 'aaaaaaaaaaa', [])
    sources.record('b.mp3', None, 'bbbbbbbbbbb', [])
    assert sources.files_for_sources(['bbbbbbbbbbb', 'zzz', '']) == {
        'bbbbbbbbbbb': 'b.mp3'
    }


# ── the API ──────────────────────────────────────────────────────────


class _Request:
    def __init__(self, body: Any):
        self._body = body

    async def json(self) -> Any:
        return self._body


@pytest.fixture
def server(library, monkeypatch):
    monkeypatch.setattr(api, 'library_context', lambda: library.ctx)
    monkeypatch.setattr(api, 'allowed_entry_keys', lambda _r: None)
    monkeypatch.setattr(api, 'request_user_id', lambda _r: 0)
    monkeypatch.setattr(api.state, 'track_index', library.index)
    monkeypatch.setattr(api.state, 'download_sources', library.sources)
    monkeypatch.setattr(api.state, 'downloader', object())
    submitted: list[list[dict]] = []

    async def fake_submit(songs, playlist_url, **_kwargs):
        submitted.append(list(songs))
        return {'job_ids': [s['song_id'] for s in songs], 'count': len(songs)}

    async def no_log(*_a, **_k):
        return None

    monkeypatch.setattr(api, '_submit_playlist_batch', fake_submit)
    monkeypatch.setattr(api, 'log_activity', no_log)
    return SimpleNamespace(submitted=submitted)


OWNED = {
    'song_id': 'owned',
    'name': 'Held Together',
    'artists': ['Mica Ferreira'],
}
NEW = {'song_id': 'new', 'name': 'Brand New', 'artists': ['Mica Ferreira']}


def test_a_batch_queues_only_the_songs_the_library_lacks(server):
    result = asyncio.run(
        api.download_batch_endpoint(
            _Request({'songs': [OWNED, NEW], 'skip_if_in_library': True})
        )
    )
    assert server.submitted == [[NEW]]
    assert result['job_ids'] == ['new']
    assert result['already_in_library'] == [
        {
            'input_index': 0,
            'song_id': 'owned',
            'filename': 'Mica/Held Together.mp3',
            'match': SONG_KEY,
        }
    ]


def test_a_batch_of_owned_songs_queues_nothing(server):
    result = asyncio.run(
        api.download_batch_endpoint(
            _Request({'songs': [OWNED], 'skip_if_in_library': True})
        )
    )
    assert server.submitted == []
    assert result['count'] == 0
    assert result['already_in_library'][0]['song_id'] == 'owned'


def test_without_the_flag_a_batch_downloads_everything(server):
    result = asyncio.run(
        api.download_batch_endpoint(_Request({'songs': [OWNED, NEW]}))
    )
    assert server.submitted == [[OWNED, NEW]]
    assert 'already_in_library' not in result


def test_a_single_download_answers_already_in_library(server, monkeypatch):
    def no_run(*_a, **_k):
        raise AssertionError('nothing should be downloaded')

    monkeypatch.setattr(api, '_run_download', no_run)
    result = asyncio.run(
        api.download_endpoint(
            _Request(None),
            url='https://open.spotify.com/track/x',
            client_hints={
                **OWNED,
                'source': 'deezer',
                'skip_if_in_library': True,
            },
        )
    )
    assert result == {
        'status': 'already_in_library',
        'filename': 'Mica/Held Together.mp3',
        'match': SONG_KEY,
    }


def test_an_album_queues_its_tracks_and_answers_at_once(server, monkeypatch):
    album = [
        {**OWNED, 'album_name': 'Driftlight', 'album_artist': 'Mica Ferreira'},
        {**NEW, 'album_name': 'Driftlight', 'album_artist': 'Mica Ferreira'},
    ]
    monkeypatch.setattr(api, '_songs_for_album_download', lambda _url: album)
    result = asyncio.run(
        api.download_album_endpoint(
            _Request(None),
            url='https://music.youtube.com/browse/MPREb_x',
            wait=False,
            skip_if_in_library=True,
        )
    )
    assert result == {
        'album': 'Driftlight',
        'album_artist': 'Mica Ferreira',
        'track_count': 2,
        'job_ids': ['new'],
        'already_in_library': [
            {
                'input_index': 0,
                'song_id': 'owned',
                'filename': 'Mica/Held Together.mp3',
                'match': SONG_KEY,
            }
        ],
    }


def test_detailed_lookup_answers_per_requested_song(server):
    result = asyncio.run(
        api.library_lookup(
            _Request({
                'detailed': True,
                'songs': [
                    NEW,
                    {'id': 'req-7', 'song_id': SPOTIFY_ID, 'name': 'Renamed'},
                    OWNED,
                ],
            })
        )
    )
    assert [
        (m['input_index'], m.get('id'), m['match'], m['row']['file'])
        for m in result['matches']
    ] == [
        (1, 'req-7', CATALOG_ID, 'Tomas/Quiet Static.mp3'),
        (2, None, SONG_KEY, 'Mica/Held Together.mp3'),
    ]
