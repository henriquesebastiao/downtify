---
icon: lucide/shield-alert
---

# Explicit-Kennzeichnung

Ein Song mit expliziten Texten — Sprache, die nicht für Kinder gedacht ist — trägt wie bei Spotify ein kleines **E** neben dem Titel. Es erscheint überall, wo du dem Song begegnest, vor und nach dem Download, und bleibt an der Datei.

## Wo du es siehst

- **Suchergebnisse, eingefügte Links, Charts und der Finder** — bei jedem Song, den der Dienst als explizit meldet. Du siehst es vor dem Download.
- **Die Bibliothek** — im Tab Titel, auf den Seiten von Alben, Künstlern und Playlists und im Auswahldialog „Titel hinzufügen“.
- **Der Player** — neben dem Titel in der Player-Leiste, in **Wiedergabe** und in **Als Nächstes**.

Fahre mit der Maus über das **E** (oder lass es dir von einem Screenreader vorlesen), um „Explizite Inhalte“ zu sehen.

## Woher die Kennzeichnung stammt

Das entscheidet der Dienst, von dem du herunterlädst: Spotify, YouTube Music und Deezer markieren jeweils ihre expliziten Songs, und Downtify übernimmt, was der gewählte sagt. Lädt Downtify einen Song von YouTube Music, beschreibt die Kennzeichnung das **Video, das tatsächlich heruntergeladen wird**: Ist der Song auf Spotify explizit, Downtify hat aber eine entschärfte Version zugeordnet, wird die Datei nicht markiert; nennt Spotify ihn dagegen unbedenklich, die Zuordnung ist aber explizit, wird sie markiert.

Ein Song, den der Dienst nicht markiert, erhält gar keine Kennzeichnung — das ist nicht dasselbe wie als jugendfrei bestätigt, und Downtify schreibt nie eine „Clean“-Kennzeichnung.

## In der Datei

Die Kennzeichnung wird wie bei iTunes in die Tags der Datei geschrieben, damit Medienserver und Player, die sie verstehen, sie ebenfalls nutzen können. Navidrome liest genau diese Tags als Explicit-Status eines Titels.

| Format | Tag |
|--------|-----|
| MP3 | Text-Frame `ITUNESADVISORY` (`TXXX`), Wert `1` |
| FLAC, OGG, OPUS | Kommentar `ITUNESADVISORY`, Wert `1` |
| M4A | Atom `rtng`, Wert `1` |

Dateien, die du schon hattest, werden genauso gelesen: Alles, was iTunes, MusicBrainz Picard oder ein anderer Tagger mit `1` (oder dem älteren `4`) markiert hat, zeigt ebenfalls das **E**, auch Songs aus [zusätzlichen Ordnern](external-library.md).

::: info Vor dieser Version heruntergeladene Songs
Dateien, die Downtify schrieb, bevor es die Kennzeichnung gab, haben nichts in ihren Tags und zeigen deshalb kein **E**, selbst wenn der Song explizit ist. Lade den Song erneut mit [Audio ersetzen](replace-audio.md) oder ganz neu herunter, um ihn zu markieren. Eine Datei behält ihre Kennzeichnung, wenn [Bibliothek verbessern](library-upgrade.md) oder Audio ersetzen sie neu schreibt: Die Kennzeichnung wird nur hinzugefügt, nie entfernt.
:::

Beim ersten Laden der Bibliothek nach dem Update liest Downtify die Tags jeder Datei erneut, um nach der Kennzeichnung zu suchen — wie damals, als es lernte, Codec und Genre anzuzeigen. Bei einer großen Bibliothek auf einer langsamen Platte dauert das einmalig einen Moment.

## Für App-Entwickler

Der [Vertrag für mobile Clients](../mobile-client-contract.md) und die [API-Referenz](../api-reference.md#get-tracks) beschreiben das Feld `explicit`: `true` bei expliziten Titeln, sonst nicht vorhanden.
