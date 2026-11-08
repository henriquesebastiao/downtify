---
icon: lucide/heart
---

# Lieblingssongs

Tippe auf das Herz eines Songs, um ihn zu liken. Sobald ein Song geliked ist, führt Downtify eine Playlist **Lieblingssongs** mit allen Songs, die du geliked hast — deine Favoriten sind so einen Klick entfernt, in Downtify und in jedem Medienserver, der auf deine Bibliothek zeigt.

Es muss nichts aktiviert werden.

Herzen gehören dem, der sie getippt hat: Auf einem Server mit mehreren Konten hat jede Person ihre eigenen Lieblingssongs (siehe [Benutzer und Anmeldung](users.md#your-library)). Die Playlist-Datei auf der Festplatte enthält die Herzen der Admins; die Likes aller anderen liegen in der Bibliotheksdatenbank und funktionieren in den Apps genauso.


## Einen Song liken

Das Herz steht neben jedem Song in deiner Bibliothek — Downloads und Titel aus [vorhandenen Musikordnern](external-library.md):

- in den Titellisten — Bibliothek, Alben, Künstler und Playlists;
- in der [Player-Leiste](player.md#player-bar) (auf Bildschirmen ab 640 px Breite);
- in [Aktuelle Wiedergabe](player.md#now-playing), neben dem Songtitel.

Tippe zum Liken, tippe erneut, um das Like zurückzunehmen. Das Herz füllt sich grün, und die Änderung liegt sofort auf dem Server — ein auf dem Smartphone getipptes Herz ist also auch auf dem Desktop da; offene Tabs und Geräte ziehen von selbst nach.

Nur Songs aus deiner Bibliothek lassen sich liken. Ein Suchergebnis, das du noch nicht heruntergeladen hast, hat kein Herz; lade es zuerst herunter.

## Die Playlist

Das erste Like erstellt die Playlist, und ein kurzer Hinweis bietet an, sie zu öffnen. Sie wird wie jede andere Playlist aufgeführt — in der Seitenleiste, auf der Startseite und unter **Bibliothek → Playlists** —, aber immer **ganz oben**, mit einem Herz statt eines Covers. Ihre Songs sind so sortiert, dass der zuletzt gelikte oben steht.

Wird das letzte Like zurückgenommen, verschwindet die Playlist wieder; es bleibt keine leere **Lieblingssongs**-Playlist übrig.

Der Titel folgt deiner [Sprache](internationalization.md). Auf der Festplatte ist die Playlist eine schlichte [M3U-Datei](m3u-export.md) mit festem Namen:

```
<downloads>/Playlists/Downtify Liked Songs.m3u
```

Deshalb zeigen Jellyfin, Navidrome, Plex und Co. sie ebenfalls: Sie lesen dieselbe Datei. Der Name ist absichtlich reserviert. Spotify-Playlists namens *Liked Songs* sind häufig, und eine heruntergeladene Playlist dieses Namens hätte sonst in dieselbe Datei geschrieben.

## Alle Likes entfernen

Öffne die Playlist, dann **⋯ → Alle Likes entfernen**, und bestätige. Alle Herzen werden gelöscht, und die Playlist verschwindet.

::: info Deine Songs bleiben
Das Entfernen von Likes löscht nie Audio. Nur die Herzen und die Playlist werden entfernt — die Dateien bleiben in deiner Bibliothek. Das ist etwas anderes als das Löschen einer heruntergeladenen Playlist, bei dem ihre Songs gelöscht werden; **Lieblingssongs** wird nie so behandelt. Die Aufforderung, sie zu löschen (in der App oder über die [API](../api-reference.md#delete-apilibraryplaylist)), entfernt nur die Likes.
:::

## Likes im Einklang mit den Dateien halten

Ein Like folgt der Datei, der es gegeben wurde:

| Was mit der Datei passiert | Was mit dem Like passiert |
|--------------------------|--------------------------|
| Du löschst den Song in Downtify | Das Like verschwindet mit ihm, und die Playlist wird neu geschrieben |
| Du verschiebst ihn und führst [Bibliothekspfade reparieren](library-catalog.md#fix-library-paths) aus | Das Like folgt der Datei an ihren neuen Ort |
| Sie verschwindet außerhalb von Downtify (ein ausgehängtes Laufwerk, manuelles Löschen) | Das Like bleibt erhalten, der Song fehlt aber in der Playlist, bis er zurück ist |

Dass das Like einer fehlenden Datei erhalten bleibt, heißt: Ein abgestecktess Laufwerk kostet dich nicht deine Herzen. Hast du Dateien von Hand gelöscht und willst auch die Likes loswerden, nutze **Alle Likes entfernen** oder nimm die Likes zurück, bevor du die Songs löschst.

## Gut zu wissen

- Likes werden in der Bibliotheksdatenbank gespeichert (`downtify_library.db`, in deinem `/data`-Volume), nicht in den Audiodateien. In die Tags eines Songs wird nichts geschrieben.
- Die Playlist wird von Downtify nicht in [Navidrome](slskd-navidrome.md) angelegt. Es ist eine schlichte M3U-Datei; was ein Medienserver damit macht, hängt davon ab, wie er M3U-Dateien liest.
- Die [Playlist-Datei](m3u-export.md) wird auch geschrieben, wenn *M3U-Playlists schreiben* in den Download-Einstellungen ausgeschaltet ist: Die Playlist ist der Sinn der Funktion.

## API

`GET /api/likes`, `PUT /api/likes` und `POST /api/likes/clear`, dazu ein `liked`-Flag in [`GET /playlists`](../api-reference.md#get-playlists). Siehe die [API-Referenz](../api-reference.md#likes).
