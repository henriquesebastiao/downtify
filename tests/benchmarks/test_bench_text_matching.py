"""CodSpeed benchmarks for the name/title matching helpers.

These run on every track of a playlist or library listing, so they are
benchmarked over a batch of realistic, synthetic inputs (no network, no
user data).
"""

from __future__ import annotations

import pytest

from downtify.album_artist import is_act_of, is_various_artists
from downtify.file_naming import file_name_key, sanitize_file_name, title_key
from downtify.library_metadata import split_artists
from downtify.m3u import sanitize_playlist_name
from downtify.track_index import normalize_spotify_track_id
from downtify.track_tag_match import (
    remote_text_unacceptable,
    strip_mix_suffix,
    youtube_probe_title_matches,
)

_TITLES = [
    'Dummy (Deluxe Edition)',
    'Roads - Live',
    'Glory Box [Remastered 2011]',
    'Bohemian Rhapsody - Remastered 2011',
    'Ação e Reação (Ao Vivo)',
    'Smells Like Teen Spirit',
    'One More Time - Radio Edit',
    'Strobe - Extended Mix',
    'Café / Bar: "Night*Life"?',
    'M.I.A. <Paper Planes> | Single',
] * 20

_ARTISTS = [
    'AC/DC',
    '*NSYNC',
    'M.I.A.',
    'Henrique & Juliano',
    'Simon + Garfunkel',
    'Earth, Wind & Fire',
    'Zé Neto, Cristiano',
    'Various Artists',
    'Daft Punk; Pharrell Williams; Nile Rodgers',
    'Anitta x Pedro Sampaio',
] * 20

_SONGS = [
    {'name': 'Get Lucky', 'artists': ['Daft Punk', 'Pharrell Williams']},
    {'name': 'Strobe - Radio Edit', 'artists': ['deadmau5']},
    {'name': 'Bohemian Rhapsody', 'artists': ['Queen']},
    {'name': 'Ação e Reação', 'artists': ['Titãs']},
    {'name': "Don't Stop Me Now", 'artists': ['Queen']},
]

_PROBES = [
    'Daft Punk - Get Lucky (Official Audio) ft. Pharrell Williams',
    'deadmau5 - Strobe (Extended Mix)',
    'Queen – Bohemian Rhapsody (Official Video Remastered)',
    'Titãs - Ação e Reação (Ao Vivo)',
    "Queen - Don't Stop Me Now (Karaoke Version)",
    'Get Lucky - 1 hour loop',
    'Bohemian Rhapsody | Audiobook narrated by someone',
    'Totally unrelated upload',
]

_SPOTIFY_IDS = [
    {'song_id': '4uLU6hMCjMI75M1A2tKUQC'},
    {'url': 'https://open.spotify.com/track/7ouMYWpwJ422jRcDASZB7P?si=x'},
    {'song_id': 'spotify:track:0VjIjW4GlUZAMYd2vXMi3b'},
    {'song_id': 'not-a-spotify-id'},
    {'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'},
] * 40


@pytest.mark.benchmark
def test_bench_sanitize_file_names():
    for text in _TITLES + _ARTISTS:
        sanitize_file_name(text)
        sanitize_playlist_name(text)


@pytest.mark.benchmark
def test_bench_file_and_title_keys():
    for title in _TITLES:
        title_key(title)
    for artist in _ARTISTS:
        file_name_key(artist)


@pytest.mark.benchmark
def test_bench_split_artists():
    for artist in _ARTISTS:
        split_artists(artist, 'Henrique, Juliano')
        is_various_artists(artist)
        is_act_of(['Juliano', 'Henrique'], artist)


@pytest.mark.benchmark
def test_bench_youtube_probe_title_matches():
    for song in _SONGS:
        for probe in _PROBES:
            youtube_probe_title_matches(song, probe)


@pytest.mark.benchmark
def test_bench_remote_text_unacceptable():
    for song in _SONGS:
        title = song['name']
        stripped = strip_mix_suffix(title)
        for probe in _PROBES:
            remote_text_unacceptable(
                stripped, probe, spotify_artists=song['artists']
            )


@pytest.mark.benchmark
def test_bench_normalize_spotify_track_id():
    for song in _SPOTIFY_IDS:
        normalize_spotify_track_id(song)
