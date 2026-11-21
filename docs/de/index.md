---
layout: home
title: Downtify
titleTemplate: "Selbst gehosteter Spotify-Downloader und Musikplayer"
description: "Selbst gehosteter Spotify-Downloader mit Player. Link von Spotify, YouTube Music, Deezer oder SoundCloud einfügen, getaggte MP3 oder FLAC erhalten. Ohne API-Schlüssel."
icon: lucide/house
hero:
  eyebrow: Selbst gehosteter Musik-Downloader
  headline:
    - Link einfügen.
    - Musik bekommen.
  lead: Ein selbst gehosteter Musik-Downloader mit eingebautem Player. Füge einen Link von Spotify, YouTube Music, Deezer oder SoundCloud ein und erhalte eine perfekt getaggte Bibliothek, bereit zum Abspielen im Browser, auf dem Handy oder in deinem Medienserver.
  note: Ohne Spotify-Konto, ohne API-Schlüssel, ohne Premium.
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
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&label=docker%20pulls&color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: GitHub-Sterne
      src: https://img.shields.io/github/stars/henriquesebastiao/downtify?style=flat&label=stars&color=1AD05C
      link: https://star-history.com/#henriquesebastiao/downtify&Date
    - alt: Lizenz
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
video:
  src: /assets/media/downtify-demo.mp4
  poster: /assets/media/downtify-demo-poster.webp
  label: 'Downtify in 44 Sekunden: einen Playlist-Link einfügen, mit einem Klick herunterladen, synchron halten und mit synchronen Songtexten abspielen, am Computer und auf dem Handy.'
why:
  - icon: link
    title: Ein Link genügt
    text: Füge einen Song, ein Album, eine ganze Playlist oder einen Künstler von Spotify, YouTube Music, Deezer oder SoundCloud ein, oder tippe einfach, was du hören willst. Downtify findet das Audio und holt alles nach Hause.
    link: /de/how-it-works/
  - icon: tag
    title: Dateien, die man behalten will
    text: Jede Datei bringt ihr Cover mit, alle genannten Künstler, Album, Jahr, Titelnummer und den Songtext, zeitsynchron, wenn es ihn gibt. MP3, FLAC, M4A, OGG oder Opus, oder das Audio der Quelle genau so, wie es kam.
    link: /de/features/download-settings/
  - icon: music
    title: Dein eigener Streamingdienst
    text: Ein vollständiger Player im Browser, mit synchronen Songtexten, Karaoke, Warteschlange, Lieblingssongs, Playlists und Podcasts. Apps für Android und iOS nehmen deine Bibliothek mit, auch offline.
    link: /de/features/player/
  - icon: radar
    title: Einrichten und vergessen
    text: Beobachte Playlists und Künstler. Neue Songs und neue Veröffentlichungen laden sich von selbst herunter, nach dem Zeitplan, den du wählst.
    link: /de/features/playlist-monitor/
  - icon: server
    title: Gemacht für deinen Heimserver
    text: Ein Docker-Image für amd64 und arm64, SQLite oder PostgreSQL, Konten für alle im Haus mit optionalem Single Sign-on und Playlists, die Jellyfin, Navidrome und Plex erkennen.
    link: /de/getting-started/
  - icon: shield
    title: Ohne Haken
    text: Kein Spotify-API-Schlüssel, kein Entwicklerkonto, kein Premium. Die App hat keine Werbung, keine Nutzungsstatistiken und nichts hinter einer Bezahlschranke. Sie ist frei und quelloffen.
    link: /de/contributing/
showcase:
  - shot: now-playing
    label: Wiedergabe
    caption: Der Songtext folgt dem Song Zeile für Zeile, neben dem Cover und dem, was als Nächstes kommt.
    alt: Die Wiedergabeansicht im Vollbild, mit dem Albumcover, dem zeitsynchronen Songtext mit hervorgehobener aktueller Zeile und der Warteschlange.
  - shot: karaoke
    label: Karaoke
    caption: Große Songtexte, die sich füllen, während jede Zeile gesungen wird, bereit für einen zweiten Bildschirm.
    alt: Die Karaoke-Ansicht, mit großen Songtexten, die sich über einem bewegten Hintergrund in den Farben des Covers füllen.
  - shot: home
    label: Startseite
    caption: Einen Link einfügen oder nach etwas Neuem suchen, und dort weitermachen, wo du aufgehört hast.
    alt: Die Startseite, mit einem Feld zum Einfügen eines Links oder zum Suchen, Bibliotheksstatistiken, dem gerade laufenden Album und zuletzt hinzugefügten Alben.
  - shot: library
    label: Bibliothek
    caption: Alben, Künstler, Playlists und Titel, sortiert und gefiltert, wie du willst.
    alt: Die Seite Bibliothek, mit einem Raster aus Albumcovern und Tabs für Alben, Künstler, Playlists und Titel.
  - shot: playlist
    label: Playlists
    caption: Deine eigenen Playlists mit eigenem Cover, zum Abspielen, Teilen oder Herunterladen als ZIP.
    alt: Eine Playlist-Seite, mit Cover, Schaltflächen und Songs mit Album, Format und Veröffentlichungsdatum.
  - shot: phones
    label: Auf dem Handy
    caption: Dieselbe App auf deinem Handy, installierbar aus dem Browser.
    alt: Downtify auf drei Handys, mit der Startseite, der Wiedergabe und der Bibliothek.
pipeline:
  - icon: link
    title: Link einfügen
    text: Spotify, YouTube Music, Deezer oder SoundCloud. Oder einfach einen Song eintippen.
  - icon: search
    title: Audio finden
    text: Der beste Treffer auf YouTube Music, geprüft anhand der Länge. Weitere Quellen, wenn du willst.
  - icon: download
    title: Laden und taggen
    text: yt-dlp und ffmpeg holen es. Cover, Songtext und Tags kommen in die Datei.
  - icon: music
    title: Überall hören
    text: Im Browser, auf dem Handy oder in Jellyfin, Navidrome und Plex.
quickStart:
  - text: Installationsanleitung
    link: /de/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /de/getting-started/docker-compose/
  - text: Installation mit einem Klick
    link: /de/getting-started/one-click/
apps:
  - icon: smartphone
    title: Downtify für Android
    text: Die offizielle App. Sie findet deinen Server im Netzwerk, streamt im WLAN in Originalqualität und mit mobilen Daten in geringerer, hält Songs offline bereit und funktioniert mit Android Auto. Noch im Test, auf GitHub Releases und Obtainium.
    link: https://github.com/henriquesebastiao/downtify-android
  - icon: tablet-smartphone
    title: Downtify für iOS
    text: Von einem Community-Mitglied für iPhone und iPad gebaut (iOS 17 oder neuer), mit Offline-Songs und Steuerung auf dem Sperrbildschirm. Die öffentliche Beta gibt es über TestFlight.
    link: https://github.com/michaelmoskie/Downtify-IOS-Client
community:
  - text: Stern auf GitHub
    link: https://github.com/henriquesebastiao/downtify
    icon: star
    primary: true
  - text: Sponsern
    link: https://github.com/sponsors/henriquesebastiao
    icon: heart
  - text: Übersetzen
    link: /de/features/internationalization/
    icon: languages
  - text: Mitmachen
    link: /de/contributing/
    icon: git-pull-request
---

## Warum Downtify

<HomeHighlights :items="$frontmatter.why" />

## Ein genauerer Blick

<HomeShowcase :items="$frontmatter.showcase" />

## So funktioniert es

Downtify braucht keinen Spotify-API-Schlüssel und lädt nie etwas von Spotify herunter. Es liest aus öffentlichen Quellen, worauf ein Link zeigt, wählt das Audio auf YouTube Music, dessen Länge am besten passt, lädt es mit `yt-dlp` herunter, wandelt es mit `ffmpeg` um und taggt es mit `mutagen`, alles in einem einzigen Docker-Container. YouTube springt ein, wenn nichts gut passt, und SoundCloud, Soulseek und Deemix kommen dazu, wenn du sie einschaltest. [Jeder Schritt im Detail](how-it-works.md).

<HomePipeline :steps="$frontmatter.pipeline" />

## Was du einfügen kannst

| Quelle        | Was geht                             | Beispiel                            |
| ------------- | ------------------------------------ | ----------------------------------- |
| Spotify       | Titel, Alben, Playlists, Künstler    | `open.spotify.com/playlist/…`       |
| YouTube Music | Songs, Alben, Playlists, Künstler    | `music.youtube.com/playlist?list=…` |
| YouTube       | Videos                               | `youtube.com/watch?v=…`             |
| Deezer        | Titel, Alben, Playlists, Künstler    | `deezer.com/album/…`                |
| SoundCloud    | Titel                                | `soundcloud.com/artist/track`       |
| Suche         | Was du eintippen würdest             | `The Night Owls Do I Still Recall`  |
| CSV           | Bibliotheksexporte                   | Soundiiz, TuneMyMusic, Exportify    |

## Alles, was es kann

Jede Funktion hat ihre eigene Seite, auf der jede Option erklärt ist. [Alle Funktionen auf einen Blick](features/index.md).

<HomeFeatures />

## In einer Minute startklar

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Öffne [`localhost:8000`](http://localhost:8000), melde dich als **admin** mit dem Passwort **downtify** an und füge einen Link ein. Ändere dieses Passwort gleich unter **Einstellungen → Allgemein**. Deine Musik landet in `/path/to/music`, samt Tags.

<HomeActions :actions="$frontmatter.quickStart" />

## Häufige Fragen

::: details Brauche ich ein Spotify-Konto, Premium oder einen API-Schlüssel?
Nein. Downtify liest Titel-, Album- und Playlist-Daten aus den öffentlichen Embed-Seiten von Spotify, braucht also keinerlei Zugangsdaten, und das Audio kommt nie von Spotify. Siehe [So funktioniert es](how-it-works.md).
:::

::: details Woher kommt das Audio, und wie gut ist es?
Standardmäßig von YouTube Music: das Ergebnis, dessen Länge am besten zum Song passt, mit YouTube als Ausweichquelle. Wähle MP3, FLAC, M4A, OGG oder Opus mit der Bitrate, die du willst, oder behalte das beste Audio der Quelle ohne Neukodierung. Verlustfreie Dateien kommen aus Quellen, die du selbst hinzufügst: deinem eigenen [Soulseek-Server (slskd)](features/slskd-navidrome.md), dessen Dateien ihr Originalformat behalten, oder einem [Deemix](features/deemix.md)-Server. Siehe [Download-Einstellungen](features/download-settings.md).
:::

::: details Funktioniert es mit Jellyfin, Navidrome oder Plex?
Ja. Die Dateien werden so getaggt, wie Medienserver es erwarten, in `Künstler/Album/`-Ordnern abgelegt, und jede Playlist bekommt eine Standard-M3U-Datei, die sie erkennen. Navidrome kann außerdem Playlists synchronisiert und Bewertungen von Deezer gesetzt bekommen. Siehe [Dateiorganisation](features/file-organization.md) und [M3U-Export](features/m3u-export.md).
:::

::: details Läuft es auf einem Raspberry Pi oder einem NAS?
Das Image gibt es für `amd64` und `arm64`, und Umbrel, CasaOS und HomeDock OS installieren es mit einem Klick. Siehe [Installation mit einem Klick](getting-started/one-click.md).
:::

::: details YouTube sagt „Sign in to confirm you're not a bot“. Was nun?
Lade unter **Einstellungen → YouTube-Cookies** eine `cookies.txt` hoch; Downtify hält diese Sitzung dann von selbst angemeldet. Wenn YouTube dich trotzdem drosselt, erhöhe die _Pause zwischen Downloads_, senke _Parallele Downloads_ und versuche dann `DOWNTIFY_FORCE_IPV4=1`. Siehe [Fehlerbehebung](troubleshooting.md) und [YouTube-Cookies](features/youtube-cookies.md).
:::

## Nimm es mit

<HomeHighlights :items="$frontmatter.apps" />

Jeder andere Client kann dieselbe API nutzen: siehe den [Vertrag für mobile Clients](mobile-client-contract.md).

<div class="home-cta">

## Offen entwickelt

Downtify ist frei und quelloffen. Mehr als 35 Menschen haben Code beigetragen, Übersetzerinnen und Übersetzer aus der Community haben es in 12 Sprachen gebracht, und viele Funktionen begannen als Idee, die jemand in einem Issue eröffnet hat. Wenn es sich einen Platz auf deinem Server verdient hat, gib ihm einen Stern auf GitHub, erzähl einer Freundin oder einem Freund davon, die selbst hosten, oder sponsere die Entwicklung: Das hilft, die Zeit zu bezahlen, die in jede Version fließt.

<HomeActions :actions="$frontmatter.community" />

</div>
