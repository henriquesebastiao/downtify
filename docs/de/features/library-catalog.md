---
icon: lucide/library
---

# Bibliothekskatalog und Pfad-Synchronisierung

Downtify führt einen kleinen **Katalog** der Dateien unter `/downloads` (den slskd-Ordner, wenn [slskd-Dateien an Ort und Stelle gelassen werden](slskd-navidrome.md#leave-files-in-place), und [zusätzliche Ordner](external-library.md), die du in den Einstellungen hinzufügst), damit Bibliotheksseite, Player, M3U-Export, Navidrome-Synchronisierung und Dublettenerkennung konsistent bleiben, wenn Dateien verschoben werden oder Playlists wachsen.

## Was gespeichert wird

| Speicher | Ort | Zweck |
|-------|----------|---------|
| **Titelindex** | `/data/downtify_library.db` | Ordnet Spotify-Titel-IDs Bibliothekspfaden zu, damit ein bereits auf der Festplatte liegender Titel erkannt werden kann |
| **Playlist-Katalog** | `/data/downtify_library.db` | Welche Titel zu jeder heruntergeladenen Spotify-Playlist gehören |
| **Playlist-Downloads** | `/data/downtify_library.db` | Verfolgte Spotify-Playlist-Downloads und ein Cache ihrer Spotify-Titellisten |
| **Navidrome-Index** | `/data/downtify_library.db` | Navidrome-Song-IDs pro Datei |
| **Metadaten-Cache der Bibliothek** | `/data/downtify_library.db` | Titel, Künstler, alle genannten Künstler, Album, Album-Künstler, Titelnummer, Jahr, Länge und Covergröße pro Datei für `GET /tracks`, nur neu gelesen, wenn sich Änderungsdatum oder Größe einer Datei ändern |
| **Verbesserungsläufe** | `/data/downtify_library.db` | Die Warteschlange von [Bibliothek verbessern](library-upgrade.md) und wann jeder Titel zuletzt geprüft wurde, damit ein Lauf einen Neustart übersteht |
| **Pfadscan-Cache** | RAM, plus ein Snapshot in `/data/downtify_library.db` | Zusammengefasste Zeilen von `GET /tracks`, Playlist-Listen und Pfadpaare. UI-Routen liefern diesen Snapshot, ohne die Festplatte zu durchlaufen. Jeder fertige Download wird **sofort in den Snapshot eingemischt** (damit ein neuer Künstler ohne Warten erscheint). Ein Löschen **nimmt diese Dateien sofort aus dem Snapshot** (damit ein Album ohne Warten aus dem Raster verschwindet). Ein vollständiger Durchlauf des Baums läuft im Hintergrund wenige Sekunden, nachdem die Download-Warteschlange leer ist — nicht nach einem festen Timer. `GET /list?refresh=true` verwirft den Snapshot und scannt sofort neu. |
| **Verborgene Elemente** | `/data/downtify_library.db` | Die Songs, Alben und Künstler, die ein Admin [vor Benutzern verborgen](users.md#hiding-from-users) hat |
| **Cover-Cache** | `/data/cover_cache` (optional) | Extrahierte Coverbilder für `GET /cover` |

Dateien werden über Verschiebungen hinweg durch einen **Inhaltsschlüssel** zugeordnet — einen Hash aus Dateiname und Größe. Das Verschieben einer Datei in einen anderen Ordner behält ihren Schlüssel; sie durch eine andere Datei zu ersetzen gibt ihr einen neuen.

## Einstellungen → Bibliothek

### Cover auf der Festplatte zwischenspeichern

Ist es an, hält Downtify extrahierte Coverbilder unter `/data/cover_cache`, damit Bibliothek und Player nicht für jedes Vorschaubild die Tags neu lesen. Jederzeit gefahrlos abschaltbar; es kostet nur Speicherplatz.

### Bibliothekspfade korrigieren

Nutze das, nachdem du **Dateien außerhalb von Downtify auf der Festplatte verschoben oder umbenannt** oder von Hand gelöscht hast.

1. Öffne **Einstellungen → Bibliothek → Bibliothekspfade korrigieren**.
2. Downtify scannt die Bibliotheksordner und:
    - **aktualisiert Pfade** im Titelindex und Playlist-Katalog, wenn eine Datei nicht mehr dort ist, wo sie war, dieselbe Datei (gleicher Inhaltsschlüssel) aber anderswo gefunden wird;
    - **entfernt veraltete Einträge** für Dateien, die nicht mehr existieren;
    - **indexiert** ältere Einträge, die vor der Einführung der Inhaltsschlüssel gespeichert wurden;
    - **führt [Lieblingssongs](liked-songs.md#keeping-likes-in-step-with-the-files)** an ihren neuen Ort nach.
3. Sind **M3U erzeugen** und/oder **Playlists in Navidrome erstellen** aktiviert, werden die betroffenen Playlists neu geschrieben.

Es läuft nur, wenn du die Schaltfläche drückst (oder `POST /api/library/reconcile` aufrufst) — nie nach Zeitplan.

### Vorhandene Musikordner

Um eine Sammlung abzuspielen, die Downtify nicht heruntergeladen hat, füge die Ordner unter **Einstellungen → Bibliothek** hinzu und drücke **Ordner synchronisieren**. Die Dateien bleiben auf der Festplatte; Tags werden gelesen und Künstler zugeordnet. Siehe [Vorhandene Musikordner](external-library.md).

::: warning
Das Neuschreiben einer Playlist löscht Bibliotheksdateien, deren Tags erkennbar nicht zu dem Spotify-Titel passen, für den sie registriert sind — siehe [slskd und Navidrome](slskd-navidrome.md#playlist-sync).
:::

::: info Löschen vs. Verschieben
Das Löschen von Titeln auf der **Bibliothek**-Seite räumt den Katalog bereits auf und schreibt die betroffenen M3U-Dateien und Navidrome-Playlists im Hintergrund neu, danach gibt es also nichts zu korrigieren.
:::

## Bibliotheksseite

Die Bibliotheksseite hat vier Tabs — **Alben**, **Künstler**, **Playlists** und **Titel**:

- **Alben, Künstler und Playlists** erscheinen als Cover-Raster oder kompakte Liste (der Umschalter wird gemerkt), mit Textfilter und Sortierung nach zuletzt hinzugefügt, Name, Künstler, Jahr oder Titelanzahl. Alben und Künstler werden aus den Tags jeder Datei aufgebaut (Album-Künstler, Album, Jahr), hängen also nicht davon ab, wie die Dateien auf der Festplatte organisiert sind. Eine Compilation — Album-Künstler `Various Artists`, mit dem Compilation-Flag — bleibt unter Alben ein einziges Album, während ihre Titel auf den Seiten ihrer Künstler stehen. Ein Titel mit `Various Artists` ohne dieses Flag (so haben ältere Versionen jeden Song mit mehreren Künstlern getaggt, auch ein Duo wie `Zé Neto & Cristiano`) wird stattdessen nach seinem ersten Künstler gruppiert. Ein Titel ohne Album-Tag erscheint unter Titel und seinem Künstler, nicht unter Alben.
- **Künstler** listet jeden Künstler, dem ein Titel gehört — seinem Album-Künstler, bei einer Compilation (oder einer Datei ohne Album-Künstler) seinem ersten Künstler. Die Seite dieses Künstlers enthält auch die Titel, auf denen er Gast ist, mit **Gast** gekennzeichnet; sein Alben-Tab zeigt nur eigene Alben (und ist ausgeblendet, wenn es keine gibt). Ein Name, der immer nur neben jemand anderem genannt wird, bekommt keine eigene Seite: Tags können die Mitglieder eines Duos einzeln nennen (`Henrique; Juliano`, wie YouTube Music manche Duos nennt und ältere Downtify-Versionen sie schrieben), und eine Seite pro Mitglied wäre ein Künstler, den es nicht gibt. **Various Artists** wird nicht aufgeführt: Die Titel einer Compilation stehen auf den Seiten ihrer Künstler, und das Album selbst bleibt unter Alben.
- Überall, wo ein Titel seine Künstler zeigt — Titellisten, die Jetzt-läuft-Ansicht, Finder- und Top-Song-Zeilen — führt jeder Name zur Bibliotheksseite des Künstlers oder zu einer Suche nach ihm, wenn die Bibliothek keine Seite für ihn hat. In diesen Zeilen führt auch der Albumname zum Album in der Bibliothek oder zu einer Suche danach, wenn die Bibliothek es nicht hat. Entdecken und sein Finder schicken dich nie zur Suche: Dort ist ein Künstler oder Album, das die Bibliothek nicht hat, einfacher Text. Die Künstler stammen aus dem `ARTISTS`-Tag der Datei (siehe [Mehrere Künstler und Compilations](file-organization.md#several-artists-and-compilations)), sodass ein Name wie *Earth, Wind & Fire* nie am Komma getrennt wird; bei einer Datei ohne diesen Tag wird der Künstlertext an `;`, ` / ` oder `, ` getrennt, außer dieser Text ist auch der Album-Künstler der Datei, oder die Namen, in die er zerfällt, ergeben den Album-Künstler (`Henrique; Juliano` auf einem Album von `Henrique, Juliano`) — dann ist es ein Name.
- **Playlists** sind die heruntergeladenen Playlists mit einer [M3U-Datei](m3u-export.md), Playlists, die du mit **Neue Playlist** erstellst (bearbeitbar), sowie verfolgte [Playlist-Downloads](slskd-navidrome.md#playlist-downloads), die noch keine M3U haben. Importierte Spotify-/YouTube-Playlists bleiben schreibgeschützt, bis du sie [löst](#detach-an-imported-playlist). Playlists, die andere [mit dir teilen](users.md#sharing-playlists), stehen unter dem Raster, getrennt von deinen eigenen. Sobald du einen Song [geliked](liked-songs.md) hast, steht *Lieblingssongs* zuerst. Eine von dir erstellte Playlist nutzt ein Mosaik aus bis zu vier Titelcovern; importierte Playlists behalten das mit der M3U gespeicherte Artwork.
- **Titel** ist eine sortierbare Tabelle (Titel, Album, Format, Hinzufügedatum, Länge) mit Textfilter, Formatfilter und Kontrollkästchen — klicke eines an, dann mit Umschalt ein anderes, um einen Bereich auszuwählen. Sortiere durch Klick auf eine Spaltenüberschrift oder mit dem Menü **Sortieren nach** über der Tabelle (die einzige Möglichkeit am Handy, wo die Überschriften verborgen sind): zuletzt hinzugefügt oder älteste zuerst, Titel, Künstler oder Album A–Z oder Z–A, längste oder kürzeste zuerst. Die Wahl wird gemerkt.

Die Songs einer Playlist haben dasselbe Menü **Sortieren nach**, mit **Reihenfolge der Playlist** (die eigene Reihenfolge der Playlist, mit der sie beginnt) als zusätzlicher Auswahl; ein Klick auf eine Spaltenüberschrift funktioniert ebenfalls. **Abspielen** und die Songliste folgen der gewählten Reihenfolge, und die Wahl wird für jede Playlist gemerkt.

Das Öffnen eines Albums, Künstlers oder einer Playlist zeigt die Titel mit **Abspielen**, **Zufallswiedergabe** und **Zur Warteschlange hinzufügen**. **Als ZIP herunterladen** ist auf der Seite einer Playlist eine Schaltfläche und auf der eines Albums im **⋯**-Menü. Eine von dir erstellte Playlist hat zusätzlich **Titel hinzufügen**, **Umbenennen** und **Teilen…** (siehe [Playlists teilen](users.md#sharing-playlists)); eine importierte hat **Teilen…** und **Von der Quelle lösen** (unten); die Seite einer heruntergeladenen Playlist zeigt, wie viele ihrer Titel heruntergeladen sind, listet die fehlenden mit **Fehlende herunterladen** auf und bietet **Auf neue Titel achten**. **Playlist löschen** steht im **⋯**-Menü: importierte Playlists löschen das Audio; eine von dir erstellte Playlist entfernt nur die Playlist.

### Eine Playlist durchsuchen

Eine lange Playlist zeichnet nur die Titel, die gerade auf dem Bildschirm sind, deshalb sieht die Suche des Browsers (`Ctrl` + `F`) den Rest nicht. Das Feld **In dieser Playlist suchen** über den Titeln durchsucht sie alle – Titel, Künstler, Album und Dateiname, ohne Rücksicht auf Groß- und Kleinschreibung oder Akzente. Auf der Seite einer Playlist setzt `Ctrl` / `⌘` + `F` den Cursor hinein (im Feld noch einmal gedrückt öffnet es die Suche des Browsers), und `Esc` leert es.

Daneben grenzen Filter die Liste ein. Jeder zeigt, wie viele Titel er enthält, und erscheint nur, wenn er welche hat:

| Filter | Zeigt |
|--------|-------|
| **Alle** | Alle heruntergeladenen Titel der Playlist |
| **Fehlend** | Titel der Quell-Playlist, die noch nicht in der Bibliothek sind (Downloads von Spotify-Playlists), mit ihrem Download-Status – beim Auswählen bei Spotify nachgeschlagen |
| **Fehlgeschlagen** | Die fehlenden Titel, deren Download fehlgeschlagen ist, jeweils mit einer Schaltfläche für einen neuen Versuch – sobald **Fehlend** nachgeschlagen wurde |
| **YouTube Music**, **Soulseek (slskd)**, **Deemix** … | Die Titel, die diese Quelle geholt hat. Downtify merkt sich das für Titel, die ab jetzt heruntergeladen werden; ältere zählen als **Unbekannte Quelle**, außer slskd-Dateien, die an ihrem Ort bleiben, und Titeln aus deinen eigenen Ordnern |
| **Nicht in Navidrome** | Bei eingeschalteter [Navidrome-Synchronisierung](slskd-navidrome.md) die Titel, die Downtify noch keinem Navidrome-Titel zugeordnet hat |

Suche und Filter wirken zusammen, und darunter steht, wie viele Titel angezeigt werden. Jeder Titel behält seine Nummer in der Playlist, und Sortieren, Abspielen und das Menü jedes Titels beziehen sich auf das Angezeigte.

### Eine importierte Playlist lösen

Eine aus einem Spotify- oder YouTube-Music-Link importierte Playlist kann nicht bearbeitet werden, weil Downtify sie mit ihrer Quelle synchron hält. Um eine aufzuräumen — einen Song entfernen, der nicht dazugehört, einen hinzufügen, der dazugehört — öffne sie und wähle **Von der Quelle lösen**. Sie wird zu einer Playlist wie die, die du erstellst: Ihre Songs und ihr Besitzer bleiben, wie sie sind, und du erhältst **Titel hinzufügen**, **Umbenennen** und das Entfernen von Songs. Im Gegenzug wird die Verbindung zur Quelle gekappt: Sie wird nicht mehr von Spotify oder YouTube Music aktualisiert, ihre Beobachtung in der [Playlist-Überwachung](playlist-monitor.md) (falls vorhanden) wird entfernt, und ihr „fehlende Songs“-Tracking verschwindet. Bereits heruntergeladene Songs werden nie angefasst, und ihr Artwork bleibt bis zu deiner ersten Bearbeitung, wenn ein Mosaik ihrer Songs es ersetzt. Das Lösen lässt sich in der App nicht rückgängig machen; den Link erneut herunterzuladen erzeugt eine neue importierte Playlist.

Jedes Konto sieht dieselbe Bibliothek: Was ein Admin [vor Benutzern verbirgt](users.md#hiding-from-users), fehlt für sie, und ein Admin sieht alles, mit einem durchgestrichenen Auge an dem, was verborgen ist. Admins verbergen und zeigen über das `…`-Menü eines Songs, Albums oder Künstlers oder über die Auswahlleiste in **Titel**.

**Als ZIP herunterladen** speichert die ausgewählten Titel als einzelnes ZIP auf dem Gerät, von dem aus du browst, und behält ihre Ordnerstruktur — praktisch, wenn Downtify auf einem Heimserver läuft und du einen Stapel Titel lokal haben willst. Kombiniere es mit **Alle auswählen**, um alles mitzunehmen, was der aktuelle Filter zeigt. Das Archiv wird beim Herunterladen aufgebaut, sodass nichts auf die Festplatte des Servers geschrieben wird, und ist auf 2000 Titel pro Download begrenzt.

## API

| Methode | Pfad | Beschreibung |
|--------|------|-------------|
| `GET` | `/list?refresh=true` | Bibliothekspfade unter Umgehung des Pfadscan-Caches |
| `GET` | `/api/library/summary` | Zahlen der Startseite und neueste Alben, ohne die vollständige Titelliste |
| `GET` | `/api/library/albums` | Album-Kacheln (Zahlen + Coverdatei), ohne jeden Titel |
| `GET` | `/api/library/artists` | Künstler-Kacheln (Zahlen + Coverdatei) für Bibliothek und Entdecken |
| `GET` `POST` | `/api/library/visibility` | Admins: was vor Benutzern verborgen ist, und Elemente verbergen / zeigen |
| `POST` | `/api/library/lookup` | Bibliothekszeilen für bereits heruntergeladene Songs aus Suche/Links |
| `GET` | `/tracks` | Bibliothekstitel mit Tags. `?playlist=`, `?artist=`, `?album=`, `?q=` und `?limit=` liefern eine Teilmenge |
| `GET` | `/media/{path}` | Liefert eine Bibliotheksdatei aus, auch `slskd/…`- und `ext/…`-Pfade |
| `GET` | `/playlist-cover?file=…` | Liefert das eigene [Cover](playlist-cover-art.md) einer Playlist aus, von `/playlists` als `cover` gemeldet |
| `POST` | `/api/library/archive` | Bereitet ein ZIP der ausgewählten Titel vor (gibt ein Einmal-Ticket zurück) |
| `GET` | `/api/library/archive/{token}` | Streamt dieses ZIP zum Browser |
| `DELETE` | `/api/library/playlist?playlist_name=…` | Löscht Titel, M3U und Katalog einer importierten Playlist — oder nur die M3U einer von dir erstellten Playlist |
| `POST` | `/api/library/playlists` | Erstellt eine leere bearbeitbare Playlist |
| `POST` | `/api/library/playlists/tracks` | Fügt Bibliotheksdateien zu einer von dir erstellten Playlist hinzu oder entfernt sie |
| `POST` | `/api/library/playlists/rename` | Benennt eine von dir erstellte Playlist um |
| `PUT` | `/api/library/playlists/visibility` | [Teilt eine Playlist](users.md#sharing-playlists), die dir gehört, nur ansehbar |
| `POST` | `/api/library/playlists/copy` | Speichert eine Kopie einer Playlist, die du öffnen kannst, als bearbeitbare eigene |
| `POST` | `/api/library/playlists/detach` | Macht aus einer importierten Playlist eine bearbeitbare |
| `POST` | `/api/library/reconcile` | Korrigiert Bibliothekspfade und aktualisiert dann M3U-/Navidrome-Playlists |
| `POST` | `/api/library/external/sync` | Startet einen Hintergrundscan zusätzlicher Musikordner |
| `GET` | `/api/library/external/sync` | Laufende Synchronisierung zusätzlicher Ordner oder das letzte abgeschlossene Protokoll |
| `POST` | `/api/library/external/unmap` | Nimmt einen zusätzlichen Ordner aus der Bibliothek, ohne Audio zu löschen |
| `GET`/`POST` | `/api/library/upgrade…` | Scannt und repariert, was schon heruntergeladen ist — siehe [Bibliothek verbessern](library-upgrade.md#api) |

Siehe die [API-Referenz](../api-reference.md#library) für Anfrage- und Antwortformate.
