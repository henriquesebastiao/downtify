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
    enrich_from_match,
    find_match,
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
    providers._album_browse_search_cache.clear()
    yield
    providers._album_track_cache.clear()
    providers._album_browse_search_cache.clear()


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
    result = {'artists': [{'name': 'José González'}]}
    assert _artists_overlap(['José González'], result)


def test_artists_overlap_false_for_unrelated_artist():
    result = {'artists': [{'name': 'Kid Spirit'}, {'name': 'Maggie Szabo'}]}
    assert not _artists_overlap(['José González'], result)


def test_artists_overlap_true_when_any_credited_artist_matches():
    # A multi-artist target (e.g. a feature) only needs one match.
    result = {'artists': [{'name': 'Avicii'}]}
    assert _artists_overlap(['Avicii', 'José González'], result)


def test_artists_overlap_vacuously_true_without_target_artists():
    result = {'artists': [{'name': 'Anyone'}]}
    assert _artists_overlap([], result)
    assert _artists_overlap(None, result)


def test_artists_overlap_case_insensitive():
    result = {'artists': [{'name': 'JOSÉ GONZÁLEZ'}]}
    assert _artists_overlap(['josé gonzález'], result)


# ── _albums_match ─────────────────────────────────────────────────────────────


def test_albums_match_exact_casefold():
    assert _albums_match('Acrobati', 'acrobati')


def test_albums_match_tolerates_cosmetic_edition_suffix():
    # Regression: "Local Valley" must still match "Local Valley (Deluxe)"
    # — a reissue is the same release, not a different one.
    assert _albums_match('Local Valley', 'Local Valley (Deluxe)')
    assert _albums_match('Acrobati', 'Acrobati (Deluxe Edition)')
    assert _albums_match('Unplugged', 'Unplugged [Remastered 2011]')


def test_albums_match_rejects_version_qualified_suffix():
    # "Live" (and friends) mark a genuinely different recording, so
    # unlike a cosmetic edition tag it is never tolerated.
    assert not _albums_match('Nevermind', 'Nevermind - Live')


def test_albums_match_rejects_different_albums():
    assert not _albums_match(
        'Acrobati', 'Fabi Silvestri Gazzè Live al Circo Massimo'
    )


def test_albums_match_short_names_do_not_collide():
    assert not _albums_match('RIP', 'Drip')


def test_albums_match_empty_is_false():
    assert not _albums_match('', 'Acrobati')
    assert not _albums_match('Acrobati', '')


# ── _pick_best album disambiguation ───────────────────────────────────────────


def test_pick_best_prefers_correct_album_over_closer_duration():
    # The "La mia casa" case: the wrong (live) take has the *closer*
    # duration, so without the album signal it would win.
    correct = _song_row(
        'La mia casa', 'Daniele Silvestri', 'Acrobati', 240, 'right'
    )
    wrong = _song_row(
        'La mia casa',
        'Daniele Silvestri',
        'Fabi Silvestri Gazzè Live al Circo Massimo',
        238,
        'wrong',
    )
    best = _pick_best(
        [wrong, correct],
        target_duration=238,
        target_title='La mia casa',
        target_artists=['Daniele Silvestri'],
        target_album='Acrobati',
    )
    assert best['videoId'] == 'right'


def test_pick_best_without_album_is_unchanged():
    # No target album → duration remains the tiebreaker (legacy behaviour).
    a = _song_row('La mia casa', 'Daniele Silvestri', 'Acrobati', 240, 'a')
    b = _song_row('La mia casa', 'Daniele Silvestri', 'Live', 238, 'b')
    best = _pick_best(
        [a, b],
        target_duration=238,
        target_title='La mia casa',
        target_artists=['Daniele Silvestri'],
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
    assert _titles_match('Slow Moves', 'slow moves')


def test_titles_match_tolerates_only_whitespace_differences():
    assert _titles_match('Slow  Moves', 'Slow Moves')


def test_titles_match_tolerates_cosmetic_suffix():
    # A cosmetic edition tag (remaster, radio edit, …) does not make it
    # a different recording, so the bare title still matches.
    assert _titles_match(
        'Slow Moves - Remastered 2023', 'Slow Moves - Remastered 2023'
    )
    assert _titles_match('Slow Moves - Remastered 2023', 'Slow Moves')
    assert _titles_match('Song (Radio Edit)', 'Song')


def test_titles_match_rejects_unrelated_titles():
    assert not _titles_match('Slow Moves', 'Just A Rock')
    assert not _titles_match('Slow Moves', 'How Low')


def test_titles_match_short_names_do_not_collide():
    assert not _titles_match('U', 'You & We')


def test_titles_match_rejects_containment():
    # Regression: "Storm - Live" must not match "A Perfect Storm" just
    # because the base name ("storm") is a substring of the candidate.
    assert not _titles_match('Storm - Live', 'A Perfect Storm')
    assert not _titles_match('Storm', 'A Perfect Storm')


def test_titles_match_live_target_rejects_studio_candidate():
    # Regression: "Save Your Day - Live" was matching the plain studio
    # "Save Your Day" hit, downloading the wrong (non-live) recording
    # under live metadata.
    assert not _titles_match('Save Your Day - Live', 'Save Your Day')


def test_titles_match_rejects_differently_formatted_live_tag():
    # Deliberately strict: even a genuine live take is rejected if
    # YouTube Music doesn't spell the qualifier exactly like Spotify does.
    assert not _titles_match('Save Your Day - Live', 'Save Your Day (Live)')
    assert _titles_match('Save Your Day - Live', 'Save Your Day - Live')


def test_titles_match_studio_target_rejects_live_candidate():
    # The mirror case: a plain studio target must not accept a live take.
    assert not _titles_match('Save Your Day', 'Save Your Day (Live)')


def test_titles_match_rejects_remix_for_plain_target():
    # Regression: "Tjomme" must not match "Tjomme (DJ Koze Remix)" — a
    # remix is a different recording, not just a different pressing.
    assert not _titles_match('Tjomme', 'Tjomme (DJ Koze Remix)')


def test_titles_match_qualifier_words_are_word_bounded():
    # The word "Olive" contains the letters "live" but is not the
    # qualifier "live" — the check on the extra suffix text must use
    # word boundaries, not a bare substring search.
    assert _titles_match('Storm', 'Storm (Olive Edition)')


# ── _pick_best rejects title-mismatched candidates ────────────────────────────


def test_pick_best_rejects_all_candidates_with_wrong_title():
    # Reproduces the "Slow Moves" bug: YouTube Music returns only unrelated
    # songs by the same artist with plausible durations/artist overlap, and
    # none of them should be accepted.
    candidates = [
        _song_row(
            'This Is How We Walk on the Moon', 'José González', '', 307, 'a'
        ),
        _song_row('How Low', 'José González', '', 161, 'b'),
        _song_row('Just A Rock', 'José González', '', 172, 'c'),
    ]
    best = _pick_best(
        candidates,
        target_duration=172,
        target_title='Slow Moves - Remastered 2023',
        target_artists=['José González'],
    )
    assert best is None


def test_pick_best_rejects_title_collision_across_unrelated_artists():
    # Regression: "Broken Arrows" exists as three unrelated songs
    # (José González's own bonus track, Avicii's "Stories" track, and a
    # Kid Spirit & Maggie Szabo single). None of the wrong-artist hits
    # should win just for having the closer duration to the target.
    kid_spirit = _song_row(
        'Broken Arrows', 'Kid Spirit', 'Broken Arrows', 165, 'wrong-close'
    )
    avicii = _song_row('Broken Arrows', 'Avicii', 'Stories', 233, 'wrong-far')
    best = _pick_best(
        [kid_spirit, avicii],
        target_duration=118,
        target_title='Broken Arrows',
        target_artists=['José González'],
    )
    assert best is None


def test_pick_best_accepts_featured_artist_not_in_candidate_list():
    # A target with multiple credited artists (e.g. a feature) must
    # still match a candidate that only lists one of them.
    candidate = _song_row('Broken Arrows', 'Avicii', 'Stories', 233, 'right')
    best = _pick_best(
        [candidate],
        target_duration=233,
        target_title='Broken Arrows',
        target_artists=['Avicii', 'José González'],
    )
    assert best['videoId'] == 'right'


def test_pick_best_rejects_containment_match():
    # Regression: "Storm - Live" was matching "A Perfect Storm" (an
    # unrelated song) via substring containment on the base title.
    candidates = [
        _song_row('A Perfect Storm', 'José González', '', 185, 'wrong'),
    ]
    best = _pick_best(
        candidates,
        target_duration=185,
        target_title='Storm - Live',
        target_artists=['José González'],
    )
    assert best is None


def test_pick_best_rejects_remix_when_no_plain_take_available():
    # Regression: "Tjomme" (from the "Local Valley (Deluxe)" bonus disc)
    # only turns up as "Tjomme (DJ Koze Remix)" on YouTube Music — a
    # different recording, so this must error rather than download it.
    candidates = [
        _song_row(
            'Tjomme (DJ Koze Remix)',
            'José González',
            'Local Valley (Deluxe)',
            363,
            'remix',
        ),
    ]
    best = _pick_best(
        candidates,
        target_duration=154,
        target_title='Tjomme',
        target_artists=['José González'],
        target_album='Local Valley',
    )
    assert best is None


def test_pick_best_accepts_deluxe_album_for_plain_target():
    # The album counterpart of the same regression: the correct plain
    # take lives on the "(Deluxe)" reissue and must still be accepted.
    candidates = [
        _song_row(
            'Tjomme', 'José González', 'Local Valley (Deluxe)', 154, 'right'
        ),
    ]
    best = _pick_best(
        candidates,
        target_duration=154,
        target_title='Tjomme',
        target_artists=['José González'],
        target_album='Local Valley',
    )
    assert best['videoId'] == 'right'


def test_pick_best_prefers_exact_title_match_over_studio_take():
    # Regression: "Save Your Day - Live" / "Crosses - Live" were matching
    # the plain studio hit from the Veneer album instead of the actual
    # live recording, even when an exactly-titled live take was present
    # among the search results.
    studio = _song_row('Crosses', 'José González', 'Veneer', 441, 'studio')
    live = _song_row(
        'Crosses - Live', 'José González', 'Live Sessions', 430, 'live'
    )
    best = _pick_best(
        [studio, live],
        target_duration=430,
        target_title='Crosses - Live',
        target_artists=['José González'],
    )
    assert best['videoId'] == 'live'


def test_pick_best_errors_out_when_only_studio_take_available():
    # No live-tagged candidate exists at all → must not silently fall
    # back to the studio recording.
    studio_only = [
        _song_row('Save Your Day', 'José González', 'Veneer', 200, 'studio'),
    ]
    best = _pick_best(
        studio_only,
        target_duration=200,
        target_title='Save Your Day - Live',
        target_artists=['José González'],
    )
    assert best is None


def test_pick_best_accepts_title_matching_candidate_among_noise():
    candidates = [
        _song_row('Just A Rock', 'José González', '', 172, 'wrong'),
        _song_row(
            'Slow Moves - Remastered 2023',
            'José González',
            'Veneer',
            172,
            'right',
        ),
    ]
    best = _pick_best(
        candidates,
        target_duration=172,
        target_title='Slow Moves - Remastered 2023',
        target_artists=['José González'],
        target_album='Veneer',
    )
    assert best['videoId'] == 'right'


# ── find_match errors the song instead of downloading a mismatch ─────────────


class _FakeYTM:
    def __init__(self, results):
        self._results = results

    def search(self, query, filter=None, limit=10):
        return self._results


def test_find_match_returns_none_when_no_title_matches(monkeypatch):
    # Only the `songs` filter is exercised; `videos` fallback is unused here
    # since `songs` already returned non-empty results. No `album_name` is
    # given, so the album-tracklist fallback short-circuits immediately
    # rather than attempting a real network call.
    fake = _FakeYTM([
        _song_row(
            'This Is How We Walk on the Moon', 'José González', '', 307, 'a'
        ),
        _song_row('How Low', 'José González', '', 161, 'b'),
        _song_row('Just A Rock', 'José González', '', 172, 'c'),
    ])
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    video_id, match = find_match({
        'name': 'Slow Moves - Remastered 2023',
        'artists': ['José González'],
        'duration': 172,
    })
    assert video_id is None
    assert match is None


def test_find_match_rejects_title_collision_across_unrelated_artists(
    monkeypatch,
):
    # Regression: "Broken Arrows" turns up as three unrelated songs; the
    # fallback loop must reject the wrong-artist hits just like
    # _pick_best does, rather than picking "the first result" by title
    # alone. No album_name here, so the tracklist fallback is a no-op.
    fake = _FakeYTM([
        _song_row(
            'Broken Arrows', 'Kid Spirit', 'Broken Arrows', 165, 'wrong'
        ),
        _song_row('Broken Arrows', 'Avicii', 'Stories', 233, 'also-wrong'),
    ])
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    video_id, match = find_match({
        'name': 'Broken Arrows',
        'artists': ['José González'],
        'duration': 118,
    })
    assert video_id is None
    assert match is None


def test_find_match_falls_back_to_album_tracklist_when_search_misses(
    monkeypatch,
):
    # End-to-end reproduction of the "Remain" bug: YouTube Music's own
    # "artist + title" search for "José González Remain" never returns
    # "Remain" among its results (confirmed against production logs) —
    # find_match must fall back to the album tracklist and still resolve
    # the correct video.
    fake = _FakeYTM([
        _song_row(
            'Deadweight on Velveteen', 'José González', 'Veneer', 207, 'x'
        ),
        _song_row('Crosses', 'José González', 'Veneer', 162, 'y'),
    ])
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    monkeypatch.setattr(
        providers,
        '_find_match_via_album',
        lambda song: (
            'TzIpcPo8UIo',
            {'videoId': 'TzIpcPo8UIo', 'title': 'Remain'},
        ),
    )
    video_id, match = find_match({
        'name': 'Remain',
        'album_name': 'Veneer',
        'artists': ['José González'],
        'duration': 226,
    })
    assert video_id == 'TzIpcPo8UIo'
    assert match['title'] == 'Remain'


def test_find_match_returns_none_when_album_fallback_also_fails(monkeypatch):
    fake = _FakeYTM([
        _song_row('Just A Rock', 'José González', 'Veneer', 172, 'c'),
    ])
    monkeypatch.setattr(providers, '_ytm', lambda: fake)
    monkeypatch.setattr(
        providers, '_find_match_via_album', lambda song: (None, None)
    )
    video_id, match = find_match({
        'name': 'Remain',
        'album_name': 'Veneer',
        'artists': ['José González'],
        'duration': 226,
    })
    assert video_id is None
    assert match is None


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
                {'videoId': 'eAX90iTkiPk', 'title': 'Slow Moves'},
                {'videoId': 'TzIpcPo8UIo', 'title': 'Remain'},
            ],
            10,
        ),
    )
    video_id, match = _find_match_via_album({
        'name': 'Remain',
        'album_name': 'Veneer',
        'artists': ['José González'],
    })
    assert video_id == 'TzIpcPo8UIo'
    assert match['title'] == 'Remain'


def test_find_match_via_album_returns_none_without_album_name(monkeypatch):
    def _boom(*_a, **_kw):
        raise AssertionError('should not be called without an album name')

    monkeypatch.setattr(providers, '_album_browse_id_from_search', _boom)
    video_id, match = _find_match_via_album({
        'name': 'Remain',
        'album_name': '',
        'artists': ['José González'],
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
        'name': 'Remain',
        'album_name': 'Veneer',
        'artists': ['José González'],
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
            [{'videoId': 'eAX90iTkiPk', 'title': 'Slow Moves'}],
            10,
        ),
    )
    video_id, match = _find_match_via_album({
        'name': 'Remain',
        'album_name': 'Veneer',
        'artists': ['José González'],
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
            [{'videoId': 'JOgU2SajisQ', 'title': 'Tjomme (DJ Koze Remix)'}],
            11,
        ),
    )
    video_id, match = _find_match_via_album({
        'name': 'Tjomme',
        'album_name': 'Local Valley',
        'artists': ['José González'],
    })
    assert video_id is None
    assert match is None
