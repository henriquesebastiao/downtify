"""Extended tests for Downloader: _format_basename, _artist_subdir and
organize_by_artist routing logic."""

from __future__ import annotations

import base64
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import yt_dlp
from mutagen.id3 import ID3
from yt_dlp.postprocessor.ffmpeg import FFmpegExtractAudioPP

from downtify import downloader as downloader_mod
from downtify.downloader import (
    Downloader,
    _audio_bit_rate,
    _ExtractAudioPP,
    _release_type_for_tags,
    _tag_mp3,
    embed_lyrics,
    embed_metadata,
    save_playlist_cover,
)
from downtify.lyrics import Lyrics


def _make(tmp_path: Path, **kwargs) -> Downloader:
    return Downloader(tmp_path, **kwargs)


# A minimal-but-real single-frame MP3 (silence, ~0.1s), generated with
# ffmpeg. mutagen's MP3 class needs an actual MPEG audio frame to
# recognize the file and attach ID3 tags to it — an empty/garbage file
# is rejected before the ID3 write path is even reached.
_MINIMAL_MP3_B64 = (
    'SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjYwLjE2LjEwMAAAAAAAAAAAAAAA/+MYxAAAAANIAAA'
    'AAExBTUUzLjEwMFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV'
    'VVVVVV/+MYxDsAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV'
    'VVVVVVVVVVVVVVVVVVVVVVVVVVV/+MYxHYAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV'
    'VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV/+MYxLEAAANIAAAAAFVVVVVVVVV'
    'VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV'
)


def _minimal_mp3(path: Path) -> Path:
    path.write_bytes(base64.b64decode(_MINIMAL_MP3_B64))
    return path


# ── ID3v2.4 tagging (regression: v2.3 + UTF-8 corruption) ──────────────────────


def test_tag_mp3_round_trips_long_title_without_corruption(tmp_path):
    """Guards the ID3v2.4 save: every frame written by _tag_mp3 must
    round-trip byte-for-byte. See the v2_version comment in _tag_mp3
    for why v2.4 (native UTF-8) is used instead of v2.3, which has no
    UTF-8 text encoding and forces mutagen to transcode encoding=3
    frames to UTF-16 on save."""
    mp3_path = _minimal_mp3(tmp_path / 'song.mp3')
    _tag_mp3(
        mp3_path,
        title="Baba O'Riley",
        artists=['The Who'],
        album_artist='The Who',
        album="Who's Next",
        year='1971',
        genre='Rock',
        cover_bytes=None,
        track_number=1,
        album_track_total=9,
        release_type='album',
    )

    tags = ID3(mp3_path)
    assert str(tags.getall('TIT2')[0]) == "Baba O'Riley"
    assert str(tags.getall('TPE1')[0]) == 'The Who'
    assert str(tags.getall('TPE2')[0]) == 'The Who'
    assert str(tags.getall('TALB')[0]) == "Who's Next"
    assert str(tags.getall('TDRC')[0]) == '1971'
    assert str(tags.getall('TCON')[0]) == 'Rock'
    assert str(tags.getall('TRCK')[0]) == '1/9'


def test_embed_lyrics_mp3_round_trips_without_corruption(tmp_path):
    """Same v2.4-vs-v2.3 concern as _tag_mp3, but for the USLT (lyrics)
    save path."""
    mp3_path = _minimal_mp3(tmp_path / 'song.mp3')
    lyrics_text = '\n'.join(
        f'Line {i} of a fairly long set of lyrics' for i in range(20)
    )
    embed_lyrics(mp3_path, Lyrics(plain=lyrics_text))

    tags = ID3(mp3_path)
    assert str(tags.getall('USLT::eng')[0]) == lyrics_text


# ── _format_basename ──────────────────────────────────────────────────────────


def test_format_basename_default_template(tmp_path):
    d = _make(tmp_path)
    result = d._format_basename({
        'name': 'Do I Still Recall',
        'artists': ['The Night Owls'],
    })
    assert result == 'The Night Owls - Do I Still Recall'


def test_format_basename_multiple_artists_joined(tmp_path):
    d = _make(tmp_path)
    result = d._format_basename({'name': 'Collab', 'artists': ['A', 'B']})
    assert result == 'A, B - Collab'


def test_format_basename_no_artists_uses_fallback(tmp_path):
    d = _make(tmp_path)
    result = d._format_basename({'name': 'Song', 'artists': []})
    assert 'Song' in result


def test_format_basename_strips_unsafe_chars_from_title(tmp_path):
    d = _make(tmp_path)
    result = d._format_basename({'name': 'Song: Live', 'artists': ['Artist']})
    assert ':' not in result


def test_format_basename_custom_template(tmp_path):
    d = _make(tmp_path, output_template='{title} [{artists}]')
    result = d._format_basename({'name': 'Song', 'artists': ['Band']})
    assert result == 'Song [Band]'


def test_format_basename_album_available_in_template(tmp_path):
    d = _make(tmp_path, output_template='{album} - {title}')
    result = d._format_basename({
        'name': 'Song',
        'artists': ['A'],
        'album_name': 'MyAlbum',
    })
    assert result == 'MyAlbum - Song'


def test_format_basename_supports_album_subpath(tmp_path):
    d = _make(tmp_path, output_template='{album}/{title}')
    result = d._format_basename({
        'name': 'Song',
        'artists': ['A'],
        'album_name': 'MyAlbum',
    })
    assert result == 'MyAlbum/Song'


def test_format_basename_sanitizes_values_before_splitting_subpaths(tmp_path):
    d = _make(tmp_path, output_template='{album}/{title}')
    result = d._format_basename({
        'name': 'Fade/Out: Live',
        'artists': ['A'],
        'album_name': '../Bad/Album?',
    })
    assert result == 'BadAlbum/FadeOut Live'


def test_format_basename_bad_template_falls_back(tmp_path):
    d = _make(tmp_path, output_template='{nonexistent_key}')
    result = d._format_basename({'name': 'Song', 'artists': ['Artist']})
    assert 'Song' in result


# ── {tracknumber} template token ────────────────────────────────────────────


def test_format_basename_tracknumber_zero_padded(tmp_path):
    d = _make(tmp_path, output_template='{tracknumber} - {title}')
    result = d._format_basename({
        'name': 'Song',
        'artists': ['A'],
        'track_number': 7,
    })
    assert result == '07 - Song'


def test_format_basename_tracknumber_not_padded_past_two_digits(tmp_path):
    d = _make(tmp_path, output_template='{tracknumber} - {title}')
    result = d._format_basename({
        'name': 'Song',
        'artists': ['A'],
        'track_number': 123,
    })
    assert result == '123 - Song'


def test_format_basename_tracknumber_missing_is_empty(tmp_path):
    d = _make(tmp_path, output_template='{tracknumber} - {title}')
    result = d._format_basename({'name': 'Song', 'artists': ['A']})
    assert result == '- Song'


def test_format_basename_tracknumber_non_numeric_is_empty(tmp_path):
    d = _make(tmp_path, output_template='{tracknumber} - {title}')
    result = d._format_basename({
        'name': 'Song',
        'artists': ['A'],
        'track_number': 'not-a-number',
    })
    assert result == '- Song'


def test_format_basename_tracknumber_zero_is_empty(tmp_path):
    # track_number 0 isn't a valid position (matches the tag-embedding
    # normalization in _album_track_index_for_tags).
    d = _make(tmp_path, output_template='{tracknumber} - {title}')
    result = d._format_basename({
        'name': 'Song',
        'artists': ['A'],
        'track_number': 0,
    })
    assert result == '- Song'


def test_format_basename_supports_full_artist_album_tracknumber_layout(
    tmp_path,
):
    # The exact layout requested alongside this token: Artist/Album/NN -
    # Title.
    d = _make(
        tmp_path, output_template='{artists}/{album}/{tracknumber} - {title}'
    )
    result = d._format_basename({
        'name': 'Song',
        'artists': ['The Night Owls'],
        'album_name': 'First Light',
        'track_number': 3,
    })
    assert result == 'The Night Owls/First Light/03 - Song'


# ── _artist_subdir ────────────────────────────────────────────────────────────


def test_artist_subdir_returns_first_artist():
    result = Downloader._artist_subdir({
        'artists': ['The Night Owls', 'Other']
    })
    assert result == 'The Night Owls'


def test_artist_subdir_empty_list_returns_unknown():
    assert Downloader._artist_subdir({'artists': []}) == 'unknown'


def test_artist_subdir_missing_key_returns_unknown():
    assert Downloader._artist_subdir({}) == 'unknown'


def test_artist_subdir_sanitizes_slashes():
    result = Downloader._artist_subdir({'artists': ['Fade/Out']})
    assert '/' not in result


def test_artist_subdir_sanitizes_colons():
    result = Downloader._artist_subdir({'artists': ['Artist: Live']})
    assert ':' not in result


def test_artist_subdir_prefers_album_artist_over_track_artists():
    # Regression: a featuring track's own `artists` can differ from the
    # rest of the album (e.g. "Nova Ashworth & Wexler" vs "Nova
    # Ashworth"), which used to land it in a different folder than its
    # album-mates. `album_artist` (set for YouTube Music albums) takes
    # priority so the whole album stays together.
    result = Downloader._artist_subdir({
        'artists': ['Nova Ashworth & Wexler'],
        'album_artist': 'Nova Ashworth',
    })
    assert result == 'Nova Ashworth'


def test_artist_subdir_falls_back_to_track_artists_when_album_artist_blank():
    result = Downloader._artist_subdir({
        'artists': ['The Night Owls'],
        'album_artist': '',
    })
    assert result == 'The Night Owls'


# ── organize_by_artist – existing_filename_for ────────────────────────────────


def test_organize_by_artist_finds_file_in_artist_dir(tmp_path):
    d = _make(tmp_path, organize_by_artist=True)
    artist_dir = tmp_path / 'The Night Owls'
    artist_dir.mkdir()
    (artist_dir / 'The Night Owls - Do I Still Recall.mp3').write_bytes(
        b'\x00'
    )
    result = d.existing_filename_for({
        'name': 'Do I Still Recall',
        'artists': ['The Night Owls'],
    })
    assert result == 'The Night Owls/The Night Owls - Do I Still Recall.mp3'


def test_organize_by_artist_ignores_subdir_param(tmp_path):
    # File is in a playlist folder — should NOT be found when organize=True,
    # because the lookup targets the artist folder, not the playlist folder.
    d = _make(tmp_path, organize_by_artist=True)
    pl_dir = tmp_path / 'My Playlist'
    pl_dir.mkdir()
    (pl_dir / 'Artist - Song.mp3').write_bytes(b'\x00')
    result = d.existing_filename_for(
        {'name': 'Song', 'artists': ['Artist']}, subdir='My Playlist'
    )
    assert result is None


def test_organize_by_artist_finds_in_artist_dir_regardless_of_subdir(tmp_path):
    d = _make(tmp_path, organize_by_artist=True)
    artist_dir = tmp_path / 'Artist'
    artist_dir.mkdir()
    (artist_dir / 'Artist - Song.mp3').write_bytes(b'\x00')
    result = d.existing_filename_for(
        {'name': 'Song', 'artists': ['Artist']}, subdir='Some Playlist'
    )
    assert result == 'Artist/Artist - Song.mp3'


def test_organize_by_artist_combines_with_output_subpath(tmp_path):
    d = _make(
        tmp_path,
        organize_by_artist=True,
        output_template='{album}/{title}',
    )
    album_dir = tmp_path / 'Artist' / 'Album'
    album_dir.mkdir(parents=True)
    (album_dir / 'Song.mp3').write_bytes(b'\x00')
    result = d.existing_filename_for({
        'name': 'Song',
        'artists': ['Artist'],
        'album_name': 'Album',
    })
    assert result == 'Artist/Album/Song.mp3'


def test_organize_by_artist_false_keeps_playlist_routing(tmp_path):
    d = _make(tmp_path, organize_by_artist=False)
    pl_dir = tmp_path / 'My Playlist'
    pl_dir.mkdir()
    (pl_dir / 'Artist - Song.mp3').write_bytes(b'\x00')
    result = d.existing_filename_for(
        {'name': 'Song', 'artists': ['Artist']}, subdir='My Playlist'
    )
    assert result == 'My Playlist/Artist - Song.mp3'


def test_organize_by_artist_false_finds_root_file_without_subdir(tmp_path):
    d = _make(tmp_path, organize_by_artist=False)
    (tmp_path / 'Artist - Song.mp3').write_bytes(b'\x00')
    result = d.existing_filename_for({'name': 'Song', 'artists': ['Artist']})
    assert result == 'Artist - Song.mp3'


def test_organize_by_artist_default_is_false(tmp_path):
    d = Downloader(tmp_path)
    assert d.organize_by_artist is False


def test_organize_by_artist_can_be_set_true(tmp_path):
    d = Downloader(tmp_path, organize_by_artist=True)
    assert d.organize_by_artist is True


def test_organize_by_artist_keeps_unicode_folder_name(tmp_path):
    # Regression: accented artist names used to have their accents stripped
    # from the folder ("Sólrún" -> "Solrun").
    d = _make(tmp_path, organize_by_artist=True)
    artist_dir = tmp_path / 'Sólrún'
    artist_dir.mkdir()
    (artist_dir / 'Sólrún - Vindra.mp3').write_bytes(b'\x00')
    result = d.existing_filename_for({
        'name': 'Vindra',
        'artists': ['Sólrún'],
    })
    assert result == 'Sólrún/Sólrún - Vindra.mp3'


# ── _album_subdir ─────────────────────────────────────────────────────────────


def test_album_subdir_returns_album_name():
    assert Downloader._album_subdir({'album_name': 'Auroric'}) == 'Auroric'


def test_album_subdir_missing_key_returns_unknown():
    assert Downloader._album_subdir({}) == 'unknown'


def test_album_subdir_keeps_unicode():
    assert Downloader._album_subdir({'album_name': 'Nocturne é'}) == (
        'Nocturne é'
    )


# ── organize_by_album – existing_filename_for ─────────────────────────────────


def test_organize_by_album_default_is_false(tmp_path):
    assert Downloader(tmp_path).organize_by_album is False


def test_organize_by_album_finds_file_in_album_dir(tmp_path):
    d = _make(tmp_path, organize_by_album=True)
    album_dir = tmp_path / 'Auroric'
    album_dir.mkdir()
    (album_dir / 'Sólrún - Vindra.mp3').write_bytes(b'\x00')
    result = d.existing_filename_for({
        'name': 'Vindra',
        'artists': ['Sólrún'],
        'album_name': 'Auroric',
    })
    assert result == 'Auroric/Sólrún - Vindra.mp3'


def test_organize_by_artist_and_album_nests_artist_over_album(tmp_path):
    d = _make(tmp_path, organize_by_artist=True, organize_by_album=True)
    nested = tmp_path / 'Sólrún' / 'Auroric'
    nested.mkdir(parents=True)
    (nested / 'Sólrún - Vindra.mp3').write_bytes(b'\x00')
    result = d.existing_filename_for({
        'name': 'Vindra',
        'artists': ['Sólrún'],
        'album_name': 'Auroric',
    })
    assert result == 'Sólrún/Auroric/Sólrún - Vindra.mp3'


def test_organize_by_album_ignores_subdir_param(tmp_path):
    d = _make(tmp_path, organize_by_album=True)
    pl_dir = tmp_path / 'My Playlist'
    pl_dir.mkdir()
    (pl_dir / 'Artist - Song.mp3').write_bytes(b'\x00')
    result = d.existing_filename_for(
        {'name': 'Song', 'artists': ['Artist'], 'album_name': 'Some Album'},
        subdir='My Playlist',
    )
    assert result is None


# ── _save_album_cover ─────────────────────────────────────────────────────────

_SONG = {
    'name': 'Vindra',
    'artists': ['Sólrún'],
    'album_name': 'Auroric',
    'cover_url': 'https://img/cover',
}


def test_save_album_cover_writes_cover_jpg(tmp_path, monkeypatch):
    monkeypatch.setattr(
        downloader_mod, '_download_cover', lambda url: b'IMG-BYTES'
    )
    d = _make(tmp_path, organize_by_album=True)
    d._save_album_cover(tmp_path, _SONG)
    assert (tmp_path / 'cover.jpg').read_bytes() == b'IMG-BYTES'


def test_save_album_cover_noop_when_not_organizing_by_album(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        downloader_mod, '_download_cover', lambda url: b'IMG-BYTES'
    )
    d = _make(tmp_path, organize_by_album=False)
    d._save_album_cover(tmp_path, _SONG)
    assert not (tmp_path / 'cover.jpg').exists()


def test_save_album_cover_fetches_once_when_already_present(
    tmp_path, monkeypatch
):
    calls = []

    def _fake(url):
        calls.append(url)
        return b'IMG-BYTES'

    monkeypatch.setattr(downloader_mod, '_download_cover', _fake)
    d = _make(tmp_path, organize_by_album=True)
    (tmp_path / 'cover.jpg').write_bytes(b'EXISTING')
    d._save_album_cover(tmp_path, _SONG)
    # Existing file is preserved and no download is attempted.
    assert (tmp_path / 'cover.jpg').read_bytes() == b'EXISTING'
    assert calls == []


def test_save_album_cover_noop_when_no_cover_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader_mod, '_download_cover', lambda url: None)
    d = _make(tmp_path, organize_by_album=True)
    d._save_album_cover(tmp_path, _SONG)
    assert not (tmp_path / 'cover.jpg').exists()


# ── save_playlist_cover ──────────────────────────────────────────────────────


def test_save_playlist_cover_writes_jpg_next_to_m3u(tmp_path, monkeypatch):
    monkeypatch.setattr(
        downloader_mod, '_download_cover', lambda url: b'IMG-BYTES'
    )
    m3u_path = tmp_path / 'My Playlist.m3u'
    m3u_path.write_text('#EXTM3U\n', encoding='utf-8')
    result = save_playlist_cover('https://img/cover', m3u_path)
    expected = tmp_path / 'My Playlist.jpg'
    assert result == expected
    assert expected.read_bytes() == b'IMG-BYTES'


def test_save_playlist_cover_noop_when_no_url(tmp_path, monkeypatch):
    # _download_cover already no-ops on an empty URL; this just confirms
    # save_playlist_cover propagates that as no file written.
    monkeypatch.setattr(downloader_mod, '_download_cover', lambda url: None)
    m3u_path = tmp_path / 'My Playlist.m3u'
    assert save_playlist_cover('', m3u_path) is None
    assert not m3u_path.with_suffix('.jpg').exists()


def test_save_playlist_cover_noop_when_fetch_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader_mod, '_download_cover', lambda url: None)
    m3u_path = tmp_path / 'My Playlist.m3u'
    assert save_playlist_cover('https://img/cover', m3u_path) is None
    assert not (tmp_path / 'My Playlist.jpg').exists()


def test_save_playlist_cover_creates_the_playlist_folder(
    tmp_path, monkeypatch
):
    # The cover is saved before the first track, so the playlist's own
    # folder usually doesn't exist yet.
    monkeypatch.setattr(
        downloader_mod, '_download_cover', lambda url: b'IMG-BYTES'
    )
    m3u_path = tmp_path / 'My Playlist' / 'My Playlist.m3u'

    result = save_playlist_cover('https://img/cover', m3u_path)

    assert result == tmp_path / 'My Playlist' / 'My Playlist.jpg'
    assert result.read_bytes() == b'IMG-BYTES'


def test_save_playlist_cover_returns_none_on_write_failure(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        downloader_mod, '_download_cover', lambda url: b'IMG-BYTES'
    )
    # A file where the playlist folder should be: the write can't work.
    blocked = tmp_path / 'blocked'
    blocked.write_text('not a directory', encoding='utf-8')
    m3u_path = blocked / 'My Playlist.m3u'

    assert save_playlist_cover('https://img/cover', m3u_path) is None


# ── download_cover_art toggle ───────────────────────────────────────────────


def test_downloader_download_cover_art_defaults_true(tmp_path):
    assert _make(tmp_path).download_cover_art is True


def test_downloader_download_cover_art_can_be_disabled(tmp_path):
    assert _make(tmp_path, download_cover_art=False).download_cover_art is (
        False
    )


def test_embed_metadata_embeds_cover_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(
        downloader_mod, '_download_cover', lambda url: b'IMG-BYTES'
    )
    mp3_path = _minimal_mp3(tmp_path / 'song.mp3')
    embed_metadata(mp3_path, _SONG)
    frames = ID3(mp3_path).getall('APIC')
    assert len(frames) == 1
    assert frames[0].data == b'IMG-BYTES'


def test_embed_metadata_skips_cover_when_disabled(tmp_path, monkeypatch):
    def _boom(url):
        raise AssertionError(
            'should not fetch cover art when download_cover=False'
        )

    monkeypatch.setattr(downloader_mod, '_download_cover', _boom)
    mp3_path = _minimal_mp3(tmp_path / 'song.mp3')
    embed_metadata(mp3_path, _SONG, download_cover=False)
    assert ID3(mp3_path).getall('APIC') == []


# ── _release_type_for_tags ─────────────────────────────────────────────────────


def test_release_type_for_tags_lowercases():
    assert _release_type_for_tags({'release_type': 'Album'}) == 'album'
    assert _release_type_for_tags({'release_type': 'Single'}) == 'single'
    assert _release_type_for_tags({'release_type': 'EP'}) == 'ep'


def test_release_type_for_tags_strips_whitespace():
    assert _release_type_for_tags({'release_type': '  Album  '}) == 'album'


def test_release_type_for_tags_missing_key_returns_empty():
    assert not _release_type_for_tags({})


def test_release_type_for_tags_none_value_returns_empty():
    assert not _release_type_for_tags({'release_type': None})


# ── download() ydl_opts (remote EJS components for SABR fallback) ──────────────


class _CapturedOpts(Exception):
    """Raised by the fake YoutubeDL to stop download() before it would
    otherwise touch the network, once we've captured ydl_opts."""


class _FakeYoutubeDL:
    captured: dict = {}
    post_processors: list = []

    def __init__(self, opts):
        _FakeYoutubeDL.captured = opts
        # yt-dlp postprocessors read their options through `params`.
        self.params = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def add_post_processor(self, pp, when='post_process'):  # noqa: PLR6301
        _FakeYoutubeDL.post_processors.append((pp, when))

    def download(self, urls):  # noqa: PLR6301 - mirrors yt_dlp.YoutubeDL's API
        raise _CapturedOpts


_OVERWRITE_SONG = {
    'name': 'Song',
    'artists': ['Artist'],
    'youtube_id': 'abc123def45',
    'album_name': 'Album',
    'cover_url': 'https://example.com/cover.jpg',
}


# ── download() – overwrite_existing_files ───────────────────────────────────


def test_download_skips_existing_file_when_overwrite_disabled(
    tmp_path, monkeypatch
):
    _FakeYoutubeDL.captured = {}
    monkeypatch.setattr(downloader_mod.yt_dlp, 'YoutubeDL', _FakeYoutubeDL)
    d = _make(tmp_path, overwrite_existing_files=False)
    existing = tmp_path / 'Artist - Song.mp3'
    existing.write_bytes(b'already here')

    result = d.download(_OVERWRITE_SONG)

    assert result == 'Artist - Song.mp3'
    assert existing.read_bytes() == b'already here'  # untouched
    # yt-dlp must never have been reached.
    assert _FakeYoutubeDL.captured == {}


def test_download_reports_done_via_progress_cb_when_skipped(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(downloader_mod.yt_dlp, 'YoutubeDL', _FakeYoutubeDL)
    d = _make(tmp_path, overwrite_existing_files=False)
    (tmp_path / 'Artist - Song.mp3').write_bytes(b'already here')

    calls = []
    d.download(
        _OVERWRITE_SONG,
        progress_cb=lambda pct, msg, provider=None: calls.append((pct, msg)),
    )
    assert calls == [(100.0, 'Already downloaded')]


def test_download_proceeds_when_overwrite_disabled_but_no_existing_file(
    tmp_path, monkeypatch
):
    _FakeYoutubeDL.captured = {}
    monkeypatch.setattr(downloader_mod.yt_dlp, 'YoutubeDL', _FakeYoutubeDL)
    d = _make(tmp_path, overwrite_existing_files=False)

    try:
        d.download(_OVERWRITE_SONG)
    except _CapturedOpts:
        pass
    # yt-dlp *was* reached, since there was nothing to skip.
    assert _FakeYoutubeDL.captured != {}


def test_download_overwrites_by_default_even_if_file_exists(
    tmp_path, monkeypatch
):
    _FakeYoutubeDL.captured = {}
    monkeypatch.setattr(downloader_mod.yt_dlp, 'YoutubeDL', _FakeYoutubeDL)
    d = _make(tmp_path)  # overwrite_existing_files defaults to True
    (tmp_path / 'Artist - Song.mp3').write_bytes(b'already here')

    try:
        d.download(_OVERWRITE_SONG)
    except _CapturedOpts:
        pass
    # Default behavior is unchanged: yt-dlp still runs even though a
    # file already exists at the target path.
    assert _FakeYoutubeDL.captured != {}


class _YoutubeDLMustNotRun:
    def __init__(self, opts):
        raise AssertionError('yt-dlp must not run for an existing song')


def test_download_skips_song_already_in_library_root_for_playlist(
    tmp_path, monkeypatch
):
    # A single-track download lands in the library root; the same song
    # later arriving through a playlist batch targets the playlist folder.
    monkeypatch.setattr(
        downloader_mod.yt_dlp, 'YoutubeDL', _YoutubeDLMustNotRun
    )
    d = _make(tmp_path, overwrite_existing_files=False)
    (tmp_path / 'Artist - Song.mp3').write_bytes(b'already here')

    result = d.download(_OVERWRITE_SONG, subdir='Road Trip')

    assert result == 'Artist - Song.mp3'
    assert not (tmp_path / 'Road Trip').exists()


def test_download_skips_song_already_in_another_playlist_folder(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        downloader_mod.yt_dlp, 'YoutubeDL', _YoutubeDLMustNotRun
    )
    d = _make(tmp_path, overwrite_existing_files=False)
    (tmp_path / 'Gym').mkdir()
    (tmp_path / 'Gym' / 'Artist - Song.mp3').write_bytes(b'already here')

    result = d.download(_OVERWRITE_SONG, subdir='Road Trip')

    assert result == 'Gym/Artist - Song.mp3'


def test_download_skips_song_saved_under_previous_organize_layout(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        downloader_mod.yt_dlp, 'YoutubeDL', _YoutubeDLMustNotRun
    )
    d = _make(
        tmp_path, overwrite_existing_files=False, organize_by_artist=True
    )
    (tmp_path / 'Artist - Song.mp3').write_bytes(b'from before organizing')

    assert d.download(_OVERWRITE_SONG) == 'Artist - Song.mp3'


def test_download_skip_matches_filename_case_insensitively(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        downloader_mod.yt_dlp, 'YoutubeDL', _YoutubeDLMustNotRun
    )
    d = _make(tmp_path, overwrite_existing_files=False)
    (tmp_path / 'Mix').mkdir()
    (tmp_path / 'Mix' / 'ARTIST - song.flac').write_bytes(b'x')

    assert d.download(_OVERWRITE_SONG) == 'Mix/ARTIST - song.flac'


def test_download_skip_requires_template_folders_to_match(
    tmp_path, monkeypatch
):
    # With "{artists}/{title}" the artist folder is part of the song's
    # identity: another artist's "Song" is a different song.
    _FakeYoutubeDL.captured = {}
    monkeypatch.setattr(downloader_mod.yt_dlp, 'YoutubeDL', _FakeYoutubeDL)
    d = _make(
        tmp_path,
        overwrite_existing_files=False,
        output_template='{artists}/{title}',
    )
    (tmp_path / 'Someone Else').mkdir()
    (tmp_path / 'Someone Else' / 'Song.mp3').write_bytes(b'x')

    try:
        d.download(_OVERWRITE_SONG)
    except _CapturedOpts:
        pass
    assert _FakeYoutubeDL.captured != {}


def test_download_lyrics_sidecar_alone_does_not_count_as_downloaded(
    tmp_path, monkeypatch
):
    _FakeYoutubeDL.captured = {}
    monkeypatch.setattr(downloader_mod.yt_dlp, 'YoutubeDL', _FakeYoutubeDL)
    d = _make(tmp_path, overwrite_existing_files=False)
    (tmp_path / 'Artist - Song.lrc').write_text('[00:01.00]la')

    try:
        d.download(_OVERWRITE_SONG)
    except _CapturedOpts:
        pass
    assert _FakeYoutubeDL.captured != {}


def test_download_skip_happens_before_youtube_music_search(
    tmp_path, monkeypatch
):
    # Spotify songs carry title/artists/album up front, so an existing
    # file is detected without spending a YouTube Music search on it.
    def _no_search(*_args, **_kwargs):
        raise AssertionError('YouTube Music must not be searched')

    monkeypatch.setattr(downloader_mod, 'find_match', _no_search)
    monkeypatch.setattr(
        downloader_mod.yt_dlp, 'YoutubeDL', _YoutubeDLMustNotRun
    )
    d = _make(tmp_path, overwrite_existing_files=False)
    (tmp_path / 'Artist - Song.mp3').write_bytes(b'already here')
    song = {k: v for k, v in _OVERWRITE_SONG.items() if k != 'youtube_id'}

    assert d.download(song, subdir='Road Trip') == 'Artist - Song.mp3'


def test_download_searches_first_when_path_needs_enriched_fields(
    tmp_path, monkeypatch
):
    # "{album}" is unknown until enrichment, so the early check must not
    # guess a path from incomplete data.
    searched = []

    def _search(song):
        searched.append(song['name'])
        return None, None

    monkeypatch.setattr(downloader_mod, 'find_match', _search)
    d = _make(
        tmp_path,
        overwrite_existing_files=False,
        output_template='{album}/{title}',
    )
    (tmp_path / 'Song.mp3').write_bytes(b'unrelated single')

    try:
        d.download({'name': 'Song', 'artists': ['Artist']})
    except RuntimeError:
        pass  # no match: the search itself is what's asserted
    assert searched == ['Song']


def test_download_concurrent_duplicates_fetch_only_once(tmp_path, monkeypatch):
    # The same song twice in one playlist (or in two playlists syncing at
    # once) runs on parallel worker threads; only one may download it.
    fetches = []

    class _SlowYoutubeDL:
        def __init__(self, opts):
            self.outtmpl = opts['outtmpl']
            self.params = opts

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def add_post_processor(self, pp, when='post_process'):
            pass

        def download(self, urls):
            fetches.append(urls)
            time.sleep(0.2)
            _minimal_mp3(Path(self.outtmpl.replace('%(ext)s', 'mp3')))

    monkeypatch.setattr(downloader_mod.yt_dlp, 'YoutubeDL', _SlowYoutubeDL)
    monkeypatch.setattr(downloader_mod, '_fetch_itunes_genre', lambda s: None)
    monkeypatch.setattr(downloader_mod, '_download_cover', lambda url: None)
    d = _make(tmp_path, overwrite_existing_files=False)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda sub: d.download(dict(_OVERWRITE_SONG), subdir=sub),
                ['Road Trip', 'Road Trip'],
            )
        )

    assert len(fetches) == 1
    assert results == ['Road Trip/Artist - Song.mp3'] * 2


def test_existing_filename_for_ignores_non_audio_sidecars(tmp_path):
    d = _make(tmp_path, audio_format='flac')
    (tmp_path / 'Artist - Song.lrc').write_text('[00:01.00]la')
    assert d.existing_filename_for(_OVERWRITE_SONG) is None

    (tmp_path / 'Artist - Song.mp3').write_bytes(b'x')
    assert d.existing_filename_for(_OVERWRITE_SONG) == 'Artist - Song.mp3'


def test_existing_filename_for_fallback_handles_glob_characters(tmp_path):
    d = _make(tmp_path, audio_format='flac')
    song = {'name': 'Song [Live]', 'artists': ['Artist']}
    (tmp_path / 'Artist - Song [Live].mp3').write_bytes(b'x')
    assert d.existing_filename_for(song) == 'Artist - Song [Live].mp3'


def test_download_ydl_opts_enables_remote_ejs_component(tmp_path, monkeypatch):
    """Without `remote_components: ['ejs:github']`, yt-dlp refuses to
    fetch the EJS challenge-solver script even when a JS runtime is
    installed, so the `web`/`web_embedded` fallback clients silently
    yield no audio once YouTube's SABR rollout gates `ios`/`android`
    (henriquesebastiao/downtify#247)."""
    monkeypatch.setattr(downloader_mod.yt_dlp, 'YoutubeDL', _FakeYoutubeDL)
    d = _make(tmp_path)
    song = {
        'name': 'Song',
        'artists': ['Artist'],
        'youtube_id': 'abc123def45',
        'album_name': 'Album',
        'cover_url': 'https://example.com/cover.jpg',
    }
    try:
        d.download(song)
    except _CapturedOpts:
        pass
    assert _FakeYoutubeDL.captured.get('remote_components') == ['ejs:github']


# ── age-restricted error translation ────────────────────────────────────────


_AGE_GATE_ERROR = RuntimeError(
    'ERROR: [youtube] lENt7-t8I-I: Sign in to confirm your age. This video '
    'may be inappropriate for some users. Use --cookies-from-browser or '
    '--cookies for the authentication. See https://github.com/yt-dlp/yt-dlp'
    '/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp'
)


def test_age_gate_error_tells_user_to_upload_cookies():
    translated = downloader_mod._translate_download_error(
        _AGE_GATE_ERROR, {'name': 'Some Track'}, has_cookies=False
    )
    message = str(translated)
    assert isinstance(translated, RuntimeError)
    assert 'Some Track' in message
    assert 'cookies.txt' in message
    # The raw yt-dlp CLI advice means nothing in the web UI and is the
    # single most-reported "downloads are broken" symptom.
    assert '--cookies-from-browser' not in message
    assert 'yt-dlp' not in message


def test_age_gate_error_with_cookies_suggests_refreshing_them():
    translated = downloader_mod._translate_download_error(
        _AGE_GATE_ERROR, {'name': 'Some Track'}, has_cookies=True
    )
    message = str(translated)
    assert 'age verification' in message
    assert 'upload it again' in message


def test_non_age_gate_errors_are_passed_through_untouched():
    raw = RuntimeError('ERROR: unable to download video data: HTTP Error 403')
    translated = downloader_mod._translate_download_error(
        raw, {'name': 'Some Track'}, has_cookies=False
    )
    assert translated is raw


def test_is_age_restricted_error_matches_youtube_wording():
    assert downloader_mod.is_age_restricted_error(str(_AGE_GATE_ERROR))
    assert downloader_mod.is_age_restricted_error('AGE_VERIFICATION_REQUIRED')
    assert not downloader_mod.is_age_restricted_error('HTTP Error 403')


# ── audio extraction honors the chosen bitrate (M4A/OPUS) and OGG ───────────


def test_download_registers_bitrate_aware_extract_audio_pp(
    tmp_path, monkeypatch
):
    _FakeYoutubeDL.captured = {}
    _FakeYoutubeDL.post_processors = []
    monkeypatch.setattr(downloader_mod.yt_dlp, 'YoutubeDL', _FakeYoutubeDL)
    d = _make(tmp_path, audio_format='m4a', audio_bitrate='320')
    try:
        d.download(_OVERWRITE_SONG)
    except _CapturedOpts:
        pass
    assert 'postprocessors' not in _FakeYoutubeDL.captured
    [(pp, when)] = _FakeYoutubeDL.post_processors
    assert isinstance(pp, _ExtractAudioPP)
    assert when == 'post_process'
    assert pp._codec == 'm4a'
    assert pp._bitrate_bps == 320_000


def test_extract_audio_pp_maps_ogg_to_vorbis():
    # Regression: yt-dlp has no "ogg" codec; OGG downloads crashed with
    # KeyError: 'ogg' inside the conversion.
    pp = _ExtractAudioPP(yt_dlp.YoutubeDL({'quiet': True}), 'ogg', '320')
    assert pp._codec == 'vorbis'


def test_audio_bit_rate_prefers_the_audio_stream():
    meta = {
        'streams': [{'codec_type': 'audio', 'bit_rate': '129687'}],
        'format': {'bit_rate': '131000'},
    }
    assert _audio_bit_rate(meta) == 129687


def test_audio_bit_rate_falls_back_to_container_for_audio_only_files():
    # WebM/Ogg audio streams carry no bit_rate of their own.
    meta = {
        'streams': [{'codec_type': 'audio'}],
        'format': {'bit_rate': '151255'},
    }
    assert _audio_bit_rate(meta) == 151255


def test_audio_bit_rate_ignores_container_rate_inflated_by_video():
    meta = {
        'streams': [{'codec_type': 'video'}, {'codec_type': 'audio'}],
        'format': {'bit_rate': '600000'},
    }
    assert _audio_bit_rate(meta) is None


@pytest.mark.parametrize(
    'meta',
    [
        {},
        {'streams': [{'codec_type': 'video', 'bit_rate': '500000'}]},
        {'streams': [{'codec_type': 'audio', 'bit_rate': 'N/A'}]},
    ],
)
def test_audio_bit_rate_unknown(meta):
    assert _audio_bit_rate(meta) is None


@pytest.mark.parametrize(
    ('audio_format', 'bitrate', 'source_codec', 'source_bps', 'expected'),
    [
        # The reported bug: YouTube's ~128 kbps AAC copied into M4A.
        ('m4a', '320', 'aac', 129_687, 'aac-reencode'),
        ('m4a', '192', 'aac', 129_687, 'aac-reencode'),
        # Already at the chosen bitrate: keep the lossless copy.
        ('m4a', '128', 'aac', 129_687, 'aac'),
        # Same shortcut for OPUS from YouTube's Opus stream.
        ('opus', '256', 'opus', 151_255, 'opus-reencode'),
        ('opus', '128', 'opus', 151_255, 'opus-reencode'),
        # Different codecs are encoded by yt-dlp anyway: untouched.
        ('m4a', '320', 'opus', 151_255, 'opus'),
        ('mp3', '320', 'aac', 129_687, 'aac'),
        # Unknown source bitrate: don't guess, keep yt-dlp's copy.
        ('m4a', '320', 'aac', None, 'aac'),
    ],
)
def test_extract_audio_pp_copy_or_encode_decision(  # noqa: PLR0913, PLR0917
    monkeypatch, audio_format, bitrate, source_codec, source_bps, expected
):
    monkeypatch.setattr(
        FFmpegExtractAudioPP,
        'get_audio_codec',
        lambda self, path: source_codec,
    )
    stream = {'codec_type': 'audio'}
    if source_bps is not None:
        stream['bit_rate'] = str(source_bps)
    monkeypatch.setattr(
        _ExtractAudioPP,
        'get_metadata_object',
        lambda self, path, opts=None: {'streams': [stream], 'format': {}},
    )
    pp = _ExtractAudioPP(
        yt_dlp.YoutubeDL({'quiet': True}), audio_format, bitrate
    )
    assert pp.get_audio_codec('/x') == expected


def test_extract_audio_pp_keeps_copy_when_ffprobe_fails(monkeypatch):
    monkeypatch.setattr(
        FFmpegExtractAudioPP, 'get_audio_codec', lambda self, path: 'aac'
    )

    def _boom(self, path, opts=None):
        raise RuntimeError('ffprobe missing')

    monkeypatch.setattr(_ExtractAudioPP, 'get_metadata_object', _boom)
    pp = _ExtractAudioPP(yt_dlp.YoutubeDL({'quiet': True}), 'm4a', '320')
    assert pp.get_audio_codec('/x') == 'aac'


_HAS_FFMPEG = bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))


def _probe_audio(path: str) -> tuple[str, int]:
    out = subprocess.run(
        [
            'ffprobe',
            '-v',
            'error',
            '-select_streams',
            'a:0',
            '-show_entries',
            'stream=codec_name,bit_rate',
            '-of',
            'csv=p=0',
            path,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    codec, _, rate = out.partition(',')
    return codec, int(rate) if rate.isdigit() else 0


def _aac_source(tmp_path: Path) -> Path:
    # Stereo noise, so the encoders actually use the bitrate they're given
    # (a pure tone compresses far below it).
    src = tmp_path / 'source.m4a'
    subprocess.run(
        [
            'ffmpeg',
            '-v',
            'error',
            '-f',
            'lavfi',
            '-i',
            'anoisesrc=d=4:c=pink:r=44100,aformat=channel_layouts=stereo',
            '-c:a',
            'aac',
            '-b:a',
            '128k',
            str(src),
        ],
        check=True,
    )
    return src


@pytest.mark.skipif(not _HAS_FFMPEG, reason='ffmpeg/ffprobe not installed')
def test_extract_audio_pp_m4a_from_aac_source_uses_chosen_bitrate(tmp_path):
    src = _aac_source(tmp_path)
    ydl = yt_dlp.YoutubeDL({'quiet': True, 'noprogress': True})
    pp = _ExtractAudioPP(ydl, 'm4a', '320')
    _, info = pp.run({'filepath': str(src), 'ext': 'm4a'})
    codec, rate = _probe_audio(info['filepath'])
    assert codec == 'aac'
    # yt-dlp's plain ExtractAudio leaves this at the source's ~128 kbps.
    assert rate > 250_000


@pytest.mark.skipif(not _HAS_FFMPEG, reason='ffmpeg/ffprobe not installed')
def test_extract_audio_pp_m4a_at_source_bitrate_is_left_as_is(tmp_path):
    src = _aac_source(tmp_path)
    before = src.read_bytes()
    ydl = yt_dlp.YoutubeDL({'quiet': True, 'noprogress': True})
    pp = _ExtractAudioPP(ydl, 'm4a', '128')
    _, info = pp.run({'filepath': str(src), 'ext': 'm4a'})
    assert info['filepath'] == str(src)
    assert src.read_bytes() == before


@pytest.mark.skipif(not _HAS_FFMPEG, reason='ffmpeg/ffprobe not installed')
def test_extract_audio_pp_ogg_produces_vorbis(tmp_path):
    src = _aac_source(tmp_path)
    ydl = yt_dlp.YoutubeDL({'quiet': True, 'noprogress': True})
    pp = _ExtractAudioPP(ydl, 'ogg', '192')
    _, info = pp.run({'filepath': str(src), 'ext': 'm4a'})
    assert info['filepath'].endswith('.ogg')
    codec, _ = _probe_audio(info['filepath'])
    assert codec == 'vorbis'
