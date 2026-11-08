---
icon: lucide/list-music
---

# M3U-Export

Downtify erzeugt automatisch eine Standard-Playlist-Datei im Format `EXTM3U`, sobald eine Spotify-Playlist heruntergeladen wird — manuell oder über die [Playlist-Überwachung](playlist-monitor.md).

## Speicherort der Datei

| Situation | M3U-Pfad |
|-----------|---------|
| Playlist normal heruntergeladen | `<downloads>/<Playlist-Name>/<Playlist-Name>.m3u` |
| Playlist mit aktivem *Nach Künstler sortieren* heruntergeladen | `<downloads>/Playlists/<Playlist-Name>.m3u` |

Ist *Nach Künstler sortieren* aktiv, verteilen sich die Titel auf mehrere Künstlerordner; die M3U liegt daher in einem zentralen Verzeichnis `Playlists/` statt im Playlist-Unterordner.

[Lieblingssongs](liked-songs.md) werden ebenfalls in `Playlists/Downtify Liked Songs.m3u` geschrieben — unabhängig vom Layout und davon, ob *M3U-Playlists erstellen* aktiv ist.

## Relative Pfade

Die Titelpfade in der M3U werden **relativ zur M3U-Datei selbst** geschrieben, nicht als absolute Pfade. Dieselbe Datei funktioniert also sowohl, wenn sie innerhalb des Downtify-Containers (`/downloads/…`) gelesen wird, als auch bei einem anderen Verbraucher, der dieselbe Bibliothek unter einem anderen Stammverzeichnis einbindet — etwa Jellyfin unter `/nas/music/…`. Richte deinen Medienserver einfach auf denselben Bibliotheks-Mount, und die Playlist erscheint als eine Einheit.

## Aktivieren / Deaktivieren

Die M3U-Erzeugung steuerst du unter **Einstellungen → Downloads und Dateien → M3U-Playlists erstellen** (standardmäßig an). Ausgeschaltet entfällt die M3U-Erstellung komplett; der übrige Download-Ablauf bleibt unverändert.

## Cover

Direkt unter dieser Einstellung schreibt **Playlist-Cover speichern** (standardmäßig an) das eigene Titelbild der Playlist unter demselben Namen neben ihre M3U — vor den Titeln, damit der Ordner von Anfang an wie die Playlist aussieht. Downtify zeigt dann dieses Artwork für die Playlist statt eines Rasters ihrer Titel-Cover. Eine Playlist, die du in der Bibliothek anlegst, bekommt auf dieselbe Weise ein Mosaik aus bis zu vier Titel-Covern. Siehe [Playlist-Cover](playlist-cover-art.md).

## Wann sie geschrieben wird

Die M3U wird **nach jedem fertig heruntergeladenen Titel** neu geschrieben, die Playlist-Datei wächst also mit dem Download, statt am Ende auf einmal zu erscheinen. Das gilt gleichermaßen für Playlist- und Album-Downloads, [CSV-Importe](library-import.md) und Durchläufe der [Playlist-Überwachung](playlist-monitor.md#m3u-integration).

Damit ist die Playlist ab dem Moment abspielbar, in dem der erste Titel landet, du siehst die Synchronisierung laufend arbeiten, und ein einzelner langsamer oder hängender Download kann nie verhindern, dass die M3U — oder die bereits fertigen Titel — erscheint.

Ein letztes Neuschreiben läuft, sobald der gesamte Durchlauf abgeschlossen ist. Es gleicht jeden Titel mit dem Dateisystem ab (statt mit der Liste im Arbeitsspeicher, was dieser Durchlauf heruntergeladen hat), findet also auch Dateien früherer Durchläufe und korrigiert alles, was sich während des Durchlaufs auf der Platte geändert hat.

Jeder Schreibvorgang listet die Titel in **Playlist-Reihenfolge**, nicht in der Reihenfolge, in der die Downloads fertig wurden; eine teilweise geschriebene M3U ist also trotzdem korrekt sortiert.

::: info Titel, die schon auf der Platte sind
Titel, die ein früherer Durchlauf heruntergeladen hat, bleiben die ganze Zeit in der M3U — sie sind ab dem ersten Schreiben enthalten, nicht erst durch das letzte.
:::

## Neuerzeugung

Die M3U wird bei jedem Durchlauf frisch erzeugt — dieselbe Playlist-URL erneut einzufügen liefert eine vollständige, geordnete Datei, auch mit Titeln, die in früheren Durchläufen fehlten.

Titel, deren Download fehlschlug oder die keinen YouTube-Music-Treffer hatten, werden stillschweigend übersprungen.

## Kompatibilität

Die erzeugte Datei verwendet:

- UTF-8-Kodierung ohne BOM
- LF-Zeilenenden
- Das Standardformat `#EXTM3U` / `#EXTINF`

Das ist kompatibel mit Jellyfin, Navidrome, Plex, VLC, Kodi, Sonos und jedem anderen Player oder Medienserver, der Standard-M3U-Playlists einliest.

## Playlists, die du anlegst

**Bibliothek → Playlists → Neue Playlist** schreibt dieselbe Art M3U unter `Playlists/`, mit einer zusätzlichen Zeile `#EXTDOWNTIFY:manual`, damit Downtify sie von einer heruntergeladenen Spotify-/YouTube-Playlist unterscheiden kann. Du kannst sie umbenennen und Songs hinzufügen oder entfernen (auch aus [zusätzlichen Ordnern](external-library.md)). Das Löschen dieser Playlist, eines Titels oder das Aufheben der Zuordnung eines zusätzlichen Ordners aktualisiert die M3U; Audio wird nur gelöscht, wenn du den Titel selbst oder eine importierte Playlist löschst.

### Songs zu einer Playlist hinzufügen

Admins können Songs an mehreren Stellen in eine dieser Playlists oder in eine neue legen:

- **Das ⋯-Menü eines Songs** (in jeder Titelliste) → **Zu Playlist hinzufügen**.
- **Mehrere Songs auswählen** in der Bibliothek und auf **Zu Playlist hinzufügen** drücken.
- **Das ⋯-Menü eines Albums** → **Zu Playlist hinzufügen** fügt alle Songs des Albums hinzu.
- **Das ⋯-Menü eines Künstlers** (auf der Künstlerseite) → **Zu Playlist hinzufügen** fügt alles hinzu, was der Künstler in deiner Bibliothek hat, Album für Album.

Jedes Menü listet deine Playlists und einen Eintrag **Neue Playlist …**, der eine mit diesen Songs bereits gefüllte Playlist anlegt. Ein Song, den eine Playlist schon hat, wird übersprungen, und die Bestätigung sagt, wie viele tatsächlich hinzugefügt wurden (oder dass alle schon vorhanden waren). Eine Playlist fasst höchstens 500 Songs.
