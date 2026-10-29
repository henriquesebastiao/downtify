---
layout: home
title: Downtify
titleTemplate: Selbst gehosteter Musik-Downloader
description: Selbst gehosteter Musik-Downloader. Spotify-Link einfügen, perfekt getaggte Audiodatei erhalten — ohne API-Schlüssel, ohne Konto, ohne Aufwand.
icon: lucide/house
hero:
  eyebrow: Selbst gehosteter Musik-Downloader
  lead:
    - Der Musik-Downloader, den du auf deinem eigenen Rechner betreiben kannst.
    - Spotify-Link einwerfen, getaggte Audiodatei erhalten. Kein Konto, kein API-Schlüssel, kein Premium.
  actions:
    - text: Loslegen
      link: /de/getting-started/installation/
      primary: true
    - text: Quellcode auf GitHub
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Release
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Docker-Pulls
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&style=flat&label=docker%20pulls
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Lizenz
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
pipeline:
  - title: Spotify embed
    text: Metadaten
  - title: YouTube Music
    text: Audiotreffer
  - title: yt-dlp · ffmpeg · mutagen
    text: laden und taggen
highlights:
  - icon: eye
    title: Playlist-Überwachung
    text: Beobachtet eine Playlist und lädt neue Titel still und leise herunter, sobald sie hinzukommen.
    link: /de/features/playlist-monitor/
  - icon: sliders-horizontal
    title: Fünf Formate
    text: MP3, FLAC, M4A, OGG und OPUS — in der Bitrate deiner Wahl.
    link: /de/features/download-settings/
  - icon: mic-vocal
    title: Songtexte inklusive
    text: Einfache und zeitsynchrone Songtexte von lrclib, eingebettet in die Datei.
    link: /de/features/lyrics/
  - icon: headphones
    title: Web-Player
    text: Zufallswiedergabe, Wiederholen, Lautstärke und Albumcover — direkt im Browser.
    link: /de/features/player/
  - icon: list-music
    title: M3U-Export
    text: Standard-EXTM3U-Dateien, die Jellyfin, Navidrome und Plex automatisch erkennen.
    link: /de/features/m3u-export/
  - icon: folder
    title: Bibliotheksstruktur
    text: Alles in einem Ordner oder ein Ordner pro Künstler — wie es dein Medienserver lieber hat.
    link: /de/features/file-organization/
  - icon: import
    title: CSV-Import
    text: Einen Export von Soundiiz, TuneMyMusic oder Exportify mitbringen und alles in die Warteschlange stellen.
    link: /de/features/library-import/
quickStart:
  - text: Installationsanleitung
    link: /de/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /de/getting-started/docker-compose/
---

## Wie es wirklich funktioniert

Spotifys offizielle API knüpft Downloads an ein Premium-Abo. Downtify nimmt stattdessen die Seitentür — es liest die Metadaten, die Spotify ohnehin auf seinen öffentlichen Einbettungsseiten preisgibt, fragt YouTube Music nach dem passendsten Audio, übergibt die Datei an `yt-dlp` und `ffmpeg` und schreibt mit `mutagen` die richtigen Tags. Die gesamte Pipeline steckt in einem einzigen Docker-Container.

<HomePipeline :steps="$frontmatter.pipeline" />

## Was du einfügen kannst

|                    |                                    |
| ------------------ | ---------------------------------- |
| Spotify-Titel      | `open.spotify.com/track/…`         |
| Spotify-Album      | `open.spotify.com/album/…`         |
| Spotify-Playlist   | `open.spotify.com/playlist/…`      |
| YouTube / YT Music | `youtube.com/watch?v=…`            |
| Freitextsuche      | `The Night Owls Do I Still Recall` |

## Highlights

<HomeHighlights :items="$frontmatter.highlights" />

## Ein Befehl, und du bist fertig

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Öffne [`localhost:8000`](http://localhost:8000), füge einen Link ein, klicke auf Herunterladen. Die Dateien landen mit fertigen Tags in `/path/to/music`.

<HomeActions :actions="$frontmatter.quickStart" />
