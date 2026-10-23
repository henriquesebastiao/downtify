---
icon: lucide/wand-sparkles
---

# Bibliothek verbessern

Eine über die Zeit gewachsene Bibliothek trägt das, was die jeweilige Downtify-Version beim Herunterladen eines Titels konnte: das kleinste Cover, das eine Quelle bot, keine Songtexte, Tags ohne Album oder Jahr. **Bibliothek verbessern** sieht sich an, was schon auf der Festplatte liegt, und repariert nur, was zurückliegt — ohne erneutes Herunterladen und ohne etwas von Hand zu ordnen.

Öffne es über **Bibliothek → Bibliothek verbessern**.

::: info Die Standardverbesserungen schreiben nur Tags neu
Der Standardmodus schreibt **Cover, Songtexte und Tags** neu. Der optionale [Deemix-Ersatz](#deemix-recording-replacement) ist ein separater Scan-Modus, standardmäßig aus. Nutze [Audio ersetzen](replace-audio.md), um manuell eine andere Version zu wählen.
:::

## So funktioniert es

1. **Scan.** Downtify liest jeden Bibliothekstitel und meldet, was zurückliegt, pro Kategorie. Nichts wird geschrieben.
2. **Auswahl.** Jede Kategorie, für die der Scan etwas fand, wird mit ihrer Titelzahl und einem Schalter aufgelistet. Hake ab, was du nicht willst.
3. **Verbessern.** Die gewählten Titel kommen in eine Warteschlange, die einzeln abgearbeitet wird. Du kannst sie pausieren, fortsetzen oder stoppen, und sie übersteht einen Neustart.

## Was es repariert

| Kategorie | Was es tut | Wo es sucht |
|---|---|---|
| **Cover verbessern** | Ersetzt ein Cover, das kleiner als deine Zielgröße ist | Spotify, Apple Music (iTunes), YouTube Music |
| **Fehlende Songtexte ergänzen** | Ergänzt Songtexte für Titel ohne, eingebettet und als `.lrc`-Sidecar | Deine [Songtext-Anbieter](lyrics.md), in deiner Reihenfolge |
| **Tags aktualisieren** | Ergänzt Album, Album-Künstler, Veröffentlichungsdatum und Titelnummer — auch das Album, das älteren Einzeltitel-Downloads fehlt | Spotify |

Ein Titel gilt als zurückliegend, wenn:

- die kurze Seite seines eingebetteten Covers **kleiner als die Zielgröße** ist (ein Titel ganz ohne Cover zählt auch);
- er **weder** eingebettete Songtexte **noch** ein `.lrc`-Sidecar hat (neben der Datei oder im Songtext-Ordner aus den Einstellungen);
- in seinen Tags **Album**, **Album-Künstler**, **Jahr** oder **Titelnummer** fehlt.

**Tags aktualisieren** funktioniert nur für Titel, für die Downtify noch eine Spotify-Titel-ID hat — die, die es von einem Spotify-Link heruntergeladen hat und die im [Titelindex](library-catalog.md#what-gets-stored) stehen. Andere Titel werden eingereiht, kommen aber als _Keine Änderung nötig_ zurück.

## Optionen

### Cover verbessern, wenn kleiner als

`300px` · `500px` · **`600px`** · `1000px` · `1200px`

Cover dieser Größe oder größer bleiben unberührt. Downtify schreibt nur ein Cover, das **strikt größer** ist als das schon in der Datei, sodass ein zweimaliger Verbesserungslauf nie umsonst etwas neu schreibt.

Woher die Größen kommen:

| Quelle | Typische Größe |
|---|---|
| **Apple Music (iTunes)** | 1200px und mehr |
| **Spotify** | bis zu 640px |
| **YouTube Music** | bis zur Einstellung der [Cover-Auflösung](download-settings.md), höchstens ~1200px |

Deshalb bleibt eine früher heruntergeladene Bibliothek oft bei 300–640px hängen: Spotify veröffentlicht seine Cover in festen Größen, und die größte, die es bietet, ist 640px.

### Coverquelle

| Wahl | Verhalten |
|---|---|
| **Höchste verfügbare Auflösung** (Standard) | Fragt alle Quellen und behält das größte Bild |
| **Spotify bevorzugen** / **Apple Music bevorzugen** / **YouTube Music bevorzugen** | Nutzt diese Quelle, wenn sie überhaupt etwas hat; die anderen sind nur ein Rückfall, wenn sie nichts hat |

### Titel nicht erneut prüfen für

`Jeden Titel immer prüfen` · `7 Tage` · **`30 Tage`** · `90 Tage` · `365 Tage`

Nachdem ein Titel angesehen wurde, überspringt ihn der nächste Scan so lange, damit ein zweiter Lauf über eine große Bibliothek nicht dieselben Quellen nach denselben Titeln erneut fragt.

Das Gedächtnis wird **pro Titel und pro Kategorie** geführt, wodurch Teilläufe funktionieren: Nur die Cover von 16.000 Titeln zu reparieren, sagt nichts darüber, ob je jemand nach ihren Songtexten gesucht hat, daher berücksichtigt ein späterer Songtext-Lauf weiterhin jeden davon. Ein Scan hält auch die Kategorien fest, die er untersucht hat und für die er nichts zu tun fand — Nachsehen und nichts finden ist eine Prüfung wie jede andere.

Downtify merkt sich pro Titel und Kategorie: wann er geprüft wurde, welche Downtify-Version ihn geprüft hat und — bei Covern — das größte gefundene Cover und woher es kam. Welche Songtext-Anbieter schon gefragt wurden, wird getrennt gespeichert, pro Song und Anbieter (siehe [Songtexte](lyrics.md)).

Zwei Dinge heben es immer auf:

- eine **neuere Downtify-Version** prüft alles neu, da sie besser zuordnen oder taggen kann als die vorherige;
- die Wahl **Jeden Titel immer prüfen** ignoriert das Gedächtnis für diesen Scan.

Findet ein Scan nichts mehr zu tun, _weil_ alles kürzlich geprüft wurde, sagt er das und bietet an, ohne das Gedächtnis erneut zu laufen, statt dich mit einem unerklärten „nichts zu verbessern“ zurückzulassen.

## Während es läuft

Das Fortschrittspanel zeigt erledigte Titel aus der Warteschlange, eine ungefähre Datenmenge (`8.4 GB of 51.3 GB`) und wie viele verbessert wurden, nichts zu tun hatten oder fehlschlugen. Jeder Titel zeigt, was er gerade tut — _Zuordnung_, _Cover werden gesucht_, _Songtexte werden gesucht_, _Datei wird geschrieben_ — und endet mit dem, was sich änderte, z. B. `artwork 1200px (itunes)`.

**Pausieren** stoppt nach dem laufenden Titel und behält die Warteschlange. **Anhalten** verwirft den Rest; bereits verbesserte Titel bleiben verbessert. Du kannst die Seite verlassen — der Lauf geht weiter, und jeder andere offene Tab folgt mit.

Die Warteschlange liegt in `/data/downtify_library.db`, sodass ein **Neustart von Downtify (oder des Containers) mitten im Lauf ihn dort fortsetzt**, wo er aufhörte. Ein Titel, der in Bearbeitung war, als der Prozess starb, kommt zurück in die Warteschlange.

## Nichts geht verloren, wenn eine Verbesserung fehlschlägt

Jeder Schreibvorgang geht in eine Arbeitskopie neben dem Original (`<Name>.downtify-upgrade.<Endung>`). Die Kopie muss sich als Audio derselben Länge öffnen lassen, bevor sie an ihren Platz verschoben wird; andernfalls wird sie verworfen und das Original bleibt unberührt. Diese Datei erscheint nie als eigener Titel und ist weg, sobald der Titel fertig ist.

Das **ursprüngliche Änderungsdatum bleibt erhalten**, sodass das Verbessern einer Bibliothek _Kürzlich hinzugefügt_ nicht neu durchmischt.

### Schreibgeschützte Musikordner

Eine Verbesserung schreibt Tags an Ort und Stelle neu, daher werden Titel auf einem schreibgeschützten Dateisystem **übersprungen**, mit einer Erklärung, bevor Metadaten, Cover oder Songtexte nachgeschlagen werden. Sie bleiben abspielbar und in ihren Playlists; ihre Dateien und Mount-Berechtigungen bleiben unverändert. Ein übersprungener schreibgeschützter Titel wird nicht als erfolgreich geprüft gemerkt, kann also erneut berücksichtigt werden, wenn sein Ordner später beschreibbar wird. Unerwartete Berechtigungs-, Speicherplatz- und E/A-Fehler erscheinen weiterhin als Fehlschläge.

Das unterscheidet sich von der [Anreicherung vorhandener Ordner](external-library.md), die Cover und Songtexte getrennt im Datenordner von Downtify halten kann, ohne geschützte Audiodateien neu zu schreiben.

## Warum Audio nicht ersetzt wird

Gewöhnliche Tag-Verbesserungen ersetzen kein Audio. Der separate Modus unten erfordert exakte Aufnahmemetadaten und eine Veröffentlichungsreferenz; unsichere Versionen bleiben zur manuellen Prüfung.

## Ersatz von Aufnahmen durch Deemix

Nach dem Aktivieren und Testen der [Deemix-Quelle](deemix.md) bietet **Bibliothek verbessern** vor dem Scan zwei unabhängige Schalter:

- **Use verified Deemix recordings**: scannt die ursprünglichen Downtify-Downloads, auch von einer bevorzugten externen Sammlung verdeckte Kopien. Ordnet exakt Künstler, vollständigen Titel/Version und Album zu; lehnt mehrdeutige Katalogergebnisse ab. Die Länge des alten Clips wird nicht verwendet, um eine korrekte Katalogaufnahme abzulehnen. Prüft die heruntergeladenen Tags, die Katalogdauer, die gewählte Qualität und die vollständige FFmpeg-Dekodierung.
- **Remove old Downtify audio after import**: entfernt zusätzlich jedes unveränderte Original nach der Veröffentlichung. Standardmäßig aus. Das Behalten der Originale aktualisiert Playlists und Favoriten trotzdem auf die Deemix-Aufnahme.

Dieser Scan erzeugt statt Cover-/Songtext-/Tag-Aufträgen eine **Audio**-Kategorie. Deemix besitzt die Ausgabedateien, das Artwork, das Albumlayout und die nativen Songtexte. Downtify liest sie an Ort und Stelle. Vorhandene native oder eingebettete Songtexte bleiben erhalten; nur fehlende Songtexte dürfen in einem beschreibbaren, dedizierten Songtext-Ordner ergänzt werden, ohne das Audio neu zu schreiben. Ein verlustfreies Original höherer Qualität bleibt erhalten, wenn Deemix auf MP3 konfiguriert ist.

Die Veröffentlichung geschieht einmal pro Batch. M3U-Kommentare, manuelle Markierungen und die Titelreihenfolge bleiben erhalten; dann wandern Katalogpfade, Playlist-Zugehörigkeiten, die Likes aller Benutzer, Besitz und Regeln für verborgene Titel in einer einzigen SQLite-Transaktion. Gecachte Navidrome-IDs alter Dateien werden für eine frische native Suche ungültig gemacht. Bereits ausgegebene mobile IDs und alte Wiedergabe-URLs behalten schreibgeschützte Aliase auf den registrierten Ersatz; Änderungen nutzen diese URL-Aliase nie.

Dauerhafte Belege in der Bibliotheksdatenbank halten die SHA-256-Werte von Quelle/Ziel und den Veröffentlichungsstatus fest. Quellen bleiben, bis Ersatz und Referenzen verifiziert sind. Ein geänderter oder fehlender Mount, eine bearbeitete Datei, eine externe schreibgeschützte Playlist-Referenz, aktive Wiedergabe oder eine fehlgeschlagene Katalogveröffentlichung stoppen die Bereinigung mit sichtbarem Grund. Pause/Fortsetzen und Neustart verwenden die Belege wieder. Es gibt keinen allgemeinen Dublettendurchlauf und keine altersbasierte Bereinigung: Nur verifizierte Originale im Download-Ordner von Downtify kommen infrage. Manuelle Deemix-/slskd-Downloads, externe Originale, Verzeichnisse und Sidecars werden nie gelöscht. Ist ein Original einmal entfernt, stellt ein Zurückrollen des Containers diese Datei nicht wieder her; stelle sie bei Bedarf aus deinem eigenen Speicher-Backup wieder her.

Für NAS-Nutzer, deren Mount-Namen von den Docker-Pfaden abweichen, kann ein Administrator `DOWNTIFY_DEEMIX_M3U_ROOT` auf einen Container-Alias setzen, der auf die Deemix-Wurzel zeigt. Relative M3U-Pfade nutzen diesen Alias (zum Beispiel `/Download`, abgebildet auf `/music/existing`). Das optionale `DOWNTIFY_LIBRARY_READY_MARKERS` ist ein JSON-Objekt aus Markerpfaden und erwartetem Text, geprüft vor Vorbereitung und Bereinigung. Ein fehlender Marker schlägt sicherheitshalber fehl. Keine der Variablen ist für den Standardmodus nötig.

Die Scan-API akzeptiert `replace_audio_deemix: true`, optional `delete_replaced_audio: true` und optional `files: ["relative/original.mp3"]` für einen begrenzten Pilotlauf. Das Starten dieses Scans wählt `categories: ["audio"]`. Der Laufstatus enthält Ersatzzahlen und einen `finalization_error`, wenn die Veröffentlichung pausiert. Keine Quelldatei wird entfernt, nur weil ein Deemix-Warteschlangeneintrag „abgeschlossen“ meldet.

### Eine unsichere Aufnahme prüfen

Ein übersprungener oder fehlgeschlagener Audio-Auftrag bietet **Choose a Deezer recording**. Füge einen exakten Titellink ein, sieh dir Künstler, Album und Länge in der Vorschau an und wähle **Analyze this choice**. Das bereitet nur einen neuen Einzeltitel-Scan vor; bestätige diesen Scan, um den Ersatz zu starten. Der standardmäßige automatische Abgleich rät nie ein anderes Album.

Diese ausdrückliche Wahl kann ein altes Album-Label korrigieren, aber vollständiger Titel/Version und Künstler müssen weiterhin passen. Ein bekanntes explizites Original kann nicht stillschweigend zu einer bereinigten Version werden. Die gewählte Aufnahme durchläuft dieselben Prüfungen zu Dauer, Qualität, Dekodierung, Referenz und Löschung. Eine andere Wahl kann nicht stillschweigend einen bereits vorbereiteten Beleg wiederverwenden. Die erweiterte Scan-Nutzlast hält die Wahl als `deemix_recordings: {"relative/original.mp3": "123456"}` fest; sie ist auf diese Datei begrenzt und für Neustart/Fortsetzen gespeichert.

## API

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/api/library/upgrade` | Laufstatus, Warteschlangenzahlen und was der Scan fand |
| `GET` | `/api/library/upgrade/jobs` | Zeilen pro Titel (`status`, `stage`, `detail`) |
| `POST` | `/api/library/upgrade/scan` | Scannt die Bibliothek; schreibt nichts |
| `POST` | `/api/library/upgrade/start` | Startet den Lauf für die gewählten `categories` |
| `POST` | `/api/library/upgrade/pause` | Stoppt nach dem aktuellen Titel, behält die Warteschlange |
| `POST` | `/api/library/upgrade/resume` | Setzt einen pausierten Lauf fort |
| `POST` | `/api/library/upgrade/cancel` | Verwirft den Rest der Warteschlange |

Der Fortschritt wird auch über den [WebSocket](../api-reference.md#websocket) als `{"type": "library_upgrade", "upgrade": {…}}` gepusht.

Siehe die [API-Referenz](../api-reference.md#library) für Anfrage- und Antwortformate.
