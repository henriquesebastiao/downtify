"""Where to buy a song, album or artist, to support them (#429).

See ``downtify/buy_links.py`` and ``downtify.itunes.store_match``. The
iTunes Search API is never called: its answers are recorded below.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi import HTTPException

from downtify import api, artist_profile, itunes
from downtify.auth import ADMIN, CLIENT, classify
from downtify.buy_links import (
    buy_links,
    kind_of,
    normalize_country,
    website_url,
)

SONG = {
    'wrapperType': 'track',
    'kind': 'song',
    'artistName': 'Portishead',
    'trackName': 'Roads',
    'collectionName': 'Dummy',
    'trackViewUrl': 'https://music.apple.com/br/album/roads/1?i=2&uo=4',
    'trackPrice': 2.9,
    'currency': 'BRL',
}
COVER = {
    **SONG,
    'artistName': 'Some Tribute Band',
    'trackViewUrl': 'https://music.apple.com/br/album/roads/9?i=9&uo=4',
}
ALBUM = {
    'wrapperType': 'collection',
    'collectionType': 'Album',
    'artistName': 'Portishead',
    'collectionName': 'Dummy',
    'collectionViewUrl': 'https://music.apple.com/us/album/dummy/1?uo=4',
    'collectionPrice': 9.99,
    'currency': 'USD',
}
ARTIST = {
    'wrapperType': 'artist',
    'artistName': 'Portishead',
    'artistLinkUrl': 'https://music.apple.com/us/artist/portishead/8?uo=4',
}


@pytest.fixture
def itunes_answers(monkeypatch):
    """Record what is asked; answer from ``answers[entity]``."""

    asked: list[dict[str, Any]] = []
    answers: dict[str, list[dict[str, Any]]] = {}

    def search(query, limit=5, *, entity='song', country=''):
        asked.append({'query': query, 'entity': entity, 'country': country})
        return list(answers.get(entity, []))

    monkeypatch.setattr(itunes, '_search_itunes', search)
    monkeypatch.setattr(itunes, '_store_cache', {})
    return answers, asked


# ── The iTunes Store lookup ─────────────────────────────────────────────


def test_a_song_is_found_with_its_price(itunes_answers):
    answers, asked = itunes_answers
    answers['song'] = [COVER, SONG]

    found = itunes.store_match('track', 'Portishead', 'Roads', country='BR')

    assert found == {
        'url': SONG['trackViewUrl'],
        'price': 2.9,
        'currency': 'BRL',
    }
    assert asked == [
        {'query': 'Portishead Roads', 'entity': 'song', 'country': 'BR'}
    ]


def test_someone_elses_recording_is_never_offered(itunes_answers):
    answers, asked = itunes_answers
    answers['song'] = [COVER]

    assert itunes.store_match('track', 'Portishead', 'Roads') is None
    # The miss is remembered: no second request for the same song.
    assert itunes.store_match('track', 'Portishead', 'Roads') is None
    assert len(asked) == 1


def test_an_empty_or_failed_answer_is_asked_again(itunes_answers):
    _answers, asked = itunes_answers

    assert itunes.store_match('track', 'Portishead', 'Roads') is None
    assert itunes.store_match('track', 'Portishead', 'Roads') is None
    assert len(asked) == 2


def test_a_song_sold_only_with_its_album_has_no_price(itunes_answers):
    answers, _asked = itunes_answers
    answers['song'] = [{**SONG, 'trackPrice': -1}]

    found = itunes.store_match('track', 'Portishead', 'Roads')

    assert found == {
        'url': SONG['trackViewUrl'],
        'price': None,
        'currency': '',
    }


def test_albums_and_artists_are_looked_up_too(itunes_answers):
    answers, asked = itunes_answers
    answers['album'] = [ALBUM]
    answers['musicArtist'] = [ARTIST]

    album = itunes.store_match('album', 'Portishead', album='Dummy')
    artist = itunes.store_match('artist', 'Portishead')

    assert album == {
        'url': ALBUM['collectionViewUrl'],
        'price': 9.99,
        'currency': 'USD',
    }
    assert artist == {
        'url': ARTIST['artistLinkUrl'],
        'price': None,
        'currency': '',
    }
    assert [a['entity'] for a in asked] == ['album', 'musicArtist']
    assert itunes.store_match('album', 'Portishead') is None
    assert itunes.store_match('playlist', 'Portishead') is None


def test_a_link_that_is_not_https_is_dropped(itunes_answers):
    answers, _asked = itunes_answers
    answers['song'] = [{**SONG, 'trackViewUrl': 'javascript:alert(1)'}]

    assert itunes.store_match('track', 'Portishead', 'Roads') is None


# ── The links ───────────────────────────────────────────────────────────


def _found(*_args, **_kwargs):
    return {
        'url': 'https://music.apple.com/x',
        'price': 1.29,
        'currency': 'USD',
    }


def test_a_song_gets_the_store_item_and_searches():
    result = buy_links(
        'Portishead', 'Roads', 'Dummy', country='br', lookup=_found
    )

    assert result['kind'] == 'track'
    assert result['query'] == 'Portishead Roads'
    by_store = {link['store']: link for link in result['links']}
    assert list(by_store) == ['itunes', 'bandcamp', 'qobuz']
    assert by_store['itunes'] == {
        'store': 'itunes',
        'label': 'iTunes Store',
        'url': 'https://music.apple.com/x',
        'match': True,
        'price': 1.29,
        'currency': 'USD',
    }
    assert by_store['bandcamp']['url'] == (
        'https://bandcamp.com/search?q=Portishead+Roads&item_type=t'
    )
    assert by_store['qobuz']['url'] == (
        'https://www.qobuz.com/us-en/search/tracks/Portishead%20Roads'
    )
    assert not by_store['bandcamp']['match']


def test_without_a_store_item_the_store_is_searched():
    asked = []

    def lookup(*args):
        asked.append(args)

    result = buy_links('AC/DC', album='Back in Black', lookup=lookup)

    assert asked == [('album', 'AC/DC', '', 'Back in Black', 'US')]
    itunes_link, bandcamp, qobuz = result['links']
    assert itunes_link['match'] is False
    assert itunes_link['url'] == (
        'https://music.apple.com/us/search?term=AC%2FDC+Back+in+Black'
    )
    assert bandcamp['url'].endswith('item_type=a')
    assert qobuz['url'] == (
        'https://www.qobuz.com/us-en/search/albums/AC%2FDC%20Back%20in%20Black'
    )


def test_a_failing_lookup_still_gives_links():
    def broken(*_args):
        raise RuntimeError('offline')

    result = buy_links('Portishead', lookup=broken)

    assert result['kind'] == 'artist'
    assert [link['store'] for link in result['links']] == [
        'itunes',
        'bandcamp',
        'qobuz',
    ]
    assert result['links'][1]['url'].endswith('item_type=b')


def test_the_artists_website_comes_last():
    result = buy_links(
        'Portishead',
        'Roads',
        lookup=lambda *_a: None,
        website='portishead.co.uk',
    )

    website = result['links'][-1]
    assert website['store'] == 'website'
    assert website['url'] == 'https://portishead.co.uk'
    assert website['match'] is True


@pytest.mark.parametrize(
    ('raw', 'url'),
    [
        ('https://example.com/a', 'https://example.com/a'),
        ('HTTP://example.com', 'HTTP://example.com'),
        ('example.com', 'https://example.com'),
        ('javascript:alert(1)', ''),
        ('mailto:a@b.c', ''),
        ('two words', ''),
        ('', ''),
        (None, ''),
    ],
)
def test_website_url(raw, url):
    assert website_url(raw) == url


def test_country_and_kind():
    assert normalize_country('br') == 'BR'
    assert normalize_country('') == 'US'
    assert normalize_country('BRA') == 'US'
    assert normalize_country('1x') == 'US'
    assert kind_of('Roads', 'Dummy') == 'track'
    assert kind_of('', 'Dummy') == 'album'
    assert kind_of('', '') == 'artist'


# ── The endpoint ────────────────────────────────────────────────────────


def test_the_endpoint_adds_the_website_from_the_saved_profile(
    tmp_path, monkeypatch, itunes_answers
):
    answers, asked = itunes_answers
    answers['song'] = [SONG]
    monkeypatch.setattr(api, '_artist_profile_download_dir', lambda: tmp_path)
    artist_profile.save_social(
        tmp_path, 'Portishead', {'website': 'https://portishead.co.uk'}
    )

    result = asyncio.run(
        api.buy_links_endpoint(
            artist=' Portishead ', title='Roads', album='', country='br'
        )
    )

    assert result['links'][0]['url'] == SONG['trackViewUrl']
    assert result['links'][-1]['url'] == 'https://portishead.co.uk'
    assert asked[0]['country'] == 'BR'
    # An artist without a saved profile simply has no website link.
    other = asyncio.run(
        api.buy_links_endpoint(artist='Nobody', title='', album='', country='')
    )
    assert [link['store'] for link in other['links']] == [
        'itunes',
        'bandcamp',
        'qobuz',
    ]


def test_the_endpoint_needs_an_artist():
    with pytest.raises(HTTPException) as missing:
        asyncio.run(
            api.buy_links_endpoint(
                artist=' ', title='Roads', album='', country=''
            )
        )
    assert missing.value.status_code == 400


def test_apps_may_ask_for_buy_links():
    assert classify('GET', '/api/buy') == CLIENT
    assert classify('POST', '/api/buy') == ADMIN
