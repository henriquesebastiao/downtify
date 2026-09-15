"""YouTube Music playlists and @handle artist URLs, for downloading and for
the Playlist Monitor.

All offline: the YouTube Music client is faked with payloads shaped like
the live ``get_playlist`` / ``navigation/resolve_url`` responses.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from downtify import api, monitor, providers

PLAYLIST_ID = 'PLx6XKQDAhfWZ4vxtvdmpkDKUnR2omdAdr'
PLAYLIST_URL = (
    f'https://music.youtube.com/playlist?list={PLAYLIST_ID}'
    '&si=icIkqaRdB2014lcl'
)
CHANNEL_ID = 'UCfLTxnQboSLcoSakgONmukQ'


def _row(video_id, title, artists, video_type=None, album=None, **extra):
    return {
        'videoId': video_id,
        'title': title,
        'artists': [{'name': name, 'id': aid} for name, aid in artists],
        'album': album,
        'duration': '3:13',
        'duration_seconds': 193,
        'isAvailable': True,
        'videoType': video_type,
        'thumbnails': [{'url': f'https://i.ytimg.com/vi/{video_id}/hq.jpg'}],
        **extra,
    }


class _FakeYTM:
    def __init__(self, playlist=None, resolve=None):
        self.playlist = playlist or {}
        self.resolve = resolve or {}
        self.resolve_calls: list[str] = []
        self.playlist_calls: list[tuple] = []

    def get_playlist(self, playlist_id, limit=100):
        self.playlist_calls.append((playlist_id, limit))
        return self.playlist

    def _send_request(self, endpoint, body):
        assert endpoint == 'navigation/resolve_url'
        self.resolve_calls.append(body['url'])
        return self.resolve


@pytest.fixture
def fake_ytm(monkeypatch):
    def _install(**kwargs):
        client = _FakeYTM(**kwargs)
        monkeypatch.setattr(providers, '_ytm', lambda: client)
        monkeypatch.setattr(providers, '_channel_id_cache', {})
        return client

    return _install


# ── parse_youtube_url ───────────────────────────────────────────────────────


def test_parse_playlist_url_with_share_param():
    assert providers.parse_youtube_url(PLAYLIST_URL) == (
        'playlist',
        PLAYLIST_ID,
    )


def test_parse_playlist_browse_url():
    assert providers.parse_youtube_url(
        f'https://music.youtube.com/browse/VL{PLAYLIST_ID}'
    ) == ('playlist', PLAYLIST_ID)


def test_parse_curated_youtube_music_playlist():
    assert providers.parse_youtube_url(
        'https://music.youtube.com/playlist?list=RDCLAK5uy_kmPRjHDECIcuVwnKsx'
    ) == ('playlist', 'RDCLAK5uy_kmPRjHDECIcuVwnKsx')


def test_parse_watch_url_inside_a_playlist_stays_a_track():
    assert providers.parse_youtube_url(
        f'https://music.youtube.com/watch?v=5CMuZrTy6jw&list={PLAYLIST_ID}'
    ) == ('track', '5CMuZrTy6jw')


def test_parse_radio_mix_is_not_a_playlist():
    assert (
        providers.parse_youtube_url(
            'https://music.youtube.com/playlist?list=RDAMVM5CMuZrTy6jw'
        )
        is None
    )


def test_parse_album_audio_playlist_is_still_an_album():
    assert providers.parse_youtube_url(
        'https://music.youtube.com/playlist?list=OLAK5uy_abc123'
    ) == ('album', 'OLAK5uy_abc123')


def test_parse_artist_handle_url():
    assert providers.parse_youtube_url(
        'https://music.youtube.com/@HenriqueeJuliano'
    ) == ('artist', '@HenriqueeJuliano')


def test_parse_artist_handle_on_youtube_com_and_encoded():
    assert providers.parse_youtube_url(
        'https://www.youtube.com/@Jo%C3%A3oGomes/videos?si=x'
    ) == ('artist', '@JoãoGomes')


# ── resolve_artist_channel_id ───────────────────────────────────────────────


def _resolved(browse_id):
    return {'endpoint': {'browseEndpoint': {'browseId': browse_id}}}


def test_channel_id_is_returned_as_is(fake_ytm):
    client = fake_ytm()
    assert providers.resolve_artist_channel_id(CHANNEL_ID) == CHANNEL_ID
    assert client.resolve_calls == []


def test_handle_resolves_through_youtube_music(fake_ytm):
    client = fake_ytm(resolve=_resolved(CHANNEL_ID))
    assert (
        providers.resolve_artist_channel_id('@HenriqueeJuliano') == CHANNEL_ID
    )
    # Only the music.youtube.com host maps a handle to an artist page.
    assert client.resolve_calls == [
        'https://music.youtube.com/@HenriqueeJuliano'
    ]


def test_handle_resolution_is_cached(fake_ytm):
    client = fake_ytm(resolve=_resolved(CHANNEL_ID))
    providers.resolve_artist_channel_id('@HenriqueeJuliano')
    providers.resolve_artist_channel_id('@henriqueejuliano')
    assert len(client.resolve_calls) == 1


def test_unknown_handle_raises(fake_ytm):
    # An unknown handle resolves to the YouTube Music home page.
    fake_ytm(resolve=_resolved('FEmusic_home'))
    with pytest.raises(ValueError, match='No YouTube Music artist'):
        providers.resolve_artist_channel_id('@nobody-here')


# ── playlist tracks ─────────────────────────────────────────────────────────


def _playlist(*rows, title='Best of MrSuicideSheep'):
    return {'title': title, 'trackCount': len(rows), 'tracks': list(rows)}


def test_playlist_title_and_tracks(fake_ytm):
    client = fake_ytm(
        playlist=_playlist(
            _row(
                'atv1',
                'Yellow',
                [('Coldplay', 'UCcold')],
                'MUSIC_VIDEO_TYPE_ATV',
                {'name': 'Parachutes', 'id': 'MPREb_x'},
            )
        )
    )
    title, songs = providers.playlist_info_and_tracks_from_id(PLAYLIST_ID)
    assert title == 'Best of MrSuicideSheep'
    # Every page is fetched, not just the first 100 tracks.
    assert client.playlist_calls == [(PLAYLIST_ID, None)]
    (song,) = songs
    assert song['name'] == 'Yellow'
    assert song['artists'] == ['Coldplay']
    assert song['album_name'] == 'Parachutes'


def test_playlist_song_is_pinned_to_its_own_video(fake_ytm):
    fake_ytm(
        playlist=_playlist(
            _row('ugc1', 'Bronze Whale - Patterns', [('Sheep', 'UCs')])
        )
    )
    (song,) = providers.playlist_tracks_from_id(PLAYLIST_ID)
    assert song['youtube_id'] == 'ugc1'
    assert song['song_id'] == 'ugc1'
    assert song['source'] == 'youtube'


def test_upload_credits_the_artist_in_the_title_not_the_uploader(fake_ytm):
    fake_ytm(
        playlist=_playlist(
            _row(
                'ugc1',
                'Bronze Whale - Patterns',
                [('MrSuicideSheep', 'UC5nc')],
                'MUSIC_VIDEO_TYPE_UGC',
            )
        )
    )
    (song,) = providers.playlist_tracks_from_id(PLAYLIST_ID)
    assert (song['name'], song['artists']) == ('Patterns', ['Bronze Whale'])


def test_upload_date_parsed_as_artist_is_dropped(fake_ytm):
    # ytmusicapi reports some uploads' date in the artists list.
    fake_ytm(
        playlist=_playlist(
            _row('v1', 'Illenium - Crawl Outta Love', [('Aug 7, 2017', None)])
        )
    )
    (song,) = providers.playlist_tracks_from_id(PLAYLIST_ID)
    assert (song['name'], song['artists']) == (
        'Crawl Outta Love',
        ['Illenium'],
    )


def test_upload_title_noise_is_stripped(fake_ytm):
    fake_ytm(
        playlist=_playlist(
            _row(
                'omv1',
                'Artist One, Artist Two - Song (Official Music Video)',
                [('Artist One', 'UCa')],
                'MUSIC_VIDEO_TYPE_OMV',
            )
        )
    )
    (song,) = providers.playlist_tracks_from_id(PLAYLIST_ID)
    assert song['name'] == 'Song'
    assert song['artists'] == ['Artist One', 'Artist Two']


def test_version_suffix_after_dash_is_not_taken_for_an_artist(fake_ytm):
    fake_ytm(
        playlist=_playlist(
            _row(
                'omv2',
                'Yellow - Live at Glastonbury',
                [('Coldplay', 'UCcold')],
                'MUSIC_VIDEO_TYPE_OMV',
            )
        )
    )
    (song,) = providers.playlist_tracks_from_id(PLAYLIST_ID)
    assert song['name'] == 'Yellow - Live at Glastonbury'
    assert song['artists'] == ['Coldplay']


def test_upload_without_dash_keeps_its_credited_artists(fake_ytm):
    fake_ytm(
        playlist=_playlist(
            _row(
                'omv3',
                'Somebody Else feat. GLNNA',
                [('Flux Pavilion', 'UCf'), ('GLNNA', 'UCg')],
                'MUSIC_VIDEO_TYPE_OMV',
            )
        )
    )
    (song,) = providers.playlist_tracks_from_id(PLAYLIST_ID)
    assert song['artists'] == ['Flux Pavilion', 'GLNNA']


def test_catalog_track_title_with_dash_is_left_alone(fake_ytm):
    fake_ytm(
        playlist=_playlist(
            _row(
                'atv2',
                'Hey Jude - Remastered 2015',
                [('The Beatles', 'UCb')],
                'MUSIC_VIDEO_TYPE_ATV',
            )
        )
    )
    (song,) = providers.playlist_tracks_from_id(PLAYLIST_ID)
    assert song['name'] == 'Hey Jude - Remastered 2015'
    assert song['artists'] == ['The Beatles']


def test_unavailable_and_id_less_rows_are_dropped(fake_ytm):
    gone = _row('gone', 'Deleted video', [('X', None)])
    gone['isAvailable'] = False
    no_id = _row(None, 'No id', [('X', None)])
    fake_ytm(playlist=_playlist(gone, no_id, _row('ok', 'A - B', [])))
    assert [
        s['song_id'] for s in providers.playlist_tracks_from_id(PLAYLIST_ID)
    ] == ['ok']


# ── watch source ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ('url', 'source'),
    [
        (PLAYLIST_URL, monitor.SOURCE_YOUTUBE_MUSIC),
        ('https://music.youtube.com/@HenriqueeJuliano', 'youtube_music'),
        (f'https://music.youtube.com/channel/{CHANNEL_ID}', 'youtube_music'),
        (
            'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M',
            'spotify',
        ),
        ('https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg', 'spotify'),
        # Rows written before YouTube Music watches existed.
        ('url', monitor.SOURCE_SPOTIFY),
    ],
)
def test_watch_source_from_url(url, source):
    assert monitor.watch_source(url) == source


def test_watch_dict_carries_its_source(tmp_path):
    db = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    yt = db.add_playlist(PLAYLIST_ID, 'YT', PLAYLIST_URL, 60)
    sp = db.add_playlist(
        'sp1', 'SP', 'https://open.spotify.com/playlist/sp1', 60
    )
    assert yt.to_dict()['source'] == 'youtube_music'
    assert sp.to_dict()['source'] == 'spotify'


def test_parse_playlist_url_covers_both_services():
    assert monitor.parse_playlist_url(PLAYLIST_URL) == (
        'youtube_music',
        PLAYLIST_ID,
    )
    assert monitor.parse_playlist_url(
        'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M'
    ) == ('spotify', '37i9dQZF1DXcBWIGoYBM5M')
    assert monitor.parse_playlist_url('https://music.youtube.com/@x') is None


# ── check_playlist on a YouTube Music playlist ──────────────────────────────


class _FakeDownloader:
    organize_by_artist = False
    organize_by_album = False

    def __init__(self, tmp_path):
        self.download_dir = tmp_path
        self.calls: list[tuple[str, str]] = []

    def download(self, song, progress_cb=None, subdir=None):
        self.calls.append((song['song_id'], subdir))
        (self.download_dir / f'{song["song_id"]}.mp3').write_bytes(b'x')
        return f'{song["song_id"]}.mp3'

    def existing_filename_for(self, song, subdir=None):
        name = f'{song["song_id"]}.mp3'
        return name if (self.download_dir / name).exists() else None


async def _noop_broadcast(_msg):
    return None


def _check(playlist, db, downloader):
    async def _scenario():
        return await monitor.check_playlist(
            playlist,
            db,
            downloader,
            _noop_broadcast,
            asyncio.get_running_loop(),
            settings={'generate_m3u': False},
        )

    return asyncio.run(_scenario())


def _no_spotify(*_args, **_kwargs):
    raise AssertionError('a YouTube Music watch must not call Spotify')


def test_check_youtube_music_playlist_downloads_its_tracks(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        monitor.providers,
        'playlist_tracks_from_id',
        lambda pid: [
            {'song_id': 'v1', 'name': 'One', 'artists': ['A']},
            {'song_id': 'v2', 'name': 'Two', 'artists': ['B']},
        ],
    )
    monkeypatch.setattr(
        monitor.spotify, 'playlist_tracks_from_id', _no_spotify
    )
    monkeypatch.setattr(monitor.spotify, 'track_from_id', _no_spotify)
    db = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    pl = db.add_playlist(PLAYLIST_ID, 'My YT Mix', PLAYLIST_URL, 60)
    dl = _FakeDownloader(tmp_path)

    assert _check(pl, db, dl) == 2
    assert dl.calls == [('v1', 'My YT Mix'), ('v2', 'My YT Mix')]

    # A track added to the playlist later is the only one fetched next time.
    monkeypatch.setattr(
        monitor.providers,
        'playlist_tracks_from_id',
        lambda pid: [
            {'song_id': 'v1', 'name': 'One', 'artists': ['A']},
            {'song_id': 'v2', 'name': 'Two', 'artists': ['B']},
            {'song_id': 'v3', 'name': 'Three', 'artists': ['C']},
        ],
    )
    again = _FakeDownloader(tmp_path)
    assert _check(pl, db, again) == 1
    assert again.calls == [('v3', 'My YT Mix')]


def test_check_spotify_playlist_still_uses_spotify(monkeypatch, tmp_path):
    monkeypatch.setattr(
        monitor.providers, 'playlist_tracks_from_id', _no_spotify
    )
    monkeypatch.setattr(
        monitor.spotify,
        'playlist_tracks_from_id',
        lambda pid: [{'song_id': 's1', 'name': 'One', 'artists': ['A']}],
    )
    monkeypatch.setattr(
        monitor.spotify, 'track_from_id', lambda tid: {'year': '2020'}
    )
    db = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    pl = db.add_playlist(
        'sp1', 'SP', 'https://open.spotify.com/playlist/sp1', 60
    )
    dl = _FakeDownloader(tmp_path)
    assert _check(pl, db, dl) == 1
    assert dl.calls == [('s1', 'SP')]


# ── API: adding watches ─────────────────────────────────────────────────────


def _resolve_watch(url):
    return asyncio.run(api._resolve_watch_target(url))


def test_watch_youtube_music_playlist(monkeypatch):
    monkeypatch.setattr(
        api.providers,
        'playlist_info_and_tracks_from_id',
        lambda pid: ('Best of MrSuicideSheep', []),
    )
    assert _resolve_watch(PLAYLIST_URL) == (
        monitor.KIND_PLAYLIST,
        PLAYLIST_ID,
        'Best of MrSuicideSheep',
    )


def test_watch_youtube_music_artist_handle(monkeypatch):
    monkeypatch.setattr(
        api.providers,
        'resolve_artist_channel_id',
        lambda value: CHANNEL_ID if value == '@HenriqueeJuliano' else None,
    )
    monkeypatch.setattr(
        api.providers,
        'artist_info_from_channel_id',
        lambda cid: {'name': 'Henrique & Juliano'},
    )
    assert _resolve_watch('https://music.youtube.com/@HenriqueeJuliano') == (
        monitor.KIND_ARTIST,
        CHANNEL_ID,
        'Henrique & Juliano',
    )


def test_watch_unknown_handle_is_404(monkeypatch):
    def _unknown(value):
        raise ValueError(f'No YouTube Music artist found for {value}')

    monkeypatch.setattr(api.providers, 'resolve_artist_channel_id', _unknown)
    with pytest.raises(HTTPException) as exc:
        _resolve_watch('https://music.youtube.com/@nobody-here')
    assert exc.value.status_code == 404


def test_same_artist_by_handle_and_channel_is_one_watch(monkeypatch, tmp_path):
    monkeypatch.setattr(
        api.providers, 'resolve_artist_channel_id', lambda value: CHANNEL_ID
    )
    monkeypatch.setattr(
        api.providers,
        'artist_info_from_channel_id',
        lambda cid: {'name': 'Henrique & Juliano'},
    )
    monkeypatch.setattr(
        api.state, 'monitor_db', monitor.PlaylistMonitorDB(tmp_path / 'm.db')
    )
    monkeypatch.setattr(api.state, 'downloader', None)

    class _Req:
        def __init__(self, url):
            self.url = url

        async def json(self):
            return {'url': self.url, 'interval_minutes': 60}

    added = asyncio.run(
        api.add_monitor_playlist(
            _Req(f'https://music.youtube.com/channel/{CHANNEL_ID}')
        )
    )
    assert added['source'] == 'youtube_music'
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            api.add_monitor_playlist(
                _Req('https://music.youtube.com/@HenriqueeJuliano')
            )
        )
    assert exc.value.status_code == 409


# ── API: downloading ────────────────────────────────────────────────────────


def test_resolve_url_lists_youtube_music_playlist_tracks(monkeypatch):
    songs = [{'song_id': 'v1', 'name': 'One', 'artists': ['A']}]
    monkeypatch.setattr(
        api.providers, 'playlist_tracks_from_id', lambda pid: songs
    )
    assert api._resolve_url(PLAYLIST_URL) == songs


def test_resolve_url_lists_releases_for_artist_handle(monkeypatch):
    monkeypatch.setattr(
        api.providers, 'resolve_artist_channel_id', lambda value: CHANNEL_ID
    )
    monkeypatch.setattr(
        api.providers,
        'artist_albums_from_channel_id',
        lambda cid: [{'album_id': 'MPREb_1', 'channel': cid}],
    )
    assert api._resolve_url('https://music.youtube.com/@HenriqueeJuliano') == [
        {'album_id': 'MPREb_1', 'channel': CHANNEL_ID}
    ]


def test_batch_from_youtube_music_playlist_uses_its_folder(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        api.providers,
        'playlist_info_and_tracks_from_id',
        lambda pid: ('Best of MrSuicideSheep', []),
    )
    monkeypatch.setattr(api.state, 'download_jobs', {})
    subdirs = []

    async def fake_run_download(song, song_id, subdir=None, delay_seconds=0):
        subdirs.append(subdir)

    monkeypatch.setattr(api, '_run_download', fake_run_download)
    asyncio.run(
        api._process_batch(
            [{'song_id': 'v1', 'name': 'One', 'artists': ['A']}],
            ['v1'],
            playlist_url=PLAYLIST_URL,
            generate_m3u=False,
        )
    )
    assert subdirs == ['Best of MrSuicideSheep']


# ── one check per watch at a time ───────────────────────────────────────────


def test_a_watch_is_never_checked_twice_at_once(monkeypatch, tmp_path):
    # Adding a watch starts its first check right away; the background
    # sweep must not start a second one while that is still downloading.
    db = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    pl = db.add_playlist(PLAYLIST_ID, 'Mix', PLAYLIST_URL, 60)
    runs = []

    async def _slow_check(playlist, *_args):
        runs.append(playlist.id)
        await release.wait()
        return 5

    monkeypatch.setattr(monitor, 'check_playlist', _slow_check)

    async def _scenario():
        first = asyncio.create_task(
            monitor.check_watch(pl, db, None, _noop_broadcast, None)
        )
        await asyncio.sleep(0)
        # Without the guard this second check would block on `release`.
        second = await asyncio.wait_for(
            monitor.check_watch(pl, db, None, _noop_broadcast, None), timeout=1
        )
        release.set()
        first_result = await first
        # Once the first check is done, the watch can be checked again.
        third = await monitor.check_watch(pl, db, None, _noop_broadcast, None)
        return first_result, second, third

    release = asyncio.Event()
    assert asyncio.run(_scenario()) == (5, 0, 5)
    assert runs == [pl.id, pl.id]


def test_check_guard_is_released_when_a_check_fails(monkeypatch, tmp_path):
    db = monitor.PlaylistMonitorDB(tmp_path / 'monitor.db')
    pl = db.add_playlist(PLAYLIST_ID, 'Mix', PLAYLIST_URL, 60)

    async def _boom(*_args):
        raise RuntimeError('network down')

    monkeypatch.setattr(monitor, 'check_playlist', _boom)
    with pytest.raises(RuntimeError):
        asyncio.run(monitor.check_watch(pl, db, None, _noop_broadcast, None))
    assert pl.id not in monitor._checks_running
