---
icon: lucide/headphones
---

# Eingebauter Player

Downtify bringt einen Web-Player mit, damit du deine heruntergeladene Musik ohne separate App hören kannst. Drücke Play bei einem beliebigen Titel, Album, Künstler oder einer Playlist in der Bibliothek — oder bei einem fertigen Download in der Warteschlange — und der Player startet.

## Player-Leiste

Solange ein Titel geladen ist, schwebt unten auf jeder Seite eine Player-Leiste: Cover, Titel und Künstler, Zufall, Zurück, Play/Pause, Weiter, Wiederholen, verstrichene/Gesamtzeit und Verknüpfungen zu den Panels für Songtext und Als Nächstes (das für den Songtext lässt sich [ausblenden](#hiding-the-lyrics)). Auf breiten Bildschirmen hat sie außerdem einen Lautstärkeregler und an ihrer Oberkante eine Suchleiste; am Handy schrumpft sie auf das Wesentliche und zeigt eine dünne Fortschrittslinie.

Neben dem Titel ist ein Herz, um den [Song zu liken](liked-songs.md); das Handy lässt es in der Leiste weg, um Platz für den Titel zu lassen, und hat es stattdessen in **Wiedergabe** und in den Titellisten.

Klicke auf Titel oder Cover oder auf die Schaltfläche zum Vergrößern, um **Wiedergabe** zu öffnen.

## Wiedergabe

Eine Vollbildansicht, getönt mit Farben aus dem Cover des aktuellen Albums:

- **Großes Cover**, Titel und Künstler (klicke auf den Künstler oder das Label *Wiedergabe von*, um zu diesem Künstler, Album oder dieser Playlist zu springen), mit einem Herz neben dem Titel, um den [Song zu liken](liked-songs.md). Cover und Songtext schrumpfen mit dem Fenster — auch wenn du nur dessen Höhe änderst —, damit sie unter der Kopfzeile bleiben.
- **Suchleiste** — klicke oder ziehe, oder nutze die Pfeiltasten, wenn sie den Fokus hat. Während ein Titel spielt, treiben sanfte Wellen in Farben aus dem Albumcover über den gespielten Teil; sie legen sich bei Pause flach und stehen still, wenn dein System reduzierte Bewegung wünscht
- **Wiedergabesteuerung** — Zufall, Zurück, Play/Pause, Weiter, Wiederholen (aus → alle wiederholen → einen wiederholen)
- **Lautstärke** mit Stummschaltung, zwischen Sitzungen gespeichert. Am Handy ausgeblendet, wo die Hardware-Tasten die Lautstärke steuern
- **Sleeptimer** — beendet die Wiedergabe nach 15, 30, 45, 60 oder 90 Minuten oder am Ende des aktuellen Titels. Die verbleibende Zeit steht neben der Timer-Schaltfläche
- **Dateiinfo** — Format und Größe der gerade gespielten Datei

Vier Panels sitzen auf breiten Bildschirmen neben dem Cover oder ersetzen es am Handy:

- **Songtexte** — zeitsynchronisierte Songtexte heben die aktuelle Zeile hervor und scrollen mit dem Song; klicke auf eine Zeile, um dorthin zu springen. Einfache Songtexte werden unverändert gezeigt. Songtexte stammen aus der `.lrc`-Datei neben dem Titel oder aus den in seinen Tags eingebetteten — siehe [Songtexte](lyrics.md). Du kannst dieses Panel ausblenden — siehe [Songtexte ausblenden](#hiding-the-lyrics).
- **Als Nächstes** — die Wiedergabewarteschlange. Ziehe Titel, um sie neu zu ordnen, entferne einzelne Titel oder leere alles nach dem aktuellen.
- **Details** — Titel, Künstler, Album, Titelnummer, Jahr, Länge, Format, Größe, Hinzufügedatum und Dateipfad.
- **Equalizer** — forme den Klang mit zehn Frequenzbändern; siehe [Equalizer](#equalizer).

Wiedergabe ist Teil der Seitenadresse (`?np=1`, plus `&panel=lyrics|queue|details|equalizer`), sodass die Zurück-Schaltfläche des Browsers sie schließt und ein Neuladen sie offen hält.

## Songtexte ausblenden

Lieber das Artwork und die Warteschlange ohne die Worte? Schalte **Einstellungen → Allgemein → Player → Songtexte im Player anzeigen** aus. Es gilt sofort und nimmt alles weg, was im Player zu Songtexten führt:

- das Panel **Songtexte** und seinen Tab (am Handy seine Schaltfläche in der Fußzeile von Wiedergabe);
- die Songtext-Schaltfläche in der Player-Leiste;
- das Kürzel `L`, das auch aus der Kürzelliste (`?`) verschwindet.

Wiedergabe öffnet dann stattdessen auf **Als Nächstes**. Ein Link auf `&panel=lyrics` aus der Zeit vor dem Ausschalten landet ebenfalls dort, statt auf einem leeren Tab. Der Player fragt die Songtexte eines Titels gar nicht erst ab, solange sie ausgeblendet sind.

::: info Ausblenden ist nicht Löschen
Das ändert nur, was der Player zeigt. Deine Dateien behalten die Songtexte, die Downtify darin eingebettet hat, und die `.lrc`-Dateien daneben bleiben an Ort und Stelle, sodass Medienserver und andere Player sie weiterhin sehen. Downloads holen ebenfalls weiter Songtexte — das ist die separate Einstellung **Songtexte herunterladen** unter **Tags und Songtexte** (siehe [Songtexte](lyrics.md)).
:::

Wie das Thema und der Equalizer wird die Wahl im Browser gespeichert (`localStorage`), gilt also pro Gerät und pro Browser, nicht pro Downtify-Server — du kannst die Songtexte am Handy ausblenden und am Desktop behalten.

## Equalizer

Ein grafischer Zehnband-Equalizer im Panel **Equalizer** von Wiedergabe (oder drücke `E`). Er ist als **Experimentell** gekennzeichnet: Er kann sich noch ändern und in manchen Browsern Probleme machen (siehe [Browser-Unterstützung](#browser-support)).

- **Bänder** bei 31, 62, 125, 250, 500 Hz und 1, 2, 4, 8, 16 kHz, jedes ±12 dB in 0,5-dB-Schritten. Die Bänder bei 31 Hz und 16 kHz sind Shelves, heben oder senken also auch alles darunter / darüber. Ziehe ein Band, oder gib ihm den Fokus und nutze die Pfeiltasten (`Page Up`/`Page Down` für 1 dB, `Home`/`End` für die Grenzen); ein Doppelklick setzt es auf 0 zurück.
- **Voreinstellungen** — Neutral, Bassverstärkung, Höhenverstärkung, Gesang, Rock, Elektronisch und Akustisch. Wird danach ein Band bewegt, wird die Voreinstellung zu **Benutzerdefiniert**.
- **Vorverstärkung** — ±12 dB obendrauf.
- **Ein-/Ausschalter** und **Zurücksetzen** (zurück auf Neutral, Vorverstärkung 0, aus). Ein Band zu bewegen oder eine Voreinstellung zu wählen schaltet den Equalizer ebenfalls ein.
- Die Kurve hinter den Reglern ist die kombinierte Antwort aller Bänder.

Angehobene Bänder würden laute Musik über Vollaussteuerung hinausdrücken und verzerren, daher senkt Downtify die Lautstärke automatisch um die höchste Anhebung der Kurve — das Panel nennt den Betrag. Das hält die Spitze bei 0 dB, sodass eine angehobene Voreinstellung den Klang umformt, statt ihn nur lauter zu machen. Eine Vorverstärkung über 0 dB nimmt diese Sicherheitsreserve weg, und das Panel warnt, dass laute Passagen verzerren können.

Die Einstellungen werden im Browser gespeichert (`localStorage`) und gelten für alles, was du spielst, in jedem Tab, bis du sie änderst. Sie gelten pro Browser, nicht pro Downtify-Server.

### Browser-Unterstützung

Der Equalizer nutzt die Web Audio API, in allen aktuellen Browsern verfügbar. Bis du ihn einschaltest, berührt die Wiedergabe Web Audio gar nicht. Ist er an, läuft das Audio für den Rest des Besuchs durch ihn — Ausschalten flacht nur alle Bänder ab.

::: warning Safari auf iPhone und iPad
iOS kann Web Audio pausieren, wenn der Bildschirm sperrt oder du die App wechselst, was die Wiedergabe bei eingeschaltetem Equalizer stoppt. Hörst du mit ausgeschaltetem Bildschirm, schalte den Equalizer aus und lade die Seite neu.
:::

## Die Warteschlange aufbauen

Das Abspielen eines Albums, Künstlers, einer Playlist oder der Titelliste reiht diese Titel der Reihe nach ein, beginnend mit dem gewählten. **Zufall** bei einer Sammlung startet sie in zufälliger Reihenfolge. Titel, die du nicht heruntergeladen hast, spielen direkt in der Warteschlange vollständig, ausgeliefert aus dem Stream-Cache des Servers: Während einer spielt, wird der nächste schon einen Titel im Voraus vorbereitet, sodass die Wiedergabe durch nicht heruntergeladene Zeilen ohne Halt läuft — auch dort, wo der Browser selbst YouTube nicht erreicht. Ein gestreamter Titel wird nie gespeichert, geliked oder über Neuladen hinaus gemerkt.

Das Menü jedes Titels (die Schaltfläche **⋯**, oder Rechtsklick am Desktop) hat:

- **Als nächstes abspielen** — direkt nach dem aktuellen Titel einfügen
- **Zur Warteschlange hinzufügen** — ans Ende anhängen
- **Zum Album** / **Zum Künstler**
- **Auf diesem Gerät speichern** — die Datei über den Browser herunterladen
- **Aus Bibliothek löschen**

Dieselben Aktionen gelten für eine Mehrfachauswahl in der Bibliothek.

Warteschlange, aktueller Titel, seine Position, Zufall und Wiederholen werden gemerkt, sodass das erneute Öffnen von Downtify dort fortsetzt, wo du aufgehört hast (Warteschlangen mit mehr als 2000 Titeln werden nicht gemerkt). Gelöschte Dateien fallen automatisch aus der Warteschlange.

## Tastatur und Medientasten

| Taste | Aktion |
|-----|--------|
| `Space` | Play / Pause |
| `←` / `→` | 5 Sekunden vor/zurück |
| `Shift` + `←` / `→` | Vorheriger / nächster Titel |
| `↑` / `↓` | Lautstärke |
| `M` | Stumm |
| `S` | Zufall |
| `R` | Wiederholen |
| `L` | Songtexte öffnen (außer [ausgeblendet](#hiding-the-lyrics)) |
| `Q` | Als Nächstes öffnen |
| `E` | Equalizer öffnen |
| `Ctrl` / `⌘` + `K` oder `/` | Suche |
| `Ctrl` / `⌘` + `F` | In der Playlist suchen (auf der Seite einer Playlist) |
| `G` dann `L` / `D` | Zur Bibliothek / Warteschlange |
| `Esc` | Wiedergabe schließen |
| `?` | Alle Kürzel anzeigen |

Kürzel werden ignoriert, während du in ein Feld tippst oder ein Dialog offen ist.

Der Player meldet den aktuellen Titel auch dem Betriebssystem (Media Session), sodass Sperrbildschirm-Steuerung, Headset-Tasten und Medientasten der Tastatur funktionieren, mit dem Cover, wo das System es unterstützt.

## So funktioniert es

Titel kommen aus der Bibliotheksliste (`GET /tracks`), die Titel, Künstler, Album, Titelnummer, Jahr und Länge aus den Tags jeder Datei liest. Dateien werden aus dem statischen Mount `/downloads` ausgeliefert; slskd-Downloads, die [an Ort und Stelle gelassen](slskd-navidrome.md#leave-files-in-place) wurden, werden über `/media/slskd/…` abgespielt. Das Cover kommt von `/cover` und die Songtexte von `/lyrics` — siehe die [API-Referenz](../api-reference.md#file-management).

Die Wiedergabe nutzt das native HTML5-Audio des Browsers. Keine Plugins, keine zusätzlichen Prozesse.

## Unterstützte Formate

Der Player kann jedes Format abspielen, das die HTML5-Audio-Engine deines Browsers unterstützt. Das umfasst typischerweise MP3, M4A/AAC, OGG und OPUS in allen modernen Browsern. Die FLAC-Unterstützung variiert — Chrome und Edge unterstützen es nativ; Firefox und Safari womöglich nicht.
