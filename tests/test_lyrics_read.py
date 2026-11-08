"""Reading back the lyrics saved with a downloaded track (GET /lyrics)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from mutagen.flac import VCFLACDict
from mutagen.id3 import ID3, TIT2, USLT
from mutagen.mp4 import MP4Tags
from mutagen.oggopus import OggOpusVComment
from mutagen.oggvorbis import OggVCommentDict
from starlette.testclient import TestClient

import main
from downtify import api
from downtify import lyrics as lyrics_mod
from downtify.lyrics import read_track_lyrics

_LRC = '[00:12.00]The harbor lights are blinking out\n[00:15.50]One by one'
_FORMATS = ('mp3', 'm4a', 'flac', 'ogg', 'opus')


@pytest.fixture
def lyrics_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html></html>', encoding='utf-8')
    downloads = tmp_path / 'downloads'
    data = tmp_path / 'data'
    downloads.mkdir()
    data.mkdir()
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', downloads)
    monkeypatch.setattr(main, 'DATABASE_DIR', data)
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    for name in (
        'auth',
        'activity',
        'identity',
        'downloader',
        'settings',
        'library_sync',
        'transcoder',
        'cover_thumbs',
        'likes',
        'discover',
        'metadata_cache',
        'track_index',
        'playlist_catalog',
    ):
        monkeypatch.setattr(api.state, name, getattr(api.state, name, None))
    app = main.build_app()
    main._open_library_stores(data / 'downtify_monitor.db')
    client = TestClient(app)
    client.post(
        '/api/auth/login', json={'username': 'admin', 'password': 'downtify'}
    )
    return client, downloads


def _tags_for_format(fmt: str, text: str) -> Any:
    """Real Mutagen tag containers; audio decoding is outside these tests."""

    if fmt == 'mp3':
        tags = ID3()
        tags.add(TIT2(encoding=3, text='Song'))
        if text:
            tags.add(USLT(encoding=3, lang='eng', desc='', text=text))
    elif fmt == 'm4a':
        tags = MP4Tags()
        tags['\xa9nam'] = ['Song']
        if text:
            tags['\xa9lyr'] = [text]
    else:
        comment_type = {
            'flac': VCFLACDict,
            'ogg': OggVCommentDict,
            'opus': OggOpusVComment,
        }[fmt]
        # Ogg constructors also parse audio pages. Initialise just the
        # comment base, retaining the format's real key validation.
        tags = comment_type.__new__(comment_type)
        super(comment_type, tags).__init__()
        tags['TITLE'] = ['Song']
        if text:
            tags['LYRICS'] = [text]
    return tags


@pytest.mark.parametrize('fmt', _FORMATS)
@pytest.mark.parametrize('text', ['  Words\nSecond line  ', ''])
def test_reads_each_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fmt: str, text: str
) -> None:
    tags = _tags_for_format(fmt, text)
    monkeypatch.setattr(
        lyrics_mod, 'MutagenFile', lambda _path: SimpleNamespace(tags=tags)
    )

    assert read_track_lyrics(tmp_path / f'Song.{fmt}') == {
        'synced': '',
        'plain': text.strip(),
    }


@pytest.mark.parametrize('fmt', ['flac', 'ogg', 'opus'])
def test_vorbis_comments_never_receive_mp4_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fmt: str
) -> None:
    tags = _tags_for_format(fmt, 'Vorbis lyrics')
    get = tags.get
    queried: list[str] = []

    def checked_get(key: str) -> Any:
        queried.append(key)
        return get(key)

    monkeypatch.setattr(tags, 'get', checked_get)
    monkeypatch.setattr(lyrics_mod, '_file_tags', lambda _path: tags)

    assert read_track_lyrics(tmp_path / f'Song.{fmt}')['plain'] == (
        'Vorbis lyrics'
    )
    assert queried == ['lyrics']


@pytest.mark.parametrize('fmt', _FORMATS)
@pytest.mark.parametrize('error', [ValueError, KeyError, OSError])
def test_unreadable_tags_preserve_the_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fmt: str,
    error: type[Exception],
) -> None:
    tags = _tags_for_format(fmt, '')

    def unreadable(*_args: Any) -> Any:
        raise error('unsupported or damaged lyric tag')

    monkeypatch.setattr(tags, 'getall' if fmt == 'mp3' else 'get', unreadable)
    monkeypatch.setattr(lyrics_mod, '_file_tags', lambda _path: tags)
    track = tmp_path / f'Song.{fmt}'
    track.with_suffix('.lrc').write_text(_LRC, encoding='utf-8')

    assert read_track_lyrics(track) == {'synced': _LRC, 'plain': ''}


@pytest.mark.parametrize('fmt', _FORMATS)
def test_files_without_tags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fmt: str
) -> None:
    monkeypatch.setattr(
        lyrics_mod, 'MutagenFile', lambda _path: SimpleNamespace(tags=None)
    )
    # Do not let the MP3 ID3 fallback open a nonexistent file.
    (tmp_path / f'Song.{fmt}').write_bytes(b'not audio')

    assert read_track_lyrics(tmp_path / f'Song.{fmt}') == {
        'synced': '',
        'plain': '',
    }


def test_api_returns_sidecar_when_embedded_tags_fail(
    lyrics_client: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, downloads = lyrics_client
    track = downloads / 'Song.flac'
    track.write_bytes(b'not audio')
    track.with_suffix('.lrc').write_text(_LRC, encoding='utf-8')
    tags = _tags_for_format('flac', '')

    def unreadable(_key: str) -> Any:
        raise ValueError('invalid Vorbis comment key')

    monkeypatch.setattr(tags, 'get', unreadable)
    monkeypatch.setattr(lyrics_mod, '_file_tags', lambda _path: tags)

    response = client.get('/lyrics', params={'file': 'Song.flac'})

    assert response.status_code == 200
    assert response.json() == {'synced': _LRC, 'plain': ''}


def _mp3_with_lyrics(path, text):
    tags = ID3()
    tags.add(USLT(encoding=3, lang='eng', desc='', text=text))
    tags.save(str(path), v2_version=4)


def test_reads_sidecar_and_embedded_lyrics(tmp_path):
    track = tmp_path / 'Kenji Aoki - Harbor Lights.mp3'
    _mp3_with_lyrics(track, 'The harbor lights are blinking out')
    track.with_suffix('.lrc').write_text(_LRC, encoding='utf-8')

    lyrics = read_track_lyrics(track)

    assert lyrics == {
        'synced': _LRC,
        'plain': 'The harbor lights are blinking out',
    }


def test_embedded_only(tmp_path):
    track = tmp_path / 'Song.mp3'
    _mp3_with_lyrics(track, 'Only plain words')

    assert read_track_lyrics(track) == {
        'synced': '',
        'plain': 'Only plain words',
    }


def test_track_without_lyrics(tmp_path):
    track = tmp_path / 'Song.opus'
    track.write_bytes(b'not really audio')

    assert read_track_lyrics(track) == {'synced': '', 'plain': ''}


def test_embedded_lyrics_in_vorbis_comments(tmp_path, monkeypatch):
    # FLAC/Ogg/Opus tags refuse MP4's "\xa9lyr" key outright (ValueError);
    # that must not hide the Vorbis LYRICS comment behind it.
    comments = VCFLACDict()
    comments['LYRICS'] = ['Words in a FLAC']
    monkeypatch.setattr(lyrics_mod, '_file_tags', lambda path: comments)

    assert read_track_lyrics(tmp_path / 'Song.flac')['plain'] == (
        'Words in a FLAC'
    )
