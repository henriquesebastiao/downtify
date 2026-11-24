"""Music videos saved next to their songs (issue #680). Offline: the
YouTube Music search and yt-dlp are replaced by fakes."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from downtify import api, music_video, providers
from downtify.auth import CLIENT, classify
from downtify.library_catalog import (
    AUDIO_EXTENSIONS,
    VIDEO_EXTENSIONS,
    LibraryContext,
)
from downtify.library_delete import delete_library_file
from downtify.music_video import (
    DEFAULT_NAME,
    OFFICIAL_TYPE,
    MusicVideos,
    clean_format,
    clean_template,
    clean_video_title,
    pick_video,
    render_name,
)

SONG = {
    'name': 'Night Drive',
    'artists': ['Nora Vale'],
    'album_name': 'Harbor Nights',
    'track_number': 3,
    'duration': 200,
}


def _row(title: str, **values: Any) -> dict[str, Any]:
    row = {
        'videoId': values.pop('vid', title[:11]),
        'title': title,
        'artists': [{'name': values.pop('artist', 'Nora Vale')}],
        'duration_seconds': values.pop('seconds', 205),
    }
    row.update(values)
    return row


def _pick(rows: list[dict[str, Any]], **song: Any) -> Any:
    return pick_video(
        rows,
        title=song.get('title', 'Night Drive'),
        artists=song.get('artists', ['Nora Vale']),
        duration=song.get('duration', 200),
        titles_match=providers.titles_match,
        artists_overlap=providers.artists_overlap,
    )


# ── Names ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        ('', DEFAULT_NAME),
        (None, DEFAULT_NAME),
        ('{filename}-live', '{filename}-live'),
        ('{nope}-video', DEFAULT_NAME),
        ('../{title}/x', '..{title}x'),
        ('plain', DEFAULT_NAME),
    ],
)
def test_clean_template(value, expected):
    assert clean_template(value) == expected


def test_clean_format():
    assert clean_format('MKV') == 'mkv'
    assert clean_format('.mp4') == 'mp4'
    assert clean_format('avi') == 'mp4'


def test_render_name_follows_the_song_file():
    track = Path('/music/Nora Vale/Harbor Nights/03 - Night Drive.mp3')
    assert render_name(DEFAULT_NAME, track, SONG) == '03 - Night Drive-video'
    assert (
        render_name('{track_number} {artist} - {title}', track, SONG)
        == '03 Nora Vale - Night Drive'
    )
    # Never the song's own name (it would be overwritten), never a slash.
    assert render_name('{filename}', track, SONG) == '03 - Night Drive-video'
    assert '/' not in render_name('{title}', track, {'name': 'A/B'})


# ── Picking the video ────────────────────────────────────────────────


def test_clean_video_title():
    assert (
        clean_video_title('Night Drive (Official Music Video)')
        == 'Night Drive'
    )
    assert clean_video_title('Night Drive [4K Remaster]') == 'Night Drive'
    assert clean_video_title('Night Drive (Remix)') == 'Night Drive (Remix)'


def test_official_video_beats_a_closer_upload():
    rows = [
        _row('Night Drive', vid='fan', seconds=200),
        _row(
            'Night Drive (Official Video)',
            vid='official',
            seconds=230,
            videoType=OFFICIAL_TYPE,
        ),
    ]
    assert _pick(rows)['videoId'] == 'official'


def test_other_versions_and_other_songs_are_left_out():
    rows = [
        _row('Night Drive (Live at Wembley)', vid='live'),
        _row('Night Drive (Lyric Video)', vid='lyric'),
        _row('Night Drive (Official Audio)', vid='audio'),
        _row('Night Drive', vid='other', artist='Someone Else'),
        _row('Day Drive (Official Video)', vid='title'),
        _row('Night Drive', vid='short', seconds=60),
    ]
    assert _pick(rows) is None


def test_a_live_song_may_have_a_live_video():
    rows = [_row('Night Drive (Live)', vid='live')]
    assert _pick(rows, title='Night Drive (Live)')['videoId'] == 'live'


def test_closest_length_wins_among_equals():
    rows = [
        _row('Night Drive', vid='far', seconds=300),
        _row('Night Drive', vid='near', seconds=210),
    ]
    assert _pick(rows)['videoId'] == 'near'


# ── Store and download ───────────────────────────────────────────────


def test_store_round_trip(tmp_path):
    store = MusicVideos(tmp_path / 'lib.db')
    assert store.get('a.mp3') is None
    store.set('a.mp3', 'a-video.mp4', 'vid')
    store.set('a.mp3', 'a-video.mkv', 'vid2')
    assert store.get('a.mp3') == 'a-video.mkv'
    assert store.count() == 1
    assert store.forget('a.mp3') == 'a-video.mkv'
    assert store.forget('a.mp3') is None


class _FakeYDL:
    def __init__(self, opts: dict[str, Any]) -> None:
        self.opts = opts
        _FakeYDL.seen.append(opts)

    seen: list[dict[str, Any]] = []

    def __enter__(self) -> _FakeYDL:
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def download(self, urls: list[str]) -> None:
        out = Path(self.opts['outtmpl'].replace('%(ext)s', 'mp4'))
        out.write_bytes(b'video')
        _FakeYDL.urls.extend(urls)

    urls: list[str] = []


def _downloader() -> MagicMock:
    downloader = MagicMock()
    downloader._ydl_options.side_effect = lambda out, hook: (
        {'outtmpl': out, 'format': 'bestaudio/best', 'cookiefile': 'c'},
        True,
    )
    downloader._private_cookiefile.return_value = MagicMock(
        __enter__=lambda self: None, __exit__=lambda *a: None
    )
    return downloader


def test_fetch_saves_the_video_next_to_the_song(tmp_path, monkeypatch):
    folder = tmp_path / 'Nora Vale' / 'Harbor Nights'
    folder.mkdir(parents=True)
    track = folder / '03 - Night Drive.mp3'
    track.write_bytes(b'audio')
    store = MusicVideos(tmp_path / 'lib.db')
    _FakeYDL.seen.clear()
    _FakeYDL.urls.clear()
    monkeypatch.setattr(music_video.yt_dlp, 'YoutubeDL', _FakeYDL)
    monkeypatch.setattr(
        music_video, 'find_video', lambda song: {'videoId': 'abc123'}
    )

    video = music_video.fetch_for_track(
        song=SONG,
        stored='Nora Vale/Harbor Nights/03 - Night Drive.mp3',
        full=track,
        downloader=_downloader(),
        store=store,
        settings={'music_video_name': DEFAULT_NAME},
        stored_of=lambda path: str(path.relative_to(tmp_path)),
    )

    assert video == 'Nora Vale/Harbor Nights/03 - Night Drive-video.mp4'
    assert (folder / '03 - Night Drive-video.mp4').is_file()
    assert _FakeYDL.urls == ['https://www.youtube.com/watch?v=abc123']
    opts = _FakeYDL.seen[0]
    assert opts['merge_output_format'] == 'mp4'
    assert 'height<=1080' in opts['format']
    assert opts['cookiefile'] == 'c'
    assert store.get('Nora Vale/Harbor Nights/03 - Night Drive.mp3') == video

    # Asked again: nothing more is downloaded.
    again = music_video.fetch_for_track(
        song=SONG,
        stored='Nora Vale/Harbor Nights/03 - Night Drive.mp3',
        full=track,
        downloader=_downloader(),
        store=store,
        settings={},
        stored_of=lambda path: str(path.relative_to(tmp_path)),
    )
    assert again is None
    assert len(_FakeYDL.urls) == 1


def test_fetch_without_a_match_saves_nothing(tmp_path, monkeypatch):
    track = tmp_path / 'a.mp3'
    track.write_bytes(b'audio')
    store = MusicVideos(tmp_path / 'lib.db')
    monkeypatch.setattr(music_video, 'find_video', lambda song: None)
    assert (
        music_video.fetch_for_track(
            song=SONG,
            stored='a.mp3',
            full=track,
            downloader=_downloader(),
            store=store,
            settings={},
            stored_of=lambda path: path.name,
        )
        is None
    )
    assert store.count() == 0


def test_an_existing_video_file_is_adopted(tmp_path, monkeypatch):
    track = tmp_path / 'a.mp3'
    track.write_bytes(b'audio')
    (tmp_path / 'a-video.mkv').write_bytes(b'video')
    store = MusicVideos(tmp_path / 'lib.db')
    monkeypatch.setattr(music_video, 'find_video', pytest.fail)
    video = music_video.fetch_for_track(
        song=SONG,
        stored='a.mp3',
        full=track,
        downloader=_downloader(),
        store=store,
        settings={},
        stored_of=lambda path: path.name,
    )
    assert video == 'a-video.mkv'


# ── API ──────────────────────────────────────────────────────────────


@pytest.fixture
def library(tmp_path, monkeypatch):
    music = tmp_path / 'music'
    music.mkdir()
    (music / 'a.mp3').write_bytes(b'audio')
    (music / 'a-video.mp4').write_bytes(b'video')
    store = MusicVideos(tmp_path / 'lib.db')
    ctx = LibraryContext(download_dir=music, slskd_dir=None)
    monkeypatch.setattr(api, 'library_context', lambda: ctx)
    monkeypatch.setattr(api.state, 'music_videos', store)
    return music, store, ctx


def _request() -> Request:
    return Request({'type': 'http', 'headers': []})


def test_the_player_finds_a_songs_video(library):
    _music, store, _ctx = library
    with pytest.raises(HTTPException):
        api.get_music_video(_request(), file='a.mp3')
    store.set('a.mp3', 'a-video.mp4')
    found = api.get_music_video(_request(), file='a.mp3')
    assert found['video'] == 'a-video.mp4'
    assert found['url'] == '/api/music-video/file?file=a.mp3'
    # Not a real video: no bars measured, and the answer is kept.
    assert found['crop'] is None
    assert store.crop('a.mp3') == 'full'
    response = api.stream_music_video(file='a.mp3')
    assert str(response.path).endswith('a-video.mp4')
    # Only a library song's own video, never any path.
    with pytest.raises(HTTPException):
        api.get_music_video(_request(), file='../etc/passwd')


def test_deleting_the_song_deletes_its_video(library):
    music, store, ctx = library
    store.set('a.mp3', 'a-video.mp4')
    result = delete_library_file('a.mp3', ctx, music_videos=store)
    assert result['deleted'] is True
    assert not (music / 'a-video.mp4').exists()
    assert store.get('a.mp3') is None


def test_scheduling_follows_the_setting(monkeypatch, library):
    _music, _store, _ctx = library
    submitted: list[Any] = []
    monkeypatch.setattr(
        music_video,
        'executor',
        lambda: MagicMock(submit=lambda *a: submitted.append(a)),
    )
    monkeypatch.setattr(
        api.state, 'settings', {'download_music_videos': False}
    )
    assert api.schedule_music_video(SONG, 'a.mp3') is False
    api.state.settings['download_music_videos'] = True
    assert api.schedule_music_video(SONG, 'a.mp3') is True
    assert api.schedule_music_video({**SONG, 'replace': {}}, 'a.mp3') is False
    assert len(submitted) == 1


def test_off_by_default():
    assert api.DEFAULT_SETTINGS['download_music_videos'] is False
    assert api.DEFAULT_SETTINGS['music_video_name'] == DEFAULT_NAME
    assert api.DEFAULT_SETTINGS['music_video_format'] == 'mp4'


def test_music_video_routes_are_for_clients():
    assert classify('GET', '/api/music-video') == CLIENT
    assert classify('GET', '/api/music-video/file') == CLIENT


def test_the_listing_never_takes_a_video_for_a_song():
    assert not (AUDIO_EXTENSIONS & VIDEO_EXTENSIONS)


# ── Black bars burnt into the picture ────────────────────────────────


def test_typical_and_picture_crop():
    # Two samples agree on a 4:3 picture; one bright transition reaches
    # wider and one dark scene seems smaller: neither decides.
    boxes = [
        (464, 360, 88, 0),
        (464, 360, 88, 0),
        (610, 360, 14, 0),
        (300, 200, 170, 80),
        (462, 360, 90, 0),
    ]
    assert music_video.typical_crop(boxes) == (464, 360, 88, 0)
    assert music_video.typical_crop([]) is None
    # Bars worth zooming for: the picture box and the frame.
    assert music_video.picture_crop((640, 272, 0, 44), 640, 360) == (
        640,
        272,
        0,
        44,
        640,
        360,
    )
    # A picture that (nearly) fills the frame has none.
    assert music_video.picture_crop((640, 356, 0, 2), 640, 360) is None
    assert music_video.picture_crop(None, 640, 360) is None


def test_crop_round_trip():
    crop = (480, 360, 80, 0, 640, 360)
    assert music_video.format_crop(crop) == '480:360:80:0:640:360'
    assert music_video.format_crop(None) == 'full'
    assert music_video.parse_crop('480:360:80:0:640:360') == {
        'width': 480,
        'height': 360,
        'x': 80,
        'y': 0,
        'video_width': 640,
        'video_height': 360,
    }
    assert music_video.parse_crop('full') is None
    assert music_video.parse_crop('') is None


@pytest.mark.skipif(
    not (shutil.which('ffmpeg') and shutil.which('ffprobe')),
    reason='needs ffmpeg',
)
def test_detect_crop_finds_burnt_in_bars(tmp_path):
    letterboxed = tmp_path / 'bars.mp4'
    # A 640x360 frame with a 640x240 moving picture in the middle.
    subprocess.run(
        [
            'ffmpeg',
            '-loglevel',
            'error',
            '-f',
            'lavfi',
            '-i',
            'testsrc2=size=640x240:rate=10:duration=6',
            '-vf',
            'pad=640:360:0:60:black',
            '-pix_fmt',
            'yuv420p',
            str(letterboxed),
        ],
        check=True,
    )
    crop = music_video.detect_crop(letterboxed)
    assert crop is not None
    w, h, x, y, width, height = crop
    assert (width, height) == (640, 360)
    assert w >= 630
    assert 230 <= h <= 244
    assert 56 <= y <= 64
    full = tmp_path / 'full.mp4'
    subprocess.run(
        [
            'ffmpeg',
            '-loglevel',
            'error',
            '-f',
            'lavfi',
            '-i',
            'testsrc2=size=640x360:rate=10:duration=6',
            '-pix_fmt',
            'yuv420p',
            str(full),
        ],
        check=True,
    )
    assert music_video.detect_crop(full) is None


def test_store_keeps_the_crop(tmp_path):
    store = MusicVideos(tmp_path / 'lib.db')
    store.set('a.mp3', 'a-video.mp4')
    assert not store.crop('a.mp3')
    store.set_crop('a.mp3', 'full')
    assert store.crop('a.mp3') == 'full'
