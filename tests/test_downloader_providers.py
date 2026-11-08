"""Audio provider order in Downloader.download(): slskd, YouTube Music,
plain YouTube and SoundCloud, on top of main's tagging pipeline."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Lock

import pytest
from mutagen.id3 import ID3

from downtify import downloader as downloader_mod
from downtify.downloader import Downloader, NoAudioMatchError
from tests.test_downloader_extended import _minimal_mp3

_SONG = {
    'name': 'Track',
    'artists': ['Artist'],
    'album_name': 'Album',
    'cover_url': 'https://example.com/cover.jpg',
    'duration': 200,
}


def _fake_youtube_dl(fetched: list[str]):
    class _YoutubeDL:
        def __init__(self, opts):
            self.opts = opts
            self.params = opts

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def add_post_processor(self, pp, when='post_process'):
            pass

        def download(self, urls):
            fetched.extend(urls)
            _minimal_mp3(Path(self.opts['outtmpl'].replace('%(ext)s', 'mp3')))

    return _YoutubeDL


@pytest.fixture
def no_youtube(monkeypatch):
    fetched: list[str] = []
    monkeypatch.setattr(
        downloader_mod.yt_dlp, 'YoutubeDL', _fake_youtube_dl(fetched)
    )
    monkeypatch.setattr(
        downloader_mod.spotify_mod,
        'enrich_track_from_spotify_if_sparse',
        lambda song: song,
    )
    return fetched


def _slskd_file(tmp_path: Path) -> tuple[Path, Path]:
    slskd_dir = tmp_path / 'slskd'
    source = slskd_dir / 'Artist - Album' / '01 - Track.mp3'
    source.parent.mkdir(parents=True)
    _minimal_mp3(source)
    return slskd_dir, source


class _NoMetadataLookups:
    @staticmethod
    def collect():
        return downloader_mod._LookupResults(None, None, None)

    def cancel(self):
        pass


def test_slskd_leave_in_place_tags_the_file_where_it_is(
    tmp_path, monkeypatch, no_youtube
):
    slskd_dir, source = _slskd_file(tmp_path)
    monkeypatch.setattr(
        downloader_mod, 'download_from_slskd', lambda *a, **k: source
    )
    monkeypatch.setattr(
        downloader_mod, '_fetch_itunes_genre', lambda song: 'Rock'
    )
    reports = []
    d = Downloader(
        tmp_path / 'downloads',
        audio_providers=['slskd', 'youtube-music'],
        slskd_settings={
            'enabled': True,
            'leave_in_place': True,
            'source_dir': str(slskd_dir),
        },
        organize_by_album=True,
    )

    stored = d.download(
        dict(_SONG), lambda pct, msg, provider=None: reports.append(provider)
    )

    assert stored == 'slskd/Artist - Album/01 - Track.mp3'
    assert no_youtube == []
    assert str(ID3(source).getall('TCON')[0]) == 'Rock'
    # Nothing written into slskd's own folders besides the tags.
    assert not (source.parent / 'cover.jpg').exists()
    assert reports[-1] == 'slskd'


def test_slskd_copy_mode_uses_main_destination_and_keeps_format(
    tmp_path, monkeypatch, no_youtube
):
    slskd_dir, source = _slskd_file(tmp_path)
    monkeypatch.setattr(
        downloader_mod, 'download_from_slskd', lambda *a, **k: source
    )
    monkeypatch.setattr(
        downloader_mod, '_download_cover', lambda url: b'IMG-BYTES'
    )
    d = Downloader(
        tmp_path / 'downloads',
        audio_format='m4a',
        audio_providers=['slskd'],
        slskd_settings={
            'enabled': True,
            'leave_in_place': False,
            'source_dir': str(slskd_dir),
        },
        organize_by_album=True,
    )

    stored = d.download(dict(_SONG))

    # main's organize-by-album folder; the slskd file keeps its own format.
    assert stored == 'Album/Artist - Track.mp3'
    target = tmp_path / 'downloads' / 'Album'
    assert (target / 'Artist - Track.mp3').is_file()
    assert (target / 'cover.jpg').read_bytes() == b'IMG-BYTES'
    assert not source.exists()


def test_concurrent_slskd_downloads_share_the_target_lock(
    tmp_path, monkeypatch, no_youtube
):
    slskd_dir, source = _slskd_file(tmp_path)
    requests = []
    requests_lock = Lock()

    def find_source(*_args, **_kwargs):
        with requests_lock:
            requests.append(True)
        return source

    monkeypatch.setattr(downloader_mod, 'download_from_slskd', find_source)
    monkeypatch.setattr(
        downloader_mod, '_download_cover', lambda _url: b'IMG-BYTES'
    )
    downloader = Downloader(
        tmp_path / 'downloads',
        audio_providers=['slskd'],
        slskd_settings={
            'enabled': True,
            'leave_in_place': False,
            'source_dir': str(slskd_dir),
        },
        organize_by_album=True,
        overwrite_existing_files=False,
    )
    ready = Barrier(2)

    def download():
        ready.wait(timeout=5)
        return downloader.download(dict(_SONG))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: download(), range(2)))

    assert results == ['Album/Artist - Track.mp3'] * 2
    assert len(requests) == 1
    assert len(list((tmp_path / 'downloads').rglob('*.mp3'))) == 1


def test_slskd_source_is_kept_when_tagging_fails(
    tmp_path, monkeypatch, no_youtube
):
    slskd_dir, source = _slskd_file(tmp_path)
    monkeypatch.setattr(
        downloader_mod, 'download_from_slskd', lambda *a, **k: source
    )
    monkeypatch.setattr(
        downloader_mod, '_MetadataLookups', lambda *a: _NoMetadataLookups()
    )
    d = Downloader(
        tmp_path / 'downloads',
        audio_providers=['slskd'],
        slskd_settings={
            'enabled': True,
            'leave_in_place': False,
            'source_dir': str(slskd_dir),
        },
    )
    monkeypatch.setattr(d, '_tag_file', lambda *a, **k: False)

    with pytest.raises(RuntimeError, match='source retained'):
        d.download(dict(_SONG))

    assert source.is_file()


def test_slskd_source_is_kept_when_copy_fails(
    tmp_path, monkeypatch, no_youtube
):
    slskd_dir, source = _slskd_file(tmp_path)
    monkeypatch.setattr(
        downloader_mod, 'download_from_slskd', lambda *a, **k: source
    )
    monkeypatch.setattr(
        downloader_mod, '_MetadataLookups', lambda *a: _NoMetadataLookups()
    )
    d = Downloader(
        tmp_path / 'downloads',
        audio_providers=['slskd'],
        slskd_settings={
            'enabled': True,
            'leave_in_place': False,
            'source_dir': str(slskd_dir),
        },
    )

    def fail_copy(*args, **kwargs):
        raise OSError('disk full')

    monkeypatch.setattr(downloader_mod.shutil, 'copy2', fail_copy)

    with pytest.raises(OSError, match='disk full'):
        d.download(dict(_SONG))

    assert source.is_file()


def test_slskd_source_is_kept_when_imported_audio_is_invalid(
    tmp_path, monkeypatch, no_youtube
):
    slskd_dir, source = _slskd_file(tmp_path)
    monkeypatch.setattr(
        downloader_mod, 'download_from_slskd', lambda *a, **k: source
    )
    monkeypatch.setattr(
        downloader_mod, '_MetadataLookups', lambda *a: _NoMetadataLookups()
    )
    monkeypatch.setattr(
        downloader_mod, '_valid_imported_audio', lambda path: False
    )
    d = Downloader(
        tmp_path / 'downloads',
        audio_providers=['slskd'],
        slskd_settings={
            'enabled': True,
            'leave_in_place': False,
            'source_dir': str(slskd_dir),
        },
    )
    monkeypatch.setattr(d, '_tag_file', lambda *a, **k: True)

    with pytest.raises(RuntimeError, match='verification'):
        d.download(dict(_SONG))

    assert source.is_file()


def test_slskd_source_cleanup_failure_is_logged_after_import(
    tmp_path, monkeypatch, no_youtube
):
    slskd_dir, source = _slskd_file(tmp_path)
    monkeypatch.setattr(
        downloader_mod, 'download_from_slskd', lambda *a, **k: source
    )
    monkeypatch.setattr(
        downloader_mod, '_MetadataLookups', lambda *a: _NoMetadataLookups()
    )
    monkeypatch.setattr(
        downloader_mod, '_valid_imported_audio', lambda path: True
    )
    d = Downloader(
        tmp_path / 'downloads',
        audio_providers=['slskd'],
        slskd_settings={
            'enabled': True,
            'leave_in_place': False,
            'source_dir': str(slskd_dir),
        },
    )
    monkeypatch.setattr(d, '_tag_file', lambda *a, **k: True)
    original_unlink = Path.unlink

    def fail_source_unlink(path, *args, **kwargs):
        if path == source.resolve():
            raise PermissionError('cannot remove source')
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'unlink', fail_source_unlink)
    warnings = []
    monkeypatch.setattr(
        downloader_mod.logger,
        'warning',
        lambda *args, **kwargs: warnings.append(args),
    )

    stored = d.download(dict(_SONG))

    assert (tmp_path / 'downloads' / stored).is_file()
    assert source.is_file()
    assert any('source cleanup failed' in args[0] for args in warnings)


def test_slskd_source_outside_configured_root_is_not_removed(
    tmp_path, monkeypatch, no_youtube
):
    slskd_dir, source = _slskd_file(tmp_path)
    configured_root = tmp_path / 'configured-source'
    configured_root.mkdir()
    monkeypatch.setattr(
        downloader_mod, 'download_from_slskd', lambda *a, **k: source
    )
    monkeypatch.setattr(
        downloader_mod, '_MetadataLookups', lambda *a: _NoMetadataLookups()
    )
    monkeypatch.setattr(
        downloader_mod, '_valid_imported_audio', lambda path: True
    )
    d = Downloader(
        tmp_path / 'downloads',
        audio_providers=['slskd'],
        slskd_settings={
            'enabled': True,
            'leave_in_place': False,
            'source_dir': str(configured_root),
        },
    )
    monkeypatch.setattr(d, '_tag_file', lambda *a, **k: True)

    stored = d.download(dict(_SONG))

    assert (tmp_path / 'downloads' / stored).is_file()
    assert source.is_file()


def test_slskd_cleanup_never_removes_the_destination_itself(
    tmp_path, no_youtube
):
    slskd_dir, source = _slskd_file(tmp_path)
    d = Downloader(
        tmp_path / 'downloads',
        audio_providers=['slskd'],
        slskd_settings={
            'enabled': True,
            'leave_in_place': False,
            'source_dir': str(slskd_dir),
        },
    )

    d._remove_slskd_source_after_import(source, source)

    assert source.is_file()


@pytest.mark.parametrize('leave_in_place', [False, True])
def test_the_hook_hears_which_slskd_transfer_a_copy_came_from(
    tmp_path, monkeypatch, no_youtube, leave_in_place
):
    slskd_dir, source = _slskd_file(tmp_path)
    monkeypatch.setattr(
        downloader_mod, 'download_from_slskd', lambda *a, **k: source
    )
    d = Downloader(
        tmp_path / 'downloads',
        audio_providers=['slskd'],
        slskd_settings={
            'enabled': True,
            'leave_in_place': leave_in_place,
            'source_dir': str(slskd_dir),
        },
    )
    heard = []
    d.on_downloaded = lambda song, filename: heard.append(song)

    d.download(dict(_SONG))

    # Copied: the transfer left in slskd's folder is no library song.
    expected = None if leave_in_place else str(source.resolve())
    assert heard[0].get('download_source') == expected
    assert heard[0]['download_provider'] == 'slskd'


def test_disabled_slskd_is_skipped(tmp_path, monkeypatch, no_youtube):
    def _boom(*args, **kwargs):
        raise AssertionError('slskd must not be searched when disabled')

    monkeypatch.setattr(downloader_mod, 'download_from_slskd', _boom)
    monkeypatch.setattr(
        downloader_mod, 'find_match', lambda song: ('vid12345678', {})
    )
    d = Downloader(
        tmp_path,
        audio_providers=['slskd', 'youtube-music'],
        slskd_settings={'enabled': False},
    )

    assert d.download(dict(_SONG)) == 'Artist - Track.mp3'
    assert no_youtube == ['https://music.youtube.com/watch?v=vid12345678']


def test_provider_label_reflects_youtube_fallback(
    tmp_path, monkeypatch, no_youtube
):
    # find_match returns no YouTube Music result when it fell back to
    # standard YouTube.
    monkeypatch.setattr(
        downloader_mod, 'find_match', lambda song: ('vid12345678', None)
    )
    reports = []
    d = Downloader(tmp_path)

    d.download(
        dict(_SONG),
        lambda pct, msg, provider=None: reports.append((msg, provider)),
    )

    assert reports[-1] == ('Done', 'youtube')


def test_youtube_only_provider(tmp_path, monkeypatch, no_youtube):
    def _boom(song):
        raise AssertionError('YouTube Music must not be searched')

    monkeypatch.setattr(downloader_mod, 'find_match', _boom)
    monkeypatch.setattr(
        downloader_mod, 'find_match_youtube_only', lambda song: 'vid12345678'
    )
    d = Downloader(tmp_path, audio_providers=['youtube'])

    assert d.download(dict(_SONG)) == 'Artist - Track.mp3'


def test_soundcloud_provider_is_tried_in_configured_order(
    tmp_path, monkeypatch, no_youtube
):
    calls = []
    monkeypatch.setattr(
        downloader_mod,
        'find_match_soundcloud',
        lambda song: calls.append(song) or 'https://soundcloud.com/a/track',
    )
    d = Downloader(tmp_path, audio_providers=['soundcloud'])

    assert d.download(dict(_SONG)) == 'Artist - Track.mp3'
    assert calls == [_SONG]
    assert no_youtube == ['https://soundcloud.com/a/track']


_SOUNDCLOUD_SONG = {
    **_SONG,
    'song_id': 'soundcloud:track1',
    'url': 'https://soundcloud.com/artist/track',
    'soundcloud_url': 'https://soundcloud.com/artist/track',
    'source': 'soundcloud',
}


def _reject_soundcloud_search(song):
    raise AssertionError('A known SoundCloud track must not be searched')


def test_known_soundcloud_track_is_downloaded_without_a_search(
    tmp_path, monkeypatch, no_youtube
):
    monkeypatch.setattr(
        downloader_mod, 'find_match_soundcloud', _reject_soundcloud_search
    )
    reports = []
    d = Downloader(tmp_path, audio_providers=['soundcloud'])

    d.download(
        dict(_SOUNDCLOUD_SONG),
        lambda pct, msg, provider=None: reports.append(provider),
    )

    assert no_youtube == ['https://soundcloud.com/artist/track']
    assert reports[-1] == 'soundcloud'


def test_known_soundcloud_track_respects_earlier_local_source(
    tmp_path, monkeypatch, no_youtube
):
    slskd_dir, source = _slskd_file(tmp_path)
    monkeypatch.setattr(
        downloader_mod, 'download_from_slskd', lambda *a, **k: source
    )
    monkeypatch.setattr(
        downloader_mod, 'find_match_soundcloud', _reject_soundcloud_search
    )
    d = Downloader(
        tmp_path / 'downloads',
        audio_providers=['slskd', 'soundcloud'],
        slskd_settings={
            'enabled': True,
            'source_dir': str(slskd_dir),
            'leave_in_place': True,
        },
    )

    assert d.download(dict(_SOUNDCLOUD_SONG)) == (
        'slskd/Artist - Album/01 - Track.mp3'
    )
    assert no_youtube == []


def test_known_soundcloud_track_does_not_enable_soundcloud(
    tmp_path, monkeypatch, no_youtube
):
    monkeypatch.setattr(
        downloader_mod, 'find_match', lambda song: (None, None)
    )
    d = Downloader(tmp_path, audio_providers=['youtube-music'])

    with pytest.raises(NoAudioMatchError, match='turn SoundCloud on'):
        d.download(dict(_SOUNDCLOUD_SONG))
    assert no_youtube == []


def test_soundcloud_downloads_skip_go_plus_previews(tmp_path, monkeypatch):
    opts = []

    class _YoutubeDL:
        def __init__(self, params):
            self.params = params
            opts.append(params)

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def add_post_processor(self, pp, when='post_process'):
            pass

        @staticmethod
        def download(urls):
            raise downloader_mod.yt_dlp.utils.DownloadError(
                'ERROR: [soundcloud] 123: Requested format is not available'
            )

    monkeypatch.setattr(downloader_mod.yt_dlp, 'YoutubeDL', _YoutubeDL)
    d = Downloader(tmp_path)

    with pytest.raises(RuntimeError, match='30-second preview'):
        d.fetch_audio(
            'https://soundcloud.com/artist/track',
            tmp_path,
            'Track',
            song=_SONG,
            provider='soundcloud',
        )
    assert 'preview' in opts[0]['format']


def test_fetch_audio_only_takes_soundcloud_urls(tmp_path, no_youtube):
    d = Downloader(tmp_path)

    d.fetch_audio('https://example.com/track', tmp_path, 'a', song=_SONG)
    d.fetch_audio('dQw4w9WgXcQ', tmp_path, 'b', song=_SONG)

    # Anything but a SoundCloud track is a YouTube id, never a URL to
    # hand to yt-dlp's generic extractor.
    assert no_youtube == [
        'https://music.youtube.com/watch?v=https://example.com/track',
        'https://music.youtube.com/watch?v=dQw4w9WgXcQ',
    ]


def test_youtube_is_not_searched_again_after_youtube_music(
    tmp_path, monkeypatch, no_youtube
):
    calls = []

    def _youtube_only(song):
        calls.append(song)

    monkeypatch.setattr(
        downloader_mod, 'find_match', lambda song: (None, None)
    )
    monkeypatch.setattr(
        downloader_mod, 'find_match_youtube_only', _youtube_only
    )
    d = Downloader(tmp_path, audio_providers=['youtube-music', 'youtube'])

    with pytest.raises(NoAudioMatchError, match='a YouTube match'):
        d.download(dict(_SONG))
    # find_match already includes the standard-YouTube fallback.
    assert calls == []


def test_no_audio_match_mentions_audio_when_slskd_enabled(
    tmp_path, monkeypatch, no_youtube
):
    monkeypatch.setattr(
        downloader_mod, 'download_from_slskd', lambda *a, **k: None
    )
    monkeypatch.setattr(
        downloader_mod, 'find_match', lambda song: (None, None)
    )
    d = Downloader(
        tmp_path,
        audio_providers=['slskd', 'youtube-music'],
        slskd_settings={'enabled': True},
    )

    with pytest.raises(RuntimeError, match='an audio match'):
        d.download(dict(_SONG))


def test_audio_providers_are_normalized():
    assert Downloader._normalize_audio_providers(None) == ['youtube-music']
    assert Downloader._normalize_audio_providers([
        'slskd',
        'bogus',
        'slskd',
        'youtube',
        'soundcloud',
    ]) == ['slskd', 'youtube', 'soundcloud']


@pytest.fixture(params=['youtube_id', 'youtube_song_id'])
def known_video_song(request):
    if request.param == 'youtube_id':
        return {**_SONG, 'youtube_id': 'known123456'}
    return {**_SONG, 'source': 'youtube', 'song_id': 'known123456'}


def _reject_youtube_search(*args, **kwargs):
    raise AssertionError('Known video must not cause a YouTube search')


@pytest.mark.parametrize('providers', [['slskd'], ['slskd', 'youtube-music']])
def test_known_video_respects_earlier_local_source(
    tmp_path, monkeypatch, no_youtube, known_video_song, providers
):
    slskd_dir, source = _slskd_file(tmp_path)
    monkeypatch.setattr(
        downloader_mod, 'download_from_slskd', lambda *a, **k: source
    )
    for name in (
        'find_match',
        'find_match_youtube_only',
        'find_match_for_video',
    ):
        monkeypatch.setattr(downloader_mod, name, _reject_youtube_search)
    d = Downloader(
        tmp_path / 'downloads',
        audio_providers=providers,
        slskd_settings={
            'enabled': True,
            'source_dir': str(slskd_dir),
            'leave_in_place': True,
        },
    )

    assert d.download(known_video_song) == (
        'slskd/Artist - Album/01 - Track.mp3'
    )
    assert no_youtube == []


def test_search_result_uses_metadata_through_provider_order(
    tmp_path, monkeypatch, no_youtube
):
    seen_by_slskd = []
    seen_by_match = []

    def local_miss(song, *args, **kwargs):
        seen_by_slskd.append(song.copy())

    def metadata_match(song):
        seen_by_match.append(song.copy())
        return 'matched12345', {}

    monkeypatch.setattr(downloader_mod, 'download_from_slskd', local_miss)
    monkeypatch.setattr(downloader_mod, 'find_match', metadata_match)
    d = Downloader(
        tmp_path,
        audio_providers=['slskd', 'youtube-music'],
        slskd_settings={'enabled': True},
    )
    song = {
        **_SONG,
        'song_id': 'selected12345',
        'source': 'youtube',
        '_match_by_metadata': True,
    }

    d.download(song)

    assert seen_by_slskd[0]['name'] == 'Track'
    assert seen_by_slskd[0]['artists'] == ['Artist']
    assert seen_by_slskd[0]['duration'] == 200
    assert seen_by_match[0]['name'] == 'Track'
    assert no_youtube == ['https://music.youtube.com/watch?v=matched12345']


@pytest.mark.parametrize('local_enabled', [False, True])
def test_known_video_does_not_enable_disabled_youtube(
    tmp_path, monkeypatch, no_youtube, known_video_song, local_enabled
):
    monkeypatch.setattr(
        downloader_mod, 'download_from_slskd', lambda *a, **k: None
    )
    for name in (
        'find_match',
        'find_match_youtube_only',
        'find_match_for_video',
    ):
        monkeypatch.setattr(downloader_mod, name, _reject_youtube_search)
    d = Downloader(
        tmp_path,
        audio_providers=['slskd'],
        slskd_settings={'enabled': local_enabled},
    )

    with pytest.raises(NoAudioMatchError, match='an audio match'):
        d.download(known_video_song)
    assert no_youtube == []


@pytest.mark.parametrize('provider', ['youtube-music', 'youtube'])
def test_known_video_fallback_keeps_exact_video_and_enrichment(
    tmp_path, monkeypatch, no_youtube, known_video_song, provider
):
    calls = []

    def local_miss(*args, **kwargs):
        calls.append('slskd')

    def enrich(song, video_id):
        calls.append(video_id)

    monkeypatch.setattr(downloader_mod, 'download_from_slskd', local_miss)
    monkeypatch.setattr(downloader_mod, 'find_match', _reject_youtube_search)
    monkeypatch.setattr(
        downloader_mod, 'find_match_youtube_only', _reject_youtube_search
    )
    monkeypatch.setattr(downloader_mod, 'find_match_for_video', enrich)
    song = {**known_video_song, 'album_name': '', 'cover_url': ''}
    reports = []
    d = Downloader(
        tmp_path,
        audio_providers=['slskd', provider],
        slskd_settings={'enabled': True},
    )

    assert (
        d.download(
            song, lambda pct, message, source=None: reports.append(source)
        )
        == 'Artist - Track.mp3'
    )
    assert calls == ['slskd', 'known123456']
    assert no_youtube == ['https://music.youtube.com/watch?v=known123456']
    assert reports[-1] == provider


@pytest.mark.parametrize('provider', ['youtube-music', 'youtube'])
def test_known_video_youtube_first_does_not_try_later_local_source(
    tmp_path, monkeypatch, no_youtube, known_video_song, provider
):
    monkeypatch.setattr(
        downloader_mod, 'download_from_slskd', _reject_youtube_search
    )
    monkeypatch.setattr(downloader_mod, 'find_match', _reject_youtube_search)
    monkeypatch.setattr(
        downloader_mod, 'find_match_youtube_only', _reject_youtube_search
    )
    d = Downloader(
        tmp_path,
        audio_providers=[provider, 'slskd'],
        slskd_settings={'enabled': True},
    )

    assert d.download(known_video_song) == 'Artist - Track.mp3'
    assert no_youtube == ['https://music.youtube.com/watch?v=known123456']


def test_known_video_respects_deemix_first(
    tmp_path, monkeypatch, no_youtube, known_video_song
):
    source_dir, source = _slskd_file(tmp_path)
    monkeypatch.setattr(
        downloader_mod, 'download_from_deemix', lambda *a, **k: source
    )
    for name in (
        'find_match',
        'find_match_youtube_only',
        'find_match_for_video',
    ):
        monkeypatch.setattr(downloader_mod, name, _reject_youtube_search)
    reports = []
    d = Downloader(
        tmp_path / 'downloads',
        audio_providers=['deemix', 'youtube-music'],
        deemix_settings={'enabled': True, 'source_dir': str(source_dir)},
    )

    assert d.download(
        known_video_song,
        lambda pct, message, provider=None: reports.append(provider),
    )
    assert no_youtube == []
    assert reports[-1] == 'deemix'
    assert source.is_file()


def test_known_video_deemix_miss_never_enables_youtube(
    tmp_path, monkeypatch, no_youtube, known_video_song
):
    monkeypatch.setattr(
        downloader_mod, 'download_from_deemix', lambda *a, **k: None
    )
    for name in (
        'find_match',
        'find_match_youtube_only',
        'find_match_for_video',
    ):
        monkeypatch.setattr(downloader_mod, name, _reject_youtube_search)
    d = Downloader(
        tmp_path,
        audio_providers=['deemix'],
        deemix_settings={'enabled': True},
    )

    with pytest.raises(NoAudioMatchError, match='an audio match'):
        d.download(known_video_song)
    assert no_youtube == []
