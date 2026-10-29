"""The "explicit" mark of a song: written into the file, read back for the
Library, cached, and given to the apps (issue #431)."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest
from mutagen import File as MutagenFile
from mutagen.id3 import ID3, TIT2, TXXX
from mutagen.mp4 import MP4

from downtify import api, library_upgrade, monitor, providers
from downtify.downloader import embed_metadata
from downtify.library_catalog import LibraryContext, list_library_entries
from downtify.library_metadata import library_entry_for_file, read_explicit
from downtify.library_metadata_cache import META_VERSION, LibraryMetadataCache
from downtify.library_sync import public_row
from downtify.sqlite_utils import connect_sqlite

_needs_ffmpeg = pytest.mark.skipif(
    shutil.which('ffmpeg') is None, reason='no ffmpeg'
)

_CODECS = {
    'mp3': ['-c:a', 'libmp3lame', '-b:a', '64k'],
    'flac': ['-c:a', 'flac'],
    'm4a': ['-c:a', 'aac', '-b:a', '64k'],
    'opus': ['-c:a', 'libopus', '-b:a', '32k'],
    'ogg': ['-c:a', 'libvorbis', '-q:a', '1'],
}

SONG = {'name': 'Title', 'artists': ['Artist'], 'album_name': 'Album'}


def _audio(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            'ffmpeg',
            '-nostdin',
            '-loglevel',
            'error',
            '-y',
            '-f',
            'lavfi',
            '-i',
            'sine=frequency=440:duration=1',
            *_CODECS[path.suffix.lstrip('.')],
            str(path),
        ],
        check=True,
    )
    return path


# ── Writing and reading the mark ────────────────────────────────────────


@_needs_ffmpeg
@pytest.mark.parametrize('fmt', sorted(_CODECS))
def test_the_mark_round_trips_in_every_format(tmp_path, fmt):
    marked = _audio(tmp_path / f'marked.{fmt}')
    plain = _audio(tmp_path / f'plain.{fmt}')

    embed_metadata(marked, {**SONG, 'explicit': True}, download_cover=False)
    embed_metadata(plain, SONG, download_cover=False)

    assert read_explicit(marked) is True
    assert read_explicit(plain) is False


@_needs_ffmpeg
def test_each_format_uses_the_tag_players_and_servers_read(tmp_path):
    mp3 = _audio(tmp_path / 'a.mp3')
    m4a = _audio(tmp_path / 'a.m4a')
    flac = _audio(tmp_path / 'a.flac')
    for path in (mp3, m4a, flac):
        embed_metadata(path, {**SONG, 'explicit': True}, download_cover=False)

    frames = ID3(str(mp3)).getall('TXXX:ITUNESADVISORY')
    assert [(f.desc, list(f.text)) for f in frames] == [
        ('ITUNESADVISORY', ['1'])
    ]
    assert MP4(str(m4a)).tags['rtng'] == [1]
    assert MutagenFile(str(flac)).tags['ITUNESADVISORY'] == ['1']


@_needs_ffmpeg
def test_a_song_that_does_not_say_never_clears_the_mark(tmp_path):
    """The library upgrade and a retag write tags again from what they
    know; a file that was marked must stay marked."""

    path = _audio(tmp_path / 'a.flac')
    embed_metadata(path, {**SONG, 'explicit': True}, download_cover=False)
    embed_metadata(path, SONG, download_cover=False)
    assert read_explicit(path) is True


def test_only_explicit_values_count(tmp_path):
    path = tmp_path / 'a.mp3'

    def tag(desc, value):
        tags = ID3()
        tags.add(TIT2(encoding=3, text='T'))
        tags.add(TXXX(encoding=3, desc=desc, text=value))
        tags.save(str(path), v2_version=3)

    tag('ITUNESADVISORY', '1')
    assert read_explicit(path) is True
    tag('itunesadvisory', '4')  # the older value, and any letter case
    assert read_explicit(path) is True
    tag('ITUNESADVISORY', '2')  # "clean"
    assert read_explicit(path) is False
    tag('ITUNESADVISORY', '0')
    assert read_explicit(path) is False
    tag('SOMETHING ELSE', '1')
    assert read_explicit(path) is False


def test_a_missing_or_unreadable_file_is_not_explicit(tmp_path):
    assert read_explicit(tmp_path / 'nope.mp3') is False
    broken = tmp_path / 'broken.flac'
    broken.write_bytes(b'not audio')
    assert read_explicit(broken) is False


# ── The Library ─────────────────────────────────────────────────────────


def _marked_mp3(path: Path, explicit: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tags = ID3()
    tags.add(TIT2(encoding=3, text=path.stem))
    if explicit:
        tags.add(TXXX(encoding=3, desc='ITUNESADVISORY', text='1'))
    tags.save(str(path), v2_version=3)


def test_library_rows_say_whether_a_track_is_explicit(tmp_path):
    loud = tmp_path / 'loud.mp3'
    quiet = tmp_path / 'quiet.mp3'
    _marked_mp3(loud, True)
    _marked_mp3(quiet, False)

    assert library_entry_for_file('loud.mp3', loud)['explicit'] is True
    assert library_entry_for_file('quiet.mp3', quiet)['explicit'] is False


def test_the_cache_keeps_the_mark(tmp_path):
    download_dir = tmp_path / 'downloads'
    _marked_mp3(download_dir / 'loud.mp3', True)
    _marked_mp3(download_dir / 'quiet.mp3', False)
    cache = LibraryMetadataCache(tmp_path / 'library.db')
    ctx = LibraryContext(download_dir=download_dir, metadata_cache=cache)

    first = {row['file']: row['explicit'] for row in list_library_entries(ctx)}
    # Again, from the cache this time (the files are not read).
    second = {
        row['file']: row['explicit'] for row in list_library_entries(ctx)
    }

    assert first == second == {'loud.mp3': True, 'quiet.mp3': False}


def test_a_database_from_before_gains_the_column_and_rereads(tmp_path):
    db = tmp_path / 'library.db'
    download_dir = tmp_path / 'downloads'
    _marked_mp3(download_dir / 'loud.mp3', True)
    LibraryMetadataCache(db)
    # What the table looked like before the column, and a row cached then.
    with connect_sqlite(str(db)) as conn:
        conn.execute('ALTER TABLE library_metadata DROP COLUMN explicit')
        conn.execute(
            'INSERT INTO library_metadata (content_key, filename, '
            'meta_version, file_mtime_ns, file_size, cached_at) '
            "VALUES ('k', 'loud.mp3', ?, 0, 0, '')",
            (META_VERSION - 1,),
        )

    cache = LibraryMetadataCache(db)  # migrates
    ctx = LibraryContext(download_dir=download_dir, metadata_cache=cache)
    (row,) = list_library_entries(ctx)

    assert row['explicit'] is True


# ── What the apps get ───────────────────────────────────────────────────


def test_sync_rows_carry_the_mark_only_on_explicit_tracks():
    base = {'file': 'a.mp3', 'title': 'T', 'artist': 'A', 'size': 1}
    plain = public_row(base)
    loud = public_row({**base, 'explicit': True})
    not_loud = public_row({**base, 'explicit': False})

    assert 'explicit' not in plain
    assert 'explicit' not in not_loud
    assert plain == not_loud  # every other row stays exactly as it was
    assert loud['explicit'] is True


# ── The paths that write tags back ──────────────────────────────────────


def test_a_library_upgrade_keeps_the_mark_it_writes_back():
    entry = {'title': 'T', 'artist': 'A', 'explicit': True}
    assert library_upgrade.song_for_track(entry)['explicit'] is True
    assert library_upgrade.song_for_track({'title': 'T'})['explicit'] is False


def test_the_monitor_takes_the_mark_from_the_tracks_own_page(monkeypatch):
    monkeypatch.setattr(
        monitor.spotify,
        'track_from_id',
        lambda _id: {'explicit': True, 'album_name': 'Album'},
    )
    row = {'song_id': '4uLU6hMCjMI75M1A2tKUQC', 'name': 'T'}

    asyncio.run(monitor._fill_from_spotify_track(row))
    assert row['explicit'] is True

    # A track the page doesn't flag doesn't lose a mark the row had.
    monkeypatch.setattr(
        monitor.spotify, 'track_from_id', lambda _id: {'explicit': False}
    )
    asyncio.run(monitor._fill_from_spotify_track(row))
    assert row['explicit'] is True


# ── Getting the mark from the services into the song ────────────────────


@pytest.fixture
def offline_enrich(monkeypatch):
    """enrich_from_match without the album lookups it makes on YouTube."""

    monkeypatch.setattr(
        providers, 'youtube_music_track_index_for_match', lambda m, s: (1, 9)
    )
    monkeypatch.setattr(providers, '_album_browse_id', lambda m, s: None)


def test_a_client_row_that_says_explicit_marks_the_download():
    base = {'song_id': 'vid', 'name': 'T', 'explicit': False}

    api._merge_client_track_hints(base, {'explicit': True})
    assert base['explicit'] is True

    # A row that doesn't say never clears what the URL's own lookup found.
    api._merge_client_track_hints(base, {'explicit': False})
    api._merge_client_track_hints(base, {'track_number': 3})
    assert base['explicit'] is True


def test_a_catalog_hit_that_is_explicit_marks_the_song(offline_enrich):
    song = {'song_id': '4uLU6hMCjMI75M1A2tKUQC', 'name': 'T', 'artists': ['A']}

    loud = providers.enrich_from_match(
        song, {'videoId': 'v', 'isExplicit': True}
    )
    quiet = providers.enrich_from_match(song, {'videoId': 'v'})

    assert loud['explicit'] is True
    assert not quiet.get('explicit')
    # And a hit that isn't flagged doesn't un-mark a song a service flagged.
    marked = providers.enrich_from_match(
        {**song, 'explicit': True}, {'videoId': 'v'}
    )
    assert marked['explicit'] is True


def _video(monkeypatch, match):
    monkeypatch.setattr(
        providers,
        '_song_from_video_details',
        lambda vid: {
            'song_id': vid,
            'name': 'T',
            'artists': ['A'],
            'explicit': False,
        },
    )
    monkeypatch.setattr(
        providers, '_find_youtube_music_match', lambda song: ('x', match)
    )


def test_a_video_is_explicit_when_its_own_catalog_hit_is(
    monkeypatch, offline_enrich
):
    _video(monkeypatch, {'videoId': 'asked', 'isExplicit': True})
    assert providers.song_from_video_id('asked')['explicit'] is True


def test_a_clean_edit_does_not_inherit_the_albums_mark(
    monkeypatch, offline_enrich
):
    """The catalog lookup can land on the explicit album version of a song
    whose video, the one actually downloaded, is a clean edit."""

    _video(monkeypatch, {'videoId': 'album-version', 'isExplicit': True})
    assert providers.song_from_video_id('radio-edit')['explicit'] is False
