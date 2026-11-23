"""A small Discord bot that answers Downtify's slash commands.

A Discord webhook can only post, so the commands (``/status``,
``/progress``, ``/queue``...) need a bot: it connects to Discord's
gateway (one WebSocket, through the ``websockets`` package Downtify
already has), registers the commands and answers each one with what the
job records say right now. The commands only read: nothing in Discord
can start, stop or change anything in Downtify.

It asks for no privileged intents (no message content, no members):
slash commands reach a bot without them. Answers go only to the channel
set in Settings (elsewhere the bot answers privately that it is not
listening there) and, when a list of Discord user ids is set, only to
those users.

The bot token is a secret: it is sent to Discord only, never logged,
and a rejected token stops the bot with an error the page shows.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import random
from collections.abc import Callable
from typing import Any, Optional

import httpx
from loguru import logger

from .notifications import DISCORD_API, Message, discord_embed

GATEWAY = 'wss://gateway.discord.gg/?v=10&encoding=json'

#: Close codes after which reconnecting cannot help.
FATAL_CLOSES = {
    4004: 'Discord rejected the bot token',
    4010: 'Discord rejected the shard settings',
    4011: 'The bot needs sharding',
    4012: 'Discord rejected the gateway version',
    4013: 'Discord rejected the intents',
    4014: 'Discord refused the intents',
}

#: Interaction types and callback types (Discord API).
PING = 1
APPLICATION_COMMAND = 2
REPLY = 4
DEFERRED = 5
EPHEMERAL = 64

#: View channel, send messages, embed links: what the invite asks for.
INVITE_PERMISSIONS = 1024 + 2048 + 16384

TASK_CHOICES = (
    ('Doctor', 'doctor'),
    ('Library upgrade', 'upgrade'),
    ('Star ratings', 'ratings'),
    ('Wanted catch-up', 'wanted'),
    ('Download queue', 'queue'),
)

#: The commands, as Discord's bulk-overwrite endpoint takes them.
COMMANDS: list[dict[str, Any]] = [
    {'name': 'help', 'description': 'What Downtify can tell you here'},
    {'name': 'status', 'description': 'Everything Downtify is doing now'},
    {
        'name': 'progress',
        'description': 'The progress of one task',
        'options': [
            {
                'type': 3,
                'name': 'task',
                'description': 'Which task',
                'required': True,
                'choices': [
                    {'name': label, 'value': value}
                    for label, value in TASK_CHOICES
                ],
            }
        ],
    },
    {'name': 'queue', 'description': 'The download queue'},
    {'name': 'doctor', 'description': 'The Doctor: running or last check'},
    {'name': 'upgrade', 'description': 'The Library upgrade'},
    {'name': 'lyrics', 'description': 'Lyrics found by the Library upgrade'},
    {'name': 'ratings', 'description': 'The Navidrome star ratings'},
    {'name': 'wanted', 'description': 'The Wanted catch-up job'},
]

Answer = Callable[[str, dict[str, Any]], Message]


def invite_url(application_id: str) -> str:
    return (
        'https://discord.com/oauth2/authorize'
        f'?client_id={application_id}'
        f'&permissions={INVITE_PERMISSIONS}'
        '&scope=bot%20applications.commands'
    )


def command_options(data: dict[str, Any]) -> dict[str, Any]:
    """An interaction's options as ``{name: value}``."""

    return {
        str(opt.get('name')): opt.get('value')
        for opt in data.get('options') or []
        if isinstance(opt, dict)
    }


def interaction_user(interaction: dict[str, Any]) -> str:
    user = (interaction.get('member') or {}).get('user') or interaction.get(
        'user'
    )
    return str((user or {}).get('id') or '')


def refusal(
    interaction: dict[str, Any], channel_id: str, allowed: set[str]
) -> Optional[str]:
    """Why this interaction is not answered, or ``None`` to answer it."""

    if channel_id and str(interaction.get('channel_id') or '') != channel_id:
        return 'Downtify only answers in its notification channel.'
    if allowed and interaction_user(interaction) not in allowed:
        return 'You are not on Downtify’s list of allowed users.'
    return None


class DiscordBot:
    """Runs the gateway connection while the settings ask for it."""

    def __init__(
        self,
        answer: Answer,
        *,
        client_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
        connect: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._answer = answer
        self._client_factory = client_factory or (
            lambda: httpx.AsyncClient(timeout=15.0)
        )
        self._connect = connect
        self._task: Optional[asyncio.Task[None]] = None
        self._key: Optional[str] = None
        self._channel_id = ''
        self._allowed: set[str] = set()
        self.state = 'off'
        self.error = ''
        self.user = ''
        self.application_id = ''

    # -- the page's view ---------------------------------------------

    def status(self) -> dict[str, Any]:
        return {
            'state': self.state,
            'error': self.error,
            'user': self.user,
            'invite_url': invite_url(self.application_id)
            if self.application_id
            else '',
            'commands': [c['name'] for c in COMMANDS],
        }

    # -- lifecycle ----------------------------------------------------

    def apply(self, cfg: dict[str, Any]) -> None:
        """Start, restart or stop the bot to match the settings."""

        ch = cfg['channels']['discord']
        wanted = (
            cfg['enabled']
            and ch['enabled']
            and ch['mode'] == 'bot'
            and ch['commands']
            and bool(ch['bot_token'])
        )
        self._channel_id = ch['channel_id']
        self._allowed = set(ch['allowed_users'].split())
        key = ch['bot_token'] if wanted else None
        running = self._task is not None and not self._task.done()
        if key == self._key and (running or key is None):
            return
        self._stop_task()
        self._key = key
        if key is None:
            self.state, self.error = 'off', ''
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Settings loaded before the server loop: started later.
            self._key = None
            return
        self.state, self.error = 'connecting', ''
        self._task = loop.create_task(
            self._run(ch['bot_token']), name='discord-bot'
        )

    def _stop_task(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def stop(self) -> None:
        task = self._task
        self._stop_task()
        self._key = None
        if task is not None:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        self.state = 'off'

    # -- the gateway --------------------------------------------------

    def _open(self, url: str) -> Any:
        if self._connect is not None:
            return self._connect(url)
        from websockets.asyncio.client import connect  # noqa: PLC0415

        return connect(url, max_size=2**22, open_timeout=20)

    async def _run(self, token: str) -> None:
        delay = 5.0
        async with self._client_factory() as client:
            while True:
                try:
                    fatal = await self._session(client, token)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    fatal = None
                    self.state = 'connecting'
                    self.error = (
                        f'Could not reach Discord ({type(exc).__name__})'
                    )
                    logger.info('discord bot: {}', self.error)
                if fatal:
                    self.state, self.error = 'error', fatal
                    logger.warning('discord bot stopped: {}', fatal)
                    return
                await asyncio.sleep(delay + random.random())
                delay = min(delay * 2, 300.0)

    async def _session(
        self, client: httpx.AsyncClient, token: str
    ) -> Optional[str]:
        """One gateway connection; a fatal reason, or ``None`` to retry."""

        seq: list[Optional[int]] = [None]
        async with self._open(GATEWAY) as ws:
            hello = json.loads(await ws.recv())
            interval = float(hello['d']['heartbeat_interval']) / 1000

            async def heartbeat() -> None:
                await asyncio.sleep(interval * random.random())
                while True:
                    await ws.send(json.dumps({'op': 1, 'd': seq[0]}))
                    await asyncio.sleep(interval)

            beat = asyncio.create_task(heartbeat())
            try:
                await ws.send(
                    json.dumps({
                        'op': 2,
                        'd': {
                            'token': token,
                            'intents': 0,
                            'properties': {
                                'os': 'linux',
                                'browser': 'downtify',
                                'device': 'downtify',
                            },
                        },
                    })
                )
                async for raw in ws:
                    event = json.loads(raw)
                    if event.get('s') is not None:
                        seq[0] = event['s']
                    op = event.get('op')
                    if op == 0:
                        await self._dispatch(client, token, event)
                    elif op == 1:
                        await ws.send(json.dumps({'op': 1, 'd': seq[0]}))
                    elif op in {7, 9}:
                        # Reconnect / invalid session: start over.
                        return None
            finally:
                beat.cancel()
            code = getattr(ws, 'close_code', None)
        return FATAL_CLOSES.get(int(code or 0))

    async def _dispatch(
        self, client: httpx.AsyncClient, token: str, event: dict[str, Any]
    ) -> None:
        kind = event.get('t')
        data = event.get('d') or {}
        if kind == 'READY':
            app = data.get('application') or {}
            user = data.get('user') or {}
            self.application_id = str(app.get('id') or '')
            self.user = str(user.get('username') or '')
            self.state, self.error = 'connected', ''
            logger.info('discord bot: connected as {}', self.user)
            await self._register(client, token)
        elif kind == 'INTERACTION_CREATE':
            await self._interaction(client, data)

    async def _register(self, client: httpx.AsyncClient, token: str) -> None:
        if not self.application_id:
            return
        try:
            response = await client.put(
                f'{DISCORD_API}/applications/{self.application_id}/commands',
                headers={'Authorization': f'Bot {token}'},
                json=COMMANDS,
            )
        except httpx.HTTPError as exc:
            self.error = f'Could not register the commands ({exc!r})'[:200]
            return
        if response.status_code >= 400:
            self.error = (
                f'Discord refused the commands (HTTP {response.status_code})'
            )
            logger.warning('discord bot: {}', self.error)

    async def _interaction(
        self, client: httpx.AsyncClient, interaction: dict[str, Any]
    ) -> None:
        if interaction.get('type') != APPLICATION_COMMAND:
            return
        url = (
            f'{DISCORD_API}/interactions/{interaction.get("id")}'
            f'/{interaction.get("token")}/callback'
        )
        why = refusal(interaction, self._channel_id, self._allowed)
        if why:
            body = {
                'type': REPLY,
                'data': {'content': why, 'flags': EPHEMERAL},
            }
            with contextlib.suppress(httpx.HTTPError):
                await client.post(url, json=body)
            return
        data = interaction.get('data') or {}
        name = str(data.get('name') or '')
        options = command_options(data)
        work = asyncio.ensure_future(
            asyncio.to_thread(self._answer, name, options)
        )
        try:
            # Discord waits 3 seconds for the reply.
            msg = await asyncio.wait_for(asyncio.shield(work), 2.0)
        except asyncio.TimeoutError:
            msg = None
        except Exception:
            logger.exception('discord bot: /{} failed', name)
            msg = Message(title='Something went wrong', level='error')
        try:
            if msg is not None:
                await client.post(
                    url,
                    json={
                        'type': REPLY,
                        'data': {'embeds': [discord_embed(msg)]},
                    },
                )
                return
            await client.post(url, json={'type': DEFERRED})
            try:
                msg = await work
            except Exception:
                logger.exception('discord bot: /{} failed', name)
                msg = Message(title='Something went wrong', level='error')
            await client.patch(
                f'{DISCORD_API}/webhooks/{self.application_id}'
                f'/{interaction.get("token")}/messages/@original',
                json={'embeds': [discord_embed(msg)]},
            )
        except httpx.HTTPError as exc:
            logger.info(
                'discord bot: reply to /{} failed ({})',
                name,
                type(exc).__name__,
            )
