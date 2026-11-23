"""Notifications: tell Discord, ntfy, Gotify or a webhook what runs.

Off until an admin turns it on (Settings > Notifications); nothing is
sent and no connection is made before that. The settings live in
``notifications.json`` beside ``settings.json``, not in it: the webhook
URLs and tokens are secrets, so ``GET /api/settings`` and the backups
never carry them, and the page only learns whether each one is set.

Two kinds of news reach the channels:

* **Tasks** - the long jobs (Doctor, Library upgrade, star ratings, the
  Wanted catch-up, backups). Their routes already keep a live job
  record for the page; :func:`register_source` hands the dispatcher a
  function that reads it, and :class:`Dispatcher` compares each reading
  with the last one to say when a task started, moved on, finished or
  failed. So the jobs need no notification calls of their own.
  Progress edits one message per task in place (Discord), at most every
  ``progress_seconds``; a channel that cannot edit gets a line at each
  quarter instead.
* **Events** - things that happen once (a download failed, an artist
  watch found new releases). :func:`emit` queues them; the same kind is
  grouped for ``BATCH_SECONDS`` so a burst becomes one message.

The pure parts (settings, filtering, the message text) are at the top;
the channels and the dispatcher follow. Secrets are never logged: a
failed send logs the channel and the HTTP status only.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from loguru import logger

FILE_NAME = 'notifications.json'

#: The long jobs a channel can follow.
TASKS = ('doctor', 'upgrade', 'ratings', 'wanted', 'backup')
#: What a channel hears about a task.
PHASES = ('start', 'progress', 'finish', 'fail')
#: One-off events.
EVENTS = ('download_failed', 'download_done', 'new_releases', 'watch_done')
CHANNELS = ('discord', 'ntfy', 'gotify', 'webhook')

#: Settings that are secrets: never sent back to the page.
SECRETS = {
    'discord': ('webhook_url', 'bot_token'),
    'ntfy': ('token',),
    'gotify': ('token',),
    'webhook': ('url',),
}

PROGRESS_CHOICES = (30, 60, 300, 900)
DEFAULT_PROGRESS_SECONDS = 60
#: How long events of one kind are gathered into one message.
BATCH_SECONDS = 30
#: Lines one grouped message lists (the count covers them all).
BATCH_LINES = 10
#: Seconds between two readings of the task records.
POLL_SECONDS = 3.0
#: Seconds between two messages to one channel (Discord allows ~5/2s).
CHANNEL_GAP = 1.0

_DEFAULT_EVENTS = ['download_failed', 'new_releases']
_DEFAULT_PHASES = ['start', 'finish', 'fail']


def _channel_defaults(name: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        'enabled': False,
        'tasks': list(TASKS),
        'phases': [
            p
            for p in PHASES
            if p in _DEFAULT_PHASES or (p == 'progress' and name == 'discord')
        ],
        'events': list(_DEFAULT_EVENTS),
    }
    if name == 'discord':
        base.update(
            mode='webhook',
            webhook_url='',
            bot_token='',
            channel_id='',
            commands=True,
            allowed_users='',
        )
    elif name == 'ntfy':
        base.update(server='https://ntfy.sh', topic='', token='')
    elif name == 'gotify':
        base.update(server='', token='')
    elif name == 'webhook':
        base.update(url='')
    return base


DEFAULTS: dict[str, Any] = {
    'enabled': False,
    'progress_seconds': DEFAULT_PROGRESS_SECONDS,
    'channels': {name: _channel_defaults(name) for name in CHANNELS},
}


def _pick(values: Any, allowed: tuple[str, ...], default: list[str]):
    if not isinstance(values, list):
        return list(default)
    return [v for v in allowed if v in values]


def _text(value: Any, limit: int = 2000) -> str:
    return str(value or '').strip()[:limit]


def _digits(value: Any) -> str:
    text = _text(value, 40)
    return text if text.isdigit() else ''


def _user_ids(value: Any) -> str:
    parts = str(value or '').replace(',', ' ').split()
    return ' '.join(p for p in parts if p.isdigit())[:1000]


def effective(raw: Any) -> dict[str, Any]:
    """A fresh, complete settings dict; unknown or bad values fall back
    to their defaults."""

    data = raw if isinstance(raw, dict) else {}
    seconds = data.get('progress_seconds')
    out: dict[str, Any] = {
        'enabled': data.get('enabled') is True,
        'progress_seconds': seconds
        if seconds in PROGRESS_CHOICES
        else DEFAULT_PROGRESS_SECONDS,
        'channels': {},
    }
    channels = data.get('channels')
    channels = channels if isinstance(channels, dict) else {}
    for name in CHANNELS:
        given = channels.get(name)
        given = given if isinstance(given, dict) else {}
        base = _channel_defaults(name)
        ch: dict[str, Any] = {
            'enabled': given.get('enabled') is True,
            'tasks': _pick(given.get('tasks'), TASKS, base['tasks']),
            'phases': _pick(given.get('phases'), PHASES, base['phases']),
            'events': _pick(given.get('events'), EVENTS, base['events']),
        }
        if name == 'discord':
            mode = given.get('mode')
            ch.update(
                mode=mode if mode in {'webhook', 'bot'} else 'webhook',
                webhook_url=_text(given.get('webhook_url'), 500),
                bot_token=_text(given.get('bot_token'), 200),
                channel_id=_digits(given.get('channel_id')),
                commands=given.get('commands', True) is not False,
                allowed_users=_user_ids(given.get('allowed_users')),
            )
        elif name == 'ntfy':
            ch.update(
                server=_text(given.get('server'), 500).rstrip('/')
                or base['server'],
                topic=_text(given.get('topic'), 64),
                token=_text(given.get('token'), 200),
            )
        elif name == 'gotify':
            ch.update(
                server=_text(given.get('server'), 500).rstrip('/'),
                token=_text(given.get('token'), 200),
            )
        else:
            ch.update(url=_text(given.get('url'), 1000))
        out['channels'][name] = ch
    return out


def merge_update(
    current: dict[str, Any], payload: Any, *, clear: tuple[str, ...] = ()
) -> dict[str, Any]:
    """*current* with the page's *payload* applied.

    A secret left empty keeps the saved one (the page never has it);
    ``clear`` lists ``channel.field`` secrets to remove.
    """

    data = payload if isinstance(payload, dict) else {}
    merged = json.loads(json.dumps(current))
    if 'enabled' in data:
        merged['enabled'] = data['enabled']
    if 'progress_seconds' in data:
        merged['progress_seconds'] = data['progress_seconds']
    given = data.get('channels')
    given = given if isinstance(given, dict) else {}
    for name in CHANNELS:
        ch = given.get(name)
        if not isinstance(ch, dict):
            continue
        for key, value in ch.items():
            if key in SECRETS[name] and not _text(value):
                continue
            merged['channels'][name][key] = value
    for item in clear:
        name, _, key = str(item).partition('.')
        if key in SECRETS.get(name, ()):
            merged['channels'][name][key] = ''
    return effective(merged)


def public(cfg: dict[str, Any]) -> dict[str, Any]:
    """*cfg* as the page sees it: each secret replaced by ``<key>_set``."""

    out = json.loads(json.dumps(cfg))
    for name, keys in SECRETS.items():
        ch = out['channels'][name]
        for key in keys:
            ch[f'{key}_set'] = bool(ch.pop(key))
    return out


def configured(name: str, ch: dict[str, Any]) -> bool:
    """Whether channel *name* has what it needs to send."""

    if name == 'discord':
        if ch['mode'] == 'bot':
            return bool(ch['bot_token'] and ch['channel_id'])
        return ch['webhook_url'].startswith('https://')
    if name == 'ntfy':
        return bool(ch['topic'])
    if name == 'gotify':
        return bool(ch['server'] and ch['token'])
    return ch['url'].startswith(('http://', 'https://'))


def wants_task(ch: dict[str, Any], kind: str, phase: str) -> bool:
    return kind in ch['tasks'] and phase in ch['phases']


def wants_event(ch: dict[str, Any], event: str) -> bool:
    return event in ch['events']


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

LEVELS = ('info', 'success', 'warning', 'error')


@dataclass
class Message:
    """What a channel shows; each channel renders it its own way."""

    title: str
    text: str = ''
    level: str = 'info'
    fields: list[tuple[str, str]] = field(default_factory=list)
    #: ``(done, total)`` for a progress bar.
    progress: Optional[tuple[int, int]] = None
    #: The event or task kind, for the webhook's JSON.
    event: str = ''


def progress_bar(done: int, total: int, width: int = 12) -> str:
    """``▓▓▓░░░ 25% (1/4)``; just the count while the total is unknown."""

    done = max(0, int(done))
    total = max(0, int(total))
    if total <= 0:
        return f'{done}' if done else '…'
    share = min(1.0, done / total)
    filled = round(share * width)
    bar = '▓' * filled + '░' * (width - filled)
    return f'{bar} {round(share * 100)}% ({done:,}/{total:,})'


@dataclass
class Task:
    """One reading of a long job, in the dispatcher's terms."""

    #: Unique per run (a new run is a new task).
    key: str
    kind: str
    title: str
    #: ``running``, ``done``, ``stopped`` or ``failed``.
    state: str
    done: int = 0
    total: int = 0
    step: str = ''
    summary: list[tuple[str, str]] = field(default_factory=list)
    error: str = ''


_STATE_TEXT = {
    'running': ('Running', 'info'),
    'done': ('Finished', 'success'),
    'stopped': ('Stopped', 'warning'),
    'failed': ('Failed', 'error'),
}


def task_message(task: Task, phase: str) -> Message:
    """The message for *task* at *phase* (start, progress, finish, fail)."""

    word, level = _STATE_TEXT.get(task.state, ('Running', 'info'))
    if phase == 'start':
        word, level = 'Started', 'info'
    lines = []
    if task.state == 'running' or phase == 'progress':
        lines.append(progress_bar(task.done, task.total))
        if task.step:
            lines.append(task.step)
    if task.error:
        lines.append(task.error)
    return Message(
        title=f'{task.title}: {word.lower()}',
        text='\n'.join(lines),
        level=level,
        fields=list(task.summary) if phase != 'start' else [],
        progress=(task.done, task.total) if task.state == 'running' else None,
        event=task.kind,
    )


_EVENT_TEXT = {
    'download_failed': ('Download failed', '{n} downloads failed', 'error'),
    'download_done': ('Downloaded', '{n} songs downloaded', 'success'),
    'new_releases': ('New releases', 'New releases from {n} watches', 'info'),
    'watch_done': ('Watch downloads', '{n} watches downloaded songs', 'info'),
}


def batch_message(event: str, items: list[tuple[str, str]]) -> Message:
    """One message for *items* (``(title, text)``) of the same *event*."""

    one, many, level = _EVENT_TEXT.get(event, (event, '{n} events', 'info'))
    if len(items) == 1:
        title, text = items[0]
        return Message(
            title=f'{one}: {title}', text=text, level=level, event=event
        )
    lines = [
        f'• {title}' + (f' - {text}' if text else '')
        for title, text in items[:BATCH_LINES]
    ]
    if len(items) > BATCH_LINES:
        lines.append(f'… and {len(items) - BATCH_LINES} more')
    return Message(
        title=many.format(n=len(items)),
        text='\n'.join(lines),
        level=level,
        event=event,
    )


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

DISCORD_API = 'https://discord.com/api/v10'
_DISCORD_COLOURS = {
    'info': 0x5865F2,
    'success': 0x1DB954,
    'warning': 0xF0B232,
    'error': 0xED4245,
}
_NTFY_TAGS = {
    'info': 'information_source',
    'success': 'white_check_mark',
    'warning': 'warning',
    'error': 'x',
}
_PRIORITY = {'info': 3, 'success': 3, 'warning': 4, 'error': 4}


class SendError(RuntimeError):
    """A channel refused a message (the text never holds a secret)."""


def discord_embed(msg: Message) -> dict[str, Any]:
    embed: dict[str, Any] = {
        'title': msg.title[:256],
        'color': _DISCORD_COLOURS.get(msg.level, _DISCORD_COLOURS['info']),
        'footer': {'text': 'Downtify'},
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }
    if msg.text:
        embed['description'] = msg.text[:4000]
    if msg.fields:
        embed['fields'] = [
            {'name': k[:256], 'value': str(v)[:1024] or '-', 'inline': True}
            for k, v in msg.fields[:24]
        ]
    return embed


def plain_text(msg: Message) -> str:
    lines = [msg.text] if msg.text else []
    lines += [f'{k}: {v}' for k, v in msg.fields]
    return '\n'.join(lines) or msg.title


Client = httpx.AsyncClient


async def _request(
    client: Client, channel: str, method: str, url: str, **kwargs: Any
) -> httpx.Response:
    """One HTTP call; a Discord 429 waits once for ``retry_after``."""

    for attempt in (1, 2):
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise SendError(
                f'Could not reach {channel} ({type(exc).__name__})'
            ) from None
        if response.status_code == 429 and attempt == 1:
            try:
                wait = float(response.json().get('retry_after', 1))
            except ValueError:
                wait = 1.0
            await asyncio.sleep(min(wait, 10.0))
            continue
        if response.status_code >= 400:
            raise SendError(f'{channel} answered HTTP {response.status_code}')
        return response
    raise SendError(f'{channel} is rate limiting')


class Channel:
    """Sends a :class:`Message`; ``editable`` ones can update it later."""

    name = ''
    editable = False

    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg

    async def send(self, client: Client, msg: Message) -> Optional[str]:
        raise NotImplementedError

    async def edit(self, client: Client, handle: str, msg: Message) -> None:
        raise NotImplementedError


class DiscordWebhook(Channel):
    name = 'discord'
    editable = True

    async def send(self, client: Client, msg: Message) -> Optional[str]:
        response = await _request(
            client,
            'Discord',
            'POST',
            self.cfg['webhook_url'],
            params={'wait': 'true'},
            json={'username': 'Downtify', 'embeds': [discord_embed(msg)]},
        )
        return str(response.json().get('id') or '') or None

    async def edit(self, client: Client, handle: str, msg: Message) -> None:
        await _request(
            client,
            'Discord',
            'PATCH',
            f'{self.cfg["webhook_url"]}/messages/{handle}',
            json={'embeds': [discord_embed(msg)]},
        )


class DiscordBotChannel(Channel):
    name = 'discord'
    editable = True

    def _headers(self) -> dict[str, str]:
        return {'Authorization': f'Bot {self.cfg["bot_token"]}'}

    async def send(self, client: Client, msg: Message) -> Optional[str]:
        response = await _request(
            client,
            'Discord',
            'POST',
            f'{DISCORD_API}/channels/{self.cfg["channel_id"]}/messages',
            headers=self._headers(),
            json={'embeds': [discord_embed(msg)]},
        )
        return str(response.json().get('id') or '') or None

    async def edit(self, client: Client, handle: str, msg: Message) -> None:
        await _request(
            client,
            'Discord',
            'PATCH',
            f'{DISCORD_API}/channels/{self.cfg["channel_id"]}'
            f'/messages/{handle}',
            headers=self._headers(),
            json={'embeds': [discord_embed(msg)]},
        )


class Ntfy(Channel):
    name = 'ntfy'

    async def send(self, client: Client, msg: Message) -> Optional[str]:
        headers = {}
        if self.cfg['token']:
            headers['Authorization'] = f'Bearer {self.cfg["token"]}'
        await _request(
            client,
            'ntfy',
            'POST',
            self.cfg['server'],
            headers=headers,
            json={
                'topic': self.cfg['topic'],
                'title': msg.title,
                'message': plain_text(msg),
                'tags': [_NTFY_TAGS.get(msg.level, 'information_source')],
                'priority': _PRIORITY.get(msg.level, 3),
            },
        )
        return None


class Gotify(Channel):
    name = 'gotify'

    async def send(self, client: Client, msg: Message) -> Optional[str]:
        await _request(
            client,
            'Gotify',
            'POST',
            f'{self.cfg["server"]}/message',
            headers={'X-Gotify-Key': self.cfg['token']},
            json={
                'title': msg.title,
                'message': plain_text(msg),
                'priority': 7 if msg.level == 'error' else 5,
            },
        )
        return None


class Webhook(Channel):
    """A JSON POST. ``title``, ``body`` and ``type`` are what an Apprise
    API server's ``/notify`` takes, so it works as-is behind one."""

    name = 'webhook'

    async def send(self, client: Client, msg: Message) -> Optional[str]:
        await _request(
            client,
            'the webhook',
            'POST',
            self.cfg['url'],
            json={
                'source': 'downtify',
                'event': msg.event,
                'level': msg.level,
                'type': 'failure' if msg.level == 'error' else msg.level,
                'title': msg.title,
                'body': plain_text(msg),
                'text': msg.text,
                'fields': dict(msg.fields),
                'progress': list(msg.progress) if msg.progress else None,
            },
        )
        return None


def make_channel(name: str, ch: dict[str, Any]) -> Channel:
    if name == 'discord':
        if ch['mode'] == 'bot':
            return DiscordBotChannel(ch)
        return DiscordWebhook(ch)
    return {'ntfy': Ntfy, 'gotify': Gotify, 'webhook': Webhook}[name](ch)


# ---------------------------------------------------------------------------
# Settings file
# ---------------------------------------------------------------------------


def load(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raw = {}
    return effective(raw)


def save(path: Path, cfg: dict[str, Any]) -> None:
    """Write *cfg* atomically, readable by the owner only."""

    tmp = path.with_name(path.name + '.tmp')
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
    with contextlib.suppress(OSError):
        os.chmod(tmp, 0o600)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# The dispatcher
# ---------------------------------------------------------------------------

Source = Callable[[], list[Task]]


@dataclass
class _Live:
    """A task's message on one channel."""

    handle: Optional[str] = None
    sent_at: float = 0.0
    quarter: int = 0


class Dispatcher:
    """Watches the task sources, gathers events and sends both."""

    def __init__(self) -> None:
        self.cfg: dict[str, Any] = effective({})
        self._sources: dict[str, Source] = {}
        self._seen: dict[str, Task] = {}
        self._primed = False
        self._live: dict[tuple[str, str], _Live] = {}
        self._pending: dict[str, list[tuple[str, str]]] = {}
        self._first_at: dict[str, float] = {}
        self._lock = threading.Lock()
        self._last_send: dict[str, float] = {}
        self._errors: dict[str, str] = {}
        #: Short tasks reported once they ended (:meth:`task_finished`).
        self._extra_tasks: list[Task] = []
        self.client_factory: Callable[[], Client] = lambda: httpx.AsyncClient(
            timeout=15.0
        )
        #: Called after the settings change (the Discord bot hooks in).
        self.on_config: list[Callable[[dict[str, Any]], None]] = []

    # -- setup --------------------------------------------------------

    def configure(self, cfg: dict[str, Any]) -> None:
        self.cfg = effective(cfg)
        for hook in self.on_config:
            try:
                hook(self.cfg)
            except Exception:
                logger.exception('notifications: settings hook failed')

    def register_source(self, name: str, source: Source) -> None:
        self._sources[name] = source

    def channels(self) -> list[tuple[str, dict[str, Any]]]:
        """The channels that are on and can send (none while off)."""

        if not self.cfg['enabled']:
            return []
        return [
            (name, ch)
            for name, ch in self.cfg['channels'].items()
            if ch['enabled'] and configured(name, ch)
        ]

    def errors(self) -> dict[str, str]:
        return dict(self._errors)

    # -- events -------------------------------------------------------

    def emit(self, event: str, title: str, text: str = '') -> None:
        """Queue a one-off *event*; cheap and silent while nobody
        listens. Safe from any thread."""

        if not any(wants_event(ch, event) for _n, ch in self.channels()):
            return
        with self._lock:
            self._pending.setdefault(event, []).append((
                _text(title, 200),
                _text(text, 300),
            ))
            self._first_at.setdefault(event, time.monotonic())

    def _due_batches(self, now: float, *, flush: bool = False):
        with self._lock:
            due = [
                event
                for event, at in self._first_at.items()
                if flush or now - at >= BATCH_SECONDS
            ]
            batches = [(e, self._pending.pop(e, [])) for e in due]
            for event in due:
                self._first_at.pop(event, None)
        return [(e, items) for e, items in batches if items]

    # -- tasks --------------------------------------------------------

    def read_tasks(self) -> list[Task]:
        tasks: list[Task] = []
        for name, source in self._sources.items():
            try:
                tasks.extend(source())
            except Exception:
                logger.opt(exception=True).debug(
                    'notifications: reading {} failed', name
                )
        return tasks

    def task_changes(self, tasks: list[Task]) -> list[tuple[Task, str]]:
        """``(task, phase)`` for what changed since the last reading.

        The first reading after a start only learns what is there: a
        job that ended before Downtify started is old news; one still
        running is announced."""

        changes: list[tuple[Task, str]] = []
        for task in tasks:
            before = self._seen.get(task.key)
            self._seen[task.key] = task
            if before is None:
                if task.state == 'running':
                    changes.append((task, 'start'))
                elif self._primed:
                    # Started and ended between two readings.
                    changes.append((task, 'start'))
                    changes.append((task, _end_phase(task)))
                continue
            if before.state == 'running' and task.state != 'running':
                changes.append((task, _end_phase(task)))
            elif task.state == 'running' and (
                (task.done, task.total, task.step)
                != (before.done, before.total, before.step)
            ):
                changes.append((task, 'progress'))
        self._primed = True
        # Forget old runs, keeping the newest of each source.
        if len(self._seen) > 200:
            keep = {t.key for t in tasks}
            self._seen = {k: v for k, v in self._seen.items() if k in keep}
        return changes

    def task_finished(
        self,
        kind: str,
        title: str,
        *,
        failed: bool = False,
        summary: Optional[list[tuple[str, str]]] = None,
        error: str = '',
    ) -> None:
        """Report a short task that has no live record (a backup)."""

        if not any(kind in ch['tasks'] for _n, ch in self.channels()):
            return
        task = Task(
            key=f'{kind}:{time.time_ns()}',
            kind=kind,
            title=title,
            state='failed' if failed else 'done',
            summary=summary or [],
            error=error,
        )
        with self._lock:
            self._extra_tasks.append(task)

    # -- sending ------------------------------------------------------

    async def _send(
        self,
        client: Client,
        name: str,
        ch: dict[str, Any],
        msg: Message,
        handle: Optional[str] = None,
    ) -> Optional[str]:
        gap = CHANNEL_GAP - (time.monotonic() - self._last_send.get(name, 0))
        if gap > 0:
            await asyncio.sleep(gap)
        channel = make_channel(name, ch)
        try:
            if handle and channel.editable:
                await channel.edit(client, handle, msg)
                result = handle
            else:
                result = await channel.send(client, msg)
        except SendError as exc:
            self._errors[name] = str(exc)
            logger.warning('notifications: {} send failed: {}', name, exc)
            return None
        finally:
            self._last_send[name] = time.monotonic()
        self._errors.pop(name, None)
        return result

    async def _task_update(
        self, client: Client, task: Task, phase: str, now: float
    ) -> None:
        for name, ch in self.channels():
            live = self._live.setdefault((name, task.key), _Live())
            editable = make_channel(name, ch).editable
            if phase == 'progress':
                if not wants_task(ch, task.kind, 'progress'):
                    continue
                if now - live.sent_at < self.cfg['progress_seconds']:
                    continue
                if not editable:
                    quarter = (
                        int(4 * task.done / task.total) if task.total else 0
                    )
                    if quarter <= live.quarter or quarter >= 4:
                        continue
                    live.quarter = quarter
                live.sent_at = now
                msg = task_message(task, 'progress')
                live.handle = await self._send(
                    client, name, ch, msg, live.handle if editable else None
                )
                continue
            if phase == 'start':
                if not wants_task(ch, task.kind, 'start'):
                    continue
                live.sent_at = now
                live.handle = await self._send(
                    client, name, ch, task_message(task, 'start')
                )
                continue
            # finish / fail: settle the live message, then announce.
            if live.handle and editable:
                await self._send(
                    client, name, ch, task_message(task, phase), live.handle
                )
            if wants_task(ch, task.kind, phase):
                await self._send(client, name, ch, task_message(task, phase))
            self._live.pop((name, task.key), None)

    async def tick(self, client: Client, *, flush: bool = False) -> None:
        """One round: read the tasks, send what changed and what is
        due. Does nothing (not even reading) while notifications are
        off."""

        if not self.channels():
            self._primed = False
            self._seen.clear()
            with self._lock:
                self._pending.clear()
                self._first_at.clear()
                self._extra_tasks.clear()
            return
        now = time.monotonic()
        tasks = await asyncio.to_thread(self.read_tasks)
        changes = self.task_changes(tasks)
        with self._lock:
            extra = list(self._extra_tasks)
            self._extra_tasks.clear()
        changes += [(t, _end_phase(t)) for t in extra]
        for task, phase in changes:
            await self._task_update(client, task, phase, now)
        for event, items in self._due_batches(now, flush=flush):
            msg = batch_message(event, items)
            for name, ch in self.channels():
                if wants_event(ch, event):
                    await self._send(client, name, ch, msg)

    async def run(self, interval: float = POLL_SECONDS) -> None:
        async with self.client_factory() as client:
            while True:
                try:
                    await self.tick(client)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception('notifications: round failed')
                await asyncio.sleep(interval)

    async def test(self, name: str, ch: dict[str, Any]) -> None:
        """Send a test message on *name* now; raises :class:`SendError`."""

        if not configured(name, ch):
            raise SendError('Fill in the channel first')
        msg = Message(
            title='Downtify test notification',
            text='If you can read this, the channel works.',
            level='success',
            event='test',
        )
        async with self.client_factory() as client:
            await make_channel(name, ch).send(client, msg)


def _end_phase(task: Task) -> str:
    return 'fail' if task.state == 'failed' else 'finish'


#: The one dispatcher of this process.
dispatcher = Dispatcher()


def emit(event: str, title: str, text: str = '') -> None:
    """Queue a one-off event (see :meth:`Dispatcher.emit`)."""

    try:
        dispatcher.emit(event, title, text)
    except Exception:
        logger.opt(exception=True).debug('notifications: emit failed')


def task_finished(kind: str, title: str, **kwargs: Any) -> None:
    """Report a short task (see :meth:`Dispatcher.task_finished`)."""

    try:
        dispatcher.task_finished(kind, title, **kwargs)
    except Exception:
        logger.opt(exception=True).debug('notifications: report failed')
