---
icon: lucide/cookie
---

# YouTube Cookies

Downtify pulls its audio from YouTube. Most of the time that works anonymously — but not always:

- **Explicit / age-restricted tracks.** YouTube only serves these to a signed-in adult account. Without cookies the download fails.
- **Bot challenges.** On datacenter IPs (VPS, some VPNs) YouTube periodically answers with "Sign in to confirm you're not a bot" instead of audio.

Supplying a `cookies.txt` fixes both: yt-dlp then talks to YouTube as your logged-in browser session does.

## Uploading a cookies.txt (recommended)

1. Install a cookie-export extension: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome/Edge) or [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox)
2. Open `youtube.com` **logged into your Google account** and export the cookies for that site — the file must be in **Netscape** format
3. In Downtify, open **Settings** (⚙️) → **YouTube cookies** → **Upload cookies.txt**

The file is validated on upload — a file that isn't a Netscape cookie jar is rejected immediately rather than silently breaking every later download. If it contains no `youtube.com` or `google.com` cookies you get a warning, since that usually means it was exported from the wrong tab.

Once uploaded you can **replace** it (upload another file) or **delete** it from the same screen.

!!! tip "This is the platform-agnostic route"
    Uploading through the web UI needs no bind mounts, no file paths and no shell — which is what makes it work on Docker Desktop for Windows, where mounting a `cookies.txt` into the container is notoriously awkward.

## Where it's stored

The uploaded file is written to `cookies.txt` inside Downtify's data directory (`/data` by default) — the same volume that holds `settings.json` and the Playlist Monitor database. It therefore **survives container updates**: pulling a new image and recreating the container keeps your cookies, as long as `/data` stays a named volume or bind mount.

## Using an environment variable instead

The pre-existing [`DOWNTIFY_COOKIES_FILE`](../getting-started/environment-variables.md#anti-bot-youtube) variable still works and **takes precedence**:

```yaml
services:
  downtify:
    volumes:
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

When it is set, the settings screen shows the cookie section as locked and refuses uploads and deletions — the deployment owns that configuration, and Downtify must not overwrite a file it doesn't manage. Unset the variable (and recreate the container) to manage cookies from the web UI instead.

`DOWNTIFY_COOKIES_FROM_BROWSER` reads cookies straight out of a browser profile, but that requires the browser's cookie store to be reachable *inside* the container, so it's rarely usable in Docker.

## Keeping them working

- Cookies expire. If age-restricted downloads start failing again, export a fresh file and upload it as a replacement.
- Exporting from a **private/incognito window** that you then close produces a longer-lived session, because closing a normal window can invalidate the exported session.
- Some regions require full identity verification on the Google account before YouTube serves age-restricted content at all. Being signed in is not always enough.

!!! warning "Treat the file like a password"
    A `cookies.txt` contains live session tokens for your Google account. Anyone who can read it can act as you on YouTube. Downtify stores it with owner-only permissions where the filesystem supports it, and never exposes its contents through the API — only whether one is configured, its size and when it changed. Use a throwaway Google account if you'd rather not risk your main one.
