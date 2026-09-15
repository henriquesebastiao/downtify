"""Playlist Monitor sweeps keep the library stores (track index, playlist
catalog, Navidrome) up to date (PR #182)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from downtify import monitor
from downtify.monitor import LibraryStores, PlaylistMonitorDB
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex

TRACK_A = '4uLU6hMCjMI75M1A2tKUQC'
TRACK_B = '7ouMYWpwJ422jRcDASZB7P'
PLAYLIST_ID = '37i9dQZF1DXcBWIGoYBM5M'


class _Downloader:
    organize_by_artist = False
    organize_by_album = False
    slskd_settings: dict = {}

    def __init__(self, download_dir: Path, *, overwrite: bool = True):
        self.download_dir = download_dir
        self.overwrite_existing_files = overwrite
        self.downloaded: list[str] = []

    def download(self, song, cb, subdir=None):
        self.downloaded.append(song['song_id'])
        name = f'{subdir}/{song["name"]}.mp3'
        path = self.download_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'audio')
        return name

    @staticmethod
    def existing_filename_for(song, subdir=None):
        return None


def _tracks():
    return [
        {'song_id': TRACK_A, 'name': 'Alpha', 'artists': ['Artist']},
        {'song_id': TRACK_B, 'name': 'Beta', 'artists': ['Artist']},
    ]


def _sweep(monkeypatch, tmp_path, downloader, settings, library):
    tracks = _tracks()
    monkeypatch.setattr(
        monitor.spotify, 'playlist_tracks_from_id', lambda _id: tracks
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda _id: {})
    # Same file on every call, so a second sweep sees the first one's rows.
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    playlist = db.get_by_spotify_id(PLAYLIST_ID) or db.add_playlist(
        PLAYLIST_ID,
        'Road Trip',
        f'https://open.spotify.com/playlist/{PLAYLIST_ID}',
    )

    async def _broadcast(_msg):
        return None

    loop = asyncio.new_event_loop()
    try:
        count = loop.run_until_complete(
            monitor.check_playlist(
                playlist, db, downloader, _broadcast, loop, settings, library
            )
        )
    finally:
        loop.close()
    return count, db, playlist


def _library(tmp_path) -> LibraryStores:
    db = tmp_path / 'library.db'
    return LibraryStores(
        track_index=TrackIndex(db), playlist_catalog=PlaylistCatalog(db)
    )


def test_sweep_registers_downloads_in_index_and_catalog(monkeypatch, tmp_path):
    library = _library(tmp_path)
    downloader = _Downloader(tmp_path / 'downloads')

    count, _db, _pl = _sweep(
        monkeypatch,
        tmp_path,
        downloader,
        {'generate_m3u': False},
        library,
    )

    assert count == 2
    assert library.track_index.lookup(TRACK_A) == 'Road Trip/Alpha.mp3'
    rows = library.playlist_catalog.list_tracks('Road Trip')
    assert [(r['filename'], r['track_order']) for r in rows] == [
        ('Road Trip/Alpha.mp3', 0),
        ('Road Trip/Beta.mp3', 1),
    ]
    assert library.playlist_catalog.spotify_id_for_playlist('Road Trip') == (
        PLAYLIST_ID
    )


def test_sweep_links_tracks_already_in_library_when_overwrite_is_off(
    monkeypatch, tmp_path
):
    library = _library(tmp_path)
    existing = tmp_path / 'downloads' / 'Other' / 'Alpha.mp3'
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b'audio')
    library.track_index.register(TRACK_A, 'Other/Alpha.mp3')
    downloader = _Downloader(tmp_path / 'downloads', overwrite=False)

    count, db, playlist = _sweep(
        monkeypatch,
        tmp_path,
        downloader,
        {'generate_m3u': False},
        library,
    )

    assert downloader.downloaded == [TRACK_B]
    assert count == 1
    assert db.get_track_filenames(playlist.id)[TRACK_A] == 'Other/Alpha.mp3'


def test_sweep_downloads_again_when_overwrite_is_on(monkeypatch, tmp_path):
    library = _library(tmp_path)
    existing = tmp_path / 'downloads' / 'Other' / 'Alpha.mp3'
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b'audio')
    library.track_index.register(TRACK_A, 'Other/Alpha.mp3')
    downloader = _Downloader(tmp_path / 'downloads', overwrite=True)

    _sweep(monkeypatch, tmp_path, downloader, {'generate_m3u': False}, library)

    assert downloader.downloaded == [TRACK_A, TRACK_B]


def test_sweep_syncs_navidrome_only_when_enabled(monkeypatch, tmp_path):
    synced = []
    monkeypatch.setattr(
        monitor,
        'sync_playlist_to_navidrome',
        lambda name, songs, settings, **kw: synced.append((name, len(songs))),
    )
    library = _library(tmp_path)
    downloader = _Downloader(tmp_path / 'downloads')
    _sweep(
        monkeypatch,
        tmp_path,
        downloader,
        {'generate_m3u': False, 'navidrome': {'enabled': False}},
        library,
    )
    assert synced == []

    # A later sweep with a new track and Navidrome on syncs the playlist.
    monkeypatch.setattr(
        monitor,
        '_split_new_tracks',
        _force_new([_tracks()[1]]),
    )
    _sweep(
        monkeypatch,
        tmp_path,
        downloader,
        {
            'generate_m3u': False,
            'navidrome': {
                'enabled': True,
                'url': 'http://nd',
                'username': 'u',
                'password': 'p',
            },
        },
        library,
    )
    assert synced == [('Road Trip', 2)]


def _force_new(new_tracks):
    """A `_split_new_tracks` stand-in that reports ``new_tracks`` as new
    and every already-recorded track as resolved."""

    async def _split(*args):
        known, resolved = args[5], args[6]
        for tid, filename in known.items():
            if filename:
                resolved[tid] = filename
        return list(new_tracks), 0

    return _split


def test_sweep_without_library_stores_keeps_working(monkeypatch, tmp_path):
    downloader = _Downloader(tmp_path / 'downloads')

    count, _db, _pl = _sweep(
        monkeypatch, tmp_path, downloader, {'generate_m3u': False}, None
    )

    assert count == 2
