"""Library-only searches and policy admission, with no network or real audio."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from downtify import api, library_only, monitor


def entry(
    file: str, title: str, artist: str = 'Björk', album: str = 'Debut'
) -> dict:
    return {
        'file': file,
        'title': title,
        'artist': artist,
        'album': album,
        'duration': 100,
    }


@pytest.fixture
def local_client(monkeypatch):
    monkeypatch.setattr(
        api.state, 'settings', {**api.DEFAULT_SETTINGS, 'library_only': True}
    )
    monkeypatch.setattr(
        api,
        'entries_for_request',
        lambda request: [
            entry('local.mp3', 'Human Behaviour'),
            entry('other.mp3', 'Venus'),
        ],
    )
    monkeypatch.setattr(api, 'playlists_for_request', lambda request: [])
    monkeypatch.setattr(api.state, 'discover', None)
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


@pytest.mark.parametrize(
    'path',
    [
        '/api/stream?video_id=dQw4w9WgXcQ',
        '/api/stream/file?video_id=dQw4w9WgXcQ',
        '/api/preview?artist=A&title=T',
        '/api/url?url=https://example.com',
        '/api/finder/album?album_id=1',
        '/api/artists/top_songs?channel_id=x',
        '/api/library/replace/candidates?file=x',
        '/api/playlists/incomplete',
    ],
)
def test_external_gets_are_refused_before_resolution(local_client, path):
    response = local_client.get(path)
    assert response.status_code == 409
    assert response.json()['detail'] == library_only.DETAIL


@pytest.mark.parametrize(
    'path',
    [
        '/api/download/url',
        '/api/download/batch',
        '/api/download/album',
        '/api/download/csv',
        '/api/stream/prefetch',
        '/api/monitor/playlists',
        '/api/library/upgrade/start',
        '/api/library/upgrade/resume',
        '/api/podcasts/episodes/1/download',
    ],
)
def test_external_posts_are_refused(local_client, path):
    assert local_client.post(path, json={}).status_code == 409


def test_search_uses_only_visible_server_entries(local_client, monkeypatch):
    def no_provider(*args, **kwargs):
        pytest.fail('External provider called')

    monkeypatch.setattr(api.providers, 'search_songs', no_provider)
    monkeypatch.setattr(api.providers, 'search_artists', no_provider)
    monkeypatch.setattr(api.providers, 'search_albums', no_provider)
    rows = local_client.get('/api/songs/search?query=bjork+human').json()
    assert len(rows) == 1
    assert rows[0]['file'] == 'local.mp3'
    assert rows[0]['source'] == 'library'
    assert not rows[0]['url']
    assert local_client.get('/api/artists/search?query=x').json() == []
    assert local_client.get('/api/albums/search?query=x').json() == []


def test_similar_never_uses_radio_and_excludes_seed(local_client, monkeypatch):
    def no_radio(*args, **kwargs):
        pytest.fail('External radio called')

    monkeypatch.setattr(api.providers, 'youtube_similar_tracks', no_radio)
    response = local_client.get(
        '/api/similar/tracks',
        params={'artist': 'Björk', 'track': 'Human Behaviour'},
    )
    assert response.status_code == 200
    assert [s['file'] for s in response.json()['tracks']] == ['other.mp3']
    assert response.json()['source'] == 'library'


def test_unknown_seed_is_explicitly_empty(local_client):
    assert (
        local_client.get('/api/similar/tracks?artist=unknown').json()['tracks']
        == []
    )


def test_empty_and_unrelated_library_do_not_fabricate_similarity():
    assert library_only.similar([], 'A', 'T', 20)['tracks'] == []
    entries = [entry('a', 'A'), entry('b', 'B', 'Other', 'Different')]
    assert library_only.similar(entries, 'Björk', 'A', 20)['tracks'] == []


def test_duplicate_recordings_are_not_suggested_twice():
    rows = [entry('seed', 'Seed'), entry('a', 'A'), entry('a-flac', 'A')]
    assert len(library_only.similar(rows, 'Björk', 'Seed', 20)['tracks']) == 1


def test_similar_accepts_a_seed_with_several_artists():
    rows = [entry('seed', 'Seed', 'A; B'), entry('candidate', 'Other', 'A')]
    assert [
        e['file']
        for e in library_only.similar(rows, 'A', 'Seed', 20)['tracks']
    ] == ['candidate']


def test_common_album_names_do_not_link_unrelated_artists():
    rows = [
        entry('seed', 'Seed', 'A', 'Greatest Hits'),
        entry('other', 'Other', 'B', 'Greatest Hits'),
    ]
    assert library_only.similar(rows, 'A', 'Seed', 20)['tracks'] == []


def test_background_admission_and_cancellation_release_policy(monkeypatch):
    monkeypatch.setattr(
        api.state, 'settings', {**api.DEFAULT_SETTINGS, 'library_only': False}
    )
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api.state, 'upgrade_runner', None)

    async def run():
        async def pending():
            await asyncio.Event().wait()

        task = api.spawn_task(pending(), name='stream-prefetch-test')
        with pytest.raises(HTTPException):
            api._set_library_only(True)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0)
        api._set_library_only(True)
        assert api.state.settings['library_only'] is True

    asyncio.run(run())


def test_policy_activation_is_atomic_and_does_not_cancel_work():
    policy = library_only.Policy()
    settings = {'library_only': False}
    with policy.external(settings), pytest.raises(HTTPException) as error:
        policy.set_enabled(settings, True)
    assert error.value.status_code == 409
    assert settings['library_only'] is False
    policy.set_enabled(settings, True)
    with pytest.raises(HTTPException):
        with policy.external(settings):
            pytest.fail('External work admitted')
    policy.set_enabled(settings, False)
    with policy.external(settings):
        assert settings['library_only'] is False


@pytest.mark.parametrize('bad', ['false', 'true', 1, None, {}])
def test_policy_rejects_non_boolean_without_changes(bad):
    settings = {'library_only': False}
    with pytest.raises(HTTPException) as error:
        library_only.Policy().set_enabled(settings, bad)
    assert error.value.status_code == 400
    assert settings == {'library_only': False}


def test_old_settings_default_off_and_persistence(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text('{}')
    assert api._load_settings(path)['library_only'] is False
    path.write_text(json.dumps({'library_only': True}))
    assert api._load_settings(path)['library_only'] is True
    path.write_text(json.dumps({'library_only': 'true'}))
    assert api._load_settings(path)['library_only'] is False


def test_automatic_watch_is_preserved_without_checking(monkeypatch):
    async def should_not_run(*args):
        pytest.fail('Watch contacted provider')

    monkeypatch.setattr(monitor, '_check_watch_online', should_not_run)
    assert (
        asyncio.run(
            monitor.check_watch(
                None, None, None, None, None, {'library_only': True}
            )
        )
        == 0
    )


def test_automatic_watch_resumes_after_mode_is_disabled(monkeypatch):
    async def check(*args):
        return 3

    monkeypatch.setattr(monitor, '_check_watch_online', check)
    assert (
        asyncio.run(
            monitor.check_watch(
                None, None, None, None, None, {'library_only': False}
            )
        )
        == 3
    )


def test_discover_caches_are_not_served_in_library_mode(local_client):
    for path in [
        '/api/discover',
        '/api/discover/collections',
        '/api/discover/collections/deezer',
        '/api/discover/collections/spotify',
    ]:
        result = local_client.post(path, json={}).json()
        assert result['source'] == 'library'
        assert all(
            row['source'] == 'library' for row in result.get('artists', [])
        )
        if not path.endswith('/spotify'):
            assert [row['name'] for row in result['artists']] == ['Björk']
            assert [row['name'] for row in result['albums']] == ['Debut']


def test_existing_search_and_finder_return_local_album_artist_cards(
    local_client,
):
    artists = local_client.get('/api/artists/search?query=bjork').json()
    albums = local_client.get('/api/albums/search?query=debut').json()
    assert artists[0]['name'] == 'Björk'
    assert albums[0]['name'] == 'Debut'
    assert all(row['source'] == 'library' for row in artists + albums)
    finder = local_client.get('/api/finder/search?query=bjork').json()
    assert len(finder['songs']) == 2
    assert finder['artists'] == artists
    assert finder['albums'] == albums


def test_chart_contains_only_accessible_library_groups(local_client):
    chart = local_client.get('/api/discover/chart').json()
    assert [row['file'] for row in chart['tracks']] == [
        'local.mp3',
        'other.mp3',
    ]
    assert [row['name'] for row in chart['albums']] == ['Debut']
    assert [row['name'] for row in chart['artists']] == ['Björk']
    assert chart['playlists'] == []


def test_playlist_cards_preserve_real_identity_and_display_name():
    rows = library_only.playlist_rows([
        {'name': 'real.m3u', 'display_name': 'My mix', 'count': 2},
        {'name': 'Favorites', 'favorite': True, 'count': 1},
    ])
    assert rows[0]['favorite'] is True
    assert rows[1]['playlist_name'] == 'real.m3u'
    assert rows[1]['name'] == 'My mix'


def test_disabled_mode_retains_provider_search(local_client, monkeypatch):
    monkeypatch.setitem(api.state.settings, 'library_only', False)
    monkeypatch.setattr(
        api.providers,
        'search_songs',
        lambda *args, **kwargs: [{'name': 'online'}],
    )
    assert local_client.get('/api/songs/search?query=online').json() == [
        {'name': 'online'}
    ]
