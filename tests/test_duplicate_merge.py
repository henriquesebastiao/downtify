"""Merging duplicate songs (downtify/duplicate_merge.py, the Doctor's
duplicate review): every reference moves to the copy kept, so nothing is
missing afterwards and nothing is downloaded again (issue #582).

Real stores on temporary databases; only downloads are faked.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from downtify import doctor_routes, m3u, monitor
from downtify.deemix_upgrade_store import AudioReplacementStore
from downtify.duplicate_merge import (
    KeptApart,
    MergeError,
    MergeStores,
    finish_merge,
    leftover_references,
    plan_merge,
    relink_duplicates,
)
from downtify.file_providers import FileProviders
from downtify.library_cache_keys import file_content_key
from downtify.library_catalog import LibraryContext
from downtify.library_delete import delete_library_file
from downtify.library_sync import LibrarySync
from downtify.library_usage import duplicates
from downtify.library_visibility import LibraryVisibility
from downtify.likes import LikedTracks
from downtify.monitor import LibraryStores, PlaylistMonitorDB
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex
from downtify.track_owners import TrackOwners

ONE_DANCE = '1zi7xx7UVEFkmKfv06H8x0'
OURS = 'Drake/Drake, WizKid, Kyla - One Dance.mp3'
YOURS = 'Drake/Drake - One Dance.mp3'


@pytest.fixture
def lib(tmp_path: Path) -> SimpleNamespace:
    root = tmp_path / 'downloads'
    (root / 'Drake').mkdir(parents=True)
    db = tmp_path / 'library.db'
    stores = SimpleNamespace(
        root=root,
        ctx=LibraryContext(download_dir=root),
        track_index=TrackIndex(db),
        catalog=PlaylistCatalog(db),
        likes=LikedTracks(db),
        owners=TrackOwners(db),
        visibility=LibraryVisibility(db),
        sync=LibrarySync(db),
        providers=FileProviders(tmp_path / 'providers.db'),
        replacements=AudioReplacementStore(db),
        monitor=PlaylistMonitorDB(tmp_path / 'monitor.db'),
    )
    stores.merge = MergeStores(
        ctx=stores.ctx,
        replacements=stores.replacements,
        monitor_db=stores.monitor,
        library_visibility=stores.visibility,
        file_providers=stores.providers,
        playlist_catalog=stores.catalog,
    )
    return stores


def _file(lib, name: str, data: bytes) -> Path:
    path = lib.root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _merge(lib, keep: str, extras: list[str]) -> list[str]:
    """What the Doctor does, without the music trash."""

    plan = relink_duplicates(plan_merge(keep, extras, lib.ctx), lib.merge)
    removed = [
        name
        for name in extras
        if delete_library_file(
            name,
            lib.ctx,
            playlist_catalog=lib.catalog,
            track_index=lib.track_index,
        )['deleted']
    ]
    finish_merge(plan, lib.merge, removed)
    assert leftover_references(plan, lib.merge) == []
    return sorted(plan.playlists)


# --- the bug -----------------------------------------------------------------


class _Downloader:
    organize_by_artist = True
    organize_by_album = False
    overwrite_existing_files = False
    slskd_settings: dict = {}

    def __init__(self, root: Path):
        self.download_dir = root
        self.downloads: list[str] = []

    def existing_filename_for(self, song, subdir=None):
        return OURS if (self.download_dir / OURS).exists() else None

    def download(self, song, cb, subdir=None):
        path = self.download_dir / OURS
        if path.exists():
            return OURS
        self.downloads.append(song['song_id'])
        path.write_bytes(b'YOUTUBE PARODY')
        return OURS


def _sweep(monkeypatch, lib, watch, downloader):
    monkeypatch.setattr(
        monitor.spotify,
        'playlist_tracks_from_id',
        lambda _id: [
            {
                'song_id': ONE_DANCE,
                'name': 'One Dance',
                'artists': ['Drake', 'WizKid', 'Kyla'],
            }
        ],
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda _id: {})

    async def broadcast(_m):
        return None

    library = LibraryStores(
        track_index=lib.track_index, playlist_catalog=lib.catalog
    )
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(
            monitor.check_playlist(
                lib.monitor.get_playlist(watch.id),
                lib.monitor,
                downloader,
                broadcast,
                loop,
                {'generate_m3u': False},
                library,
            )
        )
    finally:
        loop.close()


def test_a_merged_duplicate_is_not_downloaded_again(monkeypatch, lib):
    # Issue #582: deleting one copy of a duplicate brought it back. A
    # merge moves the watch's record to the copy kept instead.
    dl = _Downloader(lib.root)
    chill = lib.monitor.add_playlist('37i9dQZF1E4chill', 'Chill Mix', 'url')
    _sweep(monkeypatch, lib, chill, dl)
    assert dl.downloads == [ONE_DANCE]
    _file(lib, YOURS, b'REAL VERSION FROM NICOTINE+')

    _merge(lib, YOURS, [OURS])
    asyncio.run(monitor.reconcile_downloaded_tracks(lib.monitor, dl))
    _sweep(monkeypatch, lib, chill, dl)

    assert dl.downloads == [ONE_DANCE], 'downloaded again'
    assert not (lib.root / OURS).exists()
    assert (lib.root / YOURS).read_bytes() == b'REAL VERSION FROM NICOTINE+'
    assert lib.monitor.get_track_filenames(chill.id)[ONE_DANCE] == YOURS
    assert lib.track_index.lookup(ONE_DANCE) == YOURS


# --- every reference ---------------------------------------------------------


def test_merge_moves_every_reference(lib):
    extra = _file(lib, OURS, b'parody')
    _file(lib, YOURS, b'real one')
    extra_key = file_content_key(extra)
    lib.track_index.register(ONE_DANCE, OURS, full_path=extra)
    lib.catalog.upsert_track(
        'Chill Mix', {'song_id': ONE_DANCE}, OURS, extra, track_order=4
    )
    for user in (1, 2):
        lib.likes.like(
            OURS, content_key=extra_key, title='One Dance', user_id=user
        )
        lib.owners.add(extra_key, user, OURS)
    _file(
        lib,
        'Chill Mix.m3u',
        f'#EXTM3U\n#EXTINF:174,One Dance\n{OURS}\n'.encode(),
    )
    _file(
        lib,
        'Mine.m3u',
        f'#EXTM3U\n{m3u.MANUAL_M3U_MARKER}\n{OURS}\n'.encode(),
    )
    watch = lib.monitor.add_playlist('37i9dQZF1E4chill', 'Chill Mix', 'url')
    lib.monitor.mark_track_downloaded(watch.id, ONE_DANCE, OURS)
    artist = lib.monitor.add_playlist(
        'UCdrake', 'Drake', 'url', 60, monitor.KIND_ARTIST
    )
    lib.monitor.releases.record(artist.id, 'VIEWS', 12, 'yt-1', OURS)

    playlists = _merge(lib, YOURS, [OURS])

    assert {'Chill Mix', 'Mine'} <= set(playlists)
    assert lib.track_index.lookup(ONE_DANCE) == YOURS
    assert [r['filename'] for r in lib.catalog.list_tracks('Chill Mix')] == [
        YOURS
    ]
    with lib.replacements.connect() as db:
        likes = db.execute(
            'SELECT user_id, stored_path FROM liked_tracks ORDER BY user_id'
        ).fetchall()
        owners = db.execute(
            'SELECT user_id, stored_path FROM track_owners ORDER BY user_id'
        ).fetchall()
    assert [tuple(r) for r in likes] == [(1, YOURS), (2, YOURS)]
    assert [tuple(r) for r in owners] == [(1, YOURS), (2, YOURS)]
    assert YOURS in (lib.root / 'Chill Mix.m3u').read_text(encoding='utf-8')
    assert YOURS in (lib.root / 'Mine.m3u').read_text(encoding='utf-8')
    assert lib.monitor.get_track_filenames(watch.id)[ONE_DANCE] == YOURS
    assert lib.monitor.releases.tracks(artist.id, 'VIEWS') == {
        (12, 'yt-1'): YOURS
    }
    assert not extra.exists()
    assert lib.replacements.get(OURS)['state'] == 'removed'


def test_a_manual_playlist_with_both_copies_lists_the_song_once(lib):
    _file(lib, OURS, b'parody')
    _file(lib, YOURS, b'real one')
    _file(
        lib,
        'Mine.m3u',
        f'#EXTM3U\n{m3u.MANUAL_M3U_MARKER}\n{YOURS}\n{OURS}\n'.encode(),
    )

    _merge(lib, YOURS, [OURS])

    tracks = m3u.read_m3u_tracks(
        lib.root / 'Mine.m3u', lib.root, None, (), keep_missing=True
    )
    assert tracks == [YOURS]


def test_copies_sharing_a_key_keep_the_kept_files_records(lib):
    # A file's key is its name and size: exact copies in two folders
    # share it. Forgetting the removed copy mustn't forget the kept one.
    kept = _file(lib, 'Drake/One Dance.mp3', b'same bytes')
    _file(lib, 'Old/One Dance.mp3', b'same bytes')
    key = file_content_key(kept)
    lib.owners.add(key, 1, 'Drake/One Dance.mp3')
    lib.providers.record(key, 'Drake/One Dance.mp3', 'slskd')

    _merge(lib, 'Drake/One Dance.mp3', ['Old/One Dance.mp3'])

    assert lib.owners.owners(key) == [1]
    assert lib.providers.lookup({'Drake/One Dance.mp3': key}) == {
        'Drake/One Dance.mp3': 'slskd'
    }


def test_a_hidden_extra_copy_does_not_hide_the_kept_one(lib):
    extra = _file(lib, OURS, b'parody')
    _file(lib, YOURS, b'real one')
    lib.visibility.hide(
        'track', file_content_key(extra), path=OURS, label='One Dance'
    )

    _merge(lib, YOURS, [OURS])

    assert not lib.visibility.rules()


def test_plan_merge_refuses_before_changing_anything(lib):
    _file(lib, YOURS, b'real one')
    with pytest.raises(MergeError) as missing:
        plan_merge(YOURS, [OURS], lib.ctx)
    assert missing.value.code == 'dedupe_missing'
    with pytest.raises(MergeError):
        plan_merge(YOURS, [YOURS], lib.ctx)
    with pytest.raises(MergeError):
        plan_merge(YOURS, [], lib.ctx)
    assert (lib.root / YOURS).exists()


# --- keep both ---------------------------------------------------------------


def test_kept_apart_settles_a_group_until_a_new_copy_turns_up(tmp_path):
    kept = KeptApart(tmp_path / 'duplicates.db')
    assert kept.keep(['a.mp3', 'b.mp3']) == 1

    assert kept.settled(['b.mp3', 'a.mp3'])
    assert not kept.settled(['a.mp3', 'b.mp3', 'c.mp3'])
    assert not kept.settled(['a.mp3'])

    kept.forget_files(['b.mp3'])
    assert not kept.settled(['a.mp3', 'b.mp3'])
    kept.keep(['a.mp3', 'b.mp3', 'c.mp3'])
    assert kept.forget() == 3


# --- the Doctor's review -----------------------------------------------------


def _entry(file, title, size, duration=200.0, artist='Drake'):
    return {
        'file': file,
        'title': title,
        'artist': artist,
        'album': 'Views',
        'duration': duration,
        'size': size,
    }


def test_review_lists_every_group_with_each_files_tags_and_playlists(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        doctor_routes, '_kept', KeptApart(tmp_path / 'duplicates.db')
    )
    monkeypatch.setattr(doctor_routes, '_state', {})
    entries = [
        _entry('a/One Dance.mp3', 'One Dance', 900),
        _entry('b/One Dance.mp3', 'One Dance', 800, duration=201),
        _entry('a/Hotline Bling.mp3', 'Hotline Bling', 700),
        _entry('b/Hotline Bling.mp3', 'Hotline Bling', 600),
    ]
    found = duplicates(entries, {}, limit=None)['examples']
    infos = [
        doctor_routes.M3UInfo(
            path='Chill Mix.m3u',
            name='Chill Mix',
            manual=False,
            entries=['b/One Dance.mp3'],
            lines=1,
            cover=False,
            expected=True,
        )
    ]
    doctor_routes._kept_apart().keep([
        'a/Hotline Bling.mp3',
        'b/Hotline Bling.mp3',
    ])

    review = doctor_routes._duplicate_review(found, infos)

    assert review['kept_apart'] == 1
    assert len(review['groups']) == 1
    files = {f['file']: f for f in review['groups'][0]['files']}
    assert files['b/One Dance.mp3']['playlists'] == ['Chill Mix']
    assert files['b/One Dance.mp3']['duration'] == 201
    assert files['a/One Dance.mp3']['title'] == 'One Dance'
    doctor_routes._same_group(['a/One Dance.mp3', 'b/One Dance.mp3'])
    with pytest.raises(doctor_routes.HTTPException):
        doctor_routes._same_group(['a/One Dance.mp3', 'a/Hotline Bling.mp3'])


def test_settling_the_review_drops_merged_files_and_kept_groups(monkeypatch):
    group = {
        'kind': 'exact',
        'bytes': 1,
        'files': [
            {'file': 'a.mp3', 'bytes': 2},
            {'file': 'b.mp3', 'bytes': 1},
        ],
    }
    other = {
        'kind': 'likely',
        'bytes': 3,
        'files': [
            {'file': 'c.mp3', 'bytes': 3},
            {'file': 'd.mp3', 'bytes': 3},
        ],
    }
    last = {
        'health': {
            'result': {
                'duplicates': {
                    'groups': [group, other],
                    'totals': {},
                    'kept_apart': 0,
                }
            }
        }
    }
    monkeypatch.setattr(doctor_routes, '_last', last)
    monkeypatch.setattr(doctor_routes, '_state', {'duplicates': {}})

    doctor_routes._settle_review(['b.mp3'], [])
    doctor_routes._settle_review([], ['c.mp3', 'd.mp3'])

    review = last['health']['result']['duplicates']
    assert review['groups'] == []
    assert review['kept_apart'] == 1
    assert review['totals']['exact']['groups'] == 0
