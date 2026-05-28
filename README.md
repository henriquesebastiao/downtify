<h1 align="center">
  <a href="https://github.com/henriquesebastiao/downtify" target="_blank" rel="noopener noreferrer">
    <picture>
      <img width="80" src="https://github.com/user-attachments/assets/628d4334-7326-446e-9f2a-4d3ab4fc95c3">
    </picture>
  </a>
  <br>
  Downtify
</h1>

<p align="center">
  <strong>Self-hosted music downloader. Paste a Spotify link, get a perfectly tagged audio file — no API keys, no account, no hassle.</strong>
</p>

<div align="center">

[![Test](https://github.com/henriquesebastiao/downtify/actions/workflows/test.yml/badge.svg)](https://github.com/henriquesebastiao/downtify/actions/workflows/test.yml)
[![GitHub Release](https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=blue)](https://github.com/henriquesebastiao/downtify/releases)
[![GitHub License](https://img.shields.io/github/license/henriquesebastiao/downtify?color=blue)](/LICENSE)
[![Docker Pulls](https://img.shields.io/docker/pulls/henriquesebastiao/downtify?color=blue)](https://hub.docker.com/r/henriquesebastiao/downtify)
[![Visitors](https://api.visitorbadge.io/api/visitors?path=henriquesebastiao%2Fdowntify&label=repository%20visits&countColor=%231182c3&style=flat)](https://github.com/henriquesebastiao/downtify)

</div>

https://github.com/user-attachments/assets/9711efe8-a960-4e1a-8d55-e0d1c20208f7

---

## ✨ What is Downtify?

Downtify is a **self-hosted web app** that downloads music from Spotify — without touching the Spotify API, without needing an account, and without any Premium subscription. Just drop a link and get a fully-tagged audio file.

It resolves track metadata from Spotify's public embed pages, then tries your configured **audio sources** (Soulseek via **slskd**, YouTube Music, or YouTube). Downloads are tagged with `mutagen`, indexed so playlists are not re-fetched, and can export **M3U** playlists or sync into **Navidrome**. The app runs in a single Docker container.

---

## 🚀 Features

| Feature | Details |
|---------|---------|
| 🎵 **Tracks, albums & playlists** | Any Spotify link works — single track, full album, or entire playlist |
| 👁️ **Playlist Monitor** | Watch playlists and **auto-download new songs** as they are added to Spotify |
| 🎨 **Rich metadata** | Album art, title, artist, album, year — all embedded in every file |
| 🎚️ **Multiple formats** | MP3 · FLAC · M4A · OGG · OPUS |
| 🔎 **Free-text search** | Search YouTube Music directly — no Spotify link needed |
| 🔑 **Zero credentials** | No Spotify API key, no account, no Premium required |
| 🔔 **Real-time progress** | Live download progress via WebSocket — no page reload needed |
| 🐳 **One Docker command** | Up and running in under a minute |
| 🏠 **Home server platforms** | Available on Umbrel, CasaOS and HomeDock |
| 🎧 **Built-in player** | Play your downloaded music straight from the web UI — progress bar, shuffle, repeat, volume |
| 🌐 **slskd (Soulseek)** | Optional first provider via [slskd](https://github.com/slskd/slskd) — leave files in place, real download progress |
| 🎵 **Navidrome playlists** | Sync Spotify playlists into Navidrome after download (Subsonic API, same idea as Explo) |
| 📚 **Library browser** | Lists `/downloads` and `/slskd` with tags from embedded metadata (not just filenames) |
| 🔁 **Skip re-downloads** | Global Spotify track index remembers what you already have on disk |
| 🌍 **Multi-language UI** | English (default), Spanish and Brazilian Portuguese — easy to add more |

---

## 📋 Recent changes (2.7.x)

Summary of the slskd + Navidrome integration work:

| Area | Change |
|------|--------|
| **slskd provider** | Search Soulseek, poll transfers, optional leave-in-place under `/slskd`, timeouts and YouTube fallback |
| **Provider order** | Settings UI to enable and order slskd / YouTube Music / YouTube |
| **Track index** | Spotify track ID → file path; skips re-downloads for playlists and monitor |
| **Library paths** | Resolves `slskd/…` entries to `/slskd` for M3U, player, and Navidrome matching |
| **M3U** | Absolute paths (`/downloads/…`, `/slskd/…`) for media servers |
| **Navidrome** | Scan → match → **update same playlist** (no duplicate playlists on each sync) |
| **Playlist monitor** | Regenerates M3U and can sync Navidrome after new tracks |
| **Player / library** | Tag-based metadata; plays slskd files via `/media/slskd/` |

Configure everything under **Settings** (⚙️): Audio sources, slskd block, Playlists (M3U + Navidrome), and File organization.

---

## 🚀 Quick Start

**Published image (this fork, 2.7.9):** `dx616b/spoti-to-navidrome:2.7.9` (also tagged `:latest` on Docker Hub).

```bash
docker run -d -p 8000:30321 --name downtify \
  -e DOWNTIFY_PORT=30321 \
  -v /path/to/music/downloads:/downloads \
  -v /path/to/music/slskd:/slskd \
  -v downtify_data:/data \
  dx616b/spoti-to-navidrome:2.7.9
```

Open [http://localhost:8000](http://localhost:8000), paste a Spotify link, and hit download.

> Change host paths to your library folders. Omit the `/slskd` mount if you only use YouTube.

### Docker Compose

Copy the example file and start:

```bash
cp docker-compose.example.yml docker-compose.yml
# Edit ./docker-compose.yml — set your host paths for downloads and slskd
docker compose pull
docker compose up -d
```

See [`docker-compose.example.yml`](docker-compose.example.yml) for a ready-made stack using `dx616b/spoti-to-navidrome:2.7.9`.

Minimal setup (YouTube / YouTube Music only):

```yaml
services:
  downtify:
    container_name: downtify
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped

volumes:
  downtify_data:
```

With **slskd** and a separate Soulseek library folder (recommended for Navidrome + leave-in-place):

```yaml
services:
  downtify:
    container_name: downtify
    image: dx616b/spoti-to-navidrome:2.7.9
    ports:
      - '8000:30321'
    environment:
      - DOWNTIFY_PORT=30321
    volumes:
      - /path/to/music/downloads:/downloads
      - /path/to/music/slskd:/slskd      # same folder slskd writes to
      - downtify_data:/data
    restart: unless-stopped

volumes:
  downtify_data:
```

Upstream image (no slskd fork): `ghcr.io/henriquesebastiao/downtify:latest`.

> **Paths inside the container** are what you configure in the UI (`/downloads`, `/slskd`). Map host folders to those mount points. Navidrome must scan the **same** host folders.

Need a custom port? Use the `DOWNTIFY_PORT` environment variable:

```yaml
ports:
  - '8000:30321'
environment:
  - DOWNTIFY_PORT=30321
```

---

## 🏠 One-Click Install on Home Servers

| Platform | Link |
|----------|------|
| ☂️ Umbrel | [Install on Umbrel](https://apps.umbrel.com/app/downtify) |
| 🏠 CasaOS | [Install on CasaOS](https://casaos.zimaspace.com/) |
| ⚓ HomeDock OS | [Install on HomeDock](https://www.homedock.cloud/apps/downtify/) |

---

## ⚙️ How It Works

Downtify resolves **metadata** from Spotify embed pages, then tries **audio providers** in the order you set in Settings until one succeeds:

```
Spotify embed  →  Provider chain (slskd → YouTube Music → …)  →  Tag & register
  (metadata)         (find audio on disk or download)              (mutagen + index)
```

1. **Metadata** — Track, album and playlist links use the public `open.spotify.com/embed` pages. No Spotify API key or Premium account is required. Sparse playlist embeds are enriched from per-track Spotify data when needed.
2. **Audio providers** — You choose the order (see [Audio sources](#-audio-sources-slskd--youtube)). **slskd** searches Soulseek and waits for a transfer into your library folder. **YouTube Music** / **YouTube** use [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) and [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) with an optional yt-dlp search fallback when YT Music finds nothing.
3. **Tag & dedupe** — [`mutagen`](https://mutagen.readthedocs.io/) embeds title, artist, album, year and cover art. A local **track index** (`/data`) maps Spotify track IDs to on-disk paths so playlists and the monitor do not re-download songs you already have.
4. **Playlists (optional)** — **M3U** files for media servers and/or a **Navidrome** playlist sync via the Subsonic API (scan library → match tracks → update playlist in place).

---

## 👁️ Playlist Monitor

The **Playlist Monitor** lets Downtify watch your favorite Spotify playlists and automatically download any new songs added to them — hands-free.

**How to use it:**

1. Click the eye icon (👁) in the navigation bar
2. Paste a Spotify playlist URL
3. Choose how often Downtify should check for new tracks (every 15 min up to once a day)
4. Click **Watch**

From that point on, whenever a new song appears in the playlist on Spotify, Downtify will detect and download it on the next scheduled check. Tracks that were already in the playlist when you added it are skipped — only *new* additions are downloaded. Songs already on disk (including under `/slskd` from an earlier slskd download) are linked via the track index instead of being fetched again.

After a successful sweep, the monitor can **regenerate the M3U** and **sync Navidrome** (when those options are enabled in Settings), same as a manual playlist download.

You can pause, resume, force an immediate check, or stop monitoring any playlist at any time from the same page.

---

## 🎛️ Download Settings

Open the settings panel (⚙️ icon). Settings are stored under `/data` in the container and survive restarts.

| Setting | Options / notes |
|---------|-----------------|
| **Audio sources** | Ordered list: **slskd**, **YouTube Music**, **YouTube** (see below) |
| **Output format** | MP3 · FLAC · M4A · OGG · OPUS |
| **Bitrate** | 128 · 192 · 256 · 320 kbps (ignored for FLAC) |
| **Organize by artist** | Off (default) · On |
| **Generate M3U** | On by default for playlist downloads / monitor |
| **Sync Navidrome** | Create or update a Navidrome playlist after Spotify playlist jobs |
| **Parallel downloads** | How many tracks download at once (default 3) |
| **Lyrics** | Optional LRCLIB / Genius / etc. |

---

## 🔊 Audio sources (slskd + YouTube)

In **Settings → Audio sources**, pick one or more providers and drag them into priority order. Downtify tries each provider until audio is found.

| Provider | Role |
|----------|------|
| **slskd** | Search Soulseek via your [slskd](https://github.com/slskd/slskd) instance; files land in `source_dir` (usually `/slskd`). Best quality when peers have the track. |
| **YouTube Music** | Default fallback; uses YT Music search + yt-dlp download into `/downloads` (or playlist subfolder). |
| **YouTube** | Plain YouTube search via yt-dlp (also used as a last-resort search if YT Music fails). |

**Recommended order for a Soulseek + Navidrome setup:** `slskd` → `YouTube Music` (and optionally `YouTube`).

If **slskd** is enabled but nothing is queued within **queued timeout** (default 180s), or the transfer exceeds **download timeout** (default 600s), Downtify automatically tries the next provider.

---

## 🌐 slskd (Soulseek via slskd)

### Requirements

- A running **slskd** instance with API access (base URL + API key from slskd’s web UI).
- The same music folder visible to Downtify and (if used) Navidrome.

### Settings → slskd

| Field | Typical value | Meaning |
|-------|----------------|---------|
| **Enable slskd** | On | Turns the provider on (must also appear in Audio sources). |
| **Base URL** | `http://slskd:5030` | slskd API URL **as Downtify sees it** (Docker service name or host:port). |
| **API key** | *(from slskd)* | Required when enabled. |
| **slskd folder path in Downtify** | `/slskd` | Where finished Soulseek files appear **inside the Downtify container** — not the host path. |
| **Leave slskd files in place** | On (recommended) | Do not copy into `/downloads`; tag in place and register `slskd/…` paths in the library index. |
| **Download timeout** | `600` | Max seconds to wait for an slskd transfer. |
| **Queued timeout** | `180` | Max seconds stuck in slskd’s queue before falling back to YouTube. |

### Docker volumes example

```text
Host                          Downtify container
/path/to/music/downloads  →   /downloads
/path/to/music/slskd      →   /slskd        ← slskd must write here too
```

If slskd runs in another container, mount the **same host directory** on both containers, e.g. `- /mnt/music/slskd:/slskd` on each.

### Behaviour

- Downtify searches slskd, enqueues a download, and polls until the file exists under `source_dir` (or times out).
- With **leave in place**, the stored library path looks like `slskd/Album Name/track.mp3` and the built-in player serves it from `/media/slskd/…`.
- Without leave in place, files are copied into `/downloads` like a normal YouTube download.

---

## 🎵 Navidrome playlist sync

Downtify can mirror a downloaded Spotify playlist into **Navidrome** using the Subsonic API (same approach as tools like Explo).

### What it does

1. After playlist tracks finish downloading, Downtify calls Navidrome **`startScan`** (incremental library scan).
2. Waits for the scan to finish (configurable; scales with playlist size).
3. Searches the Navidrome library for each track (title, artist, tags from files, and path).
4. **Updates the existing Navidrome playlist** with the same name when possible (no duplicate playlists). Old duplicate playlists from earlier versions can be deleted manually once.

### Settings → Navidrome

| Field | Notes |
|-------|--------|
| **Enable Navidrome sync** | Master toggle (also enable **Create playlist in Navidrome** under Playlists). |
| **URL** | e.g. `https://music.example.com` |
| **Username / password** | Navidrome user that should **own** the playlists. |
| **Admin username / password** | Optional — only needed if your main user is **not** an admin. If your account is already admin, leave admin fields **empty**; one login is enough. |
| **Public playlist** | Whether the Navidrome playlist is public. |

Scan timing uses defaults in settings storage: **scan after download** (on), wait up to **120s** base (+ extra time for large playlists), **5s** poll interval, and a **15s** retry pass for tracks that were not indexed yet.

### Navidrome server setup

1. In Navidrome **Settings → Music Library**, include every folder Downtify writes to, e.g. both `/downloads` and `/slskd` (or the host paths you mapped to those mounts).
2. Use the **same** Navidrome user in Downtify that should own synced playlists.
3. After upgrading, run one full playlist download or a monitor sweep to refresh the playlist.

If sync reports `matched=46/55`, the missing tracks are usually **not scanned yet** in Navidrome, live outside configured music folders, or could not be matched by search — check Downtify logs for `not in library index`.

---

### 📁 Organize by artist

When **Settings → File organization → Organize by artist** is enabled, every downloaded track is saved inside a subfolder named after the track's primary artist:

```
<downloads>/
  Arctic Monkeys/
    Arctic Monkeys - Do I Wanna Know.mp3
    Arctic Monkeys - R U Mine.mp3
  Tame Impala/
    Tame Impala - The Less I Know The Better.mp3
```

This applies to **all** downloads — single tracks, albums and playlists alike. Playlist tracks are saved in their artist's folder instead of a playlist folder, which makes the library compatible with media apps (like Jellyfin, Navidrome, Plex and Beets) that expect an `Artist/Song.ext` folder structure.

When the setting is **off** (default), the existing behaviour is preserved: single tracks go directly into the root of the downloads folder, and playlist tracks go into a per-playlist subfolder.

> **M3U files and playlists** — If you download a Spotify playlist with both *Organize by artist* and *Generate M3U* enabled, the M3U file is placed in `<downloads>/Playlists/<playlist-name>.m3u` (rather than inside the playlist subfolder) because the tracks are now spread across multiple artist folders.

---

## 📦 What Spotify links are supported?

| Link type | Supported |
|-----------|-----------|
| Spotify track | ✅ |
| Spotify album | ✅ |
| Spotify playlist | ✅ |
| YouTube Music search (free text) | ✅ |
| Direct YouTube link | ✅ |

---

## 📃 M3U playlist export

Downtify writes a standard `EXTM3U` file whenever a playlist download (or monitor sweep) keeps at least one track on disk.

**Default location** (organize by artist **off**):

```text
<downloads>/<playlist-name>/<playlist-name>.m3u
```

**With organize by artist on**:

```text
<downloads>/Playlists/<playlist-name>.m3u
```

Toggle: **Settings → Playlists → Generate M3U file for playlists** (on by default).

Tracks that are not on disk are skipped and logged. The file is rebuilt on each run so order matches the Spotify playlist.

**Paths inside the M3U** are the **absolute paths where Downtify found each file** on disk, for example:

```text
/downloads/Robot Heart/Artist - Title.mp3
/slskd/Some Album/01 - Track.mp3
```

Use the same volume mounts in Jellyfin, Navidrome, or other tools (`/downloads` and `/slskd` in the container map to your host library). Entries under `slskd/…` resolve to `/slskd/…` inside the container even when the M3U file lives under `/downloads`.

---

> [!WARNING]
> Users are responsible for their actions and any legal consequences. Downtify does not support unauthorized downloading of copyrighted material and takes no responsibility for user actions.

---

## 🎧 Built-in Player

Downtify ships with a clean web player so you don't need a separate app to listen to what you've downloaded. Open the headphones icon (🎧) in the navigation bar — or hit the play button next to any file in the **Library** — and Downtify will load audio from `/downloads` and `/slskd` into a queue.

**What's included:**

- Big now-playing card with embedded **album art** and a progress bar (click or drag to seek)
- Play / pause / previous / next
- **Shuffle** with a stable random order across the whole queue
- **Repeat** modes: off → all → one
- Volume slider with mute toggle (volume is remembered between sessions)
- Side queue listing every track in your library, each one with its own thumbnail and the currently playing one highlighted

The **Library** and **Player** read **embedded tags** (title, artist, album) via mutagen, with filename parsing as a fallback. slskd tracks under `slskd/…` are played through `/media/slskd/…` URLs. Cover art comes from tags when present. Playback uses the browser’s HTML5 audio element — no extra dependencies.

---

## 🌍 Internationalization

Downtify's UI is fully translatable. The default language is **English**, with **Spanish** and **Brazilian Portuguese** included out of the box. You can switch languages from **Settings → Language**; your choice is saved in the browser's `localStorage` and applied instantly without a reload.

### Contributing translations

Adding a new language is a small, three-step change — no build tooling beyond the existing Vite setup is required.

1. **Copy the English file as a starting point.** Locale files live in `frontend/src/i18n/locales/`. Each file exports a single object whose keys match the structure of `en.js` exactly. Pick an [IETF language tag](https://en.wikipedia.org/wiki/IETF_language_tag) for the file name (e.g. `fr.js`, `de.js`, `it.js`, `ja.js`, `pt-PT.js`).

   ```bash
   cp frontend/src/i18n/locales/en.js frontend/src/i18n/locales/fr.js
   ```

2. **Translate the values.** Keep the keys, the placeholder tokens (e.g. `{count}`, `{name}`, `{file}`) and the overall shape unchanged — only the strings on the right-hand side should change. Update the `language.name` field at the top of the file to the **native** name of the language ("Français", "Deutsch", "Italiano"…) — this is the label that appears in the language picker.

3. **Register the locale** in `frontend/src/i18n/index.js`:

   ```js
   import fr from './locales/fr.js'

   export const AVAILABLE_LOCALES = [
     { code: 'en', name: 'English', messages: en },
     { code: 'es', name: 'Español', messages: es },
     { code: 'pt-BR', name: 'Português (BR)', messages: ptBR },
     { code: 'fr', name: 'Français', messages: fr }, // new entry
   ]
   ```

That's it. Rebuild the frontend (`cd frontend && npm run build`) — your language will show up in **Settings → Language** automatically.

**Tips for translators:**

- Missing keys fall back to English, so partial translations still ship. You can submit a PR with only the strings you're confident about.
- Placeholder tokens like `{count}` or `{file}` must be left as-is — they're substituted at runtime.
- Keep strings concise: the UI is laid out tightly and very long translations may wrap awkwardly. If you need to rephrase to fit, that's fine.
- After translating, run `npm run dev` from `frontend/` and click through every page in your language to spot anything that overflows or reads oddly in context.

Pull requests with new translations are very welcome — just open a PR against `main`.

---

## 🤝 Contributing

Contributions, issues and feature requests are welcome!
Check the [issues page](https://github.com/henriquesebastiao/downtify/issues) or open a pull request.

If Downtify has been useful to you, consider leaving a ⭐ — it helps the project grow and reach more people!

---

## 📄 License

Licensed under the [GPL-3.0](https://github.com/henriquesebastiao/downtify?tab=GPL-3.0-1-ov-file#readme) License.
