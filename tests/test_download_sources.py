"""Each file's upload, uploads rejected per song, and files swapped on
disk outside Downtify (downtify/download_sources.py; issue #582)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from downtify import api, providers
from downtify import downloader as downloader_mod
from downtify.download_sources import (
    DownloadSources,
    audio_signature,
    same_audio,
    track_keys,
)
from downtify.downloader import Downloader, embed_metadata
from downtify.hand_replaced import HandReplacedFiles
from downtify.library_upgrade import (
    JOB_SKIPPED,
    LibraryUpgradeRunner,
    UpgradeDeps,
    UpgradeOptions,
)
from tests.test_hand_replaced import SONG, _audio

_needs_ffmpeg = pytest.mark.skipif(
    shutil.which('ffmpeg') is None, reason='no ffmpeg'
)

SPOTIFY_ID = '1zi7xx7UVEFkmKfv06H8x0'

NAME = 'Drake, WizKid, Kyla - One Dance.mp3'

ONE_DANCE = {
    'song_id': SPOTIFY_ID,
    'source': 'spotify',
    'name': 'One Dance',
    'artists': ['Drake', 'WizKid', 'Kyla'],
    'album_name': 'Views',
    'cover_url': 'https://example.com/cover.jpg',
    'duration': 3,
}


# ── Song identity ───────────────────────────────────────────────────────


def test_track_keys_name_the_song_every_way_it_is_known():
    assert track_keys({**ONE_DANCE, 'isrc': 'usuM71603531'}) == [
        f'spotify:{SPOTIFY_ID}',
        'isrc:USUM71603531',
        'name:drake|one dance',
    ]
    # A YouTube row's song_id is a video id, not a Spotify id.
    assert track_keys({
        'song_id': 'abc123def45',
        'source': 'youtube',
        'name': 'One  Dance',
        'artists': ['DRAKE'],
    }) == ['name:drake|one dance']
    assert track_keys({'spotify_id': SPOTIFY_ID}) == [f'spotify:{SPOTIFY_ID}']
    assert track_keys({}) == []


# ── The store ───────────────────────────────────────────────────────────


def test_rejected_sources_follow_the_song_under_any_key(tmp_path):
    store = DownloadSources(tmp_path / 'library.db')
    keys = track_keys(ONE_DANCE)
    store.record('Drake/One Dance.mp3', None, 'parodyVid01', keys)
    assert store.get('Drake\\One Dance.mp3')['source'] == 'parodyVid01'

    assert store.reject_file_source('Drake/One Dance.mp3') == 'parodyVid01'
    assert store.rejected_for(ONE_DANCE) == {'parodyVid01'}
    # The same song from a playlist that only names it.
    assert store.rejected_for({
        'name': 'One Dance',
        'artists': ['Drake'],
    }) == {'parodyVid01'}
    assert (
        store.rejected_for({'name': 'Hotline Bling', 'artists': ['Drake']})
        == set()
    )

    # The replacement's own source is never rejected.
    assert (
        store.reject_file_source('Drake/One Dance.mp3', keep='parodyVid01')
        is None
    )
    assert store.reject_file_source('Nothing.mp3') is None

    store.allow('parodyVid01', keys)
    assert store.rejected_for(ONE_DANCE) == set()
    store.reject('parodyVid01', keys)
    assert store.forget_rejections(keys) == len(keys)
    assert store.rejected_for(ONE_DANCE) == set()


def test_same_audio_ignores_small_length_drift():
    base = {'codec': 'MPEGInfo', 'sample_rate': 44100, 'channels': 2}
    assert same_audio({**base, 'length': 200.0}, {**base, 'length': 200.3})
    assert not same_audio({**base, 'length': 200.0}, {**base, 'length': 201.2})
    assert not same_audio(
        {**base, 'length': 200.0},
        {**base, 'length': 200.0, 'sample_rate': 48000},
    )


@_needs_ffmpeg
def test_a_retag_is_not_a_swap_but_new_audio_is(tmp_path):
    store = DownloadSources(tmp_path / 'library.db')
    path = _audio(tmp_path / 'music' / 'Artist - Song.mp3', 4)
    store.record('Artist - Song.mp3', path, 'abc123def45', ['name:a|s'])
    assert store.get('Artist - Song.mp3')['signature'] == audio_signature(path)

    # Downtify (or anyone) rewriting the tags: same audio.
    embed_metadata(path, SONG)
    assert not store.replaced_on_disk('Artist - Song.mp3', path)

    # The right version saved over it under the same name.
    _audio(path, 7, freq=660)
    assert store.replaced_on_disk('Artist - Song.mp3', path)
    # Unknown files never count as swapped.
    assert not store.replaced_on_disk('Other.mp3', path)


# ── The matcher skips rejected uploads ──────────────────────────────────


def _hit(video_id: str) -> dict[str, Any]:
    return {
        'videoId': video_id,
        'title': 'One Dance',
        'artists': [{'name': 'Drake'}],
        'duration_seconds': 174,
        'resultType': 'song',
    }


def test_pick_best_never_picks_an_excluded_upload():
    hits = [
        _hit('parodyVid01'),
        {**_hit('rightVid001'), 'duration_seconds': 180},
    ]
    assert (
        providers._pick_best(hits, 174, 'One Dance', ['Drake'])['videoId']
        == 'parodyVid01'
    )
    with providers.excluding_sources({'parodyVid01'}):
        assert providers.excluded_source('parodyVid01')
        assert (
            providers._pick_best(hits, 174, 'One Dance', ['Drake'])['videoId']
            == 'rightVid001'
        )
        with providers.excluding_sources({'rightVid001'}):
            assert (
                providers._pick_best(hits, 174, 'One Dance', ['Drake']) is None
            )
    assert not providers.excluded_source('parodyVid01')


# ── Downloads ───────────────────────────────────────────────────────────


@pytest.fixture
def loader(tmp_path, monkeypatch):
    """A downloader whose search returns the first upload not rejected
    and whose fetch writes a short MP3 (no network)."""

    monkeypatch.setattr(
        downloader_mod.spotify_mod,
        'enrich_track_from_spotify_if_sparse',
        lambda song: song,
    )
    monkeypatch.setattr(
        downloader_mod.deezer_mod,
        'enrich_track_from_deezer_if_sparse',
        lambda song: song,
    )
    uploads = ['parodyVid01', 'rightVid001']

    def find_match(song):
        for video_id in uploads:
            if not providers.excluded_source(video_id):
                return video_id, None
        return None, None

    monkeypatch.setattr(downloader_mod, 'find_match', find_match)
    downloads = tmp_path / 'music'
    downloads.mkdir()
    instance = Downloader(downloads)
    instance.audio_providers = ['youtube-music']
    instance.download_sources = DownloadSources(tmp_path / 'library.db')
    instance.hand_replaced = HandReplacedFiles(tmp_path / 'library.db')
    fetched: list[str] = []

    def fetch(song, video_id, progress_cb, subdir, provider):
        fetched.append(video_id)
        target_dir, prefix, basename = instance._expected_location(
            song, subdir
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        _audio(target_dir / f'{basename}.mp3', 3)
        return f'{prefix}{basename}.mp3'

    monkeypatch.setattr(instance, '_fetch_and_tag', fetch)
    instance.fetched = fetched
    return instance


@_needs_ffmpeg
def test_a_replaced_upload_is_never_downloaded_again(loader):
    assert loader.download(dict(ONE_DANCE)) == NAME
    assert loader.fetched == ['parodyVid01']
    row = loader.download_sources.get(NAME)
    assert row['source'] == 'parodyVid01'
    assert f'spotify:{SPOTIFY_ID}' in row['track_keys']

    # Replace audio swapped it: the parody is rejected for the song.
    loader.download_sources.reject_file_source(NAME)
    (loader.download_dir / NAME).unlink()

    # Days later another playlist (a daily mix) has the song again.
    loader.download(dict(ONE_DANCE))
    assert loader.fetched == ['parodyVid01', 'rightVid001']


@_needs_ffmpeg
def test_a_rejected_known_video_is_matched_by_metadata(loader):
    loader.download_sources.reject('parodyVid01', track_keys(ONE_DANCE))
    loader.download({**ONE_DANCE, 'youtube_id': 'parodyVid01'})
    assert loader.fetched == ['rightVid001']


@_needs_ffmpeg
def test_a_file_swapped_on_disk_is_kept_even_with_download_again(loader):
    assert loader.overwrite_existing_files  # "Download again" on
    loader.download(dict(ONE_DANCE))
    target = loader.download_dir / NAME
    # The user saves the right version (Nicotine+) under the same name.
    _audio(target, 6, freq=660)
    swapped = target.read_bytes()
    messages: list[str] = []

    result = loader.download(
        dict(ONE_DANCE),
        progress_cb=lambda pct, msg, provider=None: messages.append(msg),
    )

    assert result == NAME
    assert target.read_bytes() == swapped
    assert loader.fetched == ['parodyVid01']
    assert messages[-1] == 'Kept: audio replaced by hand'
    assert loader.hand_replaced.get(result)['source'] == 'disk'
    # And the upload it replaced is never picked for the song again.
    assert loader.download_sources.rejected_for(ONE_DANCE) == {'parodyVid01'}
    # The swapped file is now what Downtify knows it as.
    assert not loader.download_sources.replaced_on_disk(result, target)


@_needs_ffmpeg
def test_an_untouched_file_is_still_downloaded_again(loader):
    loader.download(dict(ONE_DANCE))
    loader.download(dict(ONE_DANCE))
    assert loader.fetched == ['parodyVid01', 'parodyVid01']
    assert loader.hand_replaced.get(NAME) is None


# ── Library upgrade ─────────────────────────────────────────────────────


@_needs_ffmpeg
def test_library_upgrade_keeps_audio_swapped_on_disk(tmp_path, monkeypatch):
    music = tmp_path / 'music'
    path = _audio(music / 'Artist - Song.mp3', 3)
    sources = DownloadSources(tmp_path / 'library.db')
    sources.record('Artist - Song.mp3', path, 'abc123def45', ['name:a|s'])
    _audio(path, 6, freq=660)
    hand = HandReplacedFiles(tmp_path / 'library.db')

    class _Ctx:
        download_dir = music
        slskd_dir = None
        extra_dirs: tuple[Path, ...] = ()

    finished: list[tuple[str, str]] = []

    class _DB:
        @staticmethod
        def finish_job(run_id, stored, status, detail='', changed=()):
            finished.append((stored, status))

        @staticmethod
        def set_stage(*args):
            pass

    runner = LibraryUpgradeRunner.__new__(LibraryUpgradeRunner)
    runner.db = _DB()
    runner.deps = UpgradeDeps(
        context=_Ctx,
        settings=dict,
        hand_replaced=hand,
        download_sources=sources,
    )
    runner._process(
        1,
        'Artist - Song.mp3',
        UpgradeOptions(categories=('audio',)),
        ['audio'],
    )
    assert finished == [('Artist - Song.mp3', JOB_SKIPPED)]
    assert hand.get('Artist - Song.mp3')['source'] == 'disk'
    assert sources.rejected_for({'name': 's', 'artists': ['a']}) == {
        'abc123def45'
    }


# ── Replace audio ───────────────────────────────────────────────────────


def test_replace_audio_rejects_the_upload_it_replaced(tmp_path, monkeypatch):
    class _Index:
        @staticmethod
        def spotify_id_for_filename(file):
            return SPOTIFY_ID

    store = DownloadSources(tmp_path / 'library.db')
    monkeypatch.setattr(api.state, 'download_sources', store)
    monkeypatch.setattr(api.state, 'track_index', _Index())
    store.record(NAME, None, 'parodyVid01', [])
    entry = {'title': 'One Dance', 'artist': 'Drake;WizKid;Kyla'}

    api._remember_replacement(NAME, tmp_path / NAME, entry, 'rightVid001')

    assert store.rejected_for(ONE_DANCE) == {'parodyVid01'}
    row = store.get(NAME)
    assert row['source'] == 'rightVid001'
    assert f'spotify:{SPOTIFY_ID}' in row['track_keys']

    # Picking the parody again by hand takes its rejection back, and
    # rejects the one it replaces.
    api._remember_replacement(NAME, tmp_path / NAME, entry, 'parodyVid01')
    assert store.rejected_for(ONE_DANCE) == {'rightVid001'}

    # An uploaded file: the last upload is rejected, nothing recorded.
    api._remember_replacement(NAME, tmp_path / NAME, entry, '')
    assert store.rejected_for(ONE_DANCE) == {'rightVid001', 'parodyVid01'}
    assert not store.get(NAME)['source']
