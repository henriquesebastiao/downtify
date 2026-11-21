"""The AI helper's tools for the Doctor's other sections.

:mod:`downtify.doctor_ai` holds the helper itself and the duplicate
playlists. This module adds, the same way (read, compare, suggest with a
reason, the user applies):

* **Duplicate songs** - the Doctor's groups, a search over the whole
  library (a remix or a live version is never in a group: its length
  differs), each file's details, an audio comparison and a MusicBrainz
  lookup, then "keep this copy" or "these are different songs".
* **Downloaded again under a new Spotify ID** - the full list; the extra
  files are fixed with the same "keep this copy".
* **slskd leftovers** - run the check and suggest deleting the copies it
  verified identical to a library file.
* **Navidrome** - the problems found and the page's own plan, and a
  suggestion of which flagged Navidrome playlists to delete.

Every repair still runs through :mod:`downtify.doctor_routes`, with its
checks, the music trash, backups and the "check again first" locks.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException
from loguru import logger

from . import api, doctor_ai, isrc, musicbrainz, trash_routes
from .doctor import STATUS_VERIFIED, norm, relinked_tracks
from .doctor_ai import (
    ToolError,
    _doctor,
    _http_error,
    _int_arg,
    _last_health,
    _reason_arg,
    helper,
)
from .duplicate_merge import MergeError, plan_merge
from .library_catalog import resolve_library_file
from .library_trash import TrashError, identity_keys
from .library_upgrade import has_lyrics
from .library_usage import provider_of

#: At most this many copies in one "keep" suggestion (the Doctor's own
#: merge limit, plus the kept one).
MAX_COPIES = 21

_MERGE_CODES = {
    'dedupe_invalid': 'Pick one copy to keep and at least one other copy.',
    'dedupe_missing': 'One of these files is not in the library',
    'dedupe_replacement_pending': (
        'Replace audio is still working on one of these files'
    ),
}


# ---------------------------------------------------------------------------
# Library helpers
# ---------------------------------------------------------------------------


def _inputs() -> dict[str, Any]:
    return api._usage_library_inputs(api.library_context())


def _playlists_by_file() -> dict[str, list[str]]:
    dr = _doctor()
    out: dict[str, list[str]] = {}
    for info in dr._m3u_infos(dr._ctx()):
        for stored in info.entries:
            names = out.setdefault(norm(stored), [])
            if info.name not in names:
                names.append(info.name)
    return out


def _row(entry: dict[str, Any], providers: dict[str, str]) -> dict[str, Any]:
    name = norm(entry.get('file'))
    try:
        size = max(0, int(entry.get('size') or 0))
    except (TypeError, ValueError):
        size = 0
    try:
        duration = float(entry.get('duration') or 0)
    except (TypeError, ValueError):
        duration = 0.0
    return {
        'file': name,
        'bytes': size,
        'provider': provider_of(name, providers),
        'codec': str(entry.get('codec') or ''),
        'bitrate': int(entry.get('bitrate') or 0),
        'title': str(entry.get('title') or ''),
        'artist': str(entry.get('artist') or ''),
        'album': str(entry.get('album') or ''),
        'duration': duration,
    }


def _rows_for(files: list[str]) -> list[dict[str, Any]]:
    """The Doctor's card rows of *files*, in that order, with the
    playlists each is in. Raises :class:`ToolError` for a stranger."""

    inputs = _inputs()
    by_file = {norm(e.get('file')): e for e in inputs['entries']}
    playlists = _playlists_by_file()
    rows = []
    for name in files:
        entry = by_file.get(norm(name))
        if entry is None:
            raise ToolError(
                f'{name!r} is not a library file (use search_library).'
            )
        row = _row(entry, inputs['providers'])
        row['playlists'] = sorted(playlists.get(row['file'], []))
        rows.append(row)
    return rows


def _full_path(stored: str) -> Optional[Path]:
    try:
        return resolve_library_file(stored, api.library_context())
    except Exception:
        return None


def _files_arg(
    args: dict[str, Any], name: str = 'files', least: int = 1
) -> list[str]:
    raw = args.get(name)
    if not isinstance(raw, list):
        raise ToolError(f'"{name}" must be a list of library file paths.')
    files = list(dict.fromkeys(norm(f) for f in raw if norm(f)))
    if len(files) < least:
        raise ToolError(f'Give at least {least} different file(s).')
    if len(files) > MAX_COPIES:
        raise ToolError(f'At most {MAX_COPIES} files at a time.')
    return files


def _grouped(files: list[str]) -> bool:
    """Whether the last health check put all *files* in one group."""

    groups = _doctor()._state.get('duplicates') or {}
    found = {groups.get(norm(f)) for f in files}
    return None not in found and len(found) == 1


def _check_fresh(section: str) -> None:
    if section in _doctor()._stale:
        raise ToolError(
            f'The {section} section is out of date after a repair: call '
            'run_health_check before suggesting more there.'
        )


def _add(suggestion: dict[str, Any]) -> dict[str, Any]:
    try:
        return helper.add(suggestion)
    except ValueError as exc:
        code = str(exc)
        if code.startswith('already_suggested:'):
            raise ToolError(
                f'{code.split(":", 1)[1]!r} is already in a waiting '
                'suggestion; withdraw that one first.'
            ) from None
        raise ToolError('Too many waiting suggestions.') from None


#: Why the music trash would refuse a copy, in words for the assistant.
TRASH_REASONS = {
    'identity_uncertain': (
        'it has no Spotify, Deezer or YouTube id, no ISRC, and its title, '
        'artist and album tags are not all filled in, so the trash could '
        'not be sure to restore the right song'
    ),
    'unsupported_collection': "its folder isn't covered by the music trash",
    'item_not_found': 'it is not in the library any more',
    'track_is_playing': 'it is playing right now (try again after)',
    'library_task_active': (
        'a library upgrade is running (try again when it is done)'
    ),
}


def trash_check(files: list[str]) -> dict[str, str]:
    """``{file: reason}`` for each copy the music trash would refuse
    (empty when it takes them all, or is off: then nothing is checked).

    The same lookup as the trash's own preview, file by file and without
    reserving anything: a merge whose copy the trash refuses stops
    before anything changes, so this says so before the user applies.
    """

    if api.state.library_trash is None:
        return {}
    refused: dict[str, str] = {}
    for name in files:
        try:
            tracks = trash_routes._selection(
                trash_routes.Selection(files=[name])
            )
        except TrashError as exc:
            refused[name] = str(exc) or 'unknown'
            continue
        except Exception:
            # Only a heads-up: the trash checks again when applying.
            logger.opt(exception=True).debug('doctor ai: trash check')
            continue
        if not any(identity_keys(t.get('metadata') or {}) for t in tracks):
            refused[name] = 'identity_uncertain'
    return refused


def _trash_words(reason: str) -> str:
    return TRASH_REASONS.get(reason, reason)


# ---------------------------------------------------------------------------
# Duplicate songs
# ---------------------------------------------------------------------------


async def tool_list_duplicate_songs(args: dict[str, Any]) -> dict[str, Any]:
    last = _last_health()
    if not last['at']:
        raise ToolError('No health check yet: call run_health_check.')
    review = last['result'].get('duplicates') or {}
    groups = review.get('groups') or []
    kind = str(args.get('kind') or '')
    if kind in {'exact', 'likely'}:
        groups = [g for g in groups if g.get('kind') == kind]
    offset = _int_arg(args, 'offset', 0, 100_000)
    limit = _int_arg(args, 'limit', 25, 100) or 25
    return {
        'health_check_at': last['at'],
        'total_groups': len(groups),
        'offset': offset,
        'music_trash_on': bool(review.get('trash')),
        'groups': [
            {
                'kind': g.get('kind'),
                'artist': g.get('artist'),
                'title': g.get('title'),
                'files': [
                    {
                        'file': f['file'],
                        'format': f.get('codec'),
                        'kbps': round((f.get('bitrate') or 0) / 1000),
                        'seconds': round(f.get('duration') or 0, 1),
                        'bytes': f.get('bytes'),
                        'source': f.get('provider'),
                        'tags': {
                            'title': f.get('title'),
                            'artist': f.get('artist'),
                            'album': f.get('album'),
                        },
                        'playlists': f.get('playlists') or [],
                    }
                    for f in g.get('files') or []
                ],
            }
            for g in groups[offset : offset + limit]
        ],
        'out_of_date': 'duplicates' in _doctor()._stale,
    }


async def tool_search_library(args: dict[str, Any]) -> dict[str, Any]:
    words = str(args.get('query') or '').casefold().split()
    if not words:
        raise ToolError('Give a "query": words from the artist or title.')
    limit = _int_arg(args, 'limit', 50, 200) or 50
    inputs = await asyncio.to_thread(_inputs)
    found = []
    for entry in inputs['entries']:
        text = ' '.join(
            str(entry.get(k) or '')
            for k in ('artist', 'title', 'album', 'file')
        ).casefold()
        if all(w in text for w in words):
            row = _row(entry, inputs['providers'])
            found.append({
                'file': row['file'],
                'artist': row['artist'],
                'title': row['title'],
                'album': row['album'],
                'seconds': round(row['duration'], 1),
                'format': row['codec'],
                'kbps': round(row['bitrate'] / 1000),
                'source': row['provider'],
            })
    found.sort(key=lambda r: (r['artist'].casefold(), r['title'].casefold()))
    return {'total': len(found), 'files': found[:limit]}


def _file_details(stored: str) -> dict[str, Any]:
    path = _full_path(stored)
    if path is None or not path.is_file():
        return {'file': stored, 'exists': False}
    details: dict[str, Any] = {'file': stored, 'exists': True}
    try:
        details['isrc'] = isrc.read(path) or None
    except Exception:
        details['isrc'] = None
    try:
        details['lyrics'] = (
            'synced'
            if has_lyrics(path, synced_only=True)
            else ('plain' if has_lyrics(path) else 'none')
        )
    except Exception:
        details['lyrics'] = 'unknown'
    try:
        import mutagen  # noqa: PLC0415  # only when asked

        audio = mutagen.File(str(path), easy=True)
        tags = dict(audio.tags or {}) if audio is not None else {}
        details['tags'] = {
            key: (value[0] if isinstance(value, list) and value else value)
            for key, value in tags.items()
            if key
            in {
                'title',
                'artist',
                'album',
                'albumartist',
                'date',
                'tracknumber',
                'genre',
                'version',
            }
        }
    except Exception:
        details['tags'] = {}
    return details


async def tool_song_details(args: dict[str, Any]) -> dict[str, Any]:
    files = _files_arg(args)
    if len(files) > 10:
        raise ToolError('At most 10 files at a time.')
    rows = await asyncio.to_thread(_rows_for, files)
    extra = await asyncio.to_thread(lambda: [_file_details(f) for f in files])
    trash_on = api.state.library_trash is not None
    refused = await asyncio.to_thread(trash_check, files) if trash_on else {}
    return {
        'files': [
            {
                **{k: row[k] for k in ('file', 'artist', 'title', 'album')},
                'seconds': round(row['duration'], 1),
                'format': row['codec'],
                'kbps': round(row['bitrate'] / 1000),
                'bytes': row['bytes'],
                'source': row['provider'],
                'playlists': row['playlists'],
                **{k: v for k, v in more.items() if k != 'file'},
                'music_trash': (
                    'off'
                    if not trash_on
                    else (
                        'refuses: ' + _trash_words(refused[row['file']])
                        if row['file'] in refused
                        else 'can take it'
                    )
                ),
            }
            for row, more in zip(rows, extra)
        ]
    }


async def tool_compare_audio(args: dict[str, Any]) -> dict[str, Any]:
    files = _files_arg(args, least=2)
    if len(files) > 10:
        raise ToolError('At most 10 files at a time.')
    cache = _doctor()._hash_cache()

    def digests() -> dict[str, Optional[str]]:
        out = {}
        for name in files:
            path = _full_path(name)
            out[name] = cache.digest(path) if path is not None else None
        return out

    found = await asyncio.to_thread(digests)
    same: dict[str, list[str]] = {}
    for name, digest in found.items():
        if digest:
            same.setdefault(digest, []).append(name)
    return {
        'identical_audio_groups': [g for g in same.values() if len(g) > 1],
        'unreadable': [n for n, d in found.items() if not d],
        'note': (
            'Identical audio means the decoded sound is bit-for-bit the '
            'same (tags and format aside). Different audio can still be '
            'the same recording in another format or bitrate.'
        ),
    }


def _credit(rows: Any) -> str:
    return ''.join(
        str(r.get('name') or '') + str(r.get('joinphrase') or '')
        for r in rows or []
        if isinstance(r, dict)
    )


async def tool_lookup_musicbrainz(args: dict[str, Any]) -> dict[str, Any]:
    title = str(args.get('title') or '').replace('"', ' ').strip()
    artist = str(args.get('artist') or '').replace('"', ' ').strip()
    if not title:
        raise ToolError('Give at least a "title".')
    limit = _int_arg(args, 'limit', 5, 10) or 5
    query = f'recording:"{title}"' + (
        f' AND artist:"{artist}"' if artist else ''
    )
    try:
        data = await asyncio.to_thread(
            musicbrainz._get, 'recording', query=query, limit=limit
        )
    except musicbrainz.MusicBrainzError as exc:
        raise ToolError(f'MusicBrainz: {exc}') from None
    out = []
    for rec in data.get('recordings') or []:
        releases = []
        for rel in (rec.get('releases') or [])[:5]:
            group = rel.get('release-group') or {}
            releases.append({
                'title': rel.get('title'),
                'status': rel.get('status'),
                'type': group.get('primary-type'),
                'secondary_types': group.get('secondary-types') or [],
                'date': rel.get('date'),
                'country': rel.get('country'),
            })
        length = rec.get('length')
        out.append({
            'title': rec.get('title'),
            'artist': _credit(rec.get('artist-credit')),
            'disambiguation': rec.get('disambiguation') or '',
            'seconds': round(length / 1000, 1) if length else None,
            'isrcs': rec.get('isrcs') or [],
            'score': rec.get('score'),
            'releases': releases,
        })
    return {'recordings': out}


def _song_group(rows: list[dict[str, Any]], grouped: bool) -> dict[str, Any]:
    first = rows[0]
    kind = 'assistant'
    if grouped:
        review = (_last_health()['result'].get('duplicates') or {}).get(
            'groups'
        ) or []
        names = {r['file'] for r in rows}
        kind = next(
            (
                g.get('kind')
                for g in review
                if names <= {f['file'] for f in g.get('files') or []}
            ),
            'likely',
        )
    return {
        'kind': kind,
        'artist': first['artist'],
        'title': first['title'],
        'files': rows,
    }


async def tool_suggest_keep_song(args: dict[str, Any]) -> dict[str, Any]:
    _check_fresh('duplicates')
    keep = norm(args.get('keep'))
    if not keep:
        raise ToolError('Give "keep": the one copy to keep.')
    remove = [f for f in _files_arg(args, 'remove') if f != keep]
    if not remove:
        raise ToolError('"remove" must list the other copies.')
    reason = _reason_arg(args)
    ctx = api.library_context()
    try:
        await asyncio.to_thread(plan_merge, keep, remove, ctx)
    except MergeError as exc:
        text = _MERGE_CODES.get(exc.code, f'Downtify refused: {exc.code}')
        raise ToolError(
            f'{text}{": " + exc.file if exc.file else ""}.'
        ) from None
    refused = await asyncio.to_thread(trash_check, remove)
    if refused:
        name, reason = next(iter(refused.items()))
        hint = (
            ' Ways out: keep that copy instead (if it is the one to keep), '
            'leave this song as it is, have the user fill in its tags '
            '(Library > Upgrade library can add ISRCs to older files), or '
            'have the user turn the music trash off (copies are then '
            'deleted for good).'
            if reason == 'identity_uncertain'
            else ''
        )
        raise ToolError(
            f'The music trash would refuse {name!r}: {_trash_words(reason)}. '
            'Applying would stop before changing anything.' + hint
        )
    rows = await asyncio.to_thread(_rows_for, [keep, *remove])
    grouped = _grouped([keep, *remove])
    trash = api.state.library_trash is not None
    entry = _add({
        'kind': 'songs',
        'decision': 'keep',
        'paths': [keep, *remove],
        'keep': keep,
        'remove': remove,
        'grouped': grouped,
        'permanent': not trash,
        'reason': reason,
        'group': _song_group(rows, grouped),
    })
    return {
        'suggestion': entry['id'],
        'keep': keep,
        'remove': remove,
        'found_by_doctor': grouped,
        'removed_copies_go_to': 'the music trash (30 days)'
        if trash
        else 'nowhere: deleted for good (the music trash is off)',
        'note': 'Waiting for the user in Settings > Doctor > AI helper.',
    }


async def tool_suggest_different_songs(args: dict[str, Any]) -> dict[str, Any]:
    _check_fresh('duplicates')
    files = _files_arg(args, least=2)
    reason = _reason_arg(args)
    if not _grouped(files):
        raise ToolError(
            'The Doctor did not group these files, so there is nothing to '
            'keep apart: just leave them.'
        )
    rows = await asyncio.to_thread(_rows_for, files)
    entry = _add({
        'kind': 'songs',
        'decision': 'apart',
        'paths': files,
        'grouped': True,
        'reason': reason,
        'group': _song_group(rows, True),
    })
    return {'suggestion': entry['id'], 'decision': 'different songs'}


async def tool_list_new_spotify_id_repeats(
    args: dict[str, Any],
) -> dict[str, Any]:
    db = api.state.monitor_db
    if db is None:
        return {'songs': 0, 'examples': []}
    offset = _int_arg(args, 'offset', 0, 100_000)
    limit = _int_arg(args, 'limit', 50, 200) or 50

    def compute() -> dict[str, Any]:
        names = {p.id: p.name for p in db.list_playlists()}
        listing = {norm(e.get('file')): e for e in _inputs()['entries']}
        return relinked_tracks(
            db.list_all_downloaded_tracks(), names, listing, limit=None
        )

    found = await asyncio.to_thread(compute)
    songs = found.get('examples') or []
    return {
        'songs': found.get('songs'),
        'extra_files': found.get('extra_files'),
        'per_watch': found.get('playlists'),
        'offset': offset,
        'repeats': songs[offset : offset + limit],
        'note': (
            'Each repeat is one song a watch downloaded under several '
            'Spotify ids, in several files. Fix one with suggest_keep_song '
            '(keep the best file, remove the others).'
        ),
    }


def _song_steps(chosen: list[dict[str, Any]], user_id: int):
    dr = _doctor()
    steps = []
    for s in chosen:
        if s['decision'] == 'keep':
            payload = dr.DuplicateMerge(keep=s['keep'], remove=s['remove'])

            async def start(payload=payload, grouped=s['grouped']):
                return dr.start_dedupe(payload, user_id, grouped=grouped)

        else:
            files = dr.DuplicateFiles(files=s['paths'])

            async def start(files=files):
                await dr.duplicates_keep(files)

        steps.append(([s['id']], start))
    return steps


# ---------------------------------------------------------------------------
# slskd leftovers
# ---------------------------------------------------------------------------


async def tool_get_slskd_leftovers(args: dict[str, Any]) -> dict[str, Any]:
    dr = _doctor()
    health = _last_health()['result'].get('slskd') or {}
    copies = dr._state.get('copies') or {}
    status = str(args.get('status') or '')
    rows = [r for r in copies.values() if not status or r.status == status]
    rows.sort(key=lambda r: (-r.bytes, r.file))
    offset = _int_arg(args, 'offset', 0, 1_000_000)
    limit = _int_arg(args, 'limit', 50, 500) or 50
    summary: dict[str, dict[str, int]] = {}
    for r in copies.values():
        bucket = summary.setdefault(r.status, {'files': 0, 'bytes': 0})
        bucket['files'] += 1
        bucket['bytes'] += r.bytes
    return {
        'files_left_in_slskd_folder': health.get('in_place', False),
        'leftovers_in_health_check': health.get('leftovers'),
        'checked': bool(copies),
        'summary': summary,
        'downloads_held': bool(dr._state.get('hold')),
        'offset': offset,
        'files': [r.as_dict() for r in rows[offset : offset + limit]],
        'note': (
            'Only "verified" leftovers (the same audio as a library file) '
            'can be deleted. Run run_slskd_check first if not checked.'
        ),
    }


async def tool_run_slskd_check(args: dict[str, Any]) -> dict[str, Any]:
    dr = _doctor()
    wait = _int_arg(args, 'wait_seconds', 120, 600)
    if dr._busy():
        raise ToolError('The Doctor is busy: call get_job and try later.')
    try:
        job = await dr.slskd_scan()
    except HTTPException as exc:
        raise _http_error(exc) from None
    loop = asyncio.get_running_loop()
    deadline = loop.time() + wait
    while loop.time() < deadline:
        if dr._job.get('id') != job['id'] or dr._job.get('state') != 'running':
            break
        await asyncio.sleep(1)
    view = await doctor_ai.tool_get_job({})
    leftovers = await tool_get_slskd_leftovers({'limit': 20})
    leftovers['doctor_job'] = view['doctor_job']
    return leftovers


async def tool_resume_downloads(_args: dict[str, Any]) -> dict[str, Any]:
    """The page's "Keep files and resume downloads"."""

    result = await _doctor().slskd_release()
    return {
        'downloads_held': bool(_doctor()._state.get('hold')),
        'queue': result.get('queue'),
    }


async def tool_suggest_slskd_clean(args: dict[str, Any]) -> dict[str, Any]:
    _check_fresh('slskd')
    dr = _doctor()
    copies = dr._state.get('copies') or {}
    verified = {n: r for n, r in copies.items() if r.status == STATUS_VERIFIED}
    if not verified:
        raise ToolError(
            'No verified leftovers: run run_slskd_check first (or nothing '
            'is safe to delete).'
        )
    everything = args.get('all_verified') is True
    if everything:
        chosen = list(verified.values())
    else:
        files = args.get('files')
        if not isinstance(files, list) or not files:
            raise ToolError('List "files", or set "all_verified": true.')
        missing = [f for f in files if f not in verified]
        if missing:
            raise ToolError(
                f'{missing[0]!r} is not a verified leftover; only those '
                'can be deleted.'
            )
        chosen = [verified[f] for f in dict.fromkeys(files)]
    reason = _reason_arg(args)
    chosen.sort(key=lambda r: (-r.bytes, r.file))
    entry = _add({
        'kind': 'slskd',
        'decision': 'clean',
        'paths': ['slskd:*']
        if everything
        else ['slskd:' + r.file for r in chosen],
        'files': [] if everything else [r.file for r in chosen],
        'reason': reason,
        'preview': [r.as_dict() for r in chosen[:50]],
        'count': len(chosen),
        'bytes': sum(r.bytes for r in chosen),
    })
    return {
        'suggestion': entry['id'],
        'files': len(chosen),
        'bytes': sum(r.bytes for r in chosen),
    }


def _slskd_steps(chosen: list[dict[str, Any]], _user_id: int):
    dr = _doctor()
    everything = any(not s['files'] for s in chosen)
    files = [] if everything else [f for s in chosen for f in s['files']]

    async def start():
        return await dr.slskd_clean(dr.Cleanup(files=files))

    return [([s['id'] for s in chosen], start)]


# ---------------------------------------------------------------------------
# Navidrome
# ---------------------------------------------------------------------------


def navidrome_plan(nd: dict[str, Any]) -> dict[str, Any]:
    """The page's own plan (DoctorSettings.vue ``navidromePlan``)."""

    remove: list[str] = []
    blocked: list[str] = []
    for dup in nd.get('duplicates') or []:
        members = dup.get('members') or []
        imports = [m for m in members if m.get('kind') == 'import']
        ours = [m for m in members if m.get('kind') == 'downtify']
        live = [m for m in imports if m.get('m3u_exists')]
        remove += [m['id'] for m in imports if not m.get('m3u_exists')]
        if live:
            best = max(m.get('songs') or 0 for m in live)
            for copy in ours:
                (
                    remove if (copy.get('songs') or 0) <= best else blocked
                ).append(copy['id'])
        elif len(ours) > 1:
            keep = max(ours, key=lambda m: m.get('songs') or 0)
            remove += [m['id'] for m in ours if m is not keep]
    remove += [o['id'] for o in nd.get('orphans') or []]
    pairs = any(
        d.get('reason') == 'm3u_and_api' for d in nd.get('duplicates') or []
    )
    return {
        'delete': list(dict.fromkeys(remove)),
        'kept_because_bigger': blocked,
        'enable_m3u_import': pairs and not nd.get('m3u_import'),
    }


async def tool_get_navidrome_issues(_args: dict[str, Any]) -> dict[str, Any]:
    nd = _last_health()['result'].get('navidrome')
    if nd is None:
        raise ToolError('No health check yet: call run_health_check.')
    if not nd.get('enabled'):
        return {'enabled': False, 'note': 'Navidrome is not set up.'}
    if not nd.get('reachable', True):
        return {'enabled': True, 'reachable': False}
    return {
        'enabled': True,
        'admin_login_set': nd.get('admin'),
        'm3u_import_on': nd.get('m3u_import'),
        'playlists': nd.get('playlists'),
        'songs': nd.get('songs'),
        'duplicates': nd.get('duplicates') or [],
        'orphans': nd.get('orphans') or [],
        'incomplete': nd.get('incomplete') or [],
        'song_duplicates': nd.get('song_duplicates'),
        'deletable_ids': sorted(_doctor()._state.get('flagged') or []),
        'page_plan': navidrome_plan(nd),
        'note': (
            'kind "import" = Navidrome imported it from an M3U file; '
            '"downtify" = Downtify created it through the API. Only '
            'playlists in deletable_ids can be deleted.'
        ),
        'out_of_date': 'navidrome' in _doctor()._stale,
    }


async def tool_suggest_navidrome_cleanup(
    args: dict[str, Any],
) -> dict[str, Any]:
    _check_fresh('navidrome')
    nd = _last_health()['result'].get('navidrome') or {}
    flagged = _doctor()._state.get('flagged') or set()
    ids = args.get('delete')
    if not isinstance(ids, list):
        raise ToolError('"delete" must list Navidrome playlist ids.')
    ids = list(dict.fromkeys(str(i) for i in ids if str(i)))
    unknown = [i for i in ids if i not in flagged]
    if unknown:
        raise ToolError(
            f'{unknown[0]!r} was not flagged by the health check; only '
            'flagged playlists can be deleted.'
        )
    enable = args.get('enable_m3u_import') is True
    if not ids and not enable:
        raise ToolError('Nothing to do: list ids, or enable M3U import.')
    reason = _reason_arg(args)
    by_id: dict[str, dict[str, Any]] = {}
    for dup in nd.get('duplicates') or []:
        for m in dup.get('members') or []:
            by_id[m['id']] = m
    for o in nd.get('orphans') or []:
        by_id.setdefault(o['id'], o)
    entry = _add({
        'kind': 'navidrome',
        'decision': 'delete',
        'paths': ['nd:' + i for i in ids] + (['nd:import'] if enable else []),
        'delete': ids,
        'enable_m3u_import': enable,
        'reason': reason,
        'playlists': [
            {
                k: by_id.get(i, {}).get(k)
                for k in ('id', 'name', 'songs', 'kind', 'm3u', 'm3u_exists')
            }
            | {'id': i}
            for i in ids
        ],
    })
    return {
        'suggestion': entry['id'],
        'delete': len(ids),
        'enable_m3u_import': enable,
    }


def _navidrome_steps(chosen: list[dict[str, Any]], _user_id: int):
    dr = _doctor()
    payload = dr.NavidromeRepair(
        delete=list(dict.fromkeys(i for s in chosen for i in s['delete'])),
        enable_m3u_import=any(s['enable_m3u_import'] for s in chosen),
    )

    async def start():
        return await dr.navidrome_repair(payload)

    return [([s['id'] for s in chosen], start)]


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def _schema(props: dict[str, Any], required: list[str] = ()) -> dict:
    schema: dict[str, Any] = {'type': 'object', 'properties': props}
    if required:
        schema['required'] = list(required)
    return schema


_PAGE = {
    'offset': {'type': 'integer', 'minimum': 0, 'default': 0},
    'limit': {'type': 'integer', 'minimum': 1},
}
_FILES = {'type': 'array', 'items': {'type': 'string'}}
_READ = {'readOnlyHint': True}
_SUGGEST = {'readOnlyHint': False, 'destructiveHint': False}

TOOLS = [
    {
        'name': 'list_duplicate_songs',
        'description': (
            'Duplicate songs from the last health check: groups of files '
            'with the same artist, title and length ("exact" = the same '
            'file content, "likely" = same song). Each copy with format, '
            'bitrate, length, source, its own tags and its playlists.'
        ),
        'inputSchema': _schema({
            **_PAGE,
            'kind': {'type': 'string', 'enum': ['exact', 'likely']},
        }),
        'annotations': _READ,
        'run': tool_list_duplicate_songs,
    },
    {
        'name': 'search_library',
        'description': (
            'Find library files whose artist, title, album or path holds '
            'every word of "query". Use it to find versions the Doctor '
            'does not group: remixes, live, sped up, other lengths.'
        ),
        'inputSchema': _schema(
            {'query': {'type': 'string'}, 'limit': {'type': 'integer'}},
            ['query'],
        ),
        'annotations': _READ,
        'run': tool_search_library,
    },
    {
        'name': 'song_details',
        'description': (
            'Up to 10 library files in detail: tags (album, date, track, '
            'version), ISRC, lyrics (synced / plain / none), length, '
            'format, source and the playlists each is in.'
        ),
        'inputSchema': _schema({'files': _FILES}, ['files']),
        'annotations': _READ,
        'run': tool_song_details,
    },
    {
        'name': 'compare_audio',
        'description': (
            'Whether 2-10 library files hold bit-for-bit the same decoded '
            "audio (the Doctor's audio fingerprint). Can take a while."
        ),
        'inputSchema': _schema({'files': _FILES}, ['files']),
        'annotations': _READ,
        'run': tool_compare_audio,
    },
    {
        'name': 'lookup_musicbrainz',
        'description': (
            'Search MusicBrainz recordings by title (and artist): each '
            'with its length, ISRCs, disambiguation (remix, live, ...) '
            'and releases (official / bootleg, album / single / '
            'compilation, date). Use it to tell the original from other '
            'versions.'
        ),
        'inputSchema': _schema(
            {
                'title': {'type': 'string'},
                'artist': {'type': 'string'},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 10},
            },
            ['title'],
        ),
        'annotations': _READ,
        'run': tool_lookup_musicbrainz,
    },
    {
        'name': 'suggest_keep_song',
        'description': (
            'Suggest keeping one copy of a song and removing the others. '
            'On Apply, everything that used the others (playlists, likes, '
            'watches, the Spotify id index) moves to the kept copy first; '
            'then they go to the music trash (or are deleted for good if '
            'it is off). The copies need not be a Doctor group: a remix '
            'or live version you found can be folded into the original. '
            '"reason" is shown to the user.'
        ),
        'inputSchema': _schema(
            {
                'keep': {'type': 'string'},
                'remove': _FILES,
                'reason': {'type': 'string'},
            },
            ['keep', 'remove', 'reason'],
        ),
        'annotations': _SUGGEST,
        'run': tool_suggest_keep_song,
    },
    {
        'name': 'suggest_different_songs',
        'description': (
            'Suggest that the files of a Doctor duplicate group are '
            'different songs, so the Doctor stops listing them.'
        ),
        'inputSchema': _schema(
            {'files': _FILES, 'reason': {'type': 'string'}},
            ['files', 'reason'],
        ),
        'annotations': _SUGGEST,
        'run': tool_suggest_different_songs,
    },
    {
        'name': 'list_new_spotify_id_repeats',
        'description': (
            'Songs a watch downloaded again because Spotify gave the same '
            'song a new id: the watch, the song, its files and ids.'
        ),
        'inputSchema': _schema(dict(_PAGE)),
        'annotations': _READ,
        'run': tool_list_new_spotify_id_repeats,
    },
    {
        'name': 'get_slskd_leftovers',
        'description': (
            "Files left in slskd's folder after import, from the last "
            'slskd check: verified (same audio as a library file, safe to '
            'delete), different, unmatched, recent, unreadable.'
        ),
        'inputSchema': _schema({
            **_PAGE,
            'status': {
                'type': 'string',
                'enum': [
                    'verified',
                    'different',
                    'unmatched',
                    'unreadable',
                    'recent',
                    'missing',
                ],
            },
        }),
        'annotations': _READ,
        'run': tool_get_slskd_leftovers,
    },
    {
        'name': 'run_slskd_check',
        'description': (
            "Check slskd's leftovers against the library (deletes "
            'nothing). New downloads wait while it runs and until the '
            'leftovers are cleaned or resume_downloads is called (at '
            'most an hour): call it when nothing will be cleaned now.'
        ),
        'inputSchema': _schema({
            'wait_seconds': {'type': 'integer', 'minimum': 0, 'maximum': 600}
        }),
        'annotations': _READ,
        'run': tool_run_slskd_check,
    },
    {
        'name': 'resume_downloads',
        'description': (
            'Let new downloads run again after run_slskd_check, leaving '
            "the leftovers in slskd's folder (the page's \"Keep files and "
            'resume downloads").'
        ),
        'inputSchema': _schema({}),
        'annotations': {'readOnlyHint': False, 'destructiveHint': False},
        'run': tool_resume_downloads,
    },
    {
        'name': 'suggest_slskd_clean',
        'description': (
            'Suggest deleting verified slskd leftovers (listed "files", '
            'or "all_verified": true). Only verified ones can be deleted.'
        ),
        'inputSchema': _schema(
            {
                'files': _FILES,
                'all_verified': {'type': 'boolean'},
                'reason': {'type': 'string'},
            },
            ['reason'],
        ),
        'annotations': _SUGGEST,
        'run': tool_suggest_slskd_clean,
    },
    {
        'name': 'get_navidrome_issues',
        'description': (
            'What Navidrome shows: duplicate playlists (imported M3U vs '
            "Downtify's API copy), playlists whose M3U is gone, playlists "
            'missing songs, duplicate songs, which playlists may be '
            "deleted, and the Doctor page's own plan."
        ),
        'inputSchema': _schema({}),
        'annotations': _READ,
        'run': tool_get_navidrome_issues,
    },
    {
        'name': 'suggest_navidrome_cleanup',
        'description': (
            'Suggest deleting flagged Navidrome playlists ("delete": ids) '
            'and/or turning on "Let Navidrome import the M3U playlists". '
            'Navidrome rescans afterwards.'
        ),
        'inputSchema': _schema(
            {
                'delete': {'type': 'array', 'items': {'type': 'string'}},
                'enable_m3u_import': {'type': 'boolean'},
                'reason': {'type': 'string'},
            },
            ['delete', 'reason'],
        ),
        'annotations': _SUGGEST,
        'run': tool_suggest_navidrome_cleanup,
    },
]

doctor_ai.register(TOOLS)
doctor_ai.APPLIERS.update({
    'songs': _song_steps,
    'slskd': _slskd_steps,
    'navidrome': _navidrome_steps,
})
