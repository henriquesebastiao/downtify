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
| **[LRCLIB](https://lrclib.net)** | Einfach und zeitsynchron | Kostenlose Community-Datenbank, kein Schlüssel. Abgleich über Titel, Hauptkünstler, Album und Länge. |
| **NetEase Cloud Music** | Meist zeitsynchron | Großer Katalog, stark bei asiatischen und oft auch bei westlichen Veröffentlichungen. Abgleich über Titel, Künstler und Länge; ein Treffer, dessen Künstler anders geschrieben ist (etwa traditionelles vs. vereinfachtes Chinesisch), wird nur akzeptiert, wenn Titel und Länge beide passen. |

Unter **Einstellungen → Tags und Songtexte → Anbieter** kannst du die Anbieter in die gewünschte Reihenfolge ziehen oder die Pfeile benutzen und jeden ausschalten. Mindestens einer bleibt an; um die Suche nach Songtexten ganz zu beenden, nutze den Schalter **Songtexte herunterladen**.

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

## Wenn nichts gefunden wird

Hat kein Anbieter den Song, läuft der Download normal weiter — die Audiodatei wird ohne Songtexte gespeichert, und es tritt kein Fehler auf.
