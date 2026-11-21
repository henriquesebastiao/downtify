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
from downtify import track_tag_match

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
    assert len(loosened) == sp._BLOCKED_PHRASE_TRIES + sp._BLOCKED_PAIR_TRIES
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


# ── harder names and titles ────────────────────────────────────────
def _accepts(song: dict[str, Any], filename: str) -> bool:
    return bool(_rank(song, filename, int(song['duration'])))


@pytest.mark.parametrize(
    ('artist', 'title', 'filename'),
    [
        ('P!nk', 'So What', r'Pink - Funhouse\02 - So What.mp3'),
        ('$uicideboy$', 'Carrollton', r'Suicideboys - Carrollton.mp3'),
        ('AC/DC', 'Back In Black', r'ACDC - Back In Black.mp3'),
        (
            'N.W.A.',
            'Straight Outta Compton',
            r'NWA - Straight Outta Compton.mp3',
        ),
        (
            'Earth, Wind & Fire',
            'September',
            r'Earth Wind and Fire - September.mp3',
        ),
        (
            'Florence + The Machine',
            'Dog Days Are Over',
            r'Florence and the Machine - Dog Days Are Over.mp3',
        ),
        ('JAŸ-Z', 'Izzo (H.O.V.A.)', r'Jay-Z - Izzo.mp3'),
        (
            'Mötley Crüe',
            'Kickstart My Heart',
            r'Motley Crue - Kickstart My Heart.mp3',
        ),
        (
            'Daryl Hall & John Oates',
            'You Make My Dreams (Come True)',
            r'Hall & Oates - You Make My Dreams.mp3',
        ),
        ('PSY', 'Gangnam Style (강남스타일)', r'PSY - Gangnam Style.mp3'),
        ('Outkast', 'Hey Ya!', r'OutKast - Speakerboxxx\09 - Hey Ya!.mp3'),
        (
            'Mobb Deep',
            'Shook Ones, Pt. II',
            r'Mobb Deep - Shook Ones Part 2.mp3',
        ),
        (
            'A$AP Rocky',
            "F**kin' Problems (feat. Drake)",
            r'ASAP Rocky - Fuckin Problems.mp3',
        ),
        ('YOASOBI', '夜に駆ける', r'YOASOBI - 夜に駆ける.mp3'),
        (
            'Luis Fonsi',
            'Despacito - Remix',
            r'Luis Fonsi - Despacito (Remix) feat. Justin Bieber.mp3',
        ),
        (
            'The Rolling Stones',
            "(I Can't Get No) Satisfaction - Mono",
            r'Rolling Stones - Satisfaction.mp3',
        ),
    ],
)
def test_names_spelled_the_way_files_spell_them(
    artist: str, title: str, filename: str
) -> None:
    assert _accepts(
        {'name': title, 'artists': [artist], 'duration': 200}, filename
    )


@pytest.mark.parametrize(
    ('artist', 'title', 'filename'),
    [
        ('P!nk', 'So What', r'Miles Davis - So What.mp3'),
        ('YOASOBI', '夜に駆ける', r'YOASOBI - 群青.mp3'),
        ('Outkast', 'Hey Ya!', r'Outkast - Hey Yall.mp3'),
        ('Luis Fonsi', 'Despacito - Remix', r'Luis Fonsi - Despacito.mp3'),
        ('BTS', 'Dynamite - Holiday Remix', r'BTS - Dynamite.mp3'),
        ('Björk', 'Jóga - Live', r'Bjork - Homogenic\03 Joga.mp3'),
        (
            'Taylor Swift',
            'Love Story (Taylor’s Version)',
            r'Taylor Swift - Love Story.mp3',
        ),
        (
            'Mobb Deep',
            'Shook Ones, Pt. II',
            r'Mobb Deep - Shook Ones Part I.mp3',
        ),
        ('Azealia Banks', '212', r'Azealia Banks - 1212.mp3'),
        (
            'Daryl Hall & John Oates',
            'You Make My Dreams',
            r'Oates - You Make My Dreams.mp3',
        ),
    ],
)
def test_other_songs_and_versions_are_refused(
    artist: str, title: str, filename: str
) -> None:
    assert not _accepts(
        {'name': title, 'artists': [artist], 'duration': 200}, filename
    )


def test_a_live_album_track_takes_a_live_file() -> None:
    song = {
        'name': 'Jóga',
        'artists': ['Björk'],
        'album_name': 'Homogenic (Live)',
        'duration': 265,
    }
    assert _accepts(song, r'Bjork - Homogenic Live\03 Joga (Live).mp3')


def test_symbol_names_get_a_plain_spelling_search() -> None:
    assert 'Pink So What' in sp._slskd_search_queries({
        'name': 'So What',
        'artists': ['P!nk'],
    })
    assert 'ACDC Back In Black' in sp._slskd_search_queries({
        'name': 'Back In Black',
        'artists': ['AC/DC'],
    })
    queries = sp._slskd_search_queries({
        'name': "F**kin' Problems",
        'artists': ['A$AP Rocky'],
    })
    assert queries[0] == 'A AP Rocky Problems'
    assert 'AsAP Rocky Problems' in queries


def test_plain_name() -> None:
    assert sp._plain_name('P!nk') == 'Pink'
    assert sp._plain_name('$uicideboy$') == 'suicideboys'
    assert sp._plain_name('N.W.A.') == 'NWA'
    assert sp._plain_name('JAŸ-Z') == 'JAY Z'
    assert sp._plain_name('Panic! At The Disco') == 'Panic At The Disco'


# ── quality and busy peers ─────────────────────────────────────────
def _select(row: dict[str, Any]) -> list[Any]:
    settings = {'extensions': ['mp3'], 'min_bitrate': 256}
    return sp._select_download_candidates(
        [{'filename': 'a.mp3', 'match_score': 9, **row}], settings
    )


def test_a_vbr_v0_file_passes_a_256_minimum() -> None:
    assert _select({'bitRate': 245, 'isVariableBitRate': True})
    assert not _select({'bitRate': 245})
    assert not _select({'bitRate': 190, 'isVariableBitRate': True})


def test_busy_peers_are_used_when_no_free_peer_has_the_song() -> None:
    busy = {
        'username': 'busy',
        'hasFreeUploadSlot': False,
        'fileCount': 1,
        'files': [
            {
                'filename': r"music\Yung Lean - That's It.mp3",
                'length': 161,
                'bitRate': 320,
            }
        ],
    }
    assert not sp._rank_slskd_candidates(THATS_IT, [busy])
    assert sp._rank_slskd_candidates(THATS_IT, [busy], include_busy=True)
    assert sp._busy_responses([busy]) == [busy]


def test_a_blocked_artist_and_title_lose_two_words() -> None:
    # Measured: "Lady Gaga" and "Hold My Hand" both get no answer;
    # "Gaga Hold Hand" finds the song.
    song = {'name': 'Hold My Hand', 'artists': ['Lady Gaga']}
    loosened = sp._blocked_phrase_queries(song, sp._slskd_search_queries(song))
    assert 'Gaga Hold Hand' in loosened
    assert all(len(q.split()) >= 2 for q in loosened)


# ── the tag check after a download ─────────────────────────────────
@pytest.mark.parametrize(
    ('spotify', 'tags', 'same'),
    [
        ('Despacito - Remix', 'Despacito (Official Remix)', True),
        ('Shook Ones, Pt. II', 'Shook Ones Part 2', True),
        ('Shook Ones, Pt. II', 'Shook Ones Part 1', False),
        ('Tití Me Preguntó', 'Titi Me Pregunto', True),
        ("F**kin' Problems (feat. Drake)", 'Fuckin Problems', True),
        ("F**kin' Problems", 'Love Problems', False),
        ("F**kin' Problems", 'Fkin Problems', True),
        (
            "That's It (feat. Future)",
            "That's It [from GTAVI: The Album]",
            True,
        ),
        ('Blinding Lights', 'Save Your Tears', False),
    ],
)
def test_downloaded_titles_are_compared_like_names(
    spotify: str, tags: str, same: bool
) -> None:
    assert track_tag_match._titles_align(spotify, tags) is same


@pytest.mark.parametrize(
    ('spotify', 'tags', 'same'),
    [
        (['P!nk'], ['Pink'], True),
        (['Mötley Crüe'], ['Motley Crue'], True),
        (['The Weeknd'], ['Weeknd'], True),
        (['Daryl Hall & John Oates'], ['Hall & Oates'], True),
        (['JAŸ-Z'], ['Jay-Z'], True),
        (['Lady Gaga'], ['Lady Antebellum'], False),
        (['Drake'], ['Future'], False),
        (['Metro Boomin'], ['Metronomy'], False),
    ],
)
def test_downloaded_artists_are_compared_like_names(
    spotify: list[str], tags: list[str], same: bool
) -> None:
    assert track_tag_match._artist_lists_align(spotify, tags) is same
