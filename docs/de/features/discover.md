---
icon: lucide/compass
---

# Entdecken

Künstler, die du noch nicht hast, vorgeschlagen anhand der Künstler, die du hast. Öffne **Entdecken** in der Seitenleiste (am Handy: **Mehr → Entdecken**). Das Suchfeld oben ist der [Finder](finder.md), eine reine Deezer-Suche: Eine Suche zeigt ihre Ergebnisse anstelle der Vorschläge, und das Leeren des Felds bringt sie zurück.

Weder ein Konto noch ein API-Schlüssel ist nötig: Die Vorschläge stammen aus der öffentlichen Liste „ähnlicher Künstler“ von [Deezer](https://www.deezer.com/), die ohne Anmeldung funktioniert.

## Wie die Vorschläge ausgewählt werden

1. **Deine Künstler werden gewichtet.** Jeder Künstler in deiner Bibliothek zählt etwas, und zählt für jeden dieser Punkte mehr, vom wichtigsten zum unwichtigsten:
    - wie oft du ihn im Player von Downtify **hörst** (Gehörtes aus jüngster Zeit zählt mehr als Monate altes),
    - wie viele seiner Songs du **mit „Gefällt mir“ markiert** hast,
    - wie viele seiner Songs **in deiner Bibliothek** sind.

    Das Gewicht flacht ab, je größer es wird, sodass ein Künstler mit 400 Songs Diskografie nicht einen übertönt, den du jeden Tag spielst.
2. **Die obersten 15 werden bei Deezer nachgeschlagen**, das für jeden die Künstler zurückgibt, die seine Hörer ebenfalls mögen.
3. **Jeder vorgeschlagene Künstler erhält Punkte** von jedem deiner Künstler, der ihn vorschlägt — mehr von einem gewichtigeren Künstler, und mehr, je höher er in Deezers Liste steht. Ein Künstler, auf den mehrere deiner Favoriten verweisen, rangiert über einem, den nur einer von ihnen nennt. Unter jedem Vorschlag nennt *Weil du … magst* die Künstler, von denen er stammt.

Künstler, die schon in deiner Bibliothek sind, und Künstler, die du [ausgeblendet](#hiding-artists) hast, werden nie vorgeschlagen.

Klicke auf das Foto eines Vorschlags, um den Künstler in den Spalten des [Finders](finder.md) zu öffnen — Profil, gesamte Diskografie und die Titel jedes Albums, alles von Deezer. Das **⋯**-Menü eines Vorschlags bietet außerdem **Titel finden** (die Titel des Künstlers, als [Finder](finder.md)-Suche angezeigt), **Auf Deezer öffnen** und **Kein Interesse**. Die Seite zeigt die besten 12 Künstler; **Alle anzeigen** listet jeden Vorschlag (bis zu 48).

## Alben und Playlists

Unter den Künstlern, auf ihnen aufgebaut:

| Bereich | Was drin ist |
|---------|--------------|
| **Alben für dich** | Das bekannteste Album jedes der 12 besten vorgeschlagenen Künstler |
| **Mehr von deinen Künstlern** | Bis zu zwei beliebte Alben von jedem deiner 6 gewichtigsten Künstler, die noch nicht in deiner Bibliothek sind |
| **Playlists für dich** | Das Wesentliche jedes vorgeschlagenen Künstlers: Deezers eigene **`100% <Künstler>`**-Playlist (von Deezers Redakteuren zusammengestellt), dann Spotifys eigene **`This Is <Künstler>`** |

Sie kommen in zwei Schritten:

1. **Zuerst Deezer.** Die Diskografie jedes Künstlers wird bei Deezer gelesen: Ein vollständiges Album kommt vor einer Single oder EP und unter diesen das mit den meisten Fans. Diese Antwort ist schnell und füllt die Regale.
2. **Dann Spotify.** Ein paar Sekunden später werden Spotifys eigene Empfehlungen für dieselben Künstler (aus dessen Suche) **am Ende** jedes Regals ergänzt — Platzhalter zeigen, wo sie während des Ladens erscheinen, und nichts, was schon auf der Seite steht, verschiebt sich. Ein Album, das beide Dienste empfehlen, erscheint nur einmal. Jedes Spotify-Album wird bei Deezer nach Künstler und Titel gesucht; hat Deezer es, öffnet es sich wie die übrigen im Finder.

Ein kleines Symbol in der unteren linken Ecke jedes Album- und Playlist-Covers zeigt, von welchem Dienst es stammt:

- **Deezer** — ein Album öffnet sich in den Spalten des [Finders](finder.md), mit seinen Titeln bereit zum vollständigen Abspielen und Herunterladen.
- **Spotify** — Deezer hat dieses Album nicht, daher öffnet es dieselbe Seite wie ein eingefügter Spotify-Link.

Playlists — die von Deezer wie die von Spotify — öffnen immer diese Seite, auf der du **ihre Songs vollständig anhören** kannst, bevor du welche herunterlädst (siehe [Songs vor dem Herunterladen anhören](top-songs.md#playing-songs-before-downloading)), und dann alles, nur die neuen Songs oder eine Auswahl herunterlädst.

Alles wird wie die ähnlichen Künstler eine Woche aufbewahrt, die Zuordnung eines Spotify-Albums bei Deezer einen Monat (eine Woche, wenn Deezer es nicht hatte, falls es hinzugefügt wird). Ein Album, das schon in deiner Bibliothek ist (verglichen nach Künstler und Titel, `Dummy (Deluxe Edition)` zählt also als `Dummy`), und eine bereits heruntergeladene Playlist bleiben außen vor; das Ausblenden eines Künstlers nimmt auch dessen Alben und Playlists heraus.

## Was als Hören zählt

Ein Song zählt einmal pro Wiedergabe, nachdem **die Hälfte** davon (oder **vier Minuten** bei langen Songs) tatsächlich gespielt wurde — zur Mitte zu springen zählt nicht, und Songs unter 30 Sekunden zählen nie. Podcast-Episoden zählen nicht.

Gehörtes wird auf dem Server gespeichert, also formt, was du am Handy abspielst, auch die Vorschläge auf deinem Desktop. Um neu anzufangen, öffne **Ausgeblendete Künstler → Hörverlauf löschen**; deine Bibliothek und markierten Songs bleiben, wie sie sind.

## Künstler ausblenden

**⋯ → Kein Interesse** bei einem Vorschlag blendet diesen Künstler dauerhaft aus Entdecken aus (die erscheinende Meldung hat ein **Rückgängig**). Um einen Künstler auszublenden, bevor er je vorgeschlagen wird — einen, von dem du einfach nichts hören willst — öffne **Ausgeblendete Künstler** und tippe den Namen ein.

Dieselbe Liste zeigt jeden ausgeblendeten Künstler, mit **Wieder anzeigen**, um einen zurückzuholen. Namen werden ohne Beachtung von Groß-/Kleinschreibung und ohne die Zeichen verglichen, die ein Dateiname nicht enthalten kann, daher blendet `AC/DC` auch `ACDC` aus.

## Gut zu wissen

- **Vorschläge werden eine Woche zwischengespeichert.** Die Antworten von Deezer und Spotify für jeden deiner Künstler werden 7 Tage aufbewahrt, sodass erneutes Öffnen von Entdecken sofort geht und keine Anfragerunde kostet. **Aktualisieren** ordnet mit deiner neuesten Bibliothek, deinen Likes und deinem Hörverlauf neu; ein Künstler, dessen Woche vorbei ist, wird erneut nachgeschlagen.
- **Ist Deezer nicht erreichbar** (oder begrenzt die Anfragen) für einige deiner Künstler, zeigt die Seite trotzdem, was sie aufbauen konnte, und sagt, dass die Liste kürzer als üblich ist — versuche es später erneut. Eine fehlgeschlagene Abfrage wird nie als „keine ähnlichen Künstler“ gemerkt.
- **Ein Künstler, den Deezer nicht kennt**, trägt einfach nichts bei; er wird nicht erneut gesucht, bis seine Woche um ist.
- Nur die *Namen* von Künstlern und Alben verlassen deinen Server (als Deezer- und Spotify-Suchen). Nichts darüber, was du abspielst, wird irgendwohin gesendet.

## API

Siehe [Entdecken](../api-reference.md#discover) in der API-Referenz.
