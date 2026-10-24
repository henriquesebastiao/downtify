---
icon: lucide/file-headphone
---

# Dateiorganisation

Ein neuer Server organisiert Dateien nach Künstler und Album (`Künstler/Album/…`): **Nach Künstler sortieren** und **Nach Album sortieren** sind standardmäßig beide aktiv. Schalte sie aus, um die flache Struktur unten zu erhalten. Server, die vor dieser Voreinstellung eingerichtet wurden, behalten ihre bisherige Wahl.

## Flache Struktur (beide aus)

Einzelne Titel und YouTube-Suchen landen direkt im Hauptverzeichnis des Download-Ordners. Playlist- und Albumtitel kommen in einen Unterordner pro Playlist oder Album:

```
downloads/
├── My Playlist/
│   ├── My Playlist.m3u
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── Tame Impala - The Less I Know The Better.mp3
└── The Night Owls - R U Awake.mp3       ← einzelner Titel
```

## Nach Künstler sortieren

Ist **Einstellungen → Downloads und Dateien → Nach Künstler sortieren** aktiv (Standard), werden alle Titel — auch Playlist- und Album-Downloads — in einem Unterordner nach dem Hauptkünstler zusammengefasst:

```
downloads/
├── The Night Owls/
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── The Night Owls - R U Awake.mp3
├── Tame Impala/
│   └── Tame Impala - The Less I Know The Better.mp3
└── Playlists/
    └── My Playlist.m3u
```

Diese Struktur ist mit Medienservern (Jellyfin, Navidrome, Plex) und Bibliotheksverwaltungen (Beets) kompatibel, die ein Ordnerlayout `Künstler/Titel.ext` erwarten.

## M3U und Künstlerordner

Ist *Nach Künstler sortieren* aktiv und du lädst eine Spotify-Playlist mit ebenfalls aktivierter M3U-Erzeugung herunter, wird die M3U in `<downloads>/Playlists/<Playlist-Name>.m3u` statt im Playlist-Unterordner abgelegt. Das liegt daran, dass die Titel nun auf mehrere Künstlerordner verteilt sind. Die relativen Pfade in der M3U werden weiterhin korrekt aufgelöst, egal wo du die Bibliothek einbindest.

## Die Einstellung ändern

Die Einstellung gilt sofort für alle **neuen** Downloads. Bereits vorhandene Dateien werden nicht verschoben.

## Das Löschen eines Titels räumt leere Ordner auf

Wird ein Titel auf der Bibliotheksseite gelöscht, entfernt das auch seinen Playlist-, Künstler- oder Albumordner, sobald er leer ist — und steigt weiter durch alle nun leeren übergeordneten Ordner hinauf (z. B. den Künstlerordner, nachdem sein letztes Album weg ist), bis zum Download-Verzeichnis selbst, das nie entfernt wird. Ein Ordner, der noch etwas anderes enthält — einen weiteren Titel, eine `.m3u`, eine noch genutzte `cover.jpg` —, bleibt unangetastet.

## Mehrere Titel auf einmal auswählen und löschen

Die Titelliste der Bibliothek hat bei jedem Titel ein Kontrollkästchen sowie ein Kästchen **Alle auswählen**, das alle Titel auswählt, die zum aktuellen Filter passen (siehe [Bibliotheksseite](library-catalog.md#library-page)). **Aus Bibliothek löschen** in der Auswahlleiste entfernt alle in einer einzigen Anfrage (`DELETE /delete/batch`, siehe [API-Referenz](../api-reference.md)), mit derselben Aufräumarbeit pro Titel (`.lrc`, verwaiste `cover.jpg`, leere Ordner) wie beim Löschen einzelner Titel.

Um ein ganzes Album oder eine Playlist zu löschen, öffne es und wähle **Löschen** im Menü **⋯**. Für alles von einem Künstler gib seinen Namen in den Filter der Titelliste ein, wähle dann **Alle auswählen** und lösche.
