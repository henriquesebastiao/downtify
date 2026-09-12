---
icon: lucide/life-buoy
---

# Troubleshooting

Common problems and what fixes them. Most download failures come down to one of the first two entries.

## A track with explicit content won't download

**Symptom** — the download fails and the queue shows a message about the track being age-restricted, or (on older versions) a raw error like:

```
Error: ERROR: [youtube] <id>: Sign in to confirm your age.
This video may be inappropriate for some users.
```

**Cause** — YouTube only serves age-restricted (explicit) tracks to a signed-in adult account. Downtify downloads anonymously by default, so YouTube refuses.

**Fix** — supply YouTube cookies: **Settings** (⚙️) → **YouTube cookies** → **Upload cookies.txt**. See [YouTube Cookies](features/youtube-cookies.md) for how to export the file.

If it still fails with cookies configured, the cookies are stale or the account itself hasn't completed Google's age verification. Export a fresh file from a browser logged into a verified account and upload it again.

## Downloads fail, time out, or never start

**Symptom** — downloads fail for seemingly ordinary tracks, sometimes with "Sign in to confirm you're not a bot" or a format/extraction error.

**Cause** — YouTube throttles and challenges requests it considers automated. This is much more common on a VPS or behind a VPN than on a home connection.

**Fix**, in order of how often it helps:

1. **Upload a `cookies.txt`** ([YouTube Cookies](features/youtube-cookies.md)). An authenticated session is challenged far less often. This is the single most effective fix.
2. **Add a delay between downloads** — **Settings** → *Delay between downloads* (try 5–15 s) and lower *Parallel downloads*. Hammering YouTube with a whole playlist at once is what triggers rate limiting.
3. **Force IPv4** — set `DOWNTIFY_FORCE_IPV4=1` if your host advertises IPv6 but can't actually route it (shows up as DNS/`EAI_AGAIN` errors).
4. **Update the image** — `docker compose pull && docker compose up -d`. YouTube changes its defenses often and each release ships a newer `yt-dlp`.

## A cookies.txt on Windows / Docker Desktop isn't picked up

**Symptom** — `DOWNTIFY_COOKIES_FILE` is set but Downtify behaves as if there were no cookies.

**Cause** — the path is a *container* path. A Windows path like `C:\Users\me\cookies.txt` means nothing inside the container, and the file must be bind-mounted before the variable can point at it.

**Fix** — skip the variable entirely and upload the file through **Settings** → **YouTube cookies**. That path needs no mounts and works identically on every platform.

If you'd rather keep the variable, mount the file and point at the mount target, not the host path:

```yaml
volumes:
  - ./cookies.txt:/cookies.txt:ro
environment:
  - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

## The cookie upload button is greyed out

`DOWNTIFY_COOKIES_FILE` is set, so that deployment manages its own cookie file and the web UI stays read-only on purpose. Remove the variable (and recreate the container) to manage cookies from the UI.

## Uploaded cookies disappeared after updating the container

The uploaded file lives in Downtify's data directory (`/data`). If that directory isn't a named volume or bind mount, everything in it — settings and the Playlist Monitor database included — is lost when the container is recreated:

```yaml
volumes:
  - ./downloads:/downloads
  - downtify_data:/data   # ← keep this
```

## "cookies.txt is invalid" when uploading

Downtify validates the file on upload. It must be a **Netscape** cookie jar: one cookie per line, fields separated by tabs, optionally with `#` comments. A JSON export, a spreadsheet, or a copied `Cookie:` header is rejected.

Use a browser extension that exports the Netscape format (see [YouTube Cookies](features/youtube-cookies.md)) and export while the tab is on `youtube.com`.

## A playlist re-downloads tracks I already have

Downtify records every auto-downloaded track in its database, so moving files elsewhere on disk does not trigger a re-download. A track is only re-downloaded after an hourly check finds its file genuinely missing from the downloads directory. See [Playlist Monitor](features/playlist-monitor.md#how-it-works).

If files vanish on every restart, the `/downloads` volume isn't persisted — same fix as above.

## Downloaded audio has the wrong metadata or cover

Downtify resolves metadata from Spotify and matches the audio on YouTube Music. A mismatch usually means the match landed on a cover, remix or live version. Downloading from the Spotify **album** link rather than a search result gives the matcher much more to work with (track number, album, release type).

## Still stuck?

Open an issue at [github.com/henriquesebastiao/downtify/issues](https://github.com/henriquesebastiao/downtify/issues) with:

- the Downtify version (shown in the UI footer),
- the container logs around the failure (`docker compose logs downtify`),
- and whether cookies are configured.
