"""Downloading a playlist as one album (issue #531). Offline."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from downtify import api
from downtify.album_artist import PLAYLIST_ALBUM, VARIOUS_ARTISTS
from downtify.downloader import Downloader

PLAYLIST = 'Road Trip'


def _songs() -> list[dict]:
    return [
        {
            'song_id': 'a',
            'name': 'Song A',
            'artists': ['Artist A'],
            'album_name': 'Album A',
            'downtify_track_order': 0,
        },
        {
            'song_id': 'b',
            'name': 'Song B',
            'artists': ['Artist B'],
            'album_name': 'Album B',
            'downtify_track_order': 1,
        },
    ]


def _run_batch(monkeypatch, tmp_path, *, as_album: bool) -> list[str]:
    dl = Downloader(
        download_dir=tmp_path,
        audio_format='mp3',
        organize_by_artist=True,
        organize_by_album=True,
    )
    monkeypatch.setattr(api.state, 'downloader', dl)
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api.state, 'download_semaphore', None)
    saved: list[str] = []

    async def fake_run_download(song, song_id, subdir=None, **_kwargs):
        parts = dl._format_output_parts(song)
        folder = dl._effective_subdir(song, subdir)
        saved.append(f'{folder}/{parts[-1]}')

    monkeypatch.setattr(api, '_run_download', fake_run_download)
    asyncio.run(
        api._process_batch(
            _songs(),
            ['job-a', 'job-b'],
            playlist_url='',
            generate_m3u=False,
            playlist_name=PLAYLIST,
            cover_url='https://img/playlist.jpg',
            as_album=as_album,
        )
    )
    return sorted(saved)


def test_a_playlist_saved_as_an_album_lands_in_one_folder(
    monkeypatch, tmp_path
):
    saved = _run_batch(monkeypatch, tmp_path, as_album=True)
    assert saved == [
        f'{VARIOUS_ARTISTS}/{PLAYLIST}/Artist A - Song A',
        f'{VARIOUS_ARTISTS}/{PLAYLIST}/Artist B - Song B',
    ]


def test_a_playlist_otherwise_goes_to_each_artists_album(
    monkeypatch, tmp_path
):
    saved = _run_batch(monkeypatch, tmp_path, as_album=False)
    assert saved == [
        'Artist A/Album A/Artist A - Song A',
        'Artist B/Album B/Artist B - Song B',
    ]


def test_the_batch_endpoint_passes_as_album_on(monkeypatch):
    seen: dict = {}

    async def fake_submit(songs, playlist_url, **kwargs):
        seen.update(kwargs)
        return {'job_ids': [], 'count': 0}

    class _Request:
        @staticmethod
        async def json():
            return {
                'songs': _songs(),
                'playlist_name': PLAYLIST,
                'as_album': True,
            }

    async def no_log(*_a, **_k):
        return None

    monkeypatch.setattr(api.state, 'downloader', object())
    monkeypatch.setattr(api, '_submit_playlist_batch', fake_submit)
    monkeypatch.setattr(api, 'log_activity', no_log)
    monkeypatch.setattr(api, 'request_user_id', lambda _r: 0)
    asyncio.run(api.download_batch_endpoint(_Request()))
    assert seen['as_album'] is True


def test_an_album_track_ignores_the_copy_elsewhere_in_the_library(
    monkeypatch,
):
    # With "Download again if the file exists" off, a song the library
    # has elsewhere is normally linked; an album wants its own copy, so
    # only a file already in the album counts.
    seen: list = []

    def fake_resolve(downloader, song, *, subdir=None, track_index=None):
        seen.append(track_index)

    monkeypatch.setattr(
        api.state,
        'downloader',
        SimpleNamespace(overwrite_existing_files=False),
    )
    monkeypatch.setattr(api.state, 'track_index', 'the index')
    monkeypatch.setattr(api, 'resolve_existing_download', fake_resolve)
    asyncio.run(api._finish_with_existing({PLAYLIST_ALBUM: True}, {}, None))
    asyncio.run(api._finish_with_existing({}, {}, None))
    assert seen == [None, 'the index']
