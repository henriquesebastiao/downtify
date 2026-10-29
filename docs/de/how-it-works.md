---
icon: lucide/cog
---

# So funktioniert es

Die Download-Pipeline von Downtify hat drei Stufen:

```
Spotify embed  →  YouTube Music search  →  yt-dlp + ffmpeg + mutagen
  (metadata)         (audio match)          (download & tag)
```

## 1. Metadaten — Auslesen der Spotify-Einbettung

Wenn du eine Spotify-URL einfügst, holt Downtify die öffentliche Seite `open.spotify.com/embed` für diesen Titel, dieses Album oder diese Playlist. Es braucht weder ein Spotify-Konto noch einen API-Schlüssel oder ein Premium-Abo — die Einbettungsseite ist öffentlich zugänglich.

Für **Titel** liefert die Einbettung: Titel, Künstler, Albumname, Erscheinungsjahr, Länge und die URL des Covers.

Für **Alben und Playlists** liefert sie die Titelliste. Playlist-Einbettungen sind auf etwa 50–100 Einträge begrenzt, daher fordert Downtify die vollständige Liste zusätzlich vom anonymen Endpunkt `api.spotify.com` von Spotify mit Paginierung an, um Playlists mit Hunderten von Songs zu bewältigen.

::: info Anreicherung der Metadaten pro Titel
Playlist-Einträge der Einbettung enthalten kein Erscheinungsjahr und nutzen das Playlist-Cover statt des Album-Covers jedes Titels. Für die [Playlist-Überwachung](features/playlist-monitor.md) ruft Downtify jeden neuen Titel vor dem Download einzeln erneut ab, um das richtige Cover und Jahr zu erhalten.
:::

## 2. Audio-Zuordnung — YouTube Music, dann YouTube

Downtify nutzt [`ytmusicapi`](https://ytmusicapi.readthedocs.io/), um YouTube Music nach dem besten Audiotreffer zu durchsuchen. Die Suchanfrage wird aus Titel und Künstlername gebildet.

Ein Ergebnis wird nur akzeptiert, wenn sein Titel dem Quelltitel ähnelt und es mindestens einen Künstler gemeinsam hat. Spotifys Versionszusatz mit Bindestrich und der in Klammern von YouTube Music gelten als gleich (`Tubarões - Ao Vivo` passt zu `Tubarões (Ao Vivo)`), und eine Künstlerangabe, die YouTube Music in einen Eintrag packt (`A, B, and C`), wird vor dem Vergleich aufgeteilt. Ein vorangestelltes „The“ in Künstlernamen wird ignoriert (`Eden Project` passt zu `The Eden Project`), und ein Titel darf zu einem durch ` - ` getrennten Teil des Upload-Titels passen (`くちづけDiamond - Kuchizuke Diamond`, `Game OST - Song Title - Artist`), solange die übrigen Teile keine andere Version nennen. Karaoke-, Cover-, Instrumental-, beschleunigte/verlangsamte, Live- (auch `Ao Vivo`/`En Vivo`), Akustik-, Remix- und anderssprachige Versionen (z. B. `(Spanish Version)`) werden abgelehnt, es sei denn, der Quelltitel ist selbst diese Version. Unter den verbleibenden Ergebnissen gewinnt das, dessen Länge der von Spotify am nächsten kommt, mit einem Bonus für einen passenden Albumnamen. Qualifiziert sich kein Ergebnis, wird die Suche mit den Wörtern in anderer Reihenfolge wiederholt (`<Titel> <Künstler>` statt `<Künstler> <Titel>`) — YouTube Music sortiert Ergebnisse je nach Wortreihenfolge anders, und manche Songs erscheinen nur in einer Variante weit oben. Findet auch das nichts und ist das Album bekannt, wird die Titelliste des Albums direkt durchsucht.

### Rückfall auf normales YouTube

Manche Songs fehlen bei YouTube Music oder existieren dort nur als andere Aufnahme. Daher wird auch normales YouTube durchsucht, wenn:

- YouTube Music **keinen akzeptablen Treffer** hat, oder
- die Länge des besten Treffers **mehr als 10 Sekunden** von der bei Spotify abweicht — ein starker Hinweis auf eine andere Aufnahme (z. B. eine synchronisierte Version mit demselben Titel).

Ergebnisse von normalem YouTube durchlaufen dieselben Titel-, Künstler- und Versionsprüfungen und werden nie akzeptiert, wenn sie mehr als 30 Sekunden von Spotifys Länge abweichen. Ein YouTube-Ergebnis ersetzt einen schwachen YouTube-Music-Treffer nur, wenn seine Länge strikt näher liegt; andernfalls bleibt der YouTube-Music-Treffer, da seine Katalog-Uploads meist das sauberste Audio haben.

Hat keine der beiden Seiten einen akzeptablen Treffer, schlägt der Titel mit `Could not find a YouTube match for '<title>'` fehl, statt den falschen Song herunterzuladen.

Bei direkt eingegebenen YouTube-URLs entfällt dieser Schritt — Downtify lädt genau dieses Video herunter.

::: info Deezer-Links
Ein eingefügter Deezer-Link zu Titel/Album/Playlist/Künstler (`deezer.com/track/…`) funktioniert wie ein Spotify-Link: Die öffentliche REST-API von Deezer liefert Titel, Künstler, Album und Cover, jeder Titel lässt sich vor dem Download vollständig von YouTube streamen, und derselbe Schritt ordnet ihn dann auf YouTube Music/YouTube zu. Downtify hat über das hinaus, was Deezers API schon liefert, keinen eigenen Deezer-Diskografie-Auflöser; ein Deezer-Link wird also heruntergeladen und (bei einer Playlist) mit eigener M3U und eigenem Cover versehen, kann aber nicht von der [Playlist-Überwachung](features/playlist-monitor.md) beobachtet werden.
:::

## 3. Download und Tagging — yt-dlp + ffmpeg + mutagen

### Download

[yt-dlp](https://github.com/yt-dlp/yt-dlp) lädt das Audio von YouTube herunter. Downtify konfiguriert es so, dass es mehrere Player-Clients der Reihe nach probiert (`ios`, `android`, `web_embedded`, `mweb`, `web`, `tv`), um die Bot-Erkennung von YouTube zu umgehen. Erweiterte Anti-Bot-Optionen stehen unter [Umgebungsvariablen](getting-started/environment-variables.md).

### Konvertierung

[ffmpeg](https://ffmpeg.org/) wandelt das Roh-Audio in das gewählte Format (MP3, FLAC, M4A, OGG oder OPUS) mit der gewählten Bitrate um.

### Tagging

[mutagen](https://mutagen.readthedocs.io/) schreibt die Metadaten in die konvertierte Datei:

| Tag | Geschrieben |
|-----|---------|
| Titel | Ja |
| Künstler | Ja, alle genannten Künstler, außerdem einzeln als Werte eines `ARTISTS`-Tags |
| Albumkünstler | Ja, der Künstler des Albums, wie die Quelle ihn nennt, sonst der erste Künstler |
| Compilation-Flag | Nur bei einem Album, das die Quelle „Various Artists“ zuschreibt oder das ein Admin als solches markiert |
| Album | Ja |
| Jahr | Ja |
| Albumcover (JPEG) | Ja |
| Songtexte (einfach + synchron) | Ja, wenn lrclib ein Ergebnis liefert |
| Explicit-Kennzeichnung | Ja, wenn der Song als explizit markiert ist (siehe [Explicit-Kennzeichnung](features/explicit-marker.md)) |

Welche ID3-/Vorbis-/MP4-Tags genau verwendet werden, hängt vom Ausgabeformat ab. Wie Songtexte eingebettet werden, steht unter [Songtexte](features/lyrics.md).

## Fortschritt in Echtzeit

Downtify streamt den Download-Fortschritt per **WebSocket**-Verbindung (`/api/ws`) an den Browser. Sobald yt-dlp Fortschritt meldet, sendet der Server Prozent- und Statusaktualisierungen an alle verbundenen Clients. So siehst du den Fortschrittsbalken in Echtzeit wandern — ohne Polling, ohne Neuladen der Seite.

## Dateinamen und Organisation

Der Ausgabedateiname wird aus der in den Einstellungen konfigurierten Vorlage gebildet (Standard: `{artists} - {title}`). In Dateinamen ungültige Zeichen werden entfernt.

Ist *Nach Künstler sortieren* aktiv, kommt die Datei in einen Unterordner mit dem Namen des Albumkünstlers — oder, bei einem Titel einer Various-Artists-Compilation, seines ersten Künstlers. Andernfalls landen einzelne Titel im Hauptverzeichnis des Download-Ordners, und Playlist-/Albumtitel kommen in einen Unterordner pro Playlist oder Album. Siehe [Mehrere Künstler und Compilations](features/file-organization.md#several-artists-and-compilations).
