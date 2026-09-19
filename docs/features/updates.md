---
icon: lucide/download
---

# Update Notifications

Downtify checks its own [GitHub Releases page](https://github.com/henriquesebastiao/downtify/releases) once an hour. When a newer version is out, a notice appears at the bottom of the sidebar on every page — on phones, a dot on the **More** tab and a line at the top of its sheet — and in **Settings → About**:

> ✦ Update 3.0.1 available

Click it to open that release on GitHub.

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
