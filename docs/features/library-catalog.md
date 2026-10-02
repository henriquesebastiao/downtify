---
icon: lucide/library
---

# Library catalog & path sync

Downtify keeps a small **catalog** of the files under `/downloads` (the slskd folder, when [slskd files are left in place](slskd-navidrome.md#leave-files-in-place), and [extra folders](external-library.md) you add in Settings) so the Library page, player, M3U export, Navidrome sync and duplicate detection stay consistent when files move or playlists grow.

## What gets stored

| Store | Location | Purpose |
|-------|----------|---------|
| **Track index** | `/data/downtify_library.db` | Maps Spotify track IDs to library paths, so a track already on disk can be recognized |
| **Playlist catalog** | `/data/downtify_library.db` | Which tracks belong to each downloaded Spotify playlist |
| **Playlist downloads** | `/data/downtify_library.db` | Tracked Spotify playlist downloads and a cache of their Spotify track lists |
| **Navidrome index** | `/data/downtify_library.db` | Navidrome song IDs per file |
| **Library metadata cache** | `/data/downtify_library.db` | Title, artist, every credited artist, album, album artist, track number, year, length and cover size per file for `GET /tracks`, re-read only when a file's modification time or size changes |
| **Upgrade runs** | `/data/downtify_library.db` | The [library upgrade](library-upgrade.md) queue and when each track was last checked, so a run survives a restart |
| **Path scan cache** | RAM, plus a snapshot in `/data/downtify_library.db` | Folded `GET /tracks` rows, playlist listings and path pairs. UI routes serve this snapshot without walking the disk. Each finished download is **merged into the snapshot immediately** (so a new artist shows up without waiting). A delete **drops those files from the snapshot immediately** (so an album disappears from the grid without waiting). A full tree walk runs in the background a few seconds after the download queue is idle — not on a fixed timer. `GET /list?refresh=true` drops the snapshot and rescans now. |
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
    - **indexes** older entries that were stored before content keys existed;
    - **follows [liked songs](liked-songs.md#keeping-likes-in-step-with-the-files)** to their new location.
3. If **Generate M3U** and/or **Create playlists in Navidrome** are enabled, the affected playlists are rewritten.

It only runs when you press the button (or call `POST /api/library/reconcile`) — never on a schedule.

### Existing music folders

To play a collection that Downtify did not download, add the folders in **Settings → Library** and press **Sync folders**. Files stay on disk; tags are read and artists are matched. See [Existing music folders](external-library.md).

::: warning
Rewriting a playlist deletes library files whose tags clearly don't match the Spotify track they're registered for — see [slskd & Navidrome](slskd-navidrome.md#playlist-sync).
:::

::: info Deletes vs moves
Deleting tracks from the **Library** page already cleans up the catalog and rewrites the affected M3U files and Navidrome playlists in the background, so there's nothing to fix afterwards.
:::

## Library page

The Library page has four tabs — **Albums**, **Artists**, **Playlists** and **Tracks**:

- **Albums, artists and playlists** show as a cover grid or a compact list (the toggle is remembered), with a text filter and sorting by recently added, name, artist, year or number of tracks. Albums and artists are built from each file's tags (album artist, album, year), so they don't depend on how files are organized on disk. A compilation — album artist `Various Artists` — stays one album under Albums, while its tracks are on their own artists' pages (a duo wrongly tagged that way, like `Zé Neto & Cristiano`, too; **Unmark as Various Artists** on the album's page fixes the tag). A track without an album tag appears under Tracks and its artist, not under Albums.
- **Artists** lists every artist credited on a track, guests included: *Lady Marmalade* (Christina Aguilera, Lil' Kim, Mýa, P!nk) gives each of the four a page. A track counts for the artist it belongs to — its album artist, or for a compilation its first artist — and for each other artist credited on it; on a guest's page it's labelled **Guest**, and their Albums tab only shows albums of their own (it's hidden when there are none). **Various Artists** isn't listed: a compilation's tracks are on their artists' pages, and the album itself stays under Albums. Wherever a track shows its artists — track lists, the Now playing screen, Finder and top-song rows — each name links to that artist's own page (a song not in the Library yet only links the artists the Library already has). The artists come from the file's `ARTISTS` tag (see [Several artists and compilations](file-organization.md#several-artists-and-compilations)), so a name like *Earth, Wind & Fire* is never split on its comma; a file without that tag has its artist text split on `;`, ` / ` or `, `, unless that text is also the file's album artist (then it's one name).
- **Playlists** are the downloaded playlists with an [M3U file](m3u-export.md), playlists you create with **New playlist** (editable), plus tracked [playlist downloads](slskd-navidrome.md#playlist-downloads) that don't have an M3U yet. Imported Spotify/YouTube playlists stay read-only. Once you have [liked](liked-songs.md) a song, *Liked songs* is listed first. A playlist you created uses a mosaic of up to four track covers; imported playlists keep the artwork saved with the M3U.
- **Tracks** is a sortable table (title, album, format, date added, length) with a text filter, a format filter, and checkboxes — click one, then Shift-click another to select a range.

Opening an album, artist or playlist shows its tracks with **Play**, **Shuffle**, **Add to queue** and **Download as ZIP**. A playlist you created also has **Add songs** and **Rename**; a downloaded playlist page shows how many of its tracks are downloaded, lists the missing ones with **Download missing**, and offers **Watch for new tracks**. **Delete playlist** is in the **⋯** menu: imported playlists delete the audio; a playlist you created only removes the playlist.

**Download as ZIP** saves the selected tracks to the device you're browsing from as a single ZIP, keeping their folder layout — handy when Downtify runs on a home server and you want a batch of tracks locally. Combine it with **Select all** to take everything the current filter shows. The archive is built while it downloads, so nothing is written to the server's disk, and it's capped at 2000 tracks per download.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/list?refresh=true` | Library paths, bypassing the path scan cache |
| `GET` | `/api/library/summary` | Home page counts and recent albums, without the full track list |
| `GET` | `/api/library/albums` | Album tiles (counts + cover file), without every track |
| `GET` | `/api/library/artists` | Artist tiles (counts + cover file) for Library and Discover |
| `POST` | `/api/library/lookup` | Library rows for search/link songs already downloaded |
| `GET` | `/tracks` | Library tracks with tags. `?playlist=`, `?artist=`, `?album=`, `?q=` and `?limit=` return a subset |
| `GET` | `/media/{path}` | Serve a library file, including `slskd/…` and `ext/…` paths |
| `GET` | `/playlist-cover?file=…` | Serve a playlist's own [cover art](playlist-cover-art.md), reported as `cover` by `/playlists` |
| `POST` | `/api/library/archive` | Prepare a ZIP of selected tracks (returns a single-use ticket) |
| `GET` | `/api/library/archive/{token}` | Stream that ZIP to the browser |
| `DELETE` | `/api/library/playlist?playlist_name=…` | Delete an imported playlist's tracks, M3U and catalog — or only the M3U of a playlist you created |
| `POST` | `/api/library/playlists` | Create an empty editable playlist |
| `POST` | `/api/library/playlists/tracks` | Add or remove library files on a playlist you created |
| `POST` | `/api/library/playlists/rename` | Rename a playlist you created |
| `POST` | `/api/library/reconcile` | Fix library paths, then refresh M3U/Navidrome playlists |
| `POST` | `/api/library/external/sync` | Start a background scan of extra music folders |
| `GET` | `/api/library/external/sync` | Running extra-folder sync, or the last finished log |
| `POST` | `/api/library/external/unmap` | Drop an extra folder from the library without deleting audio |
| `GET`/`POST` | `/api/library/upgrade…` | Scan and repair what is already downloaded — see [Upgrade library](library-upgrade.md#api) |

See the [API reference](../api-reference.md#library) for request and response shapes.
