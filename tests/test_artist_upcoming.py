"""Announced releases: listed as coming, downloaded on their release day."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from downtify import artist_catalogue, monitor, wanted_routes
from downtify.artist_catalogue import catalogue_view, release_day, upcoming
from tests.test_artist_wanted import (  # noqa: F401  # db: the fixture
    _artist,
    _library,
    db,
)
from tests.test_artist_watch import (
    CHANNEL_ID,
    _db,
    _FakeDownloader,
    _patch_provider,
    _run_check,
    _track,
)

FUTURE = '2999-12-05'
PAST = '2001-02-03'
TODAY = date(2026, 11, 19)


def _album(album_id, name, day):
    return {
        'album_id': album_id,
        'name': name,
        'year': day[:4],
        'release_date': day,
    }


def test_upcoming_compares_as_much_of_the_date_as_is_known():
    assert upcoming({'release_date': '2026-12-05'}, TODAY)
    assert not upcoming({'release_date': '2026-11-19'}, TODAY)  # out today
    assert not upcoming({'release_date': '2026-11-01'}, TODAY)
    assert upcoming({'release_date': '2026-12'}, TODAY)
    assert not upcoming({'release_date': '2026-11'}, TODAY)
    assert upcoming({'release_date': '2027'}, TODAY)
    assert not upcoming({'release_date': '2026'}, TODAY)
    assert not upcoming({'release_date': 'soon'}, TODAY)
    assert not upcoming({'year': '2030'}, TODAY)  # a year alone isn't a date
    assert release_day({'release_date': '2026-12-05T00:00:00'}) == '2026-12-05'


def test_the_page_shows_a_wanted_announced_release_as_upcoming():
    row = {
        'album_id': 'deezer:1',
        'name': 'Next',
        'release_type': 'Album',
        'kinds': '',
        'year': '2026',
        'release_date': '2026-12-05',
        'source': 'deezer',
        'cover_url': '',
        'url': '',
        'track_total': 0,
        'not_own': 0,
        'choice': '',
    }
    common = {'have': {}, 'seen': {}, 'kinds': set(), 'today': TODAY}

    [shown] = catalogue_view([row], types={'album'}, **common)
    assert shown['state'] == 'upcoming'
    assert shown['release_date'] == '2026-12-05'
    assert shown['wanted'] is True
    # Nothing to fetch for "Download missing" yet.
    assert artist_catalogue.missing([shown]) == {
        'tracks': 0,
        'releases': 0,
        'unread': 0,
    }
    # A type the watch doesn't download stays "not watched".
    [single] = catalogue_view([row], types={'single'}, **common)
    assert single['state'] == 'not_watched'
    # Out: to download.
    [out] = catalogue_view(
        [{**row, 'release_date': '2026-11-19'}], types={'album'}, **common
    )
    assert out['state'] == 'missing'


def test_the_sweep_waits_for_the_release_day(monkeypatch, tmp_path):
    tracks = {'NEXT': [_track('t1', 'One', 'Next', 1)]}
    _patch_provider(monkeypatch, [_album('NEXT', 'Next', FUTURE)], tracks)
    store = _db(tmp_path)
    watch = store.add_playlist(
        CHANNEL_ID, 'Test Artist', 'url', 60, monitor.KIND_ARTIST
    )

    dl = _FakeDownloader(tmp_path)
    assert _run_check(watch, store, dl) == 0
    assert dl.calls == []
    [row] = store.catalogue.rows(watch.id)
    assert row['release_date'] == FUTURE

    # Out now: the next check downloads it.
    _patch_provider(monkeypatch, [_album('NEXT', 'Next', PAST)], tracks)
    dl = _FakeDownloader(tmp_path)
    assert _run_check(store.get_playlist(watch.id), store, dl) == 1
    assert dl.calls == ['t1']


def test_new_only_never_skips_an_announced_release(monkeypatch, tmp_path):
    tracks = {
        'OLD': [_track('t0', 'Zero', 'Old', 1)],
        'NEXT': [_track('t1', 'One', 'Next', 1)],
    }
    albums = [_album('OLD', 'Old', PAST), _album('NEXT', 'Next', FUTURE)]
    _patch_provider(monkeypatch, albums, tracks)
    store = _db(tmp_path)
    watch = store.add_playlist(
        CHANNEL_ID, 'A', 'url', 60, monitor.KIND_ARTIST, new_only=True
    )
    assert _run_check(watch, store, _FakeDownloader(tmp_path)) == 0
    assert store.get_seen_album_ids(watch.id) == {'OLD'}

    _patch_provider(
        monkeypatch, [albums[0], _album('NEXT', 'Next', PAST)], tracks
    )
    dl = _FakeDownloader(tmp_path)
    assert _run_check(store.get_playlist(watch.id), store, dl) == 1
    assert dl.calls == ['t1']


def test_another_catalogues_date_holds_every_listing_of_the_release():
    albums = [
        {'album_id': 'YT', 'name': 'Next', 'year': '2999'},
        {
            'album_id': 'deezer:1',
            'name': 'Next',
            'release_type': 'Album',
            'release_date': FUTURE,
        },
        {'album_id': 'YT2', 'name': 'Other', 'year': '2001'},
    ]
    monitor.spread_release_dates(albums)
    assert albums[0]['release_date'] == FUTURE
    assert 'release_date' not in albums[2]
    assert [a['album_id'] for a in monitor.out_already(albums)] == ['YT2']


def test_a_watch_is_due_on_its_release_day(tmp_path):
    store = _db(tmp_path)
    watch = store.add_playlist(
        CHANNEL_ID, 'A', 'url', 60 * 24 * 7, monitor.KIND_ARTIST
    )
    today = date.today().isoformat()
    store.catalogue.record(watch.id, [_album('NEXT', 'Next', today)])
    two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    just_now = datetime.now(timezone.utc).isoformat()

    assert store.catalogue.release_day_arrived(watch.id, two_days_ago)
    assert not store.catalogue.release_day_arrived(watch.id, just_now)
    assert not store.catalogue.release_day_arrived(watch.id, None)

    store.catalogue.record(watch.id, [_album('NEXT', 'Next', FUTURE)])
    assert not store.catalogue.release_day_arrived(watch.id, two_days_ago)


def test_wanted_lists_announced_releases_after_the_rest(db, monkeypatch):  # noqa: F811
    _library(monkeypatch)
    watch = _artist(db, 'Drake')
    db.catalogue.record(
        watch.id,
        [
            {
                **_album('a2', 'Later', '2999-12-24'),
                'release_type': 'Album',
                'source': 'deezer',
            },
            {
                **_album('a1', 'Soon', FUTURE),
                'release_type': 'Album',
                'source': 'deezer',
            },
        ],
    )

    view = wanted_routes.wanted_view(db, [watch])

    [artist] = view['artists']
    assert [(r['name'], r['state']) for r in artist['releases']] == [
        ('Soon', 'upcoming'),
        ('Later', 'upcoming'),
    ]
    assert artist['upcoming'] == 2
    assert artist['unchecked'] == 0
    assert artist['missing']['tracks'] == 0
    assert view['totals']['upcoming'] == 2
