"""Tests for marking a library album as a Various Artists compilation by
hand (``downtify/compilation.py``, ``POST /api/library/compilation``).

Aliases only - no real artist names.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from mutagen.flac import FLAC
from mutagen.id3 import ID3
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis
from starlette.testclient import TestClient

import main
from downtify import api, compilation
from downtify.compilation import (
    CompilationError,
    CompilationMarks,
    retag_file,
    set_album_compilation,
    write_album_artist_tags,
)
from downtify.downloader import Downloader, embed_metadata

needs_ffmpeg = pytest.mark.skipif(
    shutil.which('ffmpeg') is None, reason='no ffmpeg'
)

_CODECS = {
    'mp3': ['-c:a', 'libmp3lame', '-b:a', '64k'],
    'flac': ['-c:a', 'flac'],
    'm4a': ['-c:a', 'aac', '-b:a', '64k'],
    'opus': ['-c:a', 'libopus', '-b:a', '32k'],
    'ogg': ['-c:a', 'libvorbis', '-q:a', '1'],
}


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
            'sine=frequency=440:duration=0.5',
            *_CODECS[path.suffix.lstrip('.')],
            str(path),
        ],
        check=True,
    )
    return path


def _track(path: Path, title: str, artists: list[str], **extra) -> Path:
    _audio(path)
    embed_metadata(
        path,
        {
            'name': title,
            'artists': artists,
            'album_name': 'Glass Harbor',
            'album_artist': 'AliasNorth',
            **extra,
        },
        download_cover=False,
    )
    return path


def _tags(path: Path) -> dict:
    """``{album_artist, compilation, title}`` as each format stores them."""

    suffix = path.suffix.lstrip('.')
    if suffix == 'mp3':
        tags = ID3(path)
        return {
            'album_artist': str(tags['TPE2'].text[0])
            if 'TPE2' in tags
            else '',
            'compilation': 'TCMP' in tags,
            'title': str(tags['TIT2'].text[0]),
        }
    if suffix == 'm4a':
        tags = MP4(path).tags
        return {
            'album_artist': (tags.get('aART') or [''])[0],
            'compilation': bool(tags.get('cpil')),
            'title': tags['\xa9nam'][0],
        }
    reader = {'flac': FLAC, 'ogg': OggVorbis, 'opus': OggOpus}[suffix]
    tags = reader(path)
    return {
        'album_artist': (tags.get('albumartist') or [''])[0],
        'compilation': bool(tags.get('compilation')),
        'title': tags['title'][0],
    }


# ── The two tags, in every format ─────────────────────────────────────────


@needs_ffmpeg
@pytest.mark.parametrize('fmt', sorted(_CODECS))
def test_write_album_artist_tags_round_trip(tmp_path, fmt):
    path = _track(tmp_path / f'a.{fmt}', 'Harbor Lights', ['AliasNorth'])

    write_album_artist_tags(path, 'Various Artists', compilation=True)
    assert _tags(path) == {
        'album_artist': 'Various Artists',
        'compilation': True,
        'title': 'Harbor Lights',
    }

    write_album_artist_tags(path, 'AliasNorth', compilation=False)
    assert _tags(path) == {
        'album_artist': 'AliasNorth',
        'compilation': False,
        'title': 'Harbor Lights',
    }


@needs_ffmpeg
def test_retag_file_keeps_the_modification_time(tmp_path):
    path = _track(tmp_path / 'a.mp3', 'Harbor Lights', ['AliasNorth'])
    os.utime(path, ns=(1_600_000_000_000_000_000, 1_600_000_000_000_000_000))

    retag_file(path, 'Various Artists', compilation=True)

    assert path.stat().st_mtime_ns == 1_600_000_000_000_000_000
    assert _tags(path)['compilation'] is True
    assert not list(tmp_path.glob('*downtify-upgrade*'))


@needs_ffmpeg
def test_retag_file_leaves_the_original_when_writing_fails(
    tmp_path, monkeypatch
):
    path = _track(tmp_path / 'a.mp3', 'Harbor Lights', ['AliasNorth'])
    before = path.read_bytes()

    def boom(*_a, **_kw):
        raise RuntimeError('disk full')

    monkeypatch.setattr(compilation, 'write_album_artist_tags', boom)
    with pytest.raises(RuntimeError):
        retag_file(path, 'Various Artists', compilation=True)

    assert path.read_bytes() == before
    assert not list(tmp_path.glob('*downtify-upgrade*'))


# ── Marking and unmarking an album ────────────────────────────────────────


def _album(tmp_path: Path) -> list[tuple[str, Path]]:
    return [
        (
            'AliasNorth/Glass Harbor/a.mp3',
            _track(
                tmp_path / 'a.mp3',
                'Harbor Lights',
                ['AliasNorth', 'AliasSouth', 'AliasEast'],
            ),
        ),
        (
            'AliasNorth/Glass Harbor/b.mp3',
            _track(tmp_path / 'b.mp3', 'Tide Line', ['AliasNorth']),
        ),
    ]


_SONG = {
    'name': 'Low Water',
    'artists': ['AliasNorth', 'AliasGuest'],
    'album_name': 'Glass Harbor',
    'album_artist': 'AliasNorth',
}


@needs_ffmpeg
def test_marking_retags_every_track_and_remembers_the_album(tmp_path):
    files = _album(tmp_path)
    marks = CompilationMarks(tmp_path / 'library.db')

    result = set_album_compilation(files, compilation=True, marks=marks)

    assert result.album_artist == 'Various Artists'
    assert result.changed == [stored for stored, _ in files]
    for _, full in files:
        assert _tags(full)['album_artist'] == 'Various Artists'
        assert _tags(full)['compilation'] is True
    # A later download of the same album gets the same tags.
    assert marks.override_for(dict(_SONG)) == {
        'album_artist': 'Various Artists',
        'compilation': True,
    }
    assert marks.override_for({**_SONG, 'album_name': 'Other'}) == {}


@needs_ffmpeg
def test_unmarking_puts_the_album_artist_back_and_forgets(tmp_path):
    files = _album(tmp_path)
    marks = CompilationMarks(tmp_path / 'library.db')
    set_album_compilation(files, compilation=True, marks=marks)

    result = set_album_compilation(files, compilation=False, marks=marks)

    assert result.album_artist == 'AliasNorth'
    for _, full in files:
        assert _tags(full)['album_artist'] == 'AliasNorth'
        assert _tags(full)['compilation'] is False
    assert marks.override_for(dict(_SONG)) == {}


@needs_ffmpeg
def test_unmarking_a_source_compilation_is_remembered(tmp_path):
    files = [
        (
            'AliasSouth/Glass Harbor/a.mp3',
            _track(
                tmp_path / 'a.mp3',
                'Harbor Lights',
                ['AliasSouth', 'AliasGuest'],
                album_artist='Various Artists',
                compilation=True,
            ),
        ),
        (
            'AliasSouth/Glass Harbor/b.mp3',
            _track(
                tmp_path / 'b.mp3',
                'Tide Line',
                ['AliasSouth'],
                album_artist='Various Artists',
                compilation=True,
            ),
        ),
    ]
    marks = CompilationMarks(tmp_path / 'library.db')

    result = set_album_compilation(files, compilation=False, marks=marks)

    # The artist most of its tracks list first.
    assert result.album_artist == 'AliasSouth'
    song = {
        'artists': ['AliasSouth'],
        'album_name': 'Glass Harbor',
        'album_artist': 'Various Artists',
        'compilation': True,
    }
    assert marks.override_for(song) == {
        'album_artist': 'AliasSouth',
        'compilation': False,
    }


@needs_ffmpeg
def test_marking_needs_one_album_in_the_other_state(tmp_path):
    files = _album(tmp_path)
    other = _track(
        tmp_path / 'c.mp3', 'Elsewhere', ['AliasNorth'], album_name='Other'
    )
    marks = CompilationMarks(tmp_path / 'library.db')

    with pytest.raises(CompilationError, match='one album'):
        set_album_compilation(
            [*files, ('c.mp3', other)], compilation=True, marks=marks
        )
    with pytest.raises(CompilationError, match='not a compilation'):
        set_album_compilation(files, compilation=False, marks=marks)
    with pytest.raises(CompilationError, match='No tracks'):
        set_album_compilation([], compilation=True, marks=marks)


@needs_ffmpeg
def test_nothing_is_remembered_when_no_file_changed(tmp_path, monkeypatch):
    files = _album(tmp_path)
    marks = CompilationMarks(tmp_path / 'library.db')

    def boom(*_a, **_kw):
        raise RuntimeError('read-only')

    monkeypatch.setattr(compilation, 'retag_file', boom)
    result = set_album_compilation(files, compilation=True, marks=marks)

    assert result.changed == []
    assert len(result.failed) == 2
    assert marks.override_for(dict(_SONG)) == {}


# ── The downloader applies a remembered mark ─────────────────────────────


def test_downloader_applies_the_album_override(tmp_path):
    dl = Downloader(tmp_path)
    dl.album_override = lambda song: {
        'album_artist': 'Various Artists',
        'compilation': True,
    }
    out = dl._with_album_override(dict(_SONG))
    assert out['album_artist'] == 'Various Artists'
    assert out['compilation'] is True


def test_downloader_ignores_a_failing_album_override(tmp_path):
    dl = Downloader(tmp_path)

    def boom(_song):
        raise RuntimeError('db locked')

    dl.album_override = boom
    assert dl._with_album_override(dict(_SONG)) == _SONG


# ── POST /api/library/compilation ─────────────────────────────────────────


@pytest.fixture
def client(tmp_path, monkeypatch):
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'index.html').write_text('<html>Downtify</html>')
    downloads = tmp_path / 'downloads'
    monkeypatch.setattr(main, 'DOWNLOAD_DIR', downloads)
    monkeypatch.setattr(main, 'DATABASE_DIR', tmp_path / 'data')
    monkeypatch.setattr(main, 'WEB_GUI_LOCATION', str(web))
    for name in (
        'auth',
        'activity',
        'identity',
        'downloader',
        'settings',
        'metadata_cache',
        'track_index',
        'compilation_marks',
    ):
        monkeypatch.setattr(api.state, name, getattr(api.state, name))
    app = TestClient(main.build_app(), base_url='http://testserver')
    api.state.compilation_marks = CompilationMarks(tmp_path / 'library.db')
    app.post(
        '/api/auth/login', json={'username': 'admin', 'password': 'downtify'}
    )
    app.downloads = downloads
    return app


@needs_ffmpeg
def test_compilation_route_marks_the_album(client):
    folder = client.downloads / 'AliasNorth' / 'Glass Harbor'
    _track(folder / 'a.mp3', 'Harbor Lights', ['AliasNorth', 'AliasGuest'])
    _track(folder / 'b.mp3', 'Tide Line', ['AliasNorth'])
    files = ['AliasNorth/Glass Harbor/a.mp3', 'AliasNorth/Glass Harbor/b.mp3']

    res = client.post(
        '/api/library/compilation', json={'files': files, 'compilation': True}
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body['album_artist'] == 'Various Artists'
    assert body['compilation'] is True
    assert sorted(body['changed']) == files
    assert _tags(folder / 'a.mp3')['compilation'] is True
    kinds = [e['kind'] for e in client.get('/api/activity').json()['entries']]
    assert 'album_compilation' in kinds


def test_compilation_route_rejects_a_bad_request(client):
    assert (
        client.post(
            '/api/library/compilation', json={'files': [], 'compilation': True}
        ).status_code
        == 400
    )
    assert (
        client.post(
            '/api/library/compilation',
            json={'files': ['a.mp3'], 'compilation': 'yes'},
        ).status_code
        == 400
    )
    assert (
        client.post(
            '/api/library/compilation',
            json={'files': ['missing.mp3'], 'compilation': True},
        ).status_code
        == 404
    )


def test_only_admins_mark_compilations(client):
    api.state.auth.users.create('maria', 'correct horse battery')
    client.cookies.clear()
    client.post(
        '/api/auth/login',
        json={'username': 'maria', 'password': 'correct horse battery'},
    )
    refused = client.post(
        '/api/library/compilation',
        json={'files': ['a.mp3'], 'compilation': True},
    )
    assert refused.status_code == 403
