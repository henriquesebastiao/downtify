"""`.lrc` sidecar location: beside the audio vs a dedicated folder."""

from __future__ import annotations

from pathlib import Path

from mutagen.id3 import ID3

from downtify import lyrics as lyrics_mod
from downtify.library_cleanup import delete_lrc_sidecar
from downtify.library_paths import EXTERNAL_LIBRARY_PREFIX, extra_dir_id
from downtify.lyrics import (
    Lyrics,
    lrc_sidecar_path,
    read_track_lyrics,
    sanitize_lyrics_lrc_dir,
    write_to_file,
)


def test_sanitize_rejects_dir_inside_downloads(tmp_path):
    downloads = tmp_path / 'downloads'
    downloads.mkdir()
    assert (
        sanitize_lyrics_lrc_dir(
            str(downloads / 'lyrics'),
            download_dir=downloads,
        )
        == '/data/lyrics'
    )


def test_sanitize_keeps_dir_outside_music_trees(tmp_path):
    downloads = tmp_path / 'downloads'
    extra = tmp_path / 'music'
    lyrics_dir = tmp_path / 'lyrics'
    downloads.mkdir()
    extra.mkdir()
    assert sanitize_lyrics_lrc_dir(
        str(lyrics_dir),
        download_dir=downloads,
        extra_dirs=(extra,),
    ) == str(lyrics_dir)


def test_sidecar_path_mirrors_library_tree(tmp_path):
    downloads = tmp_path / 'downloads'
    audio = downloads / 'Kenji Aoki' / 'Harbor Lights.mp3'
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b'x')
    lyrics_root = tmp_path / 'lrc'
    dest = lrc_sidecar_path(
        audio,
        settings={
            'lyrics_lrc_beside': False,
            'lyrics_lrc_dir': str(lyrics_root),
        },
        download_dir=downloads,
    )
    assert dest == lyrics_root / 'Kenji Aoki' / 'Harbor Lights.lrc'


def test_sidecar_path_extra_folder(tmp_path):
    extra = tmp_path / 'collection'
    extra.mkdir()
    audio = extra / 'Song.mp3'
    audio.write_bytes(b'x')
    lyrics_root = tmp_path / 'lrc'
    dest = lrc_sidecar_path(
        audio,
        settings={
            'lyrics_lrc_beside': False,
            'lyrics_lrc_dir': str(lyrics_root),
        },
        download_dir=tmp_path / 'downloads',
        extra_dirs=(extra,),
    )
    assert dest == (
        lyrics_root
        / f'{EXTERNAL_LIBRARY_PREFIX}{extra_dir_id(extra)}'
        / 'Song.lrc'
    )


def test_write_and_read_dedicated_sidecar(tmp_path):
    downloads = tmp_path / 'downloads'
    audio = downloads / 'Song.mp3'
    audio.parent.mkdir()
    ID3().save(str(audio), v2_version=4)
    lyrics_root = tmp_path / 'lrc'
    settings = {
        'lyrics_lrc_beside': False,
        'lyrics_lrc_dir': str(lyrics_root),
    }

    def _resolve(path: Path) -> Path:
        return lrc_sidecar_path(
            path,
            settings=settings,
            download_dir=downloads,
        )

    lyrics_mod.set_lrc_resolver(_resolve, tree_root=lambda: lyrics_root)
    try:
        write_to_file(audio, Lyrics(synced='[00:01.00]Hello', plain='Hello'))
        dest = lyrics_root / 'Song.lrc'
        assert dest.is_file()
        assert not audio.with_suffix('.lrc').exists()
        assert read_track_lyrics(audio)['synced'].startswith('[00:01.00]')
        delete_lrc_sidecar(audio)
        assert not dest.exists()
    finally:
        lyrics_mod.set_lrc_resolver(None)


def test_relocate_copies_beside_into_dedicated_folder(tmp_path):
    extra = tmp_path / 'collection'
    extra.mkdir()
    audio = extra / 'Song.mp3'
    audio.write_bytes(b'x')
    audio.with_suffix('.lrc').write_text('[00:01.00]Hi', encoding='utf-8')
    lyrics_root = tmp_path / 'lrc'
    settings = {
        'lyrics_lrc_beside': False,
        'lyrics_lrc_dir': str(lyrics_root),
    }

    def _resolve(path: Path) -> Path:
        return lrc_sidecar_path(
            path,
            settings=settings,
            download_dir=tmp_path / 'downloads',
            extra_dirs=(extra,),
        )

    lyrics_mod.set_lrc_resolver(_resolve, tree_root=lambda: lyrics_root)
    try:
        assert lyrics_mod.relocate_lrc_sidecar(audio) == 'copied'
        dest = (
            lyrics_root
            / f'{EXTERNAL_LIBRARY_PREFIX}{extra_dir_id(extra)}'
            / 'Song.lrc'
        )
        assert dest.read_text(encoding='utf-8') == '[00:01.00]Hi'
        assert not audio.with_suffix('.lrc').exists()
        assert lyrics_mod.relocate_lrc_sidecar(audio) == 'present'
    finally:
        lyrics_mod.set_lrc_resolver(None)


def test_relocate_copies_dedicated_into_beside(tmp_path):
    extra = tmp_path / 'collection'
    extra.mkdir()
    audio = extra / 'Song.mp3'
    audio.write_bytes(b'x')
    lyrics_root = tmp_path / 'lrc'
    dest = (
        lyrics_root
        / f'{EXTERNAL_LIBRARY_PREFIX}{extra_dir_id(extra)}'
        / 'Song.lrc'
    )
    dest.parent.mkdir(parents=True)
    dest.write_text('[00:01.00]Hi', encoding='utf-8')
    settings = {
        'lyrics_lrc_beside': True,
        'lyrics_lrc_dir': str(lyrics_root),
    }

    def _resolve(path: Path) -> Path:
        return lrc_sidecar_path(
            path,
            settings=settings,
            download_dir=tmp_path / 'downloads',
            extra_dirs=(extra,),
        )

    def _search(path: Path) -> list[Path]:
        return [
            lrc_sidecar_path(
                path,
                settings={**settings, 'lyrics_lrc_beside': False},
                download_dir=tmp_path / 'downloads',
                extra_dirs=(extra,),
            )
        ]

    lyrics_mod.set_lrc_resolver(
        _resolve, tree_root=lambda: lyrics_root, search=_search
    )
    try:
        assert lyrics_mod.relocate_lrc_sidecar(audio) == 'copied'
        assert audio.with_suffix('.lrc').read_text(encoding='utf-8') == (
            '[00:01.00]Hi'
        )
        assert not dest.exists()
    finally:
        lyrics_mod.set_lrc_resolver(None)


def test_relocate_keeps_source_on_read_only_tree(tmp_path, monkeypatch):
    extra = tmp_path / 'collection'
    extra.mkdir()
    audio = extra / 'Song.mp3'
    audio.write_bytes(b'x')
    audio.with_suffix('.lrc').write_text('[00:01.00]Hi', encoding='utf-8')
    lyrics_root = tmp_path / 'lrc'
    settings = {
        'lyrics_lrc_beside': False,
        'lyrics_lrc_dir': str(lyrics_root),
    }

    def _resolve(path: Path) -> Path:
        return lrc_sidecar_path(
            path,
            settings=settings,
            download_dir=tmp_path / 'downloads',
            extra_dirs=(extra,),
        )

    monkeypatch.setattr(lyrics_mod, 'can_mutate_audio', lambda _path: False)
    lyrics_mod.set_lrc_resolver(_resolve, tree_root=lambda: lyrics_root)
    try:
        assert lyrics_mod.relocate_lrc_sidecar(audio) == 'copied'
        dest = (
            lyrics_root
            / f'{EXTERNAL_LIBRARY_PREFIX}{extra_dir_id(extra)}'
            / 'Song.lrc'
        )
        assert dest.read_text(encoding='utf-8') == '[00:01.00]Hi'
        assert audio.with_suffix('.lrc').is_file()
    finally:
        lyrics_mod.set_lrc_resolver(None)


def test_write_to_file_skips_embed_on_read_only(tmp_path, monkeypatch):
    extra = tmp_path / 'collection'
    extra.mkdir()
    audio = extra / 'Song.mp3'
    audio.write_bytes(b'not-a-valid-mp3')
    lyrics_root = tmp_path / 'lrc'
    settings = {
        'lyrics_lrc_beside': False,
        'lyrics_lrc_dir': str(lyrics_root),
    }

    def _resolve(path: Path) -> Path:
        return lrc_sidecar_path(
            path,
            settings=settings,
            download_dir=tmp_path / 'downloads',
            extra_dirs=(extra,),
        )

    monkeypatch.setattr(lyrics_mod, 'can_mutate_audio', lambda _path: False)
    lyrics_mod.set_lrc_resolver(_resolve, tree_root=lambda: lyrics_root)
    try:
        write_to_file(
            audio,
            Lyrics(plain='Hi', synced='[00:01.00]Hi'),
        )
        dest = (
            lyrics_root
            / f'{EXTERNAL_LIBRARY_PREFIX}{extra_dir_id(extra)}'
            / 'Song.lrc'
        )
        assert dest.read_text(encoding='utf-8') == '[00:01.00]Hi'
    finally:
        lyrics_mod.set_lrc_resolver(None)
