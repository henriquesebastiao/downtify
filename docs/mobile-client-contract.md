---
icon: lucide/file-code
---

# Mobile Client Contract

How an app (the official Android client, or any other) talks to a Downtify server: **discover → check → sign in (or pair) → sync → stream → report**. Everything here is `api_version` **1**; the full request/response shapes of each endpoint are in the [API reference](api-reference.md#server-and-sign-in). User-facing behaviour (signing in, pairing, accounts, transcoding limits) is described in [Mobile Apps](features/mobile-apps.md) and [Users & Sign-in](features/users.md).

## 1. Discover

Browse mDNS/DNS-SD for **`_downtify._tcp`** (Android: `NsdManager`). Each service carries a TXT record:

| Key | Example | Meaning |
|-----|---------|---------|
| `id` | `cf12b3c4…` | Server id (stable; same as `server_id` below) |
| `name` | `nas` | Server name, editable in Settings → Apps |
| `version` | `3.2.0` | Downtify version |
| `api` | `1` | API version |
| `port` | `8000` | Port |
| `scheme` | `http` | `http` (a reverse proxy in front may offer `https` — the user types that address) |
| `path` | `/` | Base path |

Build the address from the resolved host + `port`. Discovery is a convenience: always offer manual entry (Docker bridge networks don't announce — see the user docs).

## 2. Check the address

`GET {base}/api/server/info` — public, no credentials.

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
    "signed_urls": true, "pairing": true, "password_sign_in": true, "podcasts": true, "discover": true, "lyrics": true, "library_sync": true
  }
}
```

- Refuse to continue when `product` isn't `Downtify` or `api_version` is higher than the app knows.
- Remember `server_id`: it identifies the server across address changes. When the address later answers with a different id, it's a different server.
- Use `capabilities` to enable features (e.g. hide mobile-data quality when `transcoding.available` is false).
- `capabilities.password_sign_in` decides how the app asks for credentials next: a username and password when it is `true`, a pairing code otherwise (accounts turned off, or a server older than `POST /api/auth/token`).

## 3. Sign in or pair

Either way the app ends up with the same device token, tied to one user. Sign-in is the usual way; pairing is the shortcut for a phone that shouldn't see the password, or when the web page is already open.

### Sign in

The user types their username and password (the ones they use on the web page):

```http
POST /api/auth/token
Content-Type: application/json

{ "username": "maria", "password": "…", "device_name": "Pixel 8", "platform": "android" }
```

The answer is the same as pairing's below (`token`, `device`, `server`, `user`). `401` wrong username or password, `429` too many attempts (`Retry-After` seconds; shared with the web page's sign-in), `409` accounts are turned off — offer pairing. Don't keep the password: the token is the credential from here on.

### Pair

The user opens **Settings → Apps → Pair a phone** on the web page, which shows a QR code and an 8-character code.

- **QR payload:** `downtify://pair?url=<base URL>&sid=<server_id>&code=<code>`. Use `url` as the base address (it's the address the user's browser used — prefer it over the discovered one when both exist) and check `sid` against `/api/server/info`.
- **Typed code:** `XXXX-XXXX`; send it as typed (case, spaces and dashes are normalised by the server).

```http
POST /api/auth/pair
Content-Type: application/json

{ "code": "K7QM-2XPD", "device_name": "Pixel 8", "platform": "android" }
```

```json
{
  "token": "dtfy_8uz4d35zjpn2_<secret>",
  "device": { "id": "8uz4d35zjpn2", "name": "Pixel 8" },
  "server": { "server_id": "cf12b3c4…", "name": "nas" },
  "user": { "username": "maria", "role": "user" }
}
```

- `401` wrong/expired/used code, `429` too many attempts (`Retry-After` seconds).

### Keep the token

- Store the token in the Android Keystore-backed storage (EncryptedSharedPreferences / Jetpack DataStore + Tink); it's shown once and can't be retrieved again.
- Send it on **every** request as `Authorization: Bearer <token>`. `require_sign_in` is `false` only on a server with accounts turned off (`DOWNTIFY_DISABLE_AUTH`) or an older one — send the token anyway: it lets the server tell the app when it was unpaired.
- The device belongs to the user who signed in or showed the code (`user` in the response: `{ "username", "role" }`); `GET /api/me` answers who that is. Show it in the app ("Signed in as maria").
- `GET /api/auth/status` with the token answers `{ "signed_in": true, "via": "device", "user": { "username", "role", … }, "device": { "id", "name" }, … }` — a cheap "am I still paired?" check.

**Unpaired / revoked:** any request answers `401` with `{"detail": "Invalid or revoked token"}` and the WebSocket closes with code `4401`. Drop the token and send the user back to sign in.

**What a device may do:** everything below, plus the web API's read endpoints, searching and previews (`/api/songs/search`, `/api/url/resolve`, `/api/preview`), where to buy a song to support the artist (`/api/buy`, see [Support the Artist](features/support-artists.md)), asking the server to download (`POST /api/download/url|batch|album`), likes, listens and podcast episode playback/downloads. Settings, credentials, deleting files and managing devices answer `403` for a device. Searching, previews, streaming and asking the server to download are shared: a track anyone downloaded can be played and then claimed by downloading it. The library feed, playlists, likes and the queue hold the paired account’s own entries (everything, on an admin’s device). An account being deleted, or its owner choosing **Sign out everywhere**, unpairs the device (`401`).

## 4. Sync the library

```http
GET /api/v1/library?since=<cursor>
```

```json
{
  "cursor": 1742,
  "full": false,
  "tracks": [
    {
      "id": "t7b255c87668ba03b",
      "file": "Portishead - Roads.flac",
      "title": "Roads", "artist": "Portishead", "artists": ["Portishead"],
      "album": "Dummy", "album_artist": "Portishead",
      "album_id": "6aa1df0c3e5f2b11", "artist_id": "0a92c1e0bb3d8f44",
      "track_number": 3, "year": "1994", "duration": 305.12,
      "codec": "flac", "bitrate": 912000, "sample_rate": 44100, "channels": 2,
      "size": 34812211, "added": 1789600669, "has_cover": true, "explicit": true, "playlists": ["Trip-hop"]
    }
  ],
  "deleted": ["t0c4…"]
}
```

- First launch: `since=0` → `full: true`, `tracks` is the whole library.
- Later: `since=<last cursor>` → only tracks added or changed since, and ids of removed ones. Save `cursor` only after applying the response.
- **`full: true` at any time** (a cursor too old — removed tracks are remembered for 90 days — or one the server doesn't recognise) means: replace the local library with `tracks`.
- **`id`** is stable across moves and renames of the file (see `downtify/library_sync.py` for the exact rules); a file moved *and* re-tagged in the same sweep comes back as a new id plus a deleted old one. Key everything local (offline files, likes, queue, history) by `id`, never by `file`.
- **`explicit`** is `true` on a track whose file is marked explicit and **absent** on every other track: read absent as `false`. Show it like the web app does, a small "E" next to the title (see [Explicit Marker](features/explicit-marker.md)).
- **Grouping:** albums group by `album_id` (album artist + album title, case-insensitive; `""` = no album), artists by `artist_id` (the album artist). This is exactly the web app's grouping.
- `ETag`/`If-None-Match` are supported (`304` when nothing changed for that `since`).
- `refresh=true` rescans the folder now (pull to refresh) — otherwise the scan behind the list is cached for about a minute.
- When the server says the library changed (WebSocket `library_changed`, below), sync again.
- **Whose library:** the library is shared, so the feed holds every track except what an admin [hid from users](features/users.md#hiding-from-users) (an admin’s device gets everything). A track that becomes hidden arrives as a removed id, and one shown again arrives as an ordinary row. Nothing below changes shape because of this. Podcast shows, episode progress, listens and the block list are per-account the same way; subscribing to a show works from the web page.

Other reads, all by track id:

| Endpoint | Returns |
|----------|---------|
| `GET /api/v1/tracks/{id}` | One track row |
| `GET /api/v1/tracks/{id}/lyrics` | `{ "synced": "<LRC>", "plain": "…" }` (either may be empty) |
| `GET /api/v1/tracks/{id}/loudness` | The track's [playback loudness profile](features/playback-normalization.md): `{ "state", "gain_db", "integrated_lufs", "true_peak_dbtp", "algorithm_version", "fingerprint", "source_etag", "source_size" }`. Apply `gain_db` only when `state` is `ready` and `algorithm_version` is `1`, capped at +12 dB and at `-1 - true_peak_dbtp`; anything else (`unanalysed`, `silent`, a `404` from an older server) means the original level. `source_etag` and `source_size` are the `ETag` and size of the original file's stream: bind the profile to an offline copy only when they match the download |
| `GET /api/v1/tracks/{id}/cover?size=150\|300\|600` | JPEG thumbnail; omit `size` for the full picture. `ETag` + `Cache-Control: private, max-age=604800` |
| `GET /api/v1/playlists` | `[{ "name", "liked", "manual", "count", "cover", "track_ids": [...], "owner", "visibility", "mine", "followed", "shared_with_me", "new", "hidden_count" }]` (`cover` is a path for `GET /playlist-cover?file=`, or `""`). Other people's shared or followed playlists are in here, view-only (`mine: false`): list them apart from the user's own, labelled with `owner` |
| `GET /api/v1/usernames` | `{ "enabled", "usernames": [...] }` — who a playlist can be shared with |
| `POST` / `DELETE /api/v1/playlists/follow` | Body (or `?name=`) `{ "name" }` — follow a public playlist, or stop |
| `POST /api/v1/playlists/seen` | Body `{ "name" }` — clear the `new` marker of a playlist shared with the user |
| `GET /api/v1/playlists/hidden?name=` | `{ "name", "songs": [{ "key", "label", "track_id", "hidden_at" }] }` — the songs the user hid from an imported playlist of theirs (`track_id` is `""` once the file is gone) |
| `POST /api/v1/playlists/hidden` | Body `{ "name", "hide": [track_ids], "show": [keys] }` — hide tracks from an imported playlist of the user's (they stay out when its watch or link brings them back; the tracks stay in the library), or show hidden ones again. Answers `{ "name", "hidden", "keys", "shown", "restored", "count", "track_ids" }`; send `keys` as `show` to undo. Offer it on `mine` playlists that aren't `manual` or `liked` (`409` otherwise). See [Hidden playlist songs](features/hidden-playlist-songs.md) |
| `GET /api/v1/likes` | `{ "track_ids": [...] }`, newest first |
| `PUT /api/v1/likes` | Body `{ "track_id", "liked" }` — idempotent |

## 5. Stream and download

```http
GET /api/v1/tracks/{id}/stream                          # original file
GET /api/v1/tracks/{id}/stream?format=opus&bitrate=160  # transcoded (opus | aac | mp3; 96–320)
```

- Full **HTTP Range** support (`206`, `Content-Range`, `Accept-Ranges: bytes`), exact `Content-Length`, `Content-Type` (`audio/flac`, `audio/mpeg`, `audio/mp4`, `audio/ogg`). `HEAD` works too.
- `X-Downtify-Transcoded: opus/160` for a transcoded copy; `no` when the original was served because it already fits (lossy and not above the requested bitrate).
- A transcoded copy is made on the first request (the request waits — a few seconds for a song) and cached; after that it behaves like a file. Set a generous read timeout (≥ 60 s) for transcoded requests.
- **Offline copies:** the same URL, with `download=true` for a `Content-Disposition` filename. Resume interrupted downloads with `Range`. Use the size from `Content-Length` (or the track's `size` for originals) for storage planning.
- Media3: set the `Authorization` header on the `DataSource.Factory` (`DefaultHttpDataSource.Factory().setDefaultRequestProperties(...)`); cache with `CacheDataSource`.

## 6. Signed URLs (Cast and headerless players)

A Cast receiver fetches media itself and can't send the token. Ask the server for signed URLs:

```http
POST /api/v1/sign
Authorization: Bearer <token>

{ "items": [ { "path": "/api/v1/tracks/t7b2…/stream", "params": { "format": "aac", "bitrate": "256" } },
             { "path": "/api/v1/tracks/t7b2…/cover", "params": { "size": "600" } } ],
  "ttl": 3600 }
```

```json
{ "urls": ["/api/v1/tracks/t7b2…/stream?format=aac&bitrate=256&exp=1790479684&kid=8uz4d35zjpn2&sig=…", "…"],
  "expires_at": 1790479684 }
```

- Prepend the base address. Valid for `GET`/`HEAD` of exactly that path and those parameters, until `exp`, while the device stays paired. `ttl` 60 s – 24 h.
- Signable paths: `/api/v1/tracks/…`, `/downloads/…`, `/media/…`, `/cover`, `/playlist-cover`.
- CORS: responses allow any origin and expose `Accept-Ranges`, `Content-Length`, `Content-Range`, `ETag`, `X-Downtify-Transcoded`.
- The receiver must be able to reach the server's address (same network, or a public HTTPS address).

## 7. Live updates (WebSocket)

`WS {base}/api/ws?client_id=<uuid>` with the `Authorization` header on the handshake (OkHttp supports it). A client that can't send it gets a single-use, 60-second ticket from `POST /api/auth/ws-ticket` and connects with `&ticket=<ticket>`.

Messages the app can rely on:

| Message | When |
|---------|------|
| `{ "type": "library_changed" }` | Tracks were added, removed or moved (debounced ~2 s) — sync |
| `{ "type": "playlists_changed" }` | A playlist was shared, unshared, followed, copied, detached, renamed or deleted, or songs were hidden from it or shown again — refetch `GET /api/v1/playlists` |
| `{ "type": "likes", "count": 3 }` | Likes changed somewhere — refetch `GET /api/v1/likes` |
| `{ "type": "queue_reload" }` | Many downloads were queued at once — refetch `GET /api/queue` |
| `{ "song": {…}, "progress": 42.5, "status": "downloading"\|"done"\|"error", "message", "filename", "provider" }` | A server download's progress (no `type`) — one’s own jobs only (every job on an admin’s device) |
| `{ "type": "podcasts" }` / `{ "type": "podcast_progress", … }` | Podcast episodes downloaded / progress |
| `{ "type": "device_paired", … }` | A device was paired (for the web page; ignore) |

"The server is downloading N songs": `GET /api/queue` (count rows with `status` `queued` or `downloading`), kept fresh by the progress messages. A waiting row carries `position` (1-based place in the queue, `null` once finished) and `user_ids` (every account waiting on that job — one shared row when two accounts ask for the same track at once). Close code `4401` = unpaired.

## 8. Report plays

```http
POST /api/discover/listens

{ "track_id": "t7b2…", "play_id": "<uuid per play>", "played_at": "2026-09-27T10:00:00Z" }
```

- Report once per play, after half the track (or 4 minutes) has played — the web player's rule.
- `play_id` makes retries safe (the same play counts once); `played_at` lets an app report plays made offline later (a future time counts as now). Queue reports while offline and send them when back.

**What's playing now** (the admins' Activity page, like Jellyfin's dashboard) — separate from counting listens:

```http
POST /api/activity/playback

{ "player": "<install id>", "state": "playing", "track": { "track_id": "t7b2…", "title": "Roads", "artist": "Portishead", "album": "Dummy", "duration": 305 }, "position": 42 }
```

- Send it when a song starts, on pause/resume (`state: "paused"`/`"playing"`), on stop (`"stopped"`, `track` may be `{}`), and about every 30 s while playing. Only while online; don't queue these.
- `player` is any id stable for this install. The app shows up by its device name.

Podcast episodes: `PUT /api/podcasts/episodes/{id}/playback` with `{ "position_seconds", "played" }` (see the API reference), roughly every 10 s while playing and on pause.

## Error handling summary

| Status | Meaning |
|--------|---------|
| `401` | No/invalid/revoked credentials — re-pair (or sign in) |
| `403` | Signed in, but this needs the web page (admin) |
| `404` | Unknown track id or missing file — resync |
| `429` | Rate-limited (pairing) — wait `Retry-After` seconds |
| `499` | The server stopped a transcode because the client disconnected (you won't normally see it) |
| `501` | Transcoding requested but the server has no ffmpeg — use `format=original` |

## Library-only policy

`GET /api/server/info` includes the optional boolean `library_only` (default false). Current clients retain it per paired server and react to `music_policy_changed` by refreshing server info. When true, use library search and local file identities, suppress external results, previews, prefetches and streams, and remove stream-only queue entries. The server refuses external music endpoints with HTTP 409. See [Library-only mode](features/library-only.md).

## Music trash (admins)

When the server has the [music trash](features/music-trash.md) on, an admin's device can move songs to it, restore them and let expired ones be downloaded again — the same endpoints as the web app, under `/api/v1/library/trash` (see [Music trash](api-reference.md#music-trash)):

- Ask `GET /api/v1/library/trash/capabilities` for each pairing, and again when the account may have changed. Offer the trash only while `can_manage` is `true`; a `404` (older server) or any error means it's off. Every request is authorised again on the server: a `403` (`admin_required`) means the account is no longer an admin — hide the trash.
- Moving takes three steps: `POST …/preview` with `{ "track_ids": [...] }` (library ids, up to 200), poll `GET …/preview/{request_id}` about once a second until `state` is `ready`, show its `items` (title, format, path) for the user to confirm, then `POST …/confirm` with its `confirmation` (good for 10 minutes). The confirmation answers before anything has moved: show the song as waiting, not as gone.
- Confirmed songs leave the library feed as removed ids (`deleted` in `GET /api/v1/library`); a restored song comes back with **the same `id`**, so likes, playlists, queue entries and offline files keyed by id find it again. Don't drop the user's queue or offline files before the first successful sync of a session: an id is gone only when a sync says so.
- Show `detail.code` from a `409` as a message (the codes are listed in the API reference) and treat an unknown code as "not done, nothing deleted".
