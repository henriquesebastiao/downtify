---
layout: home
title: Downtify
titleTemplate: Baixador de músicas auto-hospedado
description: Baixador de músicas auto-hospedado. Cole um link do Spotify e receba um arquivo de áudio perfeitamente etiquetado — sem chaves de API, sem conta, sem complicação.
icon: lucide/house
hero:
  eyebrow: Baixador de músicas auto-hospedado
  lead:
    - O baixador de músicas que você hospeda na sua própria máquina.
    - Cole um link do Spotify e receba um arquivo de áudio com tags. Sem conta, sem chave de API, sem Premium.
  actions:
    - text: Começar
      link: /pt-BR/getting-started/installation/
      primary: true
    - text: Código-fonte no GitHub
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Versão
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Downloads do Docker
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&style=flat&label=docker%20pulls
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Licença
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
pipeline:
  - title: Spotify embed
    text: metadados
  - title: YouTube Music
    text: busca do áudio
  - title: yt-dlp · ffmpeg · mutagen
    text: baixar e etiquetar
highlights:
  - icon: eye
    title: Monitor de playlists
    text: Acompanha uma playlist e baixa em silêncio as faixas novas conforme são adicionadas.
    link: /pt-BR/features/playlist-monitor/
  - icon: sliders-horizontal
    title: Cinco formatos
    text: MP3, FLAC, M4A, OGG e OPUS — na taxa de bits que você escolher.
    link: /pt-BR/features/download-settings/
  - icon: mic-vocal
    title: Letras incluídas
    text: Letras simples e sincronizadas com o tempo, buscadas no lrclib e incorporadas ao arquivo.
    link: /pt-BR/features/lyrics/
  - icon: headphones
    title: Player web
    text: Aleatório, repetir, volume e capa do álbum — direto do navegador.
    link: /pt-BR/features/player/
  - icon: list-music
    title: Exportação M3U
    text: Arquivos EXTM3U padrão que Jellyfin, Navidrome e Plex reconhecem automaticamente.
    link: /pt-BR/features/m3u-export/
  - icon: folder
    title: Organização da biblioteca
    text: Tudo numa pasta só ou uma pasta por artista — o que o seu servidor de mídia preferir.
    link: /pt-BR/features/file-organization/
  - icon: import
    title: Importação de CSV
    text: Traga uma exportação do Soundiiz, TuneMyMusic ou Exportify e coloque tudo na fila.
    link: /pt-BR/features/library-import/
quickStart:
  - text: Guia de instalação
    link: /pt-BR/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /pt-BR/getting-started/docker-compose/
---

## Como funciona de verdade

A API oficial do Spotify restringe os downloads a quem tem assinatura Premium. O Downtify pega a porta lateral — lê os metadados que o Spotify já expõe nas páginas públicas de incorporação, pede ao YouTube Music o áudio mais parecido, entrega o arquivo ao `yt-dlp` e ao `ffmpeg` e grava as tags certas com o `mutagen`. Todo o pipeline roda em um único contêiner Docker.

<HomePipeline :steps="$frontmatter.pipeline" />

## O que você pode colar

|                    |                                    |
| ------------------ | ---------------------------------- |
| Faixa do Spotify   | `open.spotify.com/track/…`         |
| Álbum do Spotify   | `open.spotify.com/album/…`         |
| Playlist do Spotify | `open.spotify.com/playlist/…`     |
| YouTube / YT Music | `youtube.com/watch?v=…`            |
| Busca por texto livre | `The Night Owls Do I Still Recall` |

## Destaques

<HomeHighlights :items="$frontmatter.highlights" />

## Um comando e pronto

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Abra [`localhost:8000`](http://localhost:8000), cole um link e clique em baixar. Os arquivos chegam a `/path/to/music` já com as tags no lugar.

<HomeActions :actions="$frontmatter.quickStart" />
