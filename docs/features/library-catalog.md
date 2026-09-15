---
icon: lucide/library
---

# Library catalog & path sync

Downtify keeps a small **catalog** of the files under `/downloads` (and the slskd folder, when [slskd files are left in place](slskd-navidrome.md#leave-files-in-place)) so the Library page, player, M3U export, Navidrome sync and duplicate detection stay consistent when files move or playlists grow.

## What gets stored

| Store | Location | Purpose |
|-------|----------|---------|
| **Track index** | `/data/downtify_library.db` | Maps Spotify track IDs to library paths, so a track already on disk can be recognized |
| **Playlist catalog** | `/data/downtify_library.db` | Which tracks belong to each downloaded Spotify playlist |
| **Playlist downloads** | `/data/downtify_library.db` | Tracked Spotify playlist downloads and a cache of their Spotify track lists |
| **Navidrome index** | `/data/downtify_library.db` | Navidrome song IDs per file |
| **Library metadata cache** | `/data/downtify_library.db` | Title, artist and album per file for `GET /tracks`, re-read only when a file's modification time or size changes |
| **Path scan cache** | In memory (short-lived) | The list of library paths, invalidated whenever Downtify adds or removes a file |
| **Cover art cache** | `/data/cover_cache` (optional) | Extracted cover images for `GET /cover` |

Files are matched across moves by a **content key** — a hash of the file's name and size. Moving a file to another folder keeps its key; replacing it with a different file gives it a new one.

## Settings → Library

### Cache cover art on disk

When enabled, Downtify keeps extracted cover images under `/data/cover_cache`, so the Library and player don't re-read tags for every thumbnail. Safe to turn off anytime; it only costs disk space.

### Fix library paths

Use this after you **move or rename files on disk** outside Downtify, or delete them by hand.

1. Open **Settings → Library → Fix library paths**.
2. Downtify scans the library folders and:
    - **updates paths** in the track index and playlist catalog when a file is no longer where it was but the same file (same content key) is found elsewhere;
    - **removes stale entries** for files that no longer exist;
    - **indexes** older entries that were stored before content keys existed.
3. If **Generate M3U** and/or **Create playlists in Navidrome** are enabled, the affected playlists are rewritten.

It only runs when you press the button (or call `POST /api/library/reconcile`) — never on a schedule.

!!! warning
    Rewriting a playlist deletes library files whose tags clearly don't match the Spotify track they're registered for — see [slskd & Navidrome](slskd-navidrome.md#playlist-sync).

!!! note "Deletes vs moves"
    Deleting tracks from the **Library** page already cleans up the catalog and rewrites the affected M3U files and Navidrome playlists in the background, so there's nothing to fix afterwards.

## Library page

Besides the existing filters and multi-select, the Library page shows your [playlist downloads](slskd-navidrome.md#playlist-downloads) and offers **Delete playlist** while a playlist filter is selected.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/list?refresh=true` | Library paths, bypassing the path scan cache |
| `GET` | `/tracks` | Library tracks with tags and, when known, the `playlists` they belong to |
| `GET` | `/media/{path}` | Serve a library file, including `slskd/…` paths |
| `DELETE` | `/api/library/playlist?playlist_name=…` | Delete a playlist's tracks, M3U and catalog entry |
| `POST` | `/api/library/reconcile` | Fix library paths, then refresh M3U/Navidrome playlists |

See the [API reference](../api-reference.md#library) for request and response shapes.
