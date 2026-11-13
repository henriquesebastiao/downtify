"""Artist Watch reads Deezer's discography as well as YouTube Music's
(monitor._artist_discography): YouTube Music's artist page doesn't list
every release - Drake's shows only his albums from 2021 on.

All offline - both catalogues and the downloader are faked.
"""

from __future__ import annotations

import asyncio

import pytest

from downtify import monitor
from tests.test_artist_watch_duplicates import (
    CHANNEL_ID,
    _album,
    _FakeDownloader,
    _patch,
    _track,
)

DEEZER_DRAKE = '246791'
ON = {'artist_watch_deezer': True}


def _dz_track(  # noqa: PLR0913  # mirrors a track's fields
    number, name, album, *, duration, artists=('Drake',), album_artist='Drake'
):
    return {
        'song_id': f'deezer-{album}-{number}',
        'name': name,
        'album_name': album,
        'track_number': number,
        'album_track_total': 0,
        'artists': list(artists),
        'album_artist': album_artist,
        'duration': duration,
        'source': 'deezer',
    }


def _release(album_id: str, name: str, kind: str = 'Album') -> dict:
    return {
        'album_id': album_id,
        'name': name,
        'artist': 'Drake',
        'year': '2016',
        'source': 'deezer',
        'release_type': kind,
    }


def _credits(songs, main=None):
    """``deezer.album_credits_from_id``'s answer for *songs*: the album
    artist, and its main contributors (the track artists unless given)."""

    owner = songs[0]['album_artist'] if songs else 'Drake'
    if main is None:
        main = list(dict.fromkeys(a for s in songs for a in s['artists']))
    return owner, main, songs


class _Deezer:
    """Deezer's artist search, discography and album tracklists."""

    def __init__(self, monkeypatch, releases, tracks, artist=DEEZER_DRAKE):
        self.lookups: list[str] = []
        self.releases = releases
        self.tracks = tracks

        def lookup(name):
            self.lookups.append(name)
            return artist

        monkeypatch.setattr(monitor.deezer, 'lookup_artist_id', lookup)
        monkeypatch.setattr(
            monitor.deezer,
            'artist_page_from_id',
            lambda _id: ('Drake', '', list(self.releases)),
        )
        monkeypatch.setattr(
            monitor.deezer,
            'album_credits_from_id',
            lambda album_id: _credits(self.tracks.get(album_id, [])),
        )


def _sweep(db, watch, downloader, settings, rows=()):
    library = monitor.LibraryStores(listing=lambda: list(rows))

    async def scenario():
        async def broadcast(_message):
            return None

        return await monitor.check_artist(
            db.get_playlist(watch.id),
            db,
            downloader,
            broadcast,
            asyncio.get_running_loop(),
            settings=settings,
            library=library,
        )

    return asyncio.run(scenario())


def _watch(tmp_path, *, new_only=False):
    db = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist(
        CHANNEL_ID, 'Drake', 'url', 60, monitor.KIND_ARTIST, new_only=new_only
    )
    return db, watch


def test_deezer_adds_the_albums_youtube_music_doesnt_list(
    monkeypatch, tmp_path
):
    _patch(
        monkeypatch,
        [_album('CLB', 'Certified Lover Boy')],
        {
            'CLB': [
                _track('tsu', 'TSU', 'Certified Lover Boy', 8, duration=308)
            ]
        },
    )
    _Deezer(
        monkeypatch,
        [_release('10', 'Certified Lover Boy'), _release('20', 'Views')],
        {
            '10': [_dz_track(8, 'TSU', 'Certified Lover Boy', duration=308)],
            '20': [_dz_track(20, 'Hotline Bling', 'Views', duration=267)],
        },
    )
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)

    downloaded = _sweep(db, watch, dl, ON)

    # TSU is on both catalogues: downloaded once, the Deezer copy linked.
    assert dl.calls == ['tsu', 'deezer-Views-20']
    assert downloaded == 2
    files = db.get_track_filenames(watch.id)
    assert files['deezer-Certified Lover Boy-8'] == files['tsu']
    assert db.get_seen_album_ids(watch.id) == {
        'CLB',
        'deezer:10',
        'deezer:20',
    }
    refreshed = db.get_playlist(watch.id)
    assert refreshed.deezer_id == DEEZER_DRAKE
    # Certified Lover Boy is one release, listed by both.
    assert refreshed.last_track_count == 2


def test_the_deezer_artist_is_looked_up_once(monkeypatch, tmp_path):
    _patch(monkeypatch, [], {})
    deezer = _Deezer(monkeypatch, [], {})
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)

    _sweep(db, watch, dl, ON)
    _sweep(db, watch, dl, ON)

    assert deezer.lookups == ['Drake']


def test_a_single_the_artist_is_a_guest_on_is_skipped(monkeypatch, tmp_path):
    # Deezer lists the singles an artist is featured on among their own,
    # with the guest as a "Main" contributor too.
    _patch(monkeypatch, [], {})
    _Deezer(
        monkeypatch, [_release('30', 'MELTDOWN (feat. Drake)', 'Single')], {}
    )
    song = _dz_track(
        1,
        'MELTDOWN (feat. Drake)',
        'MELTDOWN (feat. Drake)',
        duration=246,
        artists=('Travis Scott',),
        album_artist='Travis Scott',
    )
    monkeypatch.setattr(
        monitor.deezer,
        'album_credits_from_id',
        lambda _id: ('Travis Scott', ['Travis Scott', 'Drake'], [song]),
    )
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)

    downloaded = _sweep(db, watch, dl, ON)

    assert dl.calls == []
    assert downloaded == 0
    assert db.get_seen_album_ids(watch.id) == {'deezer:30'}


def test_an_album_the_artist_never_appears_on_is_skipped(
    monkeypatch, tmp_path
):
    album = "Now That's What I Call Music"
    _patch(monkeypatch, [], {})
    _Deezer(
        monkeypatch,
        [_release('31', album)],
        {
            '31': [
                _dz_track(
                    1,
                    'Work',
                    album,
                    duration=219,
                    artists=('Rihanna',),
                    album_artist='Various Artists',
                )
            ]
        },
    )
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)

    _sweep(db, watch, dl, ON)

    assert dl.calls == []


def test_a_joint_album_with_another_artist_is_downloaded(
    monkeypatch, tmp_path
):
    # $ome $exy $ongs 4 U: credited to PARTYNEXTDOOR, Drake a main artist.
    album = '$ome $exy $ongs 4 U'
    song = _dz_track(
        1,
        'CN TOWER',
        album,
        duration=230,
        artists=('PARTYNEXTDOOR', 'Drake'),
        album_artist='PARTYNEXTDOOR',
    )
    _patch(monkeypatch, [], {})
    _Deezer(monkeypatch, [_release('50', album)], {'50': [song]})
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)

    _sweep(db, watch, dl, ON)

    assert dl.calls == [song['song_id']]


@pytest.mark.parametrize(
    ('owner', 'main', 'titles', 'own'),
    [
        ('Drake', ['Drake'], ['Views'], True),
        ('', [], ['Views'], True),
        ('PARTYNEXTDOOR', ['PARTYNEXTDOOR', 'Drake'], ['CN TOWER'], True),
        ('Nicki Minaj', ['Nicki Minaj', 'Drake'], ['No Frauds'], True),
        ('Travis Scott', ['Travis Scott', 'Drake'], ['MELTDOWN'], True),
        (
            'Travis Scott',
            ['Travis Scott', 'Drake'],
            ['MELTDOWN', 'MELTDOWN (feat. Drake)'],
            False,
        ),
        ('DJ Khaled', ['DJ Khaled'], ['POPSTAR'], False),
        (
            'DJ Khaled',
            ['DJ Khaled', 'Drake'],
            ['STAYING ALIVE (feat. Drake & Lil Baby)'],
            False,
        ),
        ('Popcaan', ['Popcaan', 'Drake'], ['TWIST (with Drake)'], False),
        # "Drake" inside another word isn't a guest credit.
        ('Mandrake', ['Mandrake', 'Drake'], ['Song (feat. Mandrakes)'], True),
    ],
)
def test_credited_release(owner, main, titles, own):
    assert monitor._credited_release('Drake', owner, main, titles) is own


def test_a_new_releases_only_watch_skips_deezers_back_catalogue(
    monkeypatch, tmp_path
):
    # A watch that already recorded its YouTube Music baseline, before
    # Deezer was read: what Deezer lists then is old, not new.
    _patch(monkeypatch, [_album('CLB', 'Certified Lover Boy')], {})
    deezer = _Deezer(
        monkeypatch,
        [_release('20', 'Views')],
        {'20': [_dz_track(20, 'Hotline Bling', 'Views', duration=267)]},
    )
    db, watch = _watch(tmp_path, new_only=True)
    dl = _FakeDownloader(tmp_path)
    _sweep(db, watch, dl, {})  # baseline, YouTube Music only

    _sweep(db, watch, dl, ON)
    assert dl.calls == []

    deezer.releases.append(_release('40', 'Iceman'))
    deezer.tracks['40'] = [_dz_track(1, 'Dust', 'Iceman', duration=200)]
    _sweep(db, watch, dl, ON)

    assert dl.calls == ['deezer-Iceman-1']


def test_a_new_releases_only_watch_records_both_at_its_baseline(
    monkeypatch, tmp_path
):
    _patch(monkeypatch, [_album('CLB', 'Certified Lover Boy')], {})
    _Deezer(monkeypatch, [_release('20', 'Views')], {})
    db, watch = _watch(tmp_path, new_only=True)
    dl = _FakeDownloader(tmp_path)

    _sweep(db, watch, dl, ON)

    assert dl.calls == []
    assert db.get_seen_album_ids(watch.id) == {'CLB', 'deezer:20'}


def test_without_the_setting_deezer_is_not_asked(monkeypatch, tmp_path):
    _patch(
        monkeypatch,
        [_album('CLB', 'Certified Lover Boy')],
        {
            'CLB': [
                _track('tsu', 'TSU', 'Certified Lover Boy', 8, duration=308)
            ]
        },
    )

    def no_deezer(_name):
        raise AssertionError('Deezer asked with the setting off')

    monkeypatch.setattr(monitor.deezer, 'lookup_artist_id', no_deezer)
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)

    _sweep(db, watch, dl, {})

    assert dl.calls == ['tsu']


def test_deezer_failing_leaves_youtube_music(monkeypatch, tmp_path):
    _patch(
        monkeypatch,
        [_album('CLB', 'Certified Lover Boy')],
        {
            'CLB': [
                _track('tsu', 'TSU', 'Certified Lover Boy', 8, duration=308)
            ]
        },
    )

    def down(_name):
        raise ValueError('Deezer did not answer')

    monkeypatch.setattr(monitor.deezer, 'lookup_artist_id', down)
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)

    _sweep(db, watch, dl, ON)

    assert dl.calls == ['tsu']
    assert not db.get_playlist(watch.id).deezer_id


def test_youtube_music_failing_leaves_deezer(monkeypatch, tmp_path):
    def down(_channel):
        raise ValueError('YouTube Music did not answer')

    monkeypatch.setattr(
        monitor.providers, 'artist_albums_from_channel_id', down
    )
    _Deezer(
        monkeypatch,
        [_release('20', 'Views')],
        {'20': [_dz_track(20, 'Hotline Bling', 'Views', duration=267)]},
    )
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)

    _sweep(db, watch, dl, ON)

    assert dl.calls == ['deezer-Views-20']


def test_both_failing_is_a_failed_check(monkeypatch, tmp_path):
    def down(_value):
        raise ValueError('no answer')

    monkeypatch.setattr(
        monitor.providers, 'artist_albums_from_channel_id', down
    )
    monkeypatch.setattr(monitor.deezer, 'lookup_artist_id', down)
    db, watch = _watch(tmp_path, new_only=True)
    dl = _FakeDownloader(tmp_path)

    assert _sweep(db, watch, dl, ON) == 0
    # Still waiting for a real answer to record the baseline from.
    assert db.get_playlist(watch.id).baseline_pending


def test_retargeting_forgets_the_deezer_artist(monkeypatch, tmp_path):
    _patch(monkeypatch, [], {})
    _Deezer(monkeypatch, [], {})
    db, watch = _watch(tmp_path)
    _sweep(db, watch, _FakeDownloader(tmp_path), ON)
    assert db.get_playlist(watch.id).deezer_id == DEEZER_DRAKE

    db.retarget_playlist(watch.id, 'UCother', 'Drake', 'url')

    assert not db.get_playlist(watch.id).deezer_id


@pytest.mark.parametrize(
    ('names', 'count'),
    [
        (['Views', 'Views', 'Scorpion'], 2),
        (['Views', 'VIEWS'], 1),
        ([], 0),
    ],
)
def test_release_count_counts_a_release_on_both_sources_once(names, count):
    albums = [{'album_id': str(i), 'name': n} for i, n in enumerate(names)]

    assert monitor._release_count(albums) == count
