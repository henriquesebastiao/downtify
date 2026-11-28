---
icon: lucide/download
---

# Update Notifications

Downtify checks its own [GitHub Releases page](https://github.com/henriquesebastiao/downtify/releases) once an hour. When a newer version is out, a notice appears at the bottom of the sidebar on every page — on phones, a dot on the **More** tab and a line at the top of its sheet — and in **Settings → About**:

> ✦ Update 3.0.1 available

Click it to open that release on GitHub.

## What's new after an update

The first time the web app opens after Downtify was updated, a **What's new in Downtify 3.12.0** dialog lists the release's highlights, with a **Full changelog** button that opens the release on GitHub and a quiet line to star the repository. **Got it** (or closing it) hides it until the next update. **Settings → About → What's new** opens it again.

- It's remembered per browser: each browser (and each signed-in person using it) sees it once per update. A browser that never opened Downtify before — a fresh install — isn't shown it.
- The highlights are bundled with the app, so the dialog works without internet access; only the two links go to GitHub. A release without written highlights shows just the link to its changelog.
- It waits for sign-in, and doesn't open over the prompt to change the default password.

## How it works

- A background task in the backend (`downtify/update_check.py`) fetches the latest release from GitHub's API once immediately at startup, then every hour. It's fire-and-forget: nothing in the UI waits on it.
- The web UI reads the cached result from `GET /api/check_update` (see [API Reference](../api-reference.md)) once per hour and shows the notice when a newer version is found.
- Versions are compared numerically (`2.10.0` < `2.9.0` is false, unlike a plain string comparison), and an optional `v` prefix on the release tag is ignored.

## If GitHub is unreachable

A failed check (offline host, GitHub rate limit) is logged and simply retried on the next hourly pass — the previous result, if any, stays in effect until then. The check never blocks anything else Downtify does; there's no user-facing error for it.

## Nothing is downloaded automatically

This only ever *tells* you a new version exists — Downtify does not update itself (only yt-dlp can, see below). To actually update, pull the new image and recreate the container:

```bash
docker compose pull
docker compose up -d
```

## yt-dlp updates

YouTube changes its pages every few weeks, and an older [yt-dlp](https://github.com/yt-dlp/yt-dlp) then fails every YouTube download until it is updated. Each Downtify release ships the yt-dlp of its day, so a fix normally waits for the next release. **Settings → Sources → YouTube → yt-dlp** can update it in between. It is off by default.

With **Update yt-dlp by itself** on, once a day (and within two hours when YouTube downloads keep failing) Downtify:

1. asks [PyPI](https://pypi.org/project/yt-dlp/) for the newest yt-dlp release;
2. downloads its wheel and checks it against the SHA-256 checksum PyPI publishes;
3. unpacks only the `yt_dlp` package into `<data>/yt-dlp/<version>/` (nothing is installed into the image and no setup code runs);
4. tests it in a separate process: it must read the audio formats of a YouTube video, the way a download starts (with your cookies, when you uploaded some);
5. keeps it only when the test passes, and loads it the next time Downtify starts.

With **Restart when it's quiet** on (the default), Downtify then restarts by itself once nothing is downloading and no long job (Doctor, library upgrade, ratings, backup…) is running. It restarts inside the same container, the way a port change in **Settings → Server** does. **Restart now** does it straight away.

If it goes wrong:

- A version that fails the test while the one in use passes is never used.
- If both fail, YouTube may be unreachable or want fresh cookies: nothing changes and the next check tries again.
- A saved copy that won't load when Downtify starts is set aside, and the previous version (or the built-in one) is used instead.
- **Go back to …** returns to the version before, and that newer version is not installed again. **Use the built-in version** returns to the yt-dlp that came with the image and switches updating off. Both apply at the next restart.

Only the current and the previous version are kept on disk. A Downtify update brings a new built-in yt-dlp; a saved copy older than it is not used.

### When YouTube downloads keep failing

Whether updating is on or not, Downtify watches YouTube downloads. When ten fail in a row, over at least three different songs, for reasons that aren't about one song (removed, private, region-locked, age-restricted) or the network, the **yt-dlp** card shows it and the **yt-dlp** [notification](notifications.md) says so, with the yt-dlp in use and the last error. With updating off, it also says when a newer yt-dlp is out. The first YouTube download that works again sends "working again".

When most of those failures are YouTube's bot check ("Sign in to confirm you're not a bot"), the message comes as the **YouTube cookies** notification instead and asks for fresh [cookies](youtube-cookies.md).
