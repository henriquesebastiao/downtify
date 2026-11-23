"""Tests for downtify/navidrome_ratings.py: dztnr's star scale, the
options sanitiser and the repeat-schedule rule. All pure and offline.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from downtify import deezer, navidrome_ratings
from downtify.navidrome import SubsonicError

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ('rank', 'stars'),
    [
        (0, 0),
        (9_999, 0),
        (10_000, 1),
        (99_999, 1),
        (100_000, 2),
        (299_999, 2),
        (300_000, 3),
        (599_999, 3),
        (600_000, 4),
        (849_999, 4),
        (850_000, 5),
        (1_000_000, 5),
    ],
)
def test_absolute_stars_match_dztnr(rank, stars):
    assert navidrome_ratings.stars_from_rank(rank) == stars


@pytest.mark.parametrize(
    ('rank', 'top', 'stars'),
    [
        (800, 1000, 5),
        (799, 1000, 4),
        (600, 1000, 4),
        (400, 1000, 3),
        (200, 1000, 2),
        (199, 1000, 1),
        (1, 1000, 1),
        (0, 1000, 0),
        (500, None, 0),
        (500, 0, 0),
    ],
)
def test_relative_stars_match_dztnr(rank, top, stars):
    assert navidrome_ratings.stars_from_relative_rank(rank, top) == stars


def test_effective_settings_defaults_and_bad_values():
    assert navidrome_ratings.effective_settings(None) == {
        'repeat': 'off',
        'skip_rated': True,
        'skip_starred': False,
        'grading': 'absolute',
    }
    assert navidrome_ratings.effective_settings({
        'repeat': 'hourly',
        'grading': 'x',
        'skip_rated': 0,
    }) == {
        'repeat': 'off',
        'skip_rated': False,
        'skip_starred': False,
        'grading': 'absolute',
    }


def test_effective_settings_keeps_valid_values_and_drops_unknown_keys():
    assert navidrome_ratings.effective_settings({
        'repeat': 'monthly',
        'grading': 'album',
        'skip_starred': 1,
        'other': 'x',
    }) == {
        'repeat': 'monthly',
        'skip_rated': True,
        'skip_starred': True,
        'grading': 'album',
    }
    assert navidrome_ratings.effective_settings('nope') == (
        navidrome_ratings.effective_settings(None)
    )


def test_effective_settings_returns_a_fresh_dict():
    first = navidrome_ratings.effective_settings(None)
    first['repeat'] = 'daily'
    assert navidrome_ratings.effective_settings(None)['repeat'] == 'off'
    assert navidrome_ratings.DEFAULTS['repeat'] == 'off'


def test_next_run_at():
    weekly = {'repeat': 'weekly'}
    done = {'started_at': '2026-11-01T04:00:00+00:00', 'state': 'done'}
    failed = {**done, 'state': 'failed'}
    assert navidrome_ratings.next_run_at({'repeat': 'off'}, done) is None
    assert navidrome_ratings.next_run_at(weekly, None) == EPOCH
    assert navidrome_ratings.next_run_at(weekly, done) == datetime(
        2026, 11, 8, 4, tzinfo=timezone.utc
    )
    assert navidrome_ratings.next_run_at(weekly, failed) == datetime(
        2026, 11, 1, 10, tzinfo=timezone.utc
    )


@pytest.mark.parametrize(
    'last', [{}, {'started_at': None}, {'started_at': 'not a date'}]
)
def test_next_run_at_without_a_usable_last_run_is_due_now(last):
    assert navidrome_ratings.next_run_at({'repeat': 'daily'}, last) == EPOCH


def test_next_run_at_treats_naive_timestamps_as_utc():
    last = {'started_at': '2026-11-01T04:00:00', 'state': 'done'}
    assert navidrome_ratings.next_run_at({'repeat': 'daily'}, last) == (
        datetime(2026, 11, 2, 4, tzinfo=timezone.utc)
    )


def test_next_run_at_converts_offsets_to_utc():
    last = {'started_at': '2026-11-01T06:00:00+02:00', 'state': 'done'}
    assert navidrome_ratings.next_run_at({'repeat': 'daily'}, last) == (
        datetime(2026, 11, 2, 4, tzinfo=timezone.utc)
    )


@pytest.mark.parametrize('repeat', [[], {}, ['daily']])
def test_unhashable_repeat_is_treated_as_off(repeat):
    assert (
        navidrome_ratings.effective_settings({'repeat': repeat})['repeat']
        == 'off'
    )
    assert navidrome_ratings.next_run_at({'repeat': repeat}, None) is None


# --- the rating run ---------------------------------------------------------


class FakeClient:
    """A Navidrome stand-in: ``library`` maps artist name to a list of
    ``(album_id, album_name, album_artist, songs)``."""

    def __init__(self, library):
        self.library = library
        self.set_calls = []
        self.missing_albums = set()
        self.missing_songs = set()

    def artists(self):
        return [{'id': f'ar-{name}', 'name': name} for name in self.library]

    def _albums(self):
        seen = {}
        for albums in self.library.values():
            for album_id, name, artist, songs in albums:
                seen[album_id] = (name, artist, songs)
        return seen

    def artist_albums(self, artist_id):
        name = artist_id.removeprefix('ar-')
        return [
            {'id': album_id, 'name': album, 'song_count': len(songs)}
            for album_id, album, _artist, songs in self.library[name]
        ]

    def album(self, album_id):
        if album_id in self.missing_albums:
            raise SubsonicError('Data not found', 70)
        name, artist, songs = self._albums()[album_id]
        return {'id': album_id, 'name': name, 'artist': artist, 'songs': songs}

    def set_rating(self, song_id, rating):
        if song_id in self.missing_songs:
            raise SubsonicError('Data not found', 70)
        self.set_calls.append((song_id, rating))


def song(song_id, title, starred=False, rating=0):
    return {
        'id': song_id,
        'title': title,
        'starred': starred,
        'rating': rating,
    }


def one_album(*songs, artist='Drake'):
    return {artist: [('al1', 'Views', artist, list(songs))]}


class FakeDeezer:
    """``routes`` maps ``(url, q)`` to a payload, an exception, or a list
    of them answered in turn (the last one repeats)."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url, **params):
        self.calls.append((url, params))
        answer = self.routes.get((url, params.get('q')), {'data': []})
        if isinstance(answer, list):
            answer = answer.pop(0) if len(answer) > 1 else answer[0]
        if isinstance(answer, Exception):
            raise answer
        return answer


SEARCH = 'https://api.deezer.com/search'
ARTIST_SEARCH = 'https://api.deezer.com/search/artist'
ALBUM_SEARCH = 'https://api.deezer.com/search/album'


def hit(rank):
    return {'data': [{'rank': rank}]}


def make_run(monkeypatch, client, routes, **kwargs):
    fake = FakeDeezer(routes)
    monkeypatch.setattr(navidrome_ratings.deezer, '_get_json', fake)
    sleeps = []
    options = {**navidrome_ratings.DEFAULTS, **kwargs.pop('options', {})}
    run = navidrome_ratings.RatingRun(
        client, options, sleep=sleeps.append, **kwargs
    )
    return run, fake, sleeps


def queries(fake):
    return [params['q'] for _url, params in fake.calls]


def test_rates_every_song_with_absolute_stars(monkeypatch):
    client = FakeClient(one_album(song('s1', 'Hit'), song('s2', 'Deep')))
    routes = {
        (SEARCH, 'Drake Hit'): hit(900_000),
        (SEARCH, 'Drake Deep'): hit(50_000),
    }
    run, _fake, sleeps = make_run(monkeypatch, client, routes)
    summary = run.run()
    assert client.set_calls == [('s1', 5), ('s2', 1)]
    assert summary['state'] == 'done'
    assert summary['rated'] == 2
    assert summary['total'] == 2
    assert sleeps == [0.2, 0.2]


def test_skips_rated_and_starred_by_option(monkeypatch):
    songs = [
        song('s1', 'Rated', rating=3),
        song('s2', 'Starred', starred=True),
        song('s3', 'Plain'),
    ]
    routes = {
        (SEARCH, 'Drake Starred'): hit(900_000),
        (SEARCH, 'Drake Plain'): hit(900_000),
    }
    run, fake, _ = make_run(monkeypatch, FakeClient(one_album(*songs)), routes)
    assert run.run()['skipped'] == 1
    assert queries(fake) == ['Drake Starred', 'Drake Plain']

    client = FakeClient(one_album(*songs))
    run, fake, _ = make_run(
        monkeypatch, client, routes, options={'skip_starred': True}
    )
    assert run.run()['skipped'] == 2
    assert queries(fake) == ['Drake Plain']
    assert client.set_calls == [('s3', 5)]


def test_not_found_leaves_stars_alone(monkeypatch):
    client = FakeClient(one_album(song('s1', 'Nope')))
    run, _fake, _ = make_run(monkeypatch, client, {})
    summary = run.run()
    assert client.set_calls == []
    assert summary['not_found'] == 1
    assert summary['rated'] == 0
    assert summary['unmatched'] == ['Drake – Views – Nope']


def test_low_rank_clears_stars(monkeypatch):
    client = FakeClient(one_album(song('s1', 'Quiet', rating=3)))
    run, _fake, _ = make_run(
        monkeypatch,
        client,
        {(SEARCH, 'Drake Quiet'): hit(5_000)},
        options={'skip_rated': False},
    )
    summary = run.run()
    assert client.set_calls == [('s1', 0)]
    assert summary['rated'] == 1


def test_unchanged_stars_are_not_written_again(monkeypatch):
    songs = [song('s1', 'Same', rating=5), song('s2', 'Zero')]
    client = FakeClient(one_album(*songs))
    routes = {
        (SEARCH, 'Drake Same'): hit(900_000),
        (SEARCH, 'Drake Zero'): hit(5_000),
    }
    run, _fake, _ = make_run(
        monkeypatch, client, routes, options={'skip_rated': False}
    )
    summary = run.run()
    assert client.set_calls == []
    assert summary['rated'] == 2
    assert [c['stars'] for c in summary['changes']] == [5, 0]


def test_empty_library_is_done_with_zero_counts(monkeypatch):
    run, _fake, _ = make_run(monkeypatch, FakeClient({}), {})
    summary = run.run()
    assert summary['state'] == 'done'
    assert [
        summary[k] for k in ('total', 'rated', 'skipped', 'not_found')
    ] == [0, 0, 0, 0]
    assert summary['changes'] == summary['unmatched'] == []


def test_reference_top_of_zero_falls_back_to_absolute(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A')))
    top = 'https://api.deezer.com/artist/77/top'
    routes = {
        (ARTIST_SEARCH, 'Drake'): {'data': [{'id': 77, 'name': 'Drake'}]},
        (top, None): {'data': [{'rank': 0}]},
        (SEARCH, 'Drake A'): hit(900_000),
    }
    run, _fake, _ = make_run(
        monkeypatch, client, routes, options={'grading': 'artist'}
    )
    run.run()
    assert client.set_calls == [('s1', 5)]


def test_preview_sets_nothing(monkeypatch):
    client = FakeClient(one_album(song('s1', 'Hit', rating=2)))
    run, _fake, _ = make_run(
        monkeypatch,
        client,
        {(SEARCH, 'Drake Hit'): hit(900_000)},
        preview=True,
        options={'skip_rated': False},
    )
    summary = run.run()
    assert client.set_calls == []
    assert summary['preview'] is True
    assert summary['rated'] == 1
    assert summary['changes'] == [
        {
            'artist': 'Drake',
            'album': 'Views',
            'title': 'Hit',
            'rank': 900_000,
            'stars': 5,
            'was': 2,
        }
    ]


def test_artist_grading_uses_the_top_track(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A'), song('s2', 'B')))
    top = 'https://api.deezer.com/artist/77/top'
    routes = {
        (ARTIST_SEARCH, 'Drake'): {'data': [{'id': 77, 'name': 'Drake'}]},
        (top, None): {'data': [{'rank': 1000}, {'rank': 500}]},
        (SEARCH, 'Drake A'): hit(450),
        (SEARCH, 'Drake B'): hit(1000),
    }
    run, fake, _ = make_run(
        monkeypatch, client, routes, options={'grading': 'artist'}
    )
    run.run()
    assert client.set_calls == [('s1', 3), ('s2', 5)]
    assert [u for u, _p in fake.calls].count(ARTIST_SEARCH) == 1
    assert next(p for u, p in fake.calls if u == top) == {'limit': 100}


def test_artist_grading_without_reference_is_absolute_once(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A'), song('s2', 'B')))
    routes = {
        (SEARCH, 'Drake A'): hit(900_000),
        (SEARCH, 'Drake B'): hit(50_000),
    }
    run, fake, _ = make_run(
        monkeypatch, client, routes, options={'grading': 'artist'}
    )
    run.run()
    assert client.set_calls == [('s1', 5), ('s2', 1)]
    assert [u for u, _p in fake.calls].count(ARTIST_SEARCH) == 1


def test_album_grading_uses_the_album_tracks(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A'), song('s2', 'B')))
    tracks = 'https://api.deezer.com/album/9/tracks'
    routes = {
        (ALBUM_SEARCH, 'Drake Views'): {'data': [{'id': 9, 'title': 'Views'}]},
        (tracks, None): {'data': [{'rank': 200}, {'rank': 1000}]},
        (SEARCH, 'Drake A'): hit(500),
        (SEARCH, 'Drake B'): hit(100),
    }
    run, fake, _ = make_run(
        monkeypatch, client, routes, options={'grading': 'album'}
    )
    run.run()
    assert client.set_calls == [('s1', 3), ('s2', 1)]
    assert [u for u, _p in fake.calls].count(ALBUM_SEARCH) == 1


def test_artist_reference_skips_a_namesake_with_few_fans(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A')))
    top = 'https://api.deezer.com/artist/77/top'
    routes = {
        (ARTIST_SEARCH, 'Drake'): {
            'data': [
                {'id': 5, 'name': 'Drake', 'nb_fan': 201},
                {'id': 6, 'name': 'Drake Bell', 'nb_fan': 900_000},
                {'id': 77, 'name': 'Drake', 'nb_fan': 14_000_000},
            ]
        },
        (top, None): {'data': [{'rank': 1000}]},
        (SEARCH, 'Drake A'): hit(500),
    }
    run, fake, _ = make_run(
        monkeypatch, client, routes, options={'grading': 'artist'}
    )
    run.run()
    assert top in [u for u, _p in fake.calls]
    assert 'https://api.deezer.com/artist/5/top' not in [
        u for u, _p in fake.calls
    ]
    assert client.set_calls == [('s1', 3)]
    searched = next(p for u, p in fake.calls if u == ARTIST_SEARCH)
    assert searched == {'q': 'Drake', 'limit': 25}


def test_artist_without_an_exact_name_is_absolute(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A')))
    routes = {
        (ARTIST_SEARCH, 'Drake'): {
            'data': [{'id': 6, 'name': 'Drake Bell', 'nb_fan': 900_000}]
        },
        (SEARCH, 'Drake A'): hit(900_000),
    }
    run, fake, _ = make_run(
        monkeypatch, client, routes, options={'grading': 'artist'}
    )
    run.run()
    assert client.set_calls == [('s1', 5)]
    assert not [u for u, _p in fake.calls if u.endswith('/top')]


def test_album_reference_skips_a_single_with_another_title(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A')))
    mashup = 'https://api.deezer.com/album/1/tracks'
    tracks = 'https://api.deezer.com/album/9/tracks'
    routes = {
        (ALBUM_SEARCH, 'Drake Views'): {
            'data': [
                {'id': 1, 'title': 'Views Mashup'},
                {'id': 9, 'title': 'Views'},
            ]
        },
        (tracks, None): {'data': [{'rank': 1000}]},
        (SEARCH, 'Drake A'): hit(500),
    }
    run, fake, _ = make_run(
        monkeypatch, client, routes, options={'grading': 'album'}
    )
    run.run()
    urls = [u for u, _p in fake.calls]
    assert tracks in urls
    assert mashup not in urls
    assert client.set_calls == [('s1', 3)]
    searched = next(p for u, p in fake.calls if u == ALBUM_SEARCH)
    assert searched == {'q': 'Drake Views', 'limit': 25}


def test_album_without_an_exact_title_is_absolute(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A')))
    routes = {
        (ALBUM_SEARCH, 'Drake Views'): {
            'data': [{'id': 1, 'title': 'Views Mashup'}]
        },
        (SEARCH, 'Drake A'): hit(900_000),
    }
    run, fake, _ = make_run(
        monkeypatch, client, routes, options={'grading': 'album'}
    )
    run.run()
    assert client.set_calls == [('s1', 5)]
    assert not [u for u, _p in fake.calls if '/album/' in u]


def test_album_under_two_artists_is_rated_once(monkeypatch):
    shared = [song('s1', 'A')]
    library = {
        'Drake': [('al1', 'Views', 'Drake', shared)],
        'Future': [('al1', 'Views', 'Drake', shared)],
    }
    client = FakeClient(library)
    run, _fake, _ = make_run(
        monkeypatch, client, {(SEARCH, 'Drake A'): hit(900_000)}
    )
    summary = run.run()
    assert client.set_calls == [('s1', 5)]
    assert summary['total'] == 1


def test_deezer_failing_after_every_retry_stops_the_run(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A'), song('s2', 'B')))
    fail = ValueError('down')
    routes = {
        (SEARCH, 'Drake A'): hit(900_000),
        (SEARCH, 'Drake B'): [fail, fail],
    }
    run, _fake, sleeps = make_run(monkeypatch, client, routes)
    with pytest.raises(navidrome_ratings.DeezerUnavailable):
        run.run()
    assert client.set_calls == [('s1', 5)]
    # Every retry pause was waited out (in steps of at most 5 s) first.
    waited = sum(s for s in sleeps if s != navidrome_ratings.DEEZER_PAUSE)
    assert waited == sum(navidrome_ratings.RETRY_PAUSES)
    assert max(sleeps) <= 5.0


def test_one_failure_is_retried(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A')))
    routes = {(SEARCH, 'Drake A'): [ValueError('blip'), hit(900_000)]}
    run, _fake, sleeps = make_run(monkeypatch, client, routes)
    run.run()
    assert client.set_calls == [('s1', 5)]
    assert sleeps == [5.0, 0.2]


def test_cancel_returns_stopped_with_counts(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A'), song('s2', 'B')))
    routes = {
        (SEARCH, 'Drake A'): hit(900_000),
        (SEARCH, 'Drake B'): hit(900_000),
    }
    # One artist in the library pass, then one song before the stop.
    flags = iter([False, False, True])
    run, _fake, _ = make_run(
        monkeypatch, client, routes, cancelled=lambda: next(flags, True)
    )
    summary = run.run()
    assert summary['state'] == 'stopped'
    assert summary['rated'] == 1
    assert client.set_calls == [('s1', 5)]


def test_progress_reports_library_then_songs(monkeypatch):
    library = {
        'Drake': [('al1', 'Views', 'Drake', [song('s1', 'A')])],
        'Future': [('al2', 'Hndrxx', 'Future', [song('s2', 'B')])],
    }
    routes = {
        (SEARCH, 'Drake A'): hit(900_000),
        (SEARCH, 'Future B'): hit(900_000),
    }
    calls = []
    run, _fake, _ = make_run(
        monkeypatch,
        FakeClient(library),
        routes,
        progress=lambda *args: calls.append(args),
    )
    run.run()
    assert calls[:2] == [(1, 2, 'library'), (2, 2, 'library')]
    assert calls[-1] == (2, 2, 'rating')


def refused(code):
    return deezer.DeezerRefused('Deezer refused the request', code)


@pytest.mark.parametrize('grading', ['artist', 'album'])
def test_reference_refused_with_no_data_is_absolute(monkeypatch, grading):
    client = FakeClient(one_album(song('s1', 'A')))
    routes = {
        (ARTIST_SEARCH, 'Drake'): refused(800),
        (ALBUM_SEARCH, 'Drake Views'): refused(800),
        (SEARCH, 'Drake A'): hit(900_000),
    }
    run, _fake, sleeps = make_run(
        monkeypatch, client, routes, options={'grading': grading}
    )
    summary = run.run()
    assert summary['state'] == 'done'
    assert client.set_calls == [('s1', 5)]
    assert 5.0 not in sleeps


def test_reference_top_refused_is_absolute(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A')))
    top = 'https://api.deezer.com/album/9/tracks'
    routes = {
        (ALBUM_SEARCH, 'Drake Views'): {'data': [{'id': 9, 'title': 'Views'}]},
        (top, None): refused(800),
        (SEARCH, 'Drake A'): hit(900_000),
    }
    run, _fake, _ = make_run(
        monkeypatch, client, routes, options={'grading': 'album'}
    )
    run.run()
    assert client.set_calls == [('s1', 5)]


def test_song_search_refused_counts_as_not_found(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A'), song('s2', 'B')))
    routes = {
        (SEARCH, 'Drake A'): refused(800),
        (SEARCH, 'Drake B'): hit(900_000),
    }
    run, _fake, sleeps = make_run(monkeypatch, client, routes)
    summary = run.run()
    assert summary['state'] == 'done'
    assert summary['not_found'] == 1
    assert client.set_calls == [('s2', 5)]
    assert sleeps == [0.2, 0.2]


@pytest.mark.parametrize('code', [4, 700])
def test_quota_or_busy_every_time_is_unavailable(monkeypatch, code):
    client = FakeClient(one_album(song('s1', 'A')))
    routes = {(SEARCH, 'Drake A'): [refused(code)]}
    run, fake, sleeps = make_run(monkeypatch, client, routes)
    with pytest.raises(navidrome_ratings.DeezerUnavailable):
        run.run()
    assert len(fake.calls) == len(navidrome_ratings.RETRY_PAUSES) + 1
    assert sum(sleeps) == sum(navidrome_ratings.RETRY_PAUSES)


def test_a_few_failures_in_a_row_are_waited_out(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A')))
    down = ValueError('down')
    routes = {(SEARCH, 'Drake A'): [down, refused(4), down, hit(900_000)]}
    run, _fake, sleeps = make_run(monkeypatch, client, routes)
    summary = run.run()
    assert summary['state'] == 'done'
    assert client.set_calls == [('s1', 5)]
    # 5 + 15 + 30 s of waiting (in steps), then the usual pacing.
    assert sum(sleeps) == pytest.approx(50.2)


def test_stop_during_a_retry_wait_stops_without_failing(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A'), song('s2', 'B')))
    routes = {(SEARCH, 'Drake A'): [ValueError('down')]}
    stop = {'now': False}
    run, _fake, sleeps = make_run(
        monkeypatch, client, routes, cancelled=lambda: stop['now']
    )

    def sleep(seconds):
        sleeps.append(seconds)
        stop['now'] = True  # the user presses Stop during the wait

    run._sleep = sleep
    summary = run.run()
    assert summary['state'] == 'stopped'
    assert client.set_calls == []
    assert len(sleeps) == 1


def test_long_runs_rest_between_batches(monkeypatch):
    songs = [song(f's{n}', f'T{n}') for n in range(250)]
    client = FakeClient(one_album(*songs))
    run, fake, sleeps = make_run(monkeypatch, client, {})
    run.run()
    assert len(fake.calls) == 250
    # A rest before the 101st and the 201st call.
    rests = sum(sleeps) - 250 * navidrome_ratings.DEEZER_PAUSE
    assert rests == pytest.approx(2 * navidrome_ratings.BATCH_PAUSE)


def test_albums_a_previous_run_finished_are_skipped(monkeypatch):
    library = {
        'Drake': [('al1', 'Views', 'Drake', [song('s1', 'A')])],
        'Future': [('al2', 'Hndrxx', 'Future', [song('s2', 'B')])],
    }
    client = FakeClient(library)
    routes = {
        (SEARCH, 'Drake A'): hit(900_000),
        (SEARCH, 'Future B'): hit(900_000),
    }
    finished = []
    run, fake, _ = make_run(
        monkeypatch,
        client,
        routes,
        done_albums={'al1'},
        album_done=finished.append,
    )
    summary = run.run()
    assert queries(fake) == ['Future B']
    assert client.set_calls == [('s2', 5)]
    assert summary['skipped'] == 1
    assert finished == ['al2']


def test_an_album_cut_short_is_not_counted_as_finished(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A'), song('s2', 'B')))
    routes = {(SEARCH, 'Drake B'): [ValueError('down')]}
    finished = []
    run, _fake, _ = make_run(
        monkeypatch, client, routes, album_done=finished.append
    )
    with pytest.raises(navidrome_ratings.DeezerUnavailable):
        run.run()
    assert finished == []


def test_quota_once_is_retried(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A')))
    routes = {(SEARCH, 'Drake A'): [refused(4), hit(900_000)]}
    run, _fake, sleeps = make_run(monkeypatch, client, routes)
    run.run()
    assert client.set_calls == [('s1', 5)]
    assert sleeps == [5.0, 0.2]


def test_album_removed_during_the_run_is_skipped(monkeypatch):
    library = {
        'Drake': [
            ('al1', 'Views', 'Drake', [song('s1', 'A'), song('s2', 'B')]),
            ('al2', 'Care', 'Drake', [song('s3', 'C')]),
        ]
    }
    client = FakeClient(library)
    client.missing_albums.add('al1')
    calls = []
    run, _fake, _ = make_run(
        monkeypatch,
        client,
        {(SEARCH, 'Drake C'): hit(900_000)},
        progress=lambda *args: calls.append(args),
    )
    summary = run.run()
    assert summary['state'] == 'done'
    assert summary['total'] == 3
    assert summary['skipped'] == 2
    assert summary['rated'] == 1
    assert client.set_calls == [('s3', 5)]
    assert calls[-1] == (3, 3, 'rating')


def test_other_navidrome_errors_still_propagate(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A')))

    def boom(album_id):
        raise SubsonicError('Wrong username or password', 40)

    client.album = boom
    run, _fake, _ = make_run(monkeypatch, client, {})
    with pytest.raises(SubsonicError):
        run.run()


def test_song_removed_during_the_run_counts_as_skipped(monkeypatch):
    client = FakeClient(one_album(song('s1', 'A'), song('s2', 'B')))
    client.missing_songs.add('s1')
    routes = {
        (SEARCH, 'Drake A'): hit(900_000),
        (SEARCH, 'Drake B'): hit(900_000),
    }
    run, _fake, _ = make_run(monkeypatch, client, routes)
    summary = run.run()
    assert summary['state'] == 'done'
    assert summary['skipped'] == 1
    assert summary['rated'] == 1
    assert [c['title'] for c in summary['changes']] == ['B']
    assert client.set_calls == [('s2', 5)]
