"""Setting up the Spotify companion with an AI agent.

Settings > Apps > Spotify companion > "Set up with an AI agent" makes a
**setup link** and a page of instructions to paste into an agent that
runs on the server (Hermes, OpenClaw, Claude Code, n8n's AI agent…). The
agent can then fetch the extension, run it in a browser on the server -
a browser container with a web desktop, or a headless Chromium it
already has - and check that it works, without an admin's sign-in:

* ``GET /api/companion/agent/{ticket}/extension.zip`` - the extension,
  with this server's address (``?address=`` changes it) and a key. The
  first download makes the key; later ones within the day reuse it.
* ``GET /api/companion/agent/{ticket}/status`` - how the companion is
  doing (no names, no keys), for the agent to know when it's done.

A link works for a day, is kept in memory only (a restart ends it) and
is long enough to be unguessable. The instructions tell the agent never
to type or ask for the Spotify password: the person signs in themselves.
"""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote, urlsplit

#: How long a setup link works.
TTL = timedelta(hours=24)
#: Links kept at once (the oldest go first).
MAX_TICKETS = 20


@dataclass
class Ticket:
    user_id: int
    address: str
    expires: datetime
    # The key, made on the first download and reused by later ones.
    key: str = ''
    downloads: int = 0
    made: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Tickets:
    """The setup links of this process."""

    def __init__(self) -> None:
        self._items: dict[str, Ticket] = {}
        self._lock = threading.Lock()

    def make(
        self, user_id: int, address: str, now: datetime
    ) -> tuple[str, Ticket]:
        ticket = Ticket(
            user_id=user_id, address=address, expires=now + TTL, made=now
        )
        token = secrets.token_urlsafe(24)
        with self._lock:
            self._prune(now)
            while len(self._items) >= MAX_TICKETS:
                oldest = min(self._items, key=lambda k: self._items[k].made)
                self._items.pop(oldest)
            self._items[token] = ticket
        return token, ticket

    def get(self, token: str, now: datetime) -> Optional[Ticket]:
        with self._lock:
            self._prune(now)
            return self._items.get(token)

    def _prune(self, now: datetime) -> None:
        for token in [k for k, v in self._items.items() if v.expires <= now]:
            self._items.pop(token)


def origin_of(address: str) -> str:
    """``scheme://host[:port]`` of an http(s) address, or ''."""

    try:
        parts = urlsplit(str(address or '').strip())
    except ValueError:
        return ''
    if parts.scheme not in {'http', 'https'} or not parts.netloc:
        return ''
    return f'{parts.scheme}://{parts.netloc}'


_COMPOSE = """\
services:
  spotify-browser:
    image: lscr.io/linuxserver/chromium:latest
    container_name: spotify-browser
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC                 # the server's time zone
      - CUSTOM_USER=companion      # the web desktop holds a Spotify sign-in:
      - PASSWORD=<choose one>      # protect it, and tell the person
      - CHROME_CLI=--load-extension=/companion --disable-extensions-except=/companion
    volumes:
      - ./spotify-browser:/config              # the browser profile, kept
      - ./downtify-companion:/companion:ro     # the unzipped extension
    ports:
      - 3011:3001                  # the web desktop (HTTPS), home network only
    shm_size: 1gb
    restart: unless-stopped"""


def instructions(
    base: str, address: str, token: str, expires: datetime
) -> str:
    """The page to paste into an AI agent."""

    zip_url = f'{base}/api/companion/agent/{token}/extension.zip'
    status_url = f'{base}/api/companion/agent/{token}/status'
    until = expires.strftime('%Y-%m-%d %H:%M UTC')
    return f"""\
# Set up the Downtify Spotify companion

You are helping me run the **Downtify Spotify companion** on my server. It is a
browser extension that runs in a browser signed in to *my* Spotify account and
sends Downtify the songs of my personal Spotify mixes (Daily Mix, Discover
Weekly, mood mixes…), so Downtify follows my own version of them. Downtify
decides what is read and when; the extension only needs to keep running.

Guide: https://henriquesebastiao.github.io/downtify/features/spotify-companion

## Rules

- **Never type, ask for, store or copy my Spotify password, cookies or tokens.**
  I sign in to Spotify myself, in the browser you set up. When that step comes,
  stop and tell me exactly what to open and click.
- Don't change Downtify's settings, watches or library. Only set up the browser.
- Use a browser profile of its own for the companion, not one you browse with:
  the extension keeps one pinned Spotify tab, and nothing else may navigate it.
- The links below are private (they work until {until}). Don't paste them
  anywhere public.

## 1. Get the extension

Download the extension (a ZIP; its files are at the top level) and unzip it into
a folder the browser can read, for example `./downtify-companion`:

```
curl -fL "{zip_url}?address={quote(address, safe='')}" -o downtify-companion.zip
unzip -o downtify-companion.zip -d downtify-companion
```

The `address` is the Downtify address the **browser** will use. It is filled in
with `{address}`. If the browser runs in a container or on another machine and
can't reach that, download again with an address it can reach (usually
`http://<server LAN IP>:<Downtify port>`, never `localhost` from inside a
container). The ZIP carries that address and its key, and the browser is allowed
to reach that address without anyone clicking anything. You may download again
as often as needed until the link expires; the key stays the same.

## 2. Run it in a browser on the server

Pick one.

### A. A browser container with a web desktop (recommended)

Best when I'll sign in through a web page. It needs about 0.5 to 1 GB of memory.
Docker Compose (on ZimaOS: a custom app):

```yaml
{_COMPOSE}
```

Start it, then tell me to open `https://<server>:3011` (user and password as
set), sign in to Spotify there, and leave it running.

### B. A headless Chromium you already run (for example your own browser)

Only if it can load extensions:

- It must be **Chromium** (or Brave, Edge). **Google Chrome 137 and later ignore
  `--load-extension`.**
- Start a separate instance for the companion with its own, kept profile and the
  new headless mode, for example:

  ```
  chromium --headless=new \\
    --user-data-dir=/path/to/companion-profile \\
    --load-extension=/path/to/downtify-companion \\
    --disable-extensions-except=/path/to/downtify-companion \\
    --remote-debugging-address=127.0.0.1 --remote-debugging-port=9333 \\
    --no-first-run \\
    --user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
  ```

  (A normal user agent: Spotify's web player may refuse "HeadlessChrome".)
- Keep it running (a systemd service or a container with a restart policy) and
  restart it the same way after reboots. The profile must persist: it holds the
  Spotify sign-in.
- **Signing in**, by me, one of:
  1. From my computer: forward the debugging port
     (`ssh -L 9333:127.0.0.1:9333 <server>`), open `chrome://inspect` in Chrome
     on my computer, **Configure…** → add `localhost:9333`, then **inspect** the
     `open.spotify.com` tab. The page appears in DevTools and I can click
     **Log in** and type there myself.
  2. Or start the same profile once with a screen (a VNC/noVNC session or X
     forwarding), sign in, close it and start it headless again.

## 3. Check that it works

The extension checks in with Downtify about once a minute. Ask:

```
curl -fsS "{status_url}"
```

`status` should become `ready`. Until then it says what's missing:

| status | meaning | what to do |
| --- | --- | --- |
| `never_connected` | the extension hasn't reached Downtify yet | is the browser running with the extension? Can it reach the address in step 1? |
| `signed_out` | the browser isn't signed in to Spotify | ask me to sign in (step 2) |
| `no_player` | no Spotify tab to read with | wait a minute; the extension opens one |
| `other_account` | signed in to a different Spotify account than before | ask me: I accept it in Downtify, Settings > Apps > Spotify companion |
| `away` | it stopped checking in | is the browser still running? |
| `off` | the companion is turned off in Downtify | ask me to turn it on in Settings > Apps > Spotify companion |
| `error` | see `message` | |

When it's `ready`, tell me. Then you're done: the browser just needs to keep
running. If it stops, Downtify notifies me.
"""
