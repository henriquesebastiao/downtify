"""A watched playlist renamed on its service follows: the watch, its M3U
and cover, its catalog rows, hidden songs, sharing and Navidrome."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from downtify import monitor, navidrome, playlist_names
from downtify.monitor import LibraryStores, PlaylistMonitorDB
from downtify.playlist_catalog import PlaylistCatalog
from downtify.playlist_hidden import PlaylistHiddenSongs
from downtify.playlist_shares import PlaylistShares
from downtify.track_index import TrackIndex

TRACK_A = '4uLU6hMCjMI75M1A2tKUQC'
TRACK_B = '7ouMYWpwJ422jRcDASZB7P'
TRACK_C = '1301WleyT98MSxVHPZCA6M'
PLAYLIST_ID = '37i9dQZF1DXcBWIGoYBM5M'
OLD = 'HTTYD 1, 2, 3, Live Action'
NEW = 'HTTYD 1, 2, 3, Live Action 1, 2'


class _Downloader:
    organize_by_artist = False
    organize_by_album = False
    slskd_settings: dict = {}
    overwrite_existing_files = True

    def __init__(self, download_dir: Path):
        self.download_dir = download_dir
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


@pytest.fixture(autouse=True)
def _fresh_names():
    playlist_names.forget_all()
    yield
    playlist_names.forget_all()


class _Source:
    """What Spotify answers: songs, and the playlist's current name."""

    def __init__(self, monkeypatch, name: str):
        self.name = name
        self.songs = [
            {'song_id': TRACK_A, 'name': 'Alpha', 'artists': ['Artist']},
            {'song_id': TRACK_B, 'name': 'Beta', 'artists': ['Artist']},
        ]

        def tracks(playlist_id):
            playlist_names.remember('spotify', playlist_id, self.name)
            return [dict(song) for song in self.songs]

        monkeypatch.setattr(monitor.spotify, 'playlist_tracks_from_id', tracks)
        monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda _id: {})


def _check(db, playlist, downloader, library, settings=None):
    messages: list[dict] = []

    async def broadcast(message):
        messages.append(message)

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(
            monitor.check_playlist(
                playlist,
                db,
                downloader,
                broadcast,
                loop,
                settings if settings is not None else {},
                library,
            )
        )
    finally:
        loop.close()
    return messages


def _setup(tmp_path, monkeypatch):
    source = _Source(monkeypatch, OLD)
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist(
        PLAYLIST_ID, OLD, f'https://open.spotify.com/playlist/{PLAYLIST_ID}'
    )
    store = tmp_path / 'library.db'
    library = LibraryStores(
        track_index=TrackIndex(store),
        playlist_catalog=PlaylistCatalog(store),
        playlist_hidden=PlaylistHiddenSongs(store),
        playlist_shares=PlaylistShares(store),
    )
    downloader = _Downloader(tmp_path / 'downloads')
    _check(db, watch, downloader, library)
    return source, db, library, downloader


def test_rename_on_spotify_renames_watch_m3u_cover_and_stores(
    tmp_path, monkeypatch
):
    source, db, library, downloader = _setup(tmp_path, monkeypatch)
    root = downloader.download_dir
    old_m3u = root / OLD / f'{OLD}.m3u'
    assert old_m3u.is_file()
    old_m3u.with_suffix('.jpg').write_bytes(b'cover')
    library.playlist_hidden.hide(OLD, track_id=TRACK_C, label='Gamma')
    library.playlist_shares.set_visibility(OLD, 'public', [])

    source.name = NEW
    source.songs.append({
        'song_id': TRACK_C,
        'name': 'Gamma',
        'artists': ['Artist'],
    })
    messages = _check(db, db.list_playlists()[0], downloader, library)

    watch = db.list_playlists()[0]
    assert watch.name == NEW
    # Nothing downloaded again: the old songs stay where they are.
    assert downloader.downloaded == [TRACK_A, TRACK_B]
    new_m3u = root / NEW / f'{NEW}.m3u'
    assert not old_m3u.exists()
    assert not old_m3u.with_suffix('.jpg').exists()
    assert new_m3u.with_suffix('.jpg').read_bytes() == b'cover'
    lines = new_m3u.read_text(encoding='utf-8').splitlines()
    assert f'../{OLD}/Alpha.mp3' in lines
    assert f'../{OLD}/Beta.mp3' in lines
    catalog = library.playlist_catalog
    assert OLD not in catalog.list_playlist_names()
    assert [r['filename'] for r in catalog.list_tracks(NEW)] == [
        f'{OLD}/Alpha.mp3',
        f'{OLD}/Beta.mp3',
    ]
    assert catalog.spotify_id_for_playlist(NEW) == PLAYLIST_ID
    # Gamma stays hidden under the new name.
    assert library.playlist_hidden.counts() == {NEW.casefold(): 1}
    assert library.playlist_shares.visibility(NEW) == 'public'
    assert {'type': 'playlists_changed'} in messages


def test_new_songs_after_a_rename_go_to_the_new_folder(tmp_path, monkeypatch):
    source, db, library, downloader = _setup(tmp_path, monkeypatch)
    source.name = NEW
    _check(db, db.list_playlists()[0], downloader, library)
    source.songs.append({
        'song_id': TRACK_C,
        'name': 'Gamma',
        'artists': ['Artist'],
    })

    _check(db, db.list_playlists()[0], downloader, library)

    assert (downloader.download_dir / NEW / 'Gamma.mp3').is_file()
    lines = (
        (downloader.download_dir / NEW / f'{NEW}.m3u')
        .read_text(encoding='utf-8')
        .splitlines()
    )
    assert 'Gamma.mp3' in lines
    assert f'../{OLD}/Alpha.mp3' in lines


def test_a_name_given_in_downtify_is_kept(tmp_path, monkeypatch):
    source, db, library, downloader = _setup(tmp_path, monkeypatch)
    library.named_by_user = lambda name: name == OLD
    source.name = NEW

    _check(db, db.list_playlists()[0], downloader, library)

    assert db.list_playlists()[0].name == OLD
    assert (downloader.download_dir / OLD / f'{OLD}.m3u').is_file()
    assert not (downloader.download_dir / NEW).exists()


def test_never_takes_the_name_of_another_playlist(tmp_path, monkeypatch):
    source, db, library, downloader = _setup(tmp_path, monkeypatch)
    library.playlist_catalog.ensure_playlist(NEW)
    source.name = NEW

    _check(db, db.list_playlists()[0], downloader, library)

    assert db.list_playlists()[0].name == OLD
    assert [r['filename'] for r in library.playlist_catalog.list_tracks(OLD)]


def test_never_takes_the_name_of_an_m3u_on_disk(tmp_path, monkeypatch):
    source, db, library, downloader = _setup(tmp_path, monkeypatch)
    other = downloader.download_dir / 'Playlists' / f'{NEW}.m3u'
    other.parent.mkdir(parents=True)
    other.write_text('#EXTM3U\n', encoding='utf-8')
    source.name = NEW

    _check(db, db.list_playlists()[0], downloader, library)

    assert db.list_playlists()[0].name == OLD
    assert other.read_text(encoding='utf-8') == '#EXTM3U\n'


@pytest.mark.parametrize('name', ['', PLAYLIST_ID, OLD])
def test_no_name_or_the_same_name_changes_nothing(tmp_path, monkeypatch, name):
    source, db, library, downloader = _setup(tmp_path, monkeypatch)
    source.name = name

    messages = _check(db, db.list_playlists()[0], downloader, library)

    assert db.list_playlists()[0].name == OLD
    assert {'type': 'playlists_changed'} not in messages


def test_navidrome_follows_the_rename(tmp_path, monkeypatch):
    source, db, library, downloader = _setup(tmp_path, monkeypatch)
    calls: list[tuple] = []
    monkeypatch.setattr(
        monitor,
        'follow_playlist_rename',
        lambda old, new, settings, old_m3u='': calls.append((
            'follow',
            old,
            new,
            old_m3u,
        )),
    )
    monkeypatch.setattr(
        monitor,
        'sync_playlist_to_navidrome',
        lambda name, songs, settings, **kw: calls.append((
            'sync',
            name,
            len(songs),
            kw.get('trigger_scan'),
        )),
    )
    source.name = NEW

    _check(
        db,
        db.list_playlists()[0],
        downloader,
        library,
        {'navidrome': {'enabled': True}},
    )

    assert calls == [
        ('follow', OLD, NEW, f'{OLD}/{OLD}.m3u'),
        ('sync', NEW, 2, True),
    ]


def test_case_only_change_keeps_one_m3u(tmp_path, monkeypatch):
    source, db, library, downloader = _setup(tmp_path, monkeypatch)
    source.name = OLD.upper()

    _check(db, db.list_playlists()[0], downloader, library)

    assert db.list_playlists()[0].name == OLD.upper()
    m3us = list(downloader.download_dir.rglob('*.m3u'))
    assert len(m3us) == 1
    assert 'Alpha.mp3' in m3us[0].read_text(encoding='utf-8')


def test_deezer_name_comes_with_its_songs(monkeypatch):
    monkeypatch.setattr(
        monitor.deezer,
        'playlist_info_and_tracks',
        lambda pid: ('Chart', [{'song_id': 'deezer-1'}]),
    )
    assert monitor.fetch_playlist_named('deezer', 'deezer:playlist:9') == (
        'Chart',
        [{'song_id': 'deezer-1'}],
    )


def test_remember_skips_names_that_are_just_the_id():
    playlist_names.remember('spotify', 'abc', 'abc')
    playlist_names.remember('spotify', 'def', '  ')
    playlist_names.remember('youtube_music', 'ghi', ' Mix ')
    assert not playlist_names.seen('spotify', 'abc')
    assert not playlist_names.seen('spotify', 'def')
    assert playlist_names.seen('youtube_music', 'ghi') == 'Mix'
    assert not playlist_names.seen('spotify', 'ghi')


class _Navidrome:
    def __init__(self, cfg):
        self.username = 'downtify'
        self.calls: list[tuple] = []
        _Navidrome.last = self

    @staticmethod
    def configured():
        return True

    @staticmethod
    def ping():
        return True

    @staticmethod
    def list_playlists():
        return [
            {
                'id': 'api-1',
                'name': OLD,
                'owner': 'downtify',
                'comment': 'Synced from Spotify via Downtify',
            },
            {'id': 'mine', 'name': OLD, 'owner': 'someone', 'comment': ''},
        ]

    @staticmethod
    def native_playlists():
        return [
            {'id': 'imp-1', 'name': OLD, 'path': f'/music/{OLD}/{OLD}.m3u'},
            {'id': 'imp-2', 'name': OLD, 'path': f'/music/Other/{OLD}.m3u'},
        ]

    def rename_playlist(self, pid, name):
        self.calls.append(('rename', pid, name))

    def delete_playlist(self, pid, *, admin=False):
        self.calls.append(('delete', pid, admin))


def test_follow_playlist_rename_renames_own_copy_and_drops_old_import(
    monkeypatch,
):
    monkeypatch.setattr(navidrome, 'NavidromeClient', _Navidrome)
    settings = {
        'navidrome': {
            'enabled': True,
            'url': 'http://nd',
            'username': 'downtify',
            'password': 'placeholder',
        }
    }

    done = navidrome.follow_playlist_rename(
        OLD, NEW, settings, old_m3u=f'{OLD}/{OLD}.m3u'
    )

    assert done == {'renamed': 1, 'removed': 1}
    assert _Navidrome.last.calls == [
        ('rename', 'api-1', NEW),
        ('delete', 'imp-1', True),
    ]


def test_catalog_rename_refuses_a_taken_name(tmp_path):
    catalog = PlaylistCatalog(tmp_path / 'library.db')
    catalog.ensure_playlist('A', spotify_id='sid', user_id=3)
    catalog.ensure_playlist('B')
    assert catalog.rename_playlist('A', 'B') is False
    assert catalog.rename_playlist('A', 'C') is True
    assert catalog.list_playlist_names() == ['B', 'C']
    assert catalog.spotify_id_for_playlist('C') == 'sid'
    assert catalog.playlist_owner_map()['C'] == 3
