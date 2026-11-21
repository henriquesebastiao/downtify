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

This only ever *tells* you a new version exists — Downtify does not update itself. To actually update, pull the new image and recreate the container:

```bash
docker compose pull
docker compose up -d
```
