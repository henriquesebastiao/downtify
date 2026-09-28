---
icon: lucide/settings
---

# Environment Variables

All environment variables are optional. Downtify works out of the box without any of them.

## Core

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNTIFY_PORT` | `8000` | Port the server listens on inside the container. Change the left side of the port mapping to expose a different host port. |
| `DOWNLOAD_DIR` | `/downloads` | Directory where audio files are saved. Override if you mount your library at a custom path. |
| `HOST` | `0.0.0.0` | Bind address for the web server. |
| `DOWNTIFY_LOG_LEVEL` | `info` | Application log level (`debug`, `info`, `warning`, …). |
| `TZ` | `UTC` | Local timezone (IANA name, e.g. `America/Sao_Paulo`), used to interpret `DOWNTIFY_MONITOR_SYNC_TIME` below. |

## Playlist Monitor

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNTIFY_MONITOR_SYNC_TIME` | _(unset)_ | Time of day (24h `HH:MM`, local to `TZ` above) at which [Playlist Monitor](../features/playlist-monitor.md#choosing-a-daily-sync-time) syncs with a daily-or-longer interval (every day, week, 2 weeks, month) should run. Leave unset to sync exactly one interval after the previous check, whatever time that lands on. |

```yaml
environment:
  - TZ=America/Sao_Paulo
  - DOWNTIFY_MONITOR_SYNC_TIME=03:00
```

## Mobile apps and sign-in

See [Mobile Apps](../features/mobile-apps.md) and [Users & Sign-in](../features/users.md). Signing in is always required; `DOWNTIFY_REQUIRE_SIGN_IN` from earlier versions is no longer used (a warning is logged while it's set).

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNTIFY_TRUSTED_PROXIES` | _(unset)_ | Comma-separated addresses or networks of your reverse proxy (e.g. `172.18.0.0/16,10.0.0.5`). Only requests from these have their `X-Forwarded-For`, `X-Forwarded-Proto` and `X-Forwarded-Host` headers believed — for the client address that sign-in and pairing attempts are rate-limited by, the secure flag on the sign-in cookie, and the same-site check. Unset: those headers are ignored. |
| `DOWNTIFY_DISCOVERY` | `true` | `false` stops announcing the server on the local network (mDNS, `_downtify._tcp`), which the apps use to list it under *Found on this network*. In Docker's bridge network the announcement doesn't reach the LAN anyway — see [Docker Compose](docker-compose.md#finding-the-server-from-the-apps). |
| `DOWNTIFY_TRANSCODE_CACHE_MB` | `2048` | Largest size, in MB, the cache of transcoded copies (`/data/transcode_cache`) is kept under; least recently played copies go first. |
| `DOWNTIFY_TRANSCODE_CONCURRENCY` | `2` | How many songs are transcoded at once for the apps' smaller streaming qualities. |

## Health check

The image has a built-in [Docker `HEALTHCHECK`](https://docs.docker.com/reference/dockerfile/#healthcheck) — no custom `--health-cmd` needed. It polls `GET /api/health` on the container's own port every 30 seconds (5 second timeout, 20 second start-up grace period, 3 retries before the container is marked unhealthy). `docker ps` and `docker inspect` show the result, and tools like Compose's `condition: service_healthy` or Watchtower can act on it.

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNTIFY_HEALTHCHECK` | `1` | Set to `0` to disable the built-in check — it then always reports healthy without contacting the server. Use this if an external/orchestrator-level check (e.g. a Kubernetes liveness probe) should be the only one deciding container health. |

```yaml
environment:
  - DOWNTIFY_HEALTHCHECK=0
```

## Anti-bot / YouTube

YouTube periodically challenges automated downloaders. These variables give you escape hatches when the defaults stop working.

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNTIFY_FORCE_IPV4` | _(unset)_ | Set to `1` to force yt-dlp to use IPv4 only. Useful when your host has a broken or rate-limited IPv6 address. |
| `DOWNTIFY_YT_PLAYER_CLIENTS` | `ios,android,web_embedded,mweb,web,tv` | Comma-separated list of yt-dlp player clients to try, in order. Downtify's default list already favours clients that work without a JavaScript runtime. Override this only if you know a specific client is being blocked. |
| `DOWNTIFY_YT_PO_TOKEN` | _(unset)_ | Comma-separated Proof-of-Origin tokens for yt-dlp, each in the form `<client>.<context>+<token>` (e.g. `mweb.gvs+ABC123`). Required only if YouTube starts demanding PO Tokens for the clients you're using. |
| `DOWNTIFY_COOKIES_FILE` | _(unset)_ | Path to a Netscape-format `cookies.txt` **inside the container**. Lets yt-dlp authenticate as a real browser session — needed for explicit/age-restricted tracks and whenever YouTube enforces a login wall. Takes precedence over a file uploaded in the web UI, and makes that UI section read-only. See [YouTube Cookies](../features/youtube-cookies.md). |
| `DOWNTIFY_COOKIES_FROM_BROWSER` | _(unset)_ | Browser name to extract cookies from (e.g. `chrome`, `firefox`). Requires the browser's cookie store to be accessible inside the container, so it's rarely usable in Docker. |

::: tip You probably don't need these
You can upload a `cookies.txt` straight from **Settings → YouTube cookies** in the web UI. It's stored in `/data` (so it survives container updates), needs no bind mount or container path, and works the same on Windows, macOS and Linux. The variables above stay supported for deployments that prefer to manage the file themselves.
:::

## Example: Docker Compose with anti-bot settings

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_FORCE_IPV4=1
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
    restart: unless-stopped
```

## Getting a cookies.txt

Use a browser extension such as [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome) or [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox). Export from `youtube.com` while logged into a real Google account, then either upload it in **Settings → YouTube cookies** or mount it into the container as shown above.

See [YouTube Cookies](../features/youtube-cookies.md) for the full walkthrough, and [Troubleshooting](../troubleshooting.md) when downloads still fail.

::: warning
Keep your `cookies.txt` private — it contains session tokens that grant access to your Google account.
:::
