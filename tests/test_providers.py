"""Tests for YouTube Music provider helpers."""

from __future__ import annotations

import pytest

from downtify import providers
from downtify.providers import (
    _albums_match,
    _artists_overlap,
    _find_match_via_album,
    _pick_best,
    _titles_match,
    album_tracks_from_browse_id,
    enrich_from_match,
    find_match,
    parse_youtube_url,
    search_albums,
    song_from_video_id,
    youtube_music_track_index_for_match,
)


def _song_row(title, artist, album, duration, video_id):
    return {
        'videoId': video_id,
        'title': title,
        'artists': [{'name': artist}],
        'album': {'name': album},
        'duration_seconds': duration,
    }


@pytest.fixture(autouse=True)
def clear_ytm_album_cache():
    """Isolate tests that manipulate the in-memory get_album cache."""

    providers._album_track_cache.clear()
    providers._album_meta_cache.clear()
    providers._album_browse_search_cache.clear()
    providers._album_search_artist_cache.clear()
    yield
    providers._album_track_cache.clear()
    providers._album_meta_cache.clear()
    providers._album_browse_search_cache.clear()
    providers._album_search_artist_cache.clear()


def test_enrich_from_match_backfills_artists_when_empty():
    song = {
        'name': 'Test Song',
        'artists': [],
        'source': 'spotify',
        'song_id': 'spotifyTrack1',
    }
    match = {
        'videoId': 'yt123',
        'title': 'Test Song',
        'artists': [{'name': 'AliasFromYT'}],
        'thumbnails': [{'url': 'https://example.com/t.jpg'}],
        'duration_seconds': 180,
    }
    out = enrich_from_match(song, match)
    assert out['artists'] == ['AliasFromYT']
    assert out['artist'] == 'AliasFromYT'


def test_enrich_from_match_does_not_replace_existing_artists():
    song = {
        'name': 'Test Song',
        'artists': ['KeepMe'],
        'source': 'spotify',
    }
    match = {
        'videoId': 'yt123',
        'title': 'Test Song',
        'artists': [{'name': 'Other'}],
    }
    out = enrich_from_match(song, match)
    assert out['artists'] == ['KeepMe']


def test_enrich_from_match_sets_track_index_from_album(monkeypatch):
    def fake_cached(browse_id: str):
        assert browse_id == 'MPREb_test'
        return (
            [
                {'videoId': 'aaaaaaaaaaa', 'trackNumber': 1},
                {'videoId': 'bbbbbbbbbbb', 'trackNumber': 2},
            ],
            12,
        )

    monkeypatch.setattr(
        providers, '_cached_album_tracks_and_count', fake_cached
    )
    match = {
        'videoId': 'bbbbbbbbbbb',
        'title': 'B-side',
        'album': {'name': 'Test LP', 'id': 'MPREb_test'},
    }
    out = enrich_from_match({'name': 'B-side', 'source': 'spotify'}, match)
    assert out['track_number'] == 2
    assert out['album_track_total'] == 12


def test_youtube_music_track_number_zero_falls_back_to_list_position(
    monkeypatch,
):
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _browse_id: (
            [{'videoId': 'ccccccccccc', 'trackNumber': 0}],
            None,
        ),
    )
    n, total = youtube_music_track_index_for_match(
        {'videoId': 'ccccccccccc', 'album': {'name': '', 'id': 'x'}},
        None,
    )
    assert n == 1
    assert total == 1


def test_youtube_music_no_album_id_returns_no_track(monkeypatch):
    monkeypatch.setattr(
        providers, '_album_browse_id_from_search', lambda *_: ''
    )
    assert youtube_music_track_index_for_match(
        {'videoId': 'solo', 'album': {'name': 'Loose singles only'}},
        None,
    ) == (None, None)


def test_enrich_preserves_preset_track_number(monkeypatch):
    def fake_cached(_browse_id: str):
        return ([{'videoId': 'vin', 'trackNumber': 2}], 9)

    monkeypatch.setattr(
        providers, '_cached_album_tracks_and_count', fake_cached
    )
    monkeypatch.setattr(
        providers, '_album_browse_id', lambda *_args, **_kw: 'any'
    )
    out = enrich_from_match(
        {'track_number': 7, 'album_track_total': 11},
        {'videoId': 'vin', 'album': {'id': 'mbid'}},
    )
    assert out['track_number'] == 7
    assert out['album_track_total'] == 11


# ── _artists_overlap ───────────────────────────────────────────────────────────


def test_artists_overlap_true_when_shared_artist():
    result = {'artists': [{'name': 'Mica Ferreira'}]}
    assert _artists_overlap(['Mica Ferreira'], result)


def test_artists_overlap_false_for_unrelated_artist():
    result = {'artists': [{'name': 'Kid Spirit'}, {'name': 'Maggie Szabo'}]}
    assert not _artists_overlap(['Mica Ferreira'], result)


def test_artists_overlap_true_when_any_credited_artist_matches():
    # A multi-artist target (e.g. a feature) only needs one match.
    result = {'artists': [{'name': 'Solenne'}]}
    assert _artists_overlap(['Solenne', 'Mica Ferreira'], result)


def test_artists_overlap_vacuously_true_without_target_artists():
    result = {'artists': [{'name': 'Anyone'}]}
    assert _artists_overlap([], result)
    assert _artists_overlap(None, result)


def test_artists_overlap_case_insensitive():
    result = {'artists': [{'name': 'MICA FERREIRA'}]}
    assert _artists_overlap(['mica ferreira'], result)


# ── _albums_match ─────────────────────────────────────────────────────────────


def test_albums_match_exact_casefold():
    assert _albums_match('Equilibristi', 'equilibristi')


def test_albums_match_tolerates_cosmetic_edition_suffix():
    # Regression: "Amber Field" must still match "Amber Field (Deluxe)"
    # — a reissue is the same release, not a different one.
    assert _albums_match('Amber Field', 'Amber Field (Deluxe)')
    assert _albums_match('Equilibristi', 'Equilibristi (Deluxe Edition)')
    assert _albums_match('Unplugged', 'Unplugged [Remastered 2011]')


def test_albums_match_rejects_version_qualified_suffix():
    # "Live" (and friends) mark a genuinely different recording, so
    # unlike a cosmetic edition tag it is never tolerated.
    assert not _albums_match('Nevermind', 'Nevermind - Live')


def test_albums_match_rejects_different_albums():
    assert not _albums_match(
        'Equilibristi', 'Ferretti Bruno Conti Live al Foro Italico'
    )


def test_albums_match_short_names_do_not_collide():
    assert not _albums_match('RIP', 'Drip')


def test_albums_match_empty_is_false():
    assert not _albums_match('', 'Equilibristi')
    assert not _albums_match('Equilibristi', '')


# ── _pick_best album disambiguation ───────────────────────────────────────────


def test_pick_best_prefers_correct_album_over_closer_duration():
    # The "La mia strada" case: the wrong (live) take has the *closer*
    # duration, so without the album signal it would win.
    correct = _song_row(
        'La mia strada', 'Marco Ferretti', 'Equilibristi', 240, 'right'
    )
    wrong = _song_row(
        'La mia strada',
        'Marco Ferretti',
        'Ferretti Bruno Conti Live al Foro Italico',
        238,
        'wrong',
    )
    best = _pick_best(
        [wrong, correct],
        target_duration=238,
        target_title='La mia strada',
        target_artists=['Marco Ferretti'],
        target_album='Equilibristi',
    )
    assert best['videoId'] == 'right'


def test_pick_best_without_album_is_unchanged():
    # No target album → duration remains the tiebreaker (legacy behaviour).
    a = _song_row('La mia strada', 'Marco Ferretti', 'Equilibristi', 240, 'a')
    b = _song_row('La mia strada', 'Marco Ferretti', 'Live', 238, 'b')
    best = _pick_best(
        [a, b],
        target_duration=238,
        target_title='La mia strada',
        target_artists=['Marco Ferretti'],
    )
    assert best['videoId'] == 'b'


def test_pick_best_prefers_exact_album_match():
    correct = _song_row('Song', 'Artist', 'The Album', 200, 'right')
    other = _song_row('Song', 'Artist', 'Some Compilation', 200, 'other')
    best = _pick_best(
        [other, correct],
        target_duration=200,
        target_title='Song',
        target_artists=['Artist'],
        target_album='The Album',
    )
    assert best['videoId'] == 'right'


def test_pick_best_does_not_penalise_albumless_video_results():
    # `videos`-filter fallback rows have no album; they must stay eligible
    # when nothing else matches the album.
    only = {
        'videoId': 'vid',
        'title': 'Song',
        'artists': [{'name': 'Artist'}],
        'duration_seconds': 200,
    }
    best = _pick_best(
        [only],
        target_duration=200,
        target_title='Song',
        target_artists=['Artist'],
        target_album='Some Album',
    )
    assert best['videoId'] == 'vid'


# ── _titles_match ─────────────────────────────────────────────────────────────


def test_titles_match_exact_casefold():
    assert _titles_match('Quiet Static', 'quiet static')


def test_titles_match_tolerates_only_whitespace_differences():
    assert _titles_match('Quiet  Static', 'Quiet Static')


def test_titles_match_tolerates_cosmetic_suffix():
    # A cosmetic edition tag (remaster, radio edit, …) does not make it
    # a different recording, so the bare title still matches.
    assert _titles_match(
        'Quiet Static - Remastered 2023', 'Quiet Static - Remastered 2023'
    )
    assert _titles_match('Quiet Static - Remastered 2023', 'Quiet Static')
    assert _titles_match('Song (Radio Edit)', 'Song')


def test_titles_match_rejects_unrelated_titles():
    assert not _titles_match('Quiet Static', 'Paper Weight')
    assert not _titles_match('Quiet Static', 'Faint Signal')


def test_titles_match_short_names_do_not_collide():
    assert not _titles_match('U', 'You & We')


def test_titles_match_rejects_containment():
    # Regression: "Storm - Live" must not match "A Perfect Storm" just
    # because the base name ("storm") is a substring of the candidate.
    assert not _titles_match('Storm - Live', 'A Perfect Storm')
    assert not _titles_match('Storm', 'A Perfect Storm')


def test_titles_match_live_target_rejects_studio_candidate():
    # Regression: "Wait It Out - Live" was matching the plain studio
    # "Wait It Out" hit, downloading the wrong (non-live) recording
    # under live metadata.
    assert not _titles_match('Wait It Out - Live', 'Wait It Out')


def test_titles_match_rejects_differently_formatted_live_tag():
    # Deliberately strict: even a genuine live take is rejected if
    # YouTube Music doesn't spell the qualifier exactly like Spotify does.
    assert not _titles_match('Wait It Out - Live', 'Wait It Out (Live)')
    assert _titles_match('Wait It Out - Live', 'Wait It Out - Live')


def test_titles_match_studio_target_rejects_live_candidate():
    # The mirror case: a plain studio target must not accept a live take.
    assert not _titles_match('Wait It Out', 'Wait It Out (Live)')


def test_titles_match_rejects_remix_for_plain_target():
    # Regression: "Fernglow" must not match "Fernglow (DJ Koze Remix)" — a
    # remix is a different recording, not just a different pressing.
    assert not _titles_match('Fernglow', 'Fernglow (DJ Koze Remix)')


def test_titles_match_qualifier_words_are_word_bounded():
    # The word "Olive" contains the letters "live" but is not the
    # qualifier "live" — the check on the extra suffix text must use
    # word boundaries, not a bare substring search.
    assert _titles_match('Storm', 'Storm (Olive Edition)')


# ── _pick_best rejects title-mismatched candidates ────────────────────────────


def test_pick_best_rejects_all_candidates_with_wrong_title():
    # Reproduces the "Quiet Static" bug: YouTube Music returns only unrelated
    # songs by the same artist with plausible durations/artist overlap, and
    # none of them should be accepted.
    candidates = [
        _song_row('Steps We Never Made', 'Mica Ferreira', '', 307, 'a'),
        _song_row('Faint Signal', 'Mica Ferreira', '', 161, 'b'),
        _song_row('Paper Weight', 'Mica Ferreira', '', 172, 'c'),
    ]
    best = _pick_best(
        candidates,
        target_duration=172,
        target_title='Quiet Static - Remastered 2023',
        target_artists=['Mica Ferreira'],
    )
    assert best is None


def test_pick_best_rejects_title_collision_across_unrelated_artists():
    # Regression: "Fallen Wires" exists as three unrelated songs
    # (Mica Ferreira's own bonus track, Solenne's "Nightfall" track, and a
    # Kid Spirit & Maggie Szabo single). None of the wrong-artist hits
    # should win just for having the closer duration to the target.
    kid_spirit = _song_row(
        'Fallen Wires', 'Kid Spirit', 'Fallen Wires', 165, 'wrong-close'
    )
    avicii = _song_row(
        'Fallen Wires', 'Solenne', 'Nightfall', 233, 'wrong-far'
    )
    best = _pick_best(
        [kid_spirit, avicii],
        target_duration=118,
        target_title='Fallen Wires',
        target_artists=['Mica Ferreira'],
    )
    assert best is None


def test_pick_best_accepts_featured_artist_not_in_candidate_list():
    # A target with multiple credited artists (e.g. a feature) must
    # still match a candidate that only lists one of them.
    candidate = _song_row('Fallen Wires', 'Solenne', 'Nightfall', 233, 'right')
    best = _pick_best(
        [candidate],
        target_duration=233,
        target_title='Fallen Wires',
        target_artists=['Solenne', 'Mica Ferreira'],
    )
    assert best['videoId'] == 'right'


def test_pick_best_rejects_containment_match():
    # Regression: "Storm - Live" was matching "A Perfect Storm" (an
    # unrelated song) via substring containment on the base title.
    candidates = [
        _song_row('A Perfect Storm', 'Mica Ferreira', '', 185, 'wrong'),
    ]
    best = _pick_best(
        candidates,
        target_duration=185,
        target_title='Storm - Live',
        target_artists=['Mica Ferreira'],
    )
    assert best is None


def test_pick_best_rejects_remix_when_no_plain_take_available():
    # Regression: "Fernglow" (from the "Amber Field (Deluxe)" bonus disc)
    # only turns up as "Fernglow (DJ Koze Remix)" on YouTube Music — a
    # different recording, so this must error rather than download it.
    candidates = [
        _song_row(
            'Fernglow (DJ Koze Remix)',
            'Mica Ferreira',
            'Amber Field (Deluxe)',
            363,
            'remix',
        ),
    ]
    best = _pick_best(
        candidates,
        target_duration=154,
        target_title='Fernglow',
        target_artists=['Mica Ferreira'],
        target_album='Amber Field',
    )
    assert best is None


def test_pick_best_accepts_deluxe_album_for_plain_target():
    # The album counterpart of the same regression: the correct plain
    # take lives on the "(Deluxe)" reissue and must still be accepted.
    candidates = [
        _song_row(
            'Fernglow', 'Mica Ferreira', 'Amber Field (Deluxe)', 154, 'right'
        ),
    ]
    best = _pick_best(
        candidates,
        target_duration=154,
        target_title='Fernglow',
        target_artists=['Mica Ferreira'],
        target_album='Amber Field',
    )
    assert best['videoId'] == 'right'


def test_pick_best_prefers_exact_title_match_over_studio_take():
    # Regression: "Wait It Out - Live" / "North Bend - Live" were matching
    # the plain studio hit from the Driftlight album instead of the actual
    # live recording, even when an exactly-titled live take was present
    # among the search results.
    studio = _song_row(
        'North Bend', 'Mica Ferreira', 'Driftlight', 441, 'studio'
    )
    live = _song_row(
        'North Bend - Live', 'Mica Ferreira', 'After Hours', 430, 'live'
    )
    best = _pick_best(
        [studio, live],
        target_duration=430,
        target_title='North Bend - Live',
        target_artists=['Mica Ferreira'],
    )
    assert best['videoId'] == 'live'


def test_pick_best_errors_out_when_only_studio_take_available():
    # No live-tagged candidate exists at all → must not silently fall
    # back to the studio recording.
    studio_only = [
        _song_row('Wait It Out', 'Mica Ferreira', 'Driftlight', 200, 'studio'),
    ]
    best = _pick_best(
        studio_only,
        target_duration=200,
        target_title='Wait It Out - Live',
        target_artists=['Mica Ferreira'],
    )
    assert best is None


def test_pick_best_accepts_title_matching_candidate_among_noise():
    candidates = [
        _song_row('Paper Weight', 'Mica Ferreira', '', 172, 'wrong'),
        _song_row(
            'Quiet Static - Remastered 2023',
            'Mica Ferreira',
            'Driftlight',
            172,
            'right',
        ),
    ]
    best = _pick_best(
        candidates,
        target_duration=172,
        target_title='Quiet Static - Remastered 2023',
        target_artists=['Mica Ferreira'],
        target_album='Driftlight',
    )
    assert best['videoId'] == 'right'


# ── find_match errors the song instead of downloading a mismatch ─────────────


class _FakeYTM:
    def __init__(self, results):
        self._results = results

    def search(self, query, filter=None, limit=10):
        return self._results


class _FakeYTMByFilter:
    """Routes ``search()`` results by the ``filter`` kwarg, so tests can
    tell find_match's staged search attempts (unfiltered top-result,
    `songs`, `videos`) apart."""

    def __init__(self, by_filter):
        self._by_filter = by_filter

    def search(self, query, filter=None, limit=10):
        return self._by_filter.get(filter, [])


def test_find_match_uses_unfiltered_top_result_when_present(monkeypatch):
    # Regression: "Fallen Wires (Remastered 2023)" (like "Held Together" and
    # "Hollow Anchor") is absent from the `songs`-filtered
    # search entirely, but resolves instantly as the unfiltered "Top
    # result" — find_match must try that first.
    top_result = {
        'category': 'Top result',
        'resultType': 'song',
        'videoId': 'right',
        'title': 'Fallen Wires',
        'artists': [{'name': 'Mica Ferreira'}],
        'duration_seconds': 118,
    }
    songs_filtered = [
        _song_row('Fallen Wires', 'Kid Spirit', 'Fallen Wires', 165, 'wrong'),
        _song_row('Fallen Wires', 'Solenne', 'Nightfall', 233, 'also-wrong'),
    ]
    fake = _FakeYTMByFilter({None: [top_result], 'songs': songs_filtered})
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    video_id, match = find_match({
        'name': 'Fallen Wires',
        'artists': ['Mica Ferreira'],
        'duration': 118,
    })
    assert video_id == 'right'


def test_find_match_ignores_non_song_or_video_top_result(monkeypatch):
    # An album/artist/playlist Top result must not short-circuit the
    # match; find_match should fall through to the filtered search.
    top_result = {
        'category': 'Top result',
        'resultType': 'artist',
        'browseId': 'x',
    }
    songs_filtered = [
        _song_row(
            'Fallen Wires', 'Mica Ferreira', 'Fallen Wires', 118, 'right'
        ),
    ]
    fake = _FakeYTMByFilter({None: [top_result], 'songs': songs_filtered})
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    video_id, match = find_match({
        'name': 'Fallen Wires',
        'artists': ['Mica Ferreira'],
        'duration': 118,
    })
    assert video_id == 'right'


def test_find_match_falls_through_when_top_result_fails_gates(monkeypatch):
    # Same strictness as everywhere else: a Top result that doesn't pass
    # the title/artist gates is not accepted just for being "Top result".
    top_result = {
        'category': 'Top result',
        'resultType': 'song',
        'videoId': 'wrong',
        'title': 'Something Else Entirely',
        'artists': [{'name': 'Unrelated Artist'}],
        'duration_seconds': 118,
    }
    songs_filtered = [
        _song_row(
            'Fallen Wires', 'Mica Ferreira', 'Fallen Wires', 118, 'right'
        ),
    ]
    fake = _FakeYTMByFilter({None: [top_result], 'songs': songs_filtered})
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    video_id, match = find_match({
        'name': 'Fallen Wires',
        'artists': ['Mica Ferreira'],
        'duration': 118,
    })
    assert video_id == 'right'


def test_find_match_returns_none_when_no_title_matches(monkeypatch):
    # Only the `songs` filter is exercised; `videos` fallback is unused here
    # since `songs` already returned non-empty results. No `album_name` is
    # given, so the album-tracklist fallback short-circuits immediately
    # rather than attempting a real network call.
    fake = _FakeYTM([
        _song_row('Steps We Never Made', 'Mica Ferreira', '', 307, 'a'),
        _song_row('Faint Signal', 'Mica Ferreira', '', 161, 'b'),
        _song_row('Paper Weight', 'Mica Ferreira', '', 172, 'c'),
    ])
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    video_id, match = find_match({
        'name': 'Quiet Static - Remastered 2023',
        'artists': ['Mica Ferreira'],
        'duration': 172,
    })
    assert video_id is None
    assert match is None


def test_find_match_rejects_title_collision_across_unrelated_artists(
    monkeypatch,
):
    # Regression: "Fallen Wires" turns up as three unrelated songs; the
    # fallback loop must reject the wrong-artist hits just like
    # _pick_best does, rather than picking "the first result" by title
    # alone. No album_name here, so the tracklist fallback is a no-op.
    fake = _FakeYTM([
        _song_row('Fallen Wires', 'Kid Spirit', 'Fallen Wires', 165, 'wrong'),
        _song_row('Fallen Wires', 'Solenne', 'Nightfall', 233, 'also-wrong'),
    ])
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    video_id, match = find_match({
        'name': 'Fallen Wires',
        'artists': ['Mica Ferreira'],
        'duration': 118,
    })
    assert video_id is None
    assert match is None


def test_find_match_falls_back_to_album_tracklist_when_search_misses(
    monkeypatch,
):
    # End-to-end reproduction of the "Held Together" bug: YouTube Music's own
    # "artist + title" search for "Mica Ferreira Held Together" never returns
    # "Held Together" among its results (confirmed against production logs) —
    # find_match must fall back to the album tracklist and still resolve
    # the correct video.
    fake = _FakeYTM([
        _song_row('Hollow Anchor', 'Mica Ferreira', 'Driftlight', 207, 'x'),
        _song_row('North Bend', 'Mica Ferreira', 'Driftlight', 162, 'y'),
    ])
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    monkeypatch.setattr(
        providers,
        '_find_match_via_album',
        lambda song: (
            'TzIpcPo8UIo',
            {'videoId': 'TzIpcPo8UIo', 'title': 'Held Together'},
        ),
    )
    video_id, match = find_match({
        'name': 'Held Together',
        'album_name': 'Driftlight',
        'artists': ['Mica Ferreira'],
        'duration': 226,
    })
    assert video_id == 'TzIpcPo8UIo'
    assert match['title'] == 'Held Together'


def test_find_match_returns_none_when_album_fallback_also_fails(monkeypatch):
    fake = _FakeYTM([
        _song_row('Paper Weight', 'Mica Ferreira', 'Driftlight', 172, 'c'),
    ])
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    monkeypatch.setattr(
        providers, '_find_match_via_album', lambda song: (None, None)
    )
    video_id, match = find_match({
        'name': 'Held Together',
        'album_name': 'Driftlight',
        'artists': ['Mica Ferreira'],
        'duration': 226,
    })
    assert video_id is None
    assert match is None


# ── _album_title_hints ────────────────────────────────────────────────────────


def test_album_title_hints_empty_when_nothing_known():
    # Regression: an empty `song['album_name']` used to still get appended
    # as a hint (an empty string isn't already "in" an empty list), which
    # degraded the later album search down to just the artist name.
    assert providers._album_title_hints({}, {'album_name': ''}) == []
    assert providers._album_title_hints({}, None) == []


def test_album_title_hints_includes_match_album():
    match = {'album': {'name': 'Driftlight'}}
    assert providers._album_title_hints(match, None) == ['Driftlight']


def test_album_title_hints_includes_song_album_name():
    assert providers._album_title_hints({}, {'album_name': 'Driftlight'}) == [
        'Driftlight'
    ]


def test_album_title_hints_dedupes_case_insensitively():
    match = {'album': {'name': 'Driftlight'}}
    song = {'album_name': 'driftlight'}
    assert providers._album_title_hints(match, song) == ['Driftlight']


# ── _album_browse_id_from_search ────────────────────────────────────────────────


def _album_result(browse_id, title, artist='Turf Rebels'):
    return {
        'title': title,
        'browseId': browse_id,
        'artists': [{'name': artist}],
    }


def test_album_browse_id_from_search_returns_empty_without_hints(
    monkeypatch,
):
    def _boom(*_a, **_kw):
        raise AssertionError(
            'should not search when there is no title hint at all'
        )

    monkeypatch.setattr(providers, '_ytm', _boom)
    assert not providers._album_browse_id_from_search({}, {'album_name': ''})


def test_album_browse_id_from_search_picks_matching_title_not_first_result(
    monkeypatch,
):
    # Regression: a real "Shut The Lights Off" (Turf Rebels) download got
    # tagged with the album "LOCAL HERO" instead. The albums search returned
    # LOCAL HERO first (most prominent/relevant Turf Rebels album) and the
    # matching code used to always accept whatever result came first,
    # regardless of whether its title matched what we were looking for.
    fake = _FakeYTM([
        _album_result('MPREb_fenian', 'LOCAL HERO'),
        _album_result('MPREb_brits', 'Shut The Lights Off'),
    ])
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    browse_id = providers._album_browse_id_from_search(
        {'artists': [{'name': 'Turf Rebels'}]},
        {'album_name': 'Shut The Lights Off', 'artists': ['Turf Rebels']},
    )
    assert browse_id == 'MPREb_brits'


def test_album_browse_id_from_search_returns_empty_when_no_title_matches(
    monkeypatch,
):
    # None of the search results actually match the hint we're looking
    # for — must not fall back to "the first result anyway".
    fake = _FakeYTM([
        _album_result('MPREb_fenian', 'LOCAL HERO'),
        _album_result('MPREb_fineart', 'Fine Art'),
    ])
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    browse_id = providers._album_browse_id_from_search(
        {'artists': [{'name': 'Turf Rebels'}]},
        {'album_name': 'Shut The Lights Off', 'artists': ['Turf Rebels']},
    )
    assert not browse_id


# ── _find_match_via_album ─────────────────────────────────────────────────────


def test_find_match_via_album_finds_track_missing_from_text_search(
    monkeypatch,
):
    monkeypatch.setattr(
        providers,
        '_album_browse_id_from_search',
        lambda *_a, **_kw: 'MPREb_r66dI91cUVz',
    )
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _browse_id: (
            [
                {'videoId': 'eAX90iTkiPk', 'title': 'Quiet Static'},
                {'videoId': 'TzIpcPo8UIo', 'title': 'Held Together'},
            ],
            10,
        ),
    )
    video_id, match = _find_match_via_album({
        'name': 'Held Together',
        'album_name': 'Driftlight',
        'artists': ['Mica Ferreira'],
    })
    assert video_id == 'TzIpcPo8UIo'
    assert match['title'] == 'Held Together'


def test_find_match_via_album_returns_none_without_album_name(monkeypatch):
    def _boom(*_a, **_kw):
        raise AssertionError('should not be called without an album name')

    monkeypatch.setattr(providers, '_album_browse_id_from_search', _boom)
    video_id, match = _find_match_via_album({
        'name': 'Held Together',
        'album_name': '',
        'artists': ['Mica Ferreira'],
    })
    assert video_id is None
    assert match is None


def test_find_match_via_album_returns_none_when_album_not_resolved(
    monkeypatch,
):
    monkeypatch.setattr(
        providers, '_album_browse_id_from_search', lambda *_a, **_kw: ''
    )
    video_id, match = _find_match_via_album({
        'name': 'Held Together',
        'album_name': 'Driftlight',
        'artists': ['Mica Ferreira'],
    })
    assert video_id is None
    assert match is None


def test_find_match_via_album_returns_none_when_title_absent_from_tracklist(
    monkeypatch,
):
    monkeypatch.setattr(
        providers,
        '_album_browse_id_from_search',
        lambda *_a, **_kw: 'MPREb_r66dI91cUVz',
    )
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _browse_id: (
            [{'videoId': 'eAX90iTkiPk', 'title': 'Quiet Static'}],
            10,
        ),
    )
    video_id, match = _find_match_via_album({
        'name': 'Held Together',
        'album_name': 'Driftlight',
        'artists': ['Mica Ferreira'],
    })
    assert video_id is None
    assert match is None


def test_find_match_via_album_still_rejects_version_mismatch(monkeypatch):
    # Same qualifier-aware strictness as the direct search path: a remix
    # sitting in the tracklist must not stand in for the plain studio cut.
    monkeypatch.setattr(
        providers,
        '_album_browse_id_from_search',
        lambda *_a, **_kw: 'MPREb_pWSf6KQ4ms0',
    )
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _browse_id: (
            [{'videoId': 'JOgU2SajisQ', 'title': 'Fernglow (DJ Koze Remix)'}],
            11,
        ),
    )
    video_id, match = _find_match_via_album({
        'name': 'Fernglow',
        'album_name': 'Amber Field',
        'artists': ['Mica Ferreira'],
    })
    assert video_id is None
    assert match is None


# ── parse_youtube_url ─────────────────────────────────────────────────────────


def test_parse_youtube_url_watch():
    assert parse_youtube_url(
        'https://music.youtube.com/watch?v=eAX90iTkiPk'
    ) == ('track', 'eAX90iTkiPk')


def test_parse_youtube_url_short_link():
    assert parse_youtube_url('https://youtu.be/eAX90iTkiPk') == (
        'track',
        'eAX90iTkiPk',
    )


def test_parse_youtube_url_plain_youtube_watch():
    assert parse_youtube_url(
        'https://www.youtube.com/watch?v=eAX90iTkiPk&t=5s'
    ) == ('track', 'eAX90iTkiPk')


def test_parse_youtube_url_album_browse():
    assert parse_youtube_url(
        'https://music.youtube.com/browse/MPREb_r66dI91cUVz'
    ) == ('album', 'MPREb_r66dI91cUVz')


def test_parse_youtube_url_album_playlist_form():
    assert parse_youtube_url(
        'https://music.youtube.com/playlist?list=OLAK5uy_l3gkZ6IpW'
    ) == ('album', 'OLAK5uy_l3gkZ6IpW')


def test_parse_youtube_url_rejects_non_youtube_url():
    assert parse_youtube_url('https://open.spotify.com/track/abc') is None


def test_parse_youtube_url_rejects_empty_string():
    assert parse_youtube_url('') is None


# ── _split_combined_featuring_artist ────────────────────────────────────────────


@pytest.mark.parametrize(
    'combined_name',
    [
        'Nova Ashworth feat. Wexler',
        'Nova Ashworth feat Wexler',
        'Nova Ashworth featuring Wexler',
        'Nova Ashworth ft. Wexler',
        'Nova Ashworth ft Wexler',
    ],
)
def test_split_combined_featuring_artist_recognizes_common_separators(
    combined_name,
):
    # Regression: YouTube Music sometimes returns a featuring track's
    # artists as a single combined-name entry (no separate channel id)
    # instead of one dict per artist — this used to land the track in the
    # wrong artist folder and tag it with the raw combined string.
    result = providers._split_combined_featuring_artist(
        [combined_name], ['Nova Ashworth']
    )
    assert result == ['Nova Ashworth', 'Wexler']


@pytest.mark.parametrize(
    'combined_name',
    [
        # "&"/"and"/","/"with"/"x" are deliberately NOT treated as
        # featuring separators — they're too common inside real band
        # names (e.g. "Salt, Bone & Ash", "Harbor and the Wren") to
        # split safely even with the known-album-artist anchor.
        'Nova Ashworth & Wexler',
        'Nova Ashworth and Wexler',
        'Nova Ashworth, Wexler',
        'Nova Ashworth with Wexler',
        'Nova Ashworth x Wexler',
    ],
)
def test_split_combined_featuring_artist_ignores_ambiguous_separators(
    combined_name,
):
    result = providers._split_combined_featuring_artist(
        [combined_name], ['Nova Ashworth']
    )
    assert result == [combined_name]


def test_split_combined_featuring_artist_leaves_unrelated_name_alone():
    # Only split when prefixed by a *known* album artist — an unrelated
    # name that happens to contain "feat." must be left alone.
    result = providers._split_combined_featuring_artist(
        ['Random Artist feat. Someone'], ['Nova Ashworth']
    )
    assert result == ['Random Artist feat. Someone']


def test_split_combined_featuring_artist_leaves_multi_artist_list_alone():
    result = providers._split_combined_featuring_artist(
        ['Nova Ashworth', 'KYE'], ['Nova Ashworth']
    )
    assert result == ['Nova Ashworth', 'KYE']


def test_split_combined_featuring_artist_no_album_artists_known():
    result = providers._split_combined_featuring_artist(
        ['Nova Ashworth feat. Wexler'], []
    )
    assert result == ['Nova Ashworth feat. Wexler']


# ── album_tracks_from_browse_id ────────────────────────────────────────────────


def _album_track_row(video_id, title, track_number, artist='Mica Ferreira'):
    return {
        'videoId': video_id,
        'title': title,
        'artists': [{'name': artist}],
        'trackNumber': track_number,
        'duration_seconds': 200,
        'isExplicit': False,
    }


def test_album_tracks_from_browse_id_resolves_full_tracklist(monkeypatch):
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _browse_id: (
            [
                _album_track_row('aaaaaaaaaaa', 'Quiet Static', 1),
                _album_track_row('bbbbbbbbbbb', 'Held Together', 2),
            ],
            10,
        ),
    )
    monkeypatch.setattr(
        providers,
        '_cached_album_meta',
        lambda _browse_id: {
            'title': 'Driftlight',
            'year': '2003',
            'thumbnails': [{'url': 'https://img/cover.jpg'}],
            'type': 'Album',
        },
    )
    songs = album_tracks_from_browse_id('MPREb_r66dI91cUVz')
    assert len(songs) == 2
    assert songs[0]['name'] == 'Quiet Static'
    assert songs[0]['album_name'] == 'Driftlight'
    assert songs[0]['track_number'] == 1
    assert songs[0]['album_track_total'] == 10
    assert songs[0]['year'] == '2003'
    assert songs[0]['source'] == 'youtube'
    assert songs[0]['song_id'] == 'aaaaaaaaaaa'
    assert songs[0]['release_type'] == 'Album'
    assert songs[1]['name'] == 'Held Together'
    assert songs[1]['track_number'] == 2


def test_album_tracks_from_browse_id_splits_combined_featuring_artist(
    monkeypatch,
):
    # A featuring track using an unambiguous separator ("feat.") gets its
    # combined artist name split into the album's own artist plus the
    # featured one.
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _bid: (
            [
                _album_track_row(
                    'aaaaaaaaaaa', 'PULSE WIRE', 1, artist='Nova Ashworth'
                ),
                {
                    'videoId': 'bbbbbbbbbbb',
                    'title': 'DUSK ROW',
                    'artists': [{'name': 'Nova Ashworth feat. Wexler'}],
                    'trackNumber': 2,
                    'duration_seconds': 233,
                    'isExplicit': False,
                },
            ],
            2,
        ),
    )
    monkeypatch.setattr(
        providers,
        '_cached_album_meta',
        lambda _bid: {
            'title': 'NORTHFIRE & THE QUIET STORM',
            'artists': ['Nova Ashworth'],
        },
    )
    songs = album_tracks_from_browse_id('MPREb_nQ0wPNHCFH9')
    hellstar = next(s for s in songs if s['name'] == 'DUSK ROW')
    stampede = next(s for s in songs if s['name'] == 'PULSE WIRE')
    assert hellstar['artists'] == ['Nova Ashworth', 'Wexler']
    assert hellstar['artist'] == 'Nova Ashworth, Wexler'
    # The album artist tag must stay consistent across the whole album,
    # regardless of a track's own (possibly multi-artist) `artists` list.
    assert hellstar['album_artist'] == 'Nova Ashworth'
    assert stampede['album_artist'] == 'Nova Ashworth'


def test_album_tracks_from_browse_id_album_artist_consistent_even_when_unsplit(
    monkeypatch,
):
    # Regression: an actual "NORTHFIRE & THE QUIET STORM" track came
    # back from YouTube Music with a single combined artist entry
    # "Nova Ashworth & Wexler" instead of two separate artist dicts. "&"
    # is intentionally not auto-split (too ambiguous — see the
    # ignores_ambiguous_separators tests), so `artists` stays as the raw
    # combined string. `album_artist` must still stay consistent with the
    # rest of the album, independent of whether the track's own artists
    # got split — that's what actually fixes the folder/tag mismatch.
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _bid: (
            [
                _album_track_row(
                    'aaaaaaaaaaa', 'PULSE WIRE', 1, artist='Nova Ashworth'
                ),
                {
                    'videoId': 'bbbbbbbbbbb',
                    'title': 'DUSK ROW',
                    'artists': [{'name': 'Nova Ashworth & Wexler'}],
                    'trackNumber': 2,
                    'duration_seconds': 233,
                    'isExplicit': False,
                },
            ],
            2,
        ),
    )
    monkeypatch.setattr(
        providers,
        '_cached_album_meta',
        lambda _bid: {
            'title': 'NORTHFIRE & THE QUIET STORM',
            'artists': ['Nova Ashworth'],
        },
    )
    songs = album_tracks_from_browse_id('MPREb_nQ0wPNHCFH9')
    hellstar = next(s for s in songs if s['name'] == 'DUSK ROW')
    stampede = next(s for s in songs if s['name'] == 'PULSE WIRE')
    assert hellstar['artists'] == ['Nova Ashworth & Wexler']
    assert hellstar['album_artist'] == 'Nova Ashworth'
    assert stampede['album_artist'] == 'Nova Ashworth'


def test_album_tracks_from_browse_id_propagates_single_release_type(
    monkeypatch,
):
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _bid: ([_album_track_row('aaaaaaaaaaa', 'LOCAL HERO', 1)], 3),
    )
    monkeypatch.setattr(
        providers,
        '_cached_album_meta',
        lambda _bid: {'title': 'LOCAL HERO', 'type': 'Single'},
    )
    songs = album_tracks_from_browse_id('MPREb_8qovY23NPvW')
    assert songs[0]['release_type'] == 'Single'


def test_album_tracks_from_browse_id_missing_type_defaults_empty(
    monkeypatch,
):
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _bid: ([_album_track_row('aaaaaaaaaaa', 'Track', 1)], 1),
    )
    monkeypatch.setattr(
        providers, '_cached_album_meta', lambda _bid: {'title': 'No Type'}
    )
    songs = album_tracks_from_browse_id('MPREb_notype')
    assert not songs[0]['release_type']


def test_album_tracks_from_browse_id_converts_playlist_id(monkeypatch):
    calls = []

    class _Fake:
        @staticmethod
        def get_album_browse_id(playlist_id):
            calls.append(playlist_id)
            return 'MPREb_resolved'

    monkeypatch.setattr(providers, '_ytm', _Fake)
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda browse_id: (
            ([_album_track_row('aaaaaaaaaaa', 'Quiet Static', 1)], 1)
            if browse_id == 'MPREb_resolved'
            else ([], None)
        ),
    )
    monkeypatch.setattr(
        providers,
        '_cached_album_meta',
        lambda _browse_id: {'title': 'Driftlight'},
    )
    songs = album_tracks_from_browse_id('OLAK5uy_someplaylistid')
    assert calls == ['OLAK5uy_someplaylistid']
    assert len(songs) == 1
    assert songs[0]['album_name'] == 'Driftlight'


def test_album_tracks_from_browse_id_returns_empty_when_playlist_unresolvable(
    monkeypatch,
):
    class _Fake:
        @staticmethod
        def get_album_browse_id(playlist_id):
            return None

    monkeypatch.setattr(providers, '_ytm', _Fake)
    assert album_tracks_from_browse_id('OLAK5uy_bogus') == []


def test_album_tracks_from_browse_id_returns_empty_when_no_tracks(
    monkeypatch,
):
    monkeypatch.setattr(
        providers, '_cached_album_tracks_and_count', lambda _bid: ([], None)
    )
    assert album_tracks_from_browse_id('MPREb_empty') == []


def test_album_tracks_from_browse_id_skips_rows_without_video_id(monkeypatch):
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _bid: (
            [
                {'title': 'No video id here'},
                _album_track_row('aaaaaaaaaaa', 'Quiet Static', 1),
            ],
            2,
        ),
    )
    monkeypatch.setattr(
        providers, '_cached_album_meta', lambda _bid: {'title': 'Driftlight'}
    )
    songs = album_tracks_from_browse_id('MPREb_r66dI91cUVz')
    assert len(songs) == 1
    assert songs[0]['song_id'] == 'aaaaaaaaaaa'


# ── search_albums / _album_summary ────────────────────────────────────────────


def _album_search_row(browse_id, title, artist, year, release_type='Album'):
    return {
        'category': 'Albums',
        'resultType': 'album',
        'title': title,
        'browseId': browse_id,
        'year': year,
        'artists': [{'name': artist}],
        'thumbnails': [{'url': 'https://img/cover.jpg'}],
        'isExplicit': False,
        'type': release_type,
    }


def test_search_albums_returns_album_summaries(monkeypatch):
    fake = _FakeYTM([
        _album_search_row('MPREb_x', 'Driftlight', 'Mica Ferreira', '2003'),
    ])
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    albums = search_albums('Mica Ferreira Driftlight')
    assert len(albums) == 1
    assert albums[0]['album_id'] == 'MPREb_x'
    assert albums[0]['name'] == 'Driftlight'
    assert albums[0]['artist'] == 'Mica Ferreira'
    assert albums[0]['year'] == '2003'
    assert albums[0]['source'] == 'youtube'
    assert albums[0]['url'] == 'https://music.youtube.com/browse/MPREb_x'
    assert albums[0]['release_type'] == 'Album'


def test_search_albums_differentiates_single_and_ep(monkeypatch):
    # Regression: two same-titled releases by the same artist can be a
    # genuine Album and a Single (e.g. Turf Rebels's "LOCAL HERO" album vs. the
    # "LOCAL HERO" title-track single) — the type must reflect each one.
    fake = _FakeYTM([
        _album_search_row(
            'MPREb_album',
            'LOCAL HERO',
            'Turf Rebels',
            '2026',
            release_type='Album',
        ),
        _album_search_row(
            'MPREb_single',
            'LOCAL HERO',
            'Turf Rebels',
            '2026',
            release_type='Single',
        ),
        _album_search_row(
            'MPREb_ep',
            'Last Orders',
            'Turf Rebels',
            '2026',
            release_type='EP',
        ),
    ])
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    albums = search_albums('Turf Rebels')
    types = {a['album_id']: a['release_type'] for a in albums}
    assert types == {
        'MPREb_album': 'Album',
        'MPREb_single': 'Single',
        'MPREb_ep': 'EP',
    }


def test_album_summary_missing_type_defaults_empty():
    row = _album_search_row('MPREb_x', 'Driftlight', 'Mica Ferreira', '2003')
    del row['type']
    assert not providers._album_summary(row)['release_type']


def test_search_albums_skips_rows_without_browse_id(monkeypatch):
    fake = _FakeYTM([{'title': 'No browseId', 'artists': []}])
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    assert search_albums('anything') == []


def test_search_albums_empty_query_returns_empty_without_network(monkeypatch):
    def _boom(*_a, **_kw):
        raise AssertionError('should not search for an empty query')

    monkeypatch.setattr(providers, '_ytm', _boom)
    assert search_albums('   ') == []


def test_search_albums_caches_artist_for_later_album_artist_fallback(
    monkeypatch,
):
    fake = _FakeYTM([
        _album_search_row('MPREb_x', 'Driftlight', 'Mica Ferreira', '2003'),
    ])
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    search_albums('Mica Ferreira Driftlight')
    assert providers._album_search_artist_cache['MPREb_x'] == ['Mica Ferreira']


class _FakeYTMGetAlbum:
    def __init__(self, response):
        self._response = response

    def get_album(self, _browse_id):
        return self._response


def test_album_meta_falls_back_to_search_cached_artist_when_get_album_lacks_it(
    monkeypatch,
):
    # Regression: `get_album`'s own response doesn't always carry an
    # `artists` field, even though the earlier albums-filter search that
    # found this browse id already told us the artist — reuse it instead
    # of losing it and falling back to the "Various Artists" tag heuristic.
    providers._album_search_artist_cache['MPREb_nQ0wPNHCFH9'] = [
        'Nova Ashworth'
    ]
    monkeypatch.setattr(
        providers,
        '_ytm',
        lambda: _FakeYTMGetAlbum({
            'title': 'NORTHFIRE & THE QUIET STORM',
            'tracks': [_album_track_row('aaaaaaaaaaa', 'PULSE WIRE', 1)],
            # No 'artists' key at all in this get_album response.
        }),
    )
    tracks, _total = providers._cached_album_tracks_and_count(
        'MPREb_nQ0wPNHCFH9'
    )
    assert tracks
    meta = providers._cached_album_meta('MPREb_nQ0wPNHCFH9')
    assert meta['artists'] == ['Nova Ashworth']


def test_album_meta_prefers_get_album_artist_over_search_cache(monkeypatch):
    # get_album's own artists field, when present, wins over the (possibly
    # stale) search-time cache rather than being silently overridden.
    providers._album_search_artist_cache['MPREb_nQ0wPNHCFH9'] = ['Stale Name']
    monkeypatch.setattr(
        providers,
        '_ytm',
        lambda: _FakeYTMGetAlbum({
            'title': 'NORTHFIRE & THE QUIET STORM',
            'tracks': [_album_track_row('aaaaaaaaaaa', 'PULSE WIRE', 1)],
            'artists': [{'name': 'Nova Ashworth'}],
        }),
    )
    providers._cached_album_tracks_and_count('MPREb_nQ0wPNHCFH9')
    meta = providers._cached_album_meta('MPREb_nQ0wPNHCFH9')
    assert meta['artists'] == ['Nova Ashworth']


# ── song_from_video_id ────────────────────────────────────────────────────────


def test_song_from_video_id_enriches_with_catalog_match(monkeypatch):
    base_song = {
        'song_id': 'eAX90iTkiPk',
        'name': 'Quiet Static',
        'artists': ['Mica Ferreira'],
        'album_name': '',
        'cover_url': 'https://img/thumb.jpg',
        'duration': 172,
        'url': 'https://music.youtube.com/watch?v=eAX90iTkiPk',
        'explicit': False,
        'year': '',
        'release_date': '',
        'source': 'youtube',
    }
    monkeypatch.setattr(
        providers, '_song_from_video_details', lambda _vid: dict(base_song)
    )
    catalog_match = {
        'videoId': 'eAX90iTkiPk',
        'title': 'Quiet Static',
        'album': {'name': 'Driftlight', 'id': 'MPREb_r66dI91cUVz'},
    }
    monkeypatch.setattr(
        providers, 'find_match', lambda _song: ('eAX90iTkiPk', catalog_match)
    )
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _bid: ([{'videoId': 'eAX90iTkiPk', 'trackNumber': 1}], 10),
    )
    song = song_from_video_id('eAX90iTkiPk')
    assert song['album_name'] == 'Driftlight'
    assert song['track_number'] == 1
    assert song['album_track_total'] == 10
    # Identity fields describe the requested video, not the match.
    assert song['song_id'] == 'eAX90iTkiPk'
    assert song['source'] == 'youtube'
    assert song['url'] == 'https://music.youtube.com/watch?v=eAX90iTkiPk'


def test_song_from_video_id_falls_back_when_no_catalog_match(monkeypatch):
    base_song = {
        'song_id': 'xyz',
        'name': 'Some Upload',
        'artists': ['A Channel'],
        'album_name': '',
        'cover_url': '',
        'duration': 60,
        'url': 'https://music.youtube.com/watch?v=xyz',
        'explicit': False,
        'year': '',
        'release_date': '',
        'source': 'youtube',
    }
    monkeypatch.setattr(
        providers, '_song_from_video_details', lambda _vid: dict(base_song)
    )
    monkeypatch.setattr(providers, 'find_match', lambda _song: (None, None))
    song = song_from_video_id('xyz')
    assert song == base_song


def test_song_from_video_id_returns_early_without_a_title(monkeypatch):
    def _boom(_song):
        raise AssertionError('find_match must not run without a title')

    monkeypatch.setattr(
        providers,
        '_song_from_video_details',
        lambda _vid: {'song_id': 'xyz', 'name': ''},
    )
    monkeypatch.setattr(providers, 'find_match', _boom)
    song = song_from_video_id('xyz')
    assert song == {'song_id': 'xyz', 'name': ''}


def test_song_from_video_id_survives_find_match_exception(monkeypatch):
    base_song = {'song_id': 'xyz', 'name': 'Some Upload'}

    def _boom(_song):
        raise RuntimeError('network blew up')

    monkeypatch.setattr(
        providers, '_song_from_video_details', lambda _vid: dict(base_song)
    )
    monkeypatch.setattr(providers, 'find_match', _boom)
    song = song_from_video_id('xyz')
    assert song == base_song


# ── enrich_from_match album-name fallback via browse_id ───────────────────────


def test_enrich_from_match_backfills_album_name_via_browse_id(monkeypatch):
    # Regression: a search-derived `match` sometimes lacks `album.name`
    # even though `youtube_music_track_index_for_match` still manages to
    # resolve the album's browseId (via an albums-filter search) while
    # computing the track index. That browseId must be reused to
    # backfill the album title too, rather than leaving it empty.
    match = {'videoId': 'vidvidvidvi', 'title': 'Quiet Static', 'album': None}
    monkeypatch.setattr(
        providers, '_album_browse_id', lambda *_a, **_kw: 'MPREb_r66dI91cUVz'
    )
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _bid: ([{'videoId': 'vidvidvidvi', 'trackNumber': 1}], 10),
    )
    monkeypatch.setattr(
        providers, '_cached_album_title', lambda _bid: 'Driftlight'
    )
    out = enrich_from_match(
        {'name': 'Quiet Static', 'source': 'youtube'}, match
    )
    assert out['album_name'] == 'Driftlight'
    assert out['track_number'] == 1


def test_enrich_from_match_backfills_release_type_via_browse_id(monkeypatch):
    match = {'videoId': 'vidvidvidvi', 'title': 'Quiet Static', 'album': None}
    monkeypatch.setattr(
        providers, '_album_browse_id', lambda *_a, **_kw: 'MPREb_r66dI91cUVz'
    )
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _bid: ([{'videoId': 'vidvidvidvi', 'trackNumber': 1}], 10),
    )
    monkeypatch.setattr(
        providers, '_cached_album_title', lambda _bid: 'Driftlight'
    )
    monkeypatch.setattr(
        providers, '_cached_album_release_type', lambda _bid: 'Album'
    )
    out = enrich_from_match(
        {'name': 'Quiet Static', 'source': 'youtube'}, match
    )
    assert out['release_type'] == 'Album'


def test_enrich_from_match_preserves_existing_release_type(monkeypatch):
    # If the caller already knows the release type (e.g. it came from
    # album_tracks_from_browse_id), enrichment must not overwrite it.
    match = {
        'videoId': 'vidvidvidvi',
        'title': 'Quiet Static',
        'album': {'name': 'Driftlight', 'id': 'MPREb_r66dI91cUVz'},
    }
    monkeypatch.setattr(
        providers,
        '_cached_album_tracks_and_count',
        lambda _bid: ([{'videoId': 'vidvidvidvi', 'trackNumber': 1}], 10),
    )

    def _boom(_bid):
        raise AssertionError('should not be called when already set')

    monkeypatch.setattr(providers, '_cached_album_release_type', _boom)
    out = enrich_from_match(
        {
            'name': 'Quiet Static',
            'source': 'youtube',
            'release_type': 'Single',
        },
        match,
    )
    assert out['release_type'] == 'Single'
