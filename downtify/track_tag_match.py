"""Compare Spotify playlist metadata to on-disk audio tags (mutagen)."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from mutagen import File as MutagenFile

from .library_metadata import read_audio_metadata

_DEFAULT_DURATION_TOLERANCE_SECONDS = 10
_DEFAULT_DURATION_TOLERANCE_PERCENT = 15
_DEFAULT_MIX_DURATION_TOLERANCE_PERCENT = 50
_MAX_WHEN_SPOTIFY_DURATION_UNKNOWN = 600
_WRONG_MATCH_TITLE_KEYWORDS = (
    'audiobook',
    'audio book',
    'audiolibro',
    'unabridged',
    'abridged',
    'narrated by',
    'read by',
    'full book',
    'ebook',
    'e-book',
    'chapter 1',
    'chapter 2',
    'chapitre',
    'podcast',
    'spoken word',
    'complete book',
    ' hour ',
    ' hours ',
    ' hrs ',
    ' part 1 of',
    ' part 2 of',
    '1 hour',
    '2 hour',
)

# Variant modifiers (live, remix, karaoke, …) shared by YouTube and slskd.
# Use word-boundary-ish patterns for short tokens (live, remix) to avoid
# false positives inside unrelated words (e.g. "Oliver", "deliver").
_UNWANTED_REMOTE_VARIANT_KEYWORDS = (
    'karaoke',
    'instrumental',
    'acapella',
    'a cappella',
    'cover ',
    'cover)',
    'tribute',
    'guitar lesson',
    'sped up',
    'slowed',
    'reverb',
    'nightcore',
    '8d audio',
    'bass boosted',
    ' remix',
    '(remix',
    'remix)',
    'extended',
    ' clean',
    'clean version',
    ' live',
    '- live',
    '(live',
    'live)',
    'live version',
    'live at',
    'live from',
)


_NON_WORD = re.compile(r'[\W_]+')


def _spaced_words(text: str) -> str:
    """*text* as its words between single spaces, padded (`` a b ``)."""

    words = ' '.join(part for part in _NON_WORD.split(text) if part)
    return f' {words} '


# Each modifier as its words, worked out once (`` remix ``, `` live at ``).
_VARIANT_KEYWORD_WORDS = {
    kw: _spaced_words(kw) for kw in _UNWANTED_REMOTE_VARIANT_KEYWORDS
}


def remote_adds_unwanted_variant(
    spotify_title: str,
    remote_text: str,
    *,
    spotify_artists: Optional[list[str]] = None,
    skip_keywords: Optional[frozenset[str]] = None,
) -> bool:
    """True when *remote_text* adds a variant modifier absent from Spotify."""

    artists = ' '.join(
        str(a).strip() for a in (spotify_artists or []) if str(a).strip()
    )
    spotify_blob = f'{spotify_title or ""} {artists}'.casefold()
    remote_l = str(remote_text or '').casefold()
    skip = skip_keywords or frozenset()
    spotify_words = ''
    for kw in _UNWANTED_REMOTE_VARIANT_KEYWORDS:
        if kw in skip or kw not in remote_l or kw in spotify_blob:
            continue
        # Spotify's own words, so "Song - Remix" allows a "Song (Remix)"
        # file: a modifier counts as Spotify's when its words are, whatever
        # the punctuation around them. Only worked out when needed.
        spotify_words = spotify_words or _spaced_words(spotify_blob)
        if _VARIANT_KEYWORD_WORDS[kw] not in spotify_words:
            return True
    return False


def _remote_adds_spam_keyword(spotify_title: str, remote_text: str) -> bool:
    remote_l = str(remote_text or '').casefold()
    if not remote_l:
        return False
    title_l = str(spotify_title or '').casefold()
    return any(
        kw in remote_l and kw not in title_l
        for kw in _WRONG_MATCH_TITLE_KEYWORDS
    )


def remote_text_unacceptable(
    spotify_title: str,
    remote_text: str,
    *,
    spotify_artists: Optional[list[str]] = None,
    skip_variant_keywords: Optional[frozenset[str]] = None,
) -> bool:
    """True when *remote_text* adds spam or variant modifiers absent from Spotify."""

    if _remote_adds_spam_keyword(spotify_title, remote_text):
        return True
    return remote_adds_unwanted_variant(
        spotify_title,
        remote_text,
        spotify_artists=spotify_artists,
        skip_keywords=skip_variant_keywords,
    )


def youtube_title_has_negative_keyword(
    spotify_title: str, candidate_title: str
) -> bool:
    """Variant-only check (audiobook/spam uses :func:`remote_text_unacceptable`)."""

    return remote_adds_unwanted_variant(spotify_title, candidate_title)


_MIX_SUFFIX_RE = re.compile(
    r'\s*[-–—]\s*(?:radio\s+(?:mix|edit)|extended\s+mix|club\s+mix|'
    r'original\s+mix|clean\s+version|explicit\s+version|remix)\s*$',
    re.IGNORECASE,
)


_MIX_VARIANT_MARKERS = (
    'extended mix',
    'radio mix',
    'radio edit',
    'club mix',
    'original mix',
)

MIX_VARIANT_REMOTE_SKIP_KEYWORDS = frozenset({'extended'})


def strip_mix_suffix(title: str) -> str:
    """Drop trailing mix/edit suffixes for broader audio search queries."""

    return _MIX_SUFFIX_RE.sub('', str(title or '').strip()).strip()


def candidate_adds_mix_variant(
    spotify_title: str, candidate_title: str
) -> bool:
    """True when *candidate_title* adds a mix/edit label absent from Spotify."""

    spotify_l = str(spotify_title or '').casefold()
    cand_l = str(candidate_title or '').casefold()
    return any(
        marker in cand_l and marker not in spotify_l
        for marker in _MIX_VARIANT_MARKERS
    )


def mix_variant_remote_skip_keywords(
    spotify_title: str,
    remote_text: str,
) -> Optional[frozenset[str]]:
    """Allow ``extended`` in remote titles when probing mix-variant uploads."""

    if candidate_adds_mix_variant(spotify_title, remote_text):
        return MIX_VARIANT_REMOTE_SKIP_KEYWORDS
    return None


def youtube_probe_title_matches(
    song: dict[str, Any], probe_title: str
) -> bool:
    """Loose title check for YouTube downloads (probe metadata, not file tags)."""

    text = str(probe_title or '').strip()
    if not text:
        return True
    if remote_title_unacceptable(song, text):
        return False
    spotify_title = str(song.get('name') or '').strip()
    if not spotify_title:
        return True
    if _titles_align(spotify_title, text):
        return True
    if _titles_align(strip_mix_suffix(spotify_title), text):
        return True
    probe_n = _normalize_tag_loose(text)
    title_tokens = [
        token
        for token in _normalize_tag_loose(spotify_title).split()
        if len(token) >= 3
    ]
    if not title_tokens:
        return False
    hits = sum(1 for token in title_tokens if token in probe_n)
    if hits < max(1, len(title_tokens) // 2):
        return False
    artists = song.get('artists') or []
    if not artists:
        return True
    return any(
        _normalize_tag_loose(str(artist)) in probe_n for artist in artists
    )


def fold_accents(text: str) -> str:
    """*text* without accents: ``Tití Me Preguntó`` -> ``Titi Me Pregunto``
    (a file name often drops them)."""

    if text.isascii():
        return text
    decomposed = unicodedata.normalize('NFKD', text)
    return ''.join(ch for ch in decomposed if not unicodedata.combining(ch))


def plain_name(text: str) -> str:
    """*text* spelled the way file names usually spell it: symbols inside a
    word read as the letter they stand for and the rest dropped - ``P!nk``
    -> ``Pink``, ``A$AP Rocky`` -> ``ASAP Rocky``, ``$uicideboy$`` ->
    ``Suicideboys``, ``AC/DC`` -> ``ACDC``, ``N.W.A.`` -> ``NWA``,
    ``JAŸ-Z`` -> ``JAY Z`` (no accents; a hyphen splits words)."""

    words = []
    for raw in fold_accents(str(text or '')).replace('-', ' ').split():
        word = re.sub(r'(?<=[^\W\d_])!(?=[^\W\d_])', 'i', raw)
        word = re.sub(r'(?<=[^\W\d_])@(?=[^\W\d_])', 'a', word)
        word = re.sub(r'\$(?=[^\W\d_])|(?<=[^\W\d_])\$', 's', word)
        word = re.sub(r'[^\w]+', '', word)
        if word:
            words.append(word)
    return ' '.join(words)


def _normalize_tag(text: str) -> str:
    return unicodedata.normalize('NFC', str(text or '').strip()).casefold()


def _normalize_tag_loose(text: str) -> str:
    text = _normalize_tag(text)
    text = text.replace("'", '').replace('’', '').replace('‛', '')
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _titles_align(expected: str, from_file: str) -> bool:
    title_n = _normalize_tag_loose(expected)
    file_title_n = _normalize_tag_loose(from_file)
    if not title_n or not file_title_n:
        return True
    if (
        title_n == file_title_n
        or title_n in file_title_n
        or file_title_n in title_n
    ):
        return True
    # The song's own name in both, word for word, however each spells the
    # rest: "Despacito - Remix" / "Despacito (Official Remix)", "Shook Ones,
    # Pt. II" / "Shook Ones Part 2", "Tití Me Preguntó" / "Titi Me Pregunto".
    expected_words = _title_words(expected, core=True)
    file_words = _title_words(from_file, core=True)
    if not expected_words or not file_words:
        return False
    return _words_within(expected_words, _title_words(from_file)) or (
        _words_within(file_words, _title_words(expected))
    )


def _words_within(words: list[str], others: list[str]) -> bool:
    """Whether every word of *words* is among *others*; a censored word
    (``f*kin``) stands for any word it could be (``fuckin``, or ``fkin``
    when the stars were just dropped)."""

    pool = set(others)
    for word in words:
        if '*' in word:
            pattern = re.compile(
                r'\w{0,4}'.join(re.escape(p) for p in word.split('*')) + '$'
            )
            if not any(pattern.match(other) for other in pool):
                return False
        elif word not in pool:
            return False
    return True


_TAG_CREDIT = re.compile(
    r'\s*[\(\[]\s*(?:feat\.?|ft\.?|featuring|with|from|official)\b[^\)\]]*[\)\]]'
    r'|\s+(?:feat\.?|ft\.?|featuring)\s.*$',
    re.IGNORECASE,
)
_TAG_PART = re.compile(
    r'\b(?:pt|part|vol|volume)\b\.?\s*([ivx]+|\d+)\b', re.IGNORECASE
)
_TAG_ROMAN = {
    'i': '1',
    'ii': '2',
    'iii': '3',
    'iv': '4',
    'v': '5',
    'vi': '6',
    'vii': '7',
    'viii': '8',
    'ix': '9',
    'x': '10',
}


_CENSORED_RUN = re.compile(r'(?<=[^\W\d_])\*+')
_TITLE_SPLIT = re.compile(r'(?:[^\w\x00]|_)+')


@lru_cache(maxsize=4096)
def _title_words(text: str, *, core: bool = False) -> tuple[str, ...]:
    """*text*'s words for comparing titles: no accents, case, apostrophes,
    ``&``/``and``, censored words (``F**kin'``), and ``Part II`` as
    ``pt 2``. With *core*, only the song's own name: no ``(feat. …)``,
    ``(from …)`` or `` - …`` part. Remembered per title: a playlist
    compares the same titles over and over."""

    value = fold_accents(str(text or ''))
    if core:
        head = value.split(' - ', 1)[0]
        value = _TAG_CREDIT.sub('', head) or head
    value = value.casefold().replace("'", '').replace('\u2019', '')
    # A censored word ("F**kin'") stays one word, its hidden letters one
    # "*", matched against the spelled-out word (_words_within).
    value = _CENSORED_RUN.sub('\x00', value)
    value = _TAG_PART.sub(
        lambda m: f' pt {_TAG_ROMAN.get(m.group(1).casefold(), m.group(1))} ',
        value,
    )
    words = _TITLE_SPLIT.split(value)
    return tuple(w.replace('\x00', '*') for w in words if w and w != 'and')


def _artist_key(text: str) -> str:
    """An artist as tags are compared: letters only, no accents, symbols
    spelled out (``P!nk`` -> ``pink``), no leading "The" or ``&``/``and``."""

    value = plain_name(text).casefold()
    value = re.sub(r'^the\s+', '', value)
    return ''.join(w for w in re.split(r'[\W_]+', value) if w and w != 'and')


def _artist_lists_align(expected: list[str], actual: list[str]) -> bool:
    if not expected:
        return True
    if not actual:
        return True
    for exp in expected:
        exp_n = _normalize_tag_loose(exp)
        if not exp_n:
            continue
        for act in actual:
            act_n = _normalize_tag_loose(act)
            if exp_n in act_n or act_n in exp_n:
                return True
    # Spelled differently: "P!nk" / "Pink", "Mötley Crüe" / "Motley Crue",
    # "The Weeknd" / "Weeknd", "Daryl Hall & John Oates" / "Hall & Oates".
    for exp in expected:
        exp_k = _artist_key(exp)
        exp_words = {
            w
            for w in re.split(r'[\W_]+', fold_accents(exp).casefold())
            if len(w) >= 4
        }
        for act in actual:
            act_k = _artist_key(act)
            if exp_k and act_k and (exp_k in act_k or act_k in exp_k):
                return True
            act_words = {
                w
                for w in re.split(r'[\W_]+', fold_accents(act).casefold())
                if len(w) >= 4
            }
            # Every name word of one in the other ("Hall & Oates").
            if (
                act_words
                and exp_words
                and (act_words <= exp_words or exp_words <= act_words)
            ):
                return True
    return False


def song_duration_seconds(song: dict[str, Any]) -> int:
    target_duration = int(song.get('duration') or 0)
    if target_duration > 1000:
        return target_duration // 1000
    return target_duration


def _clamp_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(maximum, max(minimum, parsed))


def duration_tolerances_from_settings(
    settings: Optional[dict[str, Any]] = None,
) -> dict[str, int]:
    """Read slskd duration tolerance knobs (defaults: 10s, 15%%, 50%% mix)."""

    raw = settings if isinstance(settings, dict) else {}
    return {
        'seconds': _clamp_int(
            raw.get('duration_tolerance_seconds'),
            _DEFAULT_DURATION_TOLERANCE_SECONDS,
            minimum=1,
            maximum=120,
        ),
        'percent': _clamp_int(
            raw.get('duration_tolerance_percent'),
            _DEFAULT_DURATION_TOLERANCE_PERCENT,
            minimum=1,
            maximum=100,
        ),
        'mix_percent': _clamp_int(
            raw.get('mix_duration_tolerance_percent'),
            _DEFAULT_MIX_DURATION_TOLERANCE_PERCENT,
            minimum=1,
            maximum=200,
        ),
    }


def media_duration_matches_song(
    song: dict[str, Any],
    media_seconds: int,
    *,
    tolerance_seconds: int = _DEFAULT_DURATION_TOLERANCE_SECONDS,
    tolerance_percent: int = _DEFAULT_DURATION_TOLERANCE_PERCENT,
) -> bool:
    """Align with slskd: reject audiobooks and hour-long wrong matches."""

    if media_seconds <= 0:
        return True
    target = song_duration_seconds(song)
    if not target:
        return media_seconds <= _MAX_WHEN_SPOTIFY_DURATION_UNKNOWN
    delta = abs(media_seconds - target)
    if delta <= tolerance_seconds:
        return True
    cap = max(45, int(target * tolerance_percent / 100))
    if media_seconds > target + cap:
        return False
    if media_seconds < max(20, int(target * 0.5)) and target >= 60:
        return False
    return delta <= cap


def media_duration_matches_mix_variant(
    song: dict[str, Any],
    media_seconds: int,
    *,
    tolerance_percent: int = _DEFAULT_MIX_DURATION_TOLERANCE_PERCENT,
    normal_tolerance_seconds: int = _DEFAULT_DURATION_TOLERANCE_SECONDS,
    normal_tolerance_percent: int = _DEFAULT_DURATION_TOLERANCE_PERCENT,
) -> bool:
    """Looser runtime bounds for extended/radio/club mix last-resort matches."""

    if media_duration_matches_song(
        song,
        media_seconds,
        tolerance_seconds=normal_tolerance_seconds,
        tolerance_percent=normal_tolerance_percent,
    ):
        return True
    if media_seconds <= 0:
        return True
    target = song_duration_seconds(song)
    if not target:
        return media_seconds <= _MAX_WHEN_SPOTIFY_DURATION_UNKNOWN
    if media_seconds > max(720, int(target * 2.5)):
        return False
    if media_seconds > int(target * 1.85) + 30:
        return False
    if media_seconds < max(20, int(target * 0.35)) and target >= 60:
        return False
    return abs(media_seconds - target) <= max(
        90, int(target * tolerance_percent / 100)
    )


def duration_matches_song(song: dict[str, Any], media_seconds: int) -> bool:
    """Alias used by YouTube pre-download checks."""

    return media_duration_matches_song(song, media_seconds)


def remote_title_unacceptable(song: dict[str, Any], remote_title: str) -> bool:
    """True when a YouTube/Soulseek title looks like audiobook/podcast spam."""

    spotify_title = str(song.get('name') or '')
    return remote_text_unacceptable(
        spotify_title,
        remote_title,
        spotify_artists=[
            str(a).strip()
            for a in (song.get('artists') or [])
            if str(a).strip()
        ],
        skip_variant_keywords=mix_variant_remote_skip_keywords(
            spotify_title,
            remote_title,
        ),
    )


def audio_file_length_seconds(path: Path) -> int:
    try:
        audio = MutagenFile(str(path))
    except Exception:
        return 0
    if audio is None or not getattr(audio, 'info', None):
        return 0
    try:
        return int(getattr(audio.info, 'length', 0) or 0)
    except (TypeError, ValueError):
        return 0


def snapshot_spotify_metadata(song: dict[str, Any]) -> dict[str, Any]:
    """Preserve the Spotify row before mutagen or slskd paths overwrite fields."""

    row = dict(song)
    if not row.get('spotify_name'):
        row['spotify_name'] = str(row.get('name') or '').strip()
    if not row.get('spotify_artists'):
        row['spotify_artists'] = [
            str(a).strip()
            for a in (row.get('artists') or [])
            if str(a).strip()
        ]
    return row


def spotify_expected(song: dict[str, Any]) -> tuple[str, list[str]]:
    title = str(song.get('spotify_name') or '').strip()
    artists = [
        str(a).strip()
        for a in (song.get('spotify_artists') or [])
        if str(a).strip()
    ]
    return title, artists


def spotify_aligns_with_file_tags(song: dict[str, Any]) -> bool:
    """False when embedded tags clearly disagree with the Spotify playlist row."""

    if not song.get('library_from_tags'):
        return True

    spotify_title, spotify_artists = spotify_expected(song)
    if not spotify_title:
        return True

    file_title = str(song.get('name') or '').strip()
    file_artists = [
        str(a).strip() for a in (song.get('artists') or []) if str(a).strip()
    ]
    if not file_title:
        return True
    if not _titles_align(spotify_title, file_title):
        return False
    return _artist_lists_align(spotify_artists, file_artists)


def spotify_file_tag_mismatch_label(song: dict[str, Any]) -> str:
    spotify_title, spotify_artists = spotify_expected(song)
    file_title = str(song.get('name') or 'unknown')
    file_artists = song.get('artists') or []
    exp = spotify_title or 'unknown'
    if spotify_artists:
        exp = f'{", ".join(spotify_artists)} - {exp}'
    file = file_title
    if file_artists:
        file = f'{", ".join(str(a) for a in file_artists)} - {file}'
    return f'spotify={exp!r} tags={file!r}'


def verify_downloaded_file_matches_spotify(
    path: Path, song: dict[str, Any]
) -> bool:
    """Read mutagen tags on *path* and compare to snapshot Spotify metadata."""

    meta = read_audio_metadata(path)
    if not meta.get('title') and not meta.get('artists'):
        logger.info(
            'slskd: skip tag verify (no embedded tags) file={!r}',
            path.name,
        )
        return True

    row = snapshot_spotify_metadata(song)
    if meta.get('title'):
        row['name'] = meta['title']
    if meta.get('artists'):
        row['artists'] = meta['artists']
    row['library_from_tags'] = True
    return spotify_aligns_with_file_tags(row)


def verify_downloaded_audio_file(path: Path, song: dict[str, Any]) -> bool:
    """Tags and runtime must match the Spotify row (post-download guard)."""

    length = audio_file_length_seconds(path)
    if length > 0:
        meta = read_audio_metadata(path)
        file_title = str(meta.get('title') or path.stem)
        spotify_title = str(song.get('spotify_name') or song.get('name') or '')
        duration_ok = (
            media_duration_matches_mix_variant(song, length)
            if candidate_adds_mix_variant(spotify_title, file_title)
            else media_duration_matches_song(song, length)
        )
        if not duration_ok:
            logger.info(
                'download verify: duration mismatch file={}s spotify~{}s file={!r}',
                length,
                song_duration_seconds(song),
                path.name,
            )
            return False
    return verify_downloaded_file_matches_spotify(path, song)


def verify_youtube_download_file(
    path: Path,
    song: dict[str, Any],
    *,
    probe: Optional[dict[str, Any]] = None,
) -> bool:
    """Pre-tagging guard for yt-dlp files (duration + YouTube title, not mutagen)."""

    length = audio_file_length_seconds(path)
    probe_title = str((probe or {}).get('title') or '')
    spotify_title = str(song.get('spotify_name') or song.get('name') or '')
    if length > 0:
        duration_ok = (
            media_duration_matches_mix_variant(song, length)
            if probe_title
            and candidate_adds_mix_variant(spotify_title, probe_title)
            else media_duration_matches_song(song, length)
        )
        if not duration_ok:
            logger.info(
                'download verify: duration mismatch file={}s spotify~{}s file={!r}',
                length,
                song_duration_seconds(song),
                path.name,
            )
            return False
    if probe is None:
        return True
    if youtube_probe_title_matches(song, probe_title):
        return True
    logger.info(
        'download verify: YouTube title mismatch probe={!r} spotify={!r}',
        probe_title[:120],
        spotify_title[:120],
    )
    return False
