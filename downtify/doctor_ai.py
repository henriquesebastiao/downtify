"""The Doctor's AI helper: an MCP server an AI assistant connects to.

An admin starts it in Settings > Doctor > AI helper when they want an
assistant (Claude Code, Claude Desktop, any MCP client) to help clean up
the library, and stops it when they are done. While it runs, the
assistant can read what the Doctor found, run a health check, compare
playlists song by song, and *suggest* repairs with its reasons. The
suggestions show on the Doctor page as the usual cards, and run only
when the admin presses Apply there, or, when the admin switched it on,
when the assistant applies what the user agreed to in the chat.

Everything an assistant changes goes through the Doctor's own repairs
(:mod:`downtify.doctor_routes`), so its checks, backups and "check
again first" locks still hold.

The server speaks the MCP "Streamable HTTP" transport in its simplest
form: one ``POST`` per JSON-RPC message, answered with plain JSON (no
event stream, no sessions). Only what tools need is implemented:
``initialize``, ``ping``, ``tools/list`` and ``tools/call``.

The helper is off until started, holds its state in memory only (a
restart turns it off and forgets its suggestions), and stops by itself
after :data:`IDLE_STOP` seconds without a request from the assistant.
Each start makes a new key; stopping throws it away.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import secrets
import threading
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Optional

from fastapi import HTTPException
from loguru import logger

from . import __version__, doctor_routes

#: The helper stops by itself after this long without an AI request.
IDLE_STOP = 2 * 60 * 60

#: MCP protocol revisions this server answers to, newest first.
PROTOCOL_VERSIONS = ('2025-11-25', '2025-06-18', '2025-03-26', '2024-11-05')

#: At most this many suggestions wait at once.
MAX_SUGGESTIONS = 500

#: Longest reason kept from the assistant.
MAX_REASON = 2000

#: Songs listed per page by ``get_playlist`` / per side by ``compare``.
PAGE = 200

# JSON-RPC error codes.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Helper:
    """Whether the helper runs, its key, and the assistant's suggestions."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self.token = ''
        self.started_at = ''
        self.last_used = 0.0
        self.last_used_at = ''
        self.client = ''
        self.can_apply = False
        self.user_id = 0
        self.suggestions: list[dict[str, Any]] = []

    # -- running ---------------------------------------------------------

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running_locked()

    def _running_locked(self) -> bool:
        if not self.token:
            return False
        if self._clock() - self.last_used > IDLE_STOP:
            logger.info('doctor ai: stopped after {} s idle', IDLE_STOP)
            self._stop_locked()
            return False
        return True

    def start(self, user_id: int = 0) -> str:
        """Start (or restart) with a new key; old suggestions are kept.
        *user_id* (the admin who started it) owns what the helper does."""

        with self._lock:
            self.user_id = int(user_id or 0)
            self.token = 'dtai_' + secrets.token_urlsafe(32)
            self.started_at = _now_iso()
            self.last_used = self._clock()
            self.last_used_at = ''
            self.client = ''
            self.can_apply = False
            return self.token

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def _stop_locked(self) -> None:
        self.token = ''
        self.started_at = ''
        self.client = ''
        self.can_apply = False

    def check(self, header: str) -> bool:
        """Whether an ``Authorization`` header carries the current key;
        a good one counts as activity."""

        scheme, _, value = str(header or '').partition(' ')
        with self._lock:
            if not self._running_locked() or scheme.lower() != 'bearer':
                return False
            if not hmac.compare_digest(value.strip(), self.token):
                return False
            self.last_used = self._clock()
            self.last_used_at = _now_iso()
            return True

    def set_client(self, info: Any) -> None:
        if isinstance(info, dict):
            name = str(info.get('name') or '').strip()[:80]
            version = str(info.get('version') or '').strip()[:40]
            with self._lock:
                self.client = f'{name} {version}'.strip()

    def status(self) -> dict[str, Any]:
        with self._lock:
            running = self._running_locked()
            idle_left = (
                max(0, int(IDLE_STOP - (self._clock() - self.last_used)))
                if running
                else 0
            )
            return {
                'running': running,
                'key': self.token if running else '',
                'started_at': self.started_at,
                'last_used_at': self.last_used_at,
                'client': self.client,
                'stops_in': idle_left,
                'can_apply': self.can_apply,
                'suggestions': [dict(s) for s in self.suggestions],
            }

    # -- suggestions -----------------------------------------------------

    def add(self, suggestion: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            waiting = [s for s in self.suggestions if s['state'] == 'waiting']
            if len(waiting) >= MAX_SUGGESTIONS:
                raise ValueError('too_many_suggestions')
            taken = {p for s in waiting for p in s['paths']}
            clash = sorted(set(suggestion['paths']) & taken)
            if clash:
                raise ValueError(f'already_suggested:{clash[0]}')
            entry = {
                'id': secrets.token_hex(4),
                'state': 'waiting',
                'created_at': _now_iso(),
                'job': '',
                'error': None,
                **suggestion,
            }
            self.suggestions.append(entry)
            return dict(entry)

    def waiting(self, ids: Optional[list[str]] = None) -> list[dict[str, Any]]:
        with self._lock:
            wanted = set(ids) if ids is not None else None
            return [
                dict(s)
                for s in self.suggestions
                if s['state'] == 'waiting'
                and (wanted is None or s['id'] in wanted)
            ]

    def update(self, ids: list[str], **fields: Any) -> None:
        with self._lock:
            for s in self.suggestions:
                if s['id'] in ids:
                    s.update(fields)

    def remove(self, ids: list[str]) -> int:
        """Drop waiting suggestions (dismissed or withdrawn)."""

        with self._lock:
            before = len(self.suggestions)
            self.suggestions = [
                s
                for s in self.suggestions
                if not (s['id'] in ids and s['state'] == 'waiting')
            ]
            return before - len(self.suggestions)

    def clear_finished(self) -> int:
        with self._lock:
            before = len(self.suggestions)
            self.suggestions = [
                s
                for s in self.suggestions
                if s['state'] in {'waiting', 'applying'}
            ]
            return before - len(self.suggestions)


helper = Helper()


# ---------------------------------------------------------------------------
# What the assistant is told
# ---------------------------------------------------------------------------

INSTRUCTIONS = """\
You are connected to the Doctor of a Downtify server: a self-hosted
music library (Spotify playlists downloaded as files, with M3U playlist
files that Navidrome and other players read). The Doctor finds leftover
problems; this helper lets you look at them, reason about them, and
suggest repairs that the user approves. Its sections:

- DUPLICATE PLAYLISTS: M3U files that hold one playlist. A merge keeps
  the file Downtify writes today ("keeper"), puts every song of all of
  them in it once, keeps a cover, backs the others up to
  /data/doctor/backups/<date>/ and removes them. Allowed only when 80%
  of the smaller playlist's songs are in the larger one. "Different
  playlists" just stops the Doctor listing a group.
- DUPLICATE SONGS: copies of one song. "Keep this copy" moves
  everything that used the others (playlists, likes, watches, the
  Spotify id index) onto the kept file, then removes the others: to the
  music trash (restorable for 30 days) when it is on, for good
  otherwise. The Doctor only groups copies with the same artist, title
  and length; use search_library to find remixes, live, sped-up or
  other versions, and song_details, compare_audio and
  lookup_musicbrainz (official releases, lengths, ISRCs) to tell the
  original from the rest. With the music trash on, a copy it can't
  identify (no id or ISRC, and no full title/artist/album tags) can't
  be removed: song_details says so per copy, and suggest_keep_song
  refuses it up front.
- NEW SPOTIFY ID REPEATS: songs a watch downloaded again because Spotify
  gave them a new id; fix them with "keep this copy".
- SLSKD LEFTOVERS: files left in slskd's folder after import. Only
  leftovers verified to hold the same audio as a library file can be
  deleted. run_slskd_check holds new downloads until they are cleaned;
  call resume_downloads when nothing will be cleaned now.
- NAVIDROME: playlists Navidrome shows twice (an imported M3U and
  Downtify's API copy), imports whose M3U is gone, and more. Only
  playlists the health check flagged can be deleted.

Work like this:
1. Call get_overview. If there is no health check, it is old, or a
   section you need is out of date, call run_health_check.
2. Look at the section the user cares about. Explain each finding in
   plain words (names, counts, lengths, what differs) and what you
   recommend and why. Ask when the user's wishes are unclear: what
   "official" or "the one to keep" means can depend on them.
3. Record each decision with a suggest_* tool and a short reason
   written for the user. Suggestions show in Downtify under Settings >
   Doctor > AI helper as the Doctor's usual cards (covers, players,
   counts), where the user presses Apply.
4. Only call apply_suggestions when get_overview says you may
   (ai_can_apply) AND the user clearly agreed in this chat to exactly
   those suggestions. Apply one section at a time: a repair puts other
   sections out of date until the next health check.

Paths are relative to the downloads folder. Keep answers short and
readable: names, counts and lengths, not raw JSON.
"""


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class ToolError(Exception):
    """A tool call the assistant should correct (shown to it as text)."""


def _doctor():
    """The Doctor's routes module (a function, so tests can swap it)."""

    return doctor_routes


def _norm(path: Any) -> str:
    return str(path or '').strip().replace('\\', '/').lstrip('/')


def _song_name(stored: str) -> str:
    """``Artist - Title`` as the file name says, without the folder."""

    return PurePosixPath(str(stored).replace('\\', '/')).stem


def _paths_arg(args: dict[str, Any], *, least: int = 2) -> list[str]:
    raw = args.get('paths')
    if not isinstance(raw, list):
        raise ToolError('"paths" must be a list of playlist file paths.')
    paths = list(dict.fromkeys(_norm(p) for p in raw if _norm(p)))
    if len(paths) < least:
        raise ToolError(f'Give at least {least} different playlist paths.')
    if len(paths) > 20:
        raise ToolError('At most 20 playlists at a time.')
    return paths


def _reason_arg(args: dict[str, Any]) -> str:
    reason = str(args.get('reason') or '').strip()
    if not reason:
        raise ToolError(
            'Add a "reason": one or two sentences for the user saying why.'
        )
    return reason[:MAX_REASON]


def _int_arg(args: dict[str, Any], name: str, default: int, top: int) -> int:
    try:
        value = int(args.get(name, default))
    except (TypeError, ValueError):
        raise ToolError(f'"{name}" must be a whole number.') from None
    return max(0, min(value, top))


def _http_error(exc: HTTPException) -> ToolError:
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    code = detail.get('code') or str(exc.detail)
    hints = {
        'rescan_first': (
            'The playlists section is out of date after a repair: call '
            'run_health_check first.'
        ),
        'doctor_busy': (
            'The Doctor is busy with another job: call get_job and try '
            'again when it is done.'
        ),
        'm3u_not_found': f'No playlist file {detail.get("path")!r}.',
        'm3u_manual': (
            f'{detail.get("path")!r} is a playlist the user made in the '
            'Library; those are never merged.'
        ),
        'need_two': 'A group needs two different playlist files.',
        'playlists_differ': (
            'These playlists share too few songs to be merged '
            f'(overlap {detail.get("overlap")}, 0.8 needed).'
        ),
        'm3u_twice': f'{detail.get("path")!r} is in two groups.',
    }
    return ToolError(hints.get(code, f'Downtify refused: {code}'))


def _last_health() -> dict[str, Any]:
    entry = _doctor()._last.get('health') or {}
    return {'at': entry.get('at', ''), 'result': entry.get('result') or {}}


async def _infos() -> dict[str, Any]:
    dr = _doctor()
    infos = await asyncio.to_thread(dr._m3u_infos, dr._ctx())
    return {i.path: i for i in infos}


async def _group(paths: list[str]):
    dr = _doctor()
    try:
        return await asyncio.to_thread(dr._group_for, paths)
    except HTTPException as exc:
        raise _http_error(exc) from None


def _job_view() -> Optional[dict[str, Any]]:
    job = _doctor()._public_job()
    if not job:
        return None
    view = {
        k: job.get(k)
        for k in ('id', 'kind', 'state', 'started_at', 'finished_at')
        if job.get(k)
    }
    view['progress'] = job.get('progress')
    if job.get('error'):
        view['error'] = job['error']
    return view


async def tool_get_overview(_args: dict[str, Any]) -> dict[str, Any]:
    dr = _doctor()
    last = _last_health()
    playlists = last['result'].get('playlists') or {}
    return {
        'health_check_at': last['at'] or None,
        'playlist_files': playlists.get('m3u'),
        'duplicate_playlist_groups': len(playlists.get('groups') or []),
        'kept_apart_groups': playlists.get('kept_apart'),
        'out_of_date_sections': sorted(dr._stale),
        'doctor_job': _job_view(),
        'ai_can_apply': helper.can_apply,
        'waiting_suggestions': len(helper.waiting()),
    }


async def tool_run_health_check(args: dict[str, Any]) -> dict[str, Any]:
    dr = _doctor()
    wait = _int_arg(args, 'wait_seconds', 60, 300)
    if dr._busy():
        raise ToolError(
            'The Doctor is busy with another job; call get_job and try '
            'again when it is done.'
        )
    try:
        job = await dr.doctor_scan()
    except HTTPException as exc:
        raise _http_error(exc) from None
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if dr._job.get('id') != job['id'] or dr._job.get('state') != 'running':
            break
        await asyncio.sleep(1)
    view = _job_view() or {}
    if view.get('state') == 'running':
        return {
            'state': 'running',
            'progress': view.get('progress'),
            'note': 'Still checking; call get_job, then get_overview.',
        }
    overview = await tool_get_overview({})
    overview['state'] = view.get('state')
    return overview


async def tool_get_job(_args: dict[str, Any]) -> dict[str, Any]:
    return {'doctor_job': _job_view()}


async def tool_list_duplicate_playlists(
    args: dict[str, Any],
) -> dict[str, Any]:
    last = _last_health()
    if not last['at']:
        raise ToolError('No health check yet: call run_health_check.')
    groups = (last['result'].get('playlists') or {}).get('groups') or []
    offset = _int_arg(args, 'offset', 0, 100_000)
    limit = _int_arg(args, 'limit', 50, 200) or 50
    waiting = {p for s in helper.waiting() for p in s['paths']}
    page = []
    for group in groups[offset : offset + limit]:
        members = group.get('members') or []
        page.append({
            'found_by': group.get('reason'),
            'paths': [m['path'] for m in members],
            'members': [
                {
                    'path': m['path'],
                    'name': m.get('name'),
                    'songs': m.get('songs'),
                    'lines_in_file': m.get('lines'),
                    'has_cover': m.get('cover'),
                }
                for m in members
            ],
            'keeper': group.get('keeper'),
            'songs_after_merge': group.get('songs_after'),
            'overlap': group.get('overlap'),
            'can_merge': bool(group.get('safe')),
            'already_suggested': any(m['path'] in waiting for m in members),
        })
    return {
        'health_check_at': last['at'],
        'total_groups': len(groups),
        'offset': offset,
        'groups': page,
        'out_of_date': 'playlists' in _doctor()._stale,
    }


async def tool_list_playlists(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get('query') or '').strip().casefold()
    offset = _int_arg(args, 'offset', 0, 100_000)
    limit = _int_arg(args, 'limit', 100, 500) or 100
    rows = (_last_health()['result'].get('playlists') or {}).get('list')
    if rows is None:
        rows = [i.as_dict() for i in (await _infos()).values()]
    if query:
        rows = [
            r
            for r in rows
            if query in str(r.get('path', '')).casefold()
            or query in str(r.get('name', '')).casefold()
        ]
    rows = sorted(rows, key=lambda r: str(r.get('path', '')).casefold())
    return {
        'total': len(rows),
        'offset': offset,
        'playlists': [
            {
                'path': r.get('path'),
                'name': r.get('name'),
                'songs': r.get('songs'),
                'made_in_library': bool(r.get('manual')),
                'has_cover': r.get('cover'),
            }
            for r in rows[offset : offset + limit]
        ],
    }


async def tool_get_playlist(args: dict[str, Any]) -> dict[str, Any]:
    path = _norm(args.get('path'))
    if not path:
        raise ToolError('Give the playlist "path" (from list_playlists).')
    infos = await _infos()
    info = infos.get(path)
    if info is None:
        raise ToolError(f'No playlist file {path!r}.')
    offset = _int_arg(args, 'offset', 0, 100_000)
    limit = _int_arg(args, 'limit', PAGE, 1000) or PAGE
    songs = info.entries[offset : offset + limit]
    return {
        **info.as_dict(),
        'missing_lines': max(0, info.lines - len(info.entries)),
        'offset': offset,
        'songs': [{'song': _song_name(s), 'file': s} for s in songs],
    }


async def tool_compare_playlists(args: dict[str, Any]) -> dict[str, Any]:
    paths = _paths_arg(args)
    group = await _group(paths)
    data = group.as_dict()
    everyone = set.intersection(*(set(m.entries) for m in group.members))
    members = []
    for member in group.members:
        others = set().union(
            *(set(m.entries) for m in group.members if m is not member)
        )
        only = [e for e in member.entries if e not in others]
        members.append({
            'path': member.path,
            'name': member.name,
            'songs': len(member.entries),
            'has_cover': member.cover,
            'kept': member.path == group.keeper.path,
            'only_here_count': len(only),
            'only_here': [_song_name(e) for e in only[:PAGE]],
        })
    return {
        'keeper': data['keeper'],
        'songs_after_merge': data['songs_after'],
        'overlap': data['overlap'],
        'can_merge': data['safe'],
        'in_all_of_them': len(everyone),
        'members': members,
    }


def _check_fresh() -> None:
    if 'playlists' in _doctor()._stale:
        raise ToolError(
            'The playlists section is out of date after a repair: call '
            'run_health_check before suggesting more.'
        )


async def _suggest(args: dict[str, Any], decision: str) -> dict[str, Any]:
    _check_fresh()
    paths = _paths_arg(args)
    reason = _reason_arg(args)
    group = await _group(paths)
    data = group.as_dict()
    # Say why these were grouped: the health check's own reason when
    # the assistant picked one of its groups, else that it chose them.
    picked = {m.path for m in group.members}
    found = (_last_health()['result'].get('playlists') or {}).get('groups')
    data['reason'] = next(
        (
            g.get('reason')
            for g in found or []
            if {m['path'] for m in g.get('members') or []} == picked
        ),
        'assistant',
    )
    data['id'] = 'ai:' + data['keeper']
    if decision == 'merge' and not data['safe']:
        raise ToolError(
            'These playlists share too few songs to be merged (overlap '
            f'{data["overlap"]}, 0.8 needed). Suggest them as different '
            'playlists, or tell the user.'
        )
    try:
        entry = helper.add({
            'kind': 'playlists',
            'decision': decision,
            'paths': [m.path for m in group.members],
            'reason': reason,
            'group': data,
        })
    except ValueError as exc:
        code = str(exc)
        if code.startswith('already_suggested:'):
            raise ToolError(
                f'{code.split(":", 1)[1]!r} is already in a waiting '
                'suggestion; withdraw that one first.'
            ) from None
        raise ToolError('Too many waiting suggestions.') from None
    return {
        'suggestion': entry['id'],
        'decision': decision,
        'keeper': data['keeper'] if decision == 'merge' else None,
        'note': (
            'Shown in Downtify under Settings > Doctor > AI helper, '
            'waiting for Apply.'
        ),
    }


async def tool_suggest_merge(args: dict[str, Any]) -> dict[str, Any]:
    return await _suggest(args, 'merge')


async def tool_suggest_different(args: dict[str, Any]) -> dict[str, Any]:
    return await _suggest(args, 'apart')


def _suggestion_view(s: dict[str, Any]) -> dict[str, Any]:
    group = s.get('group') or {}
    return {
        'id': s['id'],
        'section': s.get('kind'),
        'state': s['state'],
        'decision': s['decision'],
        'paths': s['paths'],
        'keeper': group.get('keeper') if s['decision'] == 'merge' else None,
        'reason': s['reason'],
        'error': s.get('error'),
    }


async def tool_list_suggestions(_args: dict[str, Any]) -> dict[str, Any]:
    refresh_states()
    return {
        'ai_can_apply': helper.can_apply,
        'suggestions': [
            _suggestion_view(s) for s in helper.status()['suggestions']
        ],
    }


async def tool_withdraw_suggestion(args: dict[str, Any]) -> dict[str, Any]:
    ids = args.get('ids')
    if not isinstance(ids, list) or not ids:
        raise ToolError('"ids" must list suggestion ids.')
    return {'withdrawn': helper.remove([str(i) for i in ids])}


async def tool_apply_suggestions(args: dict[str, Any]) -> dict[str, Any]:
    if not helper.can_apply:
        raise ToolError(
            'Applying from the chat is switched off in Downtify. Ask the '
            'user to press Apply under Settings > Doctor > AI helper (or '
            'to switch on "Let the assistant apply what you agree to in '
            'the chat").'
        )
    if args.get('user_agreed') is not True:
        raise ToolError(
            'Set "user_agreed": true only after the user agreed in this '
            'chat to exactly these suggestions.'
        )
    ids = args.get('ids')
    if not isinstance(ids, list) or not ids:
        raise ToolError('"ids" must list the suggestions to apply.')
    return await apply([str(i) for i in ids], by='assistant')


TOOLS: list[dict[str, Any]] = [
    {
        'name': 'get_overview',
        'description': (
            "Start here. When the Doctor's last health check ran, how "
            'many duplicate playlist groups it found, which sections are '
            'out of date, the running Doctor job, whether you may apply '
            'suggestions yourself, and how many wait.'
        ),
        'inputSchema': {'type': 'object', 'properties': {}},
        'annotations': {'readOnlyHint': True},
        'run': tool_get_overview,
    },
    {
        'name': 'run_health_check',
        'description': (
            "Run the Doctor's health check (changes nothing; it may hold "
            'new downloads for a moment). Waits up to wait_seconds for it '
            'to finish.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'wait_seconds': {
                    'type': 'integer',
                    'minimum': 0,
                    'maximum': 300,
                    'default': 60,
                },
            },
        },
        'annotations': {'readOnlyHint': True},
        'run': tool_run_health_check,
    },
    {
        'name': 'get_job',
        'description': "The Doctor's running or last job and its progress.",
        'inputSchema': {'type': 'object', 'properties': {}},
        'annotations': {'readOnlyHint': True},
        'run': tool_get_job,
    },
    {
        'name': 'list_duplicate_playlists',
        'description': (
            'Groups of playlist files the last health check thinks are '
            'one playlist (found by the same name, or by mostly the same '
            'songs), with song counts, the file a merge keeps, the '
            'overlap and whether a merge is allowed.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'offset': {'type': 'integer', 'minimum': 0, 'default': 0},
                'limit': {
                    'type': 'integer',
                    'minimum': 1,
                    'maximum': 200,
                    'default': 50,
                },
            },
        },
        'annotations': {'readOnlyHint': True},
        'run': tool_list_duplicate_playlists,
    },
    {
        'name': 'list_playlists',
        'description': (
            'Every playlist file, optionally filtered by a word in its '
            'name or path. Use it to find playlists the check did not '
            'pair.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'query': {'type': 'string'},
                'offset': {'type': 'integer', 'minimum': 0, 'default': 0},
                'limit': {
                    'type': 'integer',
                    'minimum': 1,
                    'maximum': 500,
                    'default': 100,
                },
            },
        },
        'annotations': {'readOnlyHint': True},
        'run': tool_list_playlists,
    },
    {
        'name': 'get_playlist',
        'description': (
            "One playlist file's songs (as 'Artist - Title' from the file "
            'names), in order, a page at a time.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'path': {'type': 'string'},
                'offset': {'type': 'integer', 'minimum': 0, 'default': 0},
                'limit': {
                    'type': 'integer',
                    'minimum': 1,
                    'maximum': 1000,
                    'default': PAGE,
                },
            },
            'required': ['path'],
        },
        'annotations': {'readOnlyHint': True},
        'run': tool_get_playlist,
    },
    {
        'name': 'compare_playlists',
        'description': (
            'Compare 2-20 playlist files song by song: how many songs '
            'are in all of them, which are only in one, the file a merge '
            'would keep and whether a merge is allowed.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'paths': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'minItems': 2,
                    'maxItems': 20,
                },
            },
            'required': ['paths'],
        },
        'annotations': {'readOnlyHint': True},
        'run': tool_compare_playlists,
    },
    {
        'name': 'suggest_merge',
        'description': (
            'Suggest merging these playlist files into one (the keeper). '
            'Changes nothing yet: the user sees it in Downtify and '
            'presses Apply. "reason" is shown to the user.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'paths': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'minItems': 2,
                    'maxItems': 20,
                },
                'reason': {'type': 'string'},
            },
            'required': ['paths', 'reason'],
        },
        'annotations': {'readOnlyHint': False, 'destructiveHint': False},
        'run': tool_suggest_merge,
    },
    {
        'name': 'suggest_different',
        'description': (
            'Suggest marking these playlist files as different playlists '
            'so the Doctor stops listing them together. Changes nothing '
            'yet. "reason" is shown to the user.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'paths': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'minItems': 2,
                    'maxItems': 20,
                },
                'reason': {'type': 'string'},
            },
            'required': ['paths', 'reason'],
        },
        'annotations': {'readOnlyHint': False, 'destructiveHint': False},
        'run': tool_suggest_different,
    },
    {
        'name': 'list_suggestions',
        'description': (
            'Your suggestions and their state: waiting, applying, '
            'applied, failed.'
        ),
        'inputSchema': {'type': 'object', 'properties': {}},
        'annotations': {'readOnlyHint': True},
        'run': tool_list_suggestions,
    },
    {
        'name': 'withdraw_suggestion',
        'description': 'Take back waiting suggestions.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'ids': {'type': 'array', 'items': {'type': 'string'}},
            },
            'required': ['ids'],
        },
        'annotations': {'readOnlyHint': False, 'destructiveHint': False},
        'run': tool_withdraw_suggestion,
    },
    {
        'name': 'apply_suggestions',
        'description': (
            'Apply waiting suggestions now, as one Doctor job. Only '
            'allowed when the user switched it on in Downtify '
            '(get_overview: ai_can_apply) AND agreed in this chat to '
            'exactly these suggestions.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'ids': {'type': 'array', 'items': {'type': 'string'}},
                'user_agreed': {'type': 'boolean'},
            },
            'required': ['ids', 'user_agreed'],
        },
        'annotations': {'readOnlyHint': False, 'destructiveHint': True},
        'run': tool_apply_suggestions,
    },
]

_BY_NAME: dict[str, dict[str, Any]] = {t['name']: t for t in TOOLS}


def register(tools: list[dict[str, Any]]) -> None:
    """Add more tools (:mod:`downtify.doctor_ai_sections`)."""

    for tool in tools:
        if tool['name'] not in _BY_NAME:
            TOOLS.append(tool)
            _BY_NAME[tool['name']] = tool


# ---------------------------------------------------------------------------
# Applying (from the page, or by the assistant when allowed)
# ---------------------------------------------------------------------------


#: One Doctor job to run for some suggestions: their ids, and a function
#: that starts the job (returns the job, or ``None`` when it is done at
#: once, like "different playlists").
Step = tuple[list[str], Callable[[], Awaitable[Optional[dict[str, Any]]]]]

#: How each kind of suggestion becomes Doctor jobs: ``kind`` ->
#: ``steps(chosen, user_id)``. :mod:`downtify.doctor_ai_sections` adds
#: the other Doctor sections.
APPLIERS: dict[str, Callable[[list[dict[str, Any]], int], list[Step]]] = {}

#: How long a queued step waits for another Doctor job to end.
WAIT_IDLE = 30 * 60

_runs: set[asyncio.Task[Any]] = set()


def _playlist_steps(chosen: list[dict[str, Any]], _user_id: int) -> list[Step]:
    dr = _doctor()
    payload = dr.PlaylistDecisions(
        merge=[s['paths'] for s in chosen if s['decision'] == 'merge'],
        apart=[s['paths'] for s in chosen if s['decision'] == 'apart'],
    )

    async def start() -> Optional[dict[str, Any]]:
        return (await dr.playlists_apply(payload)).get('job')

    return [([s['id'] for s in chosen], start)]


APPLIERS['playlists'] = _playlist_steps


async def _wait_idle() -> None:
    dr = _doctor()
    deadline = time.monotonic() + WAIT_IDLE
    while dr._busy() and time.monotonic() < deadline:
        await asyncio.sleep(1)


async def _wait_job(job_id: str) -> None:
    dr = _doctor()
    while dr._job.get('id') == job_id and dr._job.get('state') == 'running':
        await asyncio.sleep(1)


async def _start_step(step: Step, by: str) -> Optional[str]:
    """Start one step; mark its suggestions. Returns the job's id."""

    ids, start = step
    try:
        job = await start()
    except HTTPException as exc:
        error = _http_error(exc)
        helper.update(
            ids, state='failed', error=str(error), error_code=_code(exc.detail)
        )
        raise error from None
    if not job:
        helper.update(ids, state='applied', applied_by=by)
        return None
    helper.update(ids, state='applying', job=job.get('id', ''), applied_by=by)
    return job.get('id')


async def _run_rest(steps: list[Step], first_job: Optional[str], by: str):
    """The steps after the first, one Doctor job after the other."""

    if first_job:
        await _wait_job(first_job)
        refresh_states()
    for step in steps:
        await _wait_idle()
        try:
            job_id = await _start_step(step, by)
        except ToolError:
            continue
        if job_id:
            await _wait_job(job_id)
            refresh_states()


async def apply(
    ids: list[str], *, by: str, user_id: int = 0
) -> dict[str, Any]:
    """Apply the waiting suggestions *ids*, all from one Doctor section.

    The first job starts now (so a refusal, such as "check again first",
    comes back at once); any further jobs (one per merged song) follow
    one after the other in the background.
    """

    chosen = helper.waiting(ids)
    if not chosen:
        raise ToolError('None of these suggestions is waiting.')
    kinds = {s['kind'] for s in chosen}
    if len(kinds) > 1:
        raise ToolError(
            'Apply one Doctor section at a time: a repair puts other '
            'sections out of date until they are checked again.'
        )
    kind = kinds.pop()
    steps = APPLIERS[kind](chosen, user_id or helper.user_id)
    picked = [s['id'] for s in chosen]
    helper.update(picked, state='queued', error=None)
    try:
        first_job = await _start_step(steps[0], by)
    except ToolError:
        later = [i for _ids, _start in steps[1:] for i in _ids]
        helper.update(later, state='waiting')
        raise
    if len(steps) > 1 or first_job:
        task = asyncio.get_running_loop().create_task(
            _run_rest(steps[1:], first_job, by)
        )
        _runs.add(task)
        task.add_done_callback(_runs.discard)
    logger.info(
        'doctor ai: {} applied {} {} suggestion(s) in {} job(s)',
        by,
        len(picked),
        kind,
        len(steps),
    )
    return {
        'applied': len(picked),
        'section': kind,
        'merging': sum(
            1 for s in chosen if s['decision'] in {'merge', 'keep'}
        ),
        'kept_apart': sum(1 for s in chosen if s['decision'] == 'apart'),
        'jobs': len(steps),
        'job': first_job,
        'note': (
            'Running as Doctor job(s): see list_suggestions or get_job. '
            'Afterwards the sections this changed need a new health '
            'check before more repairs there.'
            if first_job or len(steps) > 1
            else 'Done.'
        ),
    }


def _code(detail: Any) -> str:
    """The Doctor's error code (the page has a message for each)."""

    return str(detail.get('code') or '') if isinstance(detail, dict) else ''


def refresh_states() -> None:
    """Move 'applying' suggestions on once their Doctor job ended."""

    dr = _doctor()
    job = dr._public_job()
    if not job or job.get('state') == 'running':
        return
    for s in helper.status()['suggestions']:
        if s['state'] == 'applying' and s.get('job') == job.get('id'):
            if job.get('state') == 'done':
                helper.update([s['id']], state='applied')
            else:
                error = job.get('error') or 'failed'
                text = error
                if isinstance(error, dict):
                    text = ' '.join(
                        str(error.get(k))
                        for k in ('message', 'code', 'reason')
                        if error.get(k)
                    )
                helper.update(
                    [s['id']],
                    state='failed',
                    error=str(text),
                    error_code=_code(error),
                )


# ---------------------------------------------------------------------------
# JSON-RPC
# ---------------------------------------------------------------------------


def _error(id_: Any, code: int, message: str) -> dict[str, Any]:
    return {
        'jsonrpc': '2.0',
        'id': id_,
        'error': {'code': code, 'message': message},
    }


def _result(id_: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {'jsonrpc': '2.0', 'id': id_, 'result': result}


def _tool_list() -> list[dict[str, Any]]:
    return [{k: v for k, v in t.items() if k != 'run'} for t in TOOLS]


async def _call(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get('name')
    tool = _BY_NAME.get(str(name))
    if tool is None:
        raise KeyError(name)
    args = params.get('arguments') or {}
    if not isinstance(args, dict):
        args = {}
    run: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]] = tool['run']
    try:
        data = await run(args)
    except ToolError as exc:
        return {
            'content': [{'type': 'text', 'text': str(exc)}],
            'isError': True,
        }
    except Exception as exc:
        logger.opt(exception=True).warning('doctor ai: {} failed', name)
        return {
            'content': [
                {'type': 'text', 'text': f'{name} failed: {exc}'},
            ],
            'isError': True,
        }
    return {
        'content': [
            {
                'type': 'text',
                'text': json.dumps(data, ensure_ascii=False, indent=1),
            },
        ],
        'structuredContent': data,
        'isError': False,
    }


async def handle(message: Any) -> Optional[dict[str, Any]]:
    """Answer one JSON-RPC message (``None`` for a notification)."""

    if not isinstance(message, dict) or message.get('jsonrpc') != '2.0':
        return _error(None, INVALID_REQUEST, 'Not a JSON-RPC 2.0 message')
    method = message.get('method')
    id_ = message.get('id')
    if 'id' not in message:
        # Notifications (initialized, cancelled, ...) need no answer.
        return None
    if not isinstance(method, str):
        # A response to something we never ask: nothing to do.
        return None
    params = message.get('params') or {}
    if not isinstance(params, dict):
        return _error(id_, INVALID_PARAMS, 'params must be an object')
    if method == 'initialize':
        asked = str(params.get('protocolVersion') or '')
        version = asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
        helper.set_client(params.get('clientInfo'))
        return _result(
            id_,
            {
                'protocolVersion': version,
                'capabilities': {'tools': {'listChanged': False}},
                'serverInfo': {
                    'name': 'downtify-doctor',
                    'title': 'Downtify Doctor',
                    'version': __version__,
                },
                'instructions': INSTRUCTIONS,
            },
        )
    if method == 'ping':
        return _result(id_, {})
    if method == 'tools/list':
        return _result(id_, {'tools': _tool_list()})
    if method == 'tools/call':
        try:
            return _result(id_, await _call(params))
        except KeyError:
            return _error(
                id_, INVALID_PARAMS, f'Unknown tool: {params.get("name")}'
            )
    return _error(id_, METHOD_NOT_FOUND, f'Method not found: {method}')


def parse(body: bytes) -> Any:
    try:
        return json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError('parse') from None
