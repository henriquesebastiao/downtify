"""Tests for Spotify embed parsing helpers (no network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from downtify.spotify import (
    _album_names_by_uri,
    _album_release_date_from_open_page,
    _artist_full_discography,
    _artist_names,
    _artist_releases,
    _artists_from_subtitle,
    _embed_row_track,
    _fetch_embed_json,
    _largest_image,
    _normalize_release_date_text,
    _top_track_overview,
    _track_dict,
    album_tracks_from_id,
    artist_image_url_from_id,
    artist_page_from_id,
    artist_top_songs_from_id,
    enrich_track_from_spotify_if_sparse,
    playlist_cover_url_from_id,
    primary_artist_id_from_track_id,
)

# Aliases only — no real artist / track titles
_AL1 = 'AliasNorth'
_AL2 = 'AliasSouth'
_AL3 = 'AliasEast'
_AL4 = 'AliasWest'
_AL5 = 'AliasSolo'
_AL6 = 'AliasGuest'
_SUB_TWO_NBSP = f'{_AL1},\xa0{_AL2}'
_SUB_FULLWIDTH = f'{_AL3}，{_AL4}'


def test_embed_row_track_merges_wrapper_subtitle_onto_nested_track():
    item = {
        'track': {
            'uri': 'spotify:track:abc123',
            'id': 'abc123',
            'title': 'Test track title',
        },
        'subtitle': _SUB_TWO_NBSP,
    }
    merged = _embed_row_track(item)
    assert merged is not None
    assert merged['subtitle'] == _SUB_TWO_NBSP
    assert merged['id'] == 'abc123'


def test_embed_row_track_does_not_override_inner_subtitle():
    inner_sub = 'InnerSubtitle'
    item = {
        'track': {
            'id': 'x',
            'uri': 'spotify:track:x',
            'subtitle': inner_sub,
        },
        'subtitle': 'WrapperSubtitle',
    }
    merged = _embed_row_track(item)
    assert merged['subtitle'] == inner_sub


def test_embed_row_track_flat_row_returns_same_dict():
    flat = {
        'id': 'z',
        'uri': 'spotify:track:z',
        'subtitle': f'{_AL1}, {_AL2}',
    }
    assert _embed_row_track(flat) is flat


@pytest.mark.parametrize(
    ('subtitle', 'expected'),
    [
        (f'{_AL1}, {_AL2}', [_AL1, _AL2]),
        (_SUB_TWO_NBSP, [_AL1, _AL2]),
        (_SUB_FULLWIDTH, [_AL3, _AL4]),
    ],
)
def test_artists_from_subtitle_splits(subtitle, expected):
    got = [d['name'] for d in _artists_from_subtitle(subtitle)]
    assert got == expected


def test_artist_names_prefers_structured_artists():
    entity = {
        'artists': [
            {'name': _AL1},
            {'name': _AL2},
        ],
        'subtitle': 'SubtitleIgnored',
    }
    assert _artist_names(entity) == [_AL1, _AL2]


def test_artist_names_string_entries_in_artists_list():
    entity = {'artists': [f'  {_AL5}  ', _AL6]}
    assert _artist_names(entity) == [_AL5, _AL6]


def test_artist_names_falls_back_to_subtitle():
    entity = {
        'uri': 'spotify:track:t',
        'title': 'T',
        'subtitle': f'{_AL3}, {_AL4}',
    }
    assert _artist_names(entity) == [_AL3, _AL4]


def test_track_dict_parses_iso_release_date():
    track = _embed_row_track({
        'track': {
            'id': 'tid',
            'uri': 'spotify:track:tid',
            'title': 'TestSong',
            'releaseDate': {'isoString': '2024-06-15T00:00:00.000Z'},
        },
        'subtitle': f'{_AL1}, {_AL2}',
    })
    td = _track_dict(track, track_id='tid', fallback_album='TestAlbum')
    assert td['release_date'] == '2024-06-15'
    assert td['year'] == '2024'


def test_track_dict_year_only_release_date_object():
    """Embeds omit ``isoString`` for YEAR-precision rows; stamp year from ``year``."""
    entity = {
        'id': 'tid',
        'uri': 'spotify:track:tid',
        'title': 'TestSong',
        'releaseDate': {'year': 1994, 'precision': 'YEAR'},
        'artists': [{'name': _AL1}],
    }
    td = _track_dict(entity, track_id='tid', fallback_album='TestAlbum')
    assert td['release_date'] == '1994'
    assert td['year'] == '1994'


def test_track_dict_reads_track_number_from_embed():
    entity = {
        'id': 'tid',
        'uri': 'spotify:track:tid',
        'title': 'TestSong',
        'trackNumber': 4,
        'album': {'name': 'TestAlbum', 'trackCount': 12},
        'artists': [{'name': _AL1}],
    }
    td = _track_dict(entity, track_id='tid')
    assert td['track_number'] == 4
    assert td['album_track_total'] == 12


@patch('downtify.spotify.track_from_id')
def test_enrich_track_from_spotify_if_sparse_fetches_missing_fields(
    mock_track_from_id,
):
    mock_track_from_id.return_value = {
        'song_id': 'a' * 22,
        'source': 'spotify',
        'year': '2016',
        'release_date': '2016-07-01',
        'track_number': 24,
        'album_track_total': 100,
        'cover_url': 'https://example.com/cover.jpg',
        'album_name': 'TestAlbum',
        'artists': [_AL1],
        'artist': _AL1,
    }
    sparse = {
        'song_id': 'a' * 22,
        'source': 'spotify',
        'name': 'TestSong',
        'artists': [_AL1],
        'cover_url': 'https://example.com/playlist.jpg',
    }
    out = enrich_track_from_spotify_if_sparse(sparse)
    mock_track_from_id.assert_called_once_with('a' * 22)
    assert out['year'] == '2016'
    assert out['track_number'] == 24
    assert out['cover_url'] == 'https://example.com/cover.jpg'


@patch('downtify.spotify.track_from_id')
def test_enrich_track_from_spotify_if_sparse_skips_when_complete(
    mock_track_from_id,
):
    complete = {
        'song_id': 'b' * 22,
        'source': 'spotify',
        'year': '2020',
        'release_date': '2020-01-01',
        'track_number': 1,
    }
    assert enrich_track_from_spotify_if_sparse(complete) is complete
    mock_track_from_id.assert_not_called()


def test_normalize_month_precision_middle_string():
    assert _normalize_release_date_text('2024-06') == '2024-06-01'


def test_open_page_parses_music_release_meta():
    html = (
        '<html><head>'
        '<meta name="music:release_date" content="2025-10-03"/>'
        '</head></html>'
    )
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.raise_for_status = lambda: None
    with patch('downtify.spotify.httpx.get', return_value=mock_resp):
        assert _album_release_date_from_open_page(
            '4J7wEPiFH5EjMFzqec4E2k'
        ) == ('2025-10-03')


def test_album_tracks_fallback_open_page_when_embed_missing():
    entity = {
        'name': 'TestAlbum',
        'releaseDate': None,
        'trackList': [
            {
                'uri': 'spotify:track:t1',
                'title': 'TestTrackOne',
                'subtitle': _AL1,
            },
        ],
    }
    payload = {
        'props': {
            'pageProps': {'state': {'data': {'entity': entity}}},
        },
    }
    with (
        patch('downtify.spotify._fetch_embed_json', return_value=payload),
        patch(
            'downtify.spotify._album_release_date_from_open_page',
            return_value='2025-10-03',
        ),
    ):
        songs = album_tracks_from_id('dummyAlbumId')
    assert len(songs) == 1
    assert songs[0]['release_date'] == '2025-10-03'
    assert songs[0]['year'] == '2025'


def test_largest_image_sorts_by_max_width():
    sources = [
        {'url': 'https://example.com/small.jpg', 'maxWidth': 160},
        {'url': 'https://example.com/large.jpg', 'maxWidth': 640},
        {'url': 'https://example.com/medium.jpg', 'maxWidth': 320},
    ]
    assert _largest_image(sources) == 'https://example.com/large.jpg'


def test_largest_image_sorts_by_width_when_present():
    sources = [
        {'url': 'https://example.com/small.jpg', 'width': 300},
        {'url': 'https://example.com/large.jpg', 'width': 1200},
    ]
    assert _largest_image(sources) == 'https://example.com/large.jpg'


def test_artist_image_url_from_id_reads_visual_identity():
    entity = {
        'type': 'artist',
        'name': 'TestArtist',
        'visualIdentity': {
            'image': [
                {'url': 'https://example.com/artist-320.jpg', 'maxWidth': 320},
                {'url': 'https://example.com/artist-640.jpg', 'maxWidth': 640},
            ],
        },
    }
    payload = {
        'props': {
            'pageProps': {'state': {'data': {'entity': entity}}},
        },
    }
    with patch('downtify.spotify._fetch_embed_json', return_value=payload):
        assert (
            artist_image_url_from_id('dummyArtistId')
            == 'https://example.com/artist-640.jpg'
        )


def test_primary_artist_id_from_track_id_reads_first_artist_uri():
    entity = {
        'type': 'track',
        'name': 'TestTrack',
        'artists': [
            {'name': _AL1, 'uri': 'spotify:artist:aaaaaaaaaaaaaaaaaaaaaa'},
            {'name': _AL2, 'uri': 'spotify:artist:bbbbbbbbbbbbbbbbbbbbbb'},
        ],
    }
    payload = {
        'props': {
            'pageProps': {'state': {'data': {'entity': entity}}},
        },
    }
    with patch('downtify.spotify._fetch_embed_json', return_value=payload):
        assert (
            primary_artist_id_from_track_id('dummyTrackId')
            == 'aaaaaaaaaaaaaaaaaaaaaa'
        )


def test_primary_artist_id_from_track_id_no_artists_returns_none():
    entity = {'type': 'track', 'name': 'TestTrack'}
    payload = {
        'props': {
            'pageProps': {'state': {'data': {'entity': entity}}},
        },
    }
    with patch('downtify.spotify._fetch_embed_json', return_value=payload):
        assert primary_artist_id_from_track_id('dummyTrackId') is None


def test_album_tracks_inherit_album_release_date():
    entity = {
        'name': 'TestAlbum',
        'releaseDate': {'isoString': '2021-11-30T12:00:00Z'},
        'trackList': [
            {
                'uri': 'spotify:track:tr1',
                'title': 'Song One',
                'subtitle': _AL1,
            },
        ],
    }
    payload = {
        'props': {
            'pageProps': {'state': {'data': {'entity': entity}}},
        },
    }
    with patch('downtify.spotify._fetch_embed_json', return_value=payload):
        songs = album_tracks_from_id('dummy')
    assert len(songs) == 1
    assert songs[0]['release_date'] == '2021-11-30'
    assert songs[0]['year'] == '2021'


def test_track_dict_uses_subtitle_when_artists_empty():
    track = _embed_row_track({
        'track': {
            'id': 'tid',
            'uri': 'spotify:track:tid',
            'title': 'TestSong',
        },
        'subtitle': f'{_AL1}, {_AL2}',
    })
    td = _track_dict(track, track_id='tid', fallback_album='TestAlbum')
    assert td['artists'] == [_AL1, _AL2]
    assert td['artist'] == f'{_AL1}, {_AL2}'
    assert td['album_name'] == 'TestAlbum'
    assert td['name'] == 'TestSong'


def test_album_tracks_from_id_merges_row_subtitle():
    entity = {
        'name': 'TestAlbum',
        'trackList': [
            {
                'track': {
                    'id': 't1',
                    'uri': 'spotify:track:t1',
                    'title': 'TestTrackOne',
                },
                'subtitle': f'{_AL1}, {_AL2}',
            },
        ],
    }
    payload = {
        'props': {
            'pageProps': {
                'state': {'data': {'entity': entity}},
            },
        },
    }

    with (
        patch('downtify.spotify._fetch_embed_json', return_value=payload),
        patch(
            'downtify.spotify._album_release_date_from_open_page',
            return_value='',
        ),
    ):
        songs = album_tracks_from_id('dummyAlbumId')

    assert len(songs) == 1
    assert songs[0]['song_id'] == 't1'
    assert songs[0]['artists'] == [_AL1, _AL2]
    assert songs[0]['artist'] == f'{_AL1}, {_AL2}'
    assert songs[0]['album_name'] == 'TestAlbum'
    assert songs[0]['track_number'] == 1
    assert songs[0]['album_track_total'] == 1


def _http_status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request('GET', 'https://open.spotify.com/embed/x/y')
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError(
        f'HTTP {status}', request=request, response=response
    )


def test_fetch_embed_json_retries_transient_504() -> None:
    ok = MagicMock(status_code=200)
    ok.text = (
        '<script id="__NEXT_DATA__" type="application/json">'
        '{"props":{"pageProps":{"state":{"data":{"entity":{}}}}}}'
        '</script>'
    )
    ok.raise_for_status = MagicMock()

    fail = MagicMock(status_code=504)
    fail.raise_for_status.side_effect = _http_status_error(504)

    with (
        patch('downtify.spotify.time.sleep'),
        patch(
            'downtify.spotify.httpx.get',
            side_effect=[fail, fail, ok],
        ) as mock_get,
    ):
        data = _fetch_embed_json('playlist', 'abc123')

    assert mock_get.call_count == 3
    assert 'props' in data


def test_fetch_embed_json_does_not_retry_client_errors() -> None:
    fail = MagicMock(status_code=404)
    fail.raise_for_status.side_effect = _http_status_error(404)

    with (
        patch('downtify.spotify.time.sleep') as mock_sleep,
        patch('downtify.spotify.httpx.get', return_value=fail),
    ):
        with pytest.raises(httpx.HTTPStatusError):
            _fetch_embed_json('playlist', 'missing')

    mock_sleep.assert_not_called()


# ── playlist_cover_url_from_id ─────────────────────────────────────────────


def _embed_payload_for(entity: dict) -> dict:
    return {'props': {'pageProps': {'state': {'data': {'entity': entity}}}}}


def test_playlist_cover_url_picks_largest_source():
    entity = {
        'name': 'Test Playlist',
        'coverArt': {
            'sources': [
                {'url': 'https://example.test/small.jpeg', 'width': 300},
                {'url': 'https://example.test/large.jpeg', 'width': 640},
            ]
        },
    }
    with patch(
        'downtify.spotify._fetch_embed_json',
        return_value=_embed_payload_for(entity),
    ):
        cover = playlist_cover_url_from_id('dummyPlaylistId')
    assert cover == 'https://example.test/large.jpeg'


def test_playlist_cover_url_falls_back_to_visual_identity():
    entity = {
        'name': 'Test Playlist',
        'visualIdentity': {
            'image': [
                {'url': 'https://example.test/visual.jpeg', 'width': 512}
            ]
        },
    }
    with patch(
        'downtify.spotify._fetch_embed_json',
        return_value=_embed_payload_for(entity),
    ):
        cover = playlist_cover_url_from_id('dummyPlaylistId')
    assert cover == 'https://example.test/visual.jpeg'


def test_playlist_cover_url_empty_when_no_art():
    entity = {'name': 'Test Playlist'}
    with patch(
        'downtify.spotify._fetch_embed_json',
        return_value=_embed_payload_for(entity),
    ):
        cover = playlist_cover_url_from_id('dummyPlaylistId')
    assert not cover


def test_artist_top_songs_resolves_trackList_shelf():
    # Mirrors the real open.spotify.com/embed/artist/<id> payload shape,
    # confirmed against a live fetch: the shelf is entity['trackList'], a
    # bare list of flat rows (no 'track' wrapper) — same field name
    # playlists/albums use, but with per-row subtitle as the artist name
    # and no 'id' (only 'uri'). 22-char ids so enrich_track_from_spotify_
    # if_sparse's id-shape guard doesn't skip them.
    track_id_1 = '1' * 22
    track_id_2 = '2' * 22
    entity = {
        'name': 'Test Artist',
        'title': 'Test Artist',
        'subtitle': 'Top tracks',
        'visualIdentity': {
            'image': [
                {'url': 'https://example.test/artist.jpeg', 'width': 640}
            ]
        },
        'trackList': [
            {
                'uri': f'spotify:track:{track_id_1}',
                'title': 'Song One',
                'subtitle': 'Test Artist',
                'duration': 200000,
            },
            {
                'uri': f'spotify:track:{track_id_2}',
                'title': 'Song Two',
                'subtitle': 'Test Artist',
                'duration': 210000,
            },
        ],
    }
    with (
        patch(
            'downtify.spotify._fetch_embed_json',
            return_value=_embed_payload_for(entity),
        ),
        patch('downtify.spotify.track_from_id') as mock_track_from_id,
    ):
        mock_track_from_id.side_effect = lambda tid: {
            'song_id': tid,
            'source': 'spotify',
            'year': '2002',
            'release_date': '2002-06-04',
            'cover_url': f'https://example.test/album-{tid}.jpeg',
        }
        name, cover, songs = artist_top_songs_from_id('dummyArtistId')
    assert name == 'Test Artist'
    assert cover == 'https://example.test/artist.jpeg'
    assert [s['song_id'] for s in songs] == [track_id_1, track_id_2]
    assert songs[0]['name'] == 'Song One'
    assert songs[0]['artists'] == ['Test Artist']
    assert songs[0]['duration'] == 200
    assert songs[0]['source'] == 'spotify'
    # Each track gets its own album cover via enrichment (a shelf row
    # carries no per-track art of its own) — not the artist's photo,
    # and not the same cover for every track either.
    assert (
        songs[0]['cover_url']
        == f'https://example.test/album-{track_id_1}.jpeg'
    )
    assert (
        songs[1]['cover_url']
        == f'https://example.test/album-{track_id_2}.jpeg'
    )
    assert songs[0]['cover_url'] != cover
    # No token in this payload, so there is no album lookup: the name
    # stays blank rather than being invented.
    assert not songs[0]['album_name']


def test_artist_top_songs_empty_shelf_returns_empty_list():
    entity = {'name': 'Test Artist'}
    with patch(
        'downtify.spotify._fetch_embed_json',
        return_value=_embed_payload_for(entity),
    ):
        name, _cover, songs = artist_top_songs_from_id('dummyArtistId')
    assert name == 'Test Artist'
    assert songs == []


def test_artist_top_songs_raises_when_name_missing():
    entity = {'trackList': []}
    with (
        patch(
            'downtify.spotify._fetch_embed_json',
            return_value=_embed_payload_for(entity),
        ),
        pytest.raises(ValueError, match='Could not read artist name'),
    ):
        artist_top_songs_from_id('dummyArtistId')


_TRACK_1 = '1' * 22
_TRACK_2 = '2' * 22
_TRACK_3 = '3' * 22


def _discography(
    top_albums: dict[str, str],
    listed: dict[str, str],
    plays: dict | None = None,
) -> dict:
    """A ``queryArtistOverview`` discography: top tracks reference their
    album by uri only; released albums are listed with their names."""

    plays = plays or {}

    return {
        'topTracks': {
            'items': [
                {
                    'track': {
                        'id': track_id,
                        'uri': f'spotify:track:{track_id}',
                        'albumOfTrack': {'uri': album_uri},
                        'playcount': plays.get(track_id),
                    }
                }
                for track_id, album_uri in top_albums.items()
            ]
        },
        'albums': {
            'items': [
                {
                    'releases': {
                        'items': [{'uri': uri, 'name': name}],
                    }
                }
                for uri, name in listed.items()
            ]
        },
    }


def test_album_names_by_uri_only_keeps_named_albums():
    node = {
        'a': {'uri': 'spotify:album:AAA', 'name': ' Album A '},
        'b': [{'uri': 'spotify:album:BBB'}],
        'c': {'uri': 'spotify:track:TTT', 'name': 'Not an album'},
        'd': {'nested': {'uri': 'spotify:album:CCC', 'name': 'Album C'}},
    }
    assert _album_names_by_uri(node) == {
        'spotify:album:AAA': 'Album A',
        'spotify:album:CCC': 'Album C',
    }


def test_top_track_overview_albums_come_from_the_discography():
    discography = _discography(
        {_TRACK_1: 'spotify:album:AAA', _TRACK_2: 'spotify:album:AAA'},
        {'spotify:album:AAA': 'Test Album'},
    )
    with (
        patch(
            'downtify.spotify._artist_discography', return_value=discography
        ),
        patch('downtify.spotify._fetch_embed_json') as embed,
    ):
        overview = _top_track_overview('artistId', 'token')
    assert overview == {
        _TRACK_1: {'album_name': 'Test Album'},
        _TRACK_2: {'album_name': 'Test Album'},
    }
    embed.assert_not_called()


def test_top_track_overview_falls_back_to_the_album_embed():
    discography = _discography(
        {_TRACK_1: 'spotify:album:AAA', _TRACK_2: 'spotify:album:OLD'},
        {'spotify:album:AAA': 'Listed Album'},
    )
    with (
        patch(
            'downtify.spotify._artist_discography', return_value=discography
        ),
        patch(
            'downtify.spotify._fetch_embed_json',
            return_value=_embed_payload_for({'name': 'Older Album'}),
        ) as embed,
    ):
        overview = _top_track_overview('artistId', 'token')
    assert overview == {
        _TRACK_1: {'album_name': 'Listed Album'},
        _TRACK_2: {'album_name': 'Older Album'},
    }
    embed.assert_called_once_with('album', 'OLD')


def test_top_track_overview_leaves_an_album_blank_when_unresolvable():
    discography = _discography({_TRACK_1: 'spotify:album:GONE'}, {})
    with (
        patch(
            'downtify.spotify._artist_discography', return_value=discography
        ),
        patch(
            'downtify.spotify._fetch_embed_json',
            side_effect=httpx.ConnectError('down'),
        ),
    ):
        assert _top_track_overview('artistId', 'token') == {}


def test_top_track_overview_survives_a_failed_lookup():
    with patch(
        'downtify.spotify._artist_discography',
        side_effect=ValueError('PersistedQueryNotFound'),
    ):
        assert _top_track_overview('artistId', 'token') == {}


def test_top_track_overview_reads_play_counts():
    discography = _discography(
        {
            _TRACK_1: 'spotify:album:AAA',
            _TRACK_2: 'spotify:album:AAA',
            _TRACK_3: 'spotify:album:AAA',
        },
        {'spotify:album:AAA': 'Test Album'},
        # The player sends counts as strings; junk and zero are ignored.
        {_TRACK_1: '1484408385', _TRACK_2: 'n/a', _TRACK_3: 0},
    )
    with patch(
        'downtify.spotify._artist_discography', return_value=discography
    ):
        overview = _top_track_overview('artistId', 'token')
    assert overview[_TRACK_1] == {
        'album_name': 'Test Album',
        'play_count': 1484408385,
    }
    assert overview[_TRACK_2] == {'album_name': 'Test Album'}
    assert overview[_TRACK_3] == {'album_name': 'Test Album'}


def test_artist_top_songs_carry_the_album_name_and_play_count():
    entity = {
        'name': 'Test Artist',
        'trackList': [
            {
                'uri': f'spotify:track:{track_id}',
                'title': f'Song {i}',
                'subtitle': 'Test Artist',
                'duration': 200000,
            }
            for i, track_id in enumerate((_TRACK_1, _TRACK_2, _TRACK_3), 1)
        ],
    }
    payload = _embed_payload_for(entity)
    payload['props']['pageProps']['state']['settings'] = {
        'session': {'accessToken': 'anon-token'}
    }
    with (
        patch('downtify.spotify._fetch_embed_json', return_value=payload),
        patch(
            'downtify.spotify.track_from_id',
            side_effect=lambda tid: {
                'song_id': tid,
                'source': 'spotify',
                'year': '2002',
                'release_date': '2002-06-04',
            },
        ),
        patch(
            'downtify.spotify._top_track_overview',
            return_value={
                _TRACK_1: {'album_name': 'Album One', 'play_count': 1500},
                _TRACK_2: {'album_name': 'Album Two'},
            },
        ) as lookup,
    ):
        _name, _cover, songs = artist_top_songs_from_id('artistId')
    lookup.assert_called_once_with('artistId', 'anon-token')
    assert [s['album_name'] for s in songs] == ['Album One', 'Album Two', '']
    assert [s.get('play_count') for s in songs] == [1500, None, None]


def _release(album_id, name, kind, when):
    year, month, day = when
    return {
        'id': album_id,
        'uri': f'spotify:album:{album_id}',
        'name': name,
        'type': kind,
        'date': {'year': year, 'month': month, 'day': day},
        'coverArt': {
            'sources': [
                {'url': 'https://example.test/small.jpg', 'width': 64},
                {'url': f'https://example.test/{album_id}.jpg', 'width': 640},
            ]
        },
    }


def test_artist_releases_are_deduplicated_and_newest_first():
    older = _release('OLD', 'Older Album', 'ALBUM', (2002, 1, 1))
    newer = _release('NEW', 'Newer Single', 'SINGLE', (2022, 11, 25))
    discography = {
        'topTracks': {
            'items': [
                {
                    'track': {
                        'albumOfTrack': {
                            'uri': 'spotify:album:TOP',
                            'coverArt': {'sources': []},
                        }
                    }
                }
            ]
        },
        'albums': {'items': [{'releases': {'items': [older]}}]},
        'singles': {'items': [{'releases': {'items': [newer]}}]},
        'popularReleasesAlbums': {'items': [older]},
        'latest': newer,
    }
    releases = _artist_releases(discography, 'Test Artist')
    assert [r['album_id'] for r in releases] == ['NEW', 'OLD']
    newest = releases[0]
    assert newest == {
        'album_id': 'NEW',
        'name': 'Newer Single',
        'artists': ['Test Artist'],
        'artist': 'Test Artist',
        'cover_url': 'https://example.test/NEW.jpg',
        'year': '2022',
        'explicit': False,
        'url': 'https://open.spotify.com/album/NEW',
        'source': 'spotify',
        'release_type': 'Single',
    }
    assert releases[1]['release_type'] == 'Album'


def test_artist_releases_label_compilations_and_ignore_track_only_albums():
    discography = {
        'compilations': {
            'items': [
                {
                    'releases': {
                        'items': [
                            _release(
                                'CMP', 'Best Of', 'COMPILATION', (2010, 1, 1)
                            )
                        ]
                    }
                }
            ]
        },
        'albums': {
            'items': [
                {'releases': {'items': [{'uri': 'spotify:album:NONAME'}]}}
            ]
        },
    }
    releases = _artist_releases(discography, 'Test Artist')
    assert [r['album_id'] for r in releases] == ['CMP']
    assert releases[0]['release_type'] == 'Compilation'


def test_artist_releases_keep_ep_upper_case():
    discography = _full_discography(
        _release('EPX', 'A Short One', 'EP', (2003, 1, 1))
    )
    releases = _artist_releases(discography, 'Test Artist')
    assert releases[0]['release_type'] == 'EP'


def _artist_embed_payload(token):
    payload = _embed_payload_for({'name': 'Test Artist'})
    if token:
        payload['props']['pageProps']['state']['settings'] = {
            'session': {'accessToken': token}
        }
    return payload


def _full_discography(*releases):
    return {
        'all': {
            'items': [
                {'releases': {'items': [release]}} for release in releases
            ]
        }
    }


def test_artist_page_lists_the_full_discography():
    full = _full_discography(
        _release('SNG', 'Single', 'SINGLE', (2022, 11, 25)),
        _release('AAA', 'Album', 'ALBUM', (2002, 1, 1)),
    )
    with (
        patch(
            'downtify.spotify._fetch_embed_json',
            return_value=_artist_embed_payload('anon-token'),
        ),
        patch(
            'downtify.spotify._artist_full_discography', return_value=full
        ) as full_lookup,
        patch('downtify.spotify._artist_discography') as overview,
    ):
        name, _cover, releases = artist_page_from_id('artistId')
    full_lookup.assert_called_once_with('artistId', 'anon-token')
    overview.assert_not_called()
    assert name == 'Test Artist'
    assert [r['album_id'] for r in releases] == ['SNG', 'AAA']


def test_artist_page_falls_back_to_the_overview():
    overview = {
        'albums': {
            'items': [
                {
                    'releases': {
                        'items': [
                            _release('AAA', 'Album', 'ALBUM', (2002, 1, 1))
                        ]
                    }
                }
            ]
        }
    }
    with (
        patch(
            'downtify.spotify._fetch_embed_json',
            return_value=_artist_embed_payload('anon-token'),
        ),
        patch(
            'downtify.spotify._artist_full_discography',
            side_effect=ValueError('PersistedQueryNotFound'),
        ),
        patch('downtify.spotify._artist_discography', return_value=overview),
    ):
        _name, _cover, releases = artist_page_from_id('artistId')
    assert [r['album_id'] for r in releases] == ['AAA']


def test_artist_page_has_no_releases_when_every_lookup_fails():
    with (
        patch(
            'downtify.spotify._fetch_embed_json',
            return_value=_artist_embed_payload('anon-token'),
        ),
        patch(
            'downtify.spotify._artist_full_discography',
            side_effect=ValueError('PersistedQueryNotFound'),
        ),
        patch(
            'downtify.spotify._artist_discography',
            side_effect=ValueError('PersistedQueryNotFound'),
        ),
    ):
        name, _cover, releases = artist_page_from_id('artistId')
    assert name == 'Test Artist'
    assert releases == []


def test_artist_page_skips_the_lookups_without_a_token():
    with (
        patch(
            'downtify.spotify._fetch_embed_json',
            return_value=_artist_embed_payload(None),
        ),
        patch('downtify.spotify._artist_full_discography') as full,
        patch('downtify.spotify._artist_discography') as overview,
    ):
        _name, _cover, releases = artist_page_from_id('artistId')
    full.assert_not_called()
    overview.assert_not_called()
    assert releases == []


def _discography_page(count, total, first=0):
    return {
        'artistUnion': {
            'discography': {
                'all': {
                    'totalCount': total,
                    'items': [
                        {'releases': {'items': [{'id': f'R{first + i}'}]}}
                        for i in range(count)
                    ],
                }
            }
        }
    }


def test_full_discography_pages_until_the_total():
    pages = [_discography_page(100, 130), _discography_page(30, 130, 100)]
    with patch('downtify.spotify._partner_query', side_effect=pages) as query:
        result = _artist_full_discography('artistId', 'tok')
    assert len(result['all']['items']) == 130
    offsets = [call.args[1]['offset'] for call in query.call_args_list]
    assert offsets == [0, 100]
    assert all(call.args[1]['limit'] == 100 for call in query.call_args_list)
    assert query.call_args_list[0].args[0] == 'queryArtistDiscographyAll'


def test_full_discography_stops_on_an_empty_page():
    pages = [_discography_page(5, 50), _discography_page(0, 50)]
    with patch('downtify.spotify._partner_query', side_effect=pages):
        result = _artist_full_discography('artistId', 'tok')
    assert len(result['all']['items']) == 5
