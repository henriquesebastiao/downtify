---
icon: lucide/replace
---

# Audio ersetzen

Downtify wählt das Audio für jeden Song automatisch aus, und manchmal wählt es das falsche: einen anderen Song mit demselben Namen, einen Live-Mitschnitt, einen Remix oder einen Upload mit langem Intro. Mit **Audio ersetzen** wählst du die richtige Version von Hand aus. Der Titel behält überall seinen Platz — in seinen Playlists, M3U-Dateien, Likes und gekoppelten Apps — und nur das Audio ändert sich.

Nur Admins können Audio ersetzen (siehe [Benutzer und Anmeldung](users.md#admins-and-users)).

## Das Audio eines Titels ersetzen

1. Öffne in der **Bibliothek** das Menü des Titels (Rechtsklick oder die Schaltfläche **⋯**) und wähle **Audio ersetzen …**.
2. Downtify sucht auf **YouTube Music** und **YouTube** nach „Künstler - Titel“ und listet auf, was es findet. Ändere die Suche oder füge einen YouTube- oder YouTube-Music-Link zu einem Video oder Song ein, um genau den gewünschten Upload zu bekommen.
3. Wähle eine Version. Jede zeigt, woher sie stammt und wie lang sie ist, neben der Länge deiner Datei. Eine Version, die höchstens 3 Sekunden von der Länge deiner Datei abweicht, wird hervorgehoben. Die Schaltfläche ↗ öffnet sie auf YouTube, damit du vor der Auswahl reinhören kannst.
4. Drücke **Audio ersetzen**. Das Ersetzen läuft wie ein Download: Es zeigt seinen Fortschritt im Dialog und in der **Warteschlange**, und der Dialog meldet, wann es fertig ist.

Schlägt es fehl (das Video ist nicht verfügbar oder YouTube verlangt eine Anmeldung — siehe [YouTube-Cookies](youtube-cookies.md)), bleibt deine Datei genau so, wie sie war. **Erneut versuchen** in der Warteschlange probiert dasselbe Video noch einmal, und das Einfügen eines anderen Links dort ersetzt stattdessen mit diesem.

## Was gleich bleibt

- **Die Datei.** Das neue Audio wird im selben Pfad und im selben Format geschrieben: Eine `.mp3` bleibt MP3 (mit der in den [Download-Einstellungen](download-settings.md) gewählten Bitrate), eine `.flac` bleibt FLAC und so weiter. So zeigen alle Playlists, M3U-Dateien, gelikten Songs, Navidrome-Einträge und gekoppelten Apps, die auf die Datei verweisen, weiterhin auf sie.
- **Die Tags.** Titel, Künstler, Album, Titelnummer, Jahr, Cover, eingebettete Songtexte und alle anderen Tags werden unverändert von der alten Datei auf das neue Audio kopiert. Die `.lrc`-Begleitdatei bleibt unberührt. Synchrone Songtexte waren auf das alte Audio getaktet: Beginnt die neue Version an anderer Stelle, können sie verschoben sein.
- **Das Datum.** Die Datei behält ihr Änderungsdatum und springt deshalb nicht an die Spitze von „Kürzlich hinzugefügt“.

Ersetzt werden können nur `.mp3`-, `.flac`-, `.m4a`-, `.ogg`- und `.opus`-Dateien — die Formate, die Downtify schreibt.

## So funktioniert es

Das gewählte Video wird unter einem temporären Namen, den die Bibliothek ignoriert (`<Name>.downtify-upgrade.<ext>`), neben die Datei heruntergeladen, in das Format der Datei umgewandelt, auf lesbares Audio geprüft, mit den Tags der alten Datei versehen und erst dann über die alte Datei verschoben. Die API steht in der [API-Referenz](../api-reference.md#get-apilibraryreplacecandidates).
