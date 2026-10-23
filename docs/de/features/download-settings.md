---
icon: lucide/sliders-horizontal
---

# Download-Einstellungen

Öffne **Einstellungen** in der Seitenleiste (am Handy: **Mehr → Einstellungen**). Die Seite ist in Bereiche gegliedert — Allgemein, Audioquellen, Downloads und Dateien, Tags und Songtexte, Navidrome, Bibliothek und Über. Änderungen werden zurückgehalten, bis du in der unten erscheinenden Leiste auf **Änderungen speichern** drückst; wer die Seite mit ungespeicherten Änderungen verlässt, wird vorher gefragt. Einstellungen werden auf die Festplatte geschrieben und überstehen Container-Neustarts.

## Format

| Format | Endung | Hinweise |
|--------|-----------|-------|
| MP3 | `.mp3` | Standard. Universelle Kompatibilität. |
| FLAC | `.flac` | Verlustfrei. Die Bitrate-Einstellung wird ignoriert. |
| M4A | `.m4a` | AAC in einem MPEG-4-Container. Gut für Apple-Geräte. |
| OGG | `.ogg` | Ogg Vorbis. Offenes Format, gutes Verhältnis von Qualität zu Größe. |
| OPUS | `.opus` | Beste Kompression bei niedrigen Bitraten. |

## Bitrate

Verfügbar für verlustbehaftete Formate (MP3, M4A, OGG, OPUS). FLAC ignoriert diese Einstellung.

| Option | Kbps |
|--------|------|
| Niedrig | 128 |
| Mittel | 192 |
| Hoch | 256 |
| Beste | **320** (Standard) |

Das heruntergeladene Audio wird für jedes verlustbehaftete Format mit der gewählten Bitrate kodiert. Hat das von YouTube gelieferte Audio bereits den Ziel-Codec bei ungefähr dieser Bitrate (z. B. der AAC-Stream mit ~128 kbps für **M4A @ 128**), wird es unverändert übernommen statt neu kodiert, denn eine Neukodierung würde nur Qualität kosten.

::: info Eine höhere Bitrate bringt keine zusätzliche Qualität
Das Audio von YouTube reicht höchstens bis etwa **128–160 kbps** (AAC oder Opus), und Downtify lädt immer den besten verfügbaren Stream. Mit 256 oder 320 kbps kodiert, entstehen größere Dateien, die diese Quelle originalgetreu bewahren, aber keine Details zurückbringen können, die die Quelle nie hatte. Wähle eine niedrigere Bitrate, wenn dir die Dateigröße wichtiger ist.
:::

## Vorlage für den Dateinamen

Die Standardvorlage für den Dateinamen lautet:

```
{artists} - {title}
```

Sie erzeugt Dateinamen wie `The Night Owls - Do I Still Recall.mp3`.

Verfügbare Tokens:

| Token | Beschreibung |
|-------|-------------|
| `{title}` | Titel des Songs |
| `{artists}` | Künstlernamen, durch Kommas getrennt |
| `{album}` | Albumname |
| `{tracknumber}` | Position des Titels auf seinem Album, auf 2 Stellen mit Nullen aufgefüllt (z. B. `01`, `12`). Leer, wenn die Quelle keine Titelnummer hat (z. B. bei einem Freitext-/YouTube-Suchergebnis). |
| `{year}` | Erscheinungsjahr (z. B. `2025`). Leer, wenn die Quelle kein Veröffentlichungsdatum hat (z. B. bei einem Freitext-/YouTube-Suchergebnis). |

Die Vorlage kann auch `/` enthalten, um Unterordner anzulegen. Zum Beispiel, um eine Bibliothek als `Künstler/Album (2025)/01 - Titel.mp3` aufzubauen — praktisch beim Herunterladen einer ganzen Diskografie, da jedes Album samt Erscheinungsjahr in einem eigenen Ordner landet:

```
{artists}/{album} ({year})/{tracknumber} - {title}
```

::: info
Das ist unabhängig von den Schaltern **Nach Künstler sortieren** / **Nach Album sortieren** weiter unten — diese leiten Playlist-/Album-Downloads in gemeinsame Ordner pro Künstler oder pro Album in deiner ganzen Bibliothek. `{tracknumber}` und `{year}` erlauben es einer Vorlage wie der obigen lediglich, dasselbe Layout von Hand, Titel für Titel, aufzubauen, ohne diese Schalter einzuschalten.
:::

## Parallele Downloads

Steuert, wie viele Songs gleichzeitig heruntergeladen werden. Wähle eine Voreinstellung (1, 2, 3, 5, 8) oder gib im Zahlenfeld daneben einen beliebigen Wert von **1 bis 30** ein.

| Wert | Verhalten |
|-------|-----------|
| **1** | Sequenziell — ein Song nach dem anderen (am sichersten, geringster Ressourcenverbrauch) |
| **3** | Standard. Guter Kompromiss aus Geschwindigkeit und Stabilität. |
| **8** | Schneller bei großen Playlists |
| **bis 30** | Am besten für sehr schnelle Verbindungen; braucht mehr CPU und Bandbreite und erhöht die Chance, von YouTube gedrosselt zu werden. |

Das Limit gilt für jeden Batch-Download — Playlist-/Album-Downloads, den Batch-Queue-Endpunkt und CSV-[Bibliotheksimporte](library-import.md) — sowie für die Abfragen der Synchronisierung der **[Vorhandenen Musikordner](external-library.md)** (Songtexte, Cover, Genre). Es gilt **nicht** für die Durchläufe der Playlist-Überwachung, die neue Titel einzeln herunterladen. Eine Änderung dieses Werts in den Einstellungen wirkt sofort ohne Neustart; der Server begrenzt jeden Wert außerhalb von `1–30`.

## Pause zwischen Downloads

Lässt Downtify nach dem Abschluss eines Songs eine konfigurierbare Anzahl Sekunden warten, bevor der nächste beginnt, statt die Anfragen direkt hintereinander abzufeuern.

| Wert | Verhalten |
|-------|-----------|
| **0** | Standard — aus, keine Verzögerung. |
| **5 / 15 / 30 / 60** | Voreinstellungen, oder gib einen beliebigen Wert von **0 bis 300 Sekunden** ein. |

Gilt für Playlist-, Album- und Batch-Downloads, CSV-[Bibliotheksimporte](library-import.md) und die automatischen Durchläufe der Playlist-Überwachung. Entfällt bei einem einzelnen manuellen Titel-Download (es gibt keinen „nächsten“ Song, auf den zu warten wäre) und nach dem *letzten* Titel jedes Batches, damit ein Durchlauf nicht mit einer sinnlosen Wartezeit ausklingt.

In Kombination mit einem niedrigeren Wert bei **Parallele Downloads** ist das das wichtigste Mittel, YouTubes Ratenbegrenzung beim unbeaufsichtigten Herunterladen einer großen Playlist oder importierten Bibliothek zu vermeiden.

## Pause zwischen Synchronisierungsabfragen

Dieselbe Idee, aber für die **[Vorhandenen Musikordner](external-library.md)** statt für Downloads. Die Synchronisierung sucht Songtexte, fehlende Cover und das Genre in Batches von **[Parallele Downloads](#parallel-downloads)** Titeln auf einmal und wartet danach so viele Sekunden bis zum nächsten Batch. Standard **0** (die Abfragen laufen weiter gleichzeitig, weiterhin durch Parallele Downloads begrenzt). Nutze bei einer großen Sammlung ein paar Sekunden, damit LRCLIB, die Coverquellen und iTunes nicht alle auf einmal belastet werden.

## Cover herunterladen

Steuert, ob Downtify überhaupt Albumcover einbettet. Standardmäßig an. Schalte es aus, um das Abrufen von Covern ganz zu überspringen — alle anderen Tags (Titel, Künstler, Album, Jahr, Songtext) werden weiterhin normal eingebettet, aber die Dateien werden kleiner und laden etwas schneller, da das Coverbild nie angefordert oder geschrieben wird.

Ausschalten überspringt auch das Schreiben der eigenständigen `cover.jpg`, die die Option *Nach Album sortieren* (siehe [Dateiorganisation](file-organization.md)) erzeugt, und der [Player](player.md) bzw. die Bibliothek zeigen für so heruntergeladene Titel kein Cover (stattdessen das Ersatz-Notensymbol).

Diese `cover.jpg` teilen sich alle Titel im Albumordner. Löscht du einen Titel auf der Bibliotheksseite, wird sie ebenfalls entfernt, aber erst, wenn er der **letzte** Titel in diesem Ordner ist — solange noch ein anderer Titel desselben Albums dort liegt, bleibt das Cover.

## Cover-Auflösung

Nur relevant, wenn **Cover herunterladen** (oben) an ist. Legt die Zielgröße (Breite und Höhe in Pixeln) fest, die Downtify für eingebettete Cover von **YouTube Music** oder **Deezer** anfordert. Wähle eine Voreinstellung (300, 600, 800, 1000, 1200) oder ziehe den Schieberegler irgendwo zwischen **300 und 1200**; der aktuelle Wert in Pixeln steht daneben. Standard ist 600.

Das ist nützlich, wenn du deine Bibliothek in einen Medienserver wie Plex einspeist, der Cover in höherer Auflösung anzeigt, als Downtify standardmäßig einbettet.

Die beiden Quellen setzen die Einstellung unterschiedlich um, da nur eine von ihnen tatsächlich auf Abruf skaliert werden kann:

- Thumbnails von **YouTube Music** lassen sich durch Ändern ihrer URL skalieren — am echten CDN geprüft, liefern die höheren Voreinstellungen bei den meisten Covern tatsächlich mehr Details (nicht nur Hochskalierung), bis zur Auflösung des Quellbilds selbst.
- **Deezer** bietet für das Cover jedes Titels, Albums, Künstlers oder jeder Playlist nur vier feste Größen (56, 250, 500 und 1000 px) — eine Zwischengröße gibt es nicht. Downtify wählt die kleinste dieser vier, die mindestens so groß ist wie der eingestellte Wert (bei 300 px gibt es die 500-px-Version, da es keine exakte 300-px-Größe gibt); wer mehr als 1000 px verlangt, bekommt ebenfalls die 1000-px-Version, die größte von Deezer.

::: info Cover aus Spotify sind nicht betroffen
Downtify bettet bereits das **größte** Cover ein, das Spotifys öffentliche Embed-API für von Spotify aufgelöste Titel/Alben/Playlists anbietet — eine größere Größe gibt es nicht. Diese Einstellung hebt nur die Obergrenze für Titel an, die über YouTube Music aufgelöst werden (Freitextsuche, YouTube-URLs und jeder Spotify-Titel, der für das eigentliche Audio erneut YouTube Music zugeordnet wird) oder über Deezer (ein eingefügter Deezer-Link oder ein Titel aus den [Charts](charts.md)).
:::

Eine Änderung dieses Werts in den Einstellungen wirkt sofort, auch für die gerade geöffnete Suchseite — sie erfordert kein erneutes Herunterladen von etwas, das schon auf der Festplatte liegt.

## Vorhandene Dateien überschreiben

Standardmäßig an, entsprechend Downtifys bisherigem Verhalten: Jeder Download durchläuft die Pipeline (Audio abrufen, Tags, Cover, Songtext) und überschreibt, was bereits unter dem berechneten Ausgabepfad liegt.

### Was „erneut“ wirklich bedeutet

Ist es an, ist ein erneuter Download ein **komplett frischer Lauf**, keine Reparatur der vorhandenen Datei. Downtify sieht nicht nach, was du schon hast: Es durchsucht deine [Audioquellen](#audio-provider) in der konfigurierten Reihenfolge — ist also slskd zuerst, wird slskd zuerst versucht, nicht nur als Rückfall —, holt das Audio von der Quelle, die antwortet, und schreibt die heutigen Tags, Cover und Songtexte darauf.

Das hat eine Folge, die man vor dem erneuten Herunterladen einer großen Bibliothek kennen sollte:

::: warning Ein anderes Format lässt die alte Datei zurück
Die neue Datei wird an dem Pfad geschrieben, den die [Vorlage für den Dateinamen](#output-filename-template) erzeugt, mit der Endung des **neuen** Audios. Downtify überschreibt die alte Datei nur, wenn beide dieselbe Endung haben.

Lädst du also `Künstler - Song.mp3` erneut herunter und slskd antwortet mit einer FLAC, bekommst du **beide**: `Künstler - Song.mp3` (die alte, unberührt) und `Künstler - Song.flac`. Ist [slskd-Dateien an Ort und Stelle lassen](slskd-navidrome.md#leave-files-in-place) an — der Standard —, wird die slskd-Datei nicht einmal in deinen Download-Ordner kopiert, die alte bleibt also genau dort, wo sie war, und die neue liegt unter `slskd/`.

Nichts geht verloren, aber du bekommst Dubletten. Um eine Datei wirklich zu ersetzen, siehe [Audio ersetzen](replace-audio.md), das Pfad, Format und Tags beibehält.
:::

### Das Cover kommt von Spotify oder YouTube Music, nicht aus der Datei

Jedes Artwork, das das heruntergeladene Audio mitbringt — auch ein hochauflösendes Cover, das in einer slskd-Datei eingebettet ist —, wird beim Taggen **verworfen und ersetzt**. Downtify bettet immer das Cover ein, das es für den Titel von Spotify oder YouTube Music abruft, in der von dir konfigurierten [Cover-Auflösung](#cover-art-resolution) (standardmäßig 600 px). Dasselbe gilt für Titel, Künstler, Album und die übrigen Tags: Die eigenen Tags der Quelle werden nicht beibehalten.

Wenn du größere Cover auf bereits vorhandenen Dateien willst, ist erneutes Herunterladen der lange Weg. [Bibliothek verbessern](library-upgrade.md) macht genau das — es vergleicht das eingebettete Cover jeder Datei mit Spotify, iTunes und YouTube Music, schreibt das größte, ergänzt fehlende Songtexte und Tags und fasst das Audio nie an.

Schalte es aus, um nie einen Song herunterzuladen, der schon auf der Festplatte liegt. Das ist vor allem wichtig beim Herunterladen einer Playlist, beim Importieren einer [CSV-Bibliothek](library-import.md) oder wenn die [Playlist-Überwachung](playlist-monitor.md) Playlists synchronisiert, die Titel untereinander oder mit Songs gemeinsam haben, die schon in deiner Bibliothek liegen — bei eingeschalteter Option wird jede dieser Dubletten erneut heruntergeladen.

Ist sie aus, sucht Downtify den Song **irgendwo im Download-Ordner**, nicht nur dort, wo der neue Download landen würde:

- im Bibliotheksstamm (Einzeltitel-Downloads),
- im Ordner einer beliebigen Playlist (Playlist-Downloads, CSV-Importe, Playlist-Überwachung),
- in einem Künstler-/Albumordner oder im flachen Layout von vor dem Ein- oder Ausschalten von *Nach Künstler/Album sortieren*.

Ein Song gilt als bereits heruntergeladen, wenn eine Audiodatei (`.mp3`, `.flac`, `.m4a`, `.ogg`, `.opus`) den Namen trägt, den die [Vorlage für den Dateinamen](#output-filename-template) dafür erzeugt, verglichen ohne Beachtung der Groß-/Kleinschreibung. Eine übrig gebliebene `.lrc`-Songtextdatei allein zählt nicht. Enthält die Vorlage Ordner (z. B. `{artists}/{title}`), müssen auch diese Ordner übereinstimmen, damit der Song eines anderen Künstlers mit gleichem Titel nicht für diesen gehalten wird. Da Dateien keine Spotify-/YouTube-Titel-ID tragen, erfolgt der Abgleich über den Namen: Eine umbenannte Datei oder eine mit einer anderen Dateinamenvorlage gespeicherte wird nicht erkannt.

Wenn ein Song übersprungen wird:

- Es wird nichts abgerufen: kein Audio, kein Cover, kein Songtext, kein erneutes Taggen. Bei Spotify-Titeln läuft die Prüfung sogar vor der YouTube-Music-Suche, bereits heruntergeladene Songs kosten also keine Suchanfragen.
- Die Warteschlange zeigt den Song als fertig an, und die [M3U-Dateien](m3u-export.md) der Playlists zeigen auf die vorhandene Datei, wo auch immer sie liegt (z. B. `../Künstler - Titel.mp3`), sodass die Playlist weiterhin vollständig abspielt.
- Wird derselbe Song gleichzeitig zweimal eingereiht (zweimal in einer Playlist oder in zwei parallel heruntergeladenen Playlists), wird nur eine Kopie heruntergeladen. Die andere wartet darauf und wird dann übersprungen.

## Lange Titel

**Einstellungen → Downloads und Dateien → Maximale Titellänge** begrenzt die Titellänge für Downloads *und* Streams gleichermaßen (Standard **10 Minuten**, `0` nimmt alles). Längere Songs werden abgelehnt, bevor etwas abgerufen wird, mit dem Warteschlangenfehler *„Titel über … werden nicht heruntergeladen“* — stundenlange Mixe und Uploads sind nie das, was ein Bibliothekstitel sein sollte. Dieselbe Grenze schützt das Streaming: Ein längerer Titel wird mit einem `400` abgelehnt (Aufrufer, die seine Länge kennen, übergeben `duration`, und die gecachte Datei wird in jedem Fall geprüft), sodass sich lange Uploads auch nicht im Stream-Cache ansammeln. Bereits heruntergeladene Dateien und Podcast-Episoden (die oft länger sind) sind nicht betroffen.

## Audioanbieter

Der Standard-Audioanbieter ist **YouTube Music**. Downtify nutzt [`ytmusicapi`](https://ytmusicapi.readthedocs.io/), um die beste Übereinstimmung durch Vergleich der Titellänge zu finden. Hat YouTube Music keinen akzeptablen Treffer oder nur einen mit stark abweichender Länge (wahrscheinlich eine andere Aufnahme), fällt Downtify automatisch auf die Suche im normalen YouTube zurück — siehe [So funktioniert es](../how-it-works.md#fallback-to-standard-youtube).

**Einstellungen → Audioquellen** kann auch nur das normale **YouTube** oder **slskd** (Soulseek) als geordnete Rückfallliste nutzen — siehe [slskd und Navidrome](slskd-navidrome.md#audio-sources-and-fallback-order).

### Eine bestimmte Audioquelle erzwingen

Wählt Downtify das falsche YouTube-Music-Video (z. B. ein Cover statt des Originals), kannst du es pro Titel überschreiben:

**Option A — eine YouTube-Music-URL direkt einfügen**

Füge `https://music.youtube.com/watch?v=…` (oder eine normale `youtube.com/watch?v=…`-URL) in die Suchleiste ein und starte den Download. Downtify holt das Audio genau von diesem Video.

::: info
Beim Download über eine YouTube-URL stammen die Metadaten (Titel, Künstler, Cover) von YouTube statt von Spotify. Für saubere Tags nutze Option B.
:::

**Option B — Audio für einen fehlgeschlagenen Titel erzwingen**

1. Klicke in der **Download-Warteschlange** unter einem fehlgeschlagenen Titel auf **Audioquelle erzwingen**.
2. Füge eine YouTube- oder YouTube-Music-URL in das erscheinende Feld ein.
3. Drücke **Enter** oder klicke auf **Anwenden**.

Downtify lädt den Titel mit genau diesem Video erneut herunter und behält dabei alle Spotify-Metadaten (Titel, Künstler, Album, Cover, Songtext).

## Eingebettete Metadaten

Downtify bettet die folgenden Tags in jede heruntergeladene Datei ein, unabhängig vom Format:

| Tag | Quelle |
|-----|--------|
| Titel | Spotify-Embed |
| Künstler | Spotify-Embed |
| Album | Spotify-Embed — bei einem Einzeltitel-Download das Album, das die öffentliche Spotify-Seite des Titels nennt (das Embed des Titels selbst hat keines) |
| Jahr | Spotify-Embed (Abruf auf Titelebene) |
| Cover | Spotify-Embed (Cover auf Titelebene) bei von Spotify aufgelösten Titeln; sonst YouTube-Music-Thumbnail oder Deezer-Cover. Optional — siehe [Cover herunterladen](#download-cover-art) und [Cover-Auflösung](#cover-art-resolution) |
| Songtext | lrclib (falls aktiviert) |
