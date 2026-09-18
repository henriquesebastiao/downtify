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
[![Docker Pulls](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&style=flat&label=docker%20pulls)](https://github.com/henriquesebastiao/downtify/pkgs/container/downtify)
[![Visitors](https://api.visitorbadge.io/api/visitors?path=henriquesebastiao%2Fdowntify&label=repository%20visits&countColor=%231182c3&style=flat)](https://github.com/henriquesebastiao/downtify)

**[📚 Full documentation](https://henriquesebastiao.github.io/downtify/)**

</div>

https://github.com/user-attachments/assets/9711efe8-a960-4e1a-8d55-e0d1c20208f7

---

## ✨ What is Downtify?

Downtify is a **self-hosted web app** that downloads music from Spotify — without touching the Spotify API, without needing an account, and without any Premium subscription. Just drop a link and get a fully-tagged audio file.

It resolves track metadata directly from Spotify's public embed pages, finds the best audio match on YouTube Music, downloads it with `yt-dlp`, converts it with `ffmpeg`, and embeds album art + all metadata with `mutagen`. The entire pipeline runs inside a single Docker container.

---

## 🚀 Features

| Feature | Details |
|---------|---------|
| 🎵 **Tracks, albums & playlists** | Any Spotify link works — single track, full album, or entire playlist |
| 👁️ **Playlist & Artist Watch** | Watch Spotify or YouTube Music playlists **and artists** — new songs and new releases download automatically |
| 🎨 **Rich metadata** | Album art, title, artist, album, year — all embedded in every file |
| 📝 **Lyrics with fallback** | Plain and time-synced lyrics from LRCLIB and NetEase, tried in the order you choose — see **[Lyrics](https://henriquesebastiao.github.io/downtify/features/lyrics/)** |
| 🪄 **Upgrade library** | Scan music you already downloaded and repair small covers, missing lyrics and incomplete tags — see **[Upgrade library](https://henriquesebastiao.github.io/downtify/features/library-upgrade/)** |
| 🎚️ **Multiple formats** | MP3 · FLAC · M4A · OGG · OPUS |
| 🔎 **Free-text search** | Search YouTube Music directly — no Spotify link needed |
| 📥 **CSV library import** | Import a library export from Soundiiz, TuneMyMusic or Exportify and queue the whole thing |
| 🔑 **Zero credentials** | No Spotify API key, no account, no Premium required |
| 🔔 **Real-time progress** | Live download progress via WebSocket — no page reload needed |
| 🐳 **One Docker command** | Up and running in under a minute |
| 🏠 **Home server platforms** | Available on Umbrel, CasaOS and HomeDock |
| 🎧 **Built-in player** | Full-screen now playing with synced lyrics, an editable queue, sleep timer, keyboard shortcuts and lock-screen controls |
| 🎚️ **Equalizer** *(experimental)* | Ten-band equalizer with presets and a preamp in the full-screen player — see **[Equalizer](https://henriquesebastiao.github.io/downtify/features/player/#equalizer)** |
| 📚 **Library views** | Browse albums, artists, playlists and tracks in a grid or a list — sort, filter, multi-select, download as ZIP |
| 🌍 **Multi-language UI** | English (default) plus 7 more languages — easy to add more |
| 📱 **Installable (PWA)** | Add Downtify to your iOS or Android home screen — launches full-screen, no browser chrome |
| 🍪 **Cookie upload** | Upload a YouTube `cookies.txt` from the settings screen to download explicit/age-restricted tracks — no bind mounts, works on Windows |
| 🔔 **Update notifications** | Hourly check against GitHub Releases; a notice appears in the sidebar when a newer version is out |
| 🌗 **Responsive UI** | One layout from phone to widescreen, with light and dark themes |
| 🔗 **slskd & Navidrome** | Optionally download from Soulseek through your own slskd server, and mirror downloaded playlists into Navidrome, each with a **Test connection** button in Settings — see **[slskd & Navidrome](https://henriquesebastiao.github.io/downtify/features/slskd-navidrome/)** |

---

## 🚀 Quick Start

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/downloads:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Open [http://localhost:8000](http://localhost:8000), paste a Spotify link, and hit download.

> Change `/path/to/downloads` to wherever you want your music saved.

### Docker Compose

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

Downtify's download pipeline has three stages:

```
Spotify embed page  →  YouTube Music search  →  yt-dlp + ffmpeg + mutagen
   (metadata)             (audio match)            (download & tag)
```

1. **Metadata** — Track, album and playlist links are resolved by scraping the public `open.spotify.com/embed` pages. No Spotify credentials of any kind are required.
2. **Audio match** — [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) searches YouTube Music for the track and picks the best result by comparing audio duration. If YouTube Music has no good match (the song is missing, or only a different version such as a dubbed one), standard YouTube is searched automatically — see [How it works](https://henriquesebastiao.github.io/downtify/how-it-works/#fallback-to-standard-youtube). Free-text searches skip the Spotify step entirely.
3. **Download & tag** — [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) downloads the audio and `ffmpeg` converts it to your chosen format. [`mutagen`](https://mutagen.readthedocs.io/) embeds title, artist, album, year and cover art into the file.

---

## 👁️ Playlist Monitor

The **Playlist Monitor** lets Downtify watch your favorite Spotify and YouTube Music playlists — and the artists you follow — and automatically download new songs and new releases, hands-free.

**How to use it:**

1. Open **Monitor** from the sidebar (on phones: **More → Monitor**) and pick the **Playlists** or **Artists** tab
2. Paste a Spotify or YouTube Music playlist URL — or, on the Artists tab, an **artist** URL (Spotify, or YouTube Music such as `music.youtube.com/@artist`) to watch everything they release
3. Choose how often Downtify should check for new tracks (every 15 min up to once a month)
4. Click **Watch playlist** / **Watch artist**

Downtify downloads what's already there right away, then detects and downloads every new song on the scheduled checks.

Adding an **artist** works the same way: Downtify downloads their discography and then watches for new releases, so you don't need a dedicated playlist per artist. Each watch shows the link it follows and a **Spotify** or **YouTube Music** badge. You can filter the list, pause, resume, force an immediate check, **edit** a watch (including pointing it at a different playlist or artist), or stop it at any time.

YouTube Music playlists are handy for songs that aren't on Spotify: each track is downloaded from the exact video in the playlist.

Playlists checked daily or less often can be pinned to a specific hour (e.g. always sync overnight at 3 AM) with the `DOWNTIFY_MONITOR_SYNC_TIME` and `TZ` environment variables, and each tab can be sorted by date added, name, last check, frequency, or size. See **[Playlist Monitor](https://henriquesebastiao.github.io/downtify/features/playlist-monitor/)** in the full docs for details.

---

## 🎛️ Download Settings

Access the settings panel (⚙️ icon) to configure:

| Setting | Options |
|---------|---------|
| **Output format** | MP3 · FLAC · M4A · OGG · OPUS |
| **Bitrate** | 128 · 192 · 256 · 320 kbps (ignored for FLAC) |
| **Audio provider** | YouTube Music |
| **Organize by artist** | Off (default) · On |
| **Parallel downloads** | 1–30 concurrent downloads (default 3) |
| **Delay between downloads** | 0–300 seconds (default 0 = off) |
| **Download cover art** | On (default) · Off |
| **Cover art resolution** | 300–1200px (default 600) |
| **Overwrite existing files** | On (default) · Off |

**Delay between downloads** waits a configurable number of seconds between songs instead of firing requests back-to-back — combined with a lower **Parallel downloads** value, it's the main tool for avoiding YouTube rate limits on large unattended downloads.

**Cover art resolution** raises the size Downtify requests for YouTube Music-sourced cover art — handy if you feed your library into a media server like Plex that shows higher-resolution artwork than the 600px default. Turn **Download cover art** off entirely to skip fetching artwork — smaller, faster downloads.

Turn **Overwrite existing files** off to save bandwidth: a song that's already anywhere in your download folder (library root, another playlist's folder, an artist/album folder) isn't downloaded again. Useful when the same track is in several playlists or already in your library.

See **[Download Settings](https://henriquesebastiao.github.io/downtify/features/download-settings/)** for the full reference.

### 📁 Organize by artist

When **Settings → File organization → Organize by artist** is enabled, every downloaded track is saved inside a subfolder named after the track's primary artist:

```
<downloads>/
  The Night Owls/
    The Night Owls - Do I Still Recall.mp3
    The Night Owls - R U Awake.mp3
  Tame Impala/
    Tame Impala - The Less I Know The Better.mp3
```

This applies to **all** downloads — single tracks, albums and playlists alike. Playlist tracks are saved in their artist's folder instead of a playlist folder, which makes the library compatible with media apps (like Jellyfin, Navidrome, Plex and Beets) that expect an `Artist/Song.ext` folder structure.

When the setting is **off** (default), the existing behaviour is preserved: single tracks go directly into the root of the downloads folder, and playlist tracks go into a per-playlist subfolder.

> **M3U files and playlists** — If you download a Spotify playlist with both *Organize by artist* and *Generate M3U* enabled, the M3U file is placed in `<downloads>/Playlists/<playlist-name>.m3u` (rather than inside the playlist subfolder) because the tracks are now spread across multiple artist folders. The relative paths inside the M3U still resolve correctly regardless of where you mount the library.

---

## 📦 What Spotify links are supported?

| Link type | Supported |
|-----------|-----------|
| Spotify track | ✅ |
| Spotify album | ✅ |
| Spotify playlist | ✅ |
| YouTube Music playlist | ✅ |
| YouTube Music search (free text) | ✅ |
| Direct YouTube link | ✅ |

---

## 📥 Import a library CSV

Already exported your library from [Soundiiz](https://soundiiz.com/), [TuneMyMusic](https://www.tunemymusic.com/) or [Exportify](https://github.com/watsonbox/exportify)? Click **"Import a library CSV"** below the search box on the home page and pick the file — Downtify reads its Title/Artist columns and queues every track for download. See **[Library Import](https://henriquesebastiao.github.io/downtify/features/library-import/)** in the full docs for supported columns, limits, and rate-limiting tips.

---

## 📃 M3U playlist export

Downtify writes a standard `EXTM3U` file alongside your audio whenever a playlist gets downloaded — both for **manual** playlist paste-downloads and for **Playlist Monitor** sweeps that fetched at least one new track:

```
<downloads>/Playlists/<playlist-name>.m3u
```

The behaviour is governed by a single toggle in **Settings → Downloads & files → Write M3U playlists** (on by default). Flip it off if you'd rather not produce M3Us at all; the rest of the download flow is unchanged.

Right below it, **Save playlist cover art** (off by default) writes the playlist's own cover image next to its M3U, under the same name (`<playlist-name>.jpg`) — for Spotify and YouTube Music playlists alike, at the largest size the source offers. It's fetched **before the tracks**, so the folder looks like the playlist while it fills up, and Downtify shows that artwork for the playlist instead of a grid of its track covers. If you mirror playlists into Navidrome, it picks the file up on its own, with nothing extra to configure. See **[Playlist cover art](https://henriquesebastiao.github.io/downtify/features/playlist-cover-art/)**.

Tracks that failed to download or had no YouTube Music match are skipped (and logged). The M3U is regenerated fresh on every run, so re-pasting the same playlist URL — or letting the Monitor add new tracks over time — always produces a complete, in-order file.

Track paths inside the M3U are written **relative to the M3U file itself**, so the same file works whether it's read from inside Downtify (where the library is mounted at `/downloads`) or from another consumer that mounts the same library at a different root — e.g. Jellyfin under `/nas/music`. Just point your media server at the same library mount and the playlist will appear as a single unit instead of a pile of loose files.

---

> [!WARNING]
> Users are responsible for their actions and any legal consequences. Downtify does not support unauthorized downloading of copyrighted material and takes no responsibility for user actions.

---

## 🎧 Built-in Player

Downtify ships with a web player so you don't need a separate app to listen to what you've downloaded. Hit play on any album, artist, playlist or track in the **Library** and a player bar appears at the bottom of every page; open it for the full-screen **Now playing** view.

- **Now playing** with large cover art, seek bar, shuffle, repeat and volume
- **Synced lyrics** that follow the song — click a line to jump there
- **Up next** queue: play next, add to queue, drag to reorder, remove
- **Ten-band equalizer** with presets and a preamp
- **Sleep timer**, keyboard shortcuts (press `?`), and lock-screen / media-key controls
- Your queue and position are remembered between visits

The **Library** shows albums, artists and playlists as a grid or a list, plus a sortable track list with multi-select — play, queue, download as a ZIP or delete any selection. See **[Built-in Player](https://henriquesebastiao.github.io/downtify/features/player/)** and **[Library catalog](https://henriquesebastiao.github.io/downtify/features/library-catalog/)** in the full docs.

---

## 📱 Install as an App (PWA)

Downtify's web UI can be installed to your phone's home screen — on **iOS** (Safari: Share → Add to Home Screen) and **Android** (Chrome: ⋮ → Add to Home screen) — and launches full-screen with the Downtify icon, no browser address bar. See **[Install as an App](https://henriquesebastiao.github.io/downtify/features/pwa/)** in the full docs.

---

## 🌍 Internationalization

Downtify's UI is fully translatable. The default language is **English**, with **Spanish, Brazilian Portuguese, French, Turkish, Greek and Hungarian** included out of the box. You can switch languages from **Settings → Language**; your choice is saved in the browser's `localStorage` and applied instantly without a reload.

### Contributing translations

Adding a new language is a small, three-step change — no build tooling beyond the existing Vite setup is required.

1. **Copy the English file as a starting point.** Locale files live in `frontend/src/i18n/locales/`. Each file exports a single object whose keys match the structure of `en.js` exactly. Pick an [IETF language tag](https://en.wikipedia.org/wiki/IETF_language_tag) for the file name (e.g. `de.js`, `it.js`, `ja.js`, `pt-PT.js`).

   ```bash
   cp frontend/src/i18n/locales/en.js frontend/src/i18n/locales/de.js
   ```

2. **Translate the values.** Keep the keys, the placeholder tokens (e.g. `{count}`, `{name}`, `{file}`) and the overall shape unchanged — only the strings on the right-hand side should change. Update the `language.name` field at the top of the file to the **native** name of the language ("Français", "Deutsch", "Italiano"…) — this is the label that appears in the language picker.

3. **Register the locale** in `frontend/src/i18n/index.js`:

   ```js
   import de from './locales/de.js'

   export const AVAILABLE_LOCALES = [
     { code: 'en', name: 'English', messages: en },
     { code: 'es', name: 'Español', messages: es },
     { code: 'pt-BR', name: 'Português (BR)', messages: ptBR },
     { code: 'fr', name: 'Français', messages: fr },
     { code: 'tr', name: 'Türkçe', messages: tr },
     { code: 'el', name: 'Ελληνικά', messages: el },
     { code: 'hu', name: 'Magyar', messages: hu },
     { code: 'de', name: 'Deutsch', messages: de }, // new entry
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

## 🩹 Troubleshooting

Most download problems have the same root cause: **YouTube wants a signed-in session**. Upload a `cookies.txt` in **Settings (⚙️) → YouTube cookies** and they usually go away.

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| A song with **explicit content** won't download (`Sign in to confirm your age`) | YouTube only serves age-restricted tracks to a signed-in adult account | Upload a `cookies.txt` in **Settings → YouTube cookies** |
| Downloads fail, hang or say the format is unavailable | YouTube is challenging/rate-limiting the requests — common on a VPS or VPN | Upload a `cookies.txt`; then raise *Delay between downloads* and lower *Parallel downloads* in Settings; then try `DOWNTIFY_FORCE_IPV4=1`; then update the image |
| `DOWNTIFY_COOKIES_FILE` seems ignored (especially on **Windows / Docker Desktop**) | The variable needs a *container* path and a bind mount — a `C:\...` path never works | Skip the variable and upload the file in **Settings → YouTube cookies** instead |
| The cookie upload button is greyed out | `DOWNTIFY_COOKIES_FILE` is set, so the deployment owns that file | Unset the variable and recreate the container |
| Uploaded cookies / settings vanish after an update | `/data` isn't a persistent volume | Keep `- downtify_data:/data` in your compose file |
| Upload rejected as invalid | The file isn't a **Netscape** cookie jar (JSON, spreadsheet or a copied header) | Re-export with a cookies.txt browser extension, from a `youtube.com` tab |
| `Could not find a YouTube match for '…'` | Neither YouTube Music nor standard YouTube has a result that passes the title/artist/duration checks | Paste the right video's YouTube URL into the search bar to download it directly |
| A watched playlist re-downloads tracks you already have | The files are no longer in the downloads directory | Keep `/downloads` persistent; moving files *within* it is fine |

Cookies expire — if age-restricted downloads start failing again, export a fresh file and upload it as a replacement.

Full details, including how to export the file and what it contains: **[YouTube Cookies](https://henriquesebastiao.github.io/downtify/features/youtube-cookies/)** and **[Troubleshooting](https://henriquesebastiao.github.io/downtify/troubleshooting/)** in the docs.

---

## 🤝 Contributing

Contributions, issues and feature requests are welcome!
Check the [issues page](https://github.com/henriquesebastiao/downtify/issues) or open a pull request.

Before sending a pull request, please read [**CONTRIBUTING.md**](./CONTRIBUTING.md) — it covers local setup, the project's **coding and formatting standards** (Ruff for Python, Prettier for the frontend), testing requirements, commit conventions, and the PR checklist. All contributions are expected to follow those standards.

If Downtify has been useful to you, consider leaving a ⭐ — it helps the project grow and reach more people!

---

## 📄 License

Licensed under the [GPL-3.0](https://github.com/henriquesebastiao/downtify?tab=GPL-3.0-1-ov-file#readme) License.

Icons by [Font Awesome](https://fontawesome.com) (Free, [CC BY 4.0](https://fontawesome.com/license/free)), loaded via [Iconify](https://iconify.design).
