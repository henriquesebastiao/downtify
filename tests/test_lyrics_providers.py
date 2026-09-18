"""The lyrics provider chain: order, fallback, the lookup cache, and the
NetEase provider's matching and LRC parsing."""

from __future__ import annotations

import pytest

from downtify import lyrics
from downtify.lyrics import Lyrics
from downtify.lyrics_cache import LyricsLookupCache, song_key

SONG = {
    'song_id': '4cOdK2wGLETKBW3PvgPWqT',
    'name': 'Never Gonna Give You Up',
    'artists': ['Rick Astley'],
    'album_name': 'Whenever You Need Somebody',
    'duration': 213,
}


@pytest.fixture
def calls(monkeypatch):
    """Records which providers were asked, with scripted answers."""
    asked: list[str] = []
    answers: dict[str, object] = {}

    def make(name):
        def _fetch(song):
            asked.append(name)
            answer = answers.get(name)
            if isinstance(answer, Exception):
                raise answer
            return answer

        return _fetch

    monkeypatch.setattr(
        lyrics,
        '_PROVIDER_FNS',
        {name: make(name) for name in lyrics.PROVIDER_ORDER},
    )
    return asked, answers


# ── fetch ────────────────────────────────────────────────────────────


def test_first_provider_wins(calls):
    asked, answers = calls
    answers['lrclib'] = Lyrics(plain='words')
    assert lyrics.fetch(SONG, ['lrclib', 'netease']).plain == 'words'
    assert asked == ['lrclib']


def test_falls_through_to_the_next_provider(calls):
    asked, answers = calls
    answers['lrclib'] = None
    answers['netease'] = Lyrics(synced='[00:01.00]words')
    assert lyrics.fetch(SONG, ['lrclib', 'netease']).synced
    assert asked == ['lrclib', 'netease']


def test_order_is_the_users(calls):
    asked, answers = calls
    answers['netease'] = Lyrics(plain='words')
    lyrics.fetch(SONG, ['netease', 'lrclib'])
    assert asked == ['netease']


def test_empty_result_is_not_a_hit(calls):
    asked, answers = calls
    answers['lrclib'] = Lyrics()
    answers['netease'] = None
    assert lyrics.fetch(SONG, ['lrclib', 'netease']) is None
    assert asked == ['lrclib', 'netease']


def test_a_failing_provider_does_not_stop_the_chain(calls):
    asked, answers = calls
    answers['lrclib'] = RuntimeError('boom')
    answers['netease'] = Lyrics(plain='words')
    assert lyrics.fetch(SONG, ['lrclib', 'netease']).plain == 'words'
    assert asked == ['lrclib', 'netease']


def test_unknown_providers_are_skipped(calls):
    asked, answers = calls
    answers['lrclib'] = Lyrics(plain='words')
    lyrics.fetch(SONG, ['genius', 'musixmatch', 'lrclib'])
    assert asked == ['lrclib']


# ── lookup cache ─────────────────────────────────────────────────────


def test_cache_skips_a_provider_that_had_nothing(calls, tmp_path):
    asked, answers = calls
    cache = LyricsLookupCache(tmp_path / 'lyrics.db')
    answers['lrclib'] = None
    answers['netease'] = Lyrics(plain='words')

    assert lyrics.fetch(SONG, ['lrclib', 'netease'], cache).plain == 'words'
    assert asked == ['lrclib', 'netease']

    asked.clear()
    assert lyrics.fetch(SONG, ['lrclib', 'netease'], cache).plain == 'words'
    # lrclib is not asked again; the hit is not cached away.
    assert asked == ['netease']


def test_cache_retries_after_the_ttl(calls, tmp_path):
    asked, answers = calls
    cache = LyricsLookupCache(tmp_path / 'lyrics.db', miss_ttl_days=0)
    answers['lrclib'] = None
    lyrics.fetch(SONG, ['lrclib'], cache)
    asked.clear()
    lyrics.fetch(SONG, ['lrclib'], cache)
    assert asked == ['lrclib']


def test_cache_can_forget_a_song(calls, tmp_path):
    asked, answers = calls
    cache = LyricsLookupCache(tmp_path / 'lyrics.db')
    answers['lrclib'] = None
    lyrics.fetch(SONG, ['lrclib'], cache)
    assert cache.forget(song_key(SONG)) == 1
    asked.clear()
    lyrics.fetch(SONG, ['lrclib'], cache)
    assert asked == ['lrclib']
    assert cache.clear() == 1


def test_cache_is_per_song_and_per_provider(tmp_path):
    cache = LyricsLookupCache(tmp_path / 'lyrics.db')
    cache.record(song_key(SONG), 'lrclib', found=False)
    assert cache.should_skip(song_key(SONG), 'lrclib') is True
    assert cache.should_skip(song_key(SONG), 'netease') is False
    other = song_key({'name': 'Other', 'artists': ['Someone']})
    assert cache.should_skip(other, 'lrclib') is False


def test_song_key_prefers_the_track_id():
    assert song_key(SONG) == 'id:4cOdK2wGLETKBW3PvgPWqT'
    assert song_key({'name': 'Título', 'artists': ['Ana Luz']}) == (
        'text:ana luz|título'
    )
    # Same song written differently gets the same key.
    assert song_key({'name': ' TÍTULO ', 'artists': [' Ana Luz ']}) == (
        'text:ana luz|título'
    )
    assert not song_key({'artists': ['Ana']})


def test_cache_ignores_songs_without_a_key(tmp_path):
    cache = LyricsLookupCache(tmp_path / 'lyrics.db')
    cache.record('', 'lrclib', found=False)
    assert cache.should_skip('', 'lrclib') is False
    assert cache.forget('') == 0


# ── NetEase ──────────────────────────────────────────────────────────

LRC = (
    '[00:00.000] 作词 : Stock Aitken Waterman\n'
    '[00:01.000] 作曲 : Stock Aitken Waterman\n'
    '[00:18.684]We are no strangers to love\n'
    '\n'
    '[00:22.657]You know the rules and so do I\n'
)


def _netease(monkeypatch, songs, lyric):
    seen = {}

    def _get(path, params):
        seen[path] = params
        return songs if path.endswith('/search/get') else lyric

    monkeypatch.setattr(lyrics, '_netease_get', _get)
    return seen


def _hit(**overrides):
    song = {
        'id': 18520488,
        'name': 'Never Gonna Give You Up',
        'artists': [{'name': 'Rick Astley'}],
        'duration': 214018,
    }
    song.update(overrides)
    return song


def test_netease_returns_synced_and_plain(monkeypatch):
    seen = _netease(
        monkeypatch,
        {'result': {'songs': [_hit()]}},
        {'lrc': {'lyric': LRC}},
    )
    result = lyrics._fetch_netease(SONG)
    assert result.synced.splitlines() == [
        '[00:18.684]We are no strangers to love',
        '[00:22.657]You know the rules and so do I',
    ]
    assert result.plain.splitlines() == [
        'We are no strangers to love',
        'You know the rules and so do I',
    ]
    assert seen['/search/get']['s'] == 'Rick Astley Never Gonna Give You Up'
    assert seen['/song/lyric']['id'] == 18520488


def test_netease_picks_the_closest_match(monkeypatch):
    monkeypatch.setattr(
        lyrics,
        '_netease_get',
        lambda path, params: (
            {
                'result': {
                    'songs': [
                        _hit(id=1, name='Never Gonna Give You Up (Live)'),
                        _hit(id=2),
                    ]
                }
            }
            if path.endswith('/search/get')
            else {'lrc': {'lyric': f'[00:01.00]id {params["id"]}'}}
        ),
    )
    assert 'id 2' in lyrics._fetch_netease(SONG).plain


@pytest.mark.parametrize(
    'hit',
    [
        _hit(name='Something Else'),
        _hit(duration=400000),
        # Another artist, and the length doesn't vouch for it either.
        _hit(artists=[{'name': 'Another Artist'}], duration=222000),
    ],
)
def test_netease_rejects_a_wrong_match(monkeypatch, hit):
    _netease(
        monkeypatch, {'result': {'songs': [hit]}}, {'lrc': {'lyric': LRC}}
    )
    assert lyrics._fetch_netease(SONG) is None


def test_netease_needs_the_artist_when_the_length_is_unknown(monkeypatch):
    _netease(
        monkeypatch,
        {'result': {'songs': [_hit(artists=[{'name': 'Someone Else'}])]}},
        {'lrc': {'lyric': LRC}},
    )
    assert lyrics._fetch_netease({**SONG, 'duration': 0}) is None


def test_netease_accepts_a_differently_written_artist(monkeypatch):
    """Traditional/simplified spellings differ across services; an exact
    title and a matching length are enough."""
    _netease(
        monkeypatch,
        {
            'result': {
                'songs': [
                    _hit(
                        name='起风了',
                        artists=[{'name': '冯沁苑(买辣椒也用券)'}],
                        duration=325000,
                    )
                ]
            }
        },
        {'lrc': {'lyric': LRC}},
    )
    song = {
        'name': '起风了（The Wind）',
        'artists': ['馮沁苑LaJiao'],
        'duration': 326,
    }
    assert lyrics._fetch_netease(song).plain


def test_netease_handles_empty_and_instrumental(monkeypatch):
    for lyric in (
        {'lrc': {'lyric': ''}},
        {'nolyric': True},
        {'uncollected': True},
        {'lrc': {'lyric': '[00:00.000]纯音乐，请欣赏'}},
        None,
    ):
        _netease(monkeypatch, {'result': {'songs': [_hit()]}}, lyric)
        assert lyrics._fetch_netease(SONG) is None


def test_netease_handles_no_results(monkeypatch):
    _netease(monkeypatch, {'result': {'songs': []}}, None)
    assert lyrics._fetch_netease(SONG) is None
    _netease(monkeypatch, None, None)
    assert lyrics._fetch_netease(SONG) is None
    assert lyrics._fetch_netease({'artists': ['x']}) is None


def test_netease_matches_without_a_known_duration(monkeypatch):
    _netease(
        monkeypatch,
        {'result': {'songs': [_hit(duration=0)]}},
        {'lrc': {'lyric': LRC}},
    )
    assert lyrics._fetch_netease({**SONG, 'duration': 0}).plain
