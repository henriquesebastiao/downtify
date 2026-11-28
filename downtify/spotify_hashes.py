"""Keep Spotify's query codes current without a Downtify release.

Downtify reads playlists, artists and search suggestions signed out,
through the web player's GraphQL API (``api-partner.spotify.com``). Each
request names its query by a code - the sha256 of the query document in
Spotify's player (a "persisted query"). The codes ship with Downtify
(:mod:`downtify.spotify`), but Spotify's player changes them now and
then. Spotify answers an old one with ``PersistedQueryNotFound`` once it
stops accepting it, and every playlist read failed until a release
changed the code by hand.

Now such an answer is repaired on the spot (:func:`repair`):

1. load ``https://open.spotify.com/`` and its main ``web-player`` script;
2. find ``"<operation>","query","<64 hex>"`` in it - or, for queries that
   live in a lazily loaded part of the player (the artist discography is
   in ``xpui-routes-artist``), in that part, located through the chunk
   tables of the main script;
3. remember the new code (in ``<data>/spotify_hashes.json`` once
   :func:`configure` named it, so it survives restarts) and retry.

Lookups are rate limited (:data:`MIN_LOOKUP_GAP`), and each outcome goes
out once as the ``spotify`` notification: fixed by itself, or still
broken (then reading Spotify fails as before until Spotify or a release
fixes it).
"""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

import httpx
from loguru import logger

from . import notifications

PLAYER_URL = 'https://open.spotify.com/'
FILE_NAME = 'spotify_hashes.json'
#: Seconds between two lookups of one query in the player (one per
#: stale answer would hammer Spotify while it is broken).
MIN_LOOKUP_GAP = 600
#: Seconds before the same "still broken" message goes out again.
BROKEN_REPEAT = 6 * 3600
_TIMEOUT = 30
_USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
)

#: Lazily loaded player parts that hold an operation (chunk name).
CHUNKS = {'queryArtistDiscographyAll': 'xpui-routes-artist'}

_HEX64 = re.compile(r'^[0-9a-f]{64}$')
_SCRIPT_RE = re.compile(
    r'<script[^>]+src="([^"]+/web-player/web-player\.[^"]+\.js)"'
)


class Stale(RuntimeError):
    """Spotify no longer knows a query code and no new one was found."""


def is_stale(data: Any) -> bool:
    """Whether a GraphQL answer says the query code is unknown."""

    if not isinstance(data, dict):
        return False
    for err in data.get('errors') or []:
        message = err.get('message') if isinstance(err, dict) else err
        if 'PersistedQueryNotFound' in str(message):
            return True
    return False


def find_hash(script: str, operation: str) -> Optional[str]:
    """The code of *operation* in a player *script*, or ``None``."""

    match = re.search(
        r'"%s"\s*,\s*"query"\s*,\s*"([0-9a-f]{64})"' % re.escape(operation),
        script,
    )
    return match.group(1) if match else None


def chunk_urls(script: str, base: str, name: str) -> list[str]:
    """Candidate URLs of the lazily loaded part *name*.

    Webpack keeps a table of part ids to names (``7161:"xpui-routes-
    artist"``) and tables of ids to file hashes (``7161:"380c5c3e"``, one
    for scripts, one for styles): every hash for that id is a candidate.
    """

    ids = re.findall(r'(\d+):"%s"' % re.escape(name), script)
    urls: list[str] = []
    for chunk_id in dict.fromkeys(ids):
        for digest in re.findall(r'\b%s:"([0-9a-f]{8})"' % chunk_id, script):
            url = f'{base}/{name}.{digest}.js'
            if url not in urls:
                urls.append(url)
    return urls


class HashStore:
    """The codes learnt from Spotify's player, over the built-in ones."""

    def __init__(
        self,
        *,
        http_get: Callable[..., Any] = httpx.get,
        emit: Callable[[str, str, str], None] = notifications.emit,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.path: Optional[Path] = None
        self.http_get = http_get
        self.emit = emit
        self.clock = clock
        #: operation -> {'code': learnt, 'replaces': the built-in code
        #: it was learnt over}. A Downtify update that ships another
        #: built-in code makes the learnt one unused again.
        self._learnt: dict[str, dict[str, str]] = {}
        self._lock = threading.Lock()
        self._last_lookup: dict[str, float] = {}
        self._broken_sent: dict[str, float] = {}
        self.last_repair: Optional[dict[str, Any]] = None

    # -- saved codes ------------------------------------------------------

    def configure(self, path: Optional[Path]) -> None:
        """Keep learnt codes in *path* (``None``: memory only)."""

        self.path = Path(path) if path else None
        self._learnt = {}
        if self.path is None:
            return
        try:
            raw = json.loads(self.path.read_text('utf-8'))
        except (OSError, ValueError):
            return
        codes = raw.get('hashes') if isinstance(raw, dict) else None
        if isinstance(codes, dict):
            self._learnt = {
                str(op): {'code': e['code'], 'replaces': e['replaces']}
                for op, e in codes.items()
                if isinstance(e, dict)
                and all(
                    isinstance(e.get(k), str) and _HEX64.match(e[k])
                    for k in ('code', 'replaces')
                )
            }

    def _save(self) -> None:
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix('.tmp')
            tmp.write_text(
                json.dumps({'hashes': self._learnt}, indent=2), 'utf-8'
            )
            tmp.replace(self.path)
        except OSError:
            logger.opt(exception=True).warning(
                'Could not save the Spotify query codes'
            )

    def current(self, operation: str, builtin: str) -> str:
        entry = self._learnt.get(operation)
        if entry and entry['replaces'] == builtin:
            return entry['code']
        return builtin

    def learnt(self) -> dict[str, str]:
        return {op: e['code'] for op, e in self._learnt.items()}

    # -- finding new codes -----------------------------------------------

    def _get(self, url: str) -> str:
        resp = self.http_get(
            url,
            headers={'User-Agent': _USER_AGENT},
            timeout=_TIMEOUT,
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.text

    def lookup(self, operation: str) -> str:
        """The code of *operation* in Spotify's current player."""

        page = self._get(PLAYER_URL)
        match = _SCRIPT_RE.search(page)
        if not match:
            raise Stale("Spotify's player page has no web-player script")
        main_url = match.group(1)
        script = self._get(main_url)
        found = find_hash(script, operation)
        if found:
            return found
        name = CHUNKS.get(operation)
        if name:
            base = main_url.rsplit('/', 1)[0]
            for url in chunk_urls(script, base, name):
                try:
                    found = find_hash(self._get(url), operation)
                except httpx.HTTPError:
                    continue
                if found:
                    return found
        raise Stale(f"{operation} is not in Spotify's player any more")

    def repair(
        self, operation: str, stale: str, builtin: Optional[str] = None
    ) -> Optional[str]:
        """A new code for *operation* after Spotify refused *stale*, or
        ``None`` when none was found (or it was looked up very recently
        and nothing new came of it). *builtin* is the code Downtify ships
        (default *stale*). Never raises."""

        builtin = builtin or stale
        with self._lock:
            have = self.current(operation, builtin)
            if have != stale:
                # Another request already repaired it.
                return have
            now = self.clock()
            last = self._last_lookup.get(operation)
            if last is not None and now - last < MIN_LOOKUP_GAP:
                return None
            self._last_lookup[operation] = now
            try:
                found = self.lookup(operation)
            except Exception as exc:
                reason = str(exc) or type(exc).__name__
                self._broken(operation, reason)
                return None
            if found == stale:
                self._broken(
                    operation,
                    "Spotify's player still uses the code it refuses",
                )
                return None
            self._learnt[operation] = {'code': found, 'replaces': builtin}
            self._save()
            self._broken_sent.pop(operation, None)
            self.last_repair = {'operation': operation, 'ok': True}
        logger.info(
            'Spotify changed the {} query; using its new code {}…',
            operation,
            found[:12],
        )
        self.emit(
            'spotify',
            'Fixed by itself',
            f'Spotify changed its player ({operation}). Downtify found '
            'the new code and keeps reading Spotify.',
        )
        return found

    def _broken(self, operation: str, reason: str) -> None:
        self.last_repair = {
            'operation': operation,
            'ok': False,
            'reason': reason,
        }
        logger.warning(
            'Spotify refuses the {} query and no new code was found: {}',
            operation,
            reason,
        )
        now = self.clock()
        sent = self._broken_sent.get(operation)
        if sent is not None and now - sent < BROKEN_REPEAT:
            return
        self._broken_sent[operation] = now
        self.emit(
            'spotify',
            'Reading Spotify is broken',
            f'Spotify no longer accepts the {operation} query, and '
            f'Downtify could not find the new one ({reason}). Spotify '
            'playlists and watches fail until a Downtify update fixes it.',
        )


#: The one of this process.
store = HashStore()


def configure(path: Optional[Path]) -> None:
    store.configure(path)


def current(operation: str, builtin: str) -> str:
    return store.current(operation, builtin)
