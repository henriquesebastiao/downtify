---
icon: material/api
---

# API Reference

Downtify exposes a JSON REST API used by the web UI. All endpoints are served on the same port as the web UI (default: **8000**).

## General

### `GET /api/version`

Returns the current Downtify version as a plain string.

**Response:** `"2.6.0"`

---

### `GET /api/check_update`

Result of the last hourly check against [GitHub Releases](https://github.com/henriquesebastiao/downtify/releases) — powers the update notice in the sidebar (and the **More** sheet on phones). The request to GitHub happens on a background loop, never on this endpoint's own request; this just reads whatever that loop last found.

**Response:**

```json
{
  "current_version": "2.11.0",
  "latest_version": "2.12.0",
  "update_available": true,
  "release_url": "https://github.com/henriquesebastiao/downtify/releases/tag/2.12.0",
  "last_checked": "2026-09-13T07:06:16.610181+00:00"
}
```

Returns `null` in the brief window right after startup, before the first check has completed. If the check to GitHub fails (network issue, rate limit), the previous result — or `latest_version: null` if there hasn't been a successful one yet — carries over until the next hourly attempt; this endpoint itself never fails because of it.

---

## Search & resolve

### `GET /api/songs/search`

Search YouTube Music by free text.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | yes | Search query |

**Response:** Array of song objects (up to 20 results).

When YouTube Music returns nothing and slskd is an enabled audio source, the response is a single placeholder song built from the query itself (`"source": "text_search"`; `Artist - Title` is split into artist and title), so it can still be downloaded from Soulseek.

---

### `GET /api/song/url`

Resolve a Spotify or YouTube Music URL to metadata.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | yes | Spotify track, album or playlist URL, or a YouTube / YouTube Music video, album, playlist or artist URL |

**Response:**

- **Track URL** → single song object
- **Album URL** → array of song objects
- **Playlist URL** → array of song objects. For a YouTube Music playlist (`…/playlist?list=…`), every song is pinned to the playlist's own video (`youtube_id`), and for uploads the artist/title are taken from an `Artist - Title` video title. See [YouTube Music playlists](features/playlist-monitor.md#youtube-music-playlists).
- **Artist URL** (YouTube Music `…/channel/UC…` or `…/@handle`) → array of release summaries. `404` if a handle doesn't belong to an artist.

`GET /api/url` is an alias for this endpoint.

---

### `GET /api/url/resolve`

Resolve a pasted link to a single object describing what it points at — used by the web UI's link page. Accepts the same URLs as [`GET /api/song/url`](#get-apisongurl).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | yes | Spotify track, album or playlist URL, or a YouTube / YouTube Music video, album, playlist or artist URL |

**Response:**

```json
{
  "kind": "album",
  "name": "Whenever You Need Somebody",
  "subtitle": "Rick Astley",
  "cover_url": "https://…",
  "year": "1987",
  "tracks": [ /* song objects */ ],
  "albums": []
}
```

`kind` is `track`, `album`, `playlist` or `artist`. A track or collection fills `tracks`; an artist (YouTube Music only) fills `albums` with release summaries instead, and `subtitle` carries the artist description. `400` for a URL that isn't a supported link, `404` when the link resolves to nothing (e.g. a handle that isn't an artist), `502` when the upstream lookup fails.

---

## Downloads

### `POST /api/download/url`

Download a single track. Blocks until complete.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | yes | Spotify track URL or YouTube URL |
| `client_id` | string | no | WebSocket client ID for progress events |

**Request body (optional):** the song object as returned by search/resolve. Its `track_number`/`album_track_total` survive the re-fetch by URL, `youtube_id` forces the audio source, and `downtify_playlist_url` (a Spotify playlist URL) registers the track as part of that playlist's download.

**Response:** Filename string of the downloaded file — a `slskd/…` path for a slskd download left in place. `404` when no audio source has a match for the track.

---

### `POST /api/download/batch`

Download multiple tracks concurrently, gated by the [`max_parallel_downloads` setting](#post-apisettingsupdate) (default 3, configurable 1–30) and, if set, the `download_delay_seconds` delay between them. Returns immediately; progress is broadcast over WebSocket.

**Request body:**

```json
{
  "songs": [ /* array of song objects */ ],
  "playlist_url": "https://open.spotify.com/playlist/…",
  "generate_m3u": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `songs` | array | Song objects to download |
| `playlist_url` | string | Optional. A Spotify or YouTube Music playlist URL, used to determine the playlist subfolder and M3U name. A Spotify playlist is also tracked as a [playlist download](#playlist-downloads). |
| `generate_m3u` | boolean | Whether to write an M3U after the batch finishes. Default: `true`. |

**Response:**

```json
{
  "job_ids": ["track_id_1", "track_id_2"],
  "count": 2
}
```

---

### `POST /api/download/album`

Download every track of a YouTube Music album/browse URL, resolving the full tracklist once so every track shares consistent metadata (this avoids the album/compilation drift that downloading each track independently via `/api/download/url` can cause).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | yes | YouTube Music album/browse URL |

**Response:** Object mapping `song_id -> downloaded filename` for every track that downloaded successfully (failed tracks are omitted, not raised).

---

### `POST /api/download/csv`

Import a [library-export CSV](../features/library-import.md) (Soundiiz, TuneMyMusic, Exportify). The file is read client-side and sent as plain text, not a multipart upload. Reuses the same batch pipeline as `/api/download/batch` — same parallel-downloads limit, same delay-between-downloads, and an M3U is written under `playlist_name` if `generate_m3u` is true.

**Request body:**

```json
{
  "csv": "Title,Artist\nHeld Together,Slowdive\n",
  "playlist_name": "My Old Library",
  "generate_m3u": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `csv` | string | Required. The raw CSV file content. |
| `playlist_name` | string | Optional. Defaults to `"Imported Library"`. Used for the M3U filename and download subfolder. |
| `generate_m3u` | boolean | Whether to write an M3U after the import finishes. Default: `true`. |

**Response:**

```json
{
  "job_ids": ["csv:0", "csv:1"],
  "count": 2,
  "playlist_name": "My Old Library"
}
```

Returns `400` if the CSV has no recognizable title/artist columns, is empty, or exceeds 2,000 rows.

---

## Queue

### `GET /api/queue`

List all download jobs (queued, in progress, done, error).

**Response:** Array of job objects (`song`, `status`, `progress`, `message`, `filename`, and `provider` — the audio source that served it: `youtube-music`, `youtube` or `slskd`).

---

### `DELETE /api/queue/completed`

Remove finished (`done`) jobs, keeping queued, in-progress and failed ones.

**Response:** `{ "removed": 3 }`

---

### `DELETE /api/queue`

Clear the entire download queue/history.

**Response:** `{ "cleared": true }`

---

### `DELETE /api/queue/item`

Remove a single job from the queue.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `song_id` | string | yes | Job ID |

**Response:** `{ "removed": true }` or `{ "removed": false }`

---

## Settings

### `GET /api/settings`

Return the current settings.

**Response:**

```json
{
  "audio_providers": ["youtube-music"],
  "lyrics_providers": ["lrclib", "netease"],
  "download_lyrics": true,
  "format": "mp3",
  "bitrate": "320",
  "output": "{artists} - {title}.{output-ext}",
  "generate_m3u": true,
  "download_cover_art_playlists": false,
  "max_parallel_downloads": 3,
  "download_delay_seconds": 0,
  "cover_resolution": 600,
  "download_cover_art": true,
  "overwrite_existing_files": true,
  "organize_by_artist": false,
  "organize_by_album": false,
  "search_albums": true,
  "mini_player_enabled": true,
  "cache_cover_art": false,
  "library_upgrade": {
    "artwork_min_px": 600,
    "artwork_source": "highest",
    "recheck_days": 30
  },
  "sync_navidrome": true,
  "slskd": {
    "enabled": false,
    "base_url": "",
    "api_key": "",
    "source_dir": "/slskd",
    "leave_in_place": true,
    "download_timeout_seconds": 600,
    "queued_timeout_seconds": 180,
    "…": "…"
  },
  "navidrome": {
    "enabled": false,
    "url": "",
    "username": "",
    "password": "",
    "admin_username": "",
    "admin_password": "",
    "public_playlist": false,
    "…": "…"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `max_parallel_downloads` | integer | Concurrent download limit. Clamped to `1–30`. |
| `download_delay_seconds` | number | Seconds to wait after each download in a batch before starting the next. Clamped to `0–300`. |
| `mini_player_enabled` | boolean | Legacy UI preference, kept so older clients keep working. The web UI no longer reads it — the player bar always appears while a track is loaded. The backend never reads it either. |
| `download_cover_art` | boolean | Whether to fetch and embed cover art at all. See [Download cover art](features/download-settings.md#download-cover-art). |
| `cover_resolution` | integer | Target pixel size (width & height) for YouTube Music-sourced cover art. Clamped to `300–1200`. Only used when `download_cover_art` is true. See [Cover art resolution](features/download-settings.md#cover-art-resolution). |
| `overwrite_existing_files` | boolean | When `false`, a song already in the library (matched by output filename, or by Spotify track ID through the [library track index](features/library-catalog.md)) isn't downloaded again; the download returns the existing file's path instead. See [Overwrite existing files](features/download-settings.md#overwrite-existing-files). |
| `download_cover_art_playlists` | boolean | Save the playlist's own cover art alongside its M3U file, as `<playlist-name>.jpg`. Only applies while `generate_m3u` is true. Default: `false`. See [Playlist cover art](features/playlist-cover-art.md). |
| `lyrics_providers` | array | Ordered fallback list of lyrics providers: `lrclib`, `netease`. Each track tries them in order until one has lyrics. Unknown names are dropped; a list left with only the legacy `genius`/`musixmatch`/`azlyrics` names falls back to the defaults. An empty list means no lyrics, as does `download_lyrics: false`. See [Lyrics](features/lyrics.md). |
| `download_lyrics` | boolean | Whether to look lyrics up at all. |
| `audio_providers` | array | Ordered fallback list of audio sources: `youtube-music`, `youtube`, `slskd`. `slskd` is dropped while `slskd.enabled` is false. See [slskd & Navidrome](features/slskd-navidrome.md#audio-sources-and-fallback-order). |
| `slskd` | object | slskd connection and matching options. Saving with `enabled: true` but no `base_url` or `api_key` returns `400`. |
| `navidrome` | object | Navidrome connection. Saving with `enabled: true` but no `url`, `username` or `password` returns `400`. |
| `sync_navidrome` | boolean | Create/update a Navidrome playlist after playlist downloads, Playlist Monitor sweeps and library changes. |
| `cache_cover_art` | boolean | Keep extracted cover images under `/data/cover_cache`. |
| `library_upgrade` | object | Defaults a library upgrade scan starts from: `artwork_min_px` (clamped to `100–3000`), `artwork_source` (`highest`, `spotify`, `itunes`, `youtube-music`) and `recheck_days` (`0–3650`, `0` meaning always re-check). A scan request may override them. See [Upgrade library](features/library-upgrade.md#options). |

---

### `POST /api/settings/update`

Update one or more settings. Takes effect immediately and is persisted to disk.

**Request body:** Partial settings object with any subset of the fields above.

**Response:** Full settings object after the update.

---

## YouTube cookies

Backs the **Settings → YouTube cookies** screen. The uploaded file lives in the data directory (`/data/cookies.txt`) so it survives container updates. See [YouTube Cookies](features/youtube-cookies.md).

The cookie file's contents are never returned by the API — only whether one is configured, how large it is and when it changed.

### `GET /api/cookies`

Current cookie configuration.

**Response:**

```json
{
  "configured": true,
  "source": "upload",
  "locked": false,
  "path": "/data/cookies.txt",
  "size": 2048,
  "updated_at": "2026-09-12T02:22:02.282849+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `configured` | boolean | Whether a usable cookie file is in place. |
| `source` | string \| null | `"upload"`, `"env"` (`DOWNTIFY_COOKIES_FILE`), or `null` when unconfigured. |
| `locked` | boolean | `true` when `DOWNTIFY_COOKIES_FILE` is set — uploads and deletions are then refused. |
| `size` / `updated_at` | integer \| null | Only reported for an uploaded file. |

---

### `POST /api/cookies`

Upload a Netscape `cookies.txt`, replacing any previous one. The body is the **raw file**, not multipart form-data.

**Response:** the `GET /api/cookies` object plus a `warnings` array (e.g. when the file has no `youtube.com` cookies).

| Status | Meaning |
|--------|---------|
| `400` | Not a valid Netscape cookie jar (empty, binary, or no cookie lines). |
| `409` | `DOWNTIFY_COOKIES_FILE` is set, so the file is managed outside the UI. |
| `413` | Larger than 2 MB, so it isn't a cookies.txt. |

---

### `DELETE /api/cookies`

Remove the uploaded cookie file.

**Response:** the `GET /api/cookies` object plus `"deleted"` (`false` when there was nothing to delete). Returns `409` while `DOWNTIFY_COOKIES_FILE` is set.

---

## File management

### `GET /list`

List all audio files in the downloads directory (recursive), plus slskd downloads left in place (`slskd/…`).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `refresh` | boolean | no | Rescan instead of using the briefly cached listing |

**Response:** Sorted array of relative paths (e.g. `["My Playlist/Song.mp3", "Artist - Track.mp3", "slskd/user/Album/Track.flac"]`).

---

### `GET /playlists`

List downloaded playlists, derived from the `.m3u` files already on disk (see [M3U Export](features/m3u-export.md)). Used by the [Library page](features/library-catalog.md#library-page) to list playlists, and to play or queue just one of them.

**Response:**

```json
[
  { "name": "My Playlist", "files": ["My Playlist/Artist - Song.mp3"], "count": 1 }
]
```

Sorted by name. A single track or an album downloaded without an M3U doesn't appear here.

---

### `GET /tracks`

List downloaded tracks with artist/album read from each file's embedded tags. Used by the [Library page](features/library-catalog.md#library-page) to build its album, artist and track views, and by the [Built-in Player](features/player.md#how-it-works).

**Response:**

```json
[
  {
    "file": "Artist - Song.mp3",
    "title": "Song",
    "artist": "Artist",
    "album": "Some Album",
    "album_artist": "Artist",
    "track_number": 3,
    "year": "2024",
    "duration": 213.08,
    "has_cover": true,
    "added": 1789600669,
    "size": 8567376,
    "playlists": ["My Playlist"]
  }
]
```

`album_artist`, `track_number` (`0` when untagged), `year` and `duration` (seconds) come from the file's tags and stream info; `added` is the file's modification time (Unix seconds) and `size` its size in bytes. `playlists` lists the downloaded Spotify playlists the track belongs to, and is omitted when there are none. Tags are cached in `/data` per file and re-read only when the file's modification time or size changes.

Sorted by `file`, same order as `/list`. `artist`/`album` come back as `""` when the file has no readable tag for that field — the frontend then simply doesn't offer it as a filter for that track.

---

### `DELETE /delete`

Delete a downloaded file, plus its leftovers — best-effort, so a missing or unremovable one doesn't fail the request:

- its `.lrc` lyrics sidecar, if any (same basename, see [Lyrics](features/lyrics.md));
- the folder's shared `cover.jpg` under [*Organize by album*](features/download-settings.md#download-cover-art), but only once no other track in that same folder still needs it;
- the file's folder, and any of its ancestors, that end up empty as a result — climbing up but never past the downloads directory root.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | yes | Relative path to the file (as returned by `/list`) |

**Response:** `{ "deleted": true, "playlists_affected": [], "playlists_refresh_scheduled": false }` or `{ "deleted": false, "error": "…", … }`

`playlists_affected` lists the downloaded playlists that contained the file; their M3U files and Navidrome playlists are rewritten in the background (`playlists_refresh_scheduled`).

---

### `DELETE /delete/batch`

Delete several files in one request — same cleanup as `DELETE /delete` (sidecars, orphaned cover, empty-folder pruning) applied to each one independently, so one bad path or an already-deleted file doesn't stop the rest. Powers the Library page's multi-select.

**Request body:**

```json
{ "files": ["My Playlist/Song.mp3", "Some Album/Track 2.mp3"] }
```

Duplicate paths are deduplicated before processing. Capped at 2000 files per request (`413` if exceeded).

**Response:**

```json
{
  "deleted_count": 2,
  "failed_count": 0,
  "results": {
    "My Playlist/Song.mp3": { "deleted": true },
    "Some Album/Track 2.mp3": { "deleted": true }
  }
}
```

`results` maps each requested path to the same shape `DELETE /delete` returns for it. The response also carries `playlists_affected` and `playlists_refresh_scheduled`, as for `DELETE /delete`.

---

### `GET /media/{path}`

Serve a library file by its library path. Unlike the `/downloads` static mount, this also serves slskd downloads left in place (`slskd/…`).

**Response:** The audio file. `404` if the path isn't in the library.

---

### `GET /cover`

Return the embedded cover art for a file.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | yes | Relative path to the file |

**Response:** Image bytes (`image/jpeg` or `image/png`). Returns `404` if no embedded cover is found.

---

### `GET /lyrics`

Return the lyrics saved for a library file — used by the player's lyrics panel.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | yes | Relative path to the file (as returned by `/list`) |

**Response:**

```json
{ "synced": "[00:00.00] First line\n[00:05.00] Second line", "plain": "First line\nSecond line" }
```

`synced` is the content of the `.lrc` sidecar next to the file, `plain` the lyrics embedded in its tags (ID3 `USLT`, MP4 `©lyr`, Vorbis `LYRICS`); either is `""` when missing. `404` if the file isn't in the library. See [Lyrics](features/lyrics.md).

---

## Library

### `POST /api/library/archive`

Prepare a ZIP of several library tracks for download. Powers the Library page's **Download selected**, so a multi-track selection reaches the user's machine in one file instead of one click per track.

**Request body:**

```json
{ "files": ["My Playlist/Song.mp3", "slskd/user/Album/Track.flac"] }
```

Duplicate paths are deduplicated and paths that aren't in the library are dropped. Capped at 2000 files (`413` if exceeded); `400` for an empty list and `404` when none of the paths exist.

**Response:** `{ "token": "…", "count": 2, "filename": "downtify-library-20260915-215442.zip" }`

The browser then navigates to the URL below — a `fetch` would hold the whole archive in memory.

---

### `GET /api/library/archive/{token}`

Stream a prepared selection as one ZIP. Entries keep their library paths, so per-playlist and artist/album folders survive extraction, and they're stored rather than deflated (audio doesn't compress). The archive is built while it's sent, so there's no `Content-Length` and no temp file on the server.

Tickets are single-use and expire after 5 minutes: `404` for an unknown, expired or already-downloaded token. A file deleted between preparing and downloading is skipped instead of failing the archive.

**Response:** `application/zip` (chunked), as an attachment.

---

### `DELETE /api/library/playlist`

Delete a downloaded playlist: every track registered to it (including tracks other playlists also contain), its playlist-folder leftovers, its M3U file(s) and its catalog entry.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `playlist_name` | string | yes | Playlist name |

**Response:**

```json
{
  "ok": true,
  "playlist": "My Playlist",
  "files": ["My Playlist/Artist - Song.mp3"],
  "deleted_count": 1,
  "failed_count": 0,
  "failed": [],
  "playlists_affected": ["My Playlist"],
  "playlists_refresh_scheduled": true
}
```

---

### `POST /api/library/reconcile`

Fix library paths after files were moved or deleted outside Downtify, then rewrite the affected M3U files / Navidrome playlists when those are enabled. See [Fix library paths](features/library-catalog.md#fix-library-paths).

**Response:**

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

---

### `GET /api/library/upgrade`

The state of the library upgrade: the current (or last) run, its queue counts and what the scan found. See [Upgrade library](features/library-upgrade.md).

**Response:**

```json
{
  "state": "ready",
  "run": {
    "id": 3,
    "state": "ready",
    "categories": ["artwork", "lyrics", "metadata"],
    "options": {
      "artwork_min_px": 600,
      "artwork_source": "highest",
      "recheck_days": 30
    },
    "total_tracks": 18742,
    "total_bytes": 122406000000,
    "created_at": "…",
    "finished_at": ""
  },
  "counts": {
    "total": 16921,
    "queued": 16921,
    "running": 0,
    "completed": 0,
    "skipped": 0,
    "failed": 0,
    "finished": 0,
    "processed_bytes": 0
  },
  "summary": {
    "categories": { "artwork": 16921, "lyrics": 2104, "metadata": 5382 },
    "category_bytes": { "artwork": 110300000000, "lyrics": 13700000000, "metadata": 35100000000 },
    "tracks": 16921,
    "library_tracks": 18742,
    "library_bytes": 122406000000
  },
  "scan": { "scanned": 18742, "total": 18742 },
  "categories": ["artwork", "lyrics", "metadata"],
  "artwork_sources": ["highest", "spotify", "itunes", "youtube-music"]
}
```

`state` is one of `idle`, `scanning`, `ready`, `running`, `paused`, `done` or `cancelled`.

---

### `GET /api/library/upgrade/jobs`

The tracks in the current run, most recently touched first.

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Only `queued`, `running`, `done`, `skipped` or `failed` |
| `limit` | int | 1–1000, default 100 |

**Response:**

```json
[
  {
    "file": "Queen - Bohemian Rhapsody.mp3",
    "status": "done",
    "stage": "",
    "categories": ["artwork"],
    "size": 84664,
    "title": "Bohemian Rhapsody",
    "artist": "Queen",
    "detail": "artwork 1200px (itunes)",
    "changed": ["artwork"],
    "updated_at": "…"
  }
]
```

While a track is running, `stage` is `matching`, `artwork`, `lyrics` or `writing`.

---

### `POST /api/library/upgrade/scan`

Look at every library track and queue the ones that are behind. Writes nothing to the files — the queue is confirmed with `/start`.

**Body** (all optional; defaults come from the `library_upgrade` settings):

```json
{
  "artwork_min_px": 600,
  "artwork_source": "highest",
  "recheck_days": 30
}
```

Returns the same shape as `GET /api/library/upgrade`. `409` when a scan or run is already going.

---

### `POST /api/library/upgrade/start`

Start upgrading the scanned tracks.

**Body:**

```json
{ "categories": ["artwork", "lyrics"] }
```

Unknown names are dropped; an empty or missing list means every category. `409` when nothing has been scanned, or a run is already going.

---

### `POST /api/library/upgrade/pause`

Stop after the track being worked on. The queue is kept, and `POST /api/library/upgrade/resume` continues it with the same categories.

---

### `POST /api/library/upgrade/cancel`

Drop the rest of the queue. Tracks already upgraded stay upgraded.

---

## Playlist downloads

Spotify playlists downloaded through `POST /api/download/batch`, checked against Spotify for missing tracks. See [Playlist downloads](features/slskd-navidrome.md#playlist-downloads).

A playlist report looks like:

```json
{
  "batch_id": 4,
  "spotify_playlist_id": "37i9dQZF1DXcBWIGoYBM5M",
  "playlist_name": "Today's Top Hits",
  "playlist_url": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
  "expected_count": 50,
  "downloaded_count": 48,
  "missing_count": 2,
  "missing_tracks": [ /* song objects, when requested */ ],
  "active_in_queue": 0,
  "status": "incomplete",
  "source": "spotify",
  "started_at": "…",
  "finished_at": "…"
}
```

### `GET /api/playlists/batches`

Every tracked playlist download, as summary reports.

**Response:** `{ "playlists": [ /* reports */ ], "count": 1 }`

---

### `GET /api/playlists/batches/{spotify_playlist_id}`

One playlist's report, checked against its cached Spotify track list.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tracks` | boolean | no | Include `missing_tracks`. Default: `true` |
| `refresh` | boolean | no | Refetch the track list from Spotify instead of the cache |

**Response:** A playlist report. `404` if the playlist isn't tracked.

---

### `DELETE /api/playlists/batches/{spotify_playlist_id}`

Delete the playlist like `DELETE /api/library/playlist`, and also stop tracking it (playlist download records, cached Spotify track list, and its Playlist Monitor entry, if any).

**Response:** Same as `DELETE /api/library/playlist`, plus `spotify_playlist_id`.

---

### `GET /api/playlists/incomplete`

Tracked playlist downloads that are still missing tracks.

**Response:** `{ "playlists": [ /* reports */ ], "count": 1 }`

---

### `POST /api/playlists/incomplete/download-missing`

Queue only the tracks of a Spotify playlist that aren't in the library yet.

**Request body:** `{ "spotify_playlist_id": "…" }` or `{ "playlist_url": "https://open.spotify.com/playlist/…" }`, optionally with `"generate_m3u": true`.

**Response:** Same as `POST /api/download/batch`, plus `missing_count` and `playlist_name`. When nothing is missing: `{ "count": 0, "message": "Playlist already complete", "catalog_linked": 12, "playlist_refresh": true }`.

---

## Playlist M3U

### `POST /api/playlist/m3u`

Write an M3U file for a playlist after per-track downloads are complete. `playlist_url` can be a Spotify or a YouTube Music playlist.

**Request body:**

```json
{
  "playlist_url": "https://open.spotify.com/playlist/…",
  "tracks": [
    {
      "filename": "My Playlist/Artist - Title.mp3",
      "title": "Title",
      "artist": "Artist",
      "duration": 210
    }
  ]
}
```

**Response:** `{ "path": "/downloads/…/playlist.m3u", "count": 12 }`

---

## Playlist Monitor

### `GET /api/monitor/playlists`

List all watches (playlists and artists).

**Response:** Array of watch objects. Each has a `kind` of `"playlist"` or `"artist"`, and a `source` of `"spotify"` or `"youtube_music"` (the service the watch was added from, read from its `url`). `spotify_id` is the watch's unique key: the Spotify or YouTube Music playlist id, or for an artist watch the YouTube Music channel id. For an artist watch, `last_track_count` is the number of releases.

---

### `POST /api/monitor/playlists`

Add a watch. Triggers an immediate initial download.

**Request body:**

```json
{
  "url": "https://open.spotify.com/playlist/…",
  "interval_minutes": 60
}
```

| `url` | Creates |
|-------|---------|
| Spotify playlist URL | A playlist watch |
| YouTube Music playlist URL (`…/playlist?list=…`) | A playlist watch |
| Spotify artist URL | An artist watch (resolved to the matching YouTube Music artist — see [Artist Watch](features/playlist-monitor.md#artist-watch)) |
| YouTube Music artist URL (`…/channel/UC…` or `…/@handle`) | An artist watch |

**Response:** Watch object. `400` if the URL is none of the above, `409` if it is already watched (an artist added by handle and by channel URL is the same watch), `404` if no matching YouTube Music artist exists.

---

### `PATCH /api/monitor/playlists/{playlist_id}`

Update a watch.

**Request body:** Partial object with any of:

| Field | Type | Description |
|-------|------|-------------|
| `interval_minutes` | integer | Check interval |
| `enabled` | boolean | Pause (`false`) or resume (`true`) |
| `url` | string | A new link for the watch — same kinds as in `POST` |

A `url` that points at the **same** playlist or artist only replaces the stored `url`. One that points at a **different** playlist or artist of the same kind retargets the watch: `spotify_id`, `name` and `url` change, `last_checked` becomes `null`, `last_track_count` becomes `0`, and its downloaded-track and seen-release history is cleared. If the watch is enabled, a first check starts in the background, as after `POST`. An unchanged `url` is ignored.

**Response:** Updated watch object. `404` if there is no such watch; for a new `url`: `400` if it isn't a supported link or is the other kind (an artist link for a playlist watch, or the reverse), `409` if another watch already follows it, `404`/`502` if it can't be resolved. On an error nothing is changed.

---

### `DELETE /api/monitor/playlists/{playlist_id}`

Stop monitoring a playlist.

**Response:** `{ "deleted": true }` or `{ "deleted": false }`

---

### `POST /api/monitor/playlists/{playlist_id}/check`

Trigger an immediate check for a specific playlist outside the normal schedule.

**Response:** `{ "downloaded": 3 }`

---

## WebSocket

### `WS /api/ws`

Real-time download progress events.

| Query parameter | Required | Description |
|----------------|----------|-------------|
| `client_id` | yes | Unique client identifier (UUID recommended) |

**Events received from the server:**

```json
{
  "song": { /* song metadata object */ },
  "progress": 42.5,
  "message": "Downloading…",
  "status": "downloading",
  "filename": null,
  "provider": "youtube-music"
}
```

`status` is one of: `queued` · `downloading` · `done` · `error`.

`filename` is set (non-null) on the final `done` event.

A [library upgrade](features/library-upgrade.md) broadcasts its progress on the same socket, tagged so download clients can ignore it:

```json
{
  "type": "library_upgrade",
  "upgrade": { /* same shape as GET /api/library/upgrade */ }
}
```

These are sent at most once a second while a scan or run is working, and once more when it finishes.
