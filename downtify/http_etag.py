"""Answer ``304 Not Modified`` to repeat reads of large JSON listings.

The browser keeps these responses and asks again with ``If-None-Match``
(``no-cache`` means "keep it, but check first"), so a Library page whose
data hasn't changed downloads nothing instead of megabytes of JSON. The tag
hashes the body, so it needs no bookkeeping and two accounts that see
different rows never share one; ``private`` keeps them out of shared caches.
"""

from __future__ import annotations

import hashlib
from collections.abc import Collection

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CACHE_CONTROL = 'private, no-cache'


class JsonETagMiddleware:
    """Tag ``GET`` responses of *paths*; other requests pass straight on."""

    def __init__(self, app: ASGIApp, paths: Collection[str]) -> None:
        self.app = app
        self.paths = frozenset(paths)

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if (
            scope['type'] != 'http'
            or scope['method'] != 'GET'
            or scope['path'] not in self.paths
        ):
            await self.app(scope, receive, send)
            return

        start: Message = {}
        body = bytearray()

        async def capture(message: Message) -> None:
            nonlocal start
            if message['type'] == 'http.response.start':
                start = message
                return
            body.extend(message.get('body', b''))
            if message.get('more_body'):
                return
            await _send_tagged(scope, start, bytes(body), send)

        await self.app(scope, receive, capture)


async def _send_tagged(
    scope: Scope, start: Message, body: bytes, send: Send
) -> None:
    """Send the buffered response, or a 304 when the browser has it."""

    if start['status'] != 200:
        await send(start)
        await send({'type': 'http.response.body', 'body': body})
        return
    digest = hashlib.blake2b(body, digest_size=16).hexdigest()
    etag = f'"{digest}"'
    if Headers(scope=scope).get('if-none-match') == etag:
        await send({
            'type': 'http.response.start',
            'status': 304,
            'headers': [
                (b'etag', etag.encode()),
                (b'cache-control', CACHE_CONTROL.encode()),
            ],
        })
        await send({'type': 'http.response.body', 'body': b''})
        return
    headers = MutableHeaders(raw=list(start['headers']))
    headers['ETag'] = etag
    headers['Cache-Control'] = CACHE_CONTROL
    await send({**start, 'headers': headers.raw})
    await send({'type': 'http.response.body', 'body': body})
