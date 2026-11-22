"""CompilationMarks on both backends: the same results on SQLite and PostgreSQL."""

from __future__ import annotations

from downtify.album_artist import VARIOUS_ARTISTS
from downtify.compilation import CompilationMarks


def _rows(marks: CompilationMarks, album: str) -> list[tuple[str, str, str]]:
    return [
        (row['artist'], row['album'], row['album_artist'])
        for row in marks.marked_albums(album)
    ]


def test_set_then_marked_albums_lists_the_mark(backend_db) -> None:
    marks = CompilationMarks(backend_db)

    marks.set(
        'Ann Lee',
        'Summer Hits',
        compilation=True,
        album_artist=VARIOUS_ARTISTS,
    )

    assert _rows(marks, 'Summer Hits') == [
        ('Ann Lee', 'Summer Hits', VARIOUS_ARTISTS)
    ]


def test_marked_albums_matches_title_by_file_name_key(backend_db) -> None:
    marks = CompilationMarks(backend_db)
    marks.set(
        'Ann', 'Night Tapes', compilation=True, album_artist='Various Artists'
    )

    assert _rows(marks, 'night  tapes') == [
        ('Ann', 'Night Tapes', VARIOUS_ARTISTS)
    ]
    assert _rows(marks, 'Other') == []


def test_unmarked_entries_are_not_listed(backend_db) -> None:
    marks = CompilationMarks(backend_db)
    marks.set('Ann', 'Solo', compilation=False, album_artist='Ann')

    assert _rows(marks, 'Solo') == []


def test_set_again_overwrites_the_same_album(backend_db) -> None:
    marks = CompilationMarks(backend_db)
    marks.set('Ann', 'Flip', compilation=True, album_artist=VARIOUS_ARTISTS)
    marks.set('ann', 'flip', compilation=False, album_artist='Ann')

    assert _rows(marks, 'Flip') == []
    assert marks.override_for({
        'album_name': 'Flip',
        'album_artist': 'Ann',
        'name': 'x',
    }) == {'album_artist': 'Ann', 'compilation': False}


def test_remove_forgets_the_album(backend_db) -> None:
    marks = CompilationMarks(backend_db)
    marks.set('Ann', 'Gone', compilation=True, album_artist=VARIOUS_ARTISTS)

    marks.remove('ANN', 'gone')

    assert _rows(marks, 'Gone') == []
    assert (
        marks.override_for({'album_name': 'Gone', 'album_artist': 'Ann'}) == {}
    )


def test_remove_of_a_missing_album_is_a_no_op(backend_db) -> None:
    marks = CompilationMarks(backend_db)

    marks.remove('Nobody', 'Nothing')

    assert _rows(marks, 'Nothing') == []


def test_marked_albums_are_ordered_by_mark_time(backend_db) -> None:
    marks = CompilationMarks(backend_db)
    marks.set(
        'First', 'Shared', compilation=True, album_artist=VARIOUS_ARTISTS
    )
    marks.set(
        'Second', 'Shared', compilation=True, album_artist=VARIOUS_ARTISTS
    )

    assert [artist for artist, _, _ in _rows(marks, 'Shared')] == [
        'First',
        'Second',
    ]


def test_override_for_a_marked_compilation_uses_various_artists(
    backend_db,
) -> None:
    marks = CompilationMarks(backend_db)
    marks.set('Ann', 'Mix', compilation=True, album_artist=VARIOUS_ARTISTS)

    song = {'album_name': 'Mix', 'album_artist': 'Ann', 'name': 'Track'}
    assert marks.override_for(song) == {
        'album_artist': VARIOUS_ARTISTS,
        'compilation': True,
    }


def test_override_for_falls_back_to_first_artist(backend_db) -> None:
    marks = CompilationMarks(backend_db)
    marks.set('Ann', 'Mix', compilation=True, album_artist=VARIOUS_ARTISTS)

    song = {'album_name': 'Mix', 'artists': ['Ann', 'Bob']}
    assert marks.override_for(song) == {
        'album_artist': VARIOUS_ARTISTS,
        'compilation': True,
    }


def test_override_for_a_source_compilation_matches_various_artists(
    backend_db,
) -> None:
    marks = CompilationMarks(backend_db)
    marks.set(
        VARIOUS_ARTISTS, 'Sampler', compilation=False, album_artist='Ann'
    )

    song = {
        'album_name': 'Sampler',
        'album_artist': 'Ann',
        'compilation': True,
    }
    assert marks.override_for(song) == {
        'album_artist': 'Ann',
        'compilation': False,
    }


def test_override_for_unknown_album_is_empty(backend_db) -> None:
    marks = CompilationMarks(backend_db)

    assert (
        marks.override_for({'album_name': 'Unknown', 'artists': ['Ann']}) == {}
    )


def test_override_for_without_album_or_artist_is_empty(backend_db) -> None:
    marks = CompilationMarks(backend_db)
    marks.set('Ann', 'Mix', compilation=True, album_artist=VARIOUS_ARTISTS)

    assert marks.override_for({'album_artist': 'Ann'}) == {}
    assert marks.override_for({'album_name': 'Mix'}) == {}
    assert marks.override_for({'album_name': 'Mix', 'artists': []}) == {}


def test_override_for_matches_artist_as_file_name_key(backend_db) -> None:
    marks = CompilationMarks(backend_db)
    marks.set('AC/DC', 'Live', compilation=False, album_artist='AC/DC')

    song = {'album_name': 'Live', 'album_artist': 'ACDC'}
    assert marks.override_for(song) == {
        'album_artist': 'AC/DC',
        'compilation': False,
    }


def test_constructor_accepts_a_database_and_keeps_the_path(backend_db) -> None:
    marks = CompilationMarks(backend_db)

    assert marks.db is backend_db
    assert marks.db.dialect is backend_db.dialect
