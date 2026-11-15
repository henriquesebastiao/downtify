from datetime import datetime

import pytest
from ai_test_support import opted_in_store

from downtify.music_ai import covers
from downtify.music_ai.playlists import (
    PARIS,
    WEEKLY_SIZE,
    generate,
    genre_rows,
    themes,
)
from downtify.music_ai.store import GENRE_THEMES, MOODS, Store


def vector(axis=0):
    result = [0.0] * 512
    result[axis] = 1.0
    return result


def rows(count, genre='Rap'):
    return [
        {
            'id': f'{genre}-{i}',
            'artist': f'artist-{i}',
            'genre': genre,
        }
        for i in range(count)
    ]


@pytest.fixture
def store(tmp_path):
    database = opted_in_store(tmp_path / 'derived.db')
    data = rows(60)
    database.observe([
        {**row, 'fingerprint': 'f-' + row['id']} for row in data
    ])
    for row in data:
        database.put_analysis(row['id'], 'f-' + row['id'], 'm', vector())
    for mood in MOODS:
        with database.connect() as db:
            db.execute(
                'INSERT OR REPLACE INTO mood_vectors VALUES (?,?,?)',
                (mood, 'm', Store.pack(vector())),
            )
    return database


NOW = datetime(2026, 11, 12, 10, tzinfo=PARIS)


def test_daily_keeps_six_moods_and_weekly_includes_pop():
    assert len(themes('daily')) == 6
    assert set(themes('daily')).isdisjoint(GENRE_THEMES)
    assert len(themes('weekly')) == 10
    assert set(GENRE_THEMES) <= set(themes('weekly'))
    with pytest.raises(ValueError):
        themes('monthly')


def test_weekly_sets_hold_twenty_five_distinct_titles(store):
    result = generate(store, 1, 'weekly', 'calme', rows(60), 'm', now=NOW)
    ids = [row['id'] for row in result]
    assert len(ids) == WEEKLY_SIZE
    assert len(set(ids)) == WEEKLY_SIZE


def test_genre_theme_never_falls_back_to_another_style(store):
    data = rows(30, 'Rap') + rows(30, 'Jazz')
    rap = generate(store, 1, 'weekly', 'rap', data, 'm', now=NOW)
    assert len(rap) == WEEKLY_SIZE
    assert {row['id'].split('-')[0] for row in rap} == {'Rap'}
    assert genre_rows('rock', data) == []
    with pytest.raises(RuntimeError):
        generate(store, 1, 'weekly', 'rock', data, 'm', now=NOW)


def test_cover_url_is_exposed_and_stable(store):
    generate(store, 1, 'daily', 'calme', rows(60), 'm', now=NOW)
    from downtify.music_ai.playlists import period, summaries

    result = summaries(store, 1, rows(60), now=NOW)
    card = next(item for item in result if item['cadence'] == 'daily')
    assert card['cover_url'] == (
        '/api/v1/music-ai/playlists/daily/calme'
        f'/cover.svg?period={period("daily", NOW)}'
    )


def test_cover_is_deterministic_and_period_bound():
    key = '1:weekly:rock:2026-11-09'
    first = covers.svg(key, 'rock')
    assert first == covers.svg(key, 'rock')
    assert first != covers.svg('1:weekly:rock:2026-11-16', 'rock')
    assert first != covers.svg('1:weekly:rap:2026-11-09', 'rock')
    assert first.startswith('<svg')
    assert first.endswith('</svg>')
    assert len(first) < 4096


def test_pop_is_a_real_genre_filter():
    rows = [
        {'id': 'pop', 'genre': 'Synth-Pop'},
        {'id': 'rap', 'genre': 'Rap'},
        {'id': 'none', 'genre': ''},
    ]
    assert [row['id'] for row in genre_rows('pop', rows)] == ['pop']
