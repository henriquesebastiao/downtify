---
icon: lucide/folder-plus
---

# Vorhandene Musikordner

Die Bibliothek von Downtify besteht aus den Dateien, die es heruntergeladen hat — plus allen **zusätzlichen Ordnern**, auf die du es verweist. Diese Ordner werden nicht nach `/downloads` kopiert. Downtify liest die Tags jeder Datei (Titel, Künstler, Album, Titelnummer, Jahr), überspringt Songs, die du schon hast, und ordnet den Rest in der Bibliothek und im Player unter dem passenden Künstler ein.

## Ordner hinzufügen

1. Binde den Host-Ordner in den Container ein (Docker). Der Pfad, den du in den Einstellungen eingibst, ist der **innerhalb des Containers** — dieselbe Regel wie beim [Download-Ordner von slskd](slskd-navidrome.md).
2. Öffne **Einstellungen → Bibliothek**.
3. Füge unter **Vorhandene Musikordner** einen oder mehrere Pfade hinzu (zum Beispiel `/music/collection`). Das Feld schlägt beim Tippen Verzeichnisse vor.
4. Klicke auf **Speichern**, wenn du sie behalten, aber noch nicht synchronisieren willst, oder auf **Ordner synchronisieren** — das speichert die Liste und scannt sofort.

```yaml
services:
  downtify:
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

Dann lautet der Ordner in den Einstellungen `/music/collection`.

::: warning Dateien bleiben, wo sie sind
Die Synchronisierung kopiert keine Dateien nach `/downloads`. Ist der Ordner beschreibbar, schreibt sie in diese Dateien **sehr wohl** dieselben Extras wie ein Download: Songtexte (und eine `.lrc`-Begleitdatei — neben der Datei oder im in den Einstellungen gewählten Ordner), ein Cover, falls die Datei keines hat, und das Genre von iTunes, wenn möglich. Eine spätere Synchronisierung schreibt eine fehlende Begleitdatei auch dann, wenn die Songtexte schon in den Tags stehen, und **verschiebt** eine vorhandene `.lrc` an den aktuell in den Einstellungen gewählten Ort, wenn diese Quelldatei beschreibbar ist. Das Löschen eines Titels in der Bibliothek löscht weiterhin diese Datei auf der Platte.
:::

::: tip Schreibgeschützte Mounts
Binde die Sammlung mit `:ro` ein, wenn Downtify die MP3s nicht neu schreiben soll. Die Synchronisierung indiziert sie trotzdem. Lege `.lrc`-Dateien im [Songtext-Ordner](lyrics.md#sidecar-lrc-file) ab (schalte **.lrc-Datei neben Audiodatei speichern** aus). Fehlende Cover werden unter `/data/cover_cache` (dem Cover-Endpunkt der Bibliothek) gespeichert, nicht in der MP3. Das iTunes-Genre wird in der Metadatendatenbank der Downtify-Bibliothek gespeichert, nicht in der Datei. Eine `.lrc`, die schon neben einer schreibgeschützten Datei liegt, wird in den Songtext-Ordner **kopiert** und an Ort und Stelle belassen.
:::

## Was die Synchronisierung tut

1. Durchsucht jeden konfigurierten Ordner nach abspielbarem Audio (dieselben Formate wie in der übrigen Bibliothek: MP3, M4A, FLAC, OGG, WAV, AAC, OPUS).
2. Liest eingebettete Tags. Eine Datei ohne Titel/Künstler fällt auf `Künstler - Titel` im Dateinamen zurück, wie andere Bibliothekszeilen.
3. **Überspringt** eine Datei, wenn die Bibliothek diesen Song schon hat (gleicher Künstler + Titel und Länge auf wenige Sekunden genau, wenn beide bekannt sind) — egal ob von Downtify heruntergeladen oder aus einem anderen zusätzlichen Ordner.
4. **Ordnet Künstler zu** bereits vorhandenen Namen in der Bibliothek zu (`The Beatles` und `Beatles` werden ein Künstler). Namen, die zu keinem bekannten Künstler passen, erscheinen als neuer Künstler. Neue Künstler werden für dieselbe Profilbefüllung (Foto/Bio, wenn diese Einstellungen aktiv sind) wie nach einem abgeschlossenen Download eingeplant.
5. **Taggt wie ein Download**, wenn der Ordner beschreibbar ist. Für jeden importierten Titel nutzt es dieselben Songtext-Anbieter, dieselbe Cover-Suche (nur wenn die Datei kein Artwork hat) und dieselbe iTunes-Genre-Suche wie ein Download. Songtexte kommen in die Datei; eine `.lrc`-Begleitdatei wird neben das Audio oder in den in den Einstellungen gewählten [Songtext-Ordner](lyrics.md#sidecar-lrc-file) geschrieben. Cover und Genre folgen den [Download-Einstellungen](download-settings.md) (`download_cover_art`, `download_lyrics`). Bei einem **schreibgeschützten** Mount wird die MP3 nicht neu geschrieben: Ein fehlendes Cover wird unter `/data/cover_cache` abgelegt, das Genre im Bibliothekskatalog gespeichert, und `.lrc`-Dateien gehen in den Songtext-Ordner, falls du einen gewählt hast. Die Abfragen laufen in Stapeln der Größe **Parallele Downloads**; eine **Pause zwischen Synchronisierungsabfragen** unter Einstellungen → Downloads und Dateien wartet zwischen diesen Stapeln, damit große Ordner nicht an Ratenlimits der Anbieter stoßen.
6. Verwirft den Pfad-Cache der Bibliothek, damit Bibliotheksseite und Player das Ergebnis sehen, ohne die übliche kurze Scan-TTL abzuwarten.

Die Synchronisierung läuft **im Hintergrund**. Du kannst die Einstellungen verlassen; kommst du zurück, während sie noch arbeitet, siehst du, dass sie weiter synchronisiert. Ist sie fertig, zeigen die Einstellungen das **letzte Synchronisierungsprotokoll** (importiert / Duplikat / Fehler sowie Hinweise zu Songtexten/Covern).

Führe **Ordner synchronisieren** erneut aus, nachdem du weitere Dateien in diese Ordner gelegt hast. Das Speichern der Ordnerliste ohne Synchronisierung bezieht sie beim nächsten Bibliotheksscan ebenfalls ein (etwa eine Minute, oder beim nächsten Download/Löschen).

Das Entfernen eines Ordners aus der Liste **hebt seine Zuordnung auf**: Diese Titel verschwinden aus der Bibliothek und dem Player, und von Downtify erzeugte Extras (`.lrc`-Begleitdateien, zwischengespeicherte Cover) werden gelöscht. Die Audiodateien auf der Platte bleiben, wo sie sind.

Ordner, die nicht existieren oder nicht lesbar sind, werden nach der Synchronisierung gemeldet; die anderen werden trotzdem gescannt.

## Bibliothekspfade

Dateien aus zusätzlichen Ordnern verwenden einen virtuellen Pfad `ext/<id>/…` (die ID ist ein Hash des Ordnerpfads, die Liste lässt sich also umsortieren). Der Player und `GET /media/…` nutzen diesen Pfad, wie `slskd/…` für an Ort und Stelle belassene Soulseek-Dateien.

Ein Ordner, der schon **innerhalb** von `/downloads` (oder des slskd-Quellordners) liegt, wird hier ignoriert — dieser Baum ist bereits die Bibliothek.

## API

| Methode | Pfad                          | Beschreibung                                                                     |
| ------ | ----------------------------- | -------------------------------------------------------------------------------- |
| `POST` | `/api/library/external/sync`  | Startet einen Hintergrundscan. Ein optionaler Body `{folders: ["/path", …]}` wird zuerst gespeichert. |
| `GET`  | `/api/library/external/sync`  | Laufender Auftrag oder das zuletzt abgeschlossene Protokoll.                     |
| `POST` | `/api/library/external/unmap` | Entfernt einen Ordner aus der Bibliothek, ohne das Audio zu löschen.             |

Das Antwortformat steht in der [API-Referenz](../api-reference.md#post-apilibraryexternalsync).

## Primärer Bibliotheksordner

Wähle **Einstellungen → Bibliothek → Primary library folder**, um einen der
registrierten externen Ordner zu bevorzugen. Die Voreinstellung erhält das bestehende Verhalten.
Übereinstimmende Künstler, vollständiger Titel (einschließlich Version) und Album sind erforderlich;
unbekannte Metadaten verbergen keine andere Datei. Eine gewählte Quelle kann eine Aufnahme darstellen,
deren andere Kopie Clip-Intros oder -Outros enthält.

Das ist eine Anzeigepräferenz, keine Migration. Quelldateien, gespeicherte Playlist-Pfade,
Besitz, Likes und Sichtbarkeitsregeln werden weder neu geschrieben noch gelöscht.
Playlist-Kennzeichen werden auf dem angezeigten Vertreter zusammengeführt; explizit gespeicherte
Playlists spielen weiterhin ihre ursprünglichen Pfade ab. Verschiedene Alben und Versionen im
gewählten Ordner bleiben getrennt. Ein leerer oder nicht verfügbarer Ordner fällt auf die übrige Bibliothek zurück.
Das Entfernen setzt die Präferenz zurück.
