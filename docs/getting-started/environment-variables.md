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

## Anti-bot / YouTube

YouTube periodically challenges automated downloaders. These variables give you escape hatches when the defaults stop working.

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNTIFY_FORCE_IPV4` | _(unset)_ | Set to `1` to force yt-dlp to use IPv4 only. Useful when your host has a broken or rate-limited IPv6 address. |
| `DOWNTIFY_YT_PLAYER_CLIENTS` | `ios,android,web_embedded,mweb,web,tv` | Comma-separated list of yt-dlp player clients to try, in order. Downtify's default list already favours clients that work without a JavaScript runtime. Override this only if you know a specific client is being blocked. |
| `DOWNTIFY_YT_PO_TOKEN` | _(unset)_ | Comma-separated Proof-of-Origin tokens for yt-dlp, each in the form `<client>.<context>+<token>` (e.g. `mweb.gvs+ABC123`). Required only if YouTube starts demanding PO Tokens for the clients you're using. |
| `DOWNTIFY_COOKIES_FILE` | _(unset)_ | Path to a Netscape-format `cookies.txt` inside the container. Lets yt-dlp authenticate as a real browser session. Useful when YouTube enforces age verification or login walls. |
| `DOWNTIFY_COOKIES_FROM_BROWSER` | _(unset)_ | Browser name to extract cookies from (e.g. `chrome`, `firefox`). Requires the browser's cookie store to be accessible inside the container. |

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

Use a browser extension such as [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome) or [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox). Export from `youtube.com` while logged into a real Google account, then mount the file into the container as shown above.

!!! warning
    Keep your `cookies.txt` private — it contains session tokens that grant access to your Google account.
