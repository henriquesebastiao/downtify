"""Compare Spotify playlist metadata to on-disk audio tags (mutagen)."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from mutagen import File as MutagenFile

from .library_metadata import read_audio_metadata

_DEFAULT_DURATION_TOLERANCE_SECONDS = 10
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
    return (
        title_n == file_title_n
        or title_n in file_title_n
        or file_title_n in title_n
    )


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
    return False


def song_duration_seconds(song: dict[str, Any]) -> int:
    target_duration = int(song.get('duration') or 0)
    if target_duration > 1000:
        return target_duration // 1000
    return target_duration


def media_duration_matches_song(
    song: dict[str, Any], media_seconds: int
) -> bool:
    """Align with slskd: reject audiobooks and hour-long wrong matches."""

    if media_seconds <= 0:
        return True
    target = song_duration_seconds(song)
    if not target:
        return media_seconds <= _MAX_WHEN_SPOTIFY_DURATION_UNKNOWN
    delta = abs(media_seconds - target)
    if delta <= _DEFAULT_DURATION_TOLERANCE_SECONDS:
        return True
    cap = max(45, int(target * 0.20))
    if media_seconds > target + cap:
        return False
    if media_seconds < max(20, int(target * 0.5)) and target >= 60:
        return False
    return delta <= cap


def media_duration_matches_mix_variant(
    song: dict[str, Any], media_seconds: int
) -> bool:
    """Looser runtime bounds for extended/radio/club mix last-resort matches."""

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
    return abs(media_seconds - target) <= max(90, int(target * 0.50))


def duration_matches_song(song: dict[str, Any], media_seconds: int) -> bool:
    """Alias used by YouTube pre-download checks."""

    return media_duration_matches_song(song, media_seconds)


def remote_title_unacceptable(song: dict[str, Any], remote_title: str) -> bool:
    """True when a YouTube/Soulseek title looks like audiobook/podcast spam."""

    remote_l = str(remote_title or '').casefold()
    if not remote_l:
        return False
    song_title_l = str(song.get('name') or '').casefold()
    return any(
        kw in remote_l and kw not in song_title_l
        for kw in _WRONG_MATCH_TITLE_KEYWORDS
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
        spotify_title = str(
            song.get('spotify_name') or song.get('name') or ''
        )
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
