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

Ist **Einstellungen → Downloads und Dateien → Nach Künstler sortieren** aktiv (Standard), werden alle Titel — auch Playlist- und Album-Downloads — in einem Unterordner nach dem Albumkünstler zusammengefasst (siehe [Mehrere Künstler und Compilations](#several-artists-and-compilations)):

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

## Mehrere Künstler und Compilations

Ein Song nennt oft mehrere Künstler. Downtify behält sie alle im **Künstler**-Tag der Datei und schreibt jeden zusätzlich einzeln in einen **ARTISTS**-Tag (`TXXX:ARTISTS` bei MP3), damit ein Player einen Namen wie `Earth, Wind & Fire` nie am Komma trennen muss. Der Ordner gehört aber einem einzigen Künstler: dem **Albumkünstler**, bei einer Compilation dem ersten Künstler des Titels.

- Der Albumkünstler ist der Künstler, den die Quelle (Spotify, YouTube Music oder Deezer) für das **Album** nennt, auf jedem Titel derselbe, und er wird in den **Albumkünstler**-Tag geschrieben. Sagt die Quelle nichts, ist es der erste Künstler des Titels.
- Ein Duo oder eine Band ist ein Künstler. YouTube Music nennt manche Acts über ihre Mitglieder, einen pro Eintrag (`Henrique & Juliano` kommt als `Henrique` und `Juliano`, beim Album und bei jedem Titel — manchmal andersherum, `Mateus` und `Jorge` für `Jorge & Mateus`). Jeder genannte Name verlinkt auf einen YouTube-Music-Kanal; führt der Link eines Mitglieds zu einem Kanal mit dem Namen des ganzen Acts, gebildet aus den daneben genannten Namen, fügt Downtify diese Namen wieder zum Namen des Acts zusammen: Ordner, **Albumkünstler**-, **Künstler**- und **ARTISTS**-Tag lauten dann `Henrique & Juliano`. Eine echte Zusammenarbeit (jeder Künstler mit eigenem Kanal) behält alle Künstler. Verlinkt YouTube Music kein Mitglied auf den Kanal des Acts, bleiben die Namen getrennt; die Bibliothek gibt einem Namen, der immer nur neben jemand anderem genannt wird, trotzdem keine eigene Seite (siehe [Bibliothekskatalog](library-catalog.md#library-page)).
- Ein Gast ändert daran nie etwas. *The Girl Is Mine* mit einem Gast auf Michael Jacksons *Thriller* bleibt in `Michael Jackson/Thriller/`, und die Single *Lady Marmalade* (Christina Aguilera, Lil' Kim, Mýa, P!nk) kommt nach `Christina Aguilera/`.
- Nur ein Album, das die Quelle selbst **Various Artists** zuschreibt (ein Soundtrack, ein „Now That's What I Call…“), ist eine Compilation — außer du [markierst es selbst](#marking-an-album-as-various-artists). Ein einzelner YouTube-Music-Song ist es nie: YouTube Music führt dasselbe Audio unter mehreren Veröffentlichungen und kann jede davon als Album zeigen, oft eine Compilation, darum zählt nur der Download eines ganzen YouTube-Music-Albums. Seine Titel bekommen „Various Artists“ als Albumkünstler plus das Compilation-Flag (`TCMP` bei MP3, `COMPILATION` bei FLAC/Ogg/Opus, `cpil` bei M4A). So bleibt das Album in Navidrome und anderen Medienservern ganz, die Alben nach diesen Tags statt nach Ordnern gruppieren. Auf der Platte legt **Nach Künstler sortieren** aber nie einen Ordner `Various Artists` an: jeder Titel kommt in den Ordner seines ersten Künstlers.
- Ältere Downtify-Versionen haben jeden Song mit mehreren Künstlern als **Various Artists** getaggt, ohne Compilation-Flag. Die Bibliothek führt so einen Song weiter im Album seines ersten Künstlers, wie bisher; **Als Various Artists markieren** macht das Album zu einer echten Compilation.

```
downloads/
├── Christina Aguilera/
│   ├── Lady Marmalade/
│   │   └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
│   └── Moulin Rouge/                  ← aus dem Soundtrack (eine Compilation)
│       └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
└── David Bowie/
    └── Moulin Rouge/                  ← derselbe Soundtrack
        └── David Bowie - Nature Boy.mp3
```

*Lady Marmalade* von der Single und vom *Moulin Rouge*-Soundtrack sind zwei Veröffentlichungen, jede bei ihrem eigenen Album abgelegt. Die Titel des Soundtracks sind über die Ordner ihrer Künstler verteilt, aber als eine „Various Artists“-Compilation getaggt, sodass Bibliothek und Medienserver *Moulin Rouge* weiterhin als ein Album zeigen.

### Ein Album als Various Artists markieren

Eine Quelle kann eine Veröffentlichung einem Künstler zuschreiben, obwohl sie mehreren gleichermaßen gehört — Deezer führt die Single *Lady Marmalade* allein unter Christina Aguilera. Ein Admin kann das auf der Seite des Albums in der Bibliothek beheben, mit der Schaltfläche **Als Various Artists markieren** neben **Zur Warteschlange hinzufügen**.

- Jeder Titel des Albums bekommt „Various Artists“ als Albumkünstler und das Compilation-Flag. Sonst ändert sich nichts an den Dateien, und sie bleiben, wo sie sind (die Titel einer Compilation liegen ohnehin beim jeweils ersten Künstler). Jede Datei wird über eine Arbeitskopie neu geschrieben, behält ihr Änderungsdatum und bleibt unberührt, wenn das Schreiben scheitert.
- In der Bibliothek steht das Album dann bei **Various Artists** unter **Alben** (jeder Titel bleibt auf der Seite seines Künstlers), und die Albumseite folgt ihm dorthin.
- Downtify merkt sich das Album: Ein später heruntergeladener Titel davon wird genauso getaggt.
- Bei einer Compilation heißt dieselbe Schaltfläche **Markierung als Various Artists entfernen**: Sie macht die Markierung rückgängig und setzt den früheren Albumkünstler wieder ein. Sie funktioniert auch bei einem Album, das die Quelle zur Compilation gemacht hat; dann wird der Künstler zum Albumkünstler, den die meisten seiner Titel zuerst nennen, und spätere Downloads dieses Albums werden nicht wieder markiert.

Nur Admins sehen die Schaltfläche. Medienserver übernehmen die Änderung beim nächsten Bibliotheksscan.

## M3U und Künstlerordner

Ist *Nach Künstler sortieren* aktiv und du lädst eine Spotify-Playlist mit ebenfalls aktivierter M3U-Erzeugung herunter, wird die M3U in `<downloads>/Playlists/<Playlist-Name>.m3u` statt im Playlist-Unterordner abgelegt. Das liegt daran, dass die Titel nun auf mehrere Künstlerordner verteilt sind. Die relativen Pfade in der M3U werden weiterhin korrekt aufgelöst, egal wo du die Bibliothek einbindest.

## Die Einstellung ändern

Die Einstellung gilt sofort für alle **neuen** Downloads. Bereits vorhandene Dateien werden nicht verschoben.

## Das Löschen eines Titels räumt leere Ordner auf

Wird ein Titel auf der Bibliotheksseite gelöscht, entfernt das auch seinen Playlist-, Künstler- oder Albumordner, sobald er leer ist — und steigt weiter durch alle nun leeren übergeordneten Ordner hinauf (z. B. den Künstlerordner, nachdem sein letztes Album weg ist), bis zum Download-Verzeichnis selbst, das nie entfernt wird. Ein Ordner, der noch etwas anderes enthält — einen weiteren Titel, eine `.m3u`, eine noch genutzte `cover.jpg` —, bleibt unangetastet.

## Mehrere Titel auf einmal auswählen und löschen

Die Titelliste der Bibliothek hat bei jedem Titel ein Kontrollkästchen sowie ein Kästchen **Alle auswählen**, das alle Titel auswählt, die zum aktuellen Filter passen (siehe [Bibliotheksseite](library-catalog.md#library-page)). **Aus Bibliothek löschen** in der Auswahlleiste entfernt alle in einer einzigen Anfrage (`DELETE /delete/batch`, siehe [API-Referenz](../api-reference.md)), mit derselben Aufräumarbeit pro Titel (`.lrc`, verwaiste `cover.jpg`, leere Ordner) wie beim Löschen einzelner Titel.

Um ein ganzes Album oder eine Playlist zu löschen, öffne es und wähle **Löschen** im Menü **⋯**. Für alles von einem Künstler gib seinen Namen in den Filter der Titelliste ein, wähle dann **Alle auswählen** und lösche.
