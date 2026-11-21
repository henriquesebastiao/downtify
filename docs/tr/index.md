---
layout: home
title: Downtify
titleTemplate: "Kendi sunucunuzda Spotify indirici ve müzik çalar"
description: "Oynatıcılı, kendi sunucunuzda Spotify indirici. Spotify, YouTube Music, Deezer veya SoundCloud bağlantısı yapıştırın, etiketli MP3 ya da FLAC alın. API anahtarı yok."
icon: lucide/house
hero:
  eyebrow: Kendi sunucunuzda barındırılan müzik indirici
  headline:
    - Bağlantıyı yapıştırın.
    - Müziği alın.
  lead: Yerleşik oynatıcılı, kendi sunucunuzda barındırılan bir müzik indirici. Bir Spotify, YouTube Music, Deezer veya SoundCloud bağlantısı yapıştırın; tarayıcıda, telefonda ya da medya sunucunuzda çalmaya hazır, kusursuz etiketlenmiş bir kitaplık alın.
  note: Spotify hesabı yok, API anahtarı yok, Premium yok.
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
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&label=docker%20pulls&color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: GitHub yıldızları
      src: https://img.shields.io/github/stars/henriquesebastiao/downtify?style=flat&label=stars&color=1AD05C
      link: https://star-history.com/#henriquesebastiao/downtify&Date
    - alt: Lisans
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
video:
  src: /assets/media/downtify-demo.mp4
  poster: /assets/media/downtify-demo-poster.webp
  label: '44 saniyede Downtify: bir çalma listesi bağlantısı yapıştırın, tek tıkla indirin, eşitlenmiş tutun ve eşzamanlı sözlerle dinleyin; bilgisayarda ve telefonda.'
why:
  - icon: link
    title: Tek bir bağlantı yeter
    text: Spotify, YouTube Music, Deezer veya SoundCloud’dan bir şarkı, bir albüm, koca bir çalma listesi ya da bir sanatçı yapıştırın veya dinlemek istediğinizi yazmanız yeterli. Downtify sesi bulur ve hepsini eve getirir.
    link: /tr/how-it-works/
  - icon: tag
    title: Saklamaya değer dosyalar
    text: Her dosya kapağını, emeği geçen tüm sanatçıları, albümü, yılı, parça numarasını ve varsa zamanla eşzamanlı sözleri taşır. MP3, FLAC, M4A, OGG veya Opus ya da kaynağın sesi geldiği gibi.
    link: /tr/features/download-settings/
  - icon: music
    title: Kendi müzik yayın hizmetiniz
    text: Tarayıcıda eşzamanlı sözler, karaoke, kuyruk, beğenilen şarkılar, çalma listeleri ve podcast’lerle tam bir oynatıcı. Android ve iOS uygulamaları kitaplığınızı yanınızda taşır, çevrimdışı da.
    link: /tr/features/player/
  - icon: radar
    title: Kurun ve unutun
    text: Çalma listelerini ve sanatçıları izleyin. Yeni şarkılar ve yeni çıkışlar, seçtiğiniz sıklıkta kendiliğinden indirilir.
    link: /tr/features/playlist-monitor/
  - icon: server
    title: Ev sunucunuz için yapıldı
    text: amd64 ve arm64 için tek bir Docker imajı, SQLite veya PostgreSQL, evdeki herkes için isteğe bağlı tek oturum açmalı hesaplar ve Jellyfin, Navidrome ile Plex’in tanıdığı çalma listeleri.
    link: /tr/getting-started/
  - icon: shield
    title: Hiçbir bağ yok
    text: Spotify API anahtarı yok, geliştirici hesabı yok, Premium yok. Uygulamada reklam, kullanım istatistiği ya da ücretli hiçbir şey yok. Özgür ve açık kaynaklı.
    link: /tr/contributing/
showcase:
  - shot: now-playing
    label: Şimdi çalıyor
    caption: Sözler şarkıyı satır satır, kapağın ve sıradakilerin yanında takip eder.
    alt: Tam ekran Şimdi çalıyor görünümü; albüm kapağı, geçerli satırı vurgulanmış eşzamanlı sözler ve kuyruk.
  - shot: karaoke
    label: Karaoke
    caption: Her satır söylendikçe dolan büyük sözler, ikinci bir ekranda açılmaya hazır.
    alt: Karaoke görünümü; kapağın renklerinde hareketli bir arka planın üzerinde dolan büyük sözler.
  - shot: home
    label: Ana sayfa
    caption: Bir bağlantı yapıştırın ya da yeni bir şey arayın ve kaldığınız yerden devam edin.
    alt: Ana sayfa; bağlantı yapıştırmak ya da aramak için bir kutu, kitaplık istatistikleri, çalan albüm ve son eklenen albümler.
  - shot: library
    label: Kitaplık
    caption: Albümler, sanatçılar, çalma listeleri ve parçalar; istediğiniz gibi sıralanmış ve süzülmüş.
    alt: Kitaplık sayfası; albüm kapaklarından bir ızgara ve albümler, sanatçılar, çalma listeleri ve parçalar için sekmeler.
  - shot: playlist
    label: Çalma listeleri
    caption: Kendi kapağı olan kendi çalma listeleriniz; çalmak, paylaşmak ya da ZIP olarak indirmek için.
    alt: Bir çalma listesi sayfası; kapağı, düğmeleri ve albüm, biçim ve çıkış tarihiyle şarkıları.
  - shot: phones
    label: Telefonunuzda
    caption: Aynı uygulama telefonunuzda, tarayıcıdan yüklenebilir.
    alt: Üç telefonda Downtify; ana sayfa, Şimdi çalıyor ve Kitaplık.
pipeline:
  - icon: link
    title: Bağlantıyı yapıştırın
    text: Spotify, YouTube Music, Deezer veya SoundCloud. Ya da yalnızca bir şarkı yazın.
  - icon: search
    title: Sesi bulur
    text: YouTube Music’teki en yakın eşleşme, süresine göre doğrulanır. İsterseniz başka kaynaklar da.
  - icon: download
    title: İndirir ve etiketler
    text: yt-dlp ve ffmpeg sesi getirir. Kapak, sözler ve etiketler dosyanın içine yazılır.
  - icon: music
    title: Her yerde dinleyin
    text: Tarayıcıda, telefonda ya da Jellyfin, Navidrome ve Plex’te.
quickStart:
  - text: Kurulum kılavuzu
    link: /tr/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /tr/getting-started/docker-compose/
  - text: Tek tıkla kurulum
    link: /tr/getting-started/one-click/
apps:
  - icon: smartphone
    title: Android için Downtify
    text: Resmî uygulama. Sunucunuzu ağda bulur, Wi-Fi’da özgün kalitede, mobil veride daha düşük kalitede akıtır, şarkıları çevrimdışı tutar ve Android Auto ile çalışır. Hâlâ test aşamasında; GitHub Releases ve Obtainium’da.
    link: https://github.com/henriquesebastiao/downtify-android
  - icon: tablet-smartphone
    title: iOS için Downtify
    text: Bir topluluk üyesinin iPhone ve iPad için yaptığı uygulama (iOS 17 veya üstü); çevrimdışı şarkılar ve kilit ekranı denetimleriyle. Herkese açık beta TestFlight’ta.
    link: https://github.com/michaelmoskie/Downtify-IOS-Client
community:
  - text: GitHub’da yıldız ver
    link: https://github.com/henriquesebastiao/downtify
    icon: star
    primary: true
  - text: Sponsor ol
    link: https://github.com/sponsors/henriquesebastiao
    icon: heart
  - text: Çevir
    link: /tr/features/internationalization/
    icon: languages
  - text: Katkıda bulun
    link: /tr/contributing/
    icon: git-pull-request
---

## Neden Downtify

<HomeHighlights :items="$frontmatter.why" />

## Daha yakından bakın

<HomeShowcase :items="$frontmatter.showcase" />

## Nasıl çalışır

Downtify’ın Spotify API anahtarına ihtiyacı yoktur ve Spotify’dan asla bir şey indirmez. Bir bağlantının neyi gösterdiğini herkese açık kaynaklardan okur, süresi en iyi eşleşen YouTube Music sesini seçer, `yt-dlp` ile indirir, `ffmpeg` ile dönüştürür ve `mutagen` ile etiketler; hepsi tek bir Docker kapsayıcısında. Hiçbir şey iyi eşleşmezse YouTube devreye girer; SoundCloud, Soulseek ve Deemix ise siz açarsanız katılır. [Her adım ayrıntılarıyla](how-it-works.md).

<HomePipeline :steps="$frontmatter.pipeline" />

## Neler yapıştırabilirsiniz

| Kaynak        | Neler çalışır                                    | Örnek                               |
| ------------- | ------------------------------------------------ | ----------------------------------- |
| Spotify       | Parçalar, albümler, çalma listeleri, sanatçılar  | `open.spotify.com/playlist/…`       |
| YouTube Music | Şarkılar, albümler, çalma listeleri, sanatçılar  | `music.youtube.com/playlist?list=…` |
| YouTube       | Videolar                                         | `youtube.com/watch?v=…`             |
| Deezer        | Parçalar, albümler, çalma listeleri, sanatçılar  | `deezer.com/album/…`                |
| SoundCloud    | Parçalar                                         | `soundcloud.com/artist/track`       |
| Arama         | Ne yazacaksanız                                  | `The Night Owls Do I Still Recall`  |
| CSV           | Kitaplık dışa aktarımları                        | Soundiiz, TuneMyMusic, Exportify    |

## Yaptığı her şey

Her özelliğin, tüm seçeneklerin açıklandığı kendi sayfası var. [Tüm özellikler bir bakışta](features/index.md).

<HomeFeatures />

## Bir dakikada çalışır hâlde

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

[`localhost:8000`](http://localhost:8000) adresini açın, **admin** kullanıcısı ve **downtify** parolasıyla oturum açın ve bir bağlantı yapıştırın. Bu parolayı hemen **Ayarlar → Genel** bölümünden değiştirin. Müziğiniz etiketleriyle birlikte `/path/to/music` klasörüne gelir.

<HomeActions :actions="$frontmatter.quickStart" />

## Sık sorulan sorular

::: details Spotify hesabına, Premium’a ya da API anahtarına ihtiyacım var mı?
Hayır. Downtify parça, albüm ve çalma listesi bilgilerini Spotify’ın herkese açık gömme (embed) sayfalarından okur; bu yüzden hiçbir kimlik bilgisine ihtiyaç duymaz ve ses asla Spotify’dan gelmez. Bkz. [Nasıl çalışır](how-it-works.md).
:::

::: details Ses nereden geliyor ve kalitesi nasıl?
Varsayılan olarak YouTube Music’ten: süresi şarkıya en iyi uyan sonuç, yedek olarak da YouTube. İstediğiniz bit hızında MP3, FLAC, M4A, OGG veya Opus seçin ya da kaynağın en iyi sesini yeniden kodlamadan saklayın. Kayıpsız dosyalar sizin eklediğiniz kaynaklardan gelir: dosyaları özgün biçimini koruyan kendi [Soulseek (slskd)](features/slskd-navidrome.md) sunucunuz ya da bir [Deemix](features/deemix.md) sunucusu. Bkz. [İndirme ayarları](features/download-settings.md).
:::

::: details Jellyfin, Navidrome veya Plex ile çalışır mı?
Evet. Dosyalar medya sunucularının beklediği gibi etiketlenir, `Sanatçı/Albüm/` klasörlerine yerleşir ve her çalma listesi onların tanıdığı standart bir M3U dosyası alır. Navidrome ayrıca çalma listelerini eşitlenmiş ve puanlarını Deezer’dan alabilir. Bkz. [Dosya düzeni](features/file-organization.md) ve [M3U dışa aktarma](features/m3u-export.md).
:::

::: details Raspberry Pi’da ya da bir NAS’ta çalışır mı?
İmaj hem `amd64` hem `arm64` için yayımlanır; Umbrel, CasaOS ve HomeDock OS onu tek tıkla kurar. Bkz. [Tek tıkla kurulum](getting-started/one-click.md).
:::

::: details YouTube “Sign in to confirm you're not a bot” diyor. Ne yapmalıyım?
**Ayarlar → YouTube çerezleri** bölümünden bir `cookies.txt` yükleyin; Downtify bu oturumu kendiliğinden açık tutar. YouTube sizi hâlâ sınırlıyorsa _İndirmeler arası bekleme_ süresini artırın, _Eşzamanlı indirmeler_ sayısını azaltın, ardından `DOWNTIFY_FORCE_IPV4=1` deneyin. Bkz. [Sorun giderme](troubleshooting.md) ve [YouTube çerezleri](features/youtube-cookies.md).
:::

## Yanınızda taşıyın

<HomeHighlights :items="$frontmatter.apps" />

Başka herhangi bir istemci de aynı API’yi kullanabilir: [mobil istemci sözleşmesine](mobile-client-contract.md) bakın.

<div class="home-cta">

## Açıkta geliştirildi

Downtify özgür ve açık kaynaklıdır. 35’ten fazla kişi koda katkıda bulundu, topluluktan çevirmenler onu 12 dile taşıdı ve birçok özellik birinin issue olarak açtığı bir fikirle başladı. Sunucunuzda yer edindiyse GitHub’da ona bir yıldız verin, kendi hizmetlerini barındıran bir arkadaşınıza anlatın ya da geliştirilmesine sponsor olun: her sürüme giden zamanın karşılanmasına yardımcı olur.

<HomeActions :actions="$frontmatter.community" />

</div>
