---
icon: lucide/trending-up
---

# Charts

**Charts** zeigt Deezers eigene globale Hitliste — ohne Genre-Filter, einfach das, was weltweit gerade angesagt ist — ohne Deezer-Konto oder API-Schlüssel.

## So nutzt du es

Öffne **Charts** in der Seitenleiste (auf dem Smartphone im Fenster **Mehr**). Vier Tabs lesen aus derselben Hitliste: **Titel**, **Alben**, **Künstler** und **Playlists**.

- **Titel** — eine Rangliste. Drücke auf einen Titel (oder tippe auf seine Zeile), um ihn vor dem Herunterladen vollständig von YouTube direkt im integrierten Player zu streamen. Das Herunterladen einer Zeile funktioniert wie bei einem Suchergebnis: Downtify sucht auf YouTube Music (ersatzweise auf normalem YouTube) nach dem besten Treffer für Titel, Künstler und Länge des Songs — über dieselbe [Zuordnungs-Pipeline](../how-it-works.md) wie jeder andere Download. Ist ein Titel heruntergeladen, spielt seine Zeile ihn aus deiner Bibliothek ab, statt zu streamen.
- **Alben**, **Künstler** und **Playlists** — Cover-Raster. Ein Klick löst das Element auf ([`GET /api/url/resolve`](../api-reference.md#get-apiurlresolve)), genau so, als hättest du diesen Deezer-Link selbst ins Suchfeld eingefügt: Seine Titelliste wird geladen und ist bereit zum Auswählen und Herunterladen.

## Warum Titel direkt von hier heruntergeladen (und vollständig abgespielt) werden, Alben, Künstler und Playlists aber zuerst eine Seite öffnen

Ein Chart-Titel braucht zum Herunterladen keinen Auflösungsschritt: Deezer liefert bereits Titel, Künstler und Albumnamen, und das genügt, um auf YouTube zu suchen und zuzuordnen — genau wie bei einem Freitext-Suchergebnis. Ein Album, ein Künstler oder eine Playlist braucht ihn schon — den Link in eine Titelliste verwandeln —, deshalb öffnet seine Karte diese aufgelöste Seite, statt direkt aus dem Raster herunterzuladen. Das Abspielen einer Titelzeile streamt vollständig von YouTube (nie bei Alben, Künstlern oder Playlists) — dasselbe Streaming wie bei jeder anderen Titelzeile, nur gespeist mit Titel und Künstler der Hitliste.

## Eine Chart-Playlist beobachten oder speichern

Jede Playlist-Karte hat ein Menü **⋯** über ihrem Cover, mit den zwei Dingen, die ihre Seite neben dem Herunterladen bietet:

- **Auf neue Titel achten** fügt eine Beobachtung der [Playlist-Überwachung](playlist-monitor.md#deezer-playlists) hinzu, die alle 6 Stunden geprüft wird: Die erste Prüfung lädt herunter, was die Playlist jetzt enthält, spätere das, was hinzukommt. Intervall ändern, pausieren oder beenden kannst du auf der Seite **Überwachung**.
- **Zu meinen Playlists hinzufügen** öffnet die Playlist-Auswahl mit den Titeln der Playlist, die **schon in deiner Bibliothek** sind, um sie zu einer deiner Playlists oder einer neuen, nach ihr benannten hinzuzufügen. Es wird nichts heruntergeladen, und deine Playlist folgt der Chart-Playlist danach nicht — dafür gibt es die Download-Schaltfläche oder **Auf neue Titel achten**. Ist noch keiner ihrer Titel in der Bibliothek, wird das stattdessen angezeigt.

## API

Siehe [`GET /api/discover/chart`](../api-reference.md#get-apidiscoverchart) in der API-Referenz.
