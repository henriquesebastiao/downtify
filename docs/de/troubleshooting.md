---
icon: lucide/life-buoy
---

# Fehlerbehebung

Häufige Probleme und was sie behebt. Die meisten Download-Fehler lassen sich auf einen der ersten beiden Einträge zurückführen.

## Ein Titel mit explizitem Inhalt lässt sich nicht herunterladen

**Symptom** — der Download schlägt fehl und die Warteschlange zeigt eine Meldung, dass der Titel altersbeschränkt ist, oder (bei älteren Versionen) einen rohen Fehler wie:

```
Error: ERROR: [youtube] <id>: Sign in to confirm your age.
This video may be inappropriate for some users.
```

**Ursache** — YouTube liefert altersbeschränkte (explizite) Titel nur an ein angemeldetes Erwachsenenkonto. Downtify lädt standardmäßig anonym herunter, daher verweigert YouTube.

**Lösung** — YouTube-Cookies bereitstellen: **Einstellungen** (⚙️) → **YouTube-Cookies** → **cookies.txt hochladen**. Wie du die Datei exportierst, steht unter [YouTube-Cookies](features/youtube-cookies.md).

Schlägt es trotz konfigurierter Cookies weiterhin fehl, sind die Cookies veraltet oder das Konto selbst hat Googles Altersprüfung nicht abgeschlossen. Exportiere eine frische Datei aus einem Browser, der in einem verifizierten Konto angemeldet ist, und lade sie erneut hoch.

## Downloads schlagen fehl, laufen in ein Timeout oder starten nie

**Symptom** — Downloads schlagen bei scheinbar gewöhnlichen Titeln fehl, manchmal mit „Melde dich an, um zu bestätigen, dass du kein Bot bist“ oder einem Format-/Extraktionsfehler.

**Ursache** — YouTube drosselt und fordert Anfragen heraus, die es für automatisiert hält. Das kommt auf einem VPS oder hinter einem VPN viel häufiger vor als an einem Heimanschluss.

**Lösung**, in der Reihenfolge, wie oft es hilft:

1. **Eine `cookies.txt` hochladen** ([YouTube-Cookies](features/youtube-cookies.md)). Eine authentifizierte Sitzung wird weit seltener herausgefordert. Das ist die wirksamste Einzelmaßnahme.
2. **Eine Pause zwischen Downloads einfügen** — **Einstellungen** → *Pause zwischen Downloads* (probiere 5–15 s) und *Parallele Downloads* verringern. Eine ganze Playlist auf einmal auf YouTube loszulassen, löst die Drosselung aus.
3. **IPv4 erzwingen** — setze `DOWNTIFY_FORCE_IPV4=1`, wenn dein Host IPv6 ankündigt, es aber nicht wirklich routen kann (zeigt sich als DNS-/`EAI_AGAIN`-Fehler).
4. **Das Image aktualisieren** — `docker compose pull && docker compose up -d`. YouTube ändert seine Abwehr oft, und jedes Release bringt ein neueres `yt-dlp` mit.

## Eine cookies.txt unter Windows / Docker Desktop wird nicht erkannt

**Symptom** — `DOWNTIFY_COOKIES_FILE` ist gesetzt, aber Downtify verhält sich, als gäbe es keine Cookies.

**Ursache** — der Pfad ist ein *Container*-Pfad. Ein Windows-Pfad wie `C:\Users\me\cookies.txt` bedeutet im Container nichts, und die Datei muss per Bind-Mount eingebunden sein, bevor die Variable darauf zeigen kann.

**Lösung** — verzichte ganz auf die Variable und lade die Datei über **Einstellungen** → **YouTube-Cookies** hoch. Dieser Weg braucht keine Mounts und funktioniert auf jeder Plattform gleich.

Willst du die Variable behalten, binde die Datei ein und zeige auf das Mount-Ziel, nicht auf den Host-Pfad:

```yaml
volumes:
  - ./cookies.txt:/cookies.txt:ro
environment:
  - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

## Die Schaltfläche zum Hochladen von Cookies ist ausgegraut

`DOWNTIFY_COOKIES_FILE` ist gesetzt, daher verwaltet diese Bereitstellung ihre Cookie-Datei selbst, und die Weboberfläche bleibt absichtlich schreibgeschützt. Entferne die Variable (und erstelle den Container neu), um Cookies über die Oberfläche zu verwalten.

## Hochgeladene Cookies sind nach dem Container-Update verschwunden

Die hochgeladene Datei liegt im Datenverzeichnis von Downtify (`/data`). Ist dieses Verzeichnis kein benanntes Volume oder Bind-Mount, geht alles darin — Einstellungen und die Datenbank der Playlist-Überwachung eingeschlossen — verloren, wenn der Container neu erstellt wird:

```yaml
volumes:
  - ./downloads:/downloads
  - downtify_data:/data   # ← das beibehalten
```

## „cookies.txt is invalid“ beim Hochladen

Downtify prüft die Datei beim Hochladen. Sie muss ein **Netscape**-Cookie-Jar sein: ein Cookie pro Zeile, Felder durch Tabs getrennt, optional mit `#`-Kommentaren. Ein JSON-Export, eine Tabelle oder ein kopierter `Cookie:`-Header wird abgelehnt.

Nutze eine Browsererweiterung, die im Netscape-Format exportiert (siehe [YouTube-Cookies](features/youtube-cookies.md)), und exportiere, während der Tab auf `youtube.com` steht.

## Eine Playlist lädt Titel erneut herunter, die ich schon habe

Downtify vermerkt jeden automatisch heruntergeladenen Titel in seiner Datenbank, daher löst das Verschieben von Dateien an einen anderen Ort auf der Platte keinen erneuten Download aus. Ein Titel wird erst erneut heruntergeladen, wenn eine stündliche Prüfung feststellt, dass seine Datei im Download-Verzeichnis tatsächlich fehlt. Siehe [Playlist-Überwachung](features/playlist-monitor.md#how-it-works).

Verschwinden Dateien bei jedem Neustart, ist das Volume `/downloads` nicht persistent — gleiche Lösung wie oben.

## „Could not find a YouTube match for '…'“

Weder YouTube Music noch normales YouTube lieferten ein Ergebnis, das die Prüfungen des Abgleichs bestand — Titel ähnlich der Quelle, mindestens ein gemeinsamer Künstler, keine Karaoke-/Cover-/Live-/anderssprachige Version und eine Länge innerhalb von 30 Sekunden zu Spotify. Siehe [So funktioniert es](how-it-works.md#fallback-to-standard-youtube).

Das heißt meist, dass der Song tatsächlich nicht auf YouTube ist oder nur unter einem sehr anderen Titel oder Künstlernamen hochgeladen wurde. Findest du das richtige Video selbst, füge seine YouTube-URL in die Suchleiste ein, um genau dieses Video herunterzuladen.

## Das heruntergeladene Audio hat falsche Metadaten oder ein falsches Cover

Downtify bezieht die Metadaten von Spotify und ordnet das Audio auf YouTube Music zu. Eine Abweichung bedeutet meist, dass die Zuordnung bei einem Cover, Remix oder einer Live-Version gelandet ist. Der Download über den **Album**-Link von Spotify statt über ein Suchergebnis gibt dem Abgleich deutlich mehr an die Hand (Titelnummer, Album, Veröffentlichungstyp).

## Immer noch festgefahren?

Eröffne ein Issue unter [github.com/henriquesebastiao/downtify/issues](https://github.com/henriquesebastiao/downtify/issues) mit:

- der Downtify-Version (unten in der Seitenleiste und unter **Einstellungen → Über** zu sehen),
- den Container-Logs rund um den Fehler (`docker compose logs downtify`),
- und der Angabe, ob Cookies konfiguriert sind.
