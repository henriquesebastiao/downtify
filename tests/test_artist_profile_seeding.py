"""Seeding an artist's profile (downtify/artist_profile.py): what is saved and
what is not when a service fails, and how the download pipeline queues the
work - offline: every service is faked."""

from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from downtify import artist_profile as ap

APPLE_FULL = {
    'bio_html': '<p>Apple bio</p>',
    'origin': 'Sydney, Australia',
    'born_or_formed': 'novembro de 1973',
    'is_group': True,
    'genre': 'Hard rock',
    'banner_bg_color': '',
    'applemusic_id': 'acdc/1',
}
DEEZER_FULL = {
    'bio_html': '',
    'social': {
        'twitter': 'https://twitter.com/acdc',
        'facebook': '',
        'website': '',
        'instagram': '',
    },
    'related_artist_names': ['Rival'],
}


class _Services:
    """Fakes Apple Music, Deezer, Spotify and YouTube Music; a value that is
    an ``Exception`` makes that call fail the way the real one does (a
    ``ValueError``). ``calls`` counts the calls that matter."""

    def __init__(
        self, monkeypatch, *, delay: float = 0.0, **overrides: Any
    ) -> None:
        self.calls: dict[str, int] = {}
        self.delay = delay
        self.values: dict[str, Any] = {
            'apple_id': '1',
            'apple_full': APPLE_FULL,
            'deezer_id': '9',
            'deezer_full': DEEZER_FULL,
            'spotify_related': ('Rival',),
            **overrides,
        }
        # What each service answers when it works, for a test to restore.
        self.working = dict(self.values)
        for module, attr, key in (
            (ap.apple_music, 'lookup_artist_id', 'apple_id'),
            (ap.apple_music, 'resolve_artist_id', 'apple_id'),
            (ap.apple_music, 'fetch_artist_full', 'apple_full'),
            (ap.deezer, 'lookup_artist_id', 'deezer_id'),
            (ap.deezer, 'resolve_artist_id', 'deezer_id'),
            (ap.deezer, 'fetch_artist_full', 'deezer_full'),
            (
                ap.spotify,
                'related_artist_names_from_id',
                'spotify_related',
            ),
        ):
            monkeypatch.setattr(
                module, attr, self._make(f'{key}.{attr}', key, attr)
            )
        monkeypatch.setattr(
            ap.apple_music, 'resolve_artist_slug_id', lambda name: None
        )
        monkeypatch.setattr(ap.providers, 'resolve_artist_id', lambda n: None)
        monkeypatch.setattr(
            ap.spotify,
            'search_artist_by_name',
            lambda name: {'id': 'SPOTIFYBYNAME', 'name': name},
        )

    def _make(self, label: str, key: str, attr: str):
        def call(*args: Any, **kwargs: Any) -> Any:
            self.calls[label] = self.calls.get(label, 0) + 1
            if self.delay and attr == 'fetch_artist_full':
                time.sleep(self.delay)
            value = self.values[key]
            if isinstance(value, Exception):
                if attr.startswith('resolve_'):
                    return None  # the plain lookups never raise
                raise value
            return value

        return call

    def fail(self, key: str) -> None:
        self.values[key] = ValueError('service down')

    def fix(self, key: str, value: Any) -> None:
        self.values[key] = value


def _files(root: Path) -> list[str]:
    return sorted(
        p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()
    )


@pytest.fixture(autouse=True)
def _clean_seeding_state():
    def reset() -> None:
        with ap._seed_pending_guard:
            ap._seed_pending.clear()
        ap._seed_locks.clear()
        while True:
            try:
                ap._seed_jobs.get_nowait()
            except queue.Empty:
                break

    reset()
    yield
    reset()


# ── what is saved, and what is not ─────────────────────────────────────────


@pytest.mark.parametrize(
    'broken',
    ['apple_id', 'apple_full', 'deezer_id', 'deezer_full'],
)
def test_a_failing_service_saves_nothing_and_the_next_call_tries_again(
    monkeypatch, tmp_path, broken
):
    services = _Services(monkeypatch)
    services.fail(broken)
    images: list[tuple] = []
    monkeypatch.setattr(
        ap,
        '_seed_image_from_streams',
        lambda *a: images.append(a),
    )

    profile = ap.ensure_profile(
        tmp_path, 'ACDC', [], 'en', image_kinds=(ap.KIND_PHOTO,)
    )

    # No file at all - not one holding just the bio - and no photo either.
    assert _files(tmp_path) == []
    assert images == []
    assert not profile['bio']

    # The service is back: the very next call makes the whole profile.
    services.fix(broken, services.working[broken])
    profile = ap.ensure_profile(tmp_path, 'ACDC', [], 'en')
    assert _files(tmp_path) == ['Metadata/ArtistData/ACDC.json']
    assert profile['bio'] == 'Apple bio'


def test_deezer_saying_there_is_no_such_artist_is_an_answer(
    monkeypatch, tmp_path
):
    _Services(monkeypatch, deezer_id=None)
    profile = ap.ensure_profile(tmp_path, 'ACDC', [], 'en')
    assert _files(tmp_path) == ['Metadata/ArtistData/ACDC.json']
    assert profile['bio'] == 'Apple bio'
    assert profile['genre'] == 'Hard rock'
    assert not profile['platforms_id']['deezer']


def test_apple_music_saying_there_is_no_such_artist_is_an_answer(
    monkeypatch, tmp_path
):
    _Services(
        monkeypatch,
        apple_id=None,
        deezer_full={**DEEZER_FULL, 'bio_html': '<p>Deezer bio</p>'},
    )
    profile = ap.ensure_profile(tmp_path, 'ACDC', [], 'en')
    assert profile['bio'] == 'Deezer bio'
    assert profile['social']['twitter'] == 'https://twitter.com/acdc'


def test_neither_service_knowing_the_artist_still_makes_the_profile(
    monkeypatch, tmp_path
):
    services = _Services(monkeypatch, apple_id=None, deezer_id=None)
    ap.ensure_profile(tmp_path, 'Nobody', [], 'en')
    assert _files(tmp_path) == ['Metadata/ArtistData/Nobody.json']
    # ...and that file is what stops later visits from asking again.
    before = dict(services.calls)
    ap.ensure_profile(tmp_path, 'Nobody', [], 'en')
    assert services.calls == before


def test_spotify_being_down_does_not_stop_a_profile_from_being_made(
    monkeypatch, tmp_path
):
    # Spotify's related names depend on a hash that rolls now and then:
    # best effort, never a reason to keep the profile from existing.
    _Services(monkeypatch, spotify_related=RuntimeError('hash rolled'))
    profile = ap.ensure_profile(tmp_path, 'ACDC', [], 'en')
    assert profile['bio'] == 'Apple bio'
    assert _files(tmp_path) == ['Metadata/ArtistData/ACDC.json']


def test_the_photo_and_banner_come_after_the_saved_text(monkeypatch, tmp_path):
    _Services(monkeypatch)
    seen: list[tuple[str, bool]] = []

    def record(download_dir, name, kind, spotify_id):
        seen.append((kind, ap._profile_path_for(download_dir, name).is_file()))

    monkeypatch.setattr(ap, '_seed_image_from_streams', record)
    ap.ensure_profile(
        tmp_path,
        'ACDC',
        [],
        'en',
        image_kinds=(ap.KIND_PHOTO, ap.KIND_BANNER),
    )
    assert seen == [(ap.KIND_PHOTO, True), (ap.KIND_BANNER, True)]


def test_no_images_are_asked_for_unless_the_settings_say_so(
    monkeypatch, tmp_path
):
    _Services(monkeypatch)
    monkeypatch.setattr(
        ap,
        '_seed_image_from_streams',
        lambda *a: pytest.fail('no image was asked for'),
    )
    ap.ensure_profile(tmp_path, 'ACDC', [], 'en')


def test_an_error_in_the_photo_leaves_the_saved_text_alone(
    monkeypatch, tmp_path
):
    _Services(monkeypatch)

    def boom(*args):
        raise RuntimeError('image host down')

    monkeypatch.setattr(ap, '_seed_image_from_streams', boom)
    profile = ap.ensure_profile(
        tmp_path, 'ACDC', [], 'en', image_kinds=(ap.KIND_PHOTO,)
    )
    assert profile['bio'] == 'Apple bio'
    assert _files(tmp_path) == ['Metadata/ArtistData/ACDC.json']


def test_fetch_bio_on_demand_is_as_forgiving_as_before(monkeypatch, tmp_path):
    # The manual "fetch" of the artist's edit dialog is not seeding: a
    # service that fails is skipped, and what the others gave is saved.
    _Services(monkeypatch, deezer_id=ValueError('down'))
    profile = ap.fetch_bio(tmp_path, 'ACDC', 'en')
    assert profile['bio'] == 'Apple bio'
    assert _files(tmp_path) == ['Metadata/ArtistData/ACDC.json']


# ── which artist a download seeds ───────────────────────────────────────────


@pytest.mark.parametrize(
    ('song', 'expected'),
    [
        ({'artists': ['AC/DC', 'Guest']}, 'AC/DC'),
        ({'artists': ['A'], 'album_artist': 'Album Artist'}, 'Album Artist'),
        ({'artists': [' Spaced '], 'album_artist': ''}, 'Spaced'),
        ({'artists': ['Various Artists']}, ''),
        ({'artists': ['A'], 'album_artist': 'various artists'}, ''),
        ({'artists': ['unknown']}, ''),
        ({'artists': []}, ''),
        ({}, ''),
    ],
)
def test_the_artist_a_download_seeds(song, expected):
    assert ap.profile_seed_artist_of(song) == expected


def _spotify_song(**extra: Any) -> dict[str, Any]:
    return {
        'source': 'spotify',
        'song_id': 'a' * 22,
        'artists': ['AC/DC'],
        **extra,
    }


def test_a_spotify_track_gives_its_artists_id_without_a_name_search(
    monkeypatch,
):
    _Services(monkeypatch)
    monkeypatch.setattr(
        ap.spotify, 'primary_artist_id_from_track_id', lambda tid: 'FROMTRACK'
    )
    monkeypatch.setattr(
        ap,
        '_spotify_id_from_name',
        lambda name: pytest.fail('no name search needed'),
    )
    assert ap._spotify_artist_id_for_song(_spotify_song(), 'ACDC') == (
        'FROMTRACK'
    )


@pytest.mark.parametrize(
    'song',
    [
        # Another artist than the profile's: the track's id would be theirs.
        _spotify_song(artists=['Someone Else']),
        {'source': 'youtube', 'song_id': 'vid', 'artists': ['AC/DC']},
        _spotify_song(song_id='not-a-spotify-id'),
    ],
)
def test_otherwise_the_spotify_id_comes_from_an_exact_name_search(
    monkeypatch, song
):
    _Services(monkeypatch)
    monkeypatch.setattr(
        ap.spotify,
        'primary_artist_id_from_track_id',
        lambda tid: pytest.fail('the track is not this artist'),
    )
    assert ap._spotify_artist_id_for_song(song, 'ACDC') == 'SPOTIFYBYNAME'


def test_a_failing_track_lookup_falls_back_to_the_name_search(monkeypatch):
    _Services(monkeypatch)

    def boom(track_id):
        raise RuntimeError('embed down')

    monkeypatch.setattr(ap.spotify, 'primary_artist_id_from_track_id', boom)
    assert ap._spotify_artist_id_for_song(_spotify_song(), 'ACDC') == (
        'SPOTIFYBYNAME'
    )


# ── the queue: distinct, guarded, never blocking ───────────────────────────


@pytest.fixture
def no_workers(monkeypatch):
    """Queue jobs without a pool running them; tests run them by hand.

    A pool started by an earlier test is still alive, blocked on the *old*
    queue: giving these tests a queue of their own keeps it from taking
    their jobs."""

    monkeypatch.setattr(ap, '_start_seed_workers', lambda: None)
    monkeypatch.setattr(ap, '_seed_jobs', queue.SimpleQueue())


def _drain() -> list[tuple]:
    jobs = []
    while True:
        try:
            jobs.append(ap._seed_jobs.get_nowait())
        except queue.Empty:
            return jobs


def test_fifty_tracks_of_one_artist_queue_it_once(
    monkeypatch, tmp_path, no_workers
):
    _Services(monkeypatch)
    queued = [
        ap.profile_seed_enqueue(
            tmp_path, {'artists': ['AC/DC'], 'name': f'Song {i}'}, 'en'
        )
        for i in range(50)
    ]
    assert queued.count(True) == 1
    assert len(_drain()) == 1


def test_same_artist_by_another_spelling_is_the_same_artist(
    monkeypatch, tmp_path, no_workers
):
    assert ap.profile_seed_enqueue(tmp_path, {'artists': ['AC/DC']}, 'en')
    assert not ap.profile_seed_enqueue(tmp_path, {'artists': ['ACDC']}, 'en')
    assert not ap.profile_seed_enqueue(tmp_path, {'artists': ['acdc']}, 'en')


def test_different_artists_each_get_queued(monkeypatch, tmp_path, no_workers):
    for name in ('A', 'B', 'C'):
        assert ap.profile_seed_enqueue(tmp_path, {'artists': [name]}, 'en')
    assert len(_drain()) == 3


def test_nothing_is_queued_for_an_artist_who_has_a_profile(
    monkeypatch, tmp_path, no_workers
):
    ap._save_profile(tmp_path, 'ACDC', ap.load_profile(tmp_path, 'ACDC'))
    assert not ap.profile_seed_enqueue(tmp_path, {'artists': ['ACDC']}, 'en')
    assert _drain() == []


def test_nothing_is_queued_for_various_artists(tmp_path, no_workers):
    assert not ap.profile_seed_enqueue(
        tmp_path, {'artists': ['Various Artists']}, 'en'
    )
    assert _drain() == []


def test_a_finished_job_frees_the_artist(monkeypatch, tmp_path, no_workers):
    services = _Services(monkeypatch)
    song = {'artists': ['ACDC'], 'source': 'youtube', 'song_id': 'v'}
    assert ap.profile_seed_enqueue(tmp_path, song, 'en')
    (job,) = _drain()
    ap._run_seed_job(job)
    assert ap._seed_pending == set()
    assert ap._profile_path_for(tmp_path, 'ACDC').is_file()
    assert services.calls['apple_full.fetch_artist_full'] == 1


def test_a_failed_job_is_not_remembered_the_next_track_tries_again(
    monkeypatch, tmp_path, no_workers
):
    services = _Services(monkeypatch)
    services.fail('deezer_id')
    song = {'artists': ['ACDC'], 'source': 'youtube', 'song_id': 'v'}
    assert ap.profile_seed_enqueue(tmp_path, song, 'en')
    ap._run_seed_job(_drain()[0])
    assert _files(tmp_path) == []
    # No cool-down: the next track by the same artist queues it again...
    assert ap.profile_seed_enqueue(tmp_path, song, 'en')
    services.fix('deezer_id', '9')
    ap._run_seed_job(_drain()[0])
    # ...and now it works.
    assert _files(tmp_path) == ['Metadata/ArtistData/ACDC.json']


def test_a_job_that_blows_up_still_frees_the_artist(
    monkeypatch, tmp_path, no_workers
):
    def boom(*args, **kwargs):
        raise RuntimeError('unexpected')

    monkeypatch.setattr(ap, 'profile_seed_song', boom)
    assert ap.profile_seed_enqueue(tmp_path, {'artists': ['ACDC']}, 'en')
    ap._run_seed_job(_drain()[0])
    assert ap._seed_pending == set()


def test_the_language_and_images_asked_for_reach_the_seeding(
    monkeypatch, tmp_path
):
    _Services(monkeypatch)
    seen: list[tuple] = []
    monkeypatch.setattr(
        ap,
        '_seed_profile',
        lambda download_dir, name, sid, lang, kinds: seen.append((
            name,
            sid,
            lang,
            kinds,
        )),
    )
    song = {'source': 'youtube', 'song_id': 'v', 'artists': ['ACDC']}
    assert ap.profile_seed_song(tmp_path, song, 'pt-BR', (ap.KIND_BANNER,))
    assert seen == [('ACDC', 'SPOTIFYBYNAME', 'pt-BR', (ap.KIND_BANNER,))]


def test_a_service_failing_makes_no_profile_and_says_so(monkeypatch, tmp_path):
    services = _Services(monkeypatch)
    services.fail('apple_full')
    song = {'source': 'youtube', 'song_id': 'v', 'artists': ['ACDC']}
    assert ap.profile_seed_song(tmp_path, song, 'en') is False
    assert _files(tmp_path) == []


# ── the guardrail: the lock and the second look ────────────────────────────


def test_workers_racing_for_one_artist_seed_them_once(monkeypatch, tmp_path):
    services = _Services(monkeypatch, delay=0.2)
    song = {'source': 'youtube', 'song_id': 'v', 'artists': ['ACDC']}
    results: list[bool] = []

    def work():
        results.append(ap.profile_seed_song(tmp_path, song, 'en'))

    threads = [threading.Thread(target=work) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)
    assert services.calls['apple_full.fetch_artist_full'] == 1
    assert results.count(True) == 1
    assert _files(tmp_path) == ['Metadata/ArtistData/ACDC.json']


def test_a_visit_and_a_download_racing_seed_the_artist_once(
    monkeypatch, tmp_path
):
    services = _Services(monkeypatch, delay=0.2)
    song = {'source': 'youtube', 'song_id': 'v', 'artists': ['ACDC']}
    threads = [
        threading.Thread(
            target=lambda: ap.profile_seed_song(tmp_path, song, 'en')
        ),
        threading.Thread(
            target=lambda: ap.ensure_profile(tmp_path, 'ACDC', [], 'en')
        ),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)
    assert services.calls['apple_full.fetch_artist_full'] == 1


def test_the_profile_is_written_atomically(monkeypatch, tmp_path):
    # No leftover temp file next to it, and never a half-written JSON.
    _Services(monkeypatch)
    ap.ensure_profile(tmp_path, 'ACDC', [], 'en')
    folder = tmp_path / 'Metadata' / 'ArtistData'
    assert [p.name for p in folder.iterdir()] == ['ACDC.json']


def test_a_failed_write_leaves_no_temp_file(monkeypatch, tmp_path):
    def boom(src, dst):
        raise OSError('disk full')

    monkeypatch.setattr(ap.os, 'replace', boom)
    with pytest.raises(OSError, match='disk full'):
        ap._atomic_write_json(tmp_path / 'x' / 'a.json', {'a': 1})
    assert [p.name for p in (tmp_path / 'x').iterdir()] == []


# ── the pool itself ─────────────────────────────────────────────────────────


def test_the_pool_seeds_in_the_background_and_never_blocks(
    monkeypatch, tmp_path
):
    _Services(monkeypatch)
    started = time.monotonic()
    assert ap.profile_seed_enqueue(
        tmp_path,
        {'source': 'youtube', 'song_id': 'v', 'artists': ['ACDC']},
        'en',
    )
    # Queuing is instant; the seeding happens on the pool's own threads.
    assert time.monotonic() - started < 0.5
    path = ap._profile_path_for(tmp_path, 'ACDC')
    deadline = time.monotonic() + 5
    while not path.is_file() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert path.is_file()


def test_the_pool_is_small_daemon_and_started_once():
    ap._start_seed_workers()
    ap._start_seed_workers()
    workers = [
        t for t in threading.enumerate() if t.name == 'downtify-profile-seed'
    ]
    assert 1 <= len(workers) <= ap.SEED_WORKERS
    # Daemon threads: a queue still full at exit never holds the app up.
    assert all(t.daemon for t in workers)
