---
icon: lucide/sparkles
---

# Funktionen

Downtify deckt alles ab, was du brauchst, um aus Spotify eine lokale Musikbibliothek aufzubauen und zu pflegen.

## Überblick

| Funktion | Was sie tut |
|---------|-------------|
| [Charts](charts.md) | Die globale Hitliste von Deezer durchstöbern und herunterladen, was gerade angesagt ist |
| [Ähnliche Titel](similar.md) | Nenne einen Künstler oder Titel; YouTube Music antwortet mit ähnlichen Titeln, die sich vollständig abspielen und herunterladen lassen, ohne Schlüssel |
| [Finder](finder.md) | Bei Deezer suchen und dann einen Künstler, seine Alben und die Titel jedes Albums in Spalten durchblättern |
| [Download-Einstellungen](download-settings.md) | Format (MP3/FLAC/M4A/OGG/OPUS), Bitrate, parallele Downloads und Pause zwischen Downloads wählen |
| [Playlist-Überwachung](playlist-monitor.md) | Spotify- oder YouTube-Music-Playlists und -Künstler beobachten und neue Titel und Veröffentlichungen automatisch herunterladen |
| [Ausgeblendete Playlist-Titel](hidden-playlist-songs.md) | Nimm ungewollte Titel aus einer heruntergeladenen oder überwachten Playlist und halte sie draußen; die Dateien bleiben in der Bibliothek |
| [Top-Songs](top-songs.md) | Den Link eines Künstlers einfügen und seine beliebtesten Songs herunterladen, optional als Playlist |
| [Bibliotheksimport (CSV)](library-import.md) | Einen Bibliotheksexport von Soundiiz, TuneMyMusic oder Exportify importieren und alles in die Warteschlange stellen |
| [Integrierter Player](player.md) | Die Bibliothek im Browser abspielen: Warteschlangenverwaltung, synchrone Songtexte, Schlaf-Timer, Tastatur und Mediatasten |
| [Lieblingssongs](liked-songs.md) | Mit einem Herz einen Song liken; eine Playlist aller gelikten Songs entsteht von selbst |
| [Podcasts](podcasts.md) | Eine Sendung per RSS-Feed, Spotify-Link oder Namen abonnieren; neue Folgen werden von selbst geladen und getaggt |
| [Benutzer und Anmeldung](users.md) | Anmeldung mit Benutzername und Passwort (`admin` / `downtify` auf einem neuen Server), Admin- und normale Benutzerkonten, Einstellungen pro Benutzer und ein Aktivitätsprotokoll von Anmeldungen und dem, was jeder hört |
| [Explicit-Kennzeichnung](explicit-marker.md) | Das „E“ neben Songs mit expliziten Texten — in der Suche, der Bibliothek und im Player — und in den Tags der Datei |
| [Audio ersetzen](replace-audio.md) | Falscher Song oder falsche Version? Wähle die richtige auf YouTube Music oder YouTube; die Datei behält Namen, Tags und Playlists |
| [Servereinstellungen](server.md) | Der Port, auf dem Downtify lauscht, in den Einstellungen änderbar (Admins), auf Wunsch mit sofortigem Neustart |
| [Mobile Apps](mobile-apps.md) | Handy-Apps per QR-Code koppeln und die Bibliothek an sie streamen (original oder transkodiert) |
| [Entdecken](discover.md) | Künstler, Alben und Playlists, die du noch nicht hast, vorgeschlagen anhand von Bibliothek, Likes und Hörverhalten; ausblenden, was du nicht willst |
| [slskd und Navidrome](slskd-navidrome.md) | Über slskd von Soulseek herunterladen, Playlists in Navidrome spiegeln und Playlist-Downloads verfolgen |
| [Bibliothekskatalog und Pfadabgleich](library-catalog.md) | Wie Downtify Bibliotheksdateien und Playlists verfolgt, in der Bibliothek angelegte Playlists und das Reparieren von Pfaden nach dem Verschieben von Dateien |
| [Vorhandene Musikordner](external-library.md) | Downtify auf Ordner mit vorhandenem Audio richten; die Synchronisierung liest Tags, ordnet Künstler zu und überspringt Songs, die schon in der Bibliothek sind |
| [Bibliothek verbessern](library-upgrade.md) | Bereits heruntergeladene Musik scannen und kleine Cover, fehlende Songtexte und unvollständige Tags reparieren |
| [M3U-Export](m3u-export.md) | Automatisch erzeugte Playlist-Dateien für Jellyfin, Navidrome, Plex und jede Medien-App |
| [Playlist-Cover](playlist-cover-art.md) | Das eigene Titelbild der Playlist neben ihrer M3U-Datei speichern |
| [Künstlerfoto, Banner und Bio](artist-images.md) | Ein echtes Foto und Banner für einen Künstler von YouTube Music, Deezer, Spotify oder aus eigenem Upload wählen und Bio, Herkunft und Links von Apple Music und Deezer holen, automatisch oder auf Abruf |
| [Dateiorganisation](file-organization.md) | Flaches Layout oder Unterordner pro Künstler |
| [Songtexte](lyrics.md) | Songtexte (einfach und zeitsynchron) automatisch herunterladen und einbetten; `.lrc` neben der Datei oder in einem Ordner deiner Wahl |
| [YouTube-Cookies](youtube-cookies.md) | Eine `cookies.txt` über die Weboberfläche hochladen, um explizite/altersbeschränkte Titel herunterzuladen |
| [Internationalisierung](internationalization.md) | Englisch plus neun weitere Sprachen ab Werk, dazu die Dokumentation in allen |
| [Update-Benachrichtigungen](updates.md) | Stündliche Prüfung der GitHub Releases; in der Seitenleiste erscheint ein Hinweis, sobald eine neuere Version da ist |

## Eingabearten

Downtify akzeptiert in der Suchleiste mehrere Eingabearten:

| Eingabe | Beispiel |
|-------|---------|
| Spotify-URL eines Titels, Albums, einer Playlist oder eines Künstlers | `https://open.spotify.com/track/…` |
| YouTube-/YouTube-Music-URL | `https://www.youtube.com/watch?v=…` |
| URL einer YouTube-Music-Playlist oder eines Künstlers | `https://music.youtube.com/playlist?list=…` |
| Deezer-URL eines Titels, Albums, einer Playlist oder eines Künstlers | `https://www.deezer.com/track/…` |
| Freitextsuche | `The Night Owls Do I Still Recall` |

Freitextsuchen gehen direkt an YouTube Music — ein Spotify-Link ist nicht nötig.
