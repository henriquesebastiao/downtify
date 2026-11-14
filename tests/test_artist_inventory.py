"""What the library has of an artist's releases: kept tracklists, the
"Check what I have" inventory (monitor.take_inventory) and the counts
on the watch's page (artist_catalogue.library_have, GET
.../releases/tracks, POST .../releases/inventory).

All offline: the catalogues are faked.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from downtify import api, artist_catalogue, monitor
from downtify.library_songs import LibrarySongs
from tests.test_artist_catalogue import _by_name, _catalogues, _view
from tests.test_artist_watch_deezer import _release, _sweep, _watch
from tests.test_artist_watch_duplicates import _FakeDownloader
from tests.test_monitor_edit import _Req

ON = {'artist_watch_deezer': True, 'artist_watch_musicbrainz': True}


def _library(*songs):
    """The library listing rows for ``(artist, title, seconds)``."""

    return [
        {
            'file': f'{artist}/{artist} - {title}.mp3',
            'artist': artist,
            'title': title,
            'duration': seconds,
        }
        for artist, title, seconds in songs
    ]


def _view_with(db, watch, rows):
    watch = db.get_playlist(watch.id)
    have = artist_catalogue.library_have(
        db.catalogue.tracks(watch.id),
        LibrarySongs(rows),
        db.releases.counts(watch.id),
    )
    return artist_catalogue.catalogue_view(
        db.catalogue.rows(watch.id),
        have=have,
        seen=db.catalogue.seen(watch.id),
        types=set(watch.release_types.split(',')),
        kinds=artist_catalogue.watch_kinds(watch, ON),
    )


# ── Kept tracklists ─────────────────────────────────────────────────────


def test_tracklists_are_kept_and_follow_the_watch(tmp_path):
    db, watch = _watch(tmp_path)
    db.catalogue.record(watch.id, [_release('deezer:1', 'Views')])
    db.catalogue.store_tracks(
        watch.id,
        'deezer:1',
        [
            {'name': 'Hotline Bling', 'artists': ['Drake'], 'duration': 267},
            {
                'name': 'One Dance',
                'artists': ['Drake', 'Wizkid'],
                'duration': 174,
            },
        ],
    )

    tracks = db.catalogue.tracks(watch.id)
    assert [t['name'] for t in tracks['deezer:1']] == [
        'Hotline Bling',
        'One Dance',
    ]
    assert tracks['deezer:1'][1] == {
        'position': 2,
        'name': 'One Dance',
        'artists': ['Drake', 'Wizkid'],
        'duration': 174,
    }
    assert db.catalogue.rows(watch.id)[0]['track_total'] == 2

    db.retarget_playlist(watch.id, 'UCother', 'Other', 'url2')
    assert db.catalogue.tracks(watch.id) == {}


def test_a_sweep_keeps_the_tracklists_it_reads(monkeypatch, tmp_path):
    _catalogues(monkeypatch)
    db, watch = _watch(tmp_path)
    _sweep(db, watch, _FakeDownloader(tmp_path), ON)

    tracks = db.catalogue.tracks(watch.id)
    assert [t['name'] for t in tracks['deezer:10']] == ['TSU', 'Way 2 Sexy']
    assert 'mb:rfi' in tracks


# ── "Check what I have" ─────────────────────────────────────────────────


def test_the_inventory_reads_each_release_once_and_downloads_nothing(
    monkeypatch, tmp_path
):
    mb = _catalogues(monkeypatch)
    db, watch = _watch(tmp_path, new_only=True)
    dl = _FakeDownloader(tmp_path)
    _sweep(db, watch, dl, ON)  # the baseline: everything listed, skipped
    assert db.catalogue.tracks(watch.id) == {}
    read = []
    real = monitor._release_tracks

    def tracks(album, artist):
        read.append(album['album_id'])
        return real(album, artist)

    monkeypatch.setattr(monitor, '_release_tracks', tracks)
    seen = []

    result = monitor.take_inventory(
        db.get_playlist(watch.id),
        db,
        progress=lambda done, total: seen.append((done, total)),
    )

    # Certified Lover Boy is on YouTube Music and Deezer: read once, from
    # Deezer; every release is read; nothing is downloaded.
    assert 'CLB' not in read
    assert sorted(read) == sorted([
        'deezer:10',
        'deezer:20',
        'deezer:30',
        'mb:rfi',
        'mb:o2',
    ])
    assert result == {'checked': 5, 'failed': 0, 'total': 5}
    assert seen[-1] == (5, 5)
    assert dl.calls == []
    assert set(mb.track_calls) == {'rfi', 'o2'}
    named = _by_name(_view(db, watch))
    assert named['MELTDOWN (feat. Drake)']['state'] == 'not_own'

    # A second check has nothing left to read.
    read.clear()
    assert monitor.take_inventory(db.get_playlist(watch.id), db)['total'] == 0
    assert read == []


def test_a_release_a_catalogue_fails_on_is_left_for_later(
    monkeypatch, tmp_path
):
    _catalogues(monkeypatch)
    db, watch = _watch(tmp_path, new_only=True)
    _sweep(db, watch, _FakeDownloader(tmp_path), ON)
    real = monitor._release_tracks

    def flaky(album, artist):
        if album['album_id'] == 'mb:o2':
            raise RuntimeError('busy')
        return real(album, artist)

    monkeypatch.setattr(monitor, '_release_tracks', flaky)
    result = monitor.take_inventory(db.get_playlist(watch.id), db)

    assert result == {'checked': 4, 'failed': 1, 'total': 5}
    assert 'mb:o2' not in db.catalogue.tracks(watch.id)
    stopped = monitor.take_inventory(
        db.get_playlist(watch.id), db, stop=lambda: True
    )
    assert stopped == {'checked': 0, 'failed': 0, 'total': 1}


def test_an_album_owned_before_the_watch_shows_as_complete(
    monkeypatch, tmp_path
):
    _catalogues(monkeypatch)
    db, watch = _watch(tmp_path, new_only=True)
    _sweep(db, watch, _FakeDownloader(tmp_path), ON)
    monitor.take_inventory(db.get_playlist(watch.id), db)
    library = _library(
        ('Drake', 'TSU', 308),
        ('Drake', 'Way 2 Sexy', 258),  # a second off: the same song
        ('Drake', 'Do What You Do', 290),  # another recording (length)
    )

    named = _by_name(_view_with(db, watch, library))

    clb = named['Certified Lover Boy']
    assert (clb['state'], clb['have'], clb['total']) == ('complete', 2, 2)
    # Owned, but the watch still doesn't download it: its switch is off.
    assert clb['wanted'] is False
    rfi = named['Room for Improvement']
    assert (rfi['state'], rfi['have'], rfi['total']) == ('skipped', 0, 1)
    # Nothing owned of a watched release still to come: its switch is on.
    db.catalogue.set_choice(watch.id, ['mb:rfi'], 'on')
    assert _by_name(_view_with(db, watch, library))['Room for Improvement'][
        'wanted'
    ]


def test_the_tracks_of_a_release_say_which_the_library_has():
    rows = [
        {'position': 1, 'name': 'TSU', 'artists': ['Drake'], 'duration': 308},
        {
            'position': 2,
            'name': 'Way 2 Sexy',
            'artists': ['Drake'],
            'duration': 257,
        },
        {
            'position': 3,
            'name': 'Fair Trade',
            'artists': ['Drake'],
            'duration': 291,
        },
    ]
    listed = artist_catalogue.track_list(
        rows,
        LibrarySongs(_library(('Drake', 'TSU', 308))),
        {2: 'Drake/Drake - Way 2 Sexy (CLB).mp3'},
    )
    assert [t['file'] for t in listed] == [
        'Drake/Drake - TSU.mp3',
        'Drake/Drake - Way 2 Sexy (CLB).mp3',
        None,
    ]


# ── Over the API ────────────────────────────────────────────────────────


def _api(monkeypatch, tmp_path, library=()):
    _catalogues(monkeypatch)
    db, watch = _watch(tmp_path, new_only=True)
    _sweep(db, watch, _FakeDownloader(tmp_path), ON)
    monkeypatch.setattr(api.state, 'monitor_db', db)
    monkeypatch.setattr(api.state, 'downloader', None)
    monkeypatch.setattr(api.state, 'settings', dict(ON))
    monkeypatch.setattr(api, '_inventories', {})
    monkeypatch.setattr(
        api, '_library_songs', lambda: LibrarySongs(_library(*library))
    )
    spawned = []
    monkeypatch.setattr(
        api, 'spawn_task', lambda coro, name=None: spawned.append(coro)
    )
    return db, watch, spawned


def test_checking_over_the_api(monkeypatch, tmp_path):
    db, watch, spawned = _api(
        monkeypatch,
        tmp_path,
        [('Drake', 'TSU', 308), ('Drake', 'Way 2 Sexy', 257)],
    )

    started = asyncio.run(api.check_artist_watch_inventory(watch.id, _Req({})))
    assert started['inventory']['running'] is True
    # While it runs, asking again returns the running check.
    again = asyncio.run(api.check_artist_watch_inventory(watch.id, _Req({})))
    assert again['inventory']['running'] is True
    assert len(spawned) == 1
    asyncio.run(spawned[0])

    body = asyncio.run(api.artist_watch_releases(watch.id, _Req({})))
    assert body['inventory']['running'] is False
    assert body['inventory']['checked'] == 5
    assert body['inventory']['finished_at']
    clb = _by_name(body['releases'])['Certified Lover Boy']
    assert (clb['state'], clb['have'], clb['total']) == ('complete', 2, 2)

    tracks = asyncio.run(
        api.artist_watch_release_tracks(
            watch.id, _Req({}), album_id=clb['album_ids']
        )
    )
    assert tracks['album_id'] == 'deezer:10'
    assert [(t['name'], bool(t['file'])) for t in tracks['tracks']] == [
        ('TSU', True),
        ('Way 2 Sexy', True),
    ]


def test_a_release_not_read_yet_has_no_tracks(monkeypatch, tmp_path):
    _db, watch, _spawned = _api(monkeypatch, tmp_path)
    tracks = asyncio.run(
        api.artist_watch_release_tracks(
            watch.id, _Req({}), album_id=['CLB', 'deezer:10']
        )
    )
    assert tracks == {'album_id': 'CLB', 'tracks': []}


# ── "Download missing" ──────────────────────────────────────────────────


def test_download_missing_fills_in_what_a_known_release_lacks(
    monkeypatch, tmp_path
):
    _catalogues(monkeypatch)
    db, watch = _watch(tmp_path)
    db.update_playlist(watch.id, release_types='album')
    dl = _FakeDownloader(tmp_path)
    _sweep(db, watch, dl, ON)
    # Way 2 Sexy goes missing from the library since.
    files = db.get_track_filenames(watch.id)
    (tmp_path / files['wib']).unlink()
    dl.calls.clear()

    async def scenario():
        async def broadcast(_message):
            return None

        return await monitor.check_artist(
            db.get_playlist(watch.id),
            db,
            dl,
            broadcast,
            asyncio.get_running_loop(),
            settings=ON,
            library=monitor.LibraryStores(listing=lambda: []),
            fill_missing=True,
        )

    asyncio.run(scenario())

    # Only the missing song is fetched again; the single the watch
    # doesn't download stays out.
    assert dl.calls in (['wib'], ['deezer-Certified Lover Boy-2'])
    assert not any('Laugh Now Cry Later' in call for call in dl.calls)


def test_download_missing_leaves_releases_out_before_the_watch(
    monkeypatch, tmp_path
):
    _catalogues(monkeypatch)
    db, watch = _watch(tmp_path, new_only=True)
    dl = _FakeDownloader(tmp_path)
    _sweep(db, watch, dl, ON)  # the baseline

    async def scenario():
        async def broadcast(_message):
            return None

        return await monitor.check_artist(
            db.get_playlist(watch.id),
            db,
            dl,
            broadcast,
            asyncio.get_running_loop(),
            settings=ON,
            library=monitor.LibraryStores(listing=lambda: []),
            fill_missing=True,
        )

    asyncio.run(scenario())
    assert dl.calls == []


def test_what_download_missing_would_fetch():
    def release(state, have, total, wanted=True):
        return {'state': state, 'have': have, 'total': total, 'wanted': wanted}

    assert artist_catalogue.missing([
        release('partly', 3, 20),
        release('missing', 0, 12),
        release('missing', 0, 0),  # tracklist not read yet
        release('complete', 5, 5),
        release('partly', 1, 9, wanted=False),
    ]) == {'tracks': 29, 'releases': 2, 'unread': 1}


def test_download_missing_over_the_api(monkeypatch, tmp_path):
    db, watch, spawned = _api(monkeypatch, tmp_path)
    monkeypatch.setattr(api.state, 'downloader', object())
    started = []

    async def fake_check(*args, fill_missing=False, **kwargs):
        started.append(fill_missing)
        return 0

    monkeypatch.setattr(api, 'check_watch', fake_check)
    db.catalogue.set_choice(watch.id, ['mb:rfi'], 'on')

    body = asyncio.run(
        api.download_missing_artist_releases(watch.id, _Req({}))
    )
    assert body['started'] is True
    assert body['missing'] == {'tracks': 0, 'releases': 0, 'unread': 1}
    asyncio.run(spawned[0])
    assert started == [True]

    monkeypatch.setattr(api, 'check_running', lambda _id: True)
    with pytest.raises(HTTPException) as busy:
        asyncio.run(api.download_missing_artist_releases(watch.id, _Req({})))
    assert busy.value.status_code == 409
    listed = asyncio.run(api.artist_watch_releases(watch.id, _Req({})))
    assert listed['checking'] is True
    assert listed['missing']['unread'] == 1
