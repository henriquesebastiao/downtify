"""After asking slskd for a file, Downtify looks for it on disk. When the
file isn't where its Soulseek name says, a deep scan looks for the song
by title. That scan used to take any audio file with the title in its
name, in any format, at least as big as the requested one - so an MP3
download could import a FLAC already in slskd's folder (an older
download, or another app's), even with only lossy formats allowed.
"""

from __future__ import annotations

from pathlib import Path

from downtify.slskd_provider import _find_on_disk_for_song

SONG = {'name': 'Thriller (2003 Edit)', 'artists': ['Michael Jackson']}
REQUESTED = '@@abcd\\Music\\Michael Jackson\\Number Ones\\05 Thriller.mp3'
MP3_SIZE = 12_000_000


def _file(path: Path, size: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as stream:
        stream.truncate(size)
    return path


def test_a_flac_of_the_same_song_is_not_taken_for_the_mp3(tmp_path):
    _file(
        tmp_path / 'Number Ones' / '05_Thriller (2003 Edit).flac', 117_000_000
    )

    found = _find_on_disk_for_song(
        [tmp_path], SONG, REQUESTED, username='peer', expected_size=MP3_SIZE
    )

    assert found is None


def test_a_far_bigger_file_of_the_same_format_is_not_taken(tmp_path):
    # Another song with the title in its name: a 40-minute mix.
    _file(tmp_path / 'Mixes' / 'Thriller (2003 Edit) megamix.mp3', 90_000_000)

    found = _find_on_disk_for_song(
        [tmp_path], SONG, REQUESTED, username='peer', expected_size=MP3_SIZE
    )

    assert found is None


def test_the_requested_file_under_another_name_is_still_found(tmp_path):
    """What the scan is for: slskd saved the transfer somewhere else."""
    landed = _file(
        tmp_path / 'renamed' / 'Thriller (2003 Edit)_639011.mp3', MP3_SIZE
    )

    found = _find_on_disk_for_song(
        [tmp_path], SONG, REQUESTED, username='peer', expected_size=MP3_SIZE
    )

    assert found == landed


def test_the_exact_name_in_another_folder_is_still_found(tmp_path):
    landed = _file(tmp_path / 'elsewhere' / '05 Thriller.mp3', MP3_SIZE)

    found = _find_on_disk_for_song(
        [tmp_path], SONG, REQUESTED, username='peer', expected_size=MP3_SIZE
    )

    assert found == landed


def test_a_partly_written_transfer_is_still_seen_while_it_grows(tmp_path):
    """Progress polling sees the file before it is complete."""
    landed = _file(
        tmp_path / 'renamed' / 'Thriller (2003 Edit)_639011.mp3',
        MP3_SIZE // 2,
    )

    found = _find_on_disk_for_song(
        [tmp_path],
        SONG,
        REQUESTED,
        username='peer',
        expected_size=MP3_SIZE,
    )

    # Too small to count as done (min size 95 %), so not returned yet.
    assert found is None
    _file(landed, MP3_SIZE)
    assert (
        _find_on_disk_for_song(
            [tmp_path],
            SONG,
            REQUESTED,
            username='peer',
            expected_size=MP3_SIZE,
        )
        == landed
    )
