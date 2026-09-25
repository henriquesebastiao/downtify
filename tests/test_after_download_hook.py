"""The hook that seeds an artist's profile when a download finishes:
``Downloader.on_downloaded`` and ``api.enrich_artist_after_download`` -
offline: nothing is really downloaded or fetched."""

from __future__ import annotations

import contextlib
import time
from pathlib import Path

import pytest

from downtify import api, artist_profile
from downtify import downloader as downloader_mod
from downtify.downloader import Downloader

SONG = {
    'source': 'youtube',
    'song_id': 'vid',
    'name': 'Thunderstruck',
    'artists': ['AC/DC'],
    # With both of these, download() doesn't look the video up first.
    'album_name': 'The Razors Edge',
    'cover_url': 'https://img.test/c.jpg',
}


@pytest.fixture
def downloader(tmp_path, monkeypatch):
    dl = Downloader(tmp_path)
    monkeypatch.setattr(
        downloader_mod, 'enrich_from_match', lambda song, match: song
    )
    monkeypatch.setattr(
        Downloader,
        '_fetch_and_tag',
        lambda self, *a: 'AC-DC - Thunderstruck.mp3',
    )
    return dl


# ── Downloader.on_downloaded ────────────────────────────────────────────────


def test_there_is_no_hook_until_the_app_sets_one(downloader):
    assert Downloader.on_downloaded is None
    assert downloader.download(SONG) == 'AC-DC - Thunderstruck.mp3'


def test_the_hook_hears_of_each_new_file_once(downloader):
    heard: list[tuple] = []
    downloader.on_downloaded = lambda song, filename: heard.append((
        song['name'],
        filename,
    ))
    assert downloader.download(SONG) == 'AC-DC - Thunderstruck.mp3'
    assert heard == [('Thunderstruck', 'AC-DC - Thunderstruck.mp3')]


def test_a_hook_that_fails_never_fails_the_download(downloader):
    def boom(song, filename):
        raise RuntimeError('enrichment exploded')

    downloader.on_downloaded = boom
    assert downloader.download(SONG) == 'AC-DC - Thunderstruck.mp3'


def test_the_hook_is_per_downloader_not_shared(tmp_path, downloader):
    downloader.on_downloaded = lambda song, filename: pytest.fail(
        'not this one'
    )
    other = Downloader(tmp_path / 'other')
    assert other.on_downloaded is None


def test_a_song_already_in_the_library_does_not_call_the_hook(
    tmp_path, monkeypatch
):
    dl = Downloader(tmp_path, overwrite_existing_files=False)
    monkeypatch.setattr(Downloader, '_can_resolve_path_early', lambda *a: True)
    monkeypatch.setattr(
        Downloader,
        'find_existing_download',
        lambda self, song, subdir: 'old.mp3',
    )
    dl.on_downloaded = lambda song, filename: pytest.fail(
        'it was not downloaded'
    )
    assert dl.download(SONG) == 'old.mp3'


def test_a_song_found_only_after_enrichment_does_not_call_the_hook_either(
    tmp_path, monkeypatch
):
    dl = Downloader(tmp_path, overwrite_existing_files=False)
    monkeypatch.setattr(
        downloader_mod, 'enrich_from_match', lambda song, match: song
    )
    monkeypatch.setattr(
        Downloader, '_can_resolve_path_early', lambda *a: False
    )
    monkeypatch.setattr(
        Downloader, '_target_lock', lambda self, song: contextlib.nullcontext()
    )
    monkeypatch.setattr(
        Downloader,
        'find_existing_download',
        lambda self, song, subdir: 'old.mp3',
    )
    dl.on_downloaded = lambda song, filename: pytest.fail(
        'it was not downloaded'
    )
    assert dl.download(SONG) == 'old.mp3'


def test_a_new_file_found_under_the_lock_calls_the_hook(tmp_path, monkeypatch):
    dl = Downloader(tmp_path, overwrite_existing_files=False)
    monkeypatch.setattr(
        downloader_mod, 'enrich_from_match', lambda song, match: song
    )
    monkeypatch.setattr(
        Downloader, '_can_resolve_path_early', lambda *a: False
    )
    monkeypatch.setattr(
        Downloader, '_target_lock', lambda self, song: contextlib.nullcontext()
    )
    monkeypatch.setattr(
        Downloader, 'find_existing_download', lambda self, song, subdir: None
    )
    monkeypatch.setattr(
        Downloader, '_fetch_and_tag', lambda self, *a: 'new.mp3'
    )
    heard: list[str] = []
    dl.on_downloaded = lambda song, filename: heard.append(filename)
    assert dl.download(SONG) == 'new.mp3'
    assert heard == ['new.mp3']


def test_a_file_a_provider_downloaded_calls_the_hook(tmp_path, monkeypatch):
    # slskd: the file is already there, and only gets tagged.
    dl = Downloader(tmp_path)
    spotify_song = {**SONG, 'source': 'spotify', 'song_id': 'a' * 22}
    spotify_song.pop('cover_url')
    monkeypatch.setattr(
        downloader_mod.spotify_mod,
        'enrich_track_from_spotify_if_sparse',
        lambda song: song,
    )
    monkeypatch.setattr(
        Downloader,
        '_resolve_source',
        lambda self, song, cb: (None, None, 'slskd', Path('x.flac')),
    )
    monkeypatch.setattr(
        downloader_mod, 'enrich_from_match', lambda song, match: song
    )
    monkeypatch.setattr(
        Downloader, '_finalize_local_source', lambda self, *a: 'slskd/x.flac'
    )
    heard: list[str] = []
    dl.on_downloaded = lambda song, filename: heard.append(filename)
    assert dl.download(spotify_song) == 'slskd/x.flac'
    assert heard == ['slskd/x.flac']


def test_a_download_that_fails_never_calls_the_hook(downloader, monkeypatch):
    def fail(self, *a):
        raise RuntimeError('yt-dlp said no')

    monkeypatch.setattr(Downloader, '_fetch_and_tag', fail)
    downloader.on_downloaded = lambda song, filename: pytest.fail(
        'nothing came down'
    )
    with pytest.raises(RuntimeError, match='yt-dlp said no'):
        downloader.download(SONG)


# ── api.enrich_artist_after_download ────────────────────────────────────────


@pytest.fixture
def seeding(tmp_path, monkeypatch):
    """The call ``enrich_artist_after_download`` makes, recorded."""

    calls: list[tuple] = []
    monkeypatch.setattr(api, '_artist_profile_download_dir', lambda: tmp_path)
    monkeypatch.setattr(
        artist_profile,
        'profile_seed_enqueue',
        lambda download_dir, song, lang, kinds: calls.append((
            download_dir,
            song['name'],
            lang,
            kinds,
        )),
    )
    monkeypatch.setattr(
        artist_profile,
        'profile_top_songs_refresh_in_background',
        lambda *a: pytest.fail(
            'top songs are for the artist page, not the pipeline'
        ),
    )
    monkeypatch.setattr(
        artist_profile,
        'profile_top_songs_ensure',
        lambda *a: pytest.fail(
            'top songs are for the artist page, not the pipeline'
        ),
    )
    return calls


def _settings(monkeypatch, **values):
    for key, value in {
        'ui_language': '',
        'download_cover_art_artist': False,
        'download_cover_art_artist_banner': False,
        **values,
    }.items():
        monkeypatch.setitem(api.state.settings, key, value)


def test_the_artist_is_queued_in_the_users_language(
    tmp_path, monkeypatch, seeding
):
    _settings(monkeypatch, ui_language='pt-BR')
    api.enrich_artist_after_download(SONG, 'f.mp3')
    assert seeding == [(tmp_path, 'Thunderstruck', 'pt-BR', ())]


def test_the_language_falls_back_to_english_when_no_page_has_said(
    monkeypatch, seeding
):
    _settings(monkeypatch, ui_language='')
    api.enrich_artist_after_download(SONG, 'f.mp3')
    assert seeding[0][2] == 'en'


@pytest.mark.parametrize(
    ('photo', 'banner', 'expected'),
    [
        (False, False, ()),
        (True, False, (artist_profile.KIND_PHOTO,)),
        (False, True, (artist_profile.KIND_BANNER,)),
        (True, True, (artist_profile.KIND_PHOTO, artist_profile.KIND_BANNER)),
    ],
)
def test_photo_and_banner_are_asked_for_only_as_the_settings_allow(
    monkeypatch, seeding, photo, banner, expected
):
    _settings(
        monkeypatch,
        download_cover_art_artist=photo,
        download_cover_art_artist_banner=banner,
    )
    api.enrich_artist_after_download(SONG, 'f.mp3')
    assert seeding[0][3] == expected


def test_a_settings_change_applies_to_the_very_next_track(
    monkeypatch, seeding
):
    _settings(monkeypatch)
    api.enrich_artist_after_download(SONG, 'a.mp3')
    _settings(monkeypatch, download_cover_art_artist=True)
    api.enrich_artist_after_download(SONG, 'b.mp3')
    assert [call[3] for call in seeding] == [(), (artist_profile.KIND_PHOTO,)]


def test_a_failure_queuing_never_reaches_the_download(monkeypatch, tmp_path):
    monkeypatch.setattr(api, '_artist_profile_download_dir', lambda: tmp_path)

    def boom(*a):
        raise RuntimeError('queue broke')

    monkeypatch.setattr(artist_profile, 'profile_seed_enqueue', boom)
    _settings(monkeypatch)
    api.enrich_artist_after_download(SONG, 'f.mp3')  # must not raise


def test_the_whole_way_a_finished_download_seeds_its_artist(
    monkeypatch, tmp_path
):
    """Downloader -> hook -> queue -> the profile file, with the services
    faked: what ``main.py`` wires up."""

    monkeypatch.setattr(api, '_artist_profile_download_dir', lambda: tmp_path)
    _settings(monkeypatch, ui_language='fr')
    seen: list[tuple] = []

    def fake_seed(download_dir, song, lang, kinds):
        seen.append((song['name'], lang, kinds))
        return True

    monkeypatch.setattr(artist_profile, 'profile_seed_song', fake_seed)
    dl = Downloader(tmp_path)
    monkeypatch.setattr(
        downloader_mod, 'enrich_from_match', lambda song, match: song
    )
    monkeypatch.setattr(Downloader, '_fetch_and_tag', lambda self, *a: 'f.mp3')
    dl.on_downloaded = api.enrich_artist_after_download

    dl.download(SONG)

    deadline = time.monotonic() + 5
    while not seen and time.monotonic() < deadline:
        time.sleep(0.02)
    assert seen == [('Thunderstruck', 'fr', ())]
