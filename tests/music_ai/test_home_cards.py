import json
from datetime import datetime, timedelta

from downtify.music_ai import playlists, routes
from downtify.music_ai.playlists import PARIS, period, stored_selections


def test_four_daily_cards_have_stable_order_and_etag_without_full_catalog(
    client, monkeypatch
):
    http, database = client
    monkeypatch.setattr(
        routes,
        'catalog',
        lambda *_: (_ for _ in ()).throw(
            AssertionError('Home must not read the catalog')
        ),
    )
    monkeypatch.setattr(
        routes,
        'visible_rows',
        lambda request, ids: (
            [{'id': 'one', 'file': 'one.mp3'}] if 'one' in ids else []
        ),
    )
    with database.connect() as db:
        db.execute(
            'INSERT INTO playlists VALUES (?,?,?,?,?,?)',
            (
                1,
                'daily',
                'calme',
                period('daily'),
                json.dumps(['one', 'hidden']),
                10,
            ),
        )
    first = http.get('/api/v1/music-ai/home', headers={'x-test-user': '1'})
    assert first.status_code == 200
    cards = first.json()['cards']
    assert [item.get('title') for item in cards] == [
        'Détente',
        'Concentration',
        'Motivation',
        'Calme',
        None,
        None,
        None,
        None,
    ]
    assert [item['count'] for item in cards] == [0, 0, 0, 1, 0, 0, 0, 0]
    assert cards[3]['cover_track_ids'] == ['one']
    assert 'hidden' not in first.text
    assert 'one.mp3' not in first.text
    assert (
        http.get(
            '/api/v1/music-ai/home',
            headers={
                'x-test-user': '1',
                'if-none-match': first.headers['etag'],
            },
        ).status_code
        == 304
    )
    second = http.get(
        '/api/v1/music-ai/home',
        headers={'x-test-user': '2', 'if-none-match': first.headers['etag']},
    )
    assert second.status_code == 200
    assert all(item['count'] == 0 for item in second.json()['cards'])


def test_disabled_home_is_empty_without_catalog_or_generation(
    client, monkeypatch
):
    http, database = client
    database.set_preferences(
        1, {'daily': False, 'weekly': False, 'personalization': False}
    )
    monkeypatch.setattr(
        routes,
        'visible_rows',
        lambda *a: (_ for _ in ()).throw(
            AssertionError('Disabled means no reads')
        ),
    )
    assert http.get(
        '/api/v1/music-ai/home', headers={'x-test-user': '1'}
    ).json() == {'cards': []}


def test_opening_an_ungenerated_mood_is_a_cheap_pending_read(
    client, monkeypatch
):
    http, _ = client
    monkeypatch.setattr(
        playlists,
        'generate',
        lambda *a: (_ for _ in ()).throw(
            AssertionError('Never generate in HTTP')
        ),
    )
    result = http.get(
        '/api/v1/music-ai/playlists/daily/detente',
        headers={'x-test-user': '1'},
    )
    assert result.status_code == 200
    assert result.json()['state'] == 'preparing'
    assert result.json()['tracks'] == []


def test_yesterday_mix_stays_visible_until_today_is_ready(client, monkeypatch):
    http, database = client
    monkeypatch.setattr(
        routes,
        'visible_rows',
        lambda request, ids: (
            [{'id': 'one', 'file': 'one.mp3'}] if 'one' in ids else []
        ),
    )
    yesterday = period('daily', datetime.now(PARIS) - timedelta(days=1))
    with database.connect() as db:
        db.execute(
            'INSERT INTO playlists VALUES (?,?,?,?,?,?)',
            (1, 'daily', 'calme', yesterday, json.dumps(['one']), 10),
        )
    cards = http.get(
        '/api/v1/music-ai/home', headers={'x-test-user': '1'}
    ).json()['cards']
    calme = next(item for item in cards if item['mood'] == 'calme')
    assert calme['count'] == 1
    assert calme['period'] == yesterday
    assert calme['state'] == 'previous'


def test_daily_selection_falls_back_to_the_previous_period(client):
    _, database = client
    yesterday = period('daily', datetime.now(PARIS) - timedelta(days=1))
    with database.connect() as db:
        db.execute(
            'INSERT INTO playlists VALUES (?,?,?,?,?,?)',
            (1, 'daily', 'calme', yesterday, json.dumps(['one']), 10),
        )
    chosen = stored_selections(database, 1)
    assert [
        (item['cadence'], item['mood'], item['period']) for item in chosen
    ] == [('daily', 'calme', yesterday)]
    assert chosen[0]['ids'] == ['one']


def test_weekly_genres_are_on_home_and_open_without_generation(
    client, monkeypatch
):
    http, database = client
    database.set_preferences(1, {'daily': False, 'weekly': True})
    monkeypatch.setattr(
        routes,
        'catalog',
        lambda *_: (_ for _ in ()).throw(
            AssertionError('Home must not scan the catalog')
        ),
    )
    monkeypatch.setattr(
        routes,
        'visible_rows',
        lambda request, ids: (
            [{'id': 'one', 'file': 'safe-one.mp3'}] if 'one' in ids else []
        ),
    )
    with database.connect() as db:
        db.execute(
            'INSERT INTO playlists VALUES (?,?,?,?,?,?)',
            (
                1,
                'weekly',
                'rock',
                period('weekly'),
                json.dumps(['one', 'hidden']),
                10,
            ),
        )
    home = http.get('/api/v1/music-ai/home', headers={'x-test-user': '1'})
    assert home.status_code == 200
    genres = [
        card for card in home.json()['cards'] if card['cadence'] == 'weekly'
    ]
    assert {card['mood'] for card in genres} == {
        'rock',
        'rap',
        'pop',
        'electro',
    }
    rock = next(card for card in genres if card['mood'] == 'rock')
    assert rock['count'] == 1
    assert 'hidden' not in home.text
    opened = http.get(
        '/api/v1/music-ai/playlists/weekly/rock', headers={'x-test-user': '1'}
    )
    assert opened.status_code == 200
    assert [row['id'] for row in opened.json()['tracks']] == ['one']
    other = http.get(
        '/api/v1/music-ai/playlists/weekly/rock', headers={'x-test-user': '2'}
    )
    assert other.json()['tracks'] == []
    database.set_preferences(1, {'daily': True})
    for genre in ('rock', 'rap', 'pop', 'electro'):
        assert (
            http.get(
                f'/api/v1/music-ai/playlists/weekly/{genre}/cover.svg',
                headers={'x-test-user': '1'},
            ).status_code
            == 200
        )
        assert (
            http.get(
                f'/api/v1/music-ai/playlists/daily/{genre}',
                headers={'x-test-user': '1'},
            ).status_code
            == 404
        )
