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

Resolve a pasted link to a single object describing what it points at — used by the web UI's link page. Accepts the same URLs as [`GET /api/song/url`](#get-apisongurl), plus Spotify artist URLs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | yes | Spotify track, album, playlist or artist URL, or a YouTube / YouTube Music video, album, playlist or artist URL |

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

`kind` is `track`, `album`, `playlist` or `artist`. A track or collection fills `tracks`; an artist fills `albums` with release summaries instead, and, for YouTube Music, `subtitle` carries the artist description (it is empty for Spotify). A Spotify artist's releases come from the Spotify web player's discography query; if that stops resolving, a shorter list (every album, the latest singles) is returned instead, and `albums` is empty when both fail. An artist's songs come from [`GET /api/artists/top_songs/url`](#get-apiartiststop_songsurl). `400` for a URL that isn't a supported link, `404` when the link resolves to nothing (e.g. a handle that isn't an artist), `502` when the upstream lookup fails.

---

### `GET /api/artists/top_songs/url`

An artist's most popular songs, for the web UI's [Top Songs](features/top-songs.md) page.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | yes | Spotify artist URL (`open.spotify.com/artist/…`) or YouTube Music artist URL (`/channel/UC…` or `/@handle`) |

**Response:**

```json
{
  "source": "spotify",
  "artist_id": "0p4nmQO2msCgU4IF37Wi3j",
  "name": "Avril Lavigne",
  "cover_url": "https://…",
  "songs": [ /* song objects, most popular first */ ]
}
```

`source` is `spotify` or `youtube`. Songs also carry `play_count`, an integer, when the source reports one (left out otherwise). Spotify's is the exact total. YouTube Music only reports a rounded figure (`4.4M plays`), so its `play_count` is an approximation (`4400000`) and the song also has `play_count_approx: true`. Spotify returns the artist's own *Popular* shelf (up to 10 songs); YouTube Music returns the head of the artist's *Top songs* playlist (up to 50). `400` for a URL that isn't an artist link, `404` when a YouTube Music handle doesn't resolve to an artist, `502` when the upstream lookup fails.

---

### `GET /api/artists/top_songs/spotify`

The first five Spotify top songs of an artist in your Library, for the [Top songs tab](features/top-songs.md#on-an-artists-library-page) of their page. They're read from `<downloads>/Metadata/ArtistTopSongs/<Artist>.json` while that file is fresh (7 days); with no file yet they're fetched from Spotify and saved (a few seconds), and a file older than that is returned right away with `"stale": true` while a refresh runs in the background (ask again a few seconds later for the fresh one, as the web UI does). The Spotify artist comes from the artist's profile (`platforms_id.spotify`).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Artist name, exactly as shown in the Library |

**Response:** the same shape as [`GET /api/artists/top_songs/url`](#get-apiartiststop_songsurl) for Spotify, plus when the songs were fetched:

```json
{
  "source": "spotify",
  "artist_id": "6XyY86QOPPrYVGvF9ch6wz",
  "name": "Linkin Park",
  "cover_url": "https://…",
  "fetched_at": "2026-09-24T10:12:03+00:00",
  "stale": false,
  "songs": [ /* five song objects, most popular first */ ]
}
```

| Status | When |
|--------|------|
| `400` | `name` is blank. |
| `404` | The artist has no Spotify id saved yet. |
| `502` | Nothing saved and Spotify couldn't be read. |

---

## Artist photo, banner & bio

Manual picker for an artist's profile photo and banner, plus their profile data (bio, social links, related artists) — see [Artist photo, banner & bio](features/artist-images.md). Images are saved as sidecar files under `<downloads>/Metadata/ArtistImage/` and `<downloads>/Metadata/ArtistBannerImage/`, served directly from the existing `/downloads` static mount; profile data lives in `<downloads>/Metadata/ArtistData/`.

### `GET /api/artists/art`

Whether an artist has a saved photo and/or banner.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Artist name, exactly as shown in the Library |

**Response:**

```json
{ "photo_url": "/downloads/Metadata/ArtistImage/Avril Lavigne.jpg", "banner_url": null }
```

Either field is `null` when that image hasn't been saved yet.

---

### `GET /api/artists/art/search`

Free-text artist photo candidates from YouTube Music and Deezer.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Search query (usually the artist's name) |

**Response:** array of `{ "source": "youtube" | "deezer", "name": "…", "image_url": "…" }`, largest image each source offers.

---

### `GET /api/artists/art/spotify_candidate`

A Spotify photo or banner candidate. The artist is resolved from one already-downloaded track when that track came from Spotify (the most reliable route), otherwise from an exact-name search on Spotify - see [Artist photo, banner & bio](features/artist-images.md#spotify).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | no | Library-relative path of one of the artist's tracks (as returned by `GET /tracks`) |
| `name` | string | no | Artist name, used for an exact-name Spotify search when `file` is missing or wasn't downloaded from Spotify |
| `kind` | string | no | `"photo"` (default) or `"banner"` - these are different Spotify images, not the same one reused |

**Response:** `{ "source": "spotify", "name": "…", "image_url": "…" }`, or `{}` when neither `file` nor `name` resolves a Spotify artist, or (for `kind=banner`) the artist has no banner set.

---

### `POST /api/artists/art/from_url`

Fetch an image and save it as an artist's photo or banner — used both for a picked search result and a pasted image link.

**Request body:**

```json
{ "name": "Avril Lavigne", "kind": "photo", "image_url": "https://…" }
```

`kind` is `"photo"` or `"banner"`.

**Response:** `{ "url": "/downloads/Metadata/ArtistImage/Avril Lavigne.jpg" }`. `400` when `name`/`kind` are missing or invalid, or the URL doesn't resolve to a real image.

---

### `POST /api/artists/art/upload`

Save an uploaded photo or banner. The body is the **raw image file**, not multipart form-data — same idea as `POST /api/cookies`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Artist name |
| `kind` | string | yes | `"photo"` or `"banner"` |

**Response:** `{ "url": "…" }`.

| Status | Meaning |
|--------|---------|
| `400` | `kind` isn't `photo`/`banner`, or the body isn't a real image. |
| `413` | Larger than 15 MB. |

---

### `DELETE /api/artists/art`

Remove a saved photo or banner.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Artist name |
| `kind` | string | yes | `"photo"` or `"banner"` |

**Response:** `{ "removed": true }` when a file was deleted, `{ "removed": false }` when there was nothing to remove. `400` when `kind` isn't `photo`/`banner`.

---

### `GET /api/artists/photo-proxy`

A **display-only** photo for an artist that isn't in your library, used for the tiles in the artist page's *Related* tab. It is a relay, not a way to get a photo to keep: the image is fetched from Deezer, sent to your browser and forgotten - nothing is written to your downloads folder, and only the artist-name → Deezer image link is remembered (in memory, for three hours). To actually save a photo for an artist use the picker (`POST /api/artists/art/from_url`).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Artist name - matched against Deezer's results exactly (ignoring case and the characters a file name can't hold, so `ACDC` finds `AC/DC`), so a near-match never shows someone else's face. When several Deezer artists share the name, the one with the most fans is used |

**Response:** the image bytes with `Cache-Control: public, max-age=10800` and an `ETag`, so the browser holds on to it for three hours. If a photo is already saved for that artist, that local file is sent instead, without browser caching (`Cache-Control: no-cache`), so a newly picked photo shows up right away. `404` (also cacheable for three hours) when Deezer has no exact match, or when the matched artist has no photo on Deezer (it only has a generic placeholder picture, which is never returned).

---

### `GET /api/artists/profile`

An artist's saved profile: bio, origin, formation year, genre, group flag, banner hero colour, social links, related artists, platform ids, and which source (`spotify`/`youtube`/`deezer`/`link`/`upload`) their current photo/banner came from — see [Artist photo, banner & bio](features/artist-images.md#fetching-a-bio-automatically).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Artist name, exactly as shown in the Library |

**Response:**

```json
{
  "name": "Avril Lavigne",
  "bio": "",
  "origin": "",
  "born_or_formed": "",
  "genre": "",
  "is_group": null,
  "banner_bg_color": "",
  "platforms_id": {
    "spotify": "",
    "youtubemusic": "",
    "deezer": "",
    "applemusic": ""
  },
  "social": {
    "twitter": "",
    "facebook": "",
    "website": "",
    "instagram": "",
    "youtube": ""
  },
  "related_artists": [],
  "current_cover": "",
  "current_cover_banner": ""
}
```

A blank skeleton (as above) when nothing has been saved for this artist yet - never `404`. `origin`/`born_or_formed`/`genre`/`is_group`/`banner_bg_color` only ever come from Apple Music. `genre` is one localized name (e.g. `Hard rock` / `Alternativo` in `pt-BR`, `Alternative` in `en`) and follows the `lang` of the last fetch; the others aren't translated, so they stay the same across a re-fetch in a different `lang`. `bio` is plain text - blank lines between paragraphs, single line breaks kept, no HTML and no bullet characters (each item of Apple Music's `•` list becomes its own paragraph, Deezer's HTML is flattened). Never seeds a profile that doesn't exist yet - see `POST .../ensure` below for that.

---

### `POST /api/artists/profile/ensure`

Seeds a brand-new artist's profile automatically the first time it's needed (e.g. opening their Library page) - a no-op past the very first call for a given artist, so it's safe to call on every visit. Saves a photo and/or banner from Spotify (resolved from one of `track_files` already downloaded from there, else by an exact-name search on Spotify), falling back to an exact YouTube Music name match when Spotify has nothing - but only the ones enabled by the `download_cover_art_artist` (photo) and `download_cover_art_artist_banner` (banner) [settings](#post-apisettingsupdate); with both off (the default) no image is saved. Then fetches bio/origin/social/platform-ids the same way `POST .../bio` does - the profile JSON is always written, whatever those settings say.

**Request body:**

```json
{ "name": "Avril Lavigne", "lang": "pt-BR", "track_files": ["Avril Lavigne/Let Go/Complicated.mp3"] }
```

`track_files` is optional (an empty/omitted list just skips the Spotify/YouTube Music image seeding, everything else still runs).

**Response:** the same shape as `GET /api/artists/profile`. Never raises for an artist nothing could be found for - it still saves a (mostly empty) profile file so later calls take the fast, no-op path instead of repeating the lookup on every visit.

---

### `POST /api/artists/profile/bio/preview`

One service's biography text, **without saving anything** - what the artist edit modal's *Fetch from Apple Music* / *Fetch from Deezer* links use to fill the text box, so the user decides whether to keep it (with `PUT /api/artists/profile/bio`). Unlike `POST /api/artists/profile/bio`, it doesn't touch the profile at all: no bio, no other field, and an artist id it had to look up isn't cached.

**Request body:**

```json
{ "name": "Avril Lavigne", "lang": "pt-BR", "source": "deezer" }
```

`source` is required: `"applemusic"` or `"deezer"`, with no fallback to the other one. `lang` works as in `POST /api/artists/profile/bio`.

**Response:** `{ "bio": "…" }` - the same plain text a saved bio has (blank lines between paragraphs, no HTML, no bullets). `400` with a `detail` when that service has no biography for the artist, the name is blank, or `source` is anything else.

---

### `POST /api/artists/profile/bio`

Fetch an artist's bio and save it. Apple Music is the primary source (also brings origin, formation year, group flag and the banner hero colour) by exact, case-insensitive name match against the public iTunes Search API - its resolved artist id is cached in the profile and reused on later calls. Deezer is the secondary source, used to fill the bio in only when Apple's is empty for that artist/language, and is the only source for social links and related-artist names, which it always contributes when it has a match.

**Request body:**

```json
{ "name": "Avril Lavigne", "lang": "pt-BR", "source": "deezer" }
```

`source` is optional and chooses whose biography *text* is saved: `"applemusic"` or `"deezer"` use only that service's bio (no fallback to the other one; a `400` `detail` says which service has none, and the saved bio is left as it was), while `"auto"` - the default, and what `POST .../ensure` does - saves Apple Music's bio and falls back to Deezer's only when Apple Music has none. Every other field is fetched the same way whatever `source` is; an unknown value is a `400`.

`lang` affects the bio text itself, not just formatting - but for Apple Music it's not a simple header: each supported language is tied to a specific Apple Music storefront (e.g. `pt-BR` uses the Brazil storefront, `el` uses Greece's), and a language with no working storefront (`bg`) falls back to whatever that artist's default-language bio is.

**Response:** the same shape as `GET /api/artists/profile`, with `bio` updated - plus `origin`/`born_or_formed`/`genre`/`is_group`/`banner_bg_color`/`platforms_id.applemusic` when Apple Music had a match, and `social` (only fields that are still empty - a link already saved, typed by hand or fetched earlier, is never replaced)/`related_artists`/`platforms_id.deezer` when Deezer had one. `400` only when neither source matched this artist at all.

---

### `DELETE /api/artists/profile/bio`

Clear only the saved bio text. Everything else - `origin`, `born_or_formed`, `is_group`, `banner_bg_color`, `social`, `related_artists` and `platforms_id` (including the cached ids) - is left as-is, so fetching again later doesn't need to search by name.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Artist name, exactly as shown in the Library |

**Response:** the same shape as `GET /api/artists/profile`, with `bio` cleared.

---

### `PUT /api/artists/profile/bio`

Manually set the bio text directly - the user's own writing, never fetched from Apple Music/Deezer. `social`, `related_artists` and `platforms_id` are left untouched.

**Request body:**

```json
{ "name": "Avril Lavigne", "bio": "…" }
```

`bio` is plain text: blank lines between paragraphs, single line breaks kept. HTML tags are stripped and each `•` bullet becomes its own paragraph before saving, so what's saved is the same shape `GET /api/artists/profile`'s `bio` always returns.

**Response:** the same shape as `GET /api/artists/profile`, with `bio` set to the given text, formatted.

---

### `PUT /api/artists/profile/social`

Manually set all four social links directly, replacing the whole object - never fetched. A field left out of `social` is saved as an empty string, not left at its previous value.

**Request body:**

```json
{
  "name": "Avril Lavigne",
  "social": {
    "twitter": "https://twitter.com/AvrilLavigne",
    "facebook": "",
    "website": "https://avrillavigne.com",
    "instagram": ""
  }
}
```

**Response:** the same shape as `GET /api/artists/profile`, with `social` replaced.

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
| `playlist_name` | string | Optional. Names the playlist subfolder and M3U when there is no `playlist_url`, e.g. an artist's [top songs](features/top-songs.md). Ignored when `playlist_url` resolves. |
| `cover_url` | string | Optional. Image saved as the playlist's [cover art](features/playlist-cover-art.md) when there is no `playlist_url`. Only used when `generate_m3u` is true, a `playlist_name` is set and the cover art setting is on. |
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
  "download_cover_art_artist": false,
  "download_cover_art_artist_banner": false,
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
| `download_cover_art_artist` | boolean | Let Downtify save an artist's photo on its own - currently only when an artist's page is opened for the first time (see [`POST /api/artists/profile/ensure`](#post-apiartistsprofileensure)). The manual picker on an artist's Library page is always available regardless of this setting. Default: `false`. See [Artist photo, banner & bio](features/artist-images.md). |
| `download_cover_art_artist_banner` | boolean | Same as above, for the artist's banner image - independent of the photo setting. Default: `false`. See [Artist photo, banner & bio](features/artist-images.md). |
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

### `POST /api/slskd/test`

Try a slskd connection without saving anything. See [Testing the connection](features/slskd-navidrome.md#testing-the-connection).

**Request body:** the `slskd` settings object as it stands in the form — at least `base_url` and `api_key`; `source_dir` is the folder Downtify checks it can read. The body wins over the saved settings, so a field that was cleared stays cleared. An empty body tests the saved settings instead.

**Response:** always `200`, whether or not the test passed:

```json
{
  "ok": true,
  "server": "slskd 0.21.4",
  "checks": [
    { "id": "connection", "status": "ok", "code": "", "detail": "" },
    { "id": "auth", "status": "ok", "code": "", "detail": "" },
    { "id": "soulseek", "status": "ok", "code": "ok", "detail": "me" },
    { "id": "folder", "status": "warn", "code": "missing", "detail": "/slskd" }
  ]
}
```

`ok` is `false` when any check has `status: "fail"`; a `warn` (slskd signed out of Soulseek, an unreadable folder) doesn't fail the test. `server` is set only when the address and key were both accepted. Each check is `{id, status, code, detail}`, where `detail` is only ever a short fact — a path, a state, an HTTP status — never text copied from an error.

| `id` | `code` values |
|------|---------------|
| `config` | `missing` — the address or key is empty; nothing was tried |
| `connection` | `unreachable`, `timeout`, `bad_url`, `tls`, `not_slskd`, `http_error` |
| `auth` | `bad_key` |
| `soulseek` | `ok`, `offline` |
| `folder` | `ok`, `missing` |

Each request gives up after 8 seconds.

---

### `POST /api/navidrome/test`

Try a Navidrome connection without saving anything. Same behaviour and answer shape as `POST /api/slskd/test`, with the `navidrome` settings object as the body (`url`, `username`, `password`, and optionally `admin_username` and `admin_password`).

| `id` | `code` values |
|------|---------------|
| `config` | `missing` |
| `connection` | `unreachable`, `timeout`, `bad_url`, `tls`, `not_navidrome`, `http_error` |
| `auth` | `bad_credentials`, `api_error` (`detail` holds the server's own message) |
| `scan` | `ok`, `not_admin`, `not_admin_separate`, `bad_admin` |

The `scan` check reads whether the account used for library scans (the admin login when set, else the normal one) is an admin — Navidrome only lets admins start a scan — and never starts one. It is left out when the account can't be looked up, and when scanning after a download is turned off.

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
  {
    "name": "My Playlist",
    "files": ["My Playlist/Artist - Song.mp3"],
    "count": 1,
    "cover": "My Playlist/My Playlist.jpg",
    "liked": false
  }
]
```

Sorted by name, except that the [liked songs](features/liked-songs.md) playlist (`"liked": true`, named `Downtify Liked Songs`) comes first. A single track or an album downloaded without an M3U doesn't appear here.

`cover` is the library path of the playlist's own artwork when one was saved beside its M3U (see [Playlist cover art](features/playlist-cover-art.md)), and `""` otherwise. Fetch it from [`GET /playlist-cover`](#get-playlist-cover).

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

### `GET /playlist-cover`

Return a playlist's own cover art — the sidecar image saved next to its M3U, not a cover read out of a track's tags. See [Playlist cover art](features/playlist-cover-art.md).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | yes | The `cover` path from [`GET /playlists`](#get-playlists) |

**Response:** Image bytes. Returns `404` when the path isn't an image inside the library, which also refuses an audio file or a path pointing outside it.

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

::: warning The liked songs playlist is never deleted this way
`Downtify Liked Songs` isn't a downloaded playlist, so no song is removed. Asking to delete it clears the likes instead (like [`POST /api/likes/clear`](#post-apilikesclear)) and answers with `deleted_count: 0`.
:::

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
  "refresh_navidrome": false,
  "likes_updated": 0
}
```

`likes_updated` is how many [liked songs](features/liked-songs.md#keeping-likes-in-step-with-the-files) were pointed at a file's new location.

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
    "recently_checked": 1204,
    "library_tracks": 18742,
    "library_bytes": 122406000000
  },
  "scan": { "scanned": 18742, "total": 18742 },
  "categories": ["artwork", "lyrics", "metadata"],
  "artwork_sources": ["highest", "spotify", "itunes", "youtube-music"]
}
```

`state` is one of `idle`, `scanning`, `ready`, `running`, `paused`, `done` or `cancelled`.

`summary.tracks` is what the scan queued; `summary.recently_checked` is how many tracks it skipped without reading them, because every category had been looked at inside the `recheck_days` window.

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

## Likes

The heart on a library track — see [Liked songs](features/liked-songs.md). Files are library paths, the same ones [`GET /tracks`](#get-tracks) uses.

### `GET /api/likes`

The liked files, most recently liked first.

**Response:**

```json
{
  "files": ["Artist - Song.mp3", "My Playlist/Other - Song.flac"],
  "count": 2,
  "playlist": "Downtify Liked Songs"
}
```

`playlist` is the name of the playlist the likes are written to, under `Playlists/` (see [`GET /playlists`](#get-playlists)).

---

### `PUT /api/likes`

Like or unlike one library file. Idempotent: sending the state you want twice changes nothing, so a tap that may not have arrived can be retried.

**Request body:**

```json
{ "file": "Artist - Song.mp3", "liked": true }
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | string | yes | Library path of the song |
| `liked` | boolean | no | `true` (the default) to like, `false` to take the like back |

Liking needs a file that is in the library (`404` otherwise); unliking accepts any path, so the like of a file that has since vanished can still be cleared. `400` when `file` is missing.

**Response:** `{ "file": "Artist - Song.mp3", "liked": true, "count": 2 }`

The playlist file is written with the first like and removed with the last.

---

### `POST /api/likes/clear`

Unlike everything, which also removes the playlist. No song is deleted.

**Response:** `{ "cleared": 2, "count": 0 }`

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

**Response:** Array of watch objects. Each has a `kind` of `"playlist"`, `"artist"` or `"podcast"`, and a `source` of `"spotify"` or `"youtube_music"` (the service the watch was added from, read from its `url`; meaningless for a podcast watch). `spotify_id` is the watch's unique key: the Spotify or YouTube Music playlist id, an artist's YouTube Music channel id, or a podcast's RSS feed URL. For an artist watch, `last_track_count` is the number of releases.

A podcast watch only ever appears here — it's created, updated and deleted through [`POST /api/podcasts/subscribe`](#podcasts) and friends, not through this endpoint's `POST`/`PATCH`/`DELETE`, since a podcast needs a retention policy the generic watch shape has no room for.

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

## Podcasts

Subscribing to a show, its episodes, and per-episode playback position — see [Podcasts](features/podcasts.md). Scheduling (the interval, enabled flag and last-checked time) lives on the same watch object [`GET /api/monitor/playlists`](#get-apimonitorplaylists) returns for playlists and artists (`kind: "podcast"`); everything below is what that generic shape has no room for.

### `POST /api/podcasts/resolve`

Preview a podcast from a pasted link, before subscribing. Accepts a direct RSS feed URL or a Spotify show/episode link.

**Request body:** `{ "url": "https://feeds.example.com/show.xml" }`

**Response:**

```json
{
  "show": {
    "name": "Radiolab",
    "author": "WNYC Studios",
    "description": "…",
    "artwork_url": "https://…",
    "feed_url": "https://feeds.simplecast.com/EmVW7VGp",
    "source_url": "https://feeds.simplecast.com/EmVW7VGp"
  },
  "episodes": [
    {
      "guid": "…",
      "title": "The Sweetest Thing",
      "description": "…",
      "published_at": "2026-09-18T14:00:00+00:00",
      "duration_seconds": 1862,
      "season_number": null,
      "episode_number": 712,
      "enclosure_url": "https://…",
      "enclosure_type": "audio/mpeg"
    }
  ],
  "matched_episode_guid": null,
  "already_subscribed": false
}
```

`matched_episode_guid` is set only when a Spotify **episode** link's title could be matched into the feed. `400` for a link that isn't a podcast feed and isn't a Spotify show/episode link; `404` when Spotify resolves a show name but it has no public RSS feed (a Spotify-exclusive show) — the response `detail` names the show.

---

### `GET /api/podcasts/search`

Free-text podcast search, via the iTunes podcast directory.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | yes | Show name |

**Response:** `{ "results": [ { "name": "…", "author": "…", "feed_url": "…", "artwork_url": "…" } ] }`. A result with an empty `feed_url` has no public feed and can't be subscribed to.

---

### `POST /api/podcasts/subscribe`

Subscribe to a show resolved with `POST /api/podcasts/resolve`. Triggers an immediate initial sync in the background — see [How many episodes are downloaded](features/podcasts.md#how-many-episodes-are-downloaded).

**Request body:**

```json
{
  "feed_url": "https://feeds.simplecast.com/EmVW7VGp",
  "name": "Radiolab",
  "author": "WNYC Studios",
  "description": "…",
  "artwork_url": "https://…",
  "source_url": "https://feeds.simplecast.com/EmVW7VGp",
  "retention": 0,
  "interval_minutes": 720
}
```

Only `feed_url` and `name` are required. `retention` is `0` for "every new episode" or a positive integer for "keep the latest N"; default `0`. `409` if already subscribed to this feed.

**Response:** The show object (see `GET /api/podcasts/shows/{id}`).

---

### `GET /api/podcasts/shows`

List subscribed shows.

**Response:** Array of show objects:

```json
{
  "id": 1,
  "feed_url": "https://feeds.simplecast.com/EmVW7VGp",
  "name": "Radiolab",
  "author": "WNYC Studios",
  "description": "…",
  "artwork_url": "https://…",
  "source_url": "https://feeds.simplecast.com/EmVW7VGp",
  "folder_name": "Radiolab",
  "retention": 3,
  "created_at": "…",
  "watch_id": 1,
  "interval_minutes": 720,
  "enabled": true,
  "last_checked": "…",
  "episode_count": 671,
  "downloaded_count": 3
}
```

`folder_name` is the sanitized, on-disk folder name under `Podcasts/`, fixed at subscribe time. `watch_id`/`interval_minutes`/`enabled`/`last_checked` are `null` if the scheduling watch is somehow missing.

---

### `GET /api/podcasts/shows/{show_id}`

One show. `404` if not subscribed.

---

### `GET /api/podcasts/shows/{show_id}/episodes`

A show's episodes, newest first.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `include_dismissed` | boolean | no | Include episodes whose download was removed on purpose (default `false`) |

**Response:** `{ "show": { /* show object */ }, "episodes": [ /* episode objects */ ] }`

```json
{
  "id": 1,
  "show_id": 1,
  "guid": "…",
  "title": "The Sweetest Thing",
  "description": "…",
  "published_at": "2026-09-18T14:00:00+00:00",
  "duration_seconds": 1862,
  "season_number": null,
  "episode_number": 712,
  "enclosure_url": "https://…",
  "enclosure_type": "audio/mpeg",
  "filename": "Podcasts/Radiolab/2026-09-18 - The Sweetest Thing.mp3",
  "downloaded_at": "…",
  "dismissed": false,
  "position_seconds": 13.9,
  "played": false
}
```

`filename` is the library path — `null` until downloaded. `position_seconds`/`played` come from `PUT .../playback`.

---

### `PATCH /api/podcasts/shows/{show_id}`

Update a show's retention, and/or its watch's interval or enabled state.

**Request body:** Any of `{ "retention": 5, "interval_minutes": 360, "enabled": false }`.

**Response:** The show object.

---

### `DELETE /api/podcasts/shows/{show_id}`

Unsubscribe.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keep_files` | boolean | no | Keep downloaded episode files on disk (default `false`, which deletes the show's whole folder) |

**Response:** `{ "ok": true, "show": { /* the deleted show */ }, "files_deleted": true }`

---

### `POST /api/podcasts/episodes/{episode_id}/download`

Download one episode on demand, regardless of the show's retention policy.

**Response:** The episode object, with `filename` and `downloaded_at` set. `502` if the download fails.

---

### `DELETE /api/podcasts/episodes/{episode_id}`

Remove a downloaded episode's file. Sets `dismissed: true` — see [Removing episodes](features/podcasts.md#removing-episodes) for why it is never re-downloaded automatically after this.

**Response:** `{ "ok": true }`

---

### `PUT /api/podcasts/episodes/{episode_id}/playback`

Save an episode's resume position and/or played state. Called periodically while an episode plays.

**Request body:** `{ "position_seconds": 42.5, "played": false }` — either field alone is fine.

**Response:** The episode object.

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

A change to the [liked songs](features/liked-songs.md) is broadcast as well, so other open pages can catch up:

```json
{ "type": "likes", "count": 3 }
```

A [podcast](features/podcasts.md) episode download reports its progress the same way as a music download, tagged so it can be told apart:

```json
{
  "type": "podcast_progress",
  "show": "Radiolab",
  "episode": "The Sweetest Thing",
  "progress": 42.5
}
```

Once a podcast sync downloads at least one episode, a plain `{ "type": "podcasts" }` follows, telling open pages to refetch the shows/episodes they're showing.

