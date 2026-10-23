from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from mutagen.id3 import ID3, USLT

from downtify import api, lyrics
from downtify import deemix_provider as dp
from downtify.auth import ADMIN, classify
from downtify.downloader import Downloader
from downtify.library_catalog import LibraryContext


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.delenv('DOWNTIFY_DEEMIX_ARL_FILE', raising=False)
    return dp.normalize_settings({
        'enabled': True,
        'base_url': 'http://deemix:6595',
        'source_dir': str(tmp_path),
    })


def test_settings_never_persist_credentials():
    cfg = dp.normalize_settings({
        'arl': 'fixture-only',
        'password': 'fixture-only',
    })
    assert 'arl' not in cfg
    assert 'password' not in cfg
    assert cfg['enabled'] is False


@pytest.mark.parametrize(
    'url',
    [
        'ftp://server',
        'http://user:password@server',
        'http://server?arl=fixture-only',
        'http://server#fragment',
        '',
    ],
)
def test_no_embedded_credentials_or_non_http_urls(cfg, url):
    cfg['base_url'] = url
    with pytest.raises(dp.DeemixError, match='connection_bad_url'):
        dp.validate_settings(cfg)


@pytest.mark.parametrize(
    ('value', 'expected'), [('9', '9'), ('bogus', '3'), (1, '1')]
)
def test_quality_settings(value, expected):
    assert dp.normalize_settings({'bitrate': value})['bitrate'] == expected


def session(cfg, monkeypatch, handler):
    original = httpx.Client
    monkeypatch.setattr(
        dp.httpx,
        'Client',
        lambda **kw: original(**kw, transport=httpx.MockTransport(handler)),
    )
    return dp.DeemixClient(cfg)


def test_private_login_reuses_session_without_exposing_credentials(
    cfg, monkeypatch
):
    filename = Path(cfg['source_dir']) / 'private-credential'
    filename.write_text('fixture-only', encoding='utf-8')
    monkeypatch.setenv('DOWNTIFY_DEEMIX_ARL_FILE', str(filename))
    logged_in = False
    calls = []

    def handle(req):
        nonlocal logged_in
        calls.append(req.url.path)
        if req.url.path == '/api/loginArl':
            assert 'sid=fixture' in req.headers['cookie']
            assert b'fixture-only' in req.content
            logged_in = True
            return httpx.Response(200, json={'result': True})
        return httpx.Response(
            200,
            headers={'set-cookie': 'sid=fixture; Path=/'},
            json={
                'autologin': not logged_in,
                'singleUser': {},
                'currentUser': {'can_stream_hq': True},
            },
        )

    client = session(cfg, monkeypatch, handle)
    try:
        assert not client.connect()['autologin']
        assert calls == ['/api/connect', '/api/loginArl', '/api/connect']
    finally:
        client.close()


def test_no_shared_login_reports_auth_without_queue_changes(cfg, monkeypatch):
    calls = []

    def handle(req):
        calls.append(req.url.path)
        return httpx.Response(200, json={'autologin': True, 'singleUser': {}})

    client = session(cfg, monkeypatch, handle)
    try:
        with pytest.raises(dp.DeemixError, match='auth_bad_credentials'):
            client.connect()
        assert calls == ['/api/connect']
    finally:
        client.close()


def test_does_not_silently_downgrade_quality(cfg, monkeypatch):
    client = session(
        cfg,
        monkeypatch,
        lambda req: httpx.Response(
            200,
            json={
                'autologin': False,
                'currentUser': {'can_stream_hq': False},
            },
        ),
    )
    try:
        with pytest.raises(dp.DeemixError, match='quality_unavailable'):
            client.connect()
    finally:
        client.close()


def test_transport_error_never_exposes_request_or_body(cfg, monkeypatch):
    def handle(req):
        raise httpx.ConnectError('fixture-secret-url', request=req)

    client = session(cfg, monkeypatch, handle)
    try:
        with pytest.raises(dp.DeemixError) as exc:
            client.connect()
        assert str(exc.value) == 'connection_unreachable'
    finally:
        client.close()


def test_confined_shared_mapping(cfg):
    root = Path(cfg['source_dir'])
    (root / 'Artist').mkdir()
    path = root / 'Artist/Song.flac'
    path.write_bytes(b'fixture')
    client = dp.DeemixClient(cfg)
    try:
        assert client.local_file('/downloads/Artist/Song.flac') == path
        assert client.local_file('/other/Artist/Song.flac') is None
        assert client.local_file('/downloads/../Song.flac') is None
        assert client.local_file('/downloads/Artist/Song.part') is None
    finally:
        client.close()


def test_symlink_escape_is_not_imported(cfg, tmp_path):
    outside = tmp_path.parent / (tmp_path.name + '.mp3')
    outside.write_bytes(b'fixture')
    (tmp_path / 'escape.mp3').symlink_to(outside)
    client = dp.DeemixClient(cfg)
    try:
        assert client.local_file('/downloads/escape.mp3') is None
    finally:
        client.close()
        outside.unlink()


@pytest.fixture
def catalog():
    return {
        'id': 123,
        'title': 'Song',
        'artist': {'name': 'Artist'},
        'album': {'title': 'Album'},
        'duration': 173,
        'explicit_lyrics': False,
    }


def test_conservative_recording_match(catalog):
    song = {
        'name': 'Song',
        'artists': ['Artist'],
        'album_name': 'Album',
        'duration': 173,
    }
    assert dp.candidate_matches(song, catalog)
    assert not dp.candidate_matches({**song, 'name': 'Song (Live)'}, catalog)
    assert not dp.candidate_matches(
        {**song, 'artists': ['Cover artist']}, catalog
    )
    assert not dp.candidate_matches({**song, 'album_name': 'Single'}, catalog)
    assert not dp.candidate_matches({**song, 'duration': 190}, catalog)
    assert not dp.candidate_matches({**song, 'explicit': True}, catalog)


def test_recording_verification_checks_audio_not_just_completed_status(
    cfg, catalog, monkeypatch
):
    path = Path(cfg['source_dir']) / 'Song.mp3'
    path.write_bytes(b'fixture')
    monkeypatch.setattr(
        dp.mutagen,
        'File',
        lambda p, **kw: SimpleNamespace(
            tags={'title': ['Song'], 'artist': ['Artist'], 'album': ['Album']},
            info=SimpleNamespace(length=173, bitrate=320000),
            mime=['audio/mpeg'],
        ),
    )
    assert dp.verified_audio(path, catalog, '3')
    assert not dp.verified_audio(path, catalog, '9')
    monkeypatch.setattr(dp.mutagen, 'File', lambda p, **kw: None)
    assert not dp.verified_audio(path, catalog, '3')


@pytest.mark.parametrize(
    ('album', 'expected'), [('Single', False), ('', False), ('Album', True)]
)
def test_downloaded_album_must_match_the_requested_release(
    cfg, catalog, monkeypatch, album, expected
):
    path = Path(cfg['source_dir']) / 'Song.mp3'
    path.write_bytes(b'fixture')
    monkeypatch.setattr(
        dp.mutagen,
        'File',
        lambda *a, **kw: SimpleNamespace(
            tags={'title': ['Song'], 'artist': ['Artist'], 'album': [album]},
            info=SimpleNamespace(length=173, bitrate=320000),
            mime=['audio/mpeg'],
        ),
    )
    assert dp.verified_audio(path, catalog, '3') is expected


@pytest.mark.parametrize(
    'case',
    [
        ('audio/mpeg', '9', False),
        ('audio/flac', '9', True),
        ('audio/flac', '3', True),
    ],
)
def test_decoded_codec_controls_lossless_quality_not_filename(
    cfg, catalog, monkeypatch, case
):
    mime, bitrate, expected = case
    path = Path(cfg['source_dir']) / 'Renamed.flac'
    path.write_bytes(b'fixture')
    monkeypatch.setattr(
        dp.mutagen,
        'File',
        lambda *a, **kw: SimpleNamespace(
            tags={'title': ['Song'], 'artist': ['Artist'], 'album': ['Album']},
            info=SimpleNamespace(length=173, bitrate=90000),
            mime=[mime],
        ),
    )
    assert dp.verified_audio(path, catalog, bitrate) is expected


def test_deemix_finalize_preserves_native_tags_and_lrc(
    cfg, tmp_path, monkeypatch
):
    path = tmp_path / 'Song.mp3'
    tags = ID3()
    tags.add(USLT(encoding=3, lang='eng', desc='', text='Native plain lyrics'))
    tags.save(path)
    sidecar = path.with_suffix('.lrc')
    sidecar.write_text('[00:01.00]Native synced lyrics', encoding='utf-8')
    before = path.read_bytes(), sidecar.read_bytes()
    downloader = Downloader(tmp_path / 'owned', deemix_settings=cfg)

    def forbidden(*args, **kwargs):
        pytest.fail('Native Deemix metadata must not be rewritten')

    monkeypatch.setattr(downloader, '_tag_file', forbidden)
    stored = downloader._finalize_local_source({}, path, 'deemix', None, None)
    assert stored.startswith('ext/')
    assert (path.read_bytes(), sidecar.read_bytes()) == before
    result = lyrics.read_track_lyrics(path)
    assert result['synced'] == '[00:01.00]Native synced lyrics'
    assert result['plain'] == 'Native plain lyrics'


def test_non_latin_catalog_recordings_remain_distinct(catalog):
    song = {'name': '晴天', 'artists': ['周杰伦'], 'album_name': '葉惠美'}
    row = {
        **catalog,
        'title': '晴天',
        'artist': {'name': '周杰伦'},
        'album': {'title': '葉惠美'},
    }
    assert dp.candidate_matches(song, row)
    assert not dp.candidate_matches(song, {**row, 'title': '夜曲'})


def test_non_latin_file_tags_cannot_match_a_different_title(
    cfg, catalog, monkeypatch
):
    path = Path(cfg['source_dir']) / 'Song.mp3'
    path.write_bytes(b'fixture')
    row = {
        **catalog,
        'title': '晴天',
        'artist': {'name': '周杰伦'},
        'album': {'title': '葉惠美'},
    }
    monkeypatch.setattr(
        dp.mutagen,
        'File',
        lambda *a, **kw: SimpleNamespace(
            tags={
                'title': ['夜曲'],
                'artist': ['周杰伦'],
                'album': ['葉惠美'],
            },
            info=SimpleNamespace(length=173, bitrate=320000),
            mime=['audio/mpeg'],
        ),
    )
    assert not dp.verified_audio(path, row, '3')


@pytest.mark.parametrize(
    ('codec', 'lossless'), [('libmp3lame', False), ('flac', True)]
)
def test_real_audio_codec_is_verified_even_with_a_flac_filename(
    tmp_path, catalog, codec, lossless
):
    path = tmp_path / ('audio.mp3' if codec == 'libmp3lame' else 'audio.flac')
    subprocess.run(
        [
            'ffmpeg',
            '-v',
            'error',
            '-f',
            'lavfi',
            '-i',
            'anullsrc=r=44100:cl=stereo',
            '-t',
            '2',
            '-c:a',
            codec,
            '-metadata',
            'title=Song',
            '-metadata',
            'artist=Artist',
            '-metadata',
            'album=Album',
            str(path),
        ],
        check=True,
    )
    renamed = path.with_name('renamed.flac')
    path.rename(renamed)
    assert (
        dp.verified_audio(renamed, {**catalog, 'duration': 2}, '9') is lossless
    )
    if lossless:
        assert dp.verified_audio(renamed, {**catalog, 'duration': 2}, '3')


def test_deemix_is_opt_in_and_does_not_change_default_provider(tmp_path):
    assert Downloader(tmp_path).audio_providers == ['youtube-music']
    assert not Downloader(tmp_path).deemix_settings['enabled']


@pytest.mark.parametrize('status', ['completed', 'withErrors', 'failed'])
def test_only_own_job_is_observed_and_manual_jobs_are_untouched(
    cfg, catalog, monkeypatch, status
):
    path = Path(cfg['source_dir']) / 'Song.mp3'
    path.write_bytes(b'fixture')
    calls = []

    class Client:
        def __init__(self, config):
            self.cfg = config

        def connect(self):
            return dict(self.cfg)

        def close(self):
            self.closed = True
            calls.append('close')

        def local_file(self, remote):
            return (
                Path(self.cfg['source_dir']) / 'Song.mp3'
                if remote == '/downloads/Song.mp3'
                else None
            )

        def request(self, method, route, **kwargs):
            assert self.cfg['enabled']
            calls.append(route)
            if route == 'addToQueue':
                return {'result': True, 'data': {'obj': None}}
            return {
                'queue': {
                    'track_123_3': {
                        'id': 123,
                        'status': status,
                        'files': [{'path': '/downloads/Song.mp3'}],
                    },
                    'manual_job': {'id': 999, 'status': 'downloading'},
                }
            }

    monkeypatch.setattr(dp, 'DeemixClient', Client)
    monkeypatch.setattr(dp, '_catalog_track', lambda *args: catalog)
    monkeypatch.setattr(dp, 'verified_audio', lambda *args: True)
    result = dp.download_from_deemix({}, cfg)
    assert result == (None if status == 'failed' else path)
    assert calls == ['addToQueue', 'getQueue', 'close']
    assert path.read_bytes() == b'fixture'


def test_connection_probe_is_admin_only():

    assert classify('POST', '/api/deemix/test') == ADMIN


def test_deemix_native_lrc_wins_over_a_stale_dedicated_sidecar(
    cfg, monkeypatch, tmp_path
):

    path = tmp_path / 'Song.mp3'
    ID3().save(path)
    path.with_suffix('.lrc').write_text(
        '[00:01.00]Native recording', encoding='utf-8'
    )
    settings = {
        'deemix': cfg,
        'lyrics_lrc_beside': False,
        'lyrics_lrc_dir': str(tmp_path / 'dedicated'),
    }
    ctx = LibraryContext(tmp_path / 'owned', extra_dirs=(tmp_path,))
    stale = lyrics.lrc_sidecar_path(
        path,
        settings=settings,
        download_dir=ctx.download_dir,
        extra_dirs=ctx.extra_dirs,
    )
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text('[00:10.00]Old video', encoding='utf-8')
    monkeypatch.setattr(api.state, 'settings', settings)
    monkeypatch.setattr(api, 'library_context', lambda: ctx)
    previous = lyrics._lrc_resolve, lyrics._lrc_tree_root, lyrics._lrc_search
    try:
        api.bind_lrc_resolver()
        assert (
            lyrics.read_track_lyrics(path)['synced']
            == '[00:01.00]Native recording'
        )
        assert stale.read_text(encoding='utf-8') == '[00:10.00]Old video'
    finally:
        lyrics.set_lrc_resolver(
            previous[0], tree_root=previous[1], search=previous[2]
        )
