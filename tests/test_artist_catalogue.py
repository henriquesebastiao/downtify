"""An artist watch's catalogue: every release its catalogues list, what
the library has of each, and the user's per-release switch
(downtify/artist_catalogue.py, GET/PATCH
/api/monitor/playlists/{id}/releases; issue #581, phase 2).

All offline: the catalogues and the downloader are faked.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from downtify import api, artist_catalogue, musicbrainz
from tests.test_artist_watch_deezer import (
    _dz_track,
    _release,
    _sweep,
    _watch,
)
from tests.test_artist_watch_duplicates import (
    _album,
    _FakeDownloader,
    _patch,
    _track,
)
from tests.test_artist_watch_musicbrainz import (
    _deezer,
    _mb_track,
    _MusicBrainz,
    _rg,
)
from tests.test_monitor_edit import _Req

ON = {'artist_watch_deezer': True, 'artist_watch_musicbrainz': True}


def _view(db, watch, settings=ON):
    watch = db.get_playlist(watch.id)
    return artist_catalogue.catalogue_view(
        db.catalogue.rows(watch.id),
        have=db.releases.counts(watch.id),
        seen=db.catalogue.seen(watch.id),
        types=set(watch.release_types.split(',')),
        kinds=artist_catalogue.watch_kinds(watch, settings),
    )


def _by_name(releases):
    return {r['name']: r for r in releases}


def _catalogues(monkeypatch):
    """Drake on all three catalogues: an album both YouTube Music and
    Deezer list, a single, a guest spot, a mixtape and a live album."""

    _patch(
        monkeypatch,
        [_album('CLB', 'Certified Lover Boy')],
        {
            'CLB': [
                _track('tsu', 'TSU', 'Certified Lover Boy', 1, duration=308),
                _track(
                    'wib', 'Way 2 Sexy', 'Certified Lover Boy', 2, duration=257
                ),
            ]
        },
    )
    _deezer(
        monkeypatch,
        [
            _release('10', 'Certified Lover Boy'),
            _release('20', 'Laugh Now Cry Later', 'Single'),
            _release('30', 'MELTDOWN (feat. Drake)', 'Single'),
        ],
        {
            '10': [
                _dz_track(1, 'TSU', 'Certified Lover Boy', duration=308),
                _dz_track(
                    2, 'Way 2 Sexy', 'Certified Lover Boy', duration=257
                ),
            ],
            '20': [
                _dz_track(
                    1,
                    'Laugh Now Cry Later',
                    'Laugh Now Cry Later',
                    duration=261,
                )
            ],
            '30': [
                _dz_track(
                    1,
                    'MELTDOWN (feat. Drake)',
                    'MELTDOWN (feat. Drake)',
                    duration=246,
                    artists=('Travis Scott', 'Drake'),
                    album_artist='Travis Scott',
                )
            ],
        },
    )
    return _MusicBrainz(
        monkeypatch,
        [
            _rg('rfi', 'Room for Improvement', secondary=['Mixtape/Street']),
            _rg('o2', 'Live at the O2', secondary=['Live']),
        ],
        {
            'rfi': [
                _mb_track(
                    1, 'Do What You Do', 'Room for Improvement', duration=231
                )
            ],
            'o2': [
                _mb_track(
                    1,
                    'Started From the Bottom (Live)',
                    'Live at the O2',
                    duration=200,
                )
            ],
        },
    )


# ── The store ───────────────────────────────────────────────────────────


def test_a_new_listing_keeps_what_was_learnt_and_chosen(tmp_path):
    db, watch = _watch(tmp_path)
    store = db.catalogue
    store.record(watch.id, [_release('deezer:1', 'Views')])
    store.set_total(watch.id, 'deezer:1', 20)
    store.set_not_own(watch.id, 'deezer:1')
    assert store.set_choice(watch.id, ['deezer:1', 'nope'], 'off') == 1

    store.record(watch.id, [{**_release('deezer:1', 'VIEWS'), 'year': '2016'}])

    (row,) = store.rows(watch.id)
    assert row['name'] == 'VIEWS'
    assert row['source'] == 'deezer'
    assert (row['track_total'], row['not_own'], row['choice']) == (
        20,
        1,
        'off',
    )
    assert store.choices(watch.id) == {'deezer:1': 'off'}
    with pytest.raises(ValueError, match='choice'):
        store.set_choice(watch.id, ['deezer:1'], 'maybe')


def test_the_catalogue_follows_the_watch_to_another_artist(tmp_path):
    db, watch = _watch(tmp_path)
    db.catalogue.record(watch.id, [_album('CLB', 'Certified Lover Boy')])
    assert db.catalogue.rows(watch.id)[0]['source'] == 'youtube'

    db.retarget_playlist(watch.id, 'UCother', 'Other', 'url2')

    assert db.catalogue.rows(watch.id) == []


# ── A sweep and the page ────────────────────────────────────────────────


def test_the_page_shows_every_release_and_what_the_library_has(
    monkeypatch, tmp_path
):
    _catalogues(monkeypatch)
    db, watch = _watch(tmp_path)
    db.update_playlist(watch.id, release_types='album')
    dl = _FakeDownloader(tmp_path)

    _sweep(db, watch, dl, ON)
    releases = _view(db, watch)
    named = _by_name(releases)

    # Certified Lover Boy is one row for both catalogues.
    assert len(releases) == 5
    clb = named['Certified Lover Boy']
    assert clb['sources'] == ['youtube', 'deezer']
    assert len(clb['album_ids']) == 2
    assert (clb['state'], clb['have'], clb['total']) == ('complete', 2, 2)
    assert named['Room for Improvement']['state'] == 'complete'
    assert named['Room for Improvement']['section'] == 'mixtape'
    # Singles aren't watched; the live album's kind isn't let in.
    assert named['Laugh Now Cry Later']['state'] == 'not_watched'
    assert named['Live at the O2']['state'] == 'not_watched'
    assert named['Live at the O2']['kinds'] == ['live']
    assert named['Live at the O2']['section'] == 'other'
    # A single nobody fetched yet: not known to be a guest spot.
    assert named['MELTDOWN (feat. Drake)']['state'] == 'not_watched'
    assert artist_catalogue.counts(releases)['complete'] == 2


def test_switching_a_release_on_downloads_it(monkeypatch, tmp_path):
    _catalogues(monkeypatch)
    db, watch = _watch(tmp_path)
    db.update_playlist(watch.id, release_types='album')
    dl = _FakeDownloader(tmp_path)
    _sweep(db, watch, dl, ON)
    assert 'deezer-Laugh Now Cry Later-1' not in dl.calls

    db.catalogue.set_choice(watch.id, ['deezer:20'], 'on')
    _sweep(db, watch, dl, ON)

    assert 'deezer-Laugh Now Cry Later-1' in dl.calls
    assert (
        _by_name(_view(db, watch))['Laugh Now Cry Later']['state']
        == 'complete'
    )


def test_a_guest_spot_switched_on_is_still_not_downloaded(
    monkeypatch, tmp_path
):
    _catalogues(monkeypatch)
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)
    db.catalogue.record(
        watch.id, [_release('deezer:30', 'MELTDOWN (feat. Drake)', 'Single')]
    )
    db.catalogue.set_choice(watch.id, ['deezer:30'], 'on')

    _sweep(db, watch, dl, ON)

    assert not any('MELTDOWN' in call for call in dl.calls)
    assert (
        _by_name(_view(db, watch))['MELTDOWN (feat. Drake)']['state']
        == 'not_own'
    )


def test_switching_a_release_off_keeps_it_out(monkeypatch, tmp_path):
    _catalogues(monkeypatch)
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)
    db.catalogue.record(
        watch.id,
        [
            {
                'album_id': 'mb:rfi',
                'name': 'Room for Improvement',
                'release_type': 'Album',
                'kinds': ['mixtape/street'],
            }
        ],
    )
    db.catalogue.set_choice(watch.id, ['mb:rfi'], 'off')

    _sweep(db, watch, dl, ON)

    assert 'mb-Room for Improvement-1' not in dl.calls
    assert _by_name(_view(db, watch))['Room for Improvement']['state'] == 'off'


def test_a_watch_can_let_in_live_albums(monkeypatch, tmp_path):
    _catalogues(monkeypatch)
    db, watch = _watch(tmp_path)
    db.update_playlist(watch.id, musicbrainz_kinds='mixtape,live')
    dl = _FakeDownloader(tmp_path)

    _sweep(db, watch, dl, ON)

    assert 'mb-Live at the O2-1' in dl.calls
    assert _by_name(_view(db, watch))['Live at the O2']['state'] == 'complete'
    # Its own kinds, not the setting's.
    assert artist_catalogue.watch_kinds(db.get_playlist(watch.id), ON) == {
        'mixtape/street',
        'live',
    }
    db.update_playlist(watch.id, musicbrainz_kinds='')
    assert artist_catalogue.watch_kinds(db.get_playlist(watch.id), ON) == set()


def test_a_release_out_before_the_watch_can_be_switched_on(
    monkeypatch, tmp_path
):
    _catalogues(monkeypatch)
    db, watch = _watch(tmp_path, new_only=True)
    dl = _FakeDownloader(tmp_path)
    _sweep(db, watch, dl, ON)  # records what's out as skipped
    _sweep(db, watch, dl, ON)
    assert dl.calls == []
    assert (
        _by_name(_view(db, watch))['Room for Improvement']['state']
        == 'skipped'
    )

    db.catalogue.set_choice(watch.id, ['mb:rfi'], 'on')
    assert db.catalogue.forget_skipped(watch.id, ['mb:rfi']) == 1
    _sweep(db, watch, dl, ON)

    assert dl.calls == ['mb-Room for Improvement-1']


def test_states_of_a_release():
    def row(**kw):
        return {
            'album_id': 'a',
            'name': 'A',
            'release_type': 'Album',
            'kinds': '',
            'year': '',
            'source': 'deezer',
            'cover_url': '',
            'url': '',
            'track_total': 10,
            'not_own': 0,
            'choice': '',
            **kw,
        }

    def state(r, have=0, seen=None, types=frozenset({'album'})):
        (view,) = artist_catalogue.catalogue_view(
            [r],
            have={'a': have},
            seen={} if seen is None else {'a': seen},
            types=set(types),
            kinds=set(),
        )
        return view['state']

    assert state(row(), have=10) == 'complete'
    assert state(row(), have=4) == 'partly'
    assert state(row()) == 'missing'
    assert state(row(), seen=True) == 'skipped'
    assert state(row(choice='on'), seen=True) == 'missing'
    assert state(row(), types={'single'}) == 'not_watched'
    assert state(row(), seen=True, types={'single'}) == 'not_watched'
    assert state(row(choice='off'), have=10) == 'off'
    assert state(row(not_own=1)) == 'not_own'
    assert state(row(kinds='mixtape/street')) == 'not_watched'
    assert artist_catalogue.section_of('album', ['soundtrack']) == 'album'


def test_one_release_with_and_without_its_guest_is_one_row():
    rows = [
        {
            'album_id': album_id,
            'name': name,
            'release_type': 'Single',
            'kinds': '',
            'year': '2020',
            'source': source,
            'cover_url': '',
            'url': '',
            'track_total': 0,
            'not_own': 0,
            'choice': '',
        }
        for album_id, name, source in (
            ('MPREb_1', 'Laugh Now Cry Later (feat. Lil Durk)', 'youtube'),
            ('deezer:2', 'Laugh Now Cry Later', 'deezer'),
            ('deezer:3', 'Laugh Now Cry Later (Remix)', 'deezer'),
        )
    ]
    view = artist_catalogue.catalogue_view(
        rows, have={}, seen={}, types={'single'}, kinds=set()
    )
    assert [r['album_ids'] for r in view] == [
        ['MPREb_1', 'deezer:2'],
        ['deezer:3'],
    ]
    assert artist_catalogue.section_of('single', ['remix']) == 'other'


# ── Over the API ────────────────────────────────────────────────────────


@pytest.fixture
def api_db(monkeypatch, tmp_path):
    db, watch = _watch(tmp_path)
    monkeypatch.setattr(api.state, 'monitor_db', db)
    monkeypatch.setattr(api.state, 'downloader', None)
    monkeypatch.setattr(api.state, 'settings', dict(ON))
    db.catalogue.record(
        watch.id,
        [
            _release('deezer:10', 'Certified Lover Boy'),
            _release('deezer:20', 'Laugh Now Cry Later', 'Single'),
        ],
    )
    return db, watch


def test_the_releases_route(api_db):
    db, watch = api_db
    body = asyncio.run(api.artist_watch_releases(watch.id, _Req({})))
    assert [r['name'] for r in body['releases']] == [
        'Certified Lover Boy',
        'Laugh Now Cry Later',
    ]
    assert body['kinds'] == ['mixtape', 'soundtrack']
    assert body['kinds_default'] is True
    assert body['available_kinds'] == list(musicbrainz.KINDS)
    assert body['counts']['missing'] == 2


def test_switching_over_the_route(api_db):
    db, watch = api_db
    off = asyncio.run(
        api.switch_artist_watch_releases(
            watch.id, _Req({'album_ids': ['deezer:20'], 'choice': 'off'})
        )
    )
    assert _by_name(off['releases'])['Laugh Now Cry Later']['state'] == 'off'
    for bad in (
        {'album_ids': [], 'choice': 'on'},
        {'album_ids': ['deezer:20'], 'choice': 'maybe'},
        {'choice': 'on'},
    ):
        with pytest.raises(HTTPException) as refused:
            asyncio.run(api.switch_artist_watch_releases(watch.id, _Req(bad)))
        assert refused.value.status_code == 400
    with pytest.raises(HTTPException) as unknown:
        asyncio.run(
            api.switch_artist_watch_releases(
                watch.id, _Req({'album_ids': ['nope'], 'choice': 'on'})
            )
        )
    assert unknown.value.status_code == 404


def test_a_watchs_kinds_over_the_route(api_db):
    db, watch = api_db
    asyncio.run(
        api.update_monitor_playlist(
            watch.id, _Req({'musicbrainz_kinds': ['live', 'mixtape']})
        )
    )
    # Stored in KINDS order.
    assert db.get_playlist(watch.id).musicbrainz_kinds == 'mixtape,live'
    asyncio.run(
        api.update_monitor_playlist(
            watch.id, _Req({'musicbrainz_kinds': None})
        )
    )
    assert db.get_playlist(watch.id).musicbrainz_kinds is None
    with pytest.raises(HTTPException) as refused:
        asyncio.run(
            api.update_monitor_playlist(
                watch.id, _Req({'musicbrainz_kinds': ['bootleg']})
            )
        )
    assert refused.value.status_code == 400


def test_a_playlist_watch_has_no_releases(api_db):
    db, _watch_ = api_db
    playlist = db.add_playlist('37i9dQZF1DXcBWIGoYBM5M', 'Hits', 'url', 60)
    with pytest.raises(HTTPException) as refused:
        asyncio.run(api.artist_watch_releases(playlist.id, _Req({})))
    assert refused.value.status_code == 400
