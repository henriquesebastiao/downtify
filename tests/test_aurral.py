"""Hand-over downloads for Aurral (downtify/aurral.py, aurral_routes.py)."""

from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from downtify import api, aurral, aurral_routes
from downtify.auth import ADMIN, CLIENT, Principal, classify

SONG = {
    'song_id': 'vid123',
    'name': 'Song',
    'artists': ['Band', 'Guest'],
    'album_name': 'Album',
    'duration': 215,
    'url': 'https://music.youtube.com/watch?v=vid123',
    'source': 'youtube',
}


class FakeDownloader:
    """Writes one small file per download, like the real one would."""

    def __init__(self, library: Path):
        self.download_dir = library
        self.organize_by_artist = True
        self.organize_by_album = True
        self.overwrite_existing_files = False
        self.on_downloaded = lambda song, name: pytest.fail('library hook ran')
        self.on_outcome = lambda *args: pytest.fail('download log ran')
        self.download_sources = object()
        self.hand_replaced = object()
        self.download_policy = object()
        self.slskd_settings = {'leave_in_place': True, 'source_dir': ''}
        self.deemix_settings = {}
        self._target_locks = {}
        self._target_locks_guard = threading.Lock()
        self.calls = []

    @staticmethod
    def existing_filename_for(song, subdir=None):
        return None

    @staticmethod
    def _remove_slskd_source_after_import(source, final):
        raise AssertionError('slskd source removed')

    def download(self, song, progress=None, subdir=None):
        self.calls.append(song)
        if song.get('name') == 'Broken':
            raise RuntimeError('No match')
        name = f'{song["name"]}.mp3'
        (Path(self.download_dir) / name).write_bytes(b'ID3 audio')
        return name


class Principals:
    """Sets the signed-in user the way AuthMiddleware does."""

    def __init__(self, app, who):
        self.app = app
        self.who = who

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            scope.setdefault('state', {})['principal'] = self.who['now']
        await self.app(scope, receive, send)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    library = tmp_path / 'music'
    library.mkdir()
    settings_path = tmp_path / 'data' / 'settings.json'
    settings_path.parent.mkdir()
    downloader = FakeDownloader(library)
    monkeypatch.setattr(api.state, 'settings_path', settings_path)
    monkeypatch.setattr(api.state, 'downloader', downloader)
    monkeypatch.setattr(api.state, 'track_index', None)
    monkeypatch.setattr(api.state, 'download_semaphore', asyncio.Semaphore(2))
    monkeypatch.setattr(
        api.state,
        'settings',
        {**api.DEFAULT_SETTINGS, 'aurral_enabled': True},
    )
    monkeypatch.setattr(api, 'DOWNLOAD_EXECUTOR', ThreadPoolExecutor(2))

    async def no_log(*args, **kwargs):
        return None

    monkeypatch.setattr(api, 'log_activity', no_log)
    monkeypatch.setattr(
        aurral_routes.providers, 'search_songs', lambda q, limit=20: [SONG]
    )
    aurral_routes.reset(tmp_path / 'data' / aurral.FOLDER_NAME)
    who = {'now': Principal(kind='device', scope=CLIENT, user_id=7)}
    app = FastAPI()
    app.include_router(aurral_routes.router)
    app.add_middleware(Principals, who=who)
    # One event loop for the whole test, so a job outlives its request.
    with TestClient(app) as client:
        client.who = who
        client.downloader = downloader
        client.library = library
        yield client
    aurral_routes.reset(tmp_path / 'data' / aurral.FOLDER_NAME)


def _wait(client, job_id, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        body = client.get(f'/api/aurral/jobs/{job_id}').json()
        if body['status'] in {aurral.DONE, aurral.FAILED}:
            return body
        time.sleep(0.05)
    raise AssertionError('job never finished')


# ── Off by default ──────────────────────────────────────────────────


def test_hand_over_is_off_by_default():
    assert api.DEFAULT_SETTINGS['aurral_enabled'] is False


def test_turned_off_it_answers_409_and_says_where_to_turn_it_on(setup):
    api.state.settings['aurral_enabled'] = False

    assert setup.get('/api/aurral').json()['enabled'] is False
    for response in (
        setup.get('/api/aurral/search/tracks', params={'title': 'Song'}),
        setup.get('/api/aurral/search/albums', params={'title': 'Album'}),
        setup.post('/api/aurral/jobs', json={'song': SONG}),
    ):
        assert response.status_code == 409
        assert 'Settings > Apps > Aurral' in response.json()['detail']
    assert setup.downloader.calls == []


def test_routes_need_a_signed_in_app_and_the_key_an_admin():
    assert classify('GET', '/api/aurral') == CLIENT
    assert classify('GET', '/api/aurral/search/tracks') == CLIENT
    assert classify('POST', '/api/aurral/jobs') == CLIENT
    assert classify('GET', '/api/aurral/jobs/abc') == CLIENT
    assert classify('GET', '/api/aurral/jobs/abc/files/0') == CLIENT
    assert classify('DELETE', '/api/aurral/jobs/abc') == CLIENT
    assert classify('POST', '/api/aurral/key') == ADMIN
    # Nothing else under /api/aurral is open to an app.
    assert classify('PUT', '/api/aurral/jobs/abc') == ADMIN


# ── Search ──────────────────────────────────────────────────────────


def test_search_results_are_shaped_for_aurral(setup):
    [result] = setup.get(
        '/api/aurral/search/tracks', params={'artist': 'Band', 'title': 'Song'}
    ).json()

    assert result['id'] == 'vid123'
    assert (result['title'], result['artist'], result['album']) == (
        'Song',
        'Band, Guest',
        'Album',
    )
    assert result['durationMs'] == 215000
    # YouTube Music only, MP3 320 in the settings: known before download.
    assert (result['format'], result['bitrate']) == ('mp3', 320)
    assert result['data']['song']['download_by_metadata'] is True


def test_quality_is_unknown_when_a_source_keeps_its_own_format():
    settings = {
        **api.DEFAULT_SETTINGS,
        'audio_providers': ['slskd', 'youtube-music'],
        'slskd': {**api.DEFAULT_SETTINGS['slskd'], 'enabled': True},
    }
    assert aurral.audio_quality(settings) == (None, None)
    flac = {**api.DEFAULT_SETTINGS, 'format': 'flac'}
    assert aurral.audio_quality(flac) == ('flac', None)


def test_album_results_need_a_link():
    assert (
        aurral.album_result({'album_id': 'x', 'name': 'A', 'artist': 'B'})
        is None
    )
    found = aurral.album_result({
        'album_id': 'MPRE1',
        'name': 'Album',
        'artists': ['Band'],
        'year': '2019',
        'url': 'https://music.youtube.com/browse/MPRE1',
    })
    assert found == {
        'id': 'MPRE1',
        'title': 'Album',
        'artist': 'Band',
        'year': 2019,
        'data': {'url': 'https://music.youtube.com/browse/MPRE1'},
    }


# ── Jobs ────────────────────────────────────────────────────────────


def test_a_download_lands_in_its_own_folder_not_the_library(setup):
    [result] = setup.get(
        '/api/aurral/search/tracks', params={'artist': 'Band', 'title': 'Song'}
    ).json()
    job = setup.post(
        '/api/aurral/jobs', json={'song': result['data']['song']}
    ).json()
    done = _wait(setup, job['id'])

    assert done['status'] == aurral.DONE
    [entry] = done['files']
    assert entry['name'] == 'Song.mp3'
    assert entry['size'] == len(b'ID3 audio')
    assert list(setup.library.iterdir()) == []
    response = setup.get(f'/api/aurral/jobs/{job["id"]}/files/0')
    assert response.status_code == 200
    assert response.content == b'ID3 audio'
    # Searched again by its metadata, like Downtify's own search rows.
    [asked] = setup.downloader.calls
    assert asked['_match_by_metadata'] is True
    assert 'download_by_metadata' not in asked


def test_dropping_a_job_deletes_its_folder(setup):
    job = setup.post('/api/aurral/jobs', json={'song': SONG}).json()
    _wait(setup, job['id'])
    folder = aurral_routes.jobs().root / job['id']
    assert folder.is_dir()

    assert setup.delete(f'/api/aurral/jobs/{job["id"]}').json()['dropped']
    assert not folder.exists()
    assert setup.get(f'/api/aurral/jobs/{job["id"]}').status_code == 404


def test_a_song_already_in_the_library_is_handed_over_untouched(
    setup, monkeypatch
):
    owned = setup.library / 'Band' / 'Song.mp3'
    owned.parent.mkdir()
    owned.write_bytes(b'library copy')
    monkeypatch.setattr(
        aurral, 'library_file', lambda downloader, song, index: owned
    )
    job = setup.post('/api/aurral/jobs', json={'song': SONG}).json()
    done = _wait(setup, job['id'])

    assert setup.downloader.calls == []
    assert (
        setup.get(f'/api/aurral/jobs/{job["id"]}/files/0').content
        == b'library copy'
    )
    setup.delete(f'/api/aurral/jobs/{job["id"]}')
    assert owned.read_bytes() == b'library copy'
    assert done['files'][0]['name'] == 'Song.mp3'


def test_a_failed_download_says_why(setup):
    job = setup.post(
        '/api/aurral/jobs', json={'song': {**SONG, 'name': 'Broken'}}
    ).json()
    done = _wait(setup, job['id'])

    assert done['status'] == aurral.FAILED
    assert done['message'] == 'No match'
    assert (
        setup.get(f'/api/aurral/jobs/{job["id"]}/files/0').status_code == 409
    )


def test_an_album_keeps_the_tracks_it_got(setup, monkeypatch):
    tracks = [
        {**SONG, 'song_id': 'a', 'name': 'One'},
        {**SONG, 'song_id': 'b', 'name': 'Broken'},
        {**SONG, 'song_id': 'c', 'name': 'Three'},
    ]
    monkeypatch.setattr(
        aurral_routes.providers,
        'album_tracks_from_browse_id',
        lambda browse_id: tracks,
    )
    job = setup.post(
        '/api/aurral/jobs',
        json={'album_url': 'https://music.youtube.com/browse/MPREb_abc'},
    ).json()
    done = _wait(setup, job['id'])

    assert job['kind'] == 'album'
    assert done['status'] == aurral.DONE
    assert [f['name'] for f in done['files']] == ['One.mp3', 'Three.mp3']
    assert (done['total'], done['finished'], done['failed']) == (3, 3, 1)


def test_another_user_cannot_see_a_job(setup):
    job = setup.post('/api/aurral/jobs', json={'song': SONG}).json()
    _wait(setup, job['id'])

    setup.who['now'] = Principal(kind='device', scope=CLIENT, user_id=8)
    assert setup.get(f'/api/aurral/jobs/{job["id"]}').status_code == 404
    assert setup.delete(f'/api/aurral/jobs/{job["id"]}').status_code == 404
    setup.who['now'] = Principal(
        kind='session', scope=ADMIN, user_id=1, role='admin'
    )
    assert setup.get(f'/api/aurral/jobs/{job["id"]}').status_code == 200


def test_bad_requests_are_refused(setup):
    assert setup.post('/api/aurral/jobs', json={}).status_code == 400
    assert (
        setup.post(
            '/api/aurral/jobs',
            json={'album_url': 'https://example.com/album'},
        ).status_code
        == 400
    )


def test_old_jobs_are_dropped(tmp_path):
    jobs = aurral.Jobs(tmp_path / 'handover')
    job = jobs.new('track', 'Song', 1)
    job.created -= aurral.JOB_TTL_SECONDS + 1

    assert jobs.prune() == [job.id]
    assert not job.folder.exists()


def test_the_folder_is_cleared_on_start(tmp_path):
    root = tmp_path / 'handover'
    (root / 'leftover').mkdir(parents=True)
    (root / 'leftover' / 'Song.mp3').write_bytes(b'x')

    aurral_routes.reset(root)
    assert not root.exists()


# ── The hand-over downloader ────────────────────────────────────────


def test_the_hand_over_downloader_leaves_the_app_one_alone(tmp_path):
    original = FakeDownloader(tmp_path / 'music')
    folder = tmp_path / 'job'
    dl = aurral.handover_downloader(original, folder)

    assert dl.download_dir == folder
    assert folder.is_dir()
    assert (dl.organize_by_artist, dl.organize_by_album) == (False, False)
    assert dl.overwrite_existing_files is True
    assert dl.on_downloaded is None
    assert dl.on_outcome is None
    assert dl.download_sources is None
    assert dl.download_policy is None
    assert dl.slskd_settings['leave_in_place'] is False
    assert dl.slskd_settings['output_dir'] == str(folder)
    dl._remove_slskd_source_after_import(tmp_path / 'a', tmp_path / 'b')
    # The app's own downloader is unchanged.
    assert original.download_dir == tmp_path / 'music'
    assert original.slskd_settings['leave_in_place'] is True
    assert original.organize_by_artist is True
    assert original.on_downloaded is not None


def test_names_never_clash():
    files = [aurral.HandoverFile(Path('a/Song.mp3'), 'Song.mp3')]
    assert aurral.unique_name(files, 'Song.mp3') == 'Song (2).mp3'
    assert aurral.unique_name(files, 'Other.mp3') == 'Other.mp3'
