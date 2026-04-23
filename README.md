<h1 align="center">
  <a href="https://github.com/henriquesebastiao/downtify" target="_blank" rel="noopener noreferrer">
    <picture>
      <img width="80" src="https://github.com/user-attachments/assets/628d4334-7326-446e-9f2a-4d3ab4fc95c3">
    </picture>
  </a>
  <br>
  Downtify
</h1>

<p align="center">Download music from Spotify — no API keys, no account, no hassle. Just paste a link and go.</p>

<div align="center">
  
[![Test](https://github.com/henriquesebastiao/downtify/actions/workflows/test.yml/badge.svg)](https://github.com/henriquesebastiao/downtify/actions/workflows/test.yml)
[![GitHub Release](https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=blue
)](https://github.com/henriquesebastiao/downtify/releases)
[![GitHub License](https://img.shields.io/github/license/henriquesebastiao/downtify?color=blue
)](/LICENSE)
[![Visitors](https://api.visitorbadge.io/api/visitors?path=henriquesebastiao%2Fdowntify&label=repository%20visits&countColor=%231182c3&style=flat)](https://github.com/henriquesebastiao/downtify)
[![Docker Pulls](https://img.shields.io/docker/pulls/henriquesebastiao/downtify?color=blue
)](https://hub.docker.com/r/henriquesebastiao/downtify)
  
</div>

https://github.com/user-attachments/assets/9711efe8-a960-4e1a-8d55-e0d1c20208f7

## ✨ Why Downtify?

Paste a Spotify link, click download, done. No terminal. No API keys. No Spotify account. No Premium subscription.

Downtify fetches track metadata directly from Spotify's public embed pages, finds the best audio match on YouTube Music, and delivers a fully tagged file — album art, title, artist, album, and year all embedded — in whichever format you prefer.

- 🎵 **Tracks, albums & playlists** — any Spotify link works
- 🎨 **Rich metadata** — album art, title, artist, album and release year embedded in every file
- 🎚️ **Multiple formats** — MP3, FLAC, M4A, OGG and OPUS
- 🔑 **Zero credentials** — no Spotify API key, no account, no Premium required
- 🔔 **Desktop notifications** when your downloads are ready
- 🐳 **One Docker command** to get started
- 🏠 **Available on Umbrel, CasaOS and HomeDock** for one-click home server installs

## 🚀 Quick Start

Get Downtify running in under a minute:

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/downloads:/downloads \
  ghcr.io/henriquesebastiao/downtify
```

Then open http://localhost:8000, paste a Spotify link, and hit download.

> Change `/path/to/downloads` to wherever you want your music saved.

### 🐳 Docker Compose

```yaml
services:
  downtify:
    container_name: downtify
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
```

Need a custom port? Use the `DOWNTIFY_PORT` environment variable:

```yaml
ports:
  - '8000:30321'
environment:
  - DOWNTIFY_PORT=30321
```

## 🏠 Available on Home Server Platforms

Downtify is one click away on popular self-hosted home server operating systems:

| Platform | Link |
| -------- | ---- |
| ☂️ Umbrel | [Install on Umbrel](https://apps.umbrel.com/app/downtify) |
| 🏠 CasaOS | [Install on CasaOS](https://casaos.zimaspace.com/) |
| ⚓ HomeDock OS | [Install on HomeDock](https://www.homedock.cloud/apps/downtify/) |

## ⚙️ How It Works

Downtify's pipeline has three stages — metadata, audio, and tagging:

1. **Metadata** — Spotify track, album and playlist links are resolved by reading the public `open.spotify.com/embed` pages. No Spotify account or API credentials are needed.
2. **Audio match** — [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) searches YouTube Music for the track and picks the best result by comparing audio duration. Free-text searches skip the Spotify step and go straight to YouTube Music.
3. **Download & tag** — [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) downloads the audio and `ffmpeg` converts it to your chosen format. [`mutagen`](https://mutagen.readthedocs.io/) then embeds title, artist, album, year and cover art directly into the file.

| What you paste | Supported? |
| -------------- | ---------- |
| Spotify track link | ✅ |
| Spotify album link | ✅ |
| Spotify playlist link | ✅ |
| Free-text search | ✅ |

| Output format | |
| ------------- | - |
| MP3 | ✅ |
| FLAC | ✅ |
| M4A | ✅ |
| OGG | ✅ |
| OPUS | ✅ |

> [!WARNING]
> Users are responsible for their actions and any legal consequences. We do not support unauthorized downloading of copyrighted material and take no responsibility for user actions.

## 🤝 Contributing

Contributions, issues and feature requests are welcome! Feel free to check the [issues page](https://github.com/henriquesebastiao/downtify/issues).

If Downtify has been useful to you, consider leaving a ⭐ — it helps the project grow!

## 📄 License

Licensed under the [GPL-3.0](https://github.com/henriquesebastiao/downtify?tab=GPL-3.0-1-ov-file#readme) License.
