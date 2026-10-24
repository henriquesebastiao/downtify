---
layout: home
title: Downtify
titleTemplate: Самостоятелно хостван инструмент за сваляне на музика
description: Самостоятелно хостван инструмент за сваляне на музика. Поставете линк от Spotify и получете перфектно етикетиран аудиофайл — без API ключове, без акаунт, без излишни усилия.
icon: lucide/house
hero:
  eyebrow: Самостоятелно хостван инструмент за сваляне на музика
  lead:
    - Инструментът за сваляне на музика, който можете да хоствате на собствената си машина.
    - Пуснете линк от Spotify и получете етикетиран аудиофайл. Без акаунт, без API ключ, без Premium.
  actions:
    - text: Започнете
      link: /bg/getting-started/installation/
      primary: true
    - text: Изходен код в GitHub
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Версия
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Docker изтегляния
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&style=flat&label=docker%20pulls
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Лиценз
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
pipeline:
  - title: Spotify embed
    text: метаданни
  - title: YouTube Music
    text: съвпадение на аудиото
  - title: yt-dlp · ffmpeg · mutagen
    text: сваляне и тагове
highlights:
  - icon: eye
    title: Следене на плейлисти
    text: Следи плейлист и тихо сваля новите песни, щом бъдат добавени.
    link: /bg/features/playlist-monitor/
  - icon: sliders-horizontal
    title: Пет формата
    text: MP3, FLAC, M4A, OGG и OPUS — с избрания от вас битрейт.
    link: /bg/features/download-settings/
  - icon: mic-vocal
    title: Вградени текстове
    text: Обикновени и синхронизирани по време текстове от lrclib, вградени във файла.
    link: /bg/features/lyrics/
  - icon: headphones
    title: Уеб плейър
    text: Разбъркване, повторение, сила на звука и корица на албума — направо от браузъра.
    link: /bg/features/player/
  - icon: list-music
    title: M3U експорт
    text: Стандартни EXTM3U файлове, които Jellyfin, Navidrome и Plex откриват автоматично.
    link: /bg/features/m3u-export/
  - icon: folder
    title: Структура на библиотеката
    text: Всичко в една папка или папка за всеки изпълнител — каквото предпочита медийният ви сървър.
    link: /bg/features/file-organization/
  - icon: import
    title: Импорт на CSV
    text: Донесете експорт от Soundiiz, TuneMyMusic или Exportify и сложете всичко на опашката.
    link: /bg/features/library-import/
quickStart:
  - text: Ръководство за инсталиране
    link: /bg/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /bg/getting-started/docker-compose/
---

## Как наистина работи

Официалното API на Spotify обвързва изтеглянията с Premium абонамент. Downtify минава през страничната врата — чете метаданните, които Spotify така или иначе показва на публичните си страници за вграждане, пита YouTube Music за най-близкото аудио, подава файла на `yt-dlp` и `ffmpeg` и записва правилните тагове с `mutagen`. Целият процес живее в един-единствен Docker контейнер.

<HomePipeline :steps="$frontmatter.pipeline" />

## Какво можете да поставите

|                    |                                    |
| ------------------ | ---------------------------------- |
| Песен от Spotify   | `open.spotify.com/track/…`         |
| Албум от Spotify   | `open.spotify.com/album/…`         |
| Плейлист от Spotify | `open.spotify.com/playlist/…`     |
| YouTube / YT Music | `youtube.com/watch?v=…`            |
| Свободно текстово търсене | `The Night Owls Do I Still Recall` |

## Основни неща

<HomeHighlights :items="$frontmatter.highlights" />

## Една команда и готово

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Отворете [`localhost:8000`](http://localhost:8000), поставете линк, натиснете сваляне. Файловете пристигат в `/path/to/music` с вече готови тагове.

<HomeActions :actions="$frontmatter.quickStart" />
