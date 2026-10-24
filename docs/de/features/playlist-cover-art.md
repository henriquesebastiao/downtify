---
icon: lucide/image
---

# Playlist-Cover

Downtify kann das eigene Cover einer Playlist neben ihrer [M3U-Datei](m3u-export.md) speichern, damit Medienserver und Dateimanager das echte Artwork der Playlist statt eines generischen Symbols anzeigen.

Standardmäßig an. Ausschalten unter **Einstellungen → Downloads und Dateien → Playlist-Cover speichern**.

## Wohin die Datei kommt

Das Cover wird mit **demselben Namen und im selben Ordner wie die M3U der Playlist** geschrieben, nur mit der Endung `.jpg`:

```
<downloads>/<Playlist-Name>/<Playlist-Name>.m3u
<downloads>/<Playlist-Name>/<Playlist-Name>.jpg
```

Sind *Nach Künstler sortieren* oder *Nach Album sortieren* aktiv, verteilen sich die Titel auf Künstlerordner, und die M3U liegt in einem zentralen Verzeichnis `Playlists/` (siehe [Dateiorganisation](file-organization.md)) — das Cover folgt ihr:

```
<downloads>/Playlists/<Playlist-Name>.m3u
<downloads>/Playlists/<Playlist-Name>.jpg
```

::: info Es braucht die M3U
Ist **M3U-Playlists erstellen** aus, wird auch kein Cover gespeichert: Downtify legt das Bild anhand des M3U-Pfads ab, ohne M3U gibt es keinen Ort dafür. Die Einstellung ist ausgeblendet, solange das Schreiben von M3U aus ist.
:::

## Quellen und Auflösung

| Quelle | Auflösung |
|--------|-----------|
| **Spotify** | Das größte Bild, das die öffentliche Einbettungsseite für die Playlist bietet — dasselbe, das schon für die Cover der Titel verwendet wird |
| **YouTube Music** | Immer in 1200×1200 angefordert, unabhängig von der [Cover-Auflösung](download-settings.md#cover-art-resolution), die nur die Cover einzelner Titel betrifft |

Beide Dienste liefern für diese URLs JPEG, auch wenn das Original-Artwork ein PNG war; die Datei wird daher immer als `.jpg` gespeichert.

## Wann es heruntergeladen wird

**Vor den Titeln**, in beiden Fällen — der Ordner sieht schon während des Füllens wie die Playlist aus, und ein Medienserver, der mitten im Download scannt, findet das Artwork statt eines kahlen Ordners:

- **Ein manueller Playlist-Download** — einmal, sobald der Playlist-Name aufgelöst ist, vor dem ersten Titel.
- **[Playlist-Überwachung](playlist-monitor.md)** — einmal pro Durchlauf, der etwas herunterzuladen hat, vor dem ersten Titel dieses Durchlaufs. Ein Durchlauf, der nichts Neues findet, holt es nicht erneut.

Schlägt das Auflösen oder Herunterladen des Covers fehl (Netzwerkfehler, Playlist ohne Artwork), wird das protokolliert und übersprungen — der Download selbst wird dadurch nie aufgehalten oder zum Scheitern gebracht.

## In der Downtify-Oberfläche

Eine Playlist mit eigenem Artwork (heruntergeladen mit einer Spotify- oder YouTube-Playlist) zeigt es überall, wo die Bibliothek Playlists auflistet — im Raster, auf der Playlist-Seite, in der Seitenleiste und im Player. Playlists ohne eigenes Artwork sowie in der Bibliothek angelegte Playlists zeigen ein Mosaik aus bis zu vier verschiedenen Titel-Covern: zwei nebeneinander, drei als hohe Kachel links plus zwei gestapelte rechts, vier als 2×2-Raster. Dieselbe Collage wird als `<Playlist-Name>.jpg` neben der M3U einer manuellen Playlist geschrieben, damit auch Navidrome sie sieht, und neu erstellt, sobald du Songs hinzufügst oder entfernst.

## Navidrome

Nichts zu konfigurieren: Navidrome ermittelt das Playlist-Artwork aus einem **Sidecar-Bild** — einer nach der Playlist benannten Datei im selben Ordner —, und genau das schreibt Downtify. Solange der Musikordner von Navidrome deinen Download-Ordner abdeckt, erscheint das Artwork beim nächsten Scan. Ein API-Aufruf von Downtify ist nicht beteiligt. Siehe [slskd und Navidrome](slskd-navidrome.md#navidrome).

## Aufräumen

Das Löschen einer Playlist auf der Bibliotheksseite entfernt ihr Cover zusammen mit M3U und Titeln — siehe [Eine Playlist löschen](slskd-navidrome.md#deleting-a-playlist).
