"""Extended tests for Downloader: _format_basename, _artist_subdir and
organize_by_artist routing logic."""

from __future__ import annotations

from pathlib import Path

from downtify import downloader as downloader_mod
from downtify.downloader import Downloader


def _make(tmp_path: Path, **kwargs) -> Downloader:
    return Downloader(tmp_path, **kwargs)


# ── _format_basename ──────────────────────────────────────────────────────────


def test_format_basename_default_template(tmp_path):
    d = _make(tmp_path)
    result = d._format_basename({
        'name': 'Do I Wanna Know',
        'artists': ['Arctic Monkeys'],
    })
    assert result == 'Arctic Monkeys - Do I Wanna Know'


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


def test_format_basename_bad_template_falls_back(tmp_path):
    d = _make(tmp_path, output_template='{nonexistent_key}')
    result = d._format_basename({'name': 'Song', 'artists': ['Artist']})
    assert 'Song' in result


# ── _artist_subdir ────────────────────────────────────────────────────────────


def test_artist_subdir_returns_first_artist():
    result = Downloader._artist_subdir({
        'artists': ['Arctic Monkeys', 'Other']
    })
    assert result == 'Arctic Monkeys'


def test_artist_subdir_empty_list_returns_unknown():
    assert Downloader._artist_subdir({'artists': []}) == 'unknown'


def test_artist_subdir_missing_key_returns_unknown():
    assert Downloader._artist_subdir({}) == 'unknown'


def test_artist_subdir_sanitizes_slashes():
    result = Downloader._artist_subdir({'artists': ['AC/DC']})
    assert '/' not in result


def test_artist_subdir_sanitizes_colons():
    result = Downloader._artist_subdir({'artists': ['Artist: Live']})
    assert ':' not in result


# ── organize_by_artist – existing_filename_for ────────────────────────────────


def test_organize_by_artist_finds_file_in_artist_dir(tmp_path):
    d = _make(tmp_path, organize_by_artist=True)
    artist_dir = tmp_path / 'Arctic Monkeys'
    artist_dir.mkdir()
    (artist_dir / 'Arctic Monkeys - Do I Wanna Know.mp3').write_bytes(b'\x00')
    result = d.existing_filename_for({
        'name': 'Do I Wanna Know',
        'artists': ['Arctic Monkeys'],
    })
    assert result == 'Arctic Monkeys/Arctic Monkeys - Do I Wanna Know.mp3'


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


def test_fallback_video_id_via_ytdlp_returns_first_entry(monkeypatch):
    class FakeYDL:
        def __init__(self, _opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _query, download=False):
            assert download is False
            return {'entries': [{'id': 'abc123def45'}]}

    monkeypatch.setattr(downloader_mod.yt_dlp, 'YoutubeDL', FakeYDL)
    vid = downloader_mod._fallback_video_id_via_ytdlp(
        {'name': 'Track', 'artists': ['Artist']}
    )
    assert vid == 'abc123def45'


def test_resolve_video_id_prefers_provider_order_youtube_first(monkeypatch):
    d = Downloader('/tmp', audio_providers=['youtube', 'youtube-music'])

    monkeypatch.setattr(
        downloader_mod,
        '_fallback_video_id_via_ytdlp',
        lambda _song: 'yt123',
    )

    def should_not_run(_song):
        raise AssertionError('find_match should not run when youtube succeeds')

    monkeypatch.setattr(downloader_mod, 'find_match', should_not_run)
    vid, match, provider = d._resolve_video_id({'name': 'Track', 'artists': []})
    assert vid == 'yt123'
    assert match is None
    assert provider == 'youtube'


def test_resolve_video_id_uses_second_provider_on_first_failure(monkeypatch):
    d = Downloader('/tmp', audio_providers=['youtube', 'youtube-music'])
    monkeypatch.setattr(
        downloader_mod, '_fallback_video_id_via_ytdlp', lambda _song: None
    )
    monkeypatch.setattr(
        downloader_mod,
        'find_match',
        lambda _song: ('ytm456', {'videoId': 'ytm456'}),
    )
    vid, match, provider = d._resolve_video_id({'name': 'Track', 'artists': []})
    assert vid == 'ytm456'
    assert isinstance(match, dict)
    assert provider == 'youtube-music'
