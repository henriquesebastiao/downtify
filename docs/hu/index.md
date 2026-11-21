---
layout: home
title: Downtify
titleTemplate: "Saját szerveren futó Spotify-letöltő és zenelejátszó"
description: "Saját szerveres Spotify-letöltő lejátszóval. Spotify-, YouTube Music-, Deezer- vagy SoundCloud-linkből címkézett MP3 vagy FLAC lesz. API-kulcs nélkül."
icon: lucide/house
hero:
  eyebrow: Saját szerveren futtatható zeneletöltő
  headline:
    - Illessz be egy linket.
    - Megkapod a zenét.
  lead: Saját szerveren futtatható zeneletöltő beépített lejátszóval. Illessz be egy Spotify-, YouTube Music-, Deezer- vagy SoundCloud-hivatkozást, és kapj egy tökéletesen címkézett könyvtárat, amely azonnal szól a böngészőben, a telefonodon vagy a médiaszervereden.
  note: Spotify-fiók, API-kulcs és Premium nélkül.
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
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&label=docker%20pulls&color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Csillagok a GitHubon
      src: https://img.shields.io/github/stars/henriquesebastiao/downtify?style=flat&label=stars&color=1AD05C
      link: https://star-history.com/#henriquesebastiao/downtify&Date
    - alt: Licenc
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
video:
  src: /assets/media/downtify-demo.mp4
  poster: /assets/media/downtify-demo-poster.webp
  label: 'A Downtify 44 másodpercben: illessz be egy lejátszási lista hivatkozását, töltsd le egy kattintással, tartsd szinkronban, és hallgasd időzített dalszövegekkel, számítógépen és telefonon.'
why:
  - icon: link
    title: Egy hivatkozás elég
    text: Illessz be egy dalt, egy albumot, egy teljes lejátszási listát vagy egy előadót a Spotifyról, a YouTube Musicról, a Deezerről vagy a SoundCloudról, vagy egyszerűen írd be, mit szeretnél hallgatni. A Downtify megtalálja a hangot, és hazahozza.
    link: /hu/how-it-works/
  - icon: tag
    title: Fájlok, amelyeket érdemes megtartani
    text: Minden fájlban ott a borító, minden közreműködő előadó, az album, az év, a sorszám és a dalszöveg, időzítve, ha van. MP3, FLAC, M4A, OGG vagy Opus, vagy a forrás hangja pontosan úgy, ahogy érkezett.
    link: /hu/features/download-settings/
  - icon: music
    title: A saját streamingszolgáltatásod
    text: Teljes értékű lejátszó a böngészőben, időzített dalszövegekkel, karaokéval, lejátszási sorral, kedvelt számokkal, lejátszási listákkal és podcastokkal. Az Android- és iOS-alkalmazások veled viszik a könyvtáradat, offline is.
    link: /hu/features/player/
  - icon: radar
    title: Beállítod és elfelejted
    text: Figyelj lejátszási listákat és előadókat. Az új dalok és kiadványok maguktól letöltődnek, az általad választott gyakorisággal.
    link: /hu/features/playlist-monitor/
  - icon: server
    title: Az otthoni szerveredre tervezve
    text: Egyetlen Docker-image amd64-re és arm64-re, SQLite vagy PostgreSQL, fiókok az egész háztartásnak opcionális egyszeri bejelentkezéssel, és lejátszási listák, amelyeket a Jellyfin, a Navidrome és a Plex felismer.
    link: /hu/getting-started/
  - icon: shield
    title: Nincsenek kötöttségek
    text: Nincs Spotify API-kulcs, fejlesztői fiók vagy Premium. Az alkalmazásban nincs reklám, nincs használati statisztika, és semmi sem fizetős. Szabad és nyílt forráskódú.
    link: /hu/contributing/
showcase:
  - shot: now-playing
    label: Most szól
    caption: A dalszöveg soronként követi a dalt, a borító és a következő számok mellett.
    alt: A teljes képernyős Most szól nézet az album borítójával, időzített dalszöveggel, kiemelt aktuális sorral, és a lejátszási sorral.
  - shot: karaoke
    label: Karaoke
    caption: Nagy dalszövegek, amelyek soronként telnek meg az énekléssel, és egy második képernyőn is megnyithatók.
    alt: A karaoke nézet nagy dalszövegekkel, amelyek a borító színeiben mozgó háttér előtt telnek meg.
  - shot: home
    label: Kezdőlap
    caption: Illessz be egy hivatkozást vagy keress valami újat, és folytasd ott, ahol abbahagytad.
    alt: A kezdőlap egy mezővel hivatkozás beillesztéséhez vagy kereséshez, a könyvtár statisztikáival, a szóló albummal és a nemrég hozzáadott albumokkal.
  - shot: library
    label: Könyvtár
    caption: Albumok, előadók, lejátszási listák és számok, úgy rendezve és szűrve, ahogy szeretnéd.
    alt: A Könyvtár oldal albumborítók rácsával és fülekkel az albumokhoz, előadókhoz, lejátszási listákhoz és számokhoz.
  - shot: playlist
    label: Lejátszási listák
    caption: Saját lejátszási listák saját borítóval, lejátszáshoz, megosztáshoz vagy ZIP-letöltéshez.
    alt: Egy lejátszásilista-oldal a borítójával, a gombjaival és a dalokkal, albummal, formátummal és megjelenési dátummal.
  - shot: phones
    label: Telefonon
    caption: Ugyanaz az alkalmazás a telefonodon, a böngészőből telepíthető.
    alt: A Downtify három telefonon, a kezdőlappal, a Most szól nézettel és a Könyvtárral.
pipeline:
  - icon: link
    title: Illeszd be a hivatkozást
    text: Spotify, YouTube Music, Deezer vagy SoundCloud. Vagy csak írj be egy dalt.
  - icon: search
    title: Megkeresi a hangot
    text: A legközelebbi találat a YouTube Musicon, a hossza alapján ellenőrizve. Ha kéred, más források is.
  - icon: download
    title: Letölti és címkézi
    text: A yt-dlp és az ffmpeg letölti. A borító, a dalszöveg és a címkék a fájlba kerülnek.
  - icon: music
    title: Hallgasd bárhol
    text: A böngészőben, a telefonodon, vagy a Jellyfinben, a Navidrome-ban és a Plexben.
quickStart:
  - text: Telepítési útmutató
    link: /hu/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /hu/getting-started/docker-compose/
  - text: Telepítés egy kattintással
    link: /hu/getting-started/one-click/
apps:
  - icon: smartphone
    title: Downtify Androidra
    text: A hivatalos alkalmazás. Megtalálja a szerveredet a hálózaton, Wi-Fin eredeti minőségben, mobilneten kisebben streamel, offline is megőrzi a dalokat, és működik az Android Autóval. Még tesztelés alatt, a GitHub Releases oldalon és az Obtainiumban.
    link: https://github.com/henriquesebastiao/downtify-android
  - icon: tablet-smartphone
    title: Downtify iOS-re
    text: Egy közösségi tag készítette iPhone-ra és iPadre (iOS 17 vagy újabb), offline dalokkal és lezárási képernyős vezérlőkkel. A nyilvános béta a TestFlighton érhető el.
    link: https://github.com/michaelmoskie/Downtify-IOS-Client
community:
  - text: Csillag a GitHubon
    link: https://github.com/henriquesebastiao/downtify
    icon: star
    primary: true
  - text: Támogatás
    link: https://github.com/sponsors/henriquesebastiao
    icon: heart
  - text: Fordítás
    link: /hu/features/internationalization/
    icon: languages
  - text: Közreműködés
    link: /hu/contributing/
    icon: git-pull-request
---

## Miért a Downtify

<HomeHighlights :items="$frontmatter.why" />

## Közelebbről

<HomeShowcase :items="$frontmatter.showcase" />

## Hogyan működik

A Downtifynak nincs szüksége Spotify API-kulcsra, és soha semmit nem tölt le a Spotifyról. Nyilvános forrásokból olvassa ki, mire mutat egy hivatkozás, kiválasztja azt a YouTube Music-hangot, amelynek a hossza a legjobban egyezik, letölti a `yt-dlp`-vel, átalakítja az `ffmpeg`-gel, és felcímkézi a `mutagen`-nel, mindezt egyetlen Docker-konténerben. Ha semmi sem egyezik jól, a YouTube lép be, a SoundCloud, a Soulseek és a Deemix pedig akkor csatlakozik, ha bekapcsolod őket. [Minden lépés részletesen](how-it-works.md).

<HomePipeline :steps="$frontmatter.pipeline" />

## Mit illeszthetsz be

| Forrás        | Mi működik                                     | Példa                               |
| ------------- | ---------------------------------------------- | ----------------------------------- |
| Spotify       | Számok, albumok, lejátszási listák, előadók    | `open.spotify.com/playlist/…`       |
| YouTube Music | Dalok, albumok, lejátszási listák, előadók     | `music.youtube.com/playlist?list=…` |
| YouTube       | Videók                                         | `youtube.com/watch?v=…`             |
| Deezer        | Számok, albumok, lejátszási listák, előadók    | `deezer.com/album/…`                |
| SoundCloud    | Számok                                         | `soundcloud.com/artist/track`       |
| Keresés       | Amit beírnál                                   | `The Night Owls Do I Still Recall`  |
| CSV           | Könyvtárexportok                               | Soundiiz, TuneMyMusic, Exportify    |

## Minden, amit tud

Minden funkciónak saját oldala van, ahol minden beállítás el van magyarázva. [Az összes funkció egy pillantással](features/index.md).

<HomeFeatures />

## Egy perc alatt működik

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Nyisd meg a [`localhost:8000`](http://localhost:8000) címet, jelentkezz be **admin** néven a **downtify** jelszóval, és illessz be egy hivatkozást. Ezt a jelszót rögtön változtasd meg a **Beállítások → Általános** alatt. A zenéd a címkéivel együtt a `/path/to/music` mappába érkezik.

<HomeActions :actions="$frontmatter.quickStart" />

## Gyakori kérdések

::: details Kell Spotify-fiók, Premium vagy API-kulcs?
Nem. A Downtify a számok, albumok és lejátszási listák adatait a Spotify nyilvános beágyazási (embed) oldalairól olvassa, így semmilyen hitelesítő adatra nincs szüksége, és a hang sosem a Spotifyról jön. Lásd: [Hogyan működik](how-it-works.md).
:::

::: details Honnan jön a hang, és milyen a minősége?
Alapból a YouTube Musicról: az a találat, amelynek a hossza a legjobban egyezik a dallal, tartaléknak a YouTube. Válassz MP3-at, FLAC-ot, M4A-t, OGG-t vagy Opust a kívánt bitrátával, vagy tartsd meg a forrás legjobb hangját újrakódolás nélkül. A veszteségmentes fájlok az általad hozzáadott forrásokból jönnek: a saját [Soulseek (slskd)](features/slskd-navidrome.md) szerveredből, amelynek fájljai megtartják eredeti formátumukat, vagy egy [Deemix](features/deemix.md)-szerverről. Lásd: [Letöltési beállítások](features/download-settings.md).
:::

::: details Működik a Jellyfinnel, a Navidrome-mal vagy a Plexszel?
Igen. A fájlok úgy vannak címkézve, ahogy a médiaszerverek várják, `Előadó/Album/` mappákba kerülnek, és minden lejátszási lista kap egy szabványos M3U fájlt, amelyet felismernek. A Navidrome emellett szinkronizált lejátszási listákat és a Deezer alapján beállított értékeléseket is kaphat. Lásd: [Fájlszervezés](features/file-organization.md) és [M3U-exportálás](features/m3u-export.md).
:::

::: details Fut Raspberry Pi-on vagy NAS-on?
Az image `amd64`-re és `arm64`-re is elkészül, az Umbrel, a CasaOS és a HomeDock OS pedig egy kattintással telepíti. Lásd: [Telepítés egy kattintással](getting-started/one-click.md).
:::

::: details A YouTube azt írja: „Sign in to confirm you're not a bot”. Most mi legyen?
Tölts fel egy `cookies.txt` fájlt a **Beállítások → YouTube sütik** alatt; a Downtify ezután magától bejelentkezve tartja ezt a munkamenetet. Ha a YouTube még mindig korlátoz, növeld a _Szünet a letöltések között_ értékét, csökkentsd a _Párhuzamos letöltések_ számát, majd próbáld ki a `DOWNTIFY_FORCE_IPV4=1` beállítást. Lásd: [Hibaelhárítás](troubleshooting.md) és [YouTube sütik](features/youtube-cookies.md).
:::

## Vidd magaddal

<HomeHighlights :items="$frontmatter.apps" />

Bármely más kliens is használhatja ugyanazt az API-t: lásd a [mobilkliens-szerződést](mobile-client-contract.md).

<div class="home-cta">

## Nyíltan fejlesztve

A Downtify szabad és nyílt forráskódú. Több mint 35 ember járult hozzá kóddal, a közösség fordítói 12 nyelvre ültették át, és sok funkció egy ötletként indult, amelyet valaki egy issue-ban vetett fel. Ha kiérdemelte a helyét a szervereden, adj neki egy csillagot a GitHubon, mesélj róla egy barátodnak, aki szintén maga üzemelteti a szolgáltatásait, vagy támogasd a fejlesztését: ez segít megfizetni az időt, ami minden kiadásba belekerül.

<HomeActions :actions="$frontmatter.community" />

</div>
