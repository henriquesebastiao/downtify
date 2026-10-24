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

## API

Siehe [`GET /api/discover/chart`](../api-reference.md#get-apidiscoverchart) in der API-Referenz.
