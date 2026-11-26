"""Watching an artist YouTube Music doesn't have, through MusicBrainz:
a pasted MusicBrainz artist link, or a Spotify artist link MusicBrainz
links to when YouTube Music has no artist of that name.

All offline - MusicBrainz, YouTube Music and the downloader are faked.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from downtify import api, monitor, musicbrainz
from tests.test_artist_watch_deezer import _sweep
from tests.test_artist_watch_duplicates import _FakeDownloader
from tests.test_artist_watch_musicbrainz import (
    _mb_track,
    _MusicBrainz,
    _rg,
)

AKARSH = '86db4b7b-0081-4857-bf45-32f46cba2fe4'
SPOTIFY_ID = '0TnOYISbd1XYRBk9myaseg'
OWN = [{'name': 'Akarsh', 'artist': {'id': AKARSH}, 'joinphrase': ''}]


def _resolve(url):
    return asyncio.run(api._resolve_watch_target(url))


# ── Reading the link ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    'url',
    [
        f'https://musicbrainz.org/artist/{AKARSH}',
        f'musicbrainz.org/artist/{AKARSH}/releases',
        f'https://beta.musicbrainz.org/artist/{AKARSH.upper()}?tab=1',
        f'  http://musicbrainz.org/artist/{AKARSH}#top  ',
    ],
)
def test_a_musicbrainz_artist_link_is_read(url):
    assert musicbrainz.parse_artist_url(url) == AKARSH


@pytest.mark.parametrize(
    'url',
    [
        f'https://musicbrainz.org/release-group/{AKARSH}',
        'https://musicbrainz.org/artist/not-an-id',
        f'https://example.com/musicbrainz.org/artist/{AKARSH}',
        f'https://open.spotify.com/artist/{SPOTIFY_ID}',
        '',
    ],
)
def test_anything_else_is_not_a_musicbrainz_artist(url):
    assert not musicbrainz.parse_artist_url(url)


def test_a_musicbrainz_link_watches_the_artist_through_musicbrainz(
    monkeypatch,
):
    monkeypatch.setattr(
        api.musicbrainz, 'artist_name', lambda artist_id: 'Akarsh Sahay'
    )
    kind, key, name = _resolve(f'https://musicbrainz.org/artist/{AKARSH}')
    assert kind == monitor.KIND_ARTIST
    assert key == f'musicbrainz:artist:{AKARSH}'
    assert monitor.musicbrainz_artist_of(key) == AKARSH
    assert name == 'Akarsh Sahay'
    assert (
        monitor.watch_source(f'https://musicbrainz.org/artist/{AKARSH}')
        == monitor.SOURCE_MUSICBRAINZ
    )


def test_an_unknown_musicbrainz_artist_is_a_404(monkeypatch):
    def missing(_artist_id):
        raise musicbrainz.NotFound('no artist')

    monkeypatch.setattr(api.musicbrainz, 'artist_name', missing)
    with pytest.raises(HTTPException) as err:
        _resolve(f'https://musicbrainz.org/artist/{AKARSH}')
    assert err.value.status_code == 404


# ── A Spotify link YouTube Music can't follow ──────────────────────────


def _spotify_without_youtube(monkeypatch, *, linked):
    monkeypatch.setattr(
        api.spotify, 'artist_name_from_id', lambda _id: 'Akarsh'
    )
    monkeypatch.setattr(
        api.providers,
        'search_artists',
        lambda query, limit: [
            {'name': 'Akarsh Benipal', 'artist_id': 'UCbenipal'}
        ],
    )
    asked = []

    def by_spotify(spotify_id):
        asked.append(spotify_id)
        return linked

    monkeypatch.setattr(api.musicbrainz, 'artist_id_for_spotify', by_spotify)
    return asked


def test_a_spotify_artist_missing_from_youtube_music_follows_musicbrainz(
    monkeypatch,
):
    asked = _spotify_without_youtube(monkeypatch, linked=AKARSH)
    kind, key, name = _resolve(f'https://open.spotify.com/artist/{SPOTIFY_ID}')
    assert asked == [SPOTIFY_ID]
    assert (kind, key, name) == (
        monitor.KIND_ARTIST,
        f'musicbrainz:artist:{AKARSH}',
        'Akarsh',
    )


def test_the_error_names_both_links_when_musicbrainz_has_none(monkeypatch):
    _spotify_without_youtube(monkeypatch, linked='')
    with pytest.raises(HTTPException) as err:
        _resolve(f'https://open.spotify.com/artist/{SPOTIFY_ID}')
    assert err.value.status_code == 409
    assert 'No YouTube Music artist is named exactly' in err.value.detail
    assert 'YouTube Music link' in err.value.detail
    assert 'musicbrainz.org/artist/' in err.value.detail


def test_musicbrainz_being_down_keeps_the_youtube_music_error(monkeypatch):
    _spotify_without_youtube(monkeypatch, linked='')

    def down(_id):
        raise musicbrainz.MusicBrainzError('busy')

    monkeypatch.setattr(api.musicbrainz, 'artist_id_for_spotify', down)
    with pytest.raises(HTTPException) as err:
        _resolve(f'https://open.spotify.com/artist/{SPOTIFY_ID}')
    assert err.value.status_code == 409


def test_a_youtube_music_match_never_asks_musicbrainz(monkeypatch):
    asked = _spotify_without_youtube(monkeypatch, linked=AKARSH)
    monkeypatch.setattr(
        api.providers,
        'search_artists',
        lambda query, limit: [{'name': 'Akarsh', 'artist_id': 'UCakarsh'}],
    )
    _kind, key, _name = _resolve(
        f'https://open.spotify.com/artist/{SPOTIFY_ID}'
    )
    assert key == 'UCakarsh'
    assert asked == []


# ── The sweep ───────────────────────────────────────────────────────────


def test_a_musicbrainz_watch_downloads_from_musicbrainz_alone(
    monkeypatch, tmp_path
):
    def no_youtube(_channel):
        raise AssertionError('YouTube Music must not be asked')

    monkeypatch.setattr(
        monitor.providers, 'artist_albums_from_channel_id', no_youtube
    )
    mb = _MusicBrainz(
        monkeypatch,
        [
            _rg('first', 'First Album', credit=OWN),
            _rg('one', 'One Song', 'Single', credit=OWN),
        ],
        {
            'first': [_mb_track(1, 'Opening', 'First Album', duration=200)],
            'one': [_mb_track(1, 'One Song', 'One Song', duration=180)],
        },
        artist=AKARSH,
    )
    db = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist(
        monitor.musicbrainz_artist_key(AKARSH),
        'Akarsh',
        f'https://musicbrainz.org/artist/{AKARSH}',
        60,
        monitor.KIND_ARTIST,
    )
    dl = _FakeDownloader(tmp_path)

    # MusicBrainz is the watch's own catalogue: read even with the
    # gap-filling setting off.
    downloaded = _sweep(db, watch, dl, {'artist_watch_musicbrainz': False})

    assert downloaded == 2
    assert sorted(dl.calls) == ['mb-First Album-1', 'mb-One Song-1']
    # The artist came from the link, not a lookup by name.
    assert mb.lookups == []
    refreshed = db.get_playlist(watch.id)
    assert refreshed.musicbrainz_id == AKARSH
    assert refreshed.source == monitor.SOURCE_MUSICBRAINZ
