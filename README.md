<h1 align="center">
  <a href="https://github.com/henriquesebastiao/downtify" target="_blank" rel="noopener noreferrer">
    <picture>
      <img width="80" src="https://github.com/user-attachments/assets/628d4334-7326-446e-9f2a-4d3ab4fc95c3">
    </picture>
  </a>
  <br>
  Downtify
</h1>

<p align="center">Web GUI for <a href="https://github.com/spotDL/spotify-downloader">spotDL</a>. Allows you to download music from Spotify along with album art, lyrics and metadata.</p>

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

Tired of clunky command-line tools to download your Spotify music? Downtify wraps the powerful [spotDL](https://github.com/spotDL/spotify-downloader) engine in a clean, intuitive web interface — so anyone can download their favorite tracks, albums, and playlists without touching a terminal.

- 🎵 Download any Spotify link — songs, albums, playlists, podcasts
- 🖼️ Embedded metadata — album art, track name, artist, album title and more
- 🔔 Desktop notifications when your downloads are ready
- 🐳 One Docker command to get started
- 🏠 Available on popular home server platforms like Umbrel, CasaOS and HomeDock

## 🚀 Quick Start

Get Downtify running in under a minute:

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/downloads:/downloads \
  ghcr.io/henriquesebastiao/downtify
```

Then open http://localhost:8000, paste a Spotify link, and hit download. That's it.

> 💡 Change /path/to/downloads to wherever you want your music saved.

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

Custom port? Use the DOWNTIFY_PORT environment variable:

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

## 🎧 How It Works

Downtify uses SpotDL under the hood, which sources audio from YouTube to avoid Spotify DRM restrictions. Spotify's API is used only to fetch track metadata — so your downloads are rich with accurate song info.

> [!WARNING]
> Users are responsible for their actions and any legal consequences. We do not support unauthorized downloading of copyrighted material and take no responsibility for user actions.

## 🤝 Contributing

Contributions, issues and feature requests are welcome! Feel free to check the [issues page](https://github.com/henriquesebastiao/downtify/issues).

If Downtify has been useful to you, consider leaving a ⭐ — it helps the project grow!

## 📄 License

Licensed under the [GPL-3.0](https://github.com/henriquesebastiao/downtify?tab=GPL-3.0-1-ov-file#readme) License.
