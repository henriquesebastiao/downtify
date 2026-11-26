"""The low-bitrate report: library files under a bitrate, and better
copies from Soulseek (slskd) to replace them with, one approval at a time.

A library built over years carries whatever each source gave at the time:
128 kbps rips, 160 kbps YouTube audio, a 192 kbps file a friend sent.
This module lists them and offers a better copy, and **nothing changes
until the admin approves a copy for a file**:

1. **Report** (:func:`report_rows`): every library file whose bitrate is
   under the threshold (256 kbps by default), with its format, size and
   where it came from when Downtify knows. Lossless files are never
   listed. Reading the report writes nothing.
2. **Search** (:func:`search_candidates`): the usual slskd search and
   matching (``downtify/slskd_provider.py``: the same queries, scoring,
   duration tolerance and peer filters a download uses), then the
   report's own preferences (:func:`pick_candidates`): lossy files only,
   MP3 320 first, 256 kbps and up accepted, files that list no bitrate
   allowed (last), lossless only when the admin asks for it. Each
   candidate must be better than the file it would replace. Writes
   nothing either.
3. **Replace** (the routes in ``downtify/low_bitrate_routes.py``): the
   chosen copy is downloaded (:func:`fetch_candidate`, in the shared
   download slot), checked, and placed beside the old file with the old
   file's tags, cover and lyrics (:func:`place_upgrade`). Then the old
   file is merged into it exactly the way the Doctor merges duplicates
   (playlists, likes, ratings, the track index and the apps all follow
   the new file) and goes to the music trash, so the replacement can be
   undone from there.

The new copy never takes the old file's path: the music trash keeps the
old path for the file it holds (a restore puts it back there), so the
new copy is written as ``<name> (HQ).<ext>`` - or ``<name>.<ext>`` when
the format changed and that name is free.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from loguru import logger

from . import isrc as isrc_mod
from . import lyrics as lyrics_mod
from . import slskd_provider as slskd
from .audio_formats import extensions_of
from .audio_replace import copy_tags
from .cover_art import extract_embedded_cover
from .downloader import embed_metadata
from .library_catalog import UPGRADE_STAGING_MARKER
from .library_metadata import read_audio_metadata
from .library_upgrade import _song_from_tags

#: Files under this bitrate (kbps) are listed, unless the request says.
DEFAULT_THRESHOLD_KBPS = 256
MIN_THRESHOLD_KBPS = 64
MAX_THRESHOLD_KBPS = 320
#: The lowest bitrate a replacement may list (kbps): 256 is acceptable.
ACCEPTED_KBPS = 256
#: What counts as "320": a CBR 320 lists 320, some peers list 319.
BEST_KBPS = 315
#: A VBR file lists its average: LAME V0 (as good as 320 CBR) averages
#: ~220-260 kbps, so it passes at the same share slskd's rules use.
VBR_SHARE = 0.85
#: Codecs that are never "low bitrate": the report leaves them out.
LOSSLESS_CODECS = frozenset({'flac', 'alac', 'wav', 'aiff', 'ape', 'wv'})
LOSSY_EXTENSIONS = ('mp3', 'm4a', 'ogg', 'opus')
LOSSLESS_EXTENSIONS = ('flac',)
#: Candidates offered per file.
CANDIDATE_LIMIT = 8
#: How far the new copy's length may be from the old file's (seconds).
DURATION_TOLERANCE_SECONDS = 5.0
#: The suffix of a new copy that would otherwise take the old name.
HQ_SUFFIX = ' (HQ)'

ProgressCallback = Callable[[float, str, Optional[str]], None]


class UpgradeError(ValueError):
    """The replacement stopped before the library changed; ``code`` is a
    stable name for the page (``lowBitrate.errors.<code>``)."""

    def __init__(self, code: str, detail: str = '') -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail


# ── The report ──────────────────────────────────────────────────────────


def clamp_threshold(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD_KBPS
    return min(MAX_THRESHOLD_KBPS, max(MIN_THRESHOLD_KBPS, number))


def _kbps(bits_per_second: Any) -> int:
    try:
        return max(0, round(int(bits_per_second or 0) / 1000))
    except (TypeError, ValueError):
        return 0


def _extension(name: str) -> str:
    return Path(str(name or '')).suffix.lower().lstrip('.')


def is_low_bitrate(entry: dict[str, Any], threshold_kbps: int) -> bool:
    """Whether a library row is lossy audio under *threshold_kbps*. A file
    whose bitrate can't be read isn't listed: nobody knows it is low."""

    codec = str(entry.get('codec') or '').lower()
    if codec in LOSSLESS_CODECS or _extension(entry.get('file')) == 'flac':
        return False
    kbps = _kbps(entry.get('bitrate'))
    return 0 < kbps < threshold_kbps


def report_rows(
    entries: Iterable[dict[str, Any]],
    threshold_kbps: int,
    providers: Optional[dict[str, str]] = None,
) -> list[dict[str, Any]]:
    """The report's rows, lowest bitrate first: ``{file, title, artist,
    album, duration, bitrate (kbps), format, size, source}`` (``source``
    is the provider that fetched the file, ``''`` when unknown)."""

    providers = providers or {}
    rows = []
    for entry in entries:
        if not is_low_bitrate(entry, threshold_kbps):
            continue
        file = str(entry.get('file') or '')
        rows.append({
            'file': file,
            'title': str(entry.get('title') or ''),
            'artist': str(entry.get('artist') or '').replace(';', ', '),
            'album': str(entry.get('album') or ''),
            'duration': round(float(entry.get('duration') or 0), 1),
            'bitrate': _kbps(entry.get('bitrate')),
            'format': _extension(file),
            'codec': str(entry.get('codec') or ''),
            'size': int(entry.get('size') or 0),
            'source': str(providers.get(file) or ''),
        })
    rows.sort(key=lambda row: (row['bitrate'], row['artist'], row['title']))
    return rows


def song_for_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """The song slskd is searched for: the file's own tags."""

    artist = str(entry.get('artist') or '')
    artists = [part.strip() for part in artist.split(';') if part.strip()]
    if not artists:
        artists = [p.strip() for p in artist.split(',') if p.strip()]
    return {
        'name': str(entry.get('title') or ''),
        'artists': artists,
        'album_name': str(entry.get('album') or ''),
        'duration': int(round(float(entry.get('duration') or 0))),
    }


# ── Candidates ──────────────────────────────────────────────────────────


def candidate_id(row: dict[str, Any]) -> str:
    """A stable id for one peer's file (the page sends it back)."""

    raw = f'{row.get("username")}\0{row.get("filename")}'
    return hashlib.sha1(raw.encode('utf-8', 'replace')).hexdigest()[:16]


def _row_kbps(row: dict[str, Any]) -> int:
    try:
        return int(row.get('bitRate') or row.get('bitrate') or 0)
    except (TypeError, ValueError):
        return 0


def _tier(row: dict[str, Any]) -> int:
    """0 MP3 320, 1 MP3 256+, 2 other lossy 256+, 3 no bitrate listed,
    4 lossless (only offered when asked for)."""

    ext = _extension(row.get('filename'))
    if ext in LOSSLESS_EXTENSIONS:
        return 4
    kbps = _row_kbps(row)
    if not kbps:
        return 3
    if ext == 'mp3':
        # A VBR file that passes the floor is V0-class: as good as 320.
        return 0 if row.get('isVariableBitRate') or kbps >= BEST_KBPS else 1
    return 2


def _acceptable(
    row: dict[str, Any],
    old_kbps: int,
    include_lossless: bool,
    avoid: frozenset[str] = frozenset(),
) -> bool:
    ext = _extension(row.get('filename'))
    if ext in avoid:
        return False
    if ext in LOSSLESS_EXTENSIONS:
        return include_lossless
    if ext not in LOSSY_EXTENSIONS:
        return False
    kbps = _row_kbps(row)
    if not kbps:
        return True
    floor = ACCEPTED_KBPS * (VBR_SHARE if row.get('isVariableBitRate') else 1)
    return kbps >= floor and kbps > old_kbps


def pick_candidates(
    ranked: list[dict[str, Any]],
    old_kbps: int,
    *,
    include_lossless: bool = False,
    min_score: int = 0,
    limit: int = CANDIDATE_LIMIT,
    avoid: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """The copies worth offering for a file at *old_kbps*, best first:
    MP3 320, then 256 and up, then files that list no bitrate; each a
    good enough match (*min_score*, slskd's own gate). One per peer and
    name, so a peer sharing the album twice is listed once. Formats in
    *avoid* (the Formats to avoid setting) are never offered."""

    picked: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    avoided = frozenset(avoid)
    rows = [
        row
        for row in ranked
        if int(row.get('match_score') or 0) >= min_score
        and _acceptable(row, old_kbps, include_lossless, avoided)
    ]
    rows.sort(
        key=lambda row: (
            _tier(row),
            -int(row.get('match_score') or 0),
            0 if row.get('hasFreeUploadSlot', True) else 1,
            int(row.get('queueLength') or 0),
            -_row_kbps(row),
        )
    )
    for row in rows:
        key = (
            str(row.get('username') or ''),
            Path(str(row.get('filename') or '').replace('\\', '/')).name,
        )
        if key in seen:
            continue
        seen.add(key)
        picked.append(row)
        if len(picked) >= limit:
            break
    return picked


def public_candidate(
    row: dict[str, Any], old_duration: float
) -> dict[str, Any]:
    """What the page shows of a candidate (the peer's own fields kept
    server-side for the download)."""

    filename = str(row.get('filename') or '')
    duration = slskd._parse_duration_seconds(row.get('length'))
    return {
        'id': candidate_id(row),
        'username': str(row.get('username') or ''),
        'name': Path(filename.replace('\\', '/')).name,
        'folder': Path(filename.replace('\\', '/')).parent.name,
        'format': _extension(filename),
        'bitrate': _row_kbps(row),
        'vbr': bool(row.get('isVariableBitRate')),
        'size': int(row.get('size') or 0),
        'duration': duration,
        'duration_diff': (
            round(duration - old_duration)
            if duration and old_duration
            else None
        ),
        'score': int(row.get('match_score') or 0),
        'free_slot': bool(row.get('hasFreeUploadSlot', True)),
        'queue': int(row.get('queueLength') or 0),
        'best': _tier(row) == 0,
    }


def _responses_with_slots(
    responses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Every response, each file marked with its peer's slot and queue
    (a busy peer is offered too, behind the free ones)."""

    marked = []
    for resp in responses:
        free = slskd._response_has_free_slot(resp)
        queue = int(resp.get('queueLength') or 0)
        files = [
            {**row, 'hasFreeUploadSlot': free, 'queueLength': queue}
            for row in resp.get('files') or []
            if isinstance(row, dict)
        ]
        marked.append({**resp, 'files': files})
    return marked


def search_candidates(
    song: dict[str, Any],
    settings: dict[str, Any],
    old_kbps: int,
    *,
    include_lossless: bool = False,
    client: Any = None,
    cancel_check: Optional[Callable[[], None]] = None,
) -> list[dict[str, Any]]:
    """Search slskd for *song* and return the raw candidate rows worth
    offering (see :func:`pick_candidates`). Raises :class:`UpgradeError`
    when slskd can't be asked; ``[]`` when nobody has a better copy."""

    if not settings.get('enabled'):
        raise UpgradeError('slskd_off')
    client = client or slskd.SlskdClient(settings)
    if not client.configured():
        raise UpgradeError('slskd_off')
    if not client.can_connect():
        raise UpgradeError('slskd_unreachable')
    row = slskd.snapshot_spotify_metadata(song)
    queries = slskd._slskd_search_queries(row)
    if not queries:
        raise UpgradeError('no_tags')
    min_score = slskd._match_min_score(settings)
    label = f'{song.get("name")} - {", ".join(song.get("artists") or [])}'
    deadline = slskd._slskd_deadline(settings)
    # A search holds one of slskd's parallel slots, as a download does.
    with slskd._slskd_semaphore(settings):
        for query in queries:
            if cancel_check:
                cancel_check()
            if slskd._past_deadline(deadline):
                break
            search_id = client.start_search(query) or ''
            if not search_id:
                continue
            try:
                if not client.wait_search_complete(
                    search_id,
                    label,
                    deadline=deadline,
                    cancel_check=cancel_check,
                ):
                    continue
                responses = _responses_with_slots(
                    client.search_responses(search_id)
                )
            finally:
                client.delete_search(search_id)
            ranked = slskd._rank_slskd_candidates(
                song, responses, settings, include_busy=True
            )
            picked = pick_candidates(
                ranked,
                old_kbps,
                include_lossless=include_lossless,
                min_score=min_score,
                avoid=extensions_of(settings.get('avoid_formats') or ()),
            )
            if picked:
                return picked
    return []


# ── The download ────────────────────────────────────────────────────────


def fetch_candidate(
    song: dict[str, Any],
    settings: dict[str, Any],
    row: dict[str, Any],
    *,
    client: Any = None,
    progress_cb: Optional[ProgressCallback] = None,
    cancel_check: Optional[Callable[[], None]] = None,
) -> Path:
    """Download the one file *row* names (the candidate the admin chose)
    and return where slskd put it. Raises :class:`UpgradeError`."""

    client = client or slskd.SlskdClient(settings)
    if not client.configured() or not client.can_connect():
        raise UpgradeError('slskd_unreachable')
    username = str(row.get('username') or '')
    filename = str(row.get('filename') or '')
    try:
        expected = int(row.get('size') or 0)
    except (TypeError, ValueError):
        expected = 0
    roots = slskd._search_roots(settings, client)
    with slskd._slskd_semaphore(settings):
        if not client.enqueue_download(row):
            raise UpgradeError('enqueue_failed')
        if progress_cb is not None:
            progress_cb(36.0, 'slskd · queued', 'slskd')
        found = slskd._wait_for_slskd_file(
            client,
            song,
            username,
            filename,
            settings,
            roots,
            expected_size=expected,
            progress_cb=progress_cb,
            cancel_check=cancel_check,
            deadline=slskd._slskd_deadline(settings),
        )
        if found is None:
            found = slskd._resolve_downloaded_file(
                roots,
                song,
                filename,
                username=username,
                expected_size=expected,
            )
    if found is None:
        raise UpgradeError('transfer_failed')
    if not slskd.verify_downloaded_file_matches_spotify(
        found, slskd.snapshot_spotify_metadata(song)
    ):
        discard_transfer(found, settings)
        raise UpgradeError('tag_mismatch', found.name)
    return found


# ── Placing the new copy ────────────────────────────────────────────────


def target_path(old: Path, new_suffix: str) -> Path:
    """Where the new copy goes, beside *old*, never on its path."""

    suffix = new_suffix.lower()
    if suffix != old.suffix.lower():
        plain = old.with_suffix(suffix)
        if not plain.exists():
            return plain
    candidate = old.with_name(f'{old.stem}{HQ_SUFFIX}{suffix}')
    number = 2
    while candidate.exists():
        candidate = old.with_name(f'{old.stem}{HQ_SUFFIX} {number}{suffix}')
        number += 1
    return candidate


def _length(path: Path) -> float:
    return float(read_audio_metadata(path).get('duration') or 0.0)


def _decodes(path: Path) -> bool:
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        return True
    try:
        subprocess.run(
            [ffmpeg, '-nostdin', '-v', 'error', '-xerror', '-i', str(path)]
            + ['-map', '0:a:0', '-f', 'null', '-'],
            check=True,
            capture_output=True,
            timeout=300,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return True


def check_quality(old: Path, new: Path) -> dict[str, Any]:
    """Whether *new* really is a better copy of *old*: readable audio, the
    same length, and a higher bitrate than *old* (a peer's listing can be
    wrong, or list nothing). Raises :class:`UpgradeError`."""

    old_meta = read_audio_metadata(old)
    new_meta = read_audio_metadata(new)
    new_length = float(new_meta.get('duration') or 0)
    if new_length <= 0 or not _decodes(new):
        raise UpgradeError('unreadable')
    old_length = float(old_meta.get('duration') or 0)
    if (
        old_length
        and abs(new_length - old_length) > DURATION_TOLERANCE_SECONDS
    ):
        raise UpgradeError(
            'length_mismatch', f'{old_length:.0f}s -> {new_length:.0f}s'
        )
    old_kbps = _kbps(old_meta.get('bitrate'))
    new_kbps = _kbps(new_meta.get('bitrate'))
    lossless = str(new_meta.get('codec') or '').lower() in LOSSLESS_CODECS
    if (
        not lossless
        and new_kbps
        and (new_kbps <= old_kbps or new_kbps < ACCEPTED_KBPS * VBR_SHARE)
    ):
        raise UpgradeError('not_better', f'{old_kbps} -> {new_kbps} kbps')
    return {
        'bitrate_before': old_kbps,
        'bitrate_after': new_kbps,
        'duration_before': round(old_length, 1),
        'duration_after': round(new_length, 1),
    }


def _sidecar_text(audio: Path) -> str:
    for candidate in lyrics_mod.lrc_candidates(audio):
        if candidate.is_file():
            try:
                return candidate.read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError):
                return ''
    return ''


def transfer_tags(old: Path, new: Path) -> None:
    """Give *new* everything *old* carries: every tag as it is when the
    format is the same (cover and lyrics included); otherwise the title,
    artists, album, numbers, date, ISRC, explicit mark, cover and lyrics
    through Downtify's own tag writers. (The ``.lrc`` sidecar is copied
    by :func:`place_upgrade`, once the file has its final name.)"""

    if old.suffix.lower() == new.suffix.lower():
        copy_tags(old, new)
    else:
        meta = read_audio_metadata(old)
        song = _song_from_tags(meta)
        song['genre'] = str(meta.get('genre') or '')
        song['release_date'] = str(meta.get('release_date') or '')
        if meta.get('compilation'):
            song['compilation'] = True
        cover, _mime = extract_embedded_cover(old)
        embed_metadata(
            new, song, download_cover=bool(cover), cover_bytes=cover
        )
        if meta.get('isrc'):
            isrc_mod.write(new, str(meta['isrc']))
        found = lyrics_mod.read_track_lyrics(old)
        plain = str(found.get('plain') or '')
        if plain:
            lyrics_mod.write_to_file(new, lyrics_mod.Lyrics(plain=plain))


def place_upgrade(old: Path, downloaded: Path) -> tuple[Path, dict[str, Any]]:
    """Copy *downloaded* in beside *old* with *old*'s tags and date, after
    :func:`check_quality`. ``(the new file, its quality figures)``. The
    old file is not touched; a failure leaves nothing behind."""

    if not old.is_file():
        raise UpgradeError('missing')
    if not downloaded.is_file():
        raise UpgradeError('transfer_failed')
    stat = old.stat()
    suffix = downloaded.suffix.lower() or old.suffix.lower()
    staged = old.with_name(f'{old.stem}{UPGRADE_STAGING_MARKER}.lowbr{suffix}')
    final: Optional[Path] = None
    try:
        shutil.copy2(downloaded, staged)
        figures = check_quality(old, staged)
        transfer_tags(old, staged)
        if _length(staged) <= 0:
            raise UpgradeError('unreadable')
        final = target_path(old, suffix)
        # Never over an existing file (checked again right before).
        if final.exists():
            raise UpgradeError('target_exists', final.name)
        os.replace(str(staged), str(final))
    except UpgradeError:
        staged.unlink(missing_ok=True)
        raise
    except Exception as exc:
        staged.unlink(missing_ok=True)
        logger.opt(exception=True).warning(
            'Low bitrate: placing the new copy of {} failed', old.name
        )
        raise UpgradeError('write_failed', str(exc)) from exc
    synced = _sidecar_text(old)
    if synced:
        try:
            lyrics_mod.lrc_path_for(final).write_text(synced, encoding='utf-8')
        except OSError:
            logger.warning('Low bitrate: .lrc of {} not copied', old.name)
    try:
        # Not "recently added": it is the same song, kept where it was.
        os.utime(str(final), ns=(stat.st_atime_ns, stat.st_mtime_ns))
    except OSError:
        pass
    return final, figures


def discard_new_copy(path: Path) -> None:
    """Take a placed copy back out (the merge that should follow it was
    refused), with its ``.lrc``."""

    for sidecar in lyrics_mod.lrc_candidates(path):
        if sidecar.is_file() and sidecar.stem == path.stem:
            sidecar.unlink(missing_ok=True)
    path.unlink(missing_ok=True)


def discard_transfer(path: Path, settings: dict[str, Any]) -> bool:
    """Delete a downloaded copy that was refused (a different song, not
    better, unreadable), so it doesn't turn up in the library from
    slskd's folder. Only a file inside slskd's ``source_dir`` is touched.
    Whether it was deleted."""

    try:
        root = Path(str(settings.get('source_dir') or '')).resolve(strict=True)
        source = path.resolve(strict=True)
    except OSError:
        return False
    if (
        not str(settings.get('source_dir') or '').strip()
        or path.is_symlink()
        or not source.is_file()
        or not source.is_relative_to(root)
    ):
        return False
    try:
        source.unlink()
    except OSError:
        logger.warning('Low bitrate: refused copy {} kept', source.name)
        return False
    logger.info('Low bitrate: refused copy {} deleted', source.name)
    return True
