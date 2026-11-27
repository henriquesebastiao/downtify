"""A failed download says what each audio source did (the queue's
"Show each source" view on the Failed tab)."""

from __future__ import annotations

import asyncio

import pytest

from downtify import api, monitor
from downtify import downloader as downloader_mod
from downtify.download_queue import PendingDownloads
from downtify.downloader import Downloader, NoAudioMatchError, source_attempts
from tests.test_downloader_providers import _SONG, _fake_youtube_dl

SLSKD_ON = {'enabled': True, 'base_url': 'https://slskd.example'}


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


@pytest.fixture
def slskd_misses(monkeypatch):
    def install(reason='no_match', detail='3 files, none close enough'):
        monkeypatch.setattr(
            downloader_mod, 'download_from_slskd', lambda *a, **k: None
        )
        monkeypatch.setattr(
            downloader_mod,
            'take_slskd_miss',
            lambda: {'reason': reason, 'detail': detail},
        )

    return install


def _failing_youtube(monkeypatch, message):
    class _Broken:
        def __init__(self, opts):
            self.params = opts

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def add_post_processor(self, *a, **k):
            pass

        @staticmethod
        def download(urls):
            raise downloader_mod.yt_dlp.utils.DownloadError(message)

    monkeypatch.setattr(downloader_mod.yt_dlp, 'YoutubeDL', _Broken)


def test_slskd_missed_then_youtube_failed(
    tmp_path, monkeypatch, no_youtube, slskd_misses
):
    slskd_misses()
    monkeypatch.setattr(
        downloader_mod, 'find_match', lambda song: ('vid12345678', {})
    )
    _failing_youtube(
        monkeypatch,
        'ERROR: [youtube] vid12345678: The page needs to be reloaded.',
    )
    d = Downloader(
        tmp_path,
        audio_providers=['slskd', 'youtube-music'],
        slskd_settings=SLSKD_ON,
    )

    with pytest.raises(Exception, match='reloaded') as caught:
        d.download(dict(_SONG))

    attempts = source_attempts(caught.value)
    assert [(a['provider'], a['result']) for a in attempts] == [
        ('slskd', 'nothing'),
        ('youtube-music', 'failed'),
    ]
    assert attempts[0]['reason'] == 'no_match'
    assert attempts[0]['detail'] == '3 files, none close enough'
    assert 'page needs to be reloaded' in attempts[1]['detail']


def test_no_source_had_it(tmp_path, monkeypatch, no_youtube, slskd_misses):
    slskd_misses(reason='no_results', detail='')
    monkeypatch.setattr(
        downloader_mod, 'find_match', lambda song: (None, None)
    )
    monkeypatch.setattr(
        downloader_mod, 'find_match_soundcloud', lambda song: None
    )
    d = Downloader(
        tmp_path,
        audio_providers=['slskd', 'youtube-music', 'soundcloud'],
        slskd_settings=SLSKD_ON,
    )

    with pytest.raises(NoAudioMatchError) as caught:
        d.download(dict(_SONG))

    assert [
        (a['provider'], a['result'], a['reason'])
        for a in source_attempts(caught.value)
    ] == [
        ('slskd', 'nothing', 'no_results'),
        ('youtube-music', 'nothing', ''),
        ('soundcloud', 'nothing', ''),
    ]


def test_a_finished_download_leaves_nothing_for_the_next(
    tmp_path, monkeypatch, no_youtube, slskd_misses
):
    slskd_misses()
    monkeypatch.setattr(
        downloader_mod, 'find_match', lambda song: ('vid12345678', {})
    )
    d = Downloader(
        tmp_path,
        audio_providers=['slskd', 'youtube-music'],
        slskd_settings=SLSKD_ON,
    )
    assert d.download(dict(_SONG)) == 'Artist - Track.mp3'
    # The thread's list is gone once the download ends.
    assert getattr(downloader_mod._ATTEMPTS, 'value', None) is None

    # A failure later on the same thread starts from an empty list.
    monkeypatch.setattr(
        downloader_mod, 'find_match', lambda song: (None, None)
    )
    with pytest.raises(NoAudioMatchError) as caught:
        d.download({**_SONG, 'name': 'Other'})
    assert [a['provider'] for a in source_attempts(caught.value)] == [
        'slskd',
        'youtube-music',
    ]


def test_other_errors_have_no_attempts():
    assert source_attempts(ValueError('x')) == []


def test_watch_failure_event_names_the_release_check():
    error = monitor.ReleaseMismatchError('does not validate')
    error.source_attempts = [
        {
            'provider': 'slskd',
            'result': 'nothing',
            'reason': 'no_match',
            'detail': '',
        }
    ]

    event = monitor._failure_event(
        {'name': 'Intro'},
        error,
        'Usher',
        'Artist release download or validation failed',
        {'provider': 'youtube-music'},
    )

    assert event['status'] == 'error'
    assert event['detail'] == 'does not validate'
    assert [(s['provider'], s['result']) for s in event['sources']] == [
        ('slskd', 'nothing'),
        ('youtube-music', 'rejected'),
    ]
    # The card's badge: the last source tried, not slskd's progress.
    assert event['provider'] == 'youtube-music'


def test_release_mismatch_is_still_a_value_error():
    # Callers that caught the old ValueError keep working.
    assert issubclass(monitor.ReleaseMismatchError, ValueError)


def test_failed_queue_job_keeps_its_sources_over_a_restart(
    tmp_path, monkeypatch
):
    store = PendingDownloads(tmp_path / 'library.db')
    monkeypatch.setattr(api.state, 'pending_downloads', store)
    monkeypatch.setattr(api.state, 'download_jobs', {})
    song = {**_SONG, 'song_id': 'sp1'}
    song_id = api._register_job(song, status='downloading')
    job = api.state.download_jobs[song_id]
    attempts = [
        {
            'provider': 'youtube-music',
            'result': 'failed',
            'reason': '',
            'detail': 'The page needs to be reloaded.',
        }
    ]
    row = api._pending_download(song, song_id)
    row.options['sources'] = attempts
    asyncio.run(api._remember_failed(job, row, 'Error: boom'))

    monkeypatch.setattr(api.state, 'download_jobs', {})
    assert asyncio.run(api._restore_failed_jobs(store, set())) == 1
    restored = next(iter(api.state.download_jobs.values()))
    assert restored['status'] == 'error'
    assert restored['sources'] == attempts
    assert restored['provider'] == 'youtube-music'
