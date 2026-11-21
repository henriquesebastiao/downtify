"""slskd finds the songs Nicotine+ finds.

Soulseek peers match whole words of a shared path, split at punctuation,
so ``Thats`` (an apostrophe dropped) or ``(feat.`` match nothing. And a
shared file rarely carries Spotify's ``(feat. …)`` / ``(from …)`` credits
the same way, its accents, or the "The" in front of a band's name. All
of these sent songs that were on Soulseek to YouTube.
"""

from __future__ import annotations

from typing import Any

import pytest

from downtify import slskd_provider as sp

THATS_IT = {
    'name': "That's It (feat. Future & Metro Boomin)",
    'artists': ['Yung Lean', 'Metro Boomin', 'Future'],
    'album_name': 'Grand Theft Auto VI: The Album',
    'duration': 161,
}


def _rank(song: dict[str, Any], filename: str, length: int) -> list[Any]:
    response = {
        'username': 'peer',
        'hasFreeUploadSlot': True,
        'fileCount': 1,
        'files': [{'filename': filename, 'length': length, 'bitRate': 320}],
    }
    return sp._rank_slskd_candidates(song, [response])


def test_queries_are_words_a_peer_can_match() -> None:
    queries = sp._slskd_search_queries(THATS_IT)
    assert queries[0] == 'Yung Lean That s It'
    assert 'Yung Lean Thats It' in queries
    assert 'That s It' in queries
    for query in queries:
        assert not set("'()&.-:") & set(query)


def test_accent_free_query_is_tried_too() -> None:
    queries = sp._slskd_search_queries({
        'name': 'Tití Me Preguntó',
        'artists': ['Bad Bunny'],
    })
    assert queries[0] == 'Bad Bunny Tití Me Preguntó'
    assert 'Bad Bunny Titi Me Pregunto' in queries


@pytest.mark.parametrize(
    'filename',
    [
        r"music\Yung Lean - That's It (feat. Future & Metro Boomin).mp3",
        r"music\Yung Lean - That's It.mp3",
        r"music\Yung Lean - That's It (feat. Future and Metro Boomin).mp3",
        r"music\Yung Lean - That's It ft. Future, Metro Boomin.mp3",
        r"X\Yung Lean feat. Future & Metro Boomin - That's It (from GTAVI The Album).mp3",
        r"Yung Lean\GTA VI\02 That's It.mp3",
        r"music\Metro Boomin - That's It.mp3",
    ],
)
def test_the_song_is_found_however_the_file_credits_it(filename: str) -> None:
    assert _rank(THATS_IT, filename, 161)


@pytest.mark.parametrize(
    ('filename', 'length'),
    [
        (r"music\Drake - That's It.mp3", 161),
        (r"music\Yung Lean - That's It (Remix).mp3", 161),
        (r"music\Yung Lean - That's It (Live).mp3", 161),
        (r"music\Yung Lean - That's It (Instrumental).mp3", 161),
        (r"music\Yung Lean - That's It.mp3", 230),
        (r'music\Yung Lean - Ginseng Strip 2002.mp3', 161),
        (r"Grand Theft Auto VI\Various\02 That's It.mp3", 161),
    ],
)
def test_another_song_or_version_is_still_refused(
    filename: str, length: int
) -> None:
    assert not _rank(THATS_IT, filename, length)


def test_a_file_without_accents_matches() -> None:
    song = {
        'name': 'Tití Me Preguntó',
        'artists': ['Bad Bunny'],
        'duration': 243,
    }
    assert _rank(song, r'a\Bad Bunny - Titi Me Pregunto.mp3', 243)


def test_the_is_optional_in_front_of_a_band() -> None:
    song = {
        'name': 'Mr. Brightside',
        'artists': ['The Killers'],
        'duration': 222,
    }
    with_the = _rank(song, r'a\The Killers - Mr Brightside.mp3', 222)
    without = _rank(song, r'a\Killers - Mr. Brightside.mp3', 222)
    assert with_the
    assert without
    assert with_the[0]['match_score'] == without[0]['match_score']


def test_core_title() -> None:
    assert sp._core_title(THATS_IT['name']) == "That's It"
    assert (
        sp._core_title('Last Thing You Need (from GTAVI: The Album)')
        == 'Last Thing You Need'
    )
    assert sp._core_title('Dreams - 2004 Remaster') == 'Dreams'
    assert sp._core_title('Song (Remix)') == 'Song (Remix)'
    assert sp._core_title('(feat. Nobody)') == '(feat. Nobody)'


# ── searches the server answers nothing to ─────────────────────────
def test_loosened_searches_drop_one_word_filler_first() -> None:
    song = {
        'name': 'Starting From Zero (feat. Michael McDonald)',
        'artists': ['Justice'],
    }
    tried = sp._slskd_search_queries(song)
    loosened = sp._blocked_phrase_queries(song, tried)
    assert loosened[0] == 'Justice Starting Zero'
    assert len(loosened) == sp._BLOCKED_PHRASE_TRIES
    assert not set(loosened) & set(tried)


def test_loosened_searches_get_past_a_blocked_artist_name() -> None:
    song = {'name': 'Nights', 'artists': ['Frank Ocean']}
    loosened = sp._blocked_phrase_queries(song, sp._slskd_search_queries(song))
    assert 'Ocean Nights' in loosened
    assert 'Frank Nights' in loosened


def test_two_word_searches_are_not_loosened() -> None:
    song = {'name': 'Light', 'artists': ['Tom']}
    assert not sp._blocked_phrase_queries(song, ['Tom Light'])


class _Searches:
    """A slskd that answers only the searches in *answers*."""

    base_url = 'https://slskd.example'

    def __init__(self, answers: dict[str, list[dict[str, Any]]]):
        self.answers = answers
        self.asked: list[str] = []
        self._last = ''

    @staticmethod
    def configured() -> bool:
        return True

    @staticmethod
    def can_connect() -> bool:
        return True

    def start_search(self, query: str) -> str:
        self.asked.append(query)
        self._last = query
        return 'id'

    @staticmethod
    def wait_search_complete(*args: Any, **kwargs: Any) -> bool:
        return True

    def search_responses(self, search_id: str) -> list[dict[str, Any]]:
        return self.answers.get(self._last, [])

    @staticmethod
    def delete_search(search_id: str) -> None:
        return None


ZERO = {
    'name': 'Starting From Zero (feat. Michael McDonald)',
    'artists': ['Justice'],
    'duration': 189,
}


def _run(monkeypatch, answers: dict[str, list[dict[str, Any]]]) -> list[str]:
    fake = _Searches(answers)
    monkeypatch.setattr(sp, 'SlskdClient', lambda settings: fake)
    sp.download_from_slskd(ZERO, {'enabled': True, 'base_url': 'x'})
    return fake.asked


def test_nobody_answering_any_search_adds_loosened_ones(monkeypatch) -> None:
    asked = _run(monkeypatch, {})
    normal = sp._slskd_search_queries(ZERO)
    assert asked[: len(normal)] == normal
    assert asked[len(normal) :] == sp._blocked_phrase_queries(ZERO, normal)


def test_an_answered_search_is_not_loosened(monkeypatch) -> None:
    peer = {
        'username': 'peer',
        'hasFreeUploadSlot': True,
        'fileCount': 1,
        'files': [{'filename': r'x\Other - Song.mp3', 'length': 100}],
    }
    asked = _run(monkeypatch, {'Starting From Zero': [peer]})
    assert asked == sp._slskd_search_queries(ZERO)
