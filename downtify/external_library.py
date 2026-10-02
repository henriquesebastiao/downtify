"""Import audio that already lives outside Downtify's download folder.

Folders listed in Settings (``external_library.folders``) are scanned in
place — files are not copied. Tracks that already exist in the download
or slskd trees (same song, by tags) are skipped. Artist names are folded
onto names already in the library when they clearly match.
"""

from __future__ import annotations

import re
import time
import unicodedata
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from . import lyrics as lyrics_mod
from .artist_profile import profile_seed_enqueue
from .cover_sources import PREFERENCE_HIGHEST
from .image_size import image_short_side
from .itunes import fetch_genre
from .library_catalog import (
    AUDIO_EXTENSIONS,
    list_library_entries,
    resolve_library_file,
)
from .library_metadata import library_entry_for_file
from .library_paths import EXTERNAL_LIBRARY_PREFIX
from .library_paths_cache import invalidate_library_paths_cache
from .library_upgrade import (
    CATEGORY_ARTWORK,
    UpgradeOptions,
    _Artwork,
    _pick_artwork,
    _write_upgrade,
)
from .lyrics import read_track_lyrics, write_to_file

MAX_EXTERNAL_FOLDERS = 20
MAX_FOLDER_PATH_LEN = 1024
# Same ceiling as ``downloader.MAX_PARALLEL_DOWNLOADS``.
_MAX_ENRICH_WORKERS = 30
_DURATION_TOLERANCE = 5.0
_NAME_RATIO = 0.92
_LEADING_THE = re.compile(r'^the\s+', re.IGNORECASE)
_NON_ALNUM = re.compile(r'[^\w\s]', re.UNICODE)
_FEAT_TAIL = re.compile(r'\s(?:feat|ft)\.?\s.*$', re.IGNORECASE)
_REMASTER_TAIL = re.compile(r'\s-\s[^-]*remaster[^-]*$', re.IGNORECASE)
_SAME_SONG_TAG = re.compile(
    r'[([](?:(?:feat|ft|with)\b|[^)\]]*remaster)[^)\]]*[)\]]',
    re.IGNORECASE,
)


def is_external_stored(stored: str) -> bool:
    text = str(stored or '').strip().replace('\\', '/')
    return text.startswith(EXTERNAL_LIBRARY_PREFIX)


def _clean_folder_path(raw: Any) -> str:
    text = str(raw or '').strip()
    if not text or '\0' in text:
        return ''
    if len(text) > MAX_FOLDER_PATH_LEN:
        return ''
    path = Path(text)
    if not path.is_absolute():
        return ''
    return text.replace('\\', '/')


def sanitize_external_folders(raw: Any) -> list[str]:
    """Absolute paths, unique, capped — empty / relative entries dropped."""

    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, list):
        items = raw
    else:
        items = []
    folders: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = _clean_folder_path(item)
        if not cleaned:
            continue
        try:
            key = str(Path(cleaned).resolve())
        except OSError:
            key = cleaned
        if key in seen:
            continue
        seen.add(key)
        folders.append(cleaned)
        if len(folders) >= MAX_EXTERNAL_FOLDERS:
            break
    return folders


def effective_external_library(settings: dict[str, Any]) -> dict[str, Any]:
    raw = settings.get('external_library')
    if not isinstance(raw, dict):
        raw = {}
    return {'folders': sanitize_external_folders(raw.get('folders'))}


def extra_dirs_from_settings(
    settings: dict[str, Any],
    download_dir: Path,
    slskd_dir: Optional[Path] = None,
) -> tuple[Path, ...]:
    """Folders to scan, skipping ones already covered by downloads/slskd."""

    download_resolved = download_dir.resolve()
    slskd_resolved: Optional[Path] = None
    if slskd_dir is not None:
        try:
            slskd_resolved = slskd_dir.resolve()
        except OSError:
            slskd_resolved = slskd_dir
    roots: list[Path] = []
    seen: set[str] = set()
    for text in effective_external_library(settings)['folders']:
        root = Path(text)
        try:
            resolved = root.resolve()
        except OSError:
            resolved = root
        key = str(resolved)
        if key in seen:
            continue
        if _is_same_or_inside(resolved, download_resolved):
            continue
        if slskd_resolved is not None and _is_same_or_inside(
            resolved, slskd_resolved
        ):
            continue
        seen.add(key)
        roots.append(root)
    return tuple(roots)


def _is_same_or_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def fold_text(value: str) -> str:
    text = unicodedata.normalize('NFKD', str(value or ''))
    text = ''.join(char for char in text if not unicodedata.combining(char))
    return text.casefold()


def artist_match_key(name: str) -> str:
    text = fold_text(name)
    text = _LEADING_THE.sub('', text)
    text = _NON_ALNUM.sub(' ', text)
    return ' '.join(text.split())


def _compact_key(name: str) -> str:
    return artist_match_key(name).replace(' ', '')


def _title_key(title: str) -> str:
    text = fold_text(title)
    text = _SAME_SONG_TAG.sub(' ', text)
    text = _FEAT_TAIL.sub(' ', text)
    text = _REMASTER_TAIL.sub(' ', text)
    text = _NON_ALNUM.sub(' ', text)
    return ' '.join(text.split())


def _primary_artist(entry: dict[str, Any]) -> str:
    album_artist = str(entry.get('album_artist') or '').strip()
    if album_artist:
        return album_artist
    artist = str(entry.get('artist') or '').strip()
    if not artist:
        return ''
    for sep in (';', '/', ',', '\\'):
        if sep in artist:
            return artist.split(sep, 1)[0].strip()
    return artist


def song_identity(entry: dict[str, Any]) -> str:
    title = str(entry.get('title') or '').strip()
    if not title:
        stored = str(entry.get('file') or '').replace('\\', '/')
        title = Path(stored).stem
    return f'{artist_match_key(_primary_artist(entry))}|{_title_key(title)}'


def _durations_compatible(left: dict[str, Any], right: dict[str, Any]) -> bool:
    try:
        da = float(left.get('duration') or 0.0)
        db = float(right.get('duration') or 0.0)
    except (TypeError, ValueError):
        return True
    if da <= 0 or db <= 0:
        return True
    return abs(da - db) <= _DURATION_TOLERANCE


def match_artist(name: str, catalog: list[str]) -> Optional[str]:
    """Return a catalog name when *name* is the same artist, else ``None``."""

    wanted = artist_match_key(name)
    compact = _compact_key(name)
    if not wanted and not compact:
        return None
    for candidate in catalog:
        if artist_match_key(candidate) == wanted:
            return candidate
        if compact and _compact_key(candidate) == compact:
            return candidate
    if len(wanted) < 4:
        return None
    best_name = ''
    best_ratio = 0.0
    for candidate in catalog:
        other = artist_match_key(candidate)
        if not other:
            continue
        if wanted in other or other in wanted:
            return candidate
        ratio = SequenceMatcher(None, wanted, other).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_name = candidate
    if best_ratio >= _NAME_RATIO:
        return best_name
    return None


def _catalog_from_owned(owned: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for entry in owned:
        name = _primary_artist(entry)
        if not name:
            continue
        key = artist_match_key(name)
        if not key or key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names


def _replace_primary_artist(artist: str, canonical: str) -> str:
    text = str(artist or '').strip()
    if not text:
        return canonical
    for sep in ('; ', ' / ', ', ', ';', '/', ',', '\\'):
        if sep in text:
            rest = text.split(sep, 1)[1]
            joiner = sep if sep in {'; ', ' / ', ', '} else f'{sep} '
            return f'{canonical}{joiner}{rest}'
    return canonical


def _remap_entry(entry: dict[str, Any], catalog: list[str]) -> dict[str, Any]:
    primary = _primary_artist(entry)
    if not primary:
        return entry
    canonical = match_artist(primary, catalog)
    if not canonical or canonical == primary:
        return entry
    out = dict(entry)
    out['album_artist'] = canonical
    out['artist'] = _replace_primary_artist(
        str(entry.get('artist') or ''), canonical
    )
    return out


def partition_extra_entries(
    entries: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[tuple[dict[str, Any], str]],
]:
    """Split library rows into owned, imported extra, and skipped extra.

    Skip reasons: ``duplicate`` (already in downloads/slskd or another
    extra file of the same song) or ``duplicate_folder`` (same song
    twice in the extra folders).
    """

    owned: list[dict[str, Any]] = []
    extra: list[dict[str, Any]] = []
    for entry in entries:
        if is_external_stored(str(entry.get('file') or '')):
            extra.append(entry)
        else:
            owned.append(entry)
    if not extra:
        return owned, [], []

    catalog = _catalog_from_owned(owned)
    owned_by_id: dict[str, list[dict[str, Any]]] = {}
    for item in owned:
        owned_by_id.setdefault(song_identity(item), []).append(item)

    kept: list[dict[str, Any]] = []
    skipped: list[tuple[dict[str, Any], str]] = []
    seen_extra: set[str] = set()
    for entry in extra:
        remapped = _remap_entry(entry, catalog)
        ident = song_identity(remapped)
        if ident in seen_extra:
            skipped.append((remapped, 'duplicate_folder'))
            continue
        duplicates = owned_by_id.get(ident, [])
        if any(_durations_compatible(remapped, other) for other in duplicates):
            skipped.append((remapped, 'duplicate'))
            continue
        seen_extra.add(ident)
        kept.append(remapped)
    return owned, kept, skipped


def finish_library_entries(
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fold extra-folder tracks onto the rest of the library.

    Extra files that duplicate a download/slskd track (same song) are
    dropped. Artist spellings are rewritten to a name already in the
    library when the match is confident.
    """

    if not any(
        is_external_stored(str(entry.get('file') or '')) for entry in entries
    ):
        return entries
    owned, kept, _skipped = partition_extra_entries(entries)
    return owned + kept


def missing_external_folders(settings: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for text in effective_external_library(settings)['folders']:
        path = Path(text)
        try:
            ok = path.is_dir()
        except OSError:
            ok = False
        if not ok:
            missing.append(text)
    return missing


def _song_for_import(entry: dict[str, Any]) -> dict[str, Any]:
    artist = str(entry.get('artist') or '')
    artists = [part.strip() for part in artist.split(';') if part.strip()]
    if len(artists) == 1:
        text = artists[0]
        for sep in ('/', ',', ';'):
            if sep in text:
                artists = [
                    part.strip() for part in text.split(sep) if part.strip()
                ]
                break
    elif not artists and artist:
        artists = [artist]
    return {
        'name': str(entry.get('title') or ''),
        'artists': artists,
        'artist': artist,
        'album_name': str(entry.get('album') or ''),
        'album_artist': str(entry.get('album_artist') or ''),
        'year': str(entry.get('year') or ''),
        'genre': str(entry.get('genre') or ''),
        'track_number': int(entry.get('track_number') or 0),
        'duration': float(entry.get('duration') or 0.0),
    }


def _row_for_import(
    stored: str, ctx: Any, full: Path
) -> tuple[dict[str, Any], Any]:
    cache = getattr(ctx, 'metadata_cache', None)
    if cache is None:
        return library_entry_for_file(stored, full), None
    rows = cache.get_entries_batch([(stored, full)])
    return (rows[0] if rows else {'file': stored}), cache


def _lyrics_for_import(
    full: Path,
    song: dict[str, Any],
    settings: dict[str, Any],
    lyrics_cache: Optional[Any],
) -> tuple[Any, bool]:
    """Return ``(lyrics, looked_up_and_missed)``.

    A sidecar already at the configured location is enough. Embedded
    tags alone are not: Sync must still write a ``.lrc`` when the user
    chose a lyrics folder (or beside the file) and that file is missing.
    """

    providers = lyrics_mod.providers_from_settings(settings)
    if not providers:
        return None, False
    dest = lyrics_mod.lrc_path_for(full)
    try:
        if dest.is_file() and dest.stat().st_size:
            return None, False
    except OSError:
        pass
    existing = read_track_lyrics(full)
    tagged = existing.get('plain') or existing.get('synced') or ''
    if lyrics_mod.looks_like_lrc(tagged):
        plain = lyrics_mod._strip_lrc_timestamps(tagged) or tagged
        return lyrics_mod.Lyrics(synced=tagged, plain=plain), False
    try:
        found = lyrics_mod.fetch(song, providers, lyrics_cache)
    except Exception:
        logger.opt(exception=True).debug(
            'External sync: lyrics fetch failed for {!r}',
            song.get('name'),
        )
        return None, True
    if found is not None and found.has_any():
        return found, False
    return None, True


def _cover_for_import(
    song: dict[str, Any],
    full: Path,
    entry: dict[str, Any],
    settings: dict[str, Any],
) -> Any:
    if not settings.get('download_cover_art', True) or entry.get('has_cover'):
        return None
    options = UpgradeOptions(
        categories=(CATEGORY_ARTWORK,),
        artwork_min_px=1,
        artwork_source=PREFERENCE_HIGHEST,
    )
    try:
        artwork = _pick_artwork(song, full, entry, options=options)
    except Exception:
        logger.opt(exception=True).debug(
            'External sync: cover lookup failed for {!r}',
            song.get('name'),
        )
        return None
    if artwork is not None and artwork.data:
        return artwork
    return None


def _genre_for_import(song: dict[str, Any]) -> str:
    if str(song.get('genre') or '').strip():
        return ''
    try:
        return fetch_genre(song) or ''
    except Exception:
        logger.opt(exception=True).debug(
            'External sync: genre lookup failed for {!r}',
            song.get('name'),
        )
        return ''


def _write_import_tags(
    full: Path, song: dict[str, Any], artwork: Any, genre: str
) -> tuple[bool, bool, str]:
    if artwork is None and not genre:
        return False, False, ''
    error = _write_upgrade(
        full,
        song,
        artwork=artwork if artwork is not None else _Artwork(),
        new_lyrics=None,
        write_tags=True,
    )
    if error:
        logger.warning('External sync: could not tag {}: {}', full.name, error)
        return False, False, 'tags'
    return artwork is not None, bool(genre), ''


def _write_import_lyrics(full: Path, new_lyrics: Any) -> bool:
    try:
        write_to_file(full, new_lyrics)
    except Exception:
        logger.opt(exception=True).warning(
            'External sync: could not embed lyrics in {}', full.name
        )
        return False
    return True


def enrich_imported_track(
    stored: str,
    ctx: Any,
    *,
    settings: dict[str, Any],
    lyrics_cache: Optional[Any] = None,
    cover_cache: Optional[Any] = None,
) -> dict[str, Any]:
    """Lyrics, cover and genre the same way a finished download would.

    Files stay in place. When the tree is writable, cover and genre go
    through the library-upgrade staging copy. When it is read-only, the
    cover is stored under ``/data/cover_cache`` and genre in the library
    metadata cache. Lyrics are written afterwards (sidecar always; tags
    only when the audio is writable).
    """

    done: dict[str, Any] = {
        'lyrics': False,
        'artwork': False,
        'genre': False,
        'error': '',
        'lyrics_missing': False,
    }
    full = resolve_library_file(stored, ctx)
    if full is None:
        done['error'] = 'missing_file'
        return done

    entry, cache = _row_for_import(stored, ctx, full)
    song = _song_for_import(entry)
    if not str(song.get('name') or '').strip():
        done['error'] = 'no_title'
        return done

    sidecar_state = lyrics_mod.relocate_lrc_sidecar(full)
    new_lyrics, lyrics_missing = _lyrics_for_import(
        full, song, settings, lyrics_cache
    )
    done['lyrics_missing'] = lyrics_missing
    if sidecar_state == 'copied' and new_lyrics is None:
        done['lyrics'] = True
    writable = lyrics_mod.can_mutate_audio(full)
    artwork = _cover_for_import(song, full, entry, settings)
    genre = _genre_for_import(song)
    if genre:
        song = {**song, 'genre': genre}
    if new_lyrics is None and artwork is None and not genre:
        return done

    overlay: dict[str, Any] = {}
    if writable:
        tagged_art, tagged_genre, tag_error = _write_import_tags(
            full, song, artwork, genre
        )
        done['artwork'] = tagged_art
        done['genre'] = tagged_genre
        if tag_error:
            done['error'] = tag_error
    else:
        if artwork is not None and artwork.data and cover_cache is not None:
            cover_cache.store(stored, full, artwork.data, 'image/jpeg')
            done['artwork'] = True
            overlay['has_cover'] = True
            overlay['cover_px'] = artwork.px or image_short_side(artwork.data)
        if genre:
            done['genre'] = True
            overlay['genre'] = genre
    if new_lyrics is not None:
        if _write_import_lyrics(full, new_lyrics):
            done['lyrics'] = True
            done['lyrics_missing'] = False
        else:
            done['error'] = 'lyrics'
    if cache is not None:
        try:
            cache.refresh(stored, full)
            if overlay:
                cache.merge_fields(stored, full, overlay)
        except Exception:
            logger.debug('External sync: metadata cache refresh failed')
    return done


def _enrich_imported_tracks(
    extra_entries: list[dict[str, Any]],
    ctx: Any,
    *,
    settings: dict[str, Any],
    lyrics_cache: Optional[Any] = None,
    cover_cache: Optional[Any] = None,
    delay_seconds: float = 0.0,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> tuple[dict[str, int], dict[str, dict[str, Any]]]:
    totals = {'lyrics': 0, 'artwork': 0, 'genre': 0}
    by_file: dict[str, dict[str, Any]] = {}
    if not extra_entries:
        return totals, by_file

    def _one(entry: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        stored = str(entry.get('file') or '')
        try:
            return stored, enrich_imported_track(
                stored,
                ctx,
                settings=settings,
                lyrics_cache=lyrics_cache,
                cover_cache=cover_cache,
            )
        except Exception:
            logger.opt(exception=True).debug(
                'External sync: enrich worker failed'
            )
            return stored, {
                'lyrics': False,
                'artwork': False,
                'genre': False,
                'error': 'enrich',
                'lyrics_missing': False,
            }

    def _record(stored: str, result: dict[str, Any], done: int) -> None:
        by_file[stored] = result
        for key in totals:
            if result.get(key):
                totals[key] += 1
        if on_progress is not None:
            on_progress(done, len(extra_entries), stored)

    delay = max(0.0, float(delay_seconds or 0))
    workers = _enrich_workers(settings)
    done = 0
    if delay <= 0:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_one, item) for item in extra_entries]
            for future in as_completed(futures):
                stored, result = _enrich_future_result(future)
                done += 1
                _record(stored, result, done)
        return totals, by_file

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for start in range(0, len(extra_entries), workers):
            if start:
                time.sleep(delay)
            batch = extra_entries[start : start + workers]
            futures = [pool.submit(_one, item) for item in batch]
            for future in as_completed(futures):
                stored, result = _enrich_future_result(future)
                done += 1
                _record(stored, result, done)
    return totals, by_file


def _enrich_workers(settings: dict[str, Any]) -> int:
    try:
        workers = int(settings.get('max_parallel_downloads') or 3)
    except (TypeError, ValueError):
        workers = 3
    return max(1, min(workers, _MAX_ENRICH_WORKERS))


def _enrich_future_result(
    future: Future[tuple[str, dict[str, Any]]],
) -> tuple[str, dict[str, Any]]:
    try:
        return future.result()
    except Exception:
        logger.opt(exception=True).debug('External sync: enrich worker failed')
        return '', {
            'lyrics': False,
            'artwork': False,
            'genre': False,
            'error': 'enrich',
            'lyrics_missing': False,
        }


def count_audio_files(root: Path, extensions: frozenset[str]) -> int:
    if not root.is_dir():
        return 0
    total = 0
    for path in root.rglob('*'):
        try:
            if path.is_file() and path.suffix.lower() in extensions:
                total += 1
        except OSError:
            continue
    return total


def _match_extra_artists(
    extra_entries: list[dict[str, Any]],
    owned_entries: list[dict[str, Any]],
) -> tuple[int, list[str]]:
    catalog = _catalog_from_owned(owned_entries)
    matched = 0
    new_names: list[str] = []
    seen_new: set[str] = set()
    for item in extra_entries:
        primary = _primary_artist(item)
        if not primary:
            continue
        if match_artist(primary, catalog) is not None:
            matched += 1
            continue
        key = artist_match_key(primary)
        if key and key not in seen_new:
            seen_new.add(key)
            new_names.append(primary)
    return matched, new_names


def _queue_new_artist_profiles(
    download_dir: Path,
    new_names: list[str],
    lang: str,
    image_kinds: tuple[str, ...],
) -> int:
    queued = 0
    for name in new_names:
        song = {'album_artist': name, 'artists': [name]}
        try:
            if profile_seed_enqueue(download_dir, song, lang, image_kinds):
                queued += 1
        except Exception:
            logger.opt(exception=True).debug(
                'Could not queue artist profile for {!r}', name
            )
    return queued


def _log_track(
    status: str, entry: dict[str, Any], **fields: Any
) -> dict[str, Any]:
    artist = str(
        entry.get('album_artist') or entry.get('artist') or ''
    ).strip()
    row = {
        'status': status,
        'title': str(entry.get('title') or '').strip(),
        'artist': artist,
        'file': str(entry.get('file') or ''),
    }
    row.update(fields)
    return row


def _build_sync_log(
    missing: list[str],
    skipped: list[tuple[dict[str, Any], str]],
    kept: list[dict[str, Any]],
    by_file: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    for path in missing:
        log.append({
            'status': 'missing_folder',
            'title': '',
            'artist': '',
            'file': path,
        })
    for entry, reason in skipped:
        log.append(_log_track(reason, entry))
    for entry in kept:
        stored = str(entry.get('file') or '')
        info = by_file.get(stored) or {}
        error = str(info.get('error') or '')
        log.append(
            _log_track(
                'error' if error else 'imported',
                entry,
                error=error,
                lyrics=bool(info.get('lyrics')),
                cover=bool(info.get('artwork')),
                genre=bool(info.get('genre')),
                lyrics_missing=bool(info.get('lyrics_missing')),
            )
        )
    return log


def sync_external_library(
    ctx: Any,
    *,
    download_dir: Path,
    settings: dict[str, Any],
    lang: str = 'en',
    image_kinds: tuple[str, ...] = (),
    lyrics_cache: Optional[Any] = None,
    cover_cache: Optional[Any] = None,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> dict[str, Any]:
    """Rescan extra folders, tag like a download, seed artist profiles."""

    invalidate_library_paths_cache()
    cfg = effective_external_library(settings)
    missing = missing_external_folders(settings)
    scanned = sum(
        count_audio_files(root, AUDIO_EXTENSIONS) for root in ctx.extra_dirs
    )
    raw = list_library_entries(ctx, fold_extra=False)
    owned_entries, extra_entries, skipped = partition_extra_entries(raw)
    matched, new_names = _match_extra_artists(extra_entries, owned_entries)
    try:
        delay = float(settings.get('external_sync_delay_seconds') or 0)
    except (TypeError, ValueError):
        delay = 0.0
    if on_progress is not None:
        on_progress(0, len(extra_entries), '')
    enriched, by_file = _enrich_imported_tracks(
        extra_entries,
        ctx,
        settings=settings,
        lyrics_cache=lyrics_cache,
        cover_cache=cover_cache,
        delay_seconds=delay,
        on_progress=on_progress,
    )
    queued = _queue_new_artist_profiles(
        download_dir, new_names, lang, image_kinds
    )
    log = _build_sync_log(missing, skipped, extra_entries, by_file)
    errors = sum(1 for item in log if item.get('status') == 'error')
    logger.info(
        'External library sync: scanned={} added={} lyrics={} missing={}',
        scanned,
        len(extra_entries),
        enriched['lyrics'],
        len(missing),
    )
    return {
        'folders': list(cfg['folders']),
        'folder_count': len(cfg['folders']),
        'missing': missing,
        'scanned': scanned,
        'added': len(extra_entries),
        'skipped_duplicates': len(skipped),
        'matched_artists': matched,
        'new_artists': len(new_names),
        'profiles_queued': queued,
        'lyrics_embedded': enriched['lyrics'],
        'covers_fetched': enriched['artwork'],
        'genre_tagged': enriched['genre'],
        'errors': errors,
        'log': log,
    }
