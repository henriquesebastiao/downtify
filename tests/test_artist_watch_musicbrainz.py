"""Artist Watch reads MusicBrainz's release groups too (issue #581, phase
2): downtify/musicbrainz.py and monitor._musicbrainz_releases.

All offline - MusicBrainz, the other catalogues and the downloader are
faked.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from downtify import api, monitor, musicbrainz
from tests.test_artist_watch_deezer import (
    _credits,
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

DRAKE = '9fff2f8a-21e6-47de-a2b8-7f449929d43f'
PND = 'pnd00000-0000-0000-0000-000000000000'
RIHANNA = 'rihanna0-0000-0000-0000-000000000000'
ON = {'artist_watch_deezer': True, 'artist_watch_musicbrainz': True}


# ── The web service ─────────────────────────────────────────────────────


class _Response:
    def __init__(self, status: int, data: Any = None, url: str = '') -> None:
        self.status_code = status
        self._data = data
        self.url = url

    def json(self):
        return self._data


@pytest.fixture
def web(monkeypatch):
    """MusicBrainz's web service, answering from ``web.routes``:
    ``{path: answer or [answers...]}``, an answer being JSON or a status
    code."""

    class Web:
        routes: dict[str, Any] = {}
        calls: list[tuple[str, dict]] = []
        heads: list[str] = []
        covers: dict[str, str] = {}

    def get(url, params=None, headers=None, timeout=None):
        path = url[len(musicbrainz.BASE) :]
        Web.calls.append((path, dict(params or {}), dict(headers or {})))
        answer = Web.routes[path]
        if isinstance(answer, list):
            answer = answer.pop(0)
        if callable(answer):
            answer = answer(params)
        if isinstance(answer, int):
            return _Response(answer)
        return _Response(200, answer)

    def head(url, headers=None, follow_redirects=False, timeout=None):
        Web.heads.append(url)
        release = url.split('/release/')[1].split('/')[0]
        final = Web.covers.get(release)
        return _Response(200 if final else 404, url=final or url)

    monkeypatch.setattr(musicbrainz.httpx, 'get', get)
    monkeypatch.setattr(musicbrainz.httpx, 'head', head)
    monkeypatch.setattr(musicbrainz, '_INTERVAL', 0)
    Web.routes = {}
    Web.calls = []
    Web.heads = []
    Web.covers = {}
    return Web


def test_requests_name_downtify_and_ask_for_json(web):
    web.routes['url'] = {'relations': []}
    musicbrainz._artist_by_url('https://www.deezer.com/artist/1')
    path, params, headers = web.calls[0]
    assert params['fmt'] == 'json'
    assert headers['User-Agent'].startswith('Downtify/')
    assert 'github.com/henriquesebastiao/downtify' in headers['User-Agent']


def test_slow_down_is_retried_and_busy_gives_up(web, monkeypatch):
    monkeypatch.setattr(musicbrainz.time, 'sleep', lambda _s: None)
    web.routes['artist'] = [503, 503, {'artists': []}]
    assert not musicbrainz._artist_by_name('Drake')
    assert len(web.calls) == 3

    web.routes['artist'] = [503] * musicbrainz._RETRIES
    with pytest.raises(musicbrainz.MusicBrainzError, match='busy'):
        musicbrainz._artist_by_name('Drake')
    web.routes['url'] = 404
    assert not musicbrainz._artist_by_url('https://example.com')


def test_requests_are_a_second_apart(web, monkeypatch):
    monkeypatch.setattr(musicbrainz, '_INTERVAL', 0.2)
    web.routes['artist'] = {'artists': []}
    started = time.monotonic()
    for _ in range(3):
        musicbrainz._artist_by_name('Drake')
    assert time.monotonic() - started >= 0.38


def test_the_artist_comes_from_their_deezer_page_first(web):
    web.routes['url'] = lambda params: (
        {'relations': [{'artist': {'id': DRAKE, 'name': 'Drake'}}]}
        if 'deezer' in params['resource']
        else 404
    )
    assert (
        musicbrainz.artist_id_for(
            'Drake', deezer_id='246791', channel_id='UC1'
        )
        == DRAKE
    )
    assert [c[1]['resource'] for c in web.calls] == [
        'https://www.deezer.com/artist/246791'
    ]


def test_then_their_channel_then_an_unambiguous_name(web):
    web.routes['url'] = lambda params: (
        {'relations': [{'artist': {'id': DRAKE}}]}
        if 'music.youtube.com/channel/UC1' in params['resource']
        else {'relations': []}
    )
    assert musicbrainz.artist_id_for('Drake', channel_id='UC1') == DRAKE

    web.routes['url'] = {'relations': []}
    web.routes['artist'] = {
        'artists': [
            {'id': 'a', 'name': 'Portishead', 'score': 100},
            {'id': 'b', 'name': 'Portishead Tribute', 'score': 90},
        ]
    }
    assert musicbrainz.artist_id_for('Portishead', channel_id='UC2') == 'a'
    # Two artists of exactly that name: neither is picked.
    web.routes['artist'] = {
        'artists': [
            {'id': 'a', 'name': 'Drake', 'score': 100},
            {'id': 'b', 'name': 'Drake', 'score': 100},
        ]
    }
    assert not musicbrainz.artist_id_for('Drake')


def _rg(  # noqa: PLR0913, PLR0917  # mirrors a release group's fields
    gid, title, primary='Album', secondary=(), credit=None, date='2016'
):
    return {
        'id': gid,
        'title': title,
        'primary-type': primary,
        'secondary-types': list(secondary),
        'first-release-date': date,
        'artist-credit': credit
        or [{'name': 'Drake', 'artist': {'id': DRAKE}, 'joinphrase': ''}],
    }


def test_release_groups_are_read_page_by_page(web):
    first = [_rg(f'g{i}', f'Song {i}', 'Single') for i in range(100)]
    second = [_rg('g100', 'Views')]
    web.routes['release-group'] = lambda params: {
        'release-group-count': 101,
        'release-groups': first if params['offset'] == 0 else second,
    }
    groups = musicbrainz.release_groups(DRAKE)
    assert len(groups) == 101
    assert groups[-1]['title'] == 'Views'
    assert groups[-1]['primary'] == 'album'
    assert [c[1]['offset'] for c in web.calls] == [0, 100]


def _credit(*parts):
    """``('Drake', DRAKE, ' & ')`` rows as an artist credit."""

    return [
        {'name': name, 'artist': {'id': gid}, 'joinphrase': join}
        for name, gid, join in parts
    ]


def test_only_the_artists_own_groups_count():
    own = musicbrainz._group(_rg('1', 'Views'))
    joint = musicbrainz._group(
        _rg(
            '2',
            '$ome $exy $ongs 4 U',
            credit=_credit(
                ('PARTYNEXTDOOR', PND, ' & '), ('Drake', DRAKE, '')
            ),
        )
    )
    guest = musicbrainz._group(
        _rg(
            '3',
            'Work',
            'Single',
            credit=_credit(
                ('Rihanna', RIHANNA, ' feat. '), ('Drake', DRAKE, '')
            ),
        )
    )
    with_guest = musicbrainz._group(
        _rg(
            '4',
            'Wants and Needs',
            'Single',
            credit=_credit(('Drake', DRAKE, ' feat. '), ('Lil Baby', PND, '')),
        )
    )
    assert musicbrainz.credited(own, DRAKE)
    assert musicbrainz.credited(joint, DRAKE)
    assert not musicbrainz.credited(guest, DRAKE)
    assert musicbrainz.credited(with_guest, DRAKE)
    assert musicbrainz.credit_text(joint['credit']) == 'PARTYNEXTDOOR & Drake'


def test_secondary_types_let_in_by_the_setting():
    default = musicbrainz.kinds_from_setting(None)
    assert default == {'mixtape/street', 'soundtrack'}
    assert musicbrainz.kinds_from_setting(['live', 'nope']) == {'live'}

    def group(*secondary, primary='Album'):
        return musicbrainz._group(_rg('x', 'X', primary, secondary))

    primary = musicbrainz.PRIMARY_TYPES
    assert musicbrainz.wanted(group(), DRAKE, primary, default)
    assert musicbrainz.wanted(group('Mixtape/Street'), DRAKE, primary, default)
    assert not musicbrainz.wanted(group('Live'), DRAKE, primary, default)
    assert not musicbrainz.wanted(
        group('Remix', 'Mixtape/Street'), DRAKE, primary, default
    )
    assert not musicbrainz.wanted(
        group(primary='Broadcast'), DRAKE, primary, default
    )
    assert musicbrainz.wanted(
        group('Live'), DRAKE, primary, musicbrainz.kinds_from_setting(['live'])
    )


def _edition(  # noqa: PLR0913  # mirrors an edition's fields
    rid,
    *,
    tracks,
    status='Official',
    note='',
    fmt='Digital Media',
    date='2016-04-29',
):  # noqa: PLR0913
    return {
        'id': rid,
        'title': 'Views',
        'status': status,
        'disambiguation': note,
        'date': date,
        'artist-credit': _credit(('Drake', DRAKE, '')),
        'media': [
            {
                'format': fmt,
                'tracks': [
                    {
                        'title': title,
                        'length': length,
                        'recording': {
                            'id': f'{rid}-rec{n}',
                            'isrcs': [f'USCM5160{n:04d}'],
                        },
                        **(
                            {'artist-credit': _credit(*credit)}
                            if credit
                            else {}
                        ),
                    }
                    for n, (title, length, credit) in enumerate(disc, 1)
                ],
            }
            for disc in tracks
        ],
    }


def test_the_explicit_edition_with_the_most_tracks_is_picked(web):
    disc = [('Keep the Family Close', 324106, None)]
    deluxe = [
        ('Keep the Family Close', 324106, None),
        (
            'One Dance',
            173986,
            (
                ('Drake', DRAKE, ' feat. '),
                ('Wizkid', 'w', ' & '),
                ('Kyla', 'k', ''),
            ),
        ),
    ]
    web.routes['release'] = {
        'releases': [
            _edition('clean', tracks=[deluxe], note='clean'),
            _edition('bootleg', tracks=[deluxe, deluxe], status='Bootleg'),
            _edition('cd', tracks=[disc], fmt='CD'),
            _edition(
                'explicit', tracks=[deluxe, [('Hotline Bling', 267000, None)]]
            ),
        ]
    }
    web.covers['explicit'] = 'https://archive.org/explicit-front-500.jpg'

    edition, songs = musicbrainz.release_group_tracks('views')

    assert edition['id'] == 'explicit'
    assert [s['name'] for s in songs] == [
        'Keep the Family Close',
        'One Dance',
        'Hotline Bling',
    ]
    # Numbered straight through both discs.
    assert [s['track_number'] for s in songs] == [1, 2, 3]
    assert {s['album_track_total'] for s in songs} == {3}
    one_dance = songs[1]
    assert one_dance['artists'] == ['Drake', 'Wizkid', 'Kyla']
    assert one_dance['duration'] == 174
    assert one_dance['song_id'] == 'mb-explicit-rec2'
    assert one_dance['isrc'] == 'USCM51600002'
    assert one_dance['album_name'] == 'Views'
    assert one_dance['album_artist'] == 'Drake'
    assert one_dance['year'] == '2016'
    assert one_dance['source'] == 'musicbrainz'
    # The cover is the archive's image itself (the download doesn't
    # follow the archive's redirect).
    assert (
        one_dance['cover_url'] == 'https://archive.org/explicit-front-500.jpg'
    )


def test_no_cover_leaves_it_to_the_match(web):
    web.routes['release'] = {
        'releases': [_edition('r', tracks=[[('Intro', 60000, None)]])]
    }
    _edition_, songs = musicbrainz.release_group_tracks('g')
    assert not songs[0]['cover_url']
    web.routes['release'] = {'releases': []}
    assert musicbrainz.release_group_tracks('g') == ({}, [])
    # Only bootlegs and promos: nothing to download.
    web.routes['release'] = {
        'releases': [
            _edition('b', tracks=[[('Intro', 60000, None)]], status='Bootleg'),
            _edition(
                'p', tracks=[[('Intro', 60000, None)]], status='Promotion'
            ),
        ]
    }
    assert musicbrainz.release_group_tracks('g') == ({}, [])


def test_groups_made_only_of_bootlegs_arent_listed(web):
    web.routes['release-group'] = {
        'release-group-count': 0,
        'release-groups': [],
    }
    musicbrainz.release_groups(DRAKE)
    assert web.calls[0][1]['release-group-status'] == 'website-default'


# ── In Artist Watch ─────────────────────────────────────────────────────


class _MusicBrainz:
    """musicbrainz.artist_id_for, release_groups and release_group_tracks."""

    def __init__(self, monkeypatch, groups, tracks, artist=DRAKE):
        self.lookups: list[tuple] = []
        self.track_calls: list[str] = []

        def artist_id_for(name, deezer_id='', channel_id=''):
            self.lookups.append((name, deezer_id, channel_id))
            return artist

        def release_group_tracks(group_id):
            # ``None``: a group with no official edition.
            self.track_calls.append(group_id)
            songs = tracks.get(group_id, [])
            return ({'id': group_id} if songs is not None else {}), (
                songs or []
            )

        monkeypatch.setattr(
            monitor.musicbrainz, 'artist_id_for', artist_id_for
        )
        monkeypatch.setattr(
            monitor.musicbrainz,
            'release_groups',
            lambda _id: [musicbrainz._group(g) for g in groups],
        )
        monkeypatch.setattr(
            monitor.musicbrainz, 'release_group_tracks', release_group_tracks
        )


def _mb_track(number, name, album, *, duration, artists=('Drake',)):
    return {
        'song_id': f'mb-{album}-{number}',
        'name': name,
        'album_name': album,
        'track_number': number,
        'album_track_total': 0,
        'artists': list(artists),
        'album_artist': 'Drake',
        'duration': duration,
        'source': 'musicbrainz',
    }


def _deezer(monkeypatch, releases, tracks):
    monkeypatch.setattr(
        monitor.deezer, 'lookup_artist_id', lambda _n: '246791'
    )
    monkeypatch.setattr(
        monitor.deezer,
        'artist_page_from_id',
        lambda _id: ('Drake', '', list(releases)),
    )
    monkeypatch.setattr(
        monitor.deezer,
        'album_credits_from_id',
        lambda album_id: _credits(tracks.get(album_id, [])),
    )


def test_musicbrainz_fills_in_what_the_other_catalogues_miss(
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
    _deezer(
        monkeypatch,
        [_release('20', 'Views')],
        {'20': [_dz_track(1, 'Hotline Bling', 'Views', duration=267)]},
    )
    mb = _MusicBrainz(
        monkeypatch,
        [
            _rg('views', 'Views'),
            _rg(
                'ciyr',
                "If You're Reading This It's Too Late",
                secondary=['Mixtape/Street'],
            ),
            _rg('live', 'Live at the O2', secondary=['Live']),
            _rg(
                'work',
                'Work',
                'Single',
                credit=_credit(
                    ('Rihanna', RIHANNA, ' feat. '), ('Drake', DRAKE, '')
                ),
            ),
        ],
        {
            'ciyr': [
                _mb_track(
                    1,
                    'Legend',
                    "If You're Reading This It's Too Late",
                    duration=241,
                ),
                # Already downloaded from Deezer this sweep: linked.
                _mb_track(
                    2,
                    'Hotline Bling',
                    "If You're Reading This It's Too Late",
                    duration=267,
                ),
            ]
        },
    )
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)

    downloaded = _sweep(db, watch, dl, ON)

    # Views is Deezer's to fetch, the live album and Rihanna's single are
    # left out; only the mixtape's tracklist is asked of MusicBrainz.
    assert mb.track_calls == ['ciyr']
    assert dl.calls == [
        'tsu',
        'deezer-Views-1',
        "mb-If You're Reading This It's Too Late-1",
    ]
    assert downloaded == 3
    files = db.get_track_filenames(watch.id)
    assert (
        files["mb-If You're Reading This It's Too Late-2"]
        == files['deezer-Views-1']
    )
    assert 'mb:ciyr' in db.get_seen_album_ids(watch.id)
    refreshed = db.get_playlist(watch.id)
    assert refreshed.musicbrainz_id == DRAKE
    # Found through the Deezer artist found just before.
    assert mb.lookups == [('Drake', '246791', watch.spotify_id)]
    # Certified Lover Boy, Views, the mixtape and the live album (listed
    # on the watch's page, not downloaded).
    assert refreshed.last_track_count == 4


def test_the_musicbrainz_artist_is_looked_up_once(monkeypatch, tmp_path):
    _patch(monkeypatch, [], {})
    _deezer(monkeypatch, [], {})
    mb = _MusicBrainz(monkeypatch, [], {})
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)

    _sweep(db, watch, dl, ON)
    _sweep(db, watch, dl, ON)

    assert len(mb.lookups) == 1


def test_no_settled_artist_leaves_the_others_working(monkeypatch, tmp_path):
    _patch(
        monkeypatch,
        [_album('CLB', 'Certified Lover Boy')],
        {
            'CLB': [
                _track('tsu', 'TSU', 'Certified Lover Boy', 8, duration=308)
            ]
        },
    )
    _deezer(monkeypatch, [], {})
    _MusicBrainz(monkeypatch, [], {}, artist='')
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)

    assert _sweep(db, watch, dl, ON) == 1
    assert not db.get_playlist(watch.id).musicbrainz_id


def test_a_musicbrainz_failure_doesnt_stop_the_sweep(monkeypatch, tmp_path):
    _patch(
        monkeypatch,
        [_album('CLB', 'Certified Lover Boy')],
        {
            'CLB': [
                _track('tsu', 'TSU', 'Certified Lover Boy', 8, duration=308)
            ]
        },
    )
    _deezer(monkeypatch, [], {})

    def busy(*_a, **_k):
        raise musicbrainz.MusicBrainzError('busy')

    monkeypatch.setattr(monitor.musicbrainz, 'artist_id_for', busy)
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)

    assert _sweep(db, watch, dl, ON) == 1


def test_only_when_every_catalogue_fails_does_the_sweep_fail(monkeypatch):
    def broken(*_a, **_k):
        raise RuntimeError('down')

    monkeypatch.setattr(
        monitor.providers, 'artist_albums_from_channel_id', broken
    )
    monkeypatch.setattr(monitor, '_deezer_releases', broken)
    monkeypatch.setattr(monitor, '_musicbrainz_releases', broken)
    watch = monitor.MonitoredPlaylist(
        id=1,
        spotify_id='UC',
        name='Drake',
        url='',
        interval_minutes=60,
        enabled=True,
        last_checked=None,
        last_track_count=0,
        created_at='',
        kind=monitor.KIND_ARTIST,
    )
    with pytest.raises(RuntimeError, match='No discography source'):
        monitor._artist_discography(watch, None, ON)
    # Off, MusicBrainz isn't asked at all.
    monkeypatch.setattr(
        monitor.providers, 'artist_albums_from_channel_id', lambda _c: []
    )
    assert monitor._artist_discography(watch, None, {}) == []


def test_a_new_releases_only_watch_skips_what_musicbrainz_already_has(
    monkeypatch, tmp_path
):
    _patch(monkeypatch, [_album('CLB', 'Certified Lover Boy')], {})
    _deezer(monkeypatch, [], {})
    _MusicBrainz(
        monkeypatch,
        [
            _rg(
                'ciyr',
                "If You're Reading This It's Too Late",
                secondary=['Mixtape/Street'],
            )
        ],
        {'ciyr': [_mb_track(1, 'Legend', 'IYRTITL', duration=241)]},
    )
    db, watch = _watch(tmp_path, new_only=True)
    dl = _FakeDownloader(tmp_path)

    # The first sweep records the baseline; the second has nothing new.
    _sweep(db, watch, dl, ON)
    _sweep(db, watch, dl, ON)

    assert dl.calls == []
    assert 'mb:ciyr' in db.get_seen_album_ids(watch.id)


def test_a_group_without_an_official_edition_is_skipped_for_good(
    monkeypatch, tmp_path
):
    _patch(monkeypatch, [], {})
    _deezer(monkeypatch, [], {})
    mb = _MusicBrainz(
        monkeypatch,
        [_rg('fan', 'Heartbreak Drake', secondary=['Mixtape/Street'])],
        {'fan': None},
    )
    db, watch = _watch(tmp_path)
    dl = _FakeDownloader(tmp_path)

    _sweep(db, watch, dl, ON)
    _sweep(db, watch, dl, ON)

    assert dl.calls == []
    # Asked once, then known: not asked again on every check.
    assert mb.track_calls == ['fan']
    assert 'mb:fan' in db.get_seen_album_ids(watch.id)


def test_settings_default_to_musicbrainz_on():
    assert api.DEFAULT_SETTINGS['artist_watch_musicbrainz'] is True
    assert musicbrainz.kinds_from_setting(
        api.DEFAULT_SETTINGS['artist_watch_musicbrainz_kinds']
    ) == {'mixtape/street', 'soundtrack'}
