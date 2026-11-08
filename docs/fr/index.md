---
layout: home
title: Downtify
titleTemplate: Téléchargeur de musique auto-hébergé
description: Téléchargeur de musique auto-hébergé. Collez un lien Spotify et obtenez un fichier audio parfaitement étiqueté — sans clé d’API, sans compte, sans prise de tête.
icon: lucide/house
hero:
  eyebrow: Téléchargeur de musique auto-hébergé
  lead:
    - Le téléchargeur de musique que vous pouvez héberger sur votre propre machine.
    - Collez un lien Spotify et obtenez un fichier audio étiqueté. Sans compte, sans clé d’API, sans Premium.
  actions:
    - text: Commencer
      link: /fr/getting-started/installation/
      primary: true
    - text: Code source sur GitHub
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Version
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Téléchargements Docker
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&style=flat&label=docker%20pulls
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Licence
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
pipeline:
  - title: Spotify embed
    text: métadonnées
  - title: YouTube Music
    text: recherche de l’audio
  - title: yt-dlp · ffmpeg · mutagen
    text: télécharger et étiqueter
highlights:
  - icon: eye
    title: Surveillance de playlists
    text: Surveille une playlist et télécharge discrètement les nouveaux titres à mesure qu’ils sont ajoutés.
    link: /fr/features/playlist-monitor/
  - icon: sliders-horizontal
    title: Cinq formats
    text: MP3, FLAC, M4A, OGG et OPUS — au débit de votre choix.
    link: /fr/features/download-settings/
  - icon: mic-vocal
    title: Paroles intégrées
    text: Paroles simples et synchronisées dans le temps, récupérées sur lrclib et intégrées au fichier.
    link: /fr/features/lyrics/
  - icon: headphones
    title: Lecteur web
    text: Lecture aléatoire, répétition, volume et pochette — directement dans le navigateur.
    link: /fr/features/player/
  - icon: list-music
    title: Export M3U
    text: Fichiers EXTM3U standard que Jellyfin, Navidrome et Plex reconnaissent automatiquement.
    link: /fr/features/m3u-export/
  - icon: folder
    title: Organisation de la bibliothèque
    text: Tout dans un seul dossier ou un dossier par artiste — selon ce que préfère votre serveur multimédia.
    link: /fr/features/file-organization/
  - icon: import
    title: Import CSV
    text: Apportez un export de Soundiiz, TuneMyMusic ou Exportify et mettez le tout en file.
    link: /fr/features/library-import/
quickStart:
  - text: Guide d’installation
    link: /fr/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /fr/getting-started/docker-compose/
---

## Comment ça marche vraiment

L’API officielle de Spotify réserve les téléchargements aux abonnés Premium. Downtify passe par la porte de service — il lit les métadonnées que Spotify expose déjà sur ses pages d’intégration publiques, demande à YouTube Music l’audio le plus proche, confie le fichier à `yt-dlp` et `ffmpeg`, et écrit les bons tags avec `mutagen`. Tout le pipeline tient dans un seul conteneur Docker.

<HomePipeline :steps="$frontmatter.pipeline" />

## Ce que vous pouvez coller

|                    |                                    |
| ------------------ | ---------------------------------- |
| Titre Spotify      | `open.spotify.com/track/…`         |
| Album Spotify      | `open.spotify.com/album/…`         |
| Playlist Spotify   | `open.spotify.com/playlist/…`      |
| YouTube / YT Music | `youtube.com/watch?v=…`            |
| Recherche en texte libre | `The Night Owls Do I Still Recall` |

## Points forts

<HomeHighlights :items="$frontmatter.highlights" />

## Une commande et c’est fait

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Ouvrez [`localhost:8000`](http://localhost:8000), collez un lien, cliquez sur télécharger. Les fichiers arrivent dans `/path/to/music` avec les tags déjà en place.

<HomeActions :actions="$frontmatter.quickStart" />
