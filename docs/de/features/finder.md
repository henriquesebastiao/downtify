---
icon: lucide/columns-3
---

# Finder

Der **Finder** ist eine Möglichkeit, den Deezer-Katalog vor dem Herunterladen zu erkunden. Du suchst bei Deezer, öffnest einen Künstler und durchstöberst ihn in drei Spalten nebeneinander, wie in der Spaltenansicht des macOS-Finders: der Künstler, seine Diskografie und die Titel eines Albums. Ein Deezer-Konto oder API-Schlüssel ist nicht nötig.

## Suchen

Öffne **Entdecken** in der Seitenleiste (am Handy: **Mehr → Entdecken**): Das Suchfeld des Finders steht oben auf der Seite, daneben deine letzten Finder-Suchen. Eine Suche ersetzt die Vorschläge von Entdecken durch das Gefundene — Titel, Alben und Künstler mit den Chips **Alle / Titel / Alben / Künstler**, wie auf der normalen Suchseite, aber nur von Deezer. Leere das Feld (das **×**) oder gehe zurück, um die Vorschläge wieder zu sehen; eine letzte Suche läuft mit einem Klick erneut, und **Leeren** vergisst alle. Letzte Suchen werden nur in diesem Browser gespeichert.

**Titel finden** im **⋯**-Menü eines von Entdecken vorgeschlagenen Künstlers zeigt dessen Titel hier als Suche: Deezer wird nach dem Namen des Künstlers durchsucht, und nur die Titel genau dieses Künstlers — erkannt an seiner Deezer-ID, sodass ein Namensvetter oder ein Titel, der nur so heißt, außen vor bleibt — werden aufgelistet, bis zu den ersten paar hundert.

- **Titel** werden vollständig gestreamt und wie jedes Suchergebnis heruntergeladen. Downtify ordnet den Titel anhand von Titel, Künstler und Länge bei YouTube Music zu (mit YouTube als Rückfall). Ein Klick auf den Titelnamen öffnet sein Album in der Spaltenansicht, der Titel ist hervorgehoben.
- **Alben** öffnen sich bei ihrem Künstler, das Album ist ausgewählt. Die Download-Schaltfläche auf dem Cover reiht das ganze Album ein.
- **Künstler** öffnen die Spaltenansicht bei diesem Künstler.

## Die Spaltenansicht

| Spalte | Was sie zeigt |
| --- | --- |
| **Künstler** | Das Foto des Künstlers und die Anzahl der Alben, seine Biografie in der Sprache der Oberfläche (aufklappbar), seine 10 beliebtesten Titel und „Fans hören auch“ (verwandte Künstler). |
| **Diskografie** | Jedes Album, jede Single, EP und Compilation, das Neueste zuerst, mit Cover, Titel, Veröffentlichungsart, Jahr und Titelanzahl. Chips filtern nach Veröffentlichungsart. |
| **Titel** | Cover und Titel des ausgewählten Albums, sein Künstler, Jahr, Titelanzahl und Länge. Ein Infobereich listet Veröffentlichungsdatum, Label, Genres, Credits und UPC auf. Darunter stehen die Titel des Albums: Jeder wird bis zum Herunterladen vollständig gestreamt und danach aus deiner Bibliothek abgespielt; mit der Schaltfläche **Album herunterladen** reihst du alle ein. |

Ein Klick auf einen beliebten Titel wählt sein Album aus und hebt den Titel hervor; beide Spalten scrollen sanft ins Bild (sofort, wenn das System auf reduzierte Bewegung gestellt ist), und sobald die Titel des Albums zu sehen sind, startet der Titel vollständig — gestreamt oder, falls schon in deiner Bibliothek, der Song selbst. Ein erneuter Klick während der Wiedergabe pausiert ihn nicht; wird die Seite über einen Link geöffnet, der auf einen Titel zeigt, startet nichts. Ein Klick auf einen verwandten Künstler öffnet diesen Künstler, und die Zurück-Schaltfläche des Browsers führt zum vorherigen. Die Pfadleiste über den Spalten (**Entdecken › Künstler › Album**) führt zurück zur Suche (oder zu Entdecken, wenn die Spalten nicht von dort geöffnet wurden) oder nur zum Künstler. Was geöffnet ist, steht in der URL, übersteht also ein Neuladen und lässt sich als Lesezeichen speichern.

Auf einem breiten Bildschirm ziehst du die Kante zwischen zwei Spalten, um eine breiter oder schmaler zu machen, oder du fokussierst sie und nutzt die Pfeiltasten. Ein Doppelklick stellt die Standardbreiten wieder her. Die Pfeil-Schaltfläche oben in den Spalten Künstler und Diskografie klappt die Spalte auf ihre Bilder zusammen: das Foto des Künstlers, die Cover seiner beliebten Titel und die Fotos der verwandten Künstler bzw. die Albumcover. Jedes Bild funktioniert weiterhin wie seine volle Zeile, und sein Name erscheint beim Darüberfahren. Breiten und eingeklappte Spalten gelten nur, solange du auf der Seite bist: Sie werden nie gespeichert, ein Neuladen oder das Verlassen des Finders setzt sie zurück.

Am Handy liegen die Spalten nebeneinander, und du wischst zwischen ihnen. Ein Album auszuwählen schiebt dich zu seinen Titeln.

::: info Warum die Titelanzahl einen Moment später erscheint
Die Diskografieliste von Deezer enthält keine Titelanzahl, daher fragt Downtify sie für jedes Album einzeln ab, ein paar Alben auf einmal, und bleibt dabei unter dem Limit von Deezer von 50 Anfragen alle 5 Sekunden. Die Zahlen erscheinen, während du schaust, und werden bis zum Neustart von Downtify gemerkt. Ein Album, dessen Anzahl nicht abgerufen werden konnte, zeigt `…`.
:::

## API

Siehe [`GET /api/finder/search`](../api-reference.md#get-apifindersearch) und die folgenden Endpunkte in der API-Referenz.
