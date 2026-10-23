---
icon: lucide/eye
---

# Playlist-Überwachung

Die Playlist-Überwachung beobachtet deine liebsten Spotify- und YouTube-Music-Playlists — und die Künstler, denen du folgst — und lädt neue Titel und neue Veröffentlichungen automatisch herunter, sobald sie erscheinen, ganz ohne dein Zutun.

Es gibt zwei Arten von Beobachtung, jede auf einem eigenen Tab der Überwachungsseite (**Playlists** und **Künstler**, unter `/monitor/playlists` und `/monitor/artists`):

| Beobachtung | Einfügen | Lädt herunter |
|-------|-------|-----------|
| **Playlist** | Eine Spotify- oder YouTube-Music-Playlist-URL | Jeden Titel der Playlist, danach jeden später hinzugefügten |
| **Künstler** | Die URL eines Spotify-**Künstlers** oder eines YouTube-Music-Künstlers | Die ganze Diskografie des Künstlers, danach jede neue Veröffentlichung |

Jede Beobachtung zeigt unter ihrem Namen den Link, dem sie folgt, und ein Abzeichen **Spotify** oder **YouTube Music**, das den Dienst nennt, von dem sie hinzugefügt wurde.

Siehe [Künstlerbeobachtung](#artist-watch), wie Künstlerbeobachtungen funktionieren.

Beobachtungen gehören dem, der sie angelegt hat: Jedes Konto folgt seinen eigenen Playlists und Künstlern (dieselbe URL zweimal beobachtet wird zweimal durchlaufen), und ein Durchlauf ordnet seine Downloads dem Besitzer der Beobachtung zu. Ein Admin sieht alle Beobachtungen.

## So funktioniert es

Downtify lässt eine Hintergrundaufgabe laufen, die alle 60 Sekunden ausgeführt wird. Bei jedem Durchlauf prüft sie bei jeder aktivierten Beobachtung, ob sie (gemäß ihrem eingestellten Intervall) zur Prüfung ansteht. Steht eine *Playlist* an, tut Downtify Folgendes:

1. Ruft die vollständige Titelliste von Spotify oder YouTube Music ab
2. Vergleicht sie mit der Menge der bereits heruntergeladenen Titel
3. Lädt neue Titel mit derselben Pipeline wie ein manueller Download herunter
4. Aktualisiert die M3U-Datei der Playlist (wenn die M3U-Erzeugung aktiviert ist)

Die erste Prüfung, die startet, sobald du die Beobachtung hinzufügst, lädt alles herunter, was schon in der Playlist ist; spätere Prüfungen laden nur herunter, was seitdem hinzukam. „Schon heruntergeladen“ wird in einer kleinen SQLite-Datenbank (`downtify_monitor.db` unter `/data`) festgehalten, nicht durch Prüfen des Download-Ordners — das Verschieben einer heruntergeladenen Datei an eine andere Stelle auf der Festplatte (in deine eigene Bibliotheksstruktur, auf ein anderes Laufwerk, wohin auch immer) lässt Downtify also **nicht** glauben, sie fehle, und lädt sie bei der nächsten Prüfung nicht erneut herunter.

Ein separater Durchlauf läuft jede Stunde und prüft, ob die Datei jedes heruntergeladenen Titels noch da ist. Wirklich gelöschte Dateien (im Gegensatz zu verschobenen) werden dann vergessen, sodass der Titel wieder zum Download infrage kommt — bei der nächsten Prüfung der Beobachtung nach diesem stündlichen Durchlauf, nicht sofort.

Eine Beobachtung wird nie zweimal gleichzeitig geprüft. Beim Hinzufügen startet ihre erste Prüfung sofort; lädt diese noch herunter, wenn der nächste geplante Durchlauf kommt, überspringt der Durchlauf die Beobachtung, statt einen zweiten, überlappenden Download derselben Titel zu starten.

## Eine Playlist hinzufügen

1. Öffne **Überwachung** in der Seitenleiste (am Handy: **Mehr → Überwachung**) und bleibe auf dem Tab **Playlists**
2. Füge eine Playlist-URL ein:
    - Spotify: `https://open.spotify.com/playlist/…`
    - YouTube Music: `https://music.youtube.com/playlist?list=…` (ein Link `www.youtube.com/playlist?list=…` funktioniert auch)
3. Wähle ein Prüfintervall (von 15 Minuten bis einmal im Monat)
4. Klicke auf **Playlist überwachen**

Jeder Tab hat sein eigenes Feld. Einen Künstlerlink in den Tab Playlists (oder einen Playlist-Link in Künstler) einzufügen, fügt nichts hinzu: Die Seite sagt, was für ein Link es ist, und bietet an, ihn in den richtigen Tab zu verschieben.

Du kannst auch von der Seite einer Playlist aus mit dem Beobachten beginnen: Füge ihren Link in die Suchleiste ein und nutze **Auf neue Titel achten** (oder **Auf neue Veröffentlichungen achten** bei einem YouTube-Music-Künstler). Heruntergeladene Playlists in der Bibliothek bieten dieselbe Aktion in ihrem **⋯**-Menü. So hinzugefügte Beobachtungen nutzen ein 6-Stunden-Intervall — ändere es auf der Überwachungsseite.

## YouTube-Music-Playlists

Nutze eine YouTube-Music-Playlist für Songs, die nicht auf Spotify sind: Remixe, Live-Sets, Coverversionen, Uploads von Promo-Kanälen. Jeder Titel wird von **genau dem Video in der Playlist** heruntergeladen. Downtify sucht nicht erneut danach, du bekommst also, was du in die Playlist gelegt hast.

- **Alle Titel werden abgerufen**, egal wie lang die Playlist ist. Gelöschte oder private Videos werden übersprungen.
- **Songs, die YouTube Music ausgraut, werden trotzdem heruntergeladen.** Playlists von Konvertern und Importern (Soundiiz, TuneMyMusic und Ähnliche) listen Songs oft als einfache YouTube-Uploads, die YouTube Music als nicht verfügbar zeigt und ohne Song-ID führt. Downtify findet das Video anhand des Vorschaubilds des Eintrags und lädt es wie jedes andere herunter, sodass eine solche Playlist nicht leer herauskommt. Ein wirklich gelöschtes oder privat gestelltes Video kann nicht heruntergeladen werden: Kennzeichnet YouTube Music es so, wird es übersprungen, und liefert es nur ein Vorschaubild, erscheint der Titel in der Warteschlange als fehlgeschlagen.
- **Künstler und Titel stammen aus dem Videotitel.** Viele Playlist-Einträge sind Uploads, die dem Kanal zugeschrieben sind, der sie gepostet hat (z. B. `MrSuicideSheep`), und der echte Credit steht im Titel, wie `Bronze Whale - Patterns`. Bei allem, was keine Katalogveröffentlichung ist, teilt Downtify `Künstler - Titel` in Dateinamen und Tags auf. Es entfernt auch Suffixe wie `(Official Video)` oder `[Lyrics]`. Ein Teil nach dem Bindestrich, der eine Version benennt (`Yellow - Live at Glastonbury`), bleibt im Titel. Katalogtitel (offizielles Audio oder alles, was unter einem Album abgelegt ist) behalten Künstler und Titel von YouTube Music.
- **Nicht jeder `list=`-Link ist eine Playlist.** Der `OLAK5uy_…`-Link eines Albums wird weiterhin als Album heruntergeladen. Ein Link `watch?v=…&list=…` ist der eine Song, der gerade lief. Ein Radio-Mix (`list=RD…`) hat keine feste Titelliste und kann nicht beobachtet werden.

## Künstlerbeobachtung

Statt pro Künstler eine Playlist anzulegen, füge einen Künstlerlink ein, und Downtify folgt seinem ganzen Katalog. Füge einen über den Tab **Künstler** der Überwachungsseite hinzu — URL einfügen, Intervall wählen, auf **Künstler überwachen** klicken. Künstlerbeobachtungen zeigen eine Anzahl von Veröffentlichungen statt einer Titelanzahl.

Akzeptierte URLs:

- Eine Spotify-Künstler-URL (`https://open.spotify.com/artist/…`)
- Eine YouTube-Music-Künstler-URL, per Kanal (`https://music.youtube.com/channel/UC…`) oder per Handle (`https://music.youtube.com/@HenriqueeJuliano`)

Ein Handle wird beim Hinzufügen der Beobachtung zum Kanal des Künstlers aufgelöst, sodass derselbe Künstler, per Handle und per Kanal-URL eingefügt, als eine Beobachtung erkannt wird. Ein Handle, das nicht zu einem YouTube-Music-Künstler gehört, wird abgelehnt.

Bei jedem Durchlauf listet Downtify die Diskografie des Künstlers auf, vergleicht sie mit den bereits verarbeiteten Veröffentlichungen und lädt jeden Titel von allem Neuen herunter. Ein Durchlauf im Normalbetrieb kostet eine einzige Anfrage — Titellisten werden nur für Veröffentlichungen abgerufen, die es noch nicht gesehen hat.

::: info Warum die Diskografie von YouTube Music kommt
Spotifys öffentliches Embed zeigt den Namen eines Künstlers und eine Vorschau der Top-Titel, aber **nicht** seine Diskografie — sie zu lesen würde Spotify-API-Zugangsdaten erfordern, die Downtify bewusst nicht nutzt. Ein Spotify-Künstlerlink wird also zu seinem Namen aufgelöst und demselben Künstler auf YouTube Music zugeordnet, von wo auch das Audio geholt wird. Der Vorteil: Jede Veröffentlichung, die Downtify sehen kann, kann es auch tatsächlich herunterladen. Der Kompromiss: Bei einem Künstler mit mehrdeutigem Namen prüfe, dass der aufgelöste Name der Beobachtung der gemeinte Künstler ist — füge die YouTube-Music-Künstler-URL direkt ein, wenn der falsche gewählt wurde.
:::

::: warning Der erste Durchlauf lädt den gesamten Back-Katalog herunter
Das Hinzufügen eines Künstlers reiht **jede** seiner Veröffentlichungen ein, was bei einem produktiven Künstler Hunderte Alben und Singles sein können. Setze die **[Pause zwischen Downloads](download-settings.md#delay-between-downloads)**, bevor du einen Stapel Künstler hinzufügst, sonst wirst du sehr wahrscheinlich gedrosselt — oder schalte **Nur neue Veröffentlichungen** (unten) ein, um den Back-Katalog ganz zu überspringen.
:::

### Auswählen, was heruntergeladen wird

Unter dem Link-Feld im Tab **Künstler** (und im Dialog **Bearbeiten** einer Beobachtung) entscheiden zwei Optionen, was eine Künstlerbeobachtung herunterlädt:

| Option | Was sie tut |
|--------|--------------|
| **Herunterladen: Alben / Singles / EPs** | Nur Veröffentlichungen der angehakten Arten werden heruntergeladen. Alle drei sind standardmäßig an; mindestens eine muss an bleiben. Die Art ist die eigene Bezeichnung von YouTube Music für jede Veröffentlichung — eine, die es nicht kennzeichnet, zählt als Album. |
| **Nur neue Veröffentlichungen** | Alles, was der Künstler beim Start der Beobachtung bereits veröffentlicht hat, wird übersprungen; nur was danach erscheint, wird heruntergeladen. Standardmäßig aus. |

Wie sie sich verhalten, wenn du sie später änderst:

- **Eine Art einschalten** lädt die Veröffentlichungen dieser Art bei der nächsten Prüfung der Beobachtung herunter — auch ihren Back-Katalog, außer **Nur neue Veröffentlichungen** ist an (dann nur die seit dem Start der Beobachtung oder seit dem Einschalten der Option veröffentlichten). Veröffentlichungen einer ausgeschalteten Art werden nie erfasst, also geht nichts verloren, wenn du eine Art für eine Weile ausschaltest.
- **Nur neue Veröffentlichungen einschalten** bei einer bestehenden Beobachtung erfasst alles zu diesem Zeitpunkt Erschienene als übersprungen; bereits heruntergeladene Veröffentlichungen bleiben, wie sie sind.
- **Ausschalten** lädt bei der nächsten Prüfung die übersprungenen Veröffentlichungen (der angehakten Arten) herunter.
- Das Speichern einer der beiden Optionen im Dialog **Bearbeiten** prüft die Beobachtung sofort, statt auf die nächste geplante Prüfung zu warten.

Die vorhandenen Veröffentlichungen zu „überspringen“ erfordert einen erfolgreichen Blick auf die Diskografie des Künstlers: Liefert YouTube Music eine leere Liste (was öfter ein Aussetzer ist als ein Künstler ohne Veröffentlichungen), wird nichts erfasst und die nächste Prüfung versucht es erneut, sodass eine schlechte Antwort nie dazu führen kann, dass der Back-Katalog später heruntergeladen wird. Eine **Nur neue Veröffentlichungen**-Beobachtung auf einen anderen Künstler zu richten überspringt den Back-Katalog dieses Künstlers auf dieselbe Weise.

Die Liste der Überwachung zeigt die Filter einer Beobachtung unter ihrem Link, wenn sie nicht die Standardwerte sind (z. B. **Alben** · **Nur neue**).

Eine Veröffentlichung wird erst als verarbeitet erfasst, wenn jeder ihrer Titel geklärt ist, sodass ein Titel, der an einem vorübergehenden Fehler scheitert, beim nächsten Durchlauf erneut versucht wird, statt für immer übersprungen zu werden. Bereits heruntergeladene Titel werden nie zweimal abgerufen.

Künstlerbeobachtungen erzeugen keine M3U-Dateien — die Titel werden nach deinen Einstellungen zur [Dateiorganisation](file-organization.md) abgelegt, nicht als Playlist.

## Prüfintervalle

| Bezeichnung | Minuten | Am besten für |
|-------|---------|----------|
| Alle 15 Min. | 15 | Häufig aktualisierte Playlists |
| Alle 30 Min. | 30 | |
| Jede Stunde | 60 (Standard) | Die meisten Playlists |
| Alle 3 Stunden | 180 | |
| Alle 6 Stunden | 360 | |
| Alle 12 Stunden | 720 | |
| Jeden Tag | 1 440 | Sich langsam ändernde Playlists |
| Jede Woche | 10 080 | Wöchentlich aktualisierte Playlists |
| Alle 2 Wochen | 20 160 | |
| Jeden Monat | 43 200 | Archiv oder selten aktualisierte Playlists |

Du kannst das Intervall einer bestehenden Playlist jederzeit auf der Überwachungskarte ändern, ohne sie zu entfernen und neu hinzuzufügen.

## Überwachte Playlists verwalten

Jeder Tab listet nur seine eigene Art von Beobachtung. Über der Liste:

- **Filtern** — tippe einen Teil eines Namens oder des Links (z. B. einer Playlist-ID) ein, um die Liste einzugrenzen
- **Alle / Pausiert** — nur pausierte Beobachtungen zeigen
- **Alle jetzt prüfen** — jede aktive Beobachtung des aktuellen Tabs prüfen

In jeder Zeile:

- Schalter **Aktiv** — die Beobachtung pausieren oder fortsetzen, ohne sie zu entfernen
- **Prüfungen** — wie oft sie geprüft wird
- **Jetzt prüfen** (↻) — sie sofort prüfen, außerhalb des Zeitplans
- **Bearbeiten** (✎) — Link, Intervall und Aktivzustand der Beobachtung ansehen und ändern (siehe [Eine Beobachtung bearbeiten](#editing-a-watch))
- **⋯** — pausieren/fortsetzen, den Link kopieren, das Original öffnen oder **Überwachung beenden** (der Eintrag wird gelöscht; heruntergeladene Dateien bleiben)

### Eine Beobachtung bearbeiten

Klicke auf den Namen einer Beobachtung oder ihre Schaltfläche **Bearbeiten**. Der Dialog zeigt den vollständigen Link, dem gefolgt wird, mit **Link kopieren** und **Original öffnen**, dazu wann die Beobachtung hinzugefügt wurde, wann sie zuletzt geprüft wurde und wie viele Titel oder Veröffentlichungen sie hat. Du kannst ändern:

- **Link** — muss dieselbe Art von Link sein (eine Playlist für eine Playlist-Beobachtung, ein Künstler für eine Künstlerbeobachtung):
    - Ein anderer Link zur **selben** Playlist oder zum selben Künstler (zum Beispiel mit einem anderen Teilen-Code `?si=` oder der YouTube-Music-Link statt des `www.youtube.com`-Links) aktualisiert nur die gespeicherte Adresse. Sonst ändert sich nichts.
    - Ein Link zu einer **anderen** Playlist oder einem anderen Künstler richtet die Beobachtung darauf aus. Die Beobachtung behält ihr Intervall und ihren Aktivzustand, übernimmt aber den neuen Namen und fängt von vorn an: Ihr Download- bzw. Veröffentlichungsverlauf wird gelöscht und, falls aktiv, wird sie sofort geprüft. Titel, die schon in deiner Bibliothek sind, werden nicht erneut heruntergeladen, und Dateien vom vorherigen Ziel bleiben, wo sie sind.
    - Ein Link zu etwas, das schon beobachtet wird, wird abgelehnt.
- **Prüfen alle** und **Aktiv**.

Das ist praktisch für „lebende“ Playlists, die ersetzt werden: Öffne die Beobachtung, um zu prüfen, welcher Playlist sie wirklich folgt, und füge die neue ein, falls sie sich geändert hat.

## Sortierung

Das Steuerelement **Sortieren nach** über der Liste ordnet den aktuellen Tab nach:

| Feld | Hinweise |
|-------|-------|
| Hinzugefügt am | Standard — neueste zuerst |
| Name | Alphabetisch |
| Zuletzt geprüft | Zuletzt geprüfte zuerst; nie geprüfte zuletzt |
| Prüfhäufigkeit | Seltenste (längstes Intervall) zuerst |
| Anzahl der Titel / Veröffentlichungen | Meiste zuerst |

Die Schaltfläche daneben wechselt zwischen auf- und absteigender Reihenfolge. Die Wahl wird im Browser gemerkt und ändert nur die Liste — nicht die Prüfreihenfolge oder die Planung.

## Eine tägliche Synchronisierungszeit wählen

Standardmäßig synchronisiert eine täglich (oder wöchentlich / alle 2 Wochen / monatlich) geprüfte Playlist zu der Uhrzeit, zu der sie ursprünglich hinzugefügt oder zuletzt geprüft wurde — eine garantierte Tageszeit gibt es nicht. Um Synchronisierungen ab einem Tag auf eine bestimmte Stunde festzulegen (z. B. nachts um 3 Uhr statt irgendwann), setze die Umgebungsvariable `DOWNTIFY_MONITOR_SYNC_TIME` zusammen mit `TZ`. Siehe [Umgebungsvariablen](../getting-started/environment-variables.md#playlist-monitor) für die vollständige Referenz.

- Betrifft nur Intervalle von einem ganzen Tag oder mehr — kürzere Intervalle (15 Min. – 12 Std.) bleiben unberührt, da ihre Verankerung an eine einzige Tageszeit ihren Takt brechen würde.
- Die allererste Prüfung nach dem Hinzufügen einer Playlist läuft unabhängig von dieser Einstellung immer sofort.

## Anreicherung der Metadaten pro Titel

Den Einträgen im Spotify-Playlist-Embed fehlt das Erscheinungsjahr, und sie verwenden das Playlist-Cover statt des Albumcovers des einzelnen Titels. Downtify ruft jeden neuen Titel einzeln erneut ab, um vor dem Herunterladen das richtige Cover und Jahr zu erhalten — und fällt auf die Daten der Playlist-Ebene zurück, wenn der Abruf pro Titel scheitert. Einträge von YouTube-Music-Playlists überspringen diesen Schritt: Jeder trägt bereits die Metadaten seines eigenen Videos.

## M3U-Integration

Die M3U der Playlist wird **nach jedem fertigen Titel** neu geschrieben, wächst also, während der Durchlauf herunterlädt, statt erst zu erscheinen, wenn alles fertig ist. Die Playlist ist ab dem ersten Titel abspielbar, und ein langsamer oder hängender Download weiter unten in der Liste hält nie die bereits angekommenen Titel auf. Ein abschließendes Neuschreiben am Ende des Durchlaufs löst alles erneut gegen das Dateisystem auf.

Manuelle Playlist-/Album-Downloads und CSV-Importe verhalten sich genauso. Siehe [M3U-Export](m3u-export.md#when-it-is-written) für Details.

Ist [Playlist-Cover speichern](playlist-cover-art.md) an, wird das Cover einmal pro Durchlauf geholt, der Titel herunterzuladen hat — vor dem ersten davon, damit der Ordner wie die Playlist aussieht, während er sich füllt. Ein Durchlauf, der nichts Neues findet, holt es nicht erneut.

## Was mit Songs passiert, die eine Playlist verlassen

Live-Playlists (Spotifys *Top 50*, *Discover Weekly*, redaktionelle Charts) ändern sich jede Woche. Downtify behandelt eine Beobachtung als **Quelle neuer Musik**, nie als etwas, das bestimmt, was du behältst:

- **Heruntergeladene Audiodateien werden von einer Beobachtung nie gelöscht.** Nicht, wenn ein Titel die Playlist verlässt, nicht, wenn er jede von dir beobachtete Playlist verlässt, nicht, wenn die Playlist selbst schrumpft, und nicht, wenn du **Überwachung beenden** drückst.
- **Nur die Playlist folgt der Playlist.** Bei jedem Durchlauf wird die [M3U-Datei](m3u-export.md) aus den aktuellen Titeln der Playlist in ihrer aktuellen Reihenfolge neu geschrieben, sodass ein herausgefallener Titel aus der M3U verschwindet. Seine Datei bleibt im Ordner und in deiner Bibliothek, durchsuchbar und abspielbar — auch über Navidrome, Jellyfin oder alles, was auf denselben Ordner zeigt.
- **Ein Titel, der in gar keiner Playlist ist, bleibt ein Titel.** Nichts sucht nach „verwaisten“ Dateien.

So wird eine Chart-Playlist zu einem nutzbaren Entdeckungs-Feed: Neue Songs kommen automatisch, und was sie hinterlassen, sammelt sich als deine Bibliothek.

```
Top 50 - USA        →  new song appears   →  Downtify downloads it
                    →  song drops out     →  M3U updated, file kept
```

Das Einzige, was Audio löscht, sind Dinge, die du ausdrücklich verlangst: **Löschen** bei einem Titel oder einer Auswahl in der Bibliothek, das Löschen einer Playlist aus der Bibliothek (was ihre Titel löscht — es fragt vorher) oder das Entfernen von Dateien durch dich selbst im Dateisystem.

::: info Eine Beobachtung löschen vs. eine Playlist löschen
**Überwachung beenden** (im ⋯-Menü der Beobachtung) vergisst nur die Beobachtung: Auf der Festplatte ändert sich nichts. **Löschen** bei einer Playlist auf der **Bibliothek**-Seite ist die zerstörerische Aktion — es entfernt die Titel dieser Playlist, ihre M3U und ihren Katalogeintrag.
:::

Verschwindet eine Datei tatsächlich — du hast sie aus dem Download-Ordner genommen oder von Hand gelöscht —, bemerkt das ein stündlicher Durchlauf und vergisst Downtifys Eintrag dazu, sodass die nächste Prüfung einer Beobachtung, die den Titel noch listet, ihn erneut herunterlädt. Eine Datei, die nur innerhalb des Download-Ordners *verschoben* wurde, wird weiterhin gefunden und nicht erneut heruntergeladen.

## Speicherung

Der Zustand der Überwachung wird in einer SQLite-Datenbank unter `/data/downtify_monitor.db` gespeichert. Die Datenbank hält fest:

- Jede Beobachtung (Art, Spotify- oder YouTube-Music-Playlist-ID oder YouTube-Music-Kanal-ID, Name, URL, Intervall, aktiviert, Zeitpunkt der letzten Prüfung). Ob eine Beobachtung Spotify oder YouTube Music ist, wird aus ihrer gespeicherten URL gelesen, sodass keine zusätzliche Spalte nötig ist.
- Jeden erfolgreich heruntergeladenen Titel pro Beobachtung, einschließlich des Dateinamens auf der Festplatte
- Bei Künstlerbeobachtungen die bereits verarbeiteten Veröffentlichungen, damit ein Durchlauf Titellisten nur für wirklich neue abruft — einschließlich derer, die **Nur neue Veröffentlichungen** übersprungen hat, als solche markiert, damit das Ausschalten sie zurückholen kann — plus die Veröffentlichungsarten der Beobachtung und ob sie nur neue Veröffentlichungen beobachtet

Vor der Künstlerbeobachtung angelegte Datenbanken werden beim Start automatisch migriert; bestehende Zeilen funktionieren weiter als Playlist-Beobachtungen.
