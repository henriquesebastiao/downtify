---
layout: home
title: Downtify
titleTemplate: Self-hosted music downloader
description: Self-hosted music downloader. Paste a Spotify link, get a perfectly tagged audio file — no API keys, no account, no hassle.
icon: lucide/house
hero:
  eyebrow: Self-hosted music downloader
  lead:
    - The music downloader you can host on your own box.
    - Drop a Spotify link, get a tagged audio file. No account, no API key, no Premium.
  actions:
    - text: Get started
      link: /getting-started/installation/
      primary: true
    - text: Source on GitHub
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Release
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Docker Pulls
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&style=flat&label=docker%20pulls
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: License
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
pipeline:
  - title: Spotify embed
    text: metadata
  - title: YouTube Music
    text: audio match
  - title: yt-dlp · ffmpeg · mutagen
    text: download & tag
highlights:
  - icon: eye
    title: Playlist Monitor
    text: Watches a playlist and quietly downloads new tracks as they're added.
    link: /features/playlist-monitor/
  - icon: sliders-horizontal
    title: Five formats
    text: MP3, FLAC, M4A, OGG and OPUS — at the bitrate of your choice.
    link: /features/download-settings/
  - icon: mic-vocal
    title: Lyrics built-in
    text: Plain and time-synced lyrics fetched from lrclib and embedded in the file.
    link: /features/lyrics/
  - icon: headphones
    title: Web player
    text: Shuffle, repeat, volume and album art — straight from the browser.
    link: /features/player/
  - icon: list-music
    title: M3U export
    text: Standard EXTM3U files that Jellyfin, Navidrome and Plex pick up automatically.
    link: /features/m3u-export/
  - icon: folder
    title: Library layout
    text: Flat dump or per-artist folders — whichever your media server prefers.
    link: /features/file-organization/
  - icon: import
    title: CSV library import
    text: Bring a Soundiiz, TuneMyMusic or Exportify export and queue the whole thing.
    link: /features/library-import/
quickStart:
  - text: Installation guide
    link: /getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /getting-started/docker-compose/
---

## How it actually works

Spotify's official API gates downloads behind a Premium subscription. Downtify takes the side door instead — it reads the metadata Spotify already exposes on its public embed pages, asks YouTube Music for the closest matching audio, hands the file to `yt-dlp` and `ffmpeg`, and writes proper tags with `mutagen`. The whole pipeline lives in a single Docker container.

<HomePipeline :steps="$frontmatter.pipeline" />

## What you can paste in

|                    |                                    |
| ------------------ | ---------------------------------- |
| Spotify track      | `open.spotify.com/track/…`         |
| Spotify album      | `open.spotify.com/album/…`         |
| Spotify playlist   | `open.spotify.com/playlist/…`      |
| YouTube / YT Music | `youtube.com/watch?v=…`            |
| Free-text search   | `The Night Owls Do I Still Recall` |

## Highlights

<HomeHighlights :items="$frontmatter.highlights" />

## One command and you're done

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Open [`localhost:8000`](http://localhost:8000), paste a link, hit download. Files land in `/path/to/music` with the tags already in place.

<HomeActions :actions="$frontmatter.quickStart" />
