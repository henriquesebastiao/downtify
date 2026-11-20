"""Why slskd wasn't used: the reason a download fell through, kept and
counted."""

from __future__ import annotations

from typing import Any

import pytest

from downtify import api, downloader, slskd_provider
from downtify.download_log import OUTCOME_COMPLETED, OUTCOME_FAILED
from downtify.monitor import KIND_ARTIST, PlaylistMonitorDB
from downtify.slskd_misses import SlskdMisses

SONG = {'name': 'Light', 'artists': ['Tom Jung'], 'duration': 200}
SETTINGS = {'enabled': True, 'base_url': 'https://slskd.example'}


class _Client:
    base_url = 'https://slskd.example'

    def __init__(self, responses: list[list[dict[str, Any]]]):
        self._responses = list(responses)

    @staticmethod
    def configured() -> bool:
        return True

    @staticmethod
    def can_connect() -> bool:
        return True

    @staticmethod
    def start_search(query: str) -> str:
        return 'search-1'

    @staticmethod
    def wait_search_complete(*args, **kwargs) -> bool:
        return True

    def search_responses(self, search_id: str) -> list[dict[str, Any]]:
        return self._responses.pop(0) if self._responses else []

    @staticmethod
    def delete_search(search_id: str) -> None:
        pass


@pytest.fixture
def client(monkeypatch):
    def install(responses, *, ranked=None, selected=None):
        fake = _Client(responses)
        monkeypatch.setattr(
            slskd_provider, 'SlskdClient', lambda settings: fake
        )
        monkeypatch.setattr(
            slskd_provider,
            '_slskd_search_queries',
            lambda song: ['Tom Jung Light', 'Light'],
        )
        if ranked is not None:
            monkeypatch.setattr(
                slskd_provider,
                '_rank_slskd_candidates',
                lambda *a, **k: list(ranked),
            )
        if selected is not None:
            monkeypatch.setattr(
                slskd_provider,
                '_select_download_candidates',
                lambda rows, settings: list(selected),
            )
        return fake

    return install


PEER = {'username': 'peer', 'hasFreeUploadSlot': True, 'files': [{}]}


def test_nobody_has_it(client):
    client([[], []])
    assert slskd_provider.download_from_slskd(SONG, SETTINGS) is None
    assert slskd_provider.take_miss()['reason'] == 'no_results'
    # Told once.
    assert slskd_provider.take_miss() is None


def test_unreachable(monkeypatch):
    class Down(_Client):
        @staticmethod
        def can_connect() -> bool:
            return False

    monkeypatch.setattr(
        slskd_provider, 'SlskdClient', lambda settings: Down([])
    )
    slskd_provider.download_from_slskd(SONG, SETTINGS)
    assert slskd_provider.take_miss()['reason'] == 'unreachable'


def test_the_query_that_got_furthest_is_reported(client):
    low = {'filename': 'Tom Jung - Light (Remix).mp3', 'match_score': 3}
    client([[], [PEER]], ranked=[low])

    slskd_provider.download_from_slskd(
        SONG, {**SETTINGS, 'match_min_score': 6}
    )

    miss = slskd_provider.take_miss()
    assert miss['reason'] == 'low_confidence'
    assert 'Remix' in miss['detail']


def test_files_that_fail_the_quality_rules(client):
    good = {'filename': 'Tom Jung - Light.mp3', 'match_score': 9}
    client([[PEER], [PEER]], ranked=[good], selected=[])

    slskd_provider.download_from_slskd(SONG, SETTINGS)

    assert slskd_provider.take_miss()['reason'] == 'quality_filtered'


# ── Carried to the outcome ───────────────────────────────────────────


def test_the_downloader_reports_the_reason_with_the_outcome():
    heard = []
    fake = downloader.Downloader.__new__(downloader.Downloader)
    fake.on_outcome = lambda song, outcome, filename: heard.append(song)

    downloader._SLSKD_MISS.value = {'reason': 'no_match', 'detail': ''}
    fake._report_outcome(dict(SONG), OUTCOME_COMPLETED, 'a.mp3')
    fake._report_outcome(dict(SONG), OUTCOME_COMPLETED, 'b.mp3')

    assert heard[0]['slskd_miss'] == {'reason': 'no_match', 'detail': ''}
    assert 'slskd_miss' not in heard[1]  # one download, one report


@pytest.fixture
def store(monkeypatch, tmp_path):
    misses = SlskdMisses(tmp_path / 'lib.db')
    monkeypatch.setattr(api.state, 'slskd_misses', misses)
    monkeypatch.setattr(api.state, 'download_log', None)
    return misses


def _song(provider='', reason='no_match'):
    return {
        **SONG,
        'download_provider': provider,
        'slskd_miss': {'reason': reason, 'detail': 'x'},
    }


def test_only_downloads_slskd_didnt_serve_are_counted(store):
    api.record_download_outcome(_song('youtube-music'), OUTCOME_COMPLETED)
    api.record_download_outcome(
        _song('youtube', 'no_results'), OUTCOME_COMPLETED
    )
    api.record_download_outcome(_song('', 'no_results'), OUTCOME_FAILED)
    api.record_download_outcome(
        {**SONG, 'download_provider': 'youtube'}, OUTCOME_COMPLETED
    )

    summary = store.summary()

    assert summary['total'] == 3
    assert summary['reasons'] == [
        {'reason': 'no_results', 'count': 2},
        {'reason': 'no_match', 'count': 1},
    ]
    assert summary['fallbacks'] == {
        'youtube-music': 1,
        'youtube': 1,
        'none': 1,
    }
    assert summary['recent'][0]['title'] == 'Light'
    assert summary['recent'][0]['artist'] == 'Tom Jung'


def test_reset_starts_the_count_over(store):
    api.record_download_outcome(_song('youtube'), OUTCOME_COMPLETED)
    assert store.reset() == 1
    assert store.summary()['total'] == 0


def test_a_watch_can_forget_its_failures(tmp_path):
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist('UCx', 'A', 'url', 60, KIND_ARTIST)
    other = db.add_playlist('UCy', 'B', 'url', 60, KIND_ARTIST)
    for playlist in (watch, other):
        db.history.record_failure(
            playlist.id, {'song_id': 's1', 'name': 'Light'}, 'boom'
        )

    assert db.history.forget_failures(watch.id) == 1
    assert db.history.failures(watch.id) == []
    assert len(db.history.failures(other.id)) == 1
