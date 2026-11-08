---
layout: home
title: Downtify
titleTemplate: Saját szerveren futtatható zeneletöltő
description: Saját szerveren futtatható zeneletöltő. Illessz be egy Spotify-linket, és kapj egy tökéletesen címkézett hangfájlt — API-kulcs, fiók és macera nélkül.
icon: lucide/house
hero:
  eyebrow: Saját szerveren futtatható zeneletöltő
  lead:
    - A zeneletöltő, amelyet a saját gépeden futtathatsz.
    - Dobj be egy Spotify-linket, és kapj egy címkézett hangfájlt. Fiók, API-kulcs és Premium nélkül.
  actions:
    - text: Kezdés
      link: /hu/getting-started/installation/
      primary: true
    - text: Forráskód a GitHubon
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Kiadás
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Docker-letöltések
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&style=flat&label=docker%20pulls
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Licenc
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
pipeline:
  - title: Spotify embed
    text: metaadatok
  - title: YouTube Music
    text: hangillesztés
  - title: yt-dlp · ffmpeg · mutagen
    text: letöltés és címkézés
highlights:
  - icon: eye
    title: Lejátszási lista figyelő
    text: Figyel egy lejátszási listát, és csendben letölti az új számokat, ahogy hozzáadják őket.
    link: /hu/features/playlist-monitor/
  - icon: sliders-horizontal
    title: Öt formátum
    text: MP3, FLAC, M4A, OGG és OPUS — a választott bitrátával.
    link: /hu/features/download-settings/
  - icon: mic-vocal
    title: Beépített dalszövegek
    text: Sima és időzített dalszövegek az lrclibről, beágyazva a fájlba.
    link: /hu/features/lyrics/
  - icon: headphones
    title: Webes lejátszó
    text: Keverés, ismétlés, hangerő és albumborító — közvetlenül a böngészőből.
    link: /hu/features/player/
  - icon: list-music
    title: M3U-exportálás
    text: Szabványos EXTM3U fájlok, amelyeket a Jellyfin, a Navidrome és a Plex automatikusan felvesz.
    link: /hu/features/m3u-export/
  - icon: folder
    title: Könyvtárszerkezet
    text: Egyetlen mappa vagy előadónkénti mappák — amelyiket a médiaszervered jobban szereti.
    link: /hu/features/file-organization/
  - icon: import
    title: CSV-importálás
    text: Hozz egy Soundiiz-, TuneMyMusic- vagy Exportify-exportot, és állítsd sorba az egészet.
    link: /hu/features/library-import/
quickStart:
  - text: Telepítési útmutató
    link: /hu/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /hu/getting-started/docker-compose/
---

## Hogyan működik valójában

A Spotify hivatalos API-ja Premium előfizetéshez köti a letöltéseket. A Downtify az oldalajtót használja — beolvassa a metaadatokat, amelyeket a Spotify úgyis kitesz a nyilvános beágyazási oldalaira, a YouTube Musicot kéri a legközelebbi hangért, a fájlt átadja a `yt-dlp`-nek és az `ffmpeg`-nek, a megfelelő címkéket pedig a `mutagen`-nel írja. A teljes folyamat egyetlen Docker-konténerben él.

<HomePipeline :steps="$frontmatter.pipeline" />

## Mit illeszthetsz be

|                    |                                    |
| ------------------ | ---------------------------------- |
| Spotify-szám       | `open.spotify.com/track/…`         |
| Spotify-album      | `open.spotify.com/album/…`         |
| Spotify-lejátszási lista | `open.spotify.com/playlist/…` |
| YouTube / YT Music | `youtube.com/watch?v=…`            |
| Szabad szöveges keresés | `The Night Owls Do I Still Recall` |

## Kiemelt funkciók

<HomeHighlights :items="$frontmatter.highlights" />

## Egy parancs, és kész

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Nyisd meg a [`localhost:8000`](http://localhost:8000) címet, illessz be egy linket, kattints a letöltésre. A fájlok a `/path/to/music` mappába kerülnek, a címkékkel együtt.

<HomeActions :actions="$frontmatter.quickStart" />
