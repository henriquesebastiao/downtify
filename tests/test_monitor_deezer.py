"""Public Deezer playlists reuse the incremental monitor, offline."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from downtify import api, monitor
from downtify.auth import Principal
from downtify.playlist_catalog import PlaylistCatalog

URL = 'https://www.deezer.com/fr/playlist/123456'
KEY = 'deezer:playlist:123456'


def _request(user_id: int, payload: dict[str, Any]) -> Request:
    async def receive() -> dict[str, Any]:
        return {'type': 'http.request', 'body': json.dumps(payload).encode()}

    principal = Principal('device', 'test', '', user_id, 'user', 'user')
    return Request(
        {'type': 'http', 'headers': [], 'state': {'principal': principal}},
        receive,
    )


def test_deezer_resolution_and_namespace(monkeypatch):
    seen = []

    def fetch(pid: str) -> tuple[str, list[dict]]:
        seen.append(pid)
        return 'Chart', [{'song_id': 'deezer-42', 'source': 'deezer'}]

    monkeypatch.setattr(monitor.deezer, 'playlist_info_and_tracks', fetch)
    assert monitor.parse_playlist_url(URL) == ('deezer', '123456')
    assert monitor.watch_source(URL) == 'deezer'
    assert asyncio.run(api._resolve_watch_target(URL)) == (
        'playlist',
        KEY,
        'Chart',
    )
    assert monitor.fetch_playlist('deezer', KEY)[0] == 'Chart'
    assert seen == ['123456', '123456']
    assert (
        monitor.parse_playlist_url('https://www.deezer.com/artist/123456')
        is None
    )


def test_deezer_cover_uses_raw_id(monkeypatch):
    seen = []
    monkeypatch.setattr(
        monitor.deezer,
        'playlist_cover_url_from_id',
        lambda pid: seen.append(pid) or 'https://example.org/cover.jpg',
    )
    assert monitor.fetch_playlist_cover_url('deezer', KEY).endswith(
        'cover.jpg'
    )
    assert seen == ['123456']


def test_add_watch_scopes_duplicates_to_user(monkeypatch, tmp_path):
    db = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    monkeypatch.setattr(api.state, 'monitor_db', db)
    monkeypatch.setattr(api.state, 'downloader', None)
    monkeypatch.setattr(
        monitor.deezer, 'playlist_info_and_tracks', lambda _pid: ('Chart', [])
    )
    payload = {'url': URL}
    first = asyncio.run(api.add_monitor_playlist(_request(1, payload)))
    second = asyncio.run(api.add_monitor_playlist(_request(2, payload)))
    assert first['spotify_id'] == second['spotify_id'] == KEY
    assert first['source'] == second['source'] == 'deezer'
    assert first['id'] != second['id']
    assert [row.user_id for row in db.list_playlists(1)] == [1]
    with pytest.raises(HTTPException) as error:
        asyncio.run(api.add_monitor_playlist(_request(1, payload)))
    assert error.value.status_code == 409


class _Downloader:
    organize_by_artist = False
    organize_by_album = False
    overwrite_existing_files = False
    slskd_settings: dict = {}

    def __init__(self, root: Path) -> None:
        self.download_dir = root
        self.calls: list[str] = []

    def download(self, song: dict, _callback: Any, subdir: str = '') -> str:
        self.calls.append(song['song_id'])
        filename = f'{subdir}/{song["name"]}.mp3'
        path = self.download_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fixture')
        return filename

    @staticmethod
    def existing_filename_for(_song: dict, subdir: str = '') -> None:
        return None


def test_sweep_downloads_only_additions(monkeypatch, tmp_path):
    songs = [
        {
            'song_id': 'deezer-42',
            'source': 'deezer',
            'name': 'Alpha',
            'artists': ['Example'],
        }
    ]
    ids = []

    def fetch(pid: str) -> tuple[str, list[dict]]:
        ids.append(pid)
        return 'Chart', list(songs)

    monkeypatch.setattr(monitor.deezer, 'playlist_info_and_tracks', fetch)
    db = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist(KEY, 'Chart', URL, user_id=1)
    downloader = _Downloader(tmp_path / 'downloads')
    catalog = PlaylistCatalog(tmp_path / 'library.db')

    async def sweep() -> int:
        async def broadcast(_message: dict) -> None:
            pass

        return await monitor.check_playlist(
            watch,
            db,
            downloader,
            broadcast,
            asyncio.get_running_loop(),
            {'generate_m3u': False},
            monitor.LibraryStores(playlist_catalog=catalog),
        )

    assert asyncio.run(sweep()) == 1
    assert asyncio.run(sweep()) == 0
    songs.append({
        'song_id': 'deezer-43',
        'source': 'deezer',
        'name': 'Beta',
        'artists': ['Example'],
    })
    assert asyncio.run(sweep()) == 1
    assert downloader.calls == ['deezer-42', 'deezer-43']
    assert ids == ['123456'] * 3
    assert len(db.get_track_filenames(watch.id)) == 2
    assert catalog.spotify_id_for_playlist('Chart') is None
    assert len(catalog.list_tracks('Chart')) == 2
    assert catalog.playlist_owner_map()['Chart'] == 1


@pytest.mark.parametrize(
    'song',
    [
        {'song_id': 'deezer-42', 'source': 'text_search'},
        {'song_id': 'deezer-invalid', 'source': 'deezer'},
        {'song_id': '42', 'source': 'deezer'},
    ],
)
def test_catalog_rejects_ambiguous_ids(tmp_path, song):
    catalog = PlaylistCatalog(tmp_path / 'library.db')
    full = tmp_path / 'test.mp3'
    full.write_bytes(b'fixture')
    catalog.upsert_track('Chart', song, 'test.mp3', full)
    assert catalog.list_tracks('Chart') == []
