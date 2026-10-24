---
icon: lucide/import
---

# Bibliotheksimport (CSV)

Du hast deine Bibliothek schon aus einem anderen Dienst exportiert? Importiere die CSV-Datei und stelle alle Titel auf einmal in die Download-Warteschlange, statt Songs einzeln hinzuzufügen.

## Unterstützte Exportprogramme

| Tool | Hinweise |
|------|-------|
| [Soundiiz](https://soundiiz.com/) | |
| [TuneMyMusic](https://www.tunemymusic.com/) | |
| [Exportify](https://github.com/watsonbox/exportify) | |

Downtify schreibt das exakte Spaltenschema keines Tools fest vor. Stattdessen vergleicht es die Kopfzeile der CSV ohne Beachtung der Groß- und Kleinschreibung mit einer Reihe bekannter Aliase (`Title` / `Track` / `Track Title` / `Track Name` / `Song` / …, `Artist` / `Artists` / `Artist Name` / `Artist Name(s)` / … und `Album` / `Album Name` / `Album Title` / …). Exporte aller drei Tools — oder einer selbst erstellten CSV mit denselben Spaltennamen — funktionieren daher, ohne dass du etwas umbenennen musst.

Titel und Künstler sind Pflicht. Das Album wird gelesen, wenn vorhanden, und als Albumname des Titels gespeichert (Warteschlange, Zuordnung und Datei-Tags). Weitere Spalten, die manche Exportprogramme enthalten (ISRC, eine Spotify-Titel-URI, Länge), werden ignoriert. Jede Zeile wird wie eine Freitextsuche über YouTube Music aufgelöst.

## So importierst du

1. Klicke auf der Startseite unter dem Suchfeld auf **CSV importieren (Soundiiz, Exportify …)**.
2. Wähle deine exportierte `.csv`-Datei.

Die Datei wird vollständig in deinem Browser gelesen und als reiner Text an den Server gesendet — sie wird nirgendwohin sonst hochgeladen. Downtify wertet sie aus, stellt alle erkannten Zeilen in die Warteschlange, und du landest in der Download-Warteschlange, in der der Fortschritt per WebSocket genau wie bei jedem anderen Stapel-Download eintrifft.

Der importierte Stapel wird nach der Datei benannt (Dateiname ohne `.csv`) und erhält, wie jeder andere Playlist-Download, eine [M3U-Datei](m3u-export.md), sofern diese Einstellung aktiviert ist.

## Grenzen und Fehlerbehandlung

- Bis zu **2.000 Zeilen** pro Datei. Teile größere Exporte auf mehrere Dateien auf.
- Zeilen ohne Titel oder Künstler werden stillschweigend übersprungen. Eine fehlende Albumspalte oder eine leere Albumzelle ist kein Problem — YouTube Music kann das Album später noch ergänzen.
- Mehrere Künstler in einer Zelle (getrennt durch `,` oder `;`) werden in eine Liste aufgeteilt.
- Enthält die Kopfzeile keine erkennbare Titel-/Künstlerspalte, wird der gesamte Import gleich zu Beginn mit einer Fehlermeldung abgelehnt, die die gefundenen Spalten nennt — nichts wird in die Warteschlange gestellt.

## Ratenlimits vermeiden

Der Import einer großen Bibliothek stellt in kurzer Zeit viele YouTube-Music-Suchen und Downloads in die Warteschlange — so läuft man leicht in ein Ratenlimit. Erwäge vor dem Import einer großen Datei, in den Einstellungen **[Parallele Downloads](download-settings.md#parallel-downloads)** zu senken und **[Pause zwischen Downloads](download-settings.md#delay-between-downloads)** zu aktivieren.

## API

Den zugrunde liegenden Endpunkt findest du unter [`POST /api/download/csv`](../api-reference.md#post-apidownloadcsv) in der API-Referenz.
