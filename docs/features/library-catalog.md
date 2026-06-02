---
icon: lucide/library
---

# Library catalog & path sync

Downtify keeps a **catalog** of files under `/downloads` and `/slskd` so the Library page, player, M3U export, Navidrome sync, and deduplication stay fast and consistent when files move or playlists grow.

## What gets stored

| Store | Location | Purpose |
|-------|----------|---------|
| **Track index** | `/data` SQLite | Maps Spotify track IDs → library path; skips re-downloads |
| **Playlist catalog** | `/data` SQLite | Which tracks belong to each downloaded Spotify playlist |
| **Navidrome index** | `/data` SQLite | Caches Navidrome song IDs per file (`content_key`) |
| **Library metadata cache** | `/data` SQLite | Title, artist, album for `/api/list` without re-reading every tag |
| **Path scan cache** | In-memory (~90s TTL) | List of relative paths under `/downloads` and `/slskd` |
| **Cover art cache** | `/data/cover_cache` (optional) | Embedded cover bytes for `/cover` and the Library thumbnails |

Tracks are identified for matching and cache invalidation by a **content key**: SHA-256 of the file **basename + size**. Renaming or moving a file without changing name/size updates the stored path; replacing the file with different content gets a new key.

## Library page (UI)

Open **Library** in the nav bar.

- **Search** — Filters the current list by title, artist, album, or path (client-side). The global navbar search is hidden on this page so only one search box is shown.
- **Pagination** — Page size is configurable and remembered in the browser (`25` / `50` / `100`).
- **Playlist badges** — Shows which saved Spotify playlists include each track (from the playlist catalog).
- **Refresh** — Reloads the list from the server; use **Refresh** after bulk file changes. The backend bypasses caches when `?refresh=true` is passed.
- **Play / download / delete** — Same actions as before; delete removes the file and cleans track index, playlist catalog, and cover cache entries.

## Settings → Library & player

### Cache album art on disk

When enabled, Downtify writes extracted cover images under `/data/cover_cache`. The player and Library load covers from disk instead of parsing tags on every request. Safe to disable anytime; extra disk use only.

### Fix library paths (manual reconcile)

Use after you **move or reorganize files on disk** (same filename and size, new folder).

1. Open **Settings** → **Library & player** → **Fix library paths**.
2. Downtify scans `/downloads` and `/slskd`, builds a disk index by `content_key`, and:
   - **Updates paths** in the track index and playlist catalog when the old path no longer exists but the same file is found elsewhere.
   - **Prunes stale rows** when the file was deleted (including playlist catalog entries).
   - **Backfills `content_key`** on older index rows that only had paths.
3. If **Generate M3U** and/or **Create playlist in Navidrome** are enabled, affected playlists are regenerated or re-synced after path updates.

Reconcile does **not** run on a schedule or at startup — only when you press the button (or call `POST /api/library/reconcile`).

!!! note "Deletes vs moves"
    Deleting a track from the **Library** UI removes the file, catalog rows, and (when M3U or Navidrome sync is enabled) rewrites affected playlists. **Fix library paths** is for **moves** and for **manual deletes on disk** (Finder, SSH, etc.) that left stale rows in the database. If you already deleted in the UI, reconcile often reports “no changes” because the catalog is already clean — use **Refresh** on the Library page if the list looks stale.

## Navidrome (related behavior)

- **Large playlists** — `createPlaylist` uses POST with batched `updatePlaylist` so hundreds of song IDs do not trigger HTTP 414.
- **Matching** — Library scan, path tail matching, mutagen tags, and slskd-style paths; search stops early when a confident match is found.
- **Playlist catalog** — Monitor and playlist downloads register tracks so reconcile and Navidrome refresh know playlist membership.

See [Navidrome setup](../../README.md#-navidrome-playlist-sync) in the README for server folders and credentials.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/list` | Library entries with metadata and `playlists: string[]` |
| `GET` | `/api/list?refresh=true` | Bypass path/metadata caches |
| `POST` | `/api/library/reconcile` | Run path reconcile + optional M3U/Navidrome refresh |
| `GET` | `/cover?file=…` | Cover art (uses disk cache when enabled) |

Response shape for reconcile:

```json
{
  "paths_updated": 0,
  "pruned_stale": 0,
  "content_keys_backfilled": 0,
  "playlists_affected": [],
  "refresh_m3u": false,
  "refresh_navidrome": false
}
```
