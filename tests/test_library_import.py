"""Tests for downtify/library_import.py: parsing library-export CSVs
(Soundiiz, TuneMyMusic, Exportify, ...) into title/artist song dicts."""

from __future__ import annotations

import pytest

from downtify.library_import import (
    MAX_CSV_ROWS,
    LibraryCsvError,
    parse_library_csv,
)

# ── header detection across exporters ───────────────────────────────────────


def test_parses_simple_title_artist_headers():
    csv_text = 'Title,Artist\nHeld Together,Slowdive\nFallen Wires,DIIV\n'
    songs = parse_library_csv(csv_text)
    assert songs == [
        {'song_id': 'csv:0', 'name': 'Held Together', 'artists': ['Slowdive']},
        {'song_id': 'csv:1', 'name': 'Fallen Wires', 'artists': ['DIIV']},
    ]


def test_parses_exportify_style_headers():
    csv_text = (
        'Track URI,Track Name,Artist Name(s),Album Name\n'
        'spotify:track:abc,Space Song,Beach House,Depression Cherry\n'
    )
    songs = parse_library_csv(csv_text)
    assert songs == [
        {'song_id': 'csv:0', 'name': 'Space Song', 'artists': ['Beach House']}
    ]


def test_parses_tunemymusic_style_headers():
    csv_text = (
        'Track Title,Artist,Album,Playlist Name\n'
        'Motion Picture Soundtrack,Radiohead,Kid A,Favorites\n'
    )
    songs = parse_library_csv(csv_text)
    assert songs == [
        {
            'song_id': 'csv:0',
            'name': 'Motion Picture Soundtrack',
            'artists': ['Radiohead'],
        }
    ]


def test_header_matching_is_case_insensitive():
    csv_text = 'TITLE,ARTIST\nSong One,Artist One\n'
    songs = parse_library_csv(csv_text)
    assert songs == [
        {'song_id': 'csv:0', 'name': 'Song One', 'artists': ['Artist One']}
    ]


def test_semicolon_delimited_csv_is_sniffed():
    csv_text = 'Title;Artist\nSong One;Artist One\n'
    songs = parse_library_csv(csv_text)
    assert songs == [
        {'song_id': 'csv:0', 'name': 'Song One', 'artists': ['Artist One']}
    ]


# ── song_id ──────────────────────────────────────────────────────────────────


def test_song_ids_are_unique_and_sequential():
    csv_text = 'Title,Artist\nA,Artist A\nB,Artist B\nC,Artist C\n'
    songs = parse_library_csv(csv_text)
    assert [s['song_id'] for s in songs] == ['csv:0', 'csv:1', 'csv:2']


def test_song_ids_stay_sequential_when_invalid_rows_are_skipped():
    # The frontend keys every download queue item by song_id, and would
    # conflate two rows sharing one id into a single queue entry — so a
    # skipped row (missing title/artist) must not leave a gap that later
    # collides, and IDs must simply follow the surviving rows in order.
    csv_text = 'Title,Artist\nA,Artist A\n,Missing Title\nB,Artist B\n'
    songs = parse_library_csv(csv_text)
    assert [s['song_id'] for s in songs] == ['csv:0', 'csv:1']
    assert [s['name'] for s in songs] == ['A', 'B']


# ── multi-artist rows ────────────────────────────────────────────────────────


def test_splits_multiple_artists_on_comma():
    # The artist field itself contains a comma, so it must be quoted for
    # the CSV parser to keep it as one column.
    csv_text = 'Title,Artist\nCollab Song,"Artist A, Artist B"\n'
    songs = parse_library_csv(csv_text)
    assert songs == [
        {
            'song_id': 'csv:0',
            'name': 'Collab Song',
            'artists': ['Artist A', 'Artist B'],
        }
    ]


def test_splits_multiple_artists_on_semicolon_within_quoted_field():
    csv_text = 'Title,Artist\nCollab Song,"Artist A; Artist B"\n'
    songs = parse_library_csv(csv_text)
    assert songs == [
        {
            'song_id': 'csv:0',
            'name': 'Collab Song',
            'artists': ['Artist A', 'Artist B'],
        }
    ]


# ── row filtering ────────────────────────────────────────────────────────────


def test_skips_rows_missing_title_or_artist():
    csv_text = (
        'Title,Artist\nHas Both,Some Artist\n,Missing Title\nMissing Artist,\n'
    )
    songs = parse_library_csv(csv_text)
    assert songs == [
        {'song_id': 'csv:0', 'name': 'Has Both', 'artists': ['Some Artist']}
    ]


def test_strips_whitespace_from_title_and_artist():
    csv_text = 'Title,Artist\n  Padded Title  ,  Padded Artist  \n'
    songs = parse_library_csv(csv_text)
    assert songs == [
        {
            'song_id': 'csv:0',
            'name': 'Padded Title',
            'artists': ['Padded Artist'],
        }
    ]


# ── error cases ──────────────────────────────────────────────────────────────


def test_raises_when_no_recognizable_columns():
    csv_text = 'Foo,Bar\n1,2\n'
    with pytest.raises(LibraryCsvError):
        parse_library_csv(csv_text)


def test_raises_when_empty():
    with pytest.raises(LibraryCsvError):
        parse_library_csv('')


def test_raises_when_all_rows_invalid():
    csv_text = 'Title,Artist\n,\n,\n'
    with pytest.raises(LibraryCsvError):
        parse_library_csv(csv_text)


def test_raises_over_max_row_cap():
    header = 'Title,Artist\n'
    rows = ''.join(f'Song {i},Artist {i}\n' for i in range(MAX_CSV_ROWS + 1))
    with pytest.raises(LibraryCsvError):
        parse_library_csv(header + rows)


def test_accepts_exactly_max_row_cap():
    header = 'Title,Artist\n'
    rows = ''.join(f'Song {i},Artist {i}\n' for i in range(MAX_CSV_ROWS))
    songs = parse_library_csv(header + rows)
    assert len(songs) == MAX_CSV_ROWS
