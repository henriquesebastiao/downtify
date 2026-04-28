"""Tests for ``downtify.m3u``."""

from __future__ import annotations

from pathlib import Path

from downtify import m3u

# --- sanitize_playlist_name ------------------------------------------------


def test_sanitize_keeps_allowed_chars():
    assert (
        m3u.sanitize_playlist_name('My Playlist_2024 - Best')
        == 'My Playlist_2024 - Best'
    )


def test_sanitize_strips_filesystem_unsafe_chars():
    assert (
        m3u.sanitize_playlist_name('a/b\\c:d*e?f"g<h>i|j')
        == 'abcdefghij'
    )


def test_sanitize_drops_unicode_and_punctuation():
    # Accents, emojis and punctuation are dropped per the spec
    # (alphanumerics + space + hyphen + underscore only).
    assert m3u.sanitize_playlist_name('Été — Café 🎵 #1') == 't Caf 1'


def test_sanitize_empty_input_falls_back_to_default():
    assert m3u.sanitize_playlist_name('') == 'playlist'
    assert m3u.sanitize_playlist_name('***') == 'playlist'
    assert m3u.sanitize_playlist_name('   ') == 'playlist'


def test_sanitize_collapses_whitespace():
    assert m3u.sanitize_playlist_name('  foo    bar  ') == 'foo bar'


# --- build_m3u_content -----------------------------------------------------


def _touch(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_bytes(b'\x00')
    return path


def test_build_starts_with_extm3u_header(tmp_path):
    _touch(tmp_path, 'a.mp3')
    content, _ = m3u.build_m3u_content(
        [{'filename': 'a.mp3'}], download_dir=tmp_path
    )
    assert content.startswith('#EXTM3U\n')


def test_build_includes_existing_tracks_in_order(tmp_path):
    _touch(tmp_path, 'first.mp3')
    _touch(tmp_path, 'second.mp3')
    _touch(tmp_path, 'third.mp3')
    content, kept = m3u.build_m3u_content(
        [
            {'filename': 'second.mp3', 'title': 'B', 'artist': 'X'},
            {'filename': 'first.mp3', 'title': 'A', 'artist': 'X'},
            {'filename': 'third.mp3', 'title': 'C', 'artist': 'X'},
        ],
        download_dir=tmp_path,
    )
    assert kept == 3
    # Order is preserved: B, A, C.
    first = content.index('first.mp3')
    second = content.index('second.mp3')
    third = content.index('third.mp3')
    assert second < first < third


def test_build_skips_missing_files(tmp_path):
    _touch(tmp_path, 'present.mp3')
    # 'gone.mp3' is intentionally not created on disk.
    content, kept = m3u.build_m3u_content(
        [
            {'filename': 'gone.mp3', 'title': 'Gone'},
            {'filename': 'present.mp3', 'title': 'Here'},
        ],
        download_dir=tmp_path,
    )
    assert kept == 1
    assert 'gone.mp3' not in content
    assert 'present.mp3' in content


def test_build_skips_entries_without_filename(tmp_path):
    content, kept = m3u.build_m3u_content(
        [
            {'filename': None, 'title': 'Nope'},
            {},
            {'title': 'Also nope'},
        ],
        download_dir=tmp_path,
    )
    assert kept == 0
    assert content == '#EXTM3U\n'


def test_build_uses_paths_relative_to_m3u_dir(tmp_path):
    # Track is flat under download_dir; M3U lives in download_dir/Playlists.
    # Relative path back to the track is therefore '../song.mp3'.
    _touch(tmp_path, 'song.mp3')
    content, _ = m3u.build_m3u_content(
        [{'filename': 'song.mp3'}], download_dir=tmp_path
    )
    assert '../song.mp3' in content
    # Absolute path must NOT leak into the M3U.
    assert str(tmp_path) not in content


def test_build_relative_paths_with_explicit_m3u_dir(tmp_path):
    # Track nested under an artist subdir, M3U sibling at Playlists/.
    artist_dir = tmp_path / 'Artist' / 'Album'
    artist_dir.mkdir(parents=True)
    (artist_dir / 'Track.mp3').write_bytes(b'\x00')
    m3u_dir = tmp_path / 'Playlists'
    m3u_dir.mkdir()
    content, _ = m3u.build_m3u_content(
        [{'filename': 'Artist/Album/Track.mp3'}],
        download_dir=tmp_path,
        m3u_dir=m3u_dir,
    )
    assert '../Artist/Album/Track.mp3' in content


def test_build_extinf_format_with_artist_and_title(tmp_path):
    _touch(tmp_path, 's.mp3')
    content, _ = m3u.build_m3u_content(
        [
            {
                'filename': 's.mp3',
                'title': 'Song',
                'artist': 'Artist',
                'duration': 245,
            }
        ],
        download_dir=tmp_path,
    )
    assert '#EXTINF:245,Artist - Song' in content


def test_build_extinf_handles_missing_duration(tmp_path):
    _touch(tmp_path, 's.mp3')
    content, _ = m3u.build_m3u_content(
        [{'filename': 's.mp3', 'title': 'T', 'artist': 'A'}],
        download_dir=tmp_path,
    )
    assert '#EXTINF:-1,A - T' in content


def test_build_no_extinf_when_no_metadata(tmp_path):
    _touch(tmp_path, 's.mp3')
    content, _ = m3u.build_m3u_content(
        [{'filename': 's.mp3'}], download_dir=tmp_path
    )
    assert '#EXTINF' not in content


# --- write_m3u -------------------------------------------------------------


def test_write_writes_under_playlists_subdir(tmp_path):
    _touch(tmp_path, 'a.mp3')
    target, kept = m3u.write_m3u(
        tmp_path, 'My Mix', [{'filename': 'a.mp3'}]
    )
    assert target is not None
    assert target == tmp_path / 'Playlists' / 'My Mix.m3u'
    assert target.exists()
    assert kept == 1


def test_write_sanitises_playlist_name_in_filename(tmp_path):
    _touch(tmp_path, 'a.mp3')
    target, _ = m3u.write_m3u(
        tmp_path, 'Bad/Name:Here?', [{'filename': 'a.mp3'}]
    )
    assert target is not None
    assert target.name == 'BadNameHere.m3u'


def test_write_returns_none_when_no_files_resolve(tmp_path):
    target, kept = m3u.write_m3u(
        tmp_path, 'Empty', [{'filename': 'missing.mp3'}]
    )
    assert target is None
    assert kept == 0
    assert not (tmp_path / 'Playlists' / 'Empty.m3u').exists()


def test_write_utf8_no_bom_lf_line_endings(tmp_path):
    _touch(tmp_path, 's.mp3')
    target, _ = m3u.write_m3u(
        tmp_path,
        'Mix',
        [{'filename': 's.mp3', 'title': 'T', 'artist': 'A'}],
    )
    raw = target.read_bytes()
    assert not raw.startswith(b'\xef\xbb\xbf')  # no BOM
    assert b'\r\n' not in raw  # no CRLF
    assert raw.startswith(b'#EXTM3U\n')


def test_write_overwrites_existing_m3u(tmp_path):
    _touch(tmp_path, 'a.mp3')
    _touch(tmp_path, 'b.mp3')
    m3u.write_m3u(tmp_path, 'Mix', [{'filename': 'a.mp3'}])
    target, kept = m3u.write_m3u(
        tmp_path,
        'Mix',
        [{'filename': 'a.mp3'}, {'filename': 'b.mp3'}],
    )
    assert kept == 2
    assert 'b.mp3' in target.read_text(encoding='utf-8')
