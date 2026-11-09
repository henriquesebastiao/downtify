import json

from downtify.music_ai import playlists, routes
from downtify.music_ai.playlists import period


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
    assert [item['title'] for item in cards] == [
        'Détente',
        'Concentration',
        'Motivation',
        'Calme',
    ]
    assert [item['count'] for item in cards] == [0, 0, 0, 1]
    assert cards[-1]['cover_track_ids'] == ['one']
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
