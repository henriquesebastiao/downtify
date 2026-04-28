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

It resolves track metadata directly from Spotify's public embed pages, finds the best audio match on YouTube Music, downloads it with `yt-dlp`, converts it with `ffmpeg`, and embeds album art + all metadata with `mutagen`. The entire pipeline runs inside a single Docker container.

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

---

## 🚀 Quick Start

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/downloads:/downloads \
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
    restart: unless-stopped
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
2. **Audio match** — [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) searches YouTube Music for the track and picks the best result by comparing audio duration. Free-text searches skip the Spotify step entirely.
3. **Download & tag** — [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) downloads the audio and `ffmpeg` converts it to your chosen format. [`mutagen`](https://mutagen.readthedocs.io/) embeds title, artist, album, year and cover art into the file.

---

## 👁️ Playlist Monitor

The **Playlist Monitor** lets Downtify watch your favorite Spotify playlists and automatically download any new songs added to them — hands-free.

**How to use it:**

1. Click the eye icon (👁) in the navigation bar
2. Paste a Spotify playlist URL
3. Choose how often Downtify should check for new tracks (every 15 min up to once a day)
4. Click **Watch**

From that point on, whenever a new song appears in the playlist on Spotify, Downtify will detect and download it on the next scheduled check. Tracks that were already in the playlist when you added it are skipped — only *new* additions are downloaded.

You can pause, resume, force an immediate check, or stop monitoring any playlist at any time from the same page.

---

## 🎛️ Download Settings

Access the settings panel (⚙️ icon) to configure:

| Setting | Options |
|---------|---------|
| **Output format** | MP3 · FLAC · M4A · OGG · OPUS |
| **Bitrate** | 128 · 192 · 256 · 320 kbps (ignored for FLAC) |
| **Audio provider** | YouTube Music |

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

Downtify writes a standard `EXTM3U` file alongside your audio whenever a playlist gets downloaded — both for **manual** playlist paste-downloads and for **Playlist Monitor** sweeps that fetched at least one new track:

```
<downloads>/Playlists/<playlist-name>.m3u
```

The behaviour is governed by a single toggle in **Settings → Playlists → Generate M3U file for playlists** (on by default). Flip it off if you'd rather not produce M3Us at all; the rest of the download flow is unchanged.

Tracks that failed to download or had no YouTube Music match are skipped (and logged). The M3U is regenerated fresh on every run, so re-pasting the same playlist URL — or letting the Monitor add new tracks over time — always produces a complete, in-order file.

Track paths inside the M3U are written **relative to the M3U file itself**, so the same file works whether it's read from inside Downtify (where the library is mounted at `/downloads`) or from another consumer that mounts the same library at a different root — e.g. Jellyfin under `/nas/music`. Just point your media server at the same library mount and the playlist will appear as a single unit instead of a pile of loose files.

---

> [!WARNING]
> Users are responsible for their actions and any legal consequences. Downtify does not support unauthorized downloading of copyrighted material and takes no responsibility for user actions.

---

## 🤝 Contributing

Contributions, issues and feature requests are welcome!
Check the [issues page](https://github.com/henriquesebastiao/downtify/issues) or open a pull request.

If Downtify has been useful to you, consider leaving a ⭐ — it helps the project grow and reach more people!

---

## 📄 License

Licensed under the [GPL-3.0](https://github.com/henriquesebastiao/downtify?tab=GPL-3.0-1-ov-file#readme) License.
