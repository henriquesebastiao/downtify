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
| **Library metadata cache** | `/data/downtify_library.db` | Title, artist, album, album artist, track number, year and length per file for `GET /tracks`, re-read only when a file's modification time or size changes |
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

::: warning
Rewriting a playlist deletes library files whose tags clearly don't match the Spotify track they're registered for — see [slskd & Navidrome](slskd-navidrome.md#playlist-sync).
:::

::: info Deletes vs moves
Deleting tracks from the **Library** page already cleans up the catalog and rewrites the affected M3U files and Navidrome playlists in the background, so there's nothing to fix afterwards.
:::

## Library page

The Library page has four tabs — **Albums**, **Artists**, **Playlists** and **Tracks**:

- **Albums, artists and playlists** show as a cover grid or a compact list (the toggle is remembered), with a text filter and sorting by recently added, name, artist, year or number of tracks. Albums and artists are built from each file's tags (album artist, album, year), so they don't depend on how files are organized on disk. A track without an album tag appears under Tracks and its artist, not under Albums.
- **Playlists** are the downloaded playlists with an [M3U file](m3u-export.md), plus tracked [playlist downloads](slskd-navidrome.md#playlist-downloads) that don't have one yet.
- **Tracks** is a sortable table (title, album, format, date added, length) with a text filter, a format filter, and checkboxes — click one, then Shift-click another to select a range.

Opening an album, artist or playlist shows its tracks with **Play**, **Shuffle**, **Add to queue** and **Download as ZIP**. A playlist page also shows how many of its tracks are downloaded, lists the missing ones with **Download missing**, and offers **Watch for new tracks** and **Delete playlist** in its **⋯** menu.

**Download as ZIP** saves the selected tracks to the device you're browsing from as a single ZIP, keeping their folder layout — handy when Downtify runs on a home server and you want a batch of tracks locally. Combine it with **Select all** to take everything the current filter shows. The archive is built while it downloads, so nothing is written to the server's disk, and it's capped at 2000 tracks per download.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/list?refresh=true` | Library paths, bypassing the path scan cache |
| `GET` | `/tracks` | Library tracks with tags and, when known, the `playlists` they belong to |
| `GET` | `/media/{path}` | Serve a library file, including `slskd/…` paths |
| `POST` | `/api/library/archive` | Prepare a ZIP of selected tracks (returns a single-use ticket) |
| `GET` | `/api/library/archive/{token}` | Stream that ZIP to the browser |
| `DELETE` | `/api/library/playlist?playlist_name=…` | Delete a playlist's tracks, M3U and catalog entry |
| `POST` | `/api/library/reconcile` | Fix library paths, then refresh M3U/Navidrome playlists |

See the [API reference](../api-reference.md#library) for request and response shapes.
