---
layout: home
title: Downtify
titleTemplate: Kendi sunucunuzda barındırılan müzik indirici
description: Kendi sunucunuzda barındırılan müzik indirici. Bir Spotify bağlantısı yapıştırın, etiketleri eksiksiz bir ses dosyası alın — API anahtarı yok, hesap yok, zahmet yok.
icon: lucide/house
hero:
  eyebrow: Kendi sunucunuzda barındırılan müzik indirici
  lead:
    - Kendi makinenizde barındırabileceğiniz müzik indirici.
    - Bir Spotify bağlantısı bırakın, etiketli bir ses dosyası alın. Hesap yok, API anahtarı yok, Premium yok.
  actions:
    - text: Başlayın
      link: /tr/getting-started/installation/
      primary: true
    - text: GitHub’da kaynak kodu
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Sürüm
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Docker çekmeleri
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&style=flat&label=docker%20pulls
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Lisans
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
pipeline:
  - title: Spotify embed
    text: meta veri
  - title: YouTube Music
    text: ses eşleşmesi
  - title: yt-dlp · ffmpeg · mutagen
    text: indir ve etiketle
highlights:
  - icon: eye
    title: Çalma listesi izleyici
    text: Bir çalma listesini izler ve yeni parçaları eklendikçe sessizce indirir.
    link: /tr/features/playlist-monitor/
  - icon: sliders-horizontal
    title: Beş biçim
    text: MP3, FLAC, M4A, OGG ve OPUS — seçtiğiniz bit hızında.
    link: /tr/features/download-settings/
  - icon: mic-vocal
    title: Sözler dahil
    text: lrclib’den alınıp dosyaya gömülen düz ve zamanla eşzamanlı sözler.
    link: /tr/features/lyrics/
  - icon: headphones
    title: Web oynatıcı
    text: Karıştır, tekrarla, ses ve albüm kapağı — doğrudan tarayıcıdan.
    link: /tr/features/player/
  - icon: list-music
    title: M3U dışa aktarma
    text: Jellyfin, Navidrome ve Plex’in otomatik tanıdığı standart EXTM3U dosyaları.
    link: /tr/features/m3u-export/
  - icon: folder
    title: Kitaplık düzeni
    text: Tek klasör ya da sanatçı başına klasör — medya sunucunuz hangisini tercih ediyorsa.
    link: /tr/features/file-organization/
  - icon: import
    title: CSV kitaplık içe aktarma
    text: Soundiiz, TuneMyMusic veya Exportify dışa aktarımını getirin ve hepsini kuyruğa alın.
    link: /tr/features/library-import/
quickStart:
  - text: Kurulum kılavuzu
    link: /tr/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /tr/getting-started/docker-compose/
---

## Gerçekte nasıl çalışır

Spotify’ın resmi API’si indirmeleri Premium aboneliğe bağlar. Downtify yan kapıyı kullanır — Spotify’ın herkese açık gömme sayfalarında zaten gösterdiği meta verileri okur, YouTube Music’ten en yakın sesi ister, dosyayı `yt-dlp` ve `ffmpeg`’e verir ve `mutagen` ile doğru etiketleri yazar. Tüm hat tek bir Docker kapsayıcısında yaşar.

<HomePipeline :steps="$frontmatter.pipeline" />

## Neler yapıştırabilirsiniz

|                    |                                    |
| ------------------ | ---------------------------------- |
| Spotify parçası    | `open.spotify.com/track/…`         |
| Spotify albümü     | `open.spotify.com/album/…`         |
| Spotify çalma listesi | `open.spotify.com/playlist/…`   |
| YouTube / YT Music | `youtube.com/watch?v=…`            |
| Serbest metin araması | `The Night Owls Do I Still Recall` |

## Öne çıkanlar

<HomeHighlights :items="$frontmatter.highlights" />

## Tek komut, iş tamam

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

[`localhost:8000`](http://localhost:8000) adresini açın, bir bağlantı yapıştırın, indire basın. Dosyalar etiketleri yerinde olarak `/path/to/music` içine gelir.

<HomeActions :actions="$frontmatter.quickStart" />
