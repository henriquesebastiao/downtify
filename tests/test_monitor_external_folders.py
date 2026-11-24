"""A watched playlist keeps the songs it linked from an Existing music
folder: its M3U, its Library playlist and its Navidrome rows (issue #560).

The setup the issue asks for: the music library is an Existing music
folder, new downloads land in the downloads folder to be tidied up, and
a watch links what the library already has instead of downloading it
again. Before the fix those linked songs were dropped from the playlist,
since only the downloads and slskd folders were looked at.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from downtify import m3u, monitor
from downtify.downloader import Downloader
from downtify.library_paths import extra_dir_id

PLAYLIST_NAME = 'Ingest Mix'
TRACKS = [
    {'song_id': 'a', 'name': 'Fresh Song', 'artists': ['New Artist']},
    {'song_id': 'b', 'name': 'Kept Song', 'artists': ['Old Artist']},
]


def _watch() -> monitor.MonitoredPlaylist:
    return monitor.MonitoredPlaylist(
        id=1,
        spotify_id='pl560',
        name=PLAYLIST_NAME,
        url='https://open.spotify.com/playlist/pl560',
        interval_minutes=60,
        enabled=True,
        last_checked='2026-11-01T00:00:00+00:00',
        last_track_count=2,
        created_at='2026-01-01T00:00:00+00:00',
    )


def _layout(tmp_path: Path) -> tuple[Downloader, dict[str, Any], dict]:
    downloads = tmp_path / 'downloads'
    library = tmp_path / 'music'
    (downloads / PLAYLIST_NAME).mkdir(parents=True)
    (library / 'Old Artist').mkdir(parents=True)
    (downloads / PLAYLIST_NAME / 'Fresh Song.mp3').write_bytes(b'audio')
    (library / 'Old Artist' / 'Kept Song.mp3').write_bytes(b'audio')
    known = {
        'a': f'{PLAYLIST_NAME}/Fresh Song.mp3',
        'b': f'ext/{extra_dir_id(library)}/Old Artist/Kept Song.mp3',
    }
    settings = {'external_library': {'folders': [str(library)]}}
    return (
        Downloader(download_dir=downloads, audio_format='mp3'),
        settings,
        known,
    )


def _m3u_tracks(dl: Downloader, path: Path, settings: dict) -> list[str]:
    extras = monitor.extra_dirs_from_settings(
        settings, Path(dl.download_dir), None
    )
    return m3u.read_m3u_tracks(path, Path(dl.download_dir), None, extras)


def test_m3u_keeps_songs_linked_from_an_existing_music_folder(tmp_path):
    dl, settings, known = _layout(tmp_path)

    path = monitor._regenerate_m3u(
        _watch(), TRACKS, dl, None, known, settings=settings
    )

    assert path is not None
    assert _m3u_tracks(dl, path, settings) == [known['a'], known['b']]
    # Relative to the M3U, like every other line, so Jellyfin and
    # Navidrome mounting the same folders read it too.
    assert '../../music/Old Artist/Kept Song.mp3' in path.read_text()


def test_m3u_written_during_a_sweep_keeps_them_too(tmp_path):
    dl, settings, known = _layout(tmp_path)

    path = monitor._regenerate_m3u(
        _watch(), TRACKS, dl, dict(known), settings=settings
    )

    assert path is not None
    assert _m3u_tracks(dl, path, settings) == [known['a'], known['b']]


def test_without_the_folder_list_only_downloads_count(tmp_path):
    dl, settings, known = _layout(tmp_path)

    path = monitor._regenerate_m3u(_watch(), TRACKS, dl, None, known)

    assert path is not None
    assert _m3u_tracks(dl, path, settings) == [known['a']]


class _Catalog:
    def __init__(self) -> None:
        self.rows: list[tuple[dict[str, Any], str, Path]] = []

    def replace_playlist_tracks(self, name, rows, **_kwargs) -> None:
        assert name == PLAYLIST_NAME
        self.rows = list(rows)


def test_library_playlist_keeps_them(tmp_path):
    dl, settings, known = _layout(tmp_path)
    catalog = _Catalog()

    monitor._sync_library_playlist(
        _watch(),
        TRACKS,
        dl,
        known,
        monitor.LibraryStores(playlist_catalog=catalog),
        {**settings, 'sync_navidrome': False},
    )

    assert [filename for _song, filename, _full in catalog.rows] == [
        known['a'],
        known['b'],
    ]
    assert (
        catalog.rows[1][2]
        == (tmp_path / 'music' / 'Old Artist' / 'Kept Song.mp3').resolve()
    )
