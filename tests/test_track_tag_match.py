"""Tests for Spotify vs mutagen tag matching."""

from __future__ import annotations

from pathlib import Path

from downtify.track_tag_match import (
    candidate_adds_mix_variant,
    duration_tolerances_from_settings,
    media_duration_matches_mix_variant,
    media_duration_matches_song,
    remote_adds_unwanted_variant,
    remote_text_unacceptable,
    remote_title_unacceptable,
    snapshot_spotify_metadata,
    spotify_aligns_with_file_tags,
    strip_mix_suffix,
    verify_downloaded_file_matches_spotify,
    verify_youtube_download_file,
    youtube_probe_title_matches,
)


def test_snapshot_preserves_spotify_before_tag_overwrite():
    row = snapshot_spotify_metadata({
        'name': 'Light',
        'artists': ['Tom Jung'],
    })
    row['name'] = 'Wrong Title'
    row['artists'] = ['Other']
    assert row['spotify_name'] == 'Light'
    assert row['spotify_artists'] == ['Tom Jung']


def test_spotify_aligns_rejects_mismatched_tags():
    song = {
        'spotify_name': "Don't",
        'spotify_artists': ['Bryson Tiller'],
        'name': "Don't You Fear",
        'artists': ['Kraam', 'Santirini'],
        'library_from_tags': True,
    }
    assert not spotify_aligns_with_file_tags(song)


def test_verify_downloaded_file_rejects_wrong_tags(
    monkeypatch, tmp_path: Path
) -> None:
    path = tmp_path / 'wrong.mp3'
    path.write_bytes(b'x')
    monkeypatch.setattr(
        'downtify.track_tag_match.read_audio_metadata',
        lambda _p: {
            'title': 'Gold Thangs & Pinky Rangs',
            'artists': ['Ramirez', 'Pouya', 'Shakewell'],
            'album': '',
        },
    )
    spotify_row = snapshot_spotify_metadata({
        'name': 'Light',
        'artists': ['Tom Jung'],
    })
    assert not verify_downloaded_file_matches_spotify(path, spotify_row)


def test_verify_downloaded_file_accepts_matching_tags(
    monkeypatch, tmp_path: Path
) -> None:
    path = tmp_path / 'ok.mp3'
    path.write_bytes(b'x')
    monkeypatch.setattr(
        'downtify.track_tag_match.read_audio_metadata',
        lambda _p: {
            'title': 'Light',
            'artists': ['Tom Jung'],
            'album': '',
        },
    )
    spotify_row = snapshot_spotify_metadata({
        'name': 'Light',
        'artists': ['Tom Jung'],
    })
    assert verify_downloaded_file_matches_spotify(path, spotify_row)


def test_media_duration_rejects_hour_long_audiobook():
    song = {'duration': 210}
    assert media_duration_matches_song(song, 211) is True
    assert media_duration_matches_song(song, 3517) is False


def test_media_duration_accepts_youtube_rip_drift():
    song = {'duration': 257_000}
    assert media_duration_matches_song(song, 226) is True


def test_media_duration_accepts_short_track_youtube_padding():
    song = {'duration': 130}
    assert media_duration_matches_song(song, 164) is True
    assert media_duration_matches_song(song, 176) is False


def test_media_duration_accepts_mix_variant_last_resort_drift():
    song = {'duration': 210}
    assert media_duration_matches_song(song, 260) is False
    assert media_duration_matches_mix_variant(song, 260) is True
    assert media_duration_matches_mix_variant(song, 380) is False


def test_media_duration_respects_custom_tolerance_percent():
    song = {'duration': 200}
    assert (
        media_duration_matches_song(
            song, 250, tolerance_seconds=5, tolerance_percent=15
        )
        is False
    )
    assert (
        media_duration_matches_song(
            song, 235, tolerance_seconds=5, tolerance_percent=20
        )
        is True
    )
    assert (
        media_duration_matches_mix_variant(
            song,
            260,
            tolerance_percent=35,
            normal_tolerance_seconds=5,
            normal_tolerance_percent=15,
        )
        is True
    )


def test_duration_tolerances_from_slskd_settings():
    assert duration_tolerances_from_settings({}) == {
        'seconds': 10,
        'percent': 15,
        'mix_percent': 50,
    }
    tol = duration_tolerances_from_settings({
        'duration_tolerance_seconds': 12,
        'duration_tolerance_percent': 25,
        'mix_duration_tolerance_percent': 60,
    })
    assert tol == {'seconds': 12, 'percent': 25, 'mix_percent': 60}


def test_strip_mix_suffix():
    assert strip_mix_suffix('Loud Enough - Radio Mix') == 'Loud Enough'
    assert strip_mix_suffix('Heat - Extended Mix') == 'Heat'


def test_candidate_adds_mix_variant_last_resort_only():
    assert candidate_adds_mix_variant('Heat', 'Heat (Extended Mix)')
    assert not candidate_adds_mix_variant(
        'Heat - Extended Mix', 'Heat (Extended Mix)'
    )
    assert candidate_adds_mix_variant(
        'Loud Enough - Radio Mix', 'Loud Enough (Extended Mix)'
    )


def test_youtube_probe_title_matches_artist_and_title():
    song = {
        'name': 'Flor da Imperatriz',
        'artists': ['Suspectless'],
    }
    assert youtube_probe_title_matches(
        song, 'Suspectless - Flor da Imperatriz (Official Audio)'
    )
    assert not youtube_probe_title_matches(
        song, 'DJ Set #1 2026 | 1 Hour Mix | Back to the Decks'
    )


def test_verify_youtube_download_file_uses_probe_not_raw_tags(
    monkeypatch, tmp_path: Path
) -> None:
    path = tmp_path / 'track.mp3'
    path.write_bytes(b'x')
    monkeypatch.setattr(
        'downtify.track_tag_match.audio_file_length_seconds',
        lambda _p: 194,
    )
    song = snapshot_spotify_metadata({
        'name': 'Flor da Imperatriz',
        'artists': ['Suspectless'],
        'duration': 194,
    })
    probe = {'title': 'Suspectless - Flor da Imperatriz', 'duration': 194}
    assert verify_youtube_download_file(path, song, probe=probe)


def test_remote_title_rejects_audiobook_label():
    song = {'name': 'Temptation Island'}
    assert remote_title_unacceptable(
        song, 'Temptation Island - Full Audiobook Part 1'
    )
    assert not remote_title_unacceptable(
        song, 'Temptation Island (Official Video)'
    )


def test_remote_text_unacceptable_unifies_spam_and_variants():
    assert remote_text_unacceptable(
        'Old Man River',
        'Old Man River - Live',
    )
    assert remote_text_unacceptable(
        'Temptation Island',
        'Temptation Island - Full Audiobook Part 1',
    )
    assert not remote_text_unacceptable(
        'Old Man River - Live',
        'Old Man River - Live',
    )
    assert remote_adds_unwanted_variant(
        'Old Man River',
        'Old Man River - Live',
    )
    assert not remote_adds_unwanted_variant(
        'Old Man River - Live',
        'Old Man River - Live',
    )


def test_remote_adds_unwanted_variant_does_not_match_live_inside_oliver():
    assert not remote_adds_unwanted_variant(
        'Song',
        'Oliver - Song.mp3',
        spotify_artists=['Oliver'],
    )


def test_remote_adds_unwanted_variant_skips_extended_when_allowed():
    assert remote_adds_unwanted_variant(
        'Track',
        'Track (Extended Mix).mp3',
    )
    assert not remote_adds_unwanted_variant(
        'Track',
        'Track (Extended Mix).mp3',
        skip_keywords=frozenset({'extended'}),
    )
