---
icon: lucide/mic-vocal
---

# Songtexte

Downtify sucht Songtexte, während ein Titel heruntergeladen wird, und bettet sie in die Datei ein — dazu eine `.lrc`-Begleitdatei, wenn sie zeitsynchron sind.

## Songtexte aktivieren

Songtexte sind **standardmäßig aktiviert**. Ausschalten unter **Einstellungen → Tags und Songtexte → Songtexte herunterladen**.

## Anbieter und Reihenfolge

Kataloge unterscheiden sich: Ein Song, den ein Anbieter nicht kennt, ist oft bei einem anderen zu finden. Downtify führt daher eine geordnete Liste von Anbietern und probiert sie nacheinander durch, beim ersten mit einem Treffer hört es auf.

| Anbieter | Songtexte | Hinweise |
|----------|--------|-------|
| **[LRCLIB](https://lrclib.net)** | Einfach und zeitsynchron | Kostenlose Community-Datenbank, kein Schlüssel. Abgleich über Titel, Hauptkünstler, Album und Länge. Findet das nichts Zeitsynchrones, wird auch die Suche versucht; ein Treffer zählt, wenn Titel, Künstler und Länge (auf wenige Sekunden) passen. |
| **NetEase Cloud Music** | Meist zeitsynchron | Großer Katalog, stark bei asiatischen und oft auch bei westlichen Veröffentlichungen. Abgleich über Titel, Künstler und Länge; ein Treffer, dessen Künstler anders geschrieben ist (etwa traditionelles vs. vereinfachtes Chinesisch), wird nur akzeptiert, wenn Titel und Länge beide passen. |
| **Kugou Music** | Zeitsynchron | Großer Katalog, stark bei chinesischen und mit vielen westlichen Veröffentlichungen. Abgleich wie bei NetEase; die Titelzeile und die Songwriter-Angaben am Anfang werden entfernt. |

Unter **Einstellungen → Tags und Songtexte → Anbieter** kannst du die Anbieter in die gewünschte Reihenfolge ziehen oder die Pfeile benutzen und jeden ausschalten. Mindestens einer bleibt an; um die Suche nach Songtexten ganz zu beenden, nutze den Schalter **Songtexte herunterladen**. Ein Anbieter, der mit einem Update dazukommt, ist ausgeschaltet, wenn du schon eine eigene Liste gespeichert hast: schalte ihn dort ein.

### Nur zeitsynchrone Songtexte

**Einstellungen → Tags und Songtexte → Nur zeitsynchrone Songtexte** (standardmäßig aus) behält nur Songtexte mit Zeitstempeln: Hat ein Anbieter für einen Song nur einfachen Text, zählt das als nichts, und der nächste wird gefragt. [Bibliothek verbessern](library-upgrade.md) zählt dann auch einen Titel mit nur einfachem Text als ohne Songtext. Synchrone Songtexte, die eine Datei schon hat, zählen immer: eine `.lrc`-Begleitdatei, Songtexte mit Zeitstempeln in den Tags oder ein ID3-`SYLT`-Frame (wie ihn Dateien aus anderen Apps manchmal haben). Ist die Einstellung an, ersetzen gefundene synchrone Songtexte den einfachen Text: in der `.lrc`-Begleitdatei und im Songtext-Tag der Datei selbst, sodass auch Player, die nur die Tags lesen, sie synchron zeigen. Der Scan nennt außerdem, wie viele der Titel ohne Songtext nur einfachen Text hatten.

### Songtexte für Titel ohne finden

**Bibliothek → Bibliothek verbessern → Scannen und Songtexte suchen** durchsucht die Bibliothek nach Titeln ohne Songtext und sucht sie sofort, mit Fortschrittsbalken. Am Ende steht, wie viele Titel Songtexte bekommen haben, für wie viele keiner gefunden wurde und wie viele fehlgeschlagen sind. Siehe [Bibliothek verbessern](library-upgrade.md#while-it-runs).

::: info Und Genius, Musixmatch und AZLyrics?
Sie sind nicht verfügbar, und Downtify bietet sie nicht mehr an:

- **AZLyrics** verbietet die Nutzung seiner Songtexte durch Dritte auf der Seite selbst.
- Die Desktop-API von **Musixmatch** antwortet mit einem leeren Token, sofern du keine Zugangsdaten hast, die sie Anwendungen nicht gibt.
- Die `robots.txt` von **Genius** verbietet den Such-Endpunkt, der nötig ist, um die Seite eines Songs zu finden.

Gespeicherte Einstellungen, die sie noch nennen, funktionieren weiter: Die Namen werden ignoriert, und eine Liste, in der nichts anderes übrig bleibt, fällt auf die Standardanbieter zurück.
:::

## Anbieter überspringen, die nichts hatten

Nach einer Suche vermerkt Downtify für jeden Song, welche Anbieter geantwortet haben und welche leer ausgingen, in `downtify_library.db` unter `/data`.

Ein Anbieter, der für einen Song nichts hatte, wird **30 Tage** lang nicht erneut danach gefragt, damit erneute Downloads und große Bibliotheksdurchläufe nicht dieselben fehlgeschlagenen Suchen wiederholen. Danach wird er wieder probiert, denn Kataloge wachsen. Ein Anbieter, der Songtexte *hatte*, wird nie übersprungen, sodass eine erneut heruntergeladene Datei sie zurückbekommt.

## Einbetten

| Format | Tag für einfachen Songtext | Tag für synchronen Songtext |
|--------|-----------------|------------------|
| MP3 | `USLT` (ID3) | `USLT` mit Zeitstempeln |
| FLAC | `LYRICS` (Vorbis-Kommentar) | `LYRICS` mit LRC-Inhalt |
| M4A | `©lyr` | `©lyr` mit LRC-Inhalt |
| OGG / OPUS | `LYRICS` (Vorbis-Kommentar) | `LYRICS` mit LRC-Inhalt |

## Begleitdatei .lrc

Sind synchrone Songtexte verfügbar, speichert Downtify zusätzlich eine `.lrc`-Datei. Standardmäßig liegt sie **neben dem Audio** mit demselben Basisnamen. Unter **Einstellungen → Tags und Songtexte** kannst du das ausschalten und stattdessen einen **Songtext-Ordner** wählen (Standard `/data/lyrics`). Dieser Ordner muss **außerhalb** von `/downloads`, des slskd-Baums und aller zusätzlichen Musikordner liegen — der relative Pfad des Audios wird darunter nachgebildet (`Künstler/Album/titel.lrc`). Player, die externe Songtexte lesen (und der [integrierte Player](player.md#now-playing)), finden die Begleitdatei weiterhin. Wenn du diese Einstellung änderst und für einen zusätzlichen Ordner **Synchronisieren** ausführst, werden vorhandene `.lrc`-Dateien an den neuen Ort kopiert; die Quelldatei wird entfernt, wenn dieser Baum beschreibbar ist, und bei einem schreibgeschützten Mount belassen. Eine Begleitdatei wird auch dann geschrieben, wenn die Songtexte schon in den Tags eingebettet sind.

Das Löschen des Titels auf der Bibliotheksseite entfernt die `.lrc` (neben der Datei und im eigenen Ordner) zusammen mit dem Audio, sodass Songtexte nie als verwaiste Datei liegen bleiben.

## Das Timing anpassen

Online gefundene Liedtexte laufen manchmal etwas vor oder nach dem heruntergeladenen Audio: eine andere Fassung des Songs, ein längeres Intro. Um einen Song zu korrigieren, spiele ihn ab, öffne **Wiedergabe → Songtexte** und tippe oben rechts im Liedtext auf den Stoppuhr-Button, **Liedtext-Timing anpassen**:

- **−** zeigt den Liedtext früher und **+** später, eine Zehntelsekunde pro Tipp, bis zu einer Minute in jede Richtung. Der Liedtext folgt dem neuen Timing sofort, du kannst es also während der Wiedergabe ausprobieren.
- **Speichern** schreibt es in die Dateien des Songs; **Zurücksetzen** kehrt zum gespeicherten Timing zurück.

Beim Speichern werden die Zeitstempel selbst neu geschrieben, in der `.lrc`-Datei und, wenn die Tags der Datei synchronisierte Liedtexte enthalten, auch dort (einschließlich `SYLT`-Frames von MP3s). Die Korrektur zeigt sich so auch in anderen Playern, die die `.lrc` oder die Tags lesen, und in den Apps. Eine schreibgeschützte Datei behält ihre Tags; nur die `.lrc` ändert sich. Eine `[offset:N]`-Zeile in einer `.lrc` wird beim Speichern in die Zeiten eingerechnet, und der Player von Downtify berücksichtigt sie schon vorher.

Der Button erscheint nur bei Songs der Bibliothek mit synchronisiertem Liedtext. Jeder angemeldete Benutzer kann ihn anpassen; die Änderung erscheint im [Aktivitätsprotokoll](users.md#activity) als **Liedtext-Timing angepasst**. Der Endpoint ist [`POST /api/library/lyrics/offset`](../api-reference.md#post-apilibrarylyricsoffset).

## Wenn nichts gefunden wird

Hat kein Anbieter den Song, läuft der Download normal weiter — die Audiodatei wird ohne Songtexte gespeichert, und es tritt kein Fehler auf.
