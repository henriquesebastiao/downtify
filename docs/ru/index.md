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

## Как это работает на самом деле

Официальный API Spotify не пускает к загрузкам без подписки Premium. Downtify идёт в обход: он читает метаданные, которые Spotify и так показывает на своих публичных embed-страницах, просит YouTube Music найти ближайшее совпадение по аудио, передаёт файл программе `yt-dlp` и `ffmpeg`, а затем записывает полноценные теги с помощью `mutagen`. Весь конвейер живёт в одном Docker-контейнере.

<HomePipeline :steps="$frontmatter.pipeline" />

## Что можно вставить

|                    |                                    |
| ------------------ | ---------------------------------- |
| Трек Spotify       | `open.spotify.com/track/…`         |
| Альбом Spotify     | `open.spotify.com/album/…`         |
| Плейлист Spotify   | `open.spotify.com/playlist/…`      |
| YouTube / YT Music | `youtube.com/watch?v=…`            |
| Поиск текстом      | `The Night Owls Do I Still Recall` |

## Главное

<HomeHighlights :items="$frontmatter.highlights" />

## Одна команда — и готово

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Откройте [`localhost:8000`](http://localhost:8000), вставьте ссылку и нажмите «Скачать». Файлы попадут в `/path/to/music`, уже с правильными тегами.

<HomeActions :actions="$frontmatter.quickStart" />
