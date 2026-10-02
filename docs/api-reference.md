---
icon: material/api
---

# API Reference

Downtify exposes a JSON REST API used by the web UI and the mobile apps. All endpoints are served on the same port as the web UI (default: **8000**).

Every endpoint needs a signed-in user except a few public ones — see [Server and sign-in](#server-and-sign-in) for which credentials each needs (admins can do everything, normal users less), [Accounts and activity](#accounts-and-activity) for users and the activity log, and [Mobile API (v1)](#mobile-api-v1) for the apps' own routes.

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

### `GET /api/discover/chart`

Deezer's own global chart (no genre filter, no auth) — top tracks, albums, artists and playlists, for the [Charts](features/charts.md) page.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | no | Rows per section, 1–50 (default 25) |

**Response:**

```json
{
  "tracks": [ /* song objects, "source": "deezer", plus "preview_url" when Deezer offers a 30s clip */ ],
  "albums": [ { "album_id": "…", "name": "…", "artist": "…", "cover_url": "https://…", "url": "https://www.deezer.com/album/…", "source": "deezer" } ],
  "artists": [ { "artist_id": "…", "name": "…", "cover_url": "https://…", "url": "https://www.deezer.com/artist/…", "source": "deezer" } ],
  "playlists": [ { "playlist_id": "…", "name": "…", "owner": "…", "cover_url": "https://…", "url": "https://www.deezer.com/playlist/…", "source": "deezer" } ]
}
```

Track rows download the same way a search result does — Downtify has no Deezer discography resolver, so `POST /api/download/url` takes a `"source": "deezer"` row's body as-is instead of trying to parse its `url` as a Spotify/YouTube link (the same escape hatch a `text_search` row above uses), and matches it on YouTube Music/YouTube by title, artist and length. A track's `preview_url`, when present, is a 30-second MP3 clip Deezer streams directly (`https://` only) — the web UI plays it with the same preview player an artist's Spotify top songs use; it's `""` when Deezer has no clip for that track. Album, artist and playlist rows are read-only summaries — their `url` only opens the item on `deezer.com`. `502` when Deezer can't be reached or refuses the request.

---

### `GET /api/finder/search`

Free-text search on Deezer alone, for the [Finder](features/finder.md) page.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | yes | Search query (blank → empty lists, no request to Deezer) |
| `limit` | integer | no | Rows per section, 1–50 (default 25) |

**Response:**

```json
{
  "songs": [ /* song objects like /api/discover/chart's tracks, plus "deezer_artist_id" and "deezer_album_id" */ ],
  "albums": [ { "album_id": "…", "name": "…", "artist": "…", "artist_id": "…", "cover_url": "https://…", "release_type": "Album", "track_count": 14, "explicit": false, "url": "https://www.deezer.com/album/…", "source": "deezer" } ],
  "artists": [ { "artist_id": "…", "name": "…", "cover_url": "https://…", "fans": 5212632, "album_count": 36, "url": "https://www.deezer.com/artist/…", "source": "deezer" } ]
}
```

Songs download the same way chart tracks do. Albums and artists are extras: when their part of the search fails they come back empty, while a failed song search is a `502`.

---

### `GET /api/finder/artist`

Everything the Finder's artist column shows.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `artist_id` | string | yes | Deezer artist id (digits) |
| `lang` | string | no | Language of the bio (default `en`) |

**Response:** `{artist_id, name, cover_url, fans, album_count, url, source, bio, social, related, top_songs}`. `bio` is plain text, paragraphs separated by a blank line (the same cleanup a saved [artist bio](features/artist-images.md) gets). `social` holds `twitter`, `facebook`, `website` and `instagram` links. `related` lists up to 20 artists shaped like the search's artists, and `top_songs` lists their 10 most-played tracks shaped like the search's songs. Only the artist itself is required: the bio, related artists and top songs come back empty when fetching them fails. `502` when the artist doesn't resolve.

---

### `GET /api/finder/artist/songs`

A Deezer artist's songs, shaped like a Finder search — Discover's **Find songs**.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `artist_id` | string | yes | Deezer artist id (digits) |
| `name` | string | yes | The artist's name, searched for |

**Response:** `{songs, albums, artists}` like [`GET /api/finder/search`](#get-apifindersearch), with `albums` and `artists` always empty. Deezer is searched for `name` (up to 3 pages of 100 results) and only the songs whose main artist is `artist_id` are kept, in Deezer's order. Deezer's field search (`artist:"..."`) would be the direct way, but it finds no tracks at all today. `502` when Deezer can't be reached or refuses.

---

### `GET /api/finder/artist/albums`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `artist_id` | string | yes | Deezer artist id (digits) |

**Response:** The artist's whole discography, most recent first, as album rows like the search's, plus `release_date`, `year` and `fans`. Deezer's discography listing carries no track count, so `track_count` is `null` until Downtify has looked it up (see below).

---

### `GET /api/finder/albums/track_counts`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ids` | string | yes | Comma-separated Deezer album ids, 50 at most |

**Response:** `{"<album id>": <track count>}`, for the albums Deezer answered for. A lookup that fails, such as a rate limit, is left out so it can be asked again. It costs one small request per album, throttled to stay under Deezer's quota of 50 requests per 5 seconds, and counts are cached for the life of the process.

---

### `GET /api/finder/album`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `album_id` | string | yes | Deezer album id (digits) |

**Response:** `{album_id, name, artist, artist_id, cover_url, release_date, year, label, genres, duration, track_count, fans, release_type, explicit, upc, url, contributors, source, tracks}`. `contributors` is a list of `{artist_id, name, role}` objects. `tracks` holds song objects numbered like a resolved album's (`track_number`, `album_track_total`), each with its `preview_url`. `502` when the album doesn't resolve.

---

### `GET /api/song/url`

Resolve a Spotify, YouTube Music or Deezer URL to metadata.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | yes | Spotify track, album or playlist URL; a YouTube / YouTube Music video, album, playlist or artist URL; or a Deezer track, album, playlist or artist URL (`deezer.com/track/…`) |

**Response:**

- **Track URL** → single song object. A Deezer track's song object also carries `preview_url` - a 30-second MP3 clip Deezer streams (`https://` only), or `""` when it has none.
- **Album URL** → array of song objects
- **Playlist URL** → array of song objects. For a YouTube Music playlist (`…/playlist?list=…`), every song is pinned to the playlist's own video (`youtube_id`), and for uploads the artist/title are taken from an `Artist - Title` video title. See [YouTube Music playlists](features/playlist-monitor.md#youtube-music-playlists).
- **Artist URL** (YouTube Music `…/channel/UC…`/`…/@handle`, or Deezer `deezer.com/artist/…`) → array of release summaries. `404` if a YouTube Music handle doesn't belong to an artist.

`GET /api/url` is an alias for this endpoint.

---

### `GET /api/url/resolve`

Resolve a pasted link to a single object describing what it points at — used by the web UI's link page. Accepts the same URLs as [`GET /api/song/url`](#get-apisongurl), plus Spotify artist URLs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | yes | Spotify track, album, playlist or artist URL; a YouTube / YouTube Music video, album, playlist or artist URL; or a Deezer track, album, playlist or artist URL |

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

`kind` is `track`, `album`, `playlist` or `artist`. A track or collection fills `tracks` (Spotify songs carry `preview_url`, their 30-second clip, or `""` — for a long playlist only the first tracks the embed lists have one; see [`GET /api/preview`](#get-apipreview) for the rest; Deezer songs carry Deezer's own clip); an artist fills `albums` with release summaries instead, and, for YouTube Music, `subtitle` carries the artist description (it is empty for Spotify and Deezer). A Spotify artist's releases come from the Spotify web player's discography query; if that stops resolving, a shorter list (every album, the latest singles) is returned instead, and `albums` is empty when both fail. YouTube Music and Deezer both have a real discography endpoint, so neither needs that fallback. An artist's songs come from [`GET /api/artists/top_songs/url`](#get-apiartiststop_songsurl). `400` for a URL that isn't a supported link, `404` when the link resolves to nothing (e.g. a handle that isn't an artist, or a Deezer id Deezer doesn't recognize), `502` when the upstream lookup fails.

---

### `GET /api/artists/top_songs/url`

An artist's most popular songs, for the web UI's [Top Songs](features/top-songs.md) page.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | yes | Spotify artist URL (`open.spotify.com/artist/…`), YouTube Music artist URL (`/channel/UC…` or `/@handle`), or Deezer artist URL (`deezer.com/artist/…`) |

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

`source` is `spotify`, `youtube` or `deezer`. Songs also carry `play_count`, an integer, when the source reports one (left out otherwise - Deezer never does). Spotify's is the exact total. YouTube Music only reports a rounded figure (`4.4M plays`), so its `play_count` is an approximation (`4400000`) and the song also has `play_count_approx: true`. Spotify returns the artist's own *Popular* shelf (up to 10 songs); YouTube Music returns the head of the artist's *Top songs* playlist (up to 50); Deezer returns its own "top" ranking (up to 50). `400` for a URL that isn't an artist link, `404` when a YouTube Music handle doesn't resolve to an artist, `502` when the upstream lookup fails.

---

### `GET /api/artists/top_songs/spotify`

The first five Spotify top songs of an artist in your Library, for the [Top songs tab](features/top-songs.md#on-an-artists-library-page) of their page. They're read from `<downloads>/.metadata/ArtistTopSongs/<Artist>.topsongs.json` while that file is fresh (7 days); with no file yet they're fetched from Spotify and saved (a few seconds), and a file older than that is returned right away with `"stale": true` while a refresh runs in the background (ask again a few seconds later for the fresh one, as the web UI does). The Spotify artist comes from the artist's profile (`platforms_id.spotify`).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Artist name, exactly as shown in the Library |

**Response:** the same shape as [`GET /api/artists/top_songs/url`](#get-apiartiststop_songsurl) for Spotify, plus when the songs were fetched:

```json
{
  "schema": 2,
  "source": "spotify",
  "artist_id": "6XyY86QOPPrYVGvF9ch6wz",
  "name": "Linkin Park",
  "cover_url": "https://…",
  "fetched_at": "2026-09-24T10:12:03+00:00",
  "stale": false,
  "songs": [ /* five song objects, most popular first */ ]
}
```

Each song object also has `preview_url`: the 30-second clip Spotify's own player offers for the song (`https://p.scdn.co/mp3-preview/…`, MP3), or `""` when there is none. Downtify only passes on an `https` link on `p.scdn.co`. `schema` is the file's layout; a file of an older one is treated as stale.

| Status | When |
|--------|------|
| `400` | `name` is blank. |
| `404` | The artist has no Spotify id saved yet. |
| `502` | Nothing saved and Spotify couldn't be read. |

---

## Artist photo, banner & bio

Manual picker for an artist's profile photo and banner, plus their profile data (bio, social links, related artists) — see [Artist photo, banner & bio](features/artist-images.md). Images are saved as sidecar files under `<downloads>/.metadata/ArtistImage/` and `<downloads>/.metadata/ArtistBannerImage/`, served directly from the existing `/downloads` static mount; profile data lives in `<downloads>/.metadata/ArtistData/`.

### `GET /api/artists/art`

Whether an artist has a saved photo and/or banner.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Artist name, exactly as shown in the Library |

**Response:**

```json
{
  "photo_url": "/downloads/.metadata/ArtistImage/Avril Lavigne.jpg",
  "photo_version": 1758700000123,
  "banner_url": null,
  "banner_version": null
}
```

Either URL is `null` (and its version with it) when that image hasn't been saved yet.

A saved image keeps the same URL every time it's replaced, so a browser that already has it would never ask for the new one. `photo_version` and `banner_version` - the file's modified time, in milliseconds - change exactly when the file does: put them in the URL as `?v=<version>` (the web UI does) and a replaced photo shows up at once, while an untouched one stays cached.

---

### `POST /api/artists/art/bulk`

The same answer for many artists at once, so a page listing them (the Library's *Artists* tab) doesn't send one request per tile.

**Request body:** `{ "names": ["Avril Lavigne", "Evanescence"] }`

**Response:** `{ "<name>": { "photo_url": …, "photo_version": …, "banner_url": …, "banner_version": … } }`, one entry per distinct, non-blank name, each shaped like the response above. A body without a `names` list gets `{}`.

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

**Response:** `{ "url": "/downloads/.metadata/ArtistImage/Avril Lavigne.jpg" }`. `400` when `name`/`kind` are missing or invalid, or the URL doesn't resolve to a real image.

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

A **display-only** photo for an artist that has no saved photo, used for the tiles in the artist page's *Related* tab, for the artists in the Library's *Artists* grid, for the round photo on an artist's own page, for the artists on the Monitor's *Artists* tab, and for the artists Discover suggests and the Finder shows, whenever nobody picked a photo for them. The search page doesn't use it. It is a relay, not a way to get a photo to keep: the image is fetched from Deezer, sent to your browser and forgotten - nothing is written to your downloads folder, and only the artist-name → Deezer image link is remembered (in memory, for three hours). To actually save a photo for an artist use the picker (`POST /api/artists/art/from_url`).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Artist name - matched against Deezer's results exactly (ignoring case and the characters a file name can't hold, so `ACDC` finds `AC/DC`), so a near-match never shows someone else's face. When several Deezer artists share the name, the one with the most fans is used |
| `url` | string | no | The artist's Deezer picture, when the page already has it (Discover's suggestions, the Finder), **base64url-encoded** (RFC 4648 §5, `=` padding optional) so the address travels as one plain query value. It is relayed as the photo, with no search by name. Only an `https://` address on Deezer's image CDN (`*.dzcdn.net`) is accepted; anything else, or a value that isn't base64url, is a `400` |

**Response:** the image bytes with `Cache-Control: public, max-age=10800` and an `ETag`, so the browser holds on to it for three hours. If a photo is already saved for that artist, that local file is sent instead, without browser caching (`Cache-Control: no-cache`), so a newly picked photo shows up right away. `404` (also cacheable for three hours) when Deezer has no exact match, or when the matched artist has no photo on Deezer (it only has a generic placeholder picture, which is never returned).

Only a real answer is ever cached. If something goes wrong - Deezer can't be reached, it refuses because of its limit of 50 requests per 5 seconds, or the image download breaks - the answer is `503` with `Cache-Control: no-store`: nothing about it is kept, by the server or by the browser, so the next time the page asks (opening it again, or a reload) the photo simply comes through.

---

### `GET /api/artists/profile`

An artist's saved profile: bio, origin, formation year, genre, group flag, banner hero colour, social links, related artists, platform ids, and which image their current photo/banner is (`current_cover`/`current_cover_banner`: the path of the URL it was downloaded from, e.g. `/image/ab67…`, without host or query; `upload` for an uploaded one; empty for none - an older profile may still hold the source name, such as `spotify`, instead) — see [Artist photo, banner & bio](features/artist-images.md#fetching-a-bio-automatically).

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

Seeds a brand-new artist's profile automatically the first time it's needed (e.g. opening their Library page) - a no-op past the very first call for a given artist, so it's safe to call on every visit. Saves a photo and/or banner from Spotify (resolved from one of `track_files` already downloaded from there, else by an exact-name search on Spotify), falling back to an exact YouTube Music name match when Spotify has nothing - but only the ones enabled by the `download_cover_art_artist` (photo) and `download_cover_art_artist_banner` (banner) [settings](#post-apisettingsupdate); with both off (the default) no image is saved. Then fetches bio/origin/social/platform-ids the same way `POST .../bio` does - the profile JSON is always written, whatever those settings say, once Apple Music and Deezer have *answered*. If either of them fails (unreachable, over its limit), nothing is written - no JSON, no image - and the blank profile is returned, so the next call tries again; a service saying it doesn't know the artist is an answer. The same seeding also runs in the background when a download finishes (see [Artist photo, banner & bio](features/artist-images.md#when-a-download-finishes)).

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
| `url` | string | yes | Spotify track URL, YouTube URL, or Deezer track URL |
| `client_id` | string | no | WebSocket client ID for progress events |

**Request body (optional):** the song object as returned by search/resolve. Its `track_number`/`album_track_total` survive the re-fetch by URL, `youtube_id` forces the audio source, and `downtify_playlist_url` (a Spotify playlist URL) registers the track as part of that playlist's download. A body with `"source": "deezer"` (a Deezer chart or resolved-link row) is taken as-is instead of re-fetching by `url` - Deezer isn't a URL this endpoint otherwise resolves on its own.

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
| `playlist_url` | string | Optional. A Spotify, YouTube Music or Deezer playlist URL, used to determine the playlist subfolder and M3U name. A Spotify playlist is also tracked as a [playlist download](#playlist-downloads) - Deezer and YouTube Music playlists get the same folder/M3U/cover treatment but aren't tracked that way. |
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

Import a [library-export CSV](../features/library-import.md) (Soundiiz, TuneMyMusic, Exportify). Title and artist columns are required; album is used when present. The file is read client-side and sent as plain text, not a multipart upload. Reuses the same batch pipeline as `/api/download/batch` — same parallel-downloads limit, same delay-between-downloads, and an M3U is written under `playlist_name` if `generate_m3u` is true.

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
  "job_ids": ["csv:a1b2c3d4e5f6:0", "csv:a1b2c3d4e5f6:1"],
  "count": 2,
  "playlist_name": "My Old Library"
}
```

`job_ids` are `csv:{token}:{index}`. `token` is unique to that request and `index` restarts at 0 within the file, so a second import does not replace the first import's queue rows.

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
  "lyrics_lrc_beside": true,
  "lyrics_lrc_dir": "/data/lyrics",
  "format": "mp3",
  "bitrate": "320",
  "output": "{artists} - {title}.{output-ext}",
  "generate_m3u": true,
  "download_cover_art_playlists": true,
  "download_cover_art_artist": true,
  "download_cover_art_artist_banner": false,
  "max_parallel_downloads": 3,
  "download_delay_seconds": 0,
  "external_sync_delay_seconds": 0,
  "cover_resolution": 600,
  "download_cover_art": true,
  "overwrite_existing_files": true,
  "organize_by_artist": true,
  "organize_by_album": true,
  "search_albums": true,
  "mini_player_enabled": true,
  "ui_language": "pt-BR",
  "cache_cover_art": false,
  "library_upgrade": {
    "artwork_min_px": 600,
    "artwork_source": "highest",
    "recheck_days": 30
  },
  "external_library": {
    "folders": []
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
| `max_parallel_downloads` | integer | Concurrent download **and extra-folder Sync** limit. Clamped to `1–30`. |
| `download_delay_seconds` | number | Seconds to wait after each download in a batch before starting the next. Clamped to `0–300`. |
| `external_sync_delay_seconds` | number | Seconds to wait after each extra-folder **batch** (batch size = `max_parallel_downloads`) before looking up lyrics, covers and genre. Clamped to `0–300`. `0` keeps those lookups concurrent, still capped by `max_parallel_downloads`. See [Existing music folders](features/external-library.md). |
| `mini_player_enabled` | boolean | Legacy UI preference, kept so older clients keep working. The web UI no longer reads it — the player bar always appears while a track is loaded. The backend never reads it either. |
| `ui_language` | string | The language the web UI is shown in, as a code like `en` or `pt-BR`. You don't set it by hand: the page sends it every time it loads and whenever you change the language, so the server knows your language for work that runs without a browser. `""` until a page has said. Anything that isn't a language code of that shape is ignored, and the settings page's own save never touches it. See [Internationalization](features/internationalization.md). |
| `download_cover_art` | boolean | Whether to fetch and embed cover art at all. See [Download cover art](features/download-settings.md#download-cover-art). |
| `cover_resolution` | integer | Target pixel size (width & height) for YouTube Music-sourced cover art. Clamped to `300–1200`. Only used when `download_cover_art` is true. See [Cover art resolution](features/download-settings.md#cover-art-resolution). |
| `overwrite_existing_files` | boolean | When `false`, a song already in the library (matched by output filename, or by Spotify track ID through the [library track index](features/library-catalog.md)) isn't downloaded again; the download returns the existing file's path instead. See [Overwrite existing files](features/download-settings.md#overwrite-existing-files). |
| `download_cover_art_playlists` | boolean | Save the playlist's own cover art alongside its M3U file, as `<playlist-name>.jpg`. Only applies while `generate_m3u` is true. Default: `true`. See [Playlist cover art](features/playlist-cover-art.md). |
| `download_cover_art_artist` | boolean | Let Downtify save an artist's photo on its own - when an artist's page is opened for the first time and when one of their tracks finishes downloading (see [`POST /api/artists/profile/ensure`](#post-apiartistsprofileensure)). The manual picker on an artist's Library page is always available regardless of this setting. Default: `true`. See [Artist photo, banner & bio](features/artist-images.md). |
| `download_cover_art_artist_banner` | boolean | Same as above, for the artist's banner image - independent of the photo setting. Default: `false`. See [Artist photo, banner & bio](features/artist-images.md). |
| `lyrics_providers` | array | Ordered fallback list of lyrics providers: `lrclib`, `netease`. Each track tries them in order until one has lyrics. Unknown names are dropped; a list left with only the legacy `genius`/`musixmatch`/`azlyrics` names falls back to the defaults. An empty list means no lyrics, as does `download_lyrics: false`. See [Lyrics](features/lyrics.md). |
| `download_lyrics` | boolean | Whether to look lyrics up at all. |
| `lyrics_lrc_beside` | boolean | When `true` (default), time-synced `.lrc` files are written next to the audio. When `false`, they go under `lyrics_lrc_dir`. See [Lyrics](features/lyrics.md#sidecar-lrc-file). |
| `lyrics_lrc_dir` | string | Absolute folder for `.lrc` files when `lyrics_lrc_beside` is false. Default `/data/lyrics`. Paths inside downloads, slskd, or extra music folders are rejected. |
| `audio_providers` | array | Ordered fallback list of audio sources: `youtube-music`, `youtube`, `slskd`. `slskd` is dropped while `slskd.enabled` is false. See [slskd & Navidrome](features/slskd-navidrome.md#audio-sources-and-fallback-order). |
| `slskd` | object | slskd connection and matching options. Saving with `enabled: true` but no `base_url` or `api_key` returns `400`. |
| `navidrome` | object | Navidrome connection. Saving with `enabled: true` but no `url`, `username` or `password` returns `400`. |
| `sync_navidrome` | boolean | Create/update a Navidrome playlist after playlist downloads, Playlist Monitor sweeps and library changes. |
| `cache_cover_art` | boolean | Keep extracted cover images under `/data/cover_cache` to speed up `/cover`. Covers fetched for [read-only extra folders](features/external-library.md) are always stored there, even when this is `false`. |
| `library_upgrade` | object | Defaults a library upgrade scan starts from: `artwork_min_px` (clamped to `100–3000`), `artwork_source` (`highest`, `spotify`, `itunes`, `youtube-music`) and `recheck_days` (`0–3650`, `0` meaning always re-check). A scan request may override them. See [Upgrade library](features/library-upgrade.md#options). |
| `external_library` | object | Extra folders of already-tagged audio. `folders` is a list of absolute paths (as seen inside the container, max 20). Relative paths are dropped. See [Existing music folders](features/external-library.md). |

---

### `POST /api/settings/update`

Update one or more settings. Takes effect immediately and is persisted to disk.

**Request body:** Partial settings object with any subset of the fields above.

**Response:** Full settings object after the update.

---

### `GET /api/fs/dirs`

Admin. Directory names that complete a path as typed in Settings (extra music folders and the lyrics folder). Query `path` is the text in the field so far.

**Response:** `{ "dirs": ["/music", "/music/collection"] }` — only directories, never files. `/proc`, `/sys` and `/dev` are skipped.

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
    "added": 1789600669,
    "cover": "My Playlist/My Playlist.jpg",
    "liked": false,
    "manual": false
  }
]
```

Sorted by name, except that the [liked songs](features/liked-songs.md) playlist (`"liked": true`, named `Downtify Liked Songs`) comes first. `"manual": true` is a playlist created in the Library (editable); imported Spotify/YouTube playlists are `"manual": false`. A single track or an album downloaded without an M3U doesn't appear here. `added` is the M3U file's modification time (Unix seconds).

`cover` is the library path of the playlist's own artwork when one was saved beside its M3U (see [Playlist cover art](features/playlist-cover-art.md)), and `""` otherwise. Fetch it from [`GET /playlist-cover`](#get-playlist-cover).

---

### `GET /tracks`

List library tracks with artist/album read from each file's embedded tags — downloads, slskd files left in place, and [extra folders](features/external-library.md). The Library **Tracks** tab uses the unfiltered list; album and artist pages use `?artist=`; playlists use `?playlist=`. The [Built-in Player](features/player.md#how-it-works) plays the rows those pages already loaded.

**Response:**

```json
[
  {
    "file": "Artist - Song.mp3",
    "title": "Song",
    "artist": "Artist; Guest",
    "artists": ["Artist", "Guest"],
    "album": "Some Album",
    "album_artist": "Artist",
    "track_number": 3,
    "year": "2024",
    "duration": 213.08,
    "codec": "mp3",
    "bitrate": 320000,
    "sample_rate": 44100,
    "channels": 2,
    "has_cover": true,
    "added": 1789600669,
    "size": 8567376,
    "playlists": ["My Playlist"]
  }
]
```

`artists` is every credited artist, one per entry: the file's `ARTISTS` tag when it has one, else its artist text split on `;`, ` / ` or `, ` (not when it equals `album_artist`: then it's one name). `album_artist`, `track_number` (`0` when untagged), `year` and `duration` (seconds) come from the file's tags and stream info, and `codec` (`mp3`, `flac`, `aac`, `alac`, `opus`, `vorbis`, or `""`), `bitrate` (bits/s), `sample_rate` (Hz) and `channels` (`0` when unknown) from the audio stream; `added` is the file's modification time (Unix seconds) and `size` its size in bytes. `playlists` lists the downloaded Spotify playlists the track belongs to, and is omitted when there are none. Tags are cached in `/data` per file and re-read only when the file's modification time or size changes. The assembled listing is kept in memory and snapshotted in `/data`. `GET /tracks`, [`GET /api/library/summary`](#get-apilibrarysummary), albums and artists serve that snapshot without walking the disk; a download keeps the track snapshot and refreshes it in the background so the UI stays usable while the queue is running. A library delete removes those files from the snapshot immediately. `GET /list?refresh=true` (and the mobile library `refresh` flag) drop the snapshot and rescan. Writing a playlist (including Liked songs) does not rebuild the catalog. The Home page uses [`GET /api/library/summary`](#get-apilibrarysummary) instead of this endpoint.

Query filters so the browser does not download every track to show a short list:

| Query | What it returns |
|-------|-----------------|
| `playlist=Name` | That playlist's files, in playlist order |
| `artist=Name` | Tracks grouped under that album artist |
| `album=Title` | Tracks on that album (combine with `artist=` when two albums share a title) |
| `q=words` | Title / artist / album / path must contain every word |
| `limit=N` | Cap the list (`1`–`200`). Used by the "add songs" picker |

Unfiltered `GET /tracks` is still the Library **Tracks** tab. Album and artist pages use `?artist=`. Search and pasted links use [`POST /api/library/lookup`](#post-apilibrarylookup).

Sorted by `file`, same order as `/list` (except `?playlist=`, which keeps playlist order). `artist`/`album` come back as `""` when the file has no readable tag for that field — the frontend then simply doesn't offer it as a filter for that track.

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

Serve a library file by its library path. Unlike the `/downloads` static mount, this also serves slskd downloads left in place (`slskd/…`) and extra-folder tracks (`ext/<id>/…`).

**Response:** The audio file. `404` if the path isn't in the library.

---

### `GET /cover`

Return cover art for a library file: `/data/cover_cache` first (including covers Sync stored for a [read-only extra folder](features/external-library.md)), then embedded tags, then `cover.jpg` / `folder.jpg` next to the audio.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | yes | Relative path to the file |

**Response:** Image bytes (`image/jpeg` or `image/png`). Returns `404` if none of those sources have a cover.

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

Delete a downloaded playlist: every track registered to it (including tracks other playlists also contain), its playlist-folder leftovers, its M3U file(s) and its catalog entry. A playlist created in the Library (`manual`) only removes the M3U — the audio stays.

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

### `GET /api/library/summary`

Home page payload: how many tracks / albums / artists are in the library, the total size, and up to 12 recently added albums (each with their `GET /tracks` rows). The Home page uses this instead of downloading every track.

**Response:**

```json
{
  "track_count": 8234,
  "album_count": 412,
  "artist_count": 201,
  "size": 12884901888,
  "recent_albums": [
    {
      "title": "Some Album",
      "artist": "Artist",
      "year": "2024",
      "added": 1789600669,
      "tracks": [{ "file": "Artist - Song.mp3", "title": "Song" }]
    }
  ]
}
```

---

### `GET /api/library/albums`

Album tiles for **Library → Albums**: title, artist, year, added, duration, size, `track_count`, and `cover_file` (a library path for `/cover`). Tracks themselves are not included — opening an album loads `GET /tracks?artist=&album=`.

### `GET /api/library/artists`

Artist tiles for **Library → Artists** and Discover: `name`, `track_count`, `album_count`, `liked_count`, `cover_file`, added and duration. Opening an artist loads `GET /tracks?artist=`.

### `POST /api/library/lookup`

Search / link / top-songs pages send the songs on screen (`{ "songs": [{ "artist", "name" }] }`, up to 200). The response is the matching `GET /tracks` rows already in the library, so "in library" and Play work without downloading the whole catalog.

---

### `POST /api/library/playlists`

Create an empty playlist the user can edit in **Library → Playlists**. Writes `Playlists/<name>.m3u` with `#EXTDOWNTIFY:manual`. `409` if the name is taken or reserved (`Downtify Liked Songs`).

**Request body:** `{ "name": "Late night" }`

**Response:** `{ "name": "Late night", "manual": true, "files": [], "count": 0 }`

---

### `POST /api/library/playlists/tracks`

Add or remove library files (downloads or [extra folders](features/external-library.md)) on a **manual** playlist. Imported playlists return `403`. Missing files are dropped from the M3U.

**Request body:**

```json
{
  "name": "Late night",
  "add": ["Artist - Song.mp3", "ext/ab12cd34ef56/Other.mp3"],
  "remove": ["old.mp3"]
}
```

**Response:** `{ "name": "Late night", "manual": true, "files": ["Artist - Song.mp3"], "count": 1, "added": 1, "removed": 1 }`

---

### `POST /api/library/playlists/rename`

Rename a **manual** playlist. Imported playlists return `403`. The M3U and sidecar JPEG are renamed; audio files stay put. `409` if the new name is taken or reserved.

**Request body:** `{ "name": "Late night", "new_name": "Late night mix" }`

**Response:** `{ "name": "Late night mix", "previous": "Late night", "manual": true, "files": ["Artist - Song.mp3"], "count": 1 }`

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

### `POST /api/library/external/sync`

Admin. Start a **background** scan of [extra music folders](features/external-library.md). The request returns as soon as the job is queued. Progress is `GET /api/library/external/sync` and `external_sync` WebSocket frames. A second start while one is running is `409`.

**Body** (optional): `{ "folders": ["/music/collection"] }` — saved first (absolute paths only). Omit to scan whatever is already saved.

**Response:** job status (`state: "running"`), same shape as GET below.

---

### `GET /api/library/external/sync`

Admin. The running extra-folder sync, or the last finished one.

```json
{
  "state": "done",
  "started_at": "2026-10-01T12:00:00+00:00",
  "finished_at": "2026-10-01T12:04:12+00:00",
  "progress": { "done": 80, "total": 80, "current": "" },
  "error": "",
  "result": {
    "folders": ["/music/collection"],
    "added": 80,
    "skipped_duplicates": 40,
    "lyrics_embedded": 75,
    "covers_fetched": 2,
    "errors": 0,
    "log": [
      {
        "status": "imported",
        "title": "Harbor Lights",
        "artist": "Kenji Aoki",
        "file": "ext/abc123def456/Song.mp3",
        "lyrics": true,
        "cover": false,
        "genre": true,
        "lyrics_missing": false,
        "error": ""
      }
    ]
  }
}
```

`state` is `idle`, `running`, `done` or `error`. While `running`, Settings shows progress and hides the last log. `result` is the last finished job (same counters as before: `added`, `skipped_duplicates`, `log` with `imported` / `duplicate` / `error` / …).

---

### `POST /api/library/external/unmap`

Admin. Stop mapping one extra folder. Audio stays on disk; tracks leave the Library/player; `.lrc` sidecars and cached covers for those tracks are deleted.

**Body:** `{ "folder": "/music/collection" }`

**Response:** `{ "folder", "folder_id", "unmapped", "folder_ids", "folders" }` — `folders` is the list left in settings.

---

### `GET /api/library/replace/candidates`

Admin. Versions of a library track to [replace its audio](features/replace-audio.md) with.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | string | yes | The track's library path |
| `query` | string | no | What to search; default "Artist - Title" from its tags. A YouTube or YouTube Music link to one video returns just that video |

```json
{
  "track": { "file": "Portishead/Dummy/Portishead - Roads.mp3", "title": "Roads", "artist": "Portishead", "album": "Dummy", "duration": 304.1 },
  "query": "Portishead - Roads",
  "candidates": [
    {
      "video_id": "7nxWP9BhI7w",
      "title": "Roads",
      "artist": "Portishead",
      "album": "Dummy",
      "duration": 304,
      "duration_diff": 0,
      "thumbnail": "https://lh3.googleusercontent.com/…",
      "source": "youtube-music",
      "url": "https://music.youtube.com/watch?v=7nxWP9BhI7w"
    }
  ]
}
```

`source` is `youtube-music`, `youtube` or `link`. `duration_diff` is the candidate's length minus the file's, in seconds (`null` when either is unknown). `404` for an unknown file, `400` for a file that isn't `.mp3`, `.flac`, `.m4a`, `.ogg` or `.opus`, or a link to something other than one video.

---

### `POST /api/library/replace`

Admin. Replace a library track's audio with a YouTube video: `{ "file": "…", "video_id": "7nxWP9BhI7w" }`. **Response:** `{ "job_id": "replace:<file>", "file": "…" }`.

It runs as a queue job, with the usual [WebSocket](#websocket) progress messages (`song.song_id` is `job_id`, and `song.replace` is `{file, video_id}`), ending in `done` or `error`. The file keeps its path, format, tags and modification date; a failure leaves it untouched. `400` for an invalid video id or file type, `404` for an unknown file, `409` while the same file is already being replaced.

---

### `POST /api/library/compilation`

Admin. Mark (`"compilation": true`) or unmark an album as a Various Artists compilation: `{ "files": ["…", "…"], "compilation": true }`, where `files` are every track of the album. See [Marking an album as Various Artists](features/file-organization.md#marking-an-album-as-various-artists).

**Response:**

```json
{
  "album": "Lady Marmalade",
  "album_artist": "Various Artists",
  "compilation": true,
  "changed": ["Christina Aguilera/Lady Marmalade/…mp3"],
  "failed": []
}
```

Only the album-artist tag and the compilation flag of each file change; files keep their path and modification date, and one that fails to rewrite is left untouched and listed in `failed` (`{file, error}`). `album_artist` is the album's new album artist — "Various Artists", or when unmarking the one it had before. The album is remembered, so tracks of it downloaded later get the same tags. `400` when the files aren't all from one album or the album is already in that state, `404` for an unknown file.

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

## Discover

Suggested artists, counted listens and hidden artists — see [Discover](features/discover.md).

### `POST /api/discover`

Artists the library doesn't have yet, ranked from the ones it does. The client sends the library's artists (as the Library page groups them); the server adds listen counts, looks the heaviest ones up on Deezer (answers cached for 7 days) and leaves out the library and hidden artists.

**Request body:**

```json
{
  "library": [
    { "name": "Portishead", "tracks": 12, "liked": 3 },
    { "name": "Massive Attack", "tracks": 8, "liked": 0 }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `library` | array | yes | Every library artist: `name`, `tracks` (songs in the library), `liked` (of those, how many are liked) |

**Response:**

```json
{
  "artists": [
    {
      "name": "Hooverphonic",
      "deezer_id": "1146",
      "picture_url": "https://cdn-images.dzcdn.net/…/500x500-000000-80-0-0.jpg",
      "fans": 402551,
      "score": 4.428,
      "because": ["Portishead", "Massive Attack"]
    }
  ],
  "seeds": ["Portishead", "Massive Attack"],
  "partial": false
}
```

`artists` is best first (at most 48); `because` names up to three library artists that suggested it, the biggest contributor first. `picture_url` is `""` when Deezer has no photo. `seeds` are the library artists that were looked up. `partial` is `true` when Deezer couldn't be asked for some of them — the list is then built from the rest (plus any expired cached answer), not an error. `400` when `library` isn't a list.

---

### `POST /api/discover/collections`

Albums and playlists built on the suggested artists — see [Albums and playlists](features/discover.md#albums-and-playlists). Reuses the (cached) answer of [`POST /api/discover`](#post-apidiscover) and adds one Spotify search per artist, cached for 7 days.

**Request body:** the same `library` as `POST /api/discover`, plus:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `albums` | array | no | `{artist, title}` per library album — left out of the answer (titles match ignoring `(…)`/`[…]`/` - …` suffixes) |
| `playlist_ids` | array | no | Spotify ids of playlists already downloaded — left out of the answer |

**Response:**

```json
{
  "albums": [
    {
      "name": "Grace",
      "artist": "Jeff Buckley",
      "year": "1994",
      "cover_url": "https://i.scdn.co/image/…",
      "spotify_id": "7yQtjAjhtNi76KRu05XWFS",
      "url": "https://open.spotify.com/album/7yQtjAjhtNi76KRu05XWFS",
      "reason": "similar",
      "because": ["Radiohead"]
    }
  ],
  "more_albums": [ /* same shape, "reason": "more_from" */ ],
  "playlists": [
    {
      "name": "Portishead Radio",
      "owner": "Spotify",
      "cover_url": "https://…",
      "spotify_id": "37i9dQZF1E4BveUiW5aK5l",
      "url": "https://open.spotify.com/playlist/37i9dQZF1E4BveUiW5aK5l",
      "reason": "radio",
      "artist": "Portishead"
    }
  ],
  "artist_urls": { "Jeff Buckley": "https://open.spotify.com/artist/3nnQpaTvKb5jCQabZefACI" },
  "partial": false
}
```

`albums`: the top album of each of the best 12 suggested artists. `more_albums`: up to two albums per heaviest library artist that aren't in `albums`. `playlists`: Spotify's `<artist> Radio` for the heaviest library artists (`reason: "radio"`), then its `This Is <artist>` for suggested artists (`reason: "this_is"`). `artist_urls`: the Spotify page of each suggested artist the search found by exact name. `partial` as in `POST /api/discover`, also counting failed Spotify searches. `400` when `library` isn't a list.

The web page doesn't use this endpoint any more: it asks the two below, Deezer's answer first. It's kept as it is for other clients.

---

### `POST /api/discover/collections/deezer`

The same shelves from Deezer alone — the web page's first, quick answer (see [Albums and playlists](features/discover.md#albums-and-playlists)). Reuses the (cached) answer of [`POST /api/discover`](#post-apidiscover) and reads each artist's Deezer discography and editorial playlist, cached for 7 days.

**Request body:** what `POST /api/discover/collections` takes, plus:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `playlist_names` | array | no | The library's playlist names — a Deezer playlist already downloaded (known by its title) is left out |

**Response:**

```json
{
  "albums": [
    {
      "name": "Discovery",
      "artist": "Daft Punk",
      "year": "2001",
      "cover_url": "https://cdn-images.dzcdn.net/images/cover/…",
      "source": "deezer",
      "deezer_album_id": "302127",
      "deezer_artist_id": "27",
      "url": "https://www.deezer.com/album/302127",
      "key": "daft punk|discovery",
      "reason": "similar",
      "because": ["Justice"]
    }
  ],
  "more_albums": [ /* same shape, "reason": "more_from" */ ],
  "playlists": [
    {
      "name": "100% Radiohead",
      "owner": "Deezer Artist Editor",
      "cover_url": "https://cdn-images.dzcdn.net/images/playlist/…",
      "source": "deezer",
      "deezer_playlist_id": "3184748882",
      "url": "https://www.deezer.com/playlist/3184748882",
      "reason": "essentials",
      "artist": "Radiohead"
    }
  ],
  "partial": false
}
```

An album is the artist's full album with the most fans (a single or EP only when there's no album). `key` identifies an album across services (artist and title, edition suffixes dropped). `playlists`: Deezer's editorial `100% <artist>` for the suggested artists, when its editors have one. `partial` as in `POST /api/discover`, also counting failed Deezer lookups. `400` when `library` isn't a list.

---

### `POST /api/discover/collections/spotify`

What Spotify adds to the Deezer answer — the web page's second answer, loaded after it. Spotify's own picks (as in [`POST /api/discover/collections`](#post-apidiscovercollections), from the same cached searches), each album looked up on Deezer by artist and title.

**Request body:** what `POST /api/discover/collections` takes, plus:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `shown` | array | no | The `key` of every album already on the page — left out without being looked up on Deezer |

**Response:** `{albums, more_albums, playlists, partial}`. An album Deezer has comes in the Deezer shape above (`source: "deezer"`, opens in the Finder); one it doesn't keeps the Spotify shape of `POST /api/discover/collections` plus `source: "spotify"` and `key`. `playlists` are only Spotify's `This Is <artist>` (`reason: "this_is"`, `source: "spotify"`) — its `Radio` mixes aren't offered. A match is kept for 30 days (a missing one for 7); a failed lookup is never kept and makes `partial` true. `400` when `library` isn't a list.

---

### `POST /api/discover/listens`

Count one listen to an artist. Sent by the player once a library song has played half its length (or four minutes).

**Request body:** `{ "artist": "Portishead" }`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artist` | string | one of these | The artist the play counts for |
| `track_id` | string | one of these | A [track id](#mobile-api-v1) instead: its album artist is used |
| `played_at` | string | no | ISO 8601 time of the play, for plays reported after being offline (a future time counts as now; a late report never moves `last_played` back) |
| `play_id` | string | no | Identifies this play: reporting it again doesn't count it twice |

**Response:** `{ "name": "Portishead", "plays": 7, "last_played": "2026-09-26T17:31:40+00:00" }`

`400` when there's no artist to count it for.

---

### `DELETE /api/discover/listens`

Forget every counted listen. The library and likes are untouched.

**Response:** `{ "cleared": 12 }`

---

### `GET /api/discover/blocked`

Hidden artists, most recently hidden first.

**Response:** `[{ "name": "Archive", "blocked_at": "2026-09-26T17:31:03+00:00" }]`

---

### `POST /api/discover/blocked`

Never suggest an artist again. Hiding one twice is a no-op. Names are matched ignoring case and the characters a file name can't hold (`AC/DC` = `ACDC`).

**Request body:** `{ "name": "Archive" }`

**Response:** `{ "name": "Archive", "blocked_at": "2026-09-26T17:31:03+00:00" }` — `400` when `name` is blank.

---

### `DELETE /api/discover/blocked`

Show a hidden artist again.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | yes | Artist name (query parameter) |

**Response:** `{ "name": "Archive", "removed": true }` — `removed` is `false` when it wasn't hidden.

---

## Previews

### `GET /api/preview`

A song's 30-second preview clip from Deezer, for a song without a `preview_url` of its own (a YouTube Music result, or a Spotify playlist track past what the embed lists). Used by the web UI the first time a song's preview is played.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `artist` | string | yes | The song's (first) artist |
| `title` | string | yes | The song's title |
| `duration` | number | no | Its length in seconds — among matches, the closest one wins |

**Response:** `{ "preview_url": "https://cdnt-preview.dzcdn.net/…" }`

Only a Deezer song by that artist with that title counts (both compared ignoring case and `(Live)`/`[Remastered]`/` - Radio Edit` style suffixes); `preview_url` is `""` when there's none. `503` when Deezer can't be reached or refuses (rate limit). The link is Deezer's own, short-lived — ask again rather than storing it.

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

**Response:** Array of watch objects. Each has a `kind` of `"playlist"`, `"artist"` or `"podcast"`, and a `source` of `"spotify"` or `"youtube_music"` (the service the watch was added from, read from its `url`; meaningless for a podcast watch). `spotify_id` is the watch's unique key: the Spotify or YouTube Music playlist id, an artist's YouTube Music channel id, or a podcast's RSS feed URL. For an artist watch, `last_track_count` is the number of releases, `release_types` the kinds of release it downloads (a subset of `["album", "single", "ep"]`, in that order) and `new_only` whether it skips what the artist had released when the watch started — see [Choosing what to download](features/playlist-monitor.md#choosing-what-to-download). Playlist watches carry the same two fields at their defaults (all kinds, `false`); they don't mean anything there.

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

An artist watch also takes:

| Field | Type | Description |
|-------|------|-------------|
| `release_types` | array | Kinds of release to download: any of `album`, `single`, `ep` (default: all). Unknown values are ignored; `400` when none is left |
| `new_only` | boolean | Skip everything already released; only later releases download (default `false`). The first check then records the discography instead of downloading it |

Both are ignored for a playlist link.

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
| `release_types` | array | Artist watches only — as in `POST` |
| `new_only` | boolean | Artist watches only. `true` records whatever is out at the next check as skipped; `false` forgets the skipped releases so the next check downloads them |

Changing `release_types` or `new_only` starts a check in the background if the watch is enabled, and is a `400` on a playlist watch. A `url` that points at the **same** playlist or artist only replaces the stored `url`. One that points at a **different** playlist or artist of the same kind retargets the watch: `spotify_id`, `name` and `url` change, `last_checked` becomes `null`, `last_track_count` becomes `0`, and its downloaded-track and seen-release history is cleared. If the watch is enabled, a first check starts in the background, as after `POST`. An unchanged `url` is ignored.

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

## Server and sign-in

Who this server is, signing in, and pairing apps — see [Users & Sign-in](features/users.md) and [Mobile Apps](features/mobile-apps.md). Accounts, preferences and the activity log are in [Accounts and activity](#accounts-and-activity). The routes an app uses are in [Mobile API (v1)](#mobile-api-v1), and the whole flow is in the [mobile client contract](mobile-client-contract.md).

**Who may call what.** Every request needs a signed-in user, except the public routes below — unless `DOWNTIFY_DISABLE_AUTH` is `true`: then a request without credentials is the first admin's, `POST /api/auth/login`, `/api/users…` and changing your username or password answer `409`, and device tokens and the same-site check work as usual. A request that sends a revoked device token gets `401` even on a public route, so an app learns it was unpaired.

| Scope | Credentials | Covers |
|-------|-------------|--------|
| Public | none | The web app's own files, `GET /api/health`, `GET /api/version`, `GET /api/server/info`, `GET /api/auth/status`, `POST /api/auth/login`, `POST /api/auth/logout`, `POST /api/auth/pair` |
| Client | a device token (`Authorization: Bearer dtfy_…`), a signed URL (reads only), a WebSocket ticket, or any web session | Library and media reads (`/tracks`, `/list`, `/playlists`, `/lyrics`, `/cover`, `/playlist-cover`, `/downloads/…`, `/media/…`), `/api/v1/…`, search and link resolving, previews, `POST /api/download/url\|batch\|album`, likes, Discover and listens, podcast reads, episode downloads and playback, the queue and monitor lists (read), `GET /api/me`, `POST /api/activity/playback`, `POST /api/auth/ws-ticket`, `WS /api/ws` |
| User | a web session of any user (the `downtify_session` cookie) | Client, plus your own account (`/api/me…`), your paired devices and pairing (`/api/auth/devices…`, `/api/auth/pairing…`) |
| Admin | a web session of an **admin** | Everything else: settings, cookies, deleting files and playlists, library upgrade/reconcile/archive, queue changes, monitor and podcast subscription changes, artist photo/bio edits, CSV import, renaming the server, users, the activity log, signing everyone out |

Without credentials: `401` (`WWW-Authenticate: Bearer`). A normal user's browser calling an admin route: `403` `{"detail": "This needs an admin"}`; a device calling a route that needs a browser: `403` `{"detail": "This needs a signed-in browser"}`. A cookie-authenticated change (`POST`/`PUT`/`PATCH`/`DELETE`, or the WebSocket) whose `Origin`/`Referer` is another site: `403`. CORS allows any origin **without** credentials, so a web session only works from Downtify's own page.

### `GET /api/server/info`

Public. What an app checks before it has credentials.

```json
{
  "server_id": "cf12b3c4f530731551690cc62b1365a1",
  "name": "nas",
  "product": "Downtify",
  "version": "3.2.0",
  "api_version": 1,
  "require_sign_in": true,
  "capabilities": {
    "transcoding": { "available": true, "formats": ["aac", "mp3", "opus"], "bitrates": [96, 128, 160, 192, 256, 320] },
    "signed_urls": true,
    "pairing": true,
    "podcasts": true,
    "discover": true,
    "lyrics": true,
    "library_sync": true
  }
}
```

`server_id` is made once and kept in `/data/server.json`. `api_version` is the version of [`/api/v1`](#mobile-api-v1): it changes only for a change that would break an existing app. `require_sign_in` is `true` unless accounts are turned off (`DOWNTIFY_DISABLE_AUTH`). `transcoding.available` is `false` (and the lists empty) without ffmpeg.

---

### `PATCH /api/server`

Admin. Rename the server — the name apps and [LAN discovery](features/mobile-apps.md#finding-the-server-on-your-network) show.

**Request body:** `{ "name": "Living room" }` — trimmed, one line, 64 characters at most. `400` when empty.

**Response:** the new `GET /api/server/info`.

---

### `GET /api/server/port`

Admin. The port the server listens on and the one it starts on next:

```json
{ "port": 8000, "saved": 9000, "next": 9000, "locked_by": "", "in_docker": true, "can_restart": true, "min": 1024, "max": 65535 }
```

`saved` is the port chosen in Settings → Server (`null` when none). `locked_by` is `DOWNTIFY_PORT`, `PORT` or `--port` when one of those sets the port instead of Settings, `""` otherwise.

---

### `PUT /api/server/port`

Admin. Choose the port: `{ "port": 9000, "restart": false }` — saved in `/data/server.json` for the next start; `restart: true` also restarts the server on it right away (after answering). `400` for a port outside 1024–65535, `409` when the environment or the command line sets the port, or the port is already in use. **Response:** the `GET` shape plus `restarting`.

---

### `GET /api/auth/status`

Public. How this request is signed in.

```json
{
  "require_sign_in": true,
  "auth_disabled": false,
  "min_password_length": 8,
  "signed_in": true,
  "via": "device",
  "user": { "id": 2, "username": "maria", "role": "user", "default_password": false, "created_at": "…", "last_login_at": "…", "last_login_ip": "192.168.1.31" },
  "device": { "id": "8uz4d35zjpn2", "name": "Pixel 8" },
  "notice": null
}
```

`via` is `session` (a browser), `device` (an app's token) or `null`; `user` is who that is (`null` when signed out); `device` is `null` unless `via` is `device`. The web app shows its sign-in page when `signed_in` is `false`.

`auth_disabled` is `true` when accounts are turned off (`DOWNTIFY_DISABLE_AUTH`): then `signed_in` is `true`, `via` is `open` and `user` is the first admin.

`notice` is only set while signed out, on a server upgraded from a version without accounts, until an admin signs in: `{ "username": "admin", "password": "downtify" }` — `password` is `null` when the sign-in password of the older version was kept.

---

### `POST /api/auth/login`

Public, rate-limited per address (10 failures per 5 minutes, then `429` with `Retry-After`). Signs a browser in.

**Request body:** `{ "username": "admin", "password": "…" }` — the username in any case.

**Response:** `{ "signed_in": true, "user": { … } }` (the `user` shape above) and a `downtify_session` cookie (`HttpOnly`, `SameSite=Lax`, `Secure` over HTTPS, 30 days since last use). `401` `{"detail": "Wrong username or password"}` otherwise — the same for an unknown user.

---

### `POST /api/auth/logout`

Public. Ends this browser's session, if it has one. **Response:** `{ "signed_in": false }`.

---

### `GET /api/auth/devices`

User. Your paired apps, newest first — everyone's for an admin.

```json
[
  {
    "id": "8uz4d35zjpn2",
    "name": "Pixel 8",
    "platform": "android",
    "created_at": "2026-09-27T03:15:17+00:00",
    "last_seen_at": "2026-09-27T09:02:41+00:00",
    "last_ip": "192.168.1.31",
    "user_id": 2,
    "username": "maria"
  }
]
```

`last_seen_at`/`last_ip` are updated at most once a minute.

---

### `PATCH /api/auth/devices/{id}`

User. Rename one of your devices (an admin: anyone's): `{ "name": "…" }`. **Response:** the device. `404` when unknown, unpaired or someone else's.

---

### `DELETE /api/auth/devices/{id}`

User. Unpair one of your devices (an admin: anyone's): its token and signed URLs stop working and its WebSocket is closed (code `4401`). **Response:** `{ "id": "8uz4d35zjpn2", "revoked": true }`. `404` when unknown or someone else's.

---

### `POST /api/auth/revoke-all`

Admin. Unpairs every device of every user, ends every web session (this one too) and voids every signed URL (a new signing key). **Response:** `{ "revoked": true }`. To sign out only yourself everywhere, see [`POST /api/me/sign-out-everywhere`](#post-apimesign-out-everywhere).

---

### `POST /api/auth/pairing`

User. Start pairing an app to **your** account. **Response:** `{ "pairing_id": "rfLmICXqGfRBXyXl", "code": "34A3-MAMC", "expires_in": 300 }`.

The web page shows `code` and a QR code for `downtify://pair?url=<this page's origin>&sid=<server_id>&code=<code>`, then follows the pairing with the next endpoint or the `device_paired` [WebSocket](#websocket) message (sent only to that user's pages).

---

### `GET /api/auth/pairing/{pairing_id}`

User (the one who started it, or an admin). `{ "status": "pending", "expires_in": 241 }`, `{ "status": "paired", "device": { … } }` or `{ "status": "expired" }`.

---

### `DELETE /api/auth/pairing/{pairing_id}`

User (the one who started it, or an admin). Cancel a pending pairing. **Response:** `{ "cancelled": true }`.

---

### `POST /api/auth/pair`

Public, rate-limited per address (10 failures per 5 minutes). An app trades a pairing code for its device token.

**Request body:** `{ "code": "34A3-MAMC", "device_name": "Pixel 8", "platform": "android" }` — the code in any case, with or without the dash.

**Response:**

```json
{
  "token": "dtfy_8uz4d35zjpn2_Zk3…",
  "device": { "id": "8uz4d35zjpn2", "name": "Pixel 8" },
  "server": { "server_id": "cf12b3c4…", "name": "nas" },
  "user": { "username": "maria", "role": "user" }
}
```

The device belongs to the user who showed the code. A code works once and for five minutes; `401` otherwise. The token is shown only here — the server keeps a hash.

---

### `POST /api/auth/ws-ticket`

Client. A single-use ticket, valid for 60 seconds, for opening the [WebSocket](#websocket) as `/api/ws?client_id=…&ticket=…` without an `Authorization` header. **Response:** `{ "ticket": "…" }`.

---

## Accounts and activity

Your own account, every account (admins), and what everyone does — see [Users & Sign-in](features/users.md).

### `GET /api/me`

Client. Who is signed in, and their preferences: `{ "user": { … }, "preferences": { "theme": "dark", "locale": "pt-BR", "show_lyrics": true, "search_albums": false } }` — a preference not set yet is missing.

---

### `PATCH /api/me`

User. Change your username: `{ "username": "…" }` — 3 to 32 letters, digits, `.`, `-` or `_`, unique regardless of case (`400` otherwise). **Response:** `{ "user": { … } }`.

---

### `PUT /api/me/password`

User. Change your password: `{ "current_password": "…", "new_password": "…" }`. `403` when the current one is wrong (rate-limited like sign-in), `400` for a new one under 8 characters. Your other browsers and apps stay signed in. **Response:** `{ "user": { … } }`.

---

### `GET /api/me/preferences` · `PUT /api/me/preferences`

User. Your preferences (Settings → General): `theme` (`dark`/`light`/`system`), `locale`, `show_lyrics`, `search_albums`. `PUT` merges what it's sent into them and answers the result; other keys are ignored. `search_albums: false` makes `GET /api/albums/search` answer `[]` for you, whatever the server's setting.

---

### `POST /api/me/sign-out-everywhere`

User. Unpairs every app of yours and ends every web session of yours, this one included. **Response:** `{ "revoked": true }`.

---

### `GET /api/users`

Admin. Every account, by username: the `user` shape plus `devices` (how many apps it has paired).

---

### `POST /api/users`

Admin. Add an account: `{ "username": "maria", "password": "…", "role": "user" }` (`role` is `admin` or `user`, default `user`). `400` for a taken or invalid username or a short password. **Response:** the user.

---

### `PATCH /api/users/{id}`

Admin. Change an account — any of `{ "username", "role", "password" }`. A new password ends that user's web sessions (but the admin's own, when it's their account); their apps stay paired. `400` when it would leave the server without an admin. **Response:** the user.

---

### `DELETE /api/users/{id}`

Admin. Delete an account: its apps are unpaired and its sessions ended. `400` for your own account or the last admin, `404` when unknown. **Response:** `{ "id": 2, "deleted": true }`.

---

### `GET /api/activity`

Admin. The activity log, newest first.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | no | 1–200, default 100 |
| `before` | integer | no | The `next` of the previous page |
| `user_id` | integer | no | Only this user |
| `kind` | string | no | One kind, or several comma-separated |

```json
{
  "entries": [
    {
      "id": 57,
      "at": "2026-09-27T19:10:03+00:00",
      "user_id": 2,
      "username": "maria",
      "kind": "playback",
      "summary": "Portishead - Roads",
      "detail": { "track": { "title": "Roads", "artist": "Portishead", "file": "Portishead - Roads.flac", "duration": 305.0 } },
      "client": "Pixel 8",
      "ip": "192.168.1.31"
    }
  ],
  "next": 0
}
```

`kind` is one of `login`, `login_failed`, `logout`, `playback` (a song started), `download`, `like`, `unlike`, `delete`, `device_paired`, `device_unpaired`, `user_created`, `user_updated`, `user_deleted`, `password_changed`, `settings_changed` (`summary` lists the setting names, never their values). `client` is the app's name or `Web (Firefox on Linux)`. Entries are kept for 90 days.

---

### `GET /api/activity/now`

Admin. What each browser tab and app is playing — the players that reported in the last 90 seconds, playing ones first:

```json
[
  {
    "user_id": 2,
    "username": "maria",
    "client": "Pixel 8",
    "ip": "192.168.1.31",
    "track": { "title": "Roads", "artist": "Portishead", "track_id": "t7b255c87668ba03b", "duration": 305.0 },
    "paused": false,
    "position": 42.0,
    "started_at": "2026-09-27T19:10:03+00:00",
    "seconds_ago": 12
  }
]
```

---

### `POST /api/activity/playback`

Client. A player says what it plays: `{ "player": "<id stable for this player>", "state": "playing" | "paused" | "stopped", "track": { "title", "artist", "album", "file" or "track_id", "duration" }, "position": 42 }`. Send it when a song starts, on pause/resume and stop, and about every 30 seconds while playing. A new song adds a `playback` entry to the log; the rest only update `GET /api/activity/now`. `400` for an unknown `state`, or no `file`/`track_id` (except for `stopped`). **Response:** `{ "ok": true }`.

---

## Mobile API (v1)

What the apps use: everything by **track id**, which survives the file being moved or renamed. Versioned apart from the web app's routes (`api_version` in [`GET /api/server/info`](#get-apiserverinfo)). The flow is in the [mobile client contract](mobile-client-contract.md). All routes are in the client scope.

### `GET /api/v1/library`

The library as a change feed.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `since` | integer | no | The `cursor` from the last response; `0` (default) for everything |
| `refresh` | boolean | no | Rescan the folder now instead of using the scan cached for about a minute |

**Response:**

```json
{
  "cursor": 1742,
  "full": false,
  "tracks": [
    {
      "id": "t7b255c87668ba03b",
      "file": "Portishead - Roads.flac",
      "title": "Roads",
      "artist": "Portishead",
      "artists": ["Portishead"],
      "album": "Dummy",
      "album_artist": "Portishead",
      "album_id": "6aa1df0c3e5f2b11",
      "artist_id": "0a92c1e0bb3d8f44",
      "track_number": 3,
      "year": "1994",
      "duration": 305.12,
      "codec": "flac",
      "bitrate": 912000,
      "sample_rate": 44100,
      "channels": 2,
      "size": 34812211,
      "added": 1789600669,
      "has_cover": true,
      "playlists": ["Trip-hop"]
    }
  ],
  "deleted": ["t0c4d5e6f7a8b9c0d"]
}
```

`tracks` are the tracks added or changed after `since`, `deleted` the ids removed after it. `full: true` (for `since=0`, or a `since` older than the 90 days removed ids are kept, or newer than `cursor`) means `tracks` is the whole library: replace what you have. `artists` splits `artist` the way the web app does; `album_artist` is the tag, else the first artist; `album_id` (album artist + album, case-insensitive; `""` without an album) and `artist_id` (the album artist) are the keys the web app groups albums and artists by. `codec` is `mp3`, `flac`, `aac`, `alac`, `opus` or `vorbis` (`""` when unknown); `bitrate` in bits per second.

`ETag` is set; a matching `If-None-Match` gets `304`. A sync that finds changes on disk also sends `library_changed` to other connected clients.

**Track ids:** a file keeps its id when it's re-tagged in place, moved (same name and size) or renamed (same title, artist, album and length). A file moved *and* re-tagged in the same sweep gets a new id; the old one is reported in `deleted`.

---

### `GET /api/v1/tracks/{id}`

One track row (the shape above). `404` for an unknown or removed id.

---

### `GET /api/v1/tracks/{id}/stream`

The track's audio. Also `HEAD`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `format` | string | no | `original` (default), `opus`, `aac` or `mp3` |
| `bitrate` | integer | no | kbps for a transcoded format: 96, 128, 160 (default), 192, 256 or 320 (others round up) |
| `download` | boolean | no | Add `Content-Disposition: attachment` (saving an offline copy) |

**Response:** the audio with HTTP Range support (`206 Partial Content`, `Content-Range`, `Accept-Ranges: bytes`), exact `Content-Length`, and `Content-Type` `audio/flac`, `audio/mpeg`, `audio/mp4` or `audio/ogg`. `Cache-Control: private, max-age=604800`.

A transcoded copy is made with ffmpeg on the first request (the request waits), cached in `/data/transcode_cache` and served like a file from then on; `X-Downtify-Transcoded: opus/160`. When the original is lossy and already at or below the requested bitrate it's served instead: `X-Downtify-Transcoded: no`. `400` for an unknown format, `501` without ffmpeg, `500` when ffmpeg fails. A client that disconnects while its copy is being made stops the run (unless another request is waiting for the same copy).

---

### `GET /api/v1/tracks/{id}/cover`

The track's cover. Also `HEAD`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `size` | integer | no | `150`, `300` or `600` (longest side, px; others round up). Omit for the full-size picture |

**Response:** the image (thumbnails are JPEG), `ETag`, `Cache-Control: private, max-age=604800`; `304` for a matching `If-None-Match`. `404` when the file has no cover. Every size is made once and kept in `/data/cover_thumbs`.

---

### `GET /api/v1/tracks/{id}/lyrics`

`{ "synced": "<LRC text>", "plain": "<text>" }` — the same as [`GET /lyrics`](#get-lyrics); either may be empty.

---

### `GET /api/v1/playlists`

```json
[
  { "name": "Downtify Liked Songs", "liked": true, "count": 12, "cover": "", "track_ids": ["t7b2…", "…"] }
]
```

The playlists [`GET /playlists`](#get-playlists) lists, with track ids in playlist order. `cover` is a path for `GET /playlist-cover?file=`, or `""`.

---

### `GET /api/v1/likes`

`{ "track_ids": ["t7b2…"] }`, most recently liked first.

---

### `PUT /api/v1/likes`

Like or unlike a track: `{ "track_id": "t7b2…", "liked": true }`. Idempotent. **Response:** `{ "track_id": "t7b2…", "liked": true }`. `400` without `track_id`, `404` for an unknown one. The same likes as [`/api/likes`](#likes).

---

### `POST /api/v1/sign`

Signed URLs for a player that can't send the device token (a Cast receiver). Only for a paired device (`400` otherwise).

**Request body:**

```json
{
  "items": [
    { "path": "/api/v1/tracks/t7b2…/stream", "params": { "format": "aac", "bitrate": "256" } },
    { "path": "/api/v1/tracks/t7b2…/cover", "params": { "size": "600" } }
  ],
  "ttl": 3600
}
```

**Response:**

```json
{
  "urls": ["/api/v1/tracks/t7b2…/stream?format=aac&bitrate=256&exp=1790479684&kid=8uz4d35zjpn2&sig=…", "…"],
  "expires_at": 1790479684
}
```

Paths must start with `/api/v1/tracks/`, `/downloads/`, `/media/`, `/cover` or `/playlist-cover` (`400` otherwise); at most 500 items. `ttl` is seconds, 60 to 86400 (default 3600). A URL is valid for `GET`/`HEAD` of exactly that path and those parameters until `exp`, while the device stays paired; changing any parameter breaks the signature (`401`).

---

## WebSocket

### `WS /api/ws`

Real-time download progress events.

| Query parameter | Required | Description |
|----------------|----------|-------------|
| `client_id` | yes | Unique client identifier (UUID recommended) |
| `ticket` | no | A [WebSocket ticket](#post-apiauthws-ticket), for a client that can't send `Authorization` |

The handshake needs a device token (`Authorization: Bearer …`), a web session cookie (from Downtify's own page) or a ticket; otherwise it's refused. A socket is closed with code `4401` when its device is unpaired or its user is signed out everywhere or deleted.

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

`status` on a per-track event is `downloading`, `done`, or `error`. `filename` is set (non-null) on the final `done` event. A row that is still waiting has `status: "queued"` on [`GET /api/queue`](#get-apiqueue), not as its own socket event.

Queuing a playlist batch or a CSV import registers every job, then broadcasts one reload so open pages fetch that list once:

```json
{ "type": "queue_reload" }
```

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

When tracks are added, removed or moved (a finished download, a delete, a reconcile, or a [library sync](#get-apiv1library) that found changes on disk), connected clients are told once, a couple of seconds later, however many files changed — the apps sync on it:

```json
{ "type": "library_changed" }
```

When an app is paired, the web page showing the code learns it at once:

```json
{ "type": "device_paired", "pairing_id": "rfLmICXqGfRBXyXl", "device": { "id": "8uz4d35zjpn2", "name": "Pixel 8", "platform": "android", "…": "…" } }
```

