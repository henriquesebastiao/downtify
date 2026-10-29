---
layout: home
title: Downtify
titleTemplate: Descargador de música autoalojado
description: Descargador de música autoalojado. Pega un enlace de Spotify y obtén un archivo de audio perfectamente etiquetado — sin claves de API, sin cuenta, sin complicaciones.
icon: lucide/house
hero:
  eyebrow: Descargador de música autoalojado
  lead:
    - El descargador de música que puedes alojar en tu propia máquina.
    - Pega un enlace de Spotify y obtén un archivo de audio etiquetado. Sin cuenta, sin clave de API, sin Premium.
  actions:
    - text: Empezar
      link: /es/getting-started/installation/
      primary: true
    - text: Código fuente en GitHub
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Versión
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Descargas de Docker
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&style=flat&label=docker%20pulls
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Licencia
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
pipeline:
  - title: Spotify embed
    text: metadatos
  - title: YouTube Music
    text: búsqueda del audio
  - title: yt-dlp · ffmpeg · mutagen
    text: descargar y etiquetar
highlights:
  - icon: eye
    title: Monitor de playlists
    text: Vigila una playlist y descarga en silencio las canciones nuevas a medida que se añaden.
    link: /es/features/playlist-monitor/
  - icon: sliders-horizontal
    title: Cinco formatos
    text: MP3, FLAC, M4A, OGG y OPUS — con la tasa de bits que elijas.
    link: /es/features/download-settings/
  - icon: mic-vocal
    title: Letras incluidas
    text: Letras simples y sincronizadas con el tiempo, obtenidas de lrclib e incrustadas en el archivo.
    link: /es/features/lyrics/
  - icon: headphones
    title: Reproductor web
    text: Aleatorio, repetir, volumen y portada del álbum — directamente desde el navegador.
    link: /es/features/player/
  - icon: list-music
    title: Exportación M3U
    text: Archivos EXTM3U estándar que Jellyfin, Navidrome y Plex reconocen automáticamente.
    link: /es/features/m3u-export/
  - icon: folder
    title: Organización de la biblioteca
    text: Todo en una carpeta o una carpeta por artista — lo que prefiera tu servidor multimedia.
    link: /es/features/file-organization/
  - icon: import
    title: Importación de CSV
    text: Trae una exportación de Soundiiz, TuneMyMusic o Exportify y pon todo en cola.
    link: /es/features/library-import/
quickStart:
  - text: Guía de instalación
    link: /es/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /es/getting-started/docker-compose/
---

## Cómo funciona de verdad

La API oficial de Spotify condiciona las descargas a una suscripción Premium. Downtify entra por la puerta lateral — lee los metadatos que Spotify ya expone en sus páginas públicas de inserción, pide a YouTube Music el audio más parecido, entrega el archivo a `yt-dlp` y `ffmpeg` y escribe las etiquetas correctas con `mutagen`. Todo el pipeline vive en un único contenedor de Docker.

<HomePipeline :steps="$frontmatter.pipeline" />

## Qué puedes pegar

|                    |                                    |
| ------------------ | ---------------------------------- |
| Canción de Spotify | `open.spotify.com/track/…`         |
| Álbum de Spotify   | `open.spotify.com/album/…`         |
| Playlist de Spotify | `open.spotify.com/playlist/…`     |
| YouTube / YT Music | `youtube.com/watch?v=…`            |
| Búsqueda de texto libre | `The Night Owls Do I Still Recall` |

## Destacados

<HomeHighlights :items="$frontmatter.highlights" />

## Un comando y listo

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Abre [`localhost:8000`](http://localhost:8000), pega un enlace y pulsa descargar. Los archivos llegan a `/path/to/music` con las etiquetas ya puestas.

<HomeActions :actions="$frontmatter.quickStart" />
