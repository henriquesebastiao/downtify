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

## Search & resolve

### `GET /api/songs/search`

Search YouTube Music by free text.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | yes | Search query |

**Response:** Array of song objects (up to 20 results).

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

## Downloads

### `POST /api/download/url`

Download a single track. Blocks until complete.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | yes | Spotify track URL or YouTube URL |
| `client_id` | string | no | WebSocket client ID for progress events |

**Response:** Filename string of the downloaded file.

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
| `playlist_url` | string | Optional. A Spotify or YouTube Music playlist URL, used to determine the playlist subfolder and M3U name. |
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

**Response:** Array of job objects.

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
  "lyrics_providers": ["lrclib"],
  "download_lyrics": true,
  "format": "mp3",
  "bitrate": "320",
  "output": "{artists} - {title}.{output-ext}",
  "generate_m3u": true,
  "max_parallel_downloads": 3,
  "download_delay_seconds": 0,
  "cover_resolution": 600,
  "download_cover_art": true,
  "overwrite_existing_files": true,
  "organize_by_artist": false,
  "organize_by_album": false,
  "search_albums": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `max_parallel_downloads` | integer | Concurrent download limit. Clamped to `1–30`. |
| `download_delay_seconds` | number | Seconds to wait after each download in a batch before starting the next. Clamped to `0–300`. |
| `download_cover_art` | boolean | Whether to fetch and embed cover art at all. See [Download cover art](features/download-settings.md#download-cover-art). |
| `cover_resolution` | integer | Target pixel size (width & height) for YouTube Music-sourced cover art. Clamped to `300–1200`. Only used when `download_cover_art` is true. See [Cover art resolution](features/download-settings.md#cover-art-resolution). |
| `overwrite_existing_files` | boolean | When `false`, a song already anywhere in the download folder (matched by output filename) isn't downloaded again; the download returns the existing file's path instead. See [Overwrite existing files](features/download-settings.md#overwrite-existing-files). |

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

List all audio files in the downloads directory (recursive).

**Response:** Sorted array of relative paths (e.g. `["My Playlist/Song.mp3", "Artist - Track.mp3"]`).

---

### `GET /playlists`

List downloaded playlists, derived from the `.m3u` files already on disk (see [M3U Export](features/m3u-export.md)). Used by the [Built-in Player](features/player.md#playing-a-single-playlist-artist-or-album) and the Library page to offer "just this playlist" instead of the whole library.

**Response:**

```json
[
  { "name": "My Playlist", "files": ["My Playlist/Artist - Song.mp3"], "count": 1 }
]
```

Sorted by name. A single track or an album downloaded without an M3U doesn't appear here.

---

### `GET /tracks`

List downloaded tracks with artist/album read from each file's embedded tags. Used by the [Built-in Player](features/player.md#playing-a-single-playlist-artist-or-album) and the Library page to offer "just this artist" / "just this album" filtering.

**Response:**

```json
[
  { "file": "Artist - Song.mp3", "artist": "Artist", "album": "Some Album" }
]
```

Sorted by `file`, same order as `/list`. `artist`/`album` come back as `""` when the file has no readable tag for that field — the frontend then simply doesn't offer it as a filter for that track.

---

### `DELETE /delete`

Delete a downloaded file.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | yes | Relative path to the file (as returned by `/list`) |

**Response:** `{ "deleted": true }` or `{ "deleted": false, "error": "…" }`

---

### `GET /cover`

Return the embedded cover art for a file.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | yes | Relative path to the file |

**Response:** Image bytes (`image/jpeg` or `image/png`). Returns `404` if no embedded cover is found.

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

Update a monitored playlist (interval, enabled state).

**Request body:** Partial object with `interval_minutes` and/or `enabled`.

**Response:** Updated playlist monitor object.

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
  "filename": null
}
```

`status` is one of: `queued` · `downloading` · `done` · `error`.

`filename` is set (non-null) on the final `done` event.
