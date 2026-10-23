---
icon: lucide/mic
---

# Podcasts

Abonniere eine Sendung, und ihre neuen Folgen werden von selbst heruntergeladen — ohne jede Woche einen Link neu einzufügen. Podcasts werden von Anfang bis Ende anders behandelt als Musik: Eine Folge ist bereits eine fertige Audiodatei unter einer RSS-`<enclosure>`-URL, es gibt also kein YouTube-Matching und keine Transkodierung, nur einen Download und das Schreiben der Tags.

Öffne **Podcasts** in der Seitenleiste (am Handy: **Mehr → Podcasts**).

Abonnements gehören dem, der abonniert: Jedes Konto folgt seinen eigenen Sendungen (derselbe Feed zweimal abonniert landet in zwei Ordnern), mit eigenen Folgen, Fortsetzungspositionen und Ausblendungen. Ein Admin sieht jedes Abonnement.

## Abonnieren

Füge eines davon in das Feld **Podcast hinzufügen** ein oder tippe einen Namen zum Suchen:

| Eingabe | Was passiert |
|-------|--------------|
| Die RSS-Feed-URL eines Podcasts | Wird direkt abgerufen und ausgewertet |
| Ein Spotify-Sendungslink (`open.spotify.com/show/…`) | Der Name der Sendung wird von Spotify gelesen und dann über das iTunes-Podcast-Verzeichnis ihrem öffentlichen RSS-Feed zugeordnet |
| Ein Spotify-Folgenlink (`open.spotify.com/episode/…`) | Wie ein Sendungslink, und die konkrete Folge wird hervorgehoben, wenn ihr Titel im Feed gefunden werden kann |
| Der Name einer Sendung (Freitext) | Wird im iTunes-Podcast-Verzeichnis gesucht |

::: info Exklusiv bei Spotify laufende Sendungen können nicht heruntergeladen werden
Eine Sendung, die nur auf Spotify existiert (ohne öffentlichen Feed), wird als solche gemeldet — Downtify rät nicht und weicht nicht auf etwas anderes aus. Suche die Sendung nach Namen, um das zu prüfen, bevor du von Exklusivität ausgehst.
:::

Vor dem Bestätigen wählst du:

- **Behalten** — siehe [Wie viele Folgen heruntergeladen werden](#how-many-episodes-are-downloaded) weiter unten.
- **Intervall** — wie oft der Feed auf neue Folgen geprüft wird, von alle 15 Minuten bis einmal im Monat. Abonnements werden nach demselben Zeitplan und vom selben Hintergrunddurchlauf geprüft wie die Beobachtungen der [Playlist-Überwachung](playlist-monitor.md) — für sie sind sie nur eine weitere Art von Beobachtung.

## Wie viele Folgen heruntergeladen werden

Die Einstellung **Behalten** hat zwei verschiedene Verhaltensweisen, einmal pro Sendung gewählt:

- **Jede neue Folge** — lädt sofort nur die einzelne neueste Folge herunter (Abonnieren ist keine Einladung, den gesamten Back-Katalog einer Sendung zu ziehen) und danach bei jeder Prüfung alle neu erscheinenden Folgen. Nichts wird je automatisch gelöscht.
- **Die letzten *N* Folgen** — ein gleitendes Fenster. Nach jeder Prüfung (auch der ersten) werden die *N* zuletzt veröffentlichten Folgen heruntergeladen, und jede ältere heruntergeladene Folge wird entfernt, um Platz zu schaffen. Wird *N* später erhöht, lassen sich diese entfernten Folgen wieder herunterladen; eine Folge, die du selbst mit **Download entfernen** entfernt hast, kommt auf diesem Weg nie zurück — siehe [Folgen entfernen](#removing-episodes).

Ändere **Behalten** und das Intervall jederzeit auf der Seite der Sendung.

## Folgen

Die Seite einer Sendung listet ihre Folgen auf, die neueste zuerst, jede mit Veröffentlichungsdatum und Dauer. Eine Folge, die von der Aufbewahrungsregel nicht erfasst ist, erscheint hier trotzdem — tippe auf **Herunterladen**, um nur diese eine zu holen, egal wie alt.

### Folgen entfernen

Das **⋯**-Menü jeder Folge hat **Download entfernen**, das die Datei löscht, die Folge aber in der Liste behält. Es gibt zwei Wege, wie die Datei einer Folge verschwindet, mit unterschiedlichem Ergebnis:

| Wie | Kommt automatisch zurück? |
|-----|----|
| Die Aufbewahrung hat sie herausgerollt (eine ältere Folge außerhalb des Fensters „letzte N behalten“) | Ja, wenn du **Behalten** wieder erhöhst |
| Du hast selbst **Download entfernen** gewählt | Nein — lade sie jederzeit von Hand erneut herunter |

### Als gehört markieren

Nutze das **⋯**-Menü einer Folge, um sie von Hand als gehört oder ungehört zu markieren, oder lass sie einfach durchlaufen — eine Folge in den letzten Sekunden ihrer Länge wird von selbst als gehört markiert.

## Folgen abspielen

Folgen laufen im selben eingebauten Player wie Musik, mit ein paar Unterschieden, die nur bei einer Podcast-Folge auftauchen:

- **15 s zurück / 30 s vor** anstelle von Zufall und Wiederholen, die für eine einzelne Folge nicht gelten.
- **Wiedergabegeschwindigkeit** (0,75× bis 2×), neben dem Sleep-Timer.
- Die **Fortsetzungsposition** wird alle ~10 Sekunden Wiedergabe und noch einmal beim Pausieren auf dem Server gespeichert, sodass das Schließen des Tabs — oder das Öffnen von Downtify auf einem anderen Gerät — die Folge nahe der Stelle fortsetzt, an der du aufgehört hast. Die Folgenliste einer Sendung zeigt bei allem Angefangenen einen Hinweis „Fortsetzen bei …“.

Das Herz (markierte Songs) und „zum Album/Künstler gehen“ gelten nicht für Folgen und erscheinen bei einer nicht.

## Bibliothek

Podcasts haben ihren eigenen Platz — sie erscheinen nie als Titel, Alben oder Künstler in der **Bibliothek**, und ein Lauf von [Bibliothek verbessern](library-upgrade.md) lässt sie völlig in Ruhe (eine Folge hat keine Spotify-Titel-ID, von der sich Tags auffrischen ließen, und keine gesonderten Songtexte, die man suchen könnte).

Die Folgendateien liegen weiterhin im selben Download-Volume, unter `Podcasts/<Sendung>/<Datum> - <Folge>.<Endung>`, sodass jeder auf deine Bibliothek zeigende Medienserver sie ebenfalls sieht.

## Tags

Downtify schreibt, was Podcast-Apps und Medienserver bei einer Folge ohnehin lesen: Titel, die Sendung als Album, den Autor der Sendung als Künstler, das Veröffentlichungsjahr, Folgen-/Staffelnummern, das eigene Artwork der Sendung (das größere aus dem Bild des Feeds und dem von iTunes, dieselbe Idee wie beim [Cover für Musik](download-settings.md#cover-art-resolution)) und die Folgenbeschreibung als Kommentar. Show Notes werden als reiner Text gespeichert — Downtify entfernt das HTML daraus, statt es darzustellen.

## Gut zu wissen

- **Keine Video-Podcasts.** Eine Folge, deren einziger Anhang eine Videodatei ist, wird komplett übersprungen; nur Audio wird unterstützt.
- **Keine Kapitel.** Feeds mit Kapitelmarken bekommen diese in Downtify noch nicht.
- **Nicht in Navidrome gespiegelt.** Anders als Playlists werden Podcast-Abonnements nicht in eine Navidrome-Bibliothek geschoben — Folgen sind einfache Dateien, die dein Medienserver ohnehin selbst sieht.
- Das Beenden eines Abonnements (**⋯ → Abo beenden**) entfernt standardmäßig heruntergeladene Folgen; wähle **Abo beenden, Folgen behalten**, um die Dateien an Ort und Stelle zu lassen.

## API

`POST /api/podcasts/resolve`, `GET /api/podcasts/search`, `POST /api/podcasts/subscribe`, `GET/PATCH/DELETE /api/podcasts/shows/{id}`, `GET /api/podcasts/shows/{id}/episodes`, `POST /api/podcasts/episodes/{id}/download`, `DELETE /api/podcasts/episodes/{id}` und `PUT /api/podcasts/episodes/{id}/playback`. Siehe die [API-Referenz](../api-reference.md#podcasts).
