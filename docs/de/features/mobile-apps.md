---
icon: lucide/smartphone
---

# Mobile Apps

Downtify kann Apps auf deinem Handy bedienen: Sie durchsuchen die Bibliothek und streamen sie direkt von deinem Server und behalten Songs zum Offline-Hören auf dem Handy. Alles, was eine App braucht, wird unter **Einstellungen → Apps** eingerichtet: das Koppeln von Handys und der Name des Servers. Wer den Server überhaupt nutzen darf, bestimmen die Konten unter [Benutzer und Anmeldung](users.md).

::: warning Die App ist noch in Entwicklung
**Einstellungen → Apps** ist als *Experimentell* gekennzeichnet. Die auf dieser Seite beschriebene Serverseite ist fertig und funktioniert, aber **es wurde noch keine Version der Android-App veröffentlicht**, es gibt also vorerst nichts zu installieren, und Details zum Koppeln und Streamen können sich zwischen Downtify-Versionen noch ändern.

Die App wird offen unter [henriquesebastiao/downtify-android](https://github.com/henriquesebastiao/downtify-android) entwickelt. Alles andere lässt sich gegen dieselbe API bauen — siehe den [Vertrag für mobile Clients](../mobile-client-contract.md).
:::

## In der App anmelden

Gib die Adresse des Servers ein (oder wähle ihn unter **In diesem Netzwerk gefunden**) und melde dich mit **demselben Benutzernamen und Passwort** wie auf der Webseite an. Das Handy erscheint unter **Verbundene Apps**, genau als hättest du es unten mit einem Code gekoppelt: Es spielt als du, behält einen eigenen Schlüssel (das Passwort wird nicht auf dem Handy gespeichert), und **Verbindung trennen** stoppt es.

Falsche Passwörter sind zusammen mit der Anmeldung auf der Webseite ratenbegrenzt. Solange Konten ausgeschaltet sind (`DOWNTIFY_DISABLE_AUTH`), gibt es nichts, womit man sich anmelden könnte: Kopple dann mit einem Code.

## Ein Handy koppeln

Koppeln braucht kein Passwort auf dem Handy: praktisch, wenn die Webseite schon offen ist, oder auf einem Handy, auf dem du dein Passwort lieber nicht eintippst.

1. Öffne **Einstellungen → Apps** und drücke **Telefon koppeln**.
2. Wähle in der App **Code scannen** und richte die Kamera auf den QR-Code — oder tippe den darunter angezeigten 8-stelligen Code ein (`K7QM-2XPD`; Groß-/Kleinschreibung und Bindestriche spielen keine Rolle).
3. Der Dialog bestätigt, wenn das Handy gekoppelt ist, und es erscheint unter **Verbundene Apps**.

Das Handy wird mit **deinem Konto** gekoppelt: Es spielt als du und erscheint in deiner Aktivität. Jeder mit einem Konto kann seine eigenen Handys koppeln.

Ein Code funktioniert **einmal**, **fünf Minuten** lang, und das Ausprobieren falscher Codes ist ratenbegrenzt. Das Handy erhält einen eigenen Schlüssel, den es behält; der Server speichert nur einen Hash davon.

**Verbundene Apps** listet deine Handys auf (ein Admin sieht die aller, mit dem jeweiligen Besitzer) mit Plattform, letzter Sichtung und von welcher Adresse. **Verbindung trennen** stoppt ein Handy sofort — seine nächste Anfrage schlägt fehl, eine offene Verbindung wird geschlossen, und von ihm geteilte Links (siehe [Casting](#casting)) funktionieren nicht mehr. Um es wieder zu nutzen, koppelst du es erneut.

## Was eine gekoppelte App darf

Gekoppelte Apps können stöbern, abspielen, liken, Songs offline behalten und den Server bitten, Musik herunterzuladen — aber keine Einstellungen oder Zugangsdaten ändern und keine Dateien löschen; das erfordert die Webseite, als Admin angemeldet.

**Einstellungen → Apps → Überall abmelden** trennt alle deine Apps und meldet dich in jedem Browser ab, diesen eingeschlossen. Anmeldung, Konten und ein vergessenes Passwort stehen unter [Benutzer und Anmeldung](users.md).

## Den Server im Netzwerk finden

Der Server kündigt sich im lokalen Netzwerk an (mDNS / Bonjour, als `_downtify._tcp`), sodass eine App ihn unter **In diesem Netzwerk gefunden** auflistet — Name, Adresse und Version — ohne dass du etwas tippen musst. Der Name ist der unter **Einstellungen → Apps → Servername** festgelegte (der Hostname der Maschine, bis du ihn änderst).

::: info Dockers Standardnetzwerk verbirgt die Ankündigung
Im Standard-*Bridge*-Netzwerk von Docker bleibt die Ankündigung innerhalb von Docker, und Handys sehen sie nicht. Entweder startest du den Container mit `network_mode: host` (siehe [Docker Compose](../getting-started/docker-compose.md#finding-the-server-from-the-apps)), oder du tippst die Adresse des Servers in die App ein — alles andere funktioniert gleich.
:::

Setze `DOWNTIFY_DISCOVERY=false`, um die Ankündigung zu beenden.

## Streaming-Qualität

Apps spielen die Dateien so ab, wie sie sind (**Original**), oder bitten den Server um eine kleinere Kopie: Opus, AAC oder MP3 mit 96–320 kbps — nützlich bei mobilen Daten. Der Server erstellt diese Kopie mit ffmpeg beim ersten Mal, wenn ein Song so abgespielt wird (ein paar Sekunden bei einem typischen Song), und behält sie, sodass das Vor- und Zurückspulen wie bei jeder Datei funktioniert und die nächste Wiedergabe sofort startet.

- Eine Datei, die schon klein genug ist (eine verlustbehaftete Datei mit der angeforderten oder einer niedrigeren Bitrate), wird unverändert gestreamt, nie neu kodiert.
- Kopien liegen in `/data/transcode_cache`, standardmäßig höchstens 2 GB; die am längsten nicht gespielten fliegen zuerst raus. Höchstens zwei werden gleichzeitig erstellt. Beide Grenzen sind [Umgebungsvariablen](../getting-started/environment-variables.md#mobile-apps-and-sign-in).
- Gibt das Handy auf, während eine Kopie erstellt wird, hört der Server damit auf.

## Casting

Apps können einen Song an einen Chromecast oder einen anderen Player senden, der das Audio selbst abholt. Die App erhält vom Server einen Link, der für genau diesen Song eine begrenzte Zeit (standardmäßig eine Stunde) und nur gültig ist, solange das Handy gekoppelt bleibt; kein Schlüssel des Handys steckt darin.

## Hinter einem Reverse-Proxy

Steht Downtify hinter nginx, Caddy, Traefik oder Ähnlichem (für HTTPS oder um von außen darauf zuzugreifen):

- **Reiche den WebSocket durch.** `/api/ws` braucht weitergeleitete `Upgrade`-/`Connection`-Header (Caddy und Traefik tun das standardmäßig; nginx braucht `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";`).
- **Reiche Range-Anfragen** unverändert durch und puffere Audio-Antworten nicht (nginx: `proxy_buffering off;` für `/api/v1/` und `/downloads/`), sonst leiden Spulen und große Dateien.
- **Sag Downtify, welchem Proxy es vertrauen soll.** Setze `DOWNTIFY_TRUSTED_PROXIES` auf die Adresse des Proxys (z. B. `172.18.0.0/16`). Nur dann nutzt Downtify `X-Forwarded-For` für die Adresse des Clients (Ratenbegrenzungen, „zuletzt gesehen“ unter Verbundene Apps) und `X-Forwarded-Proto`/`X-Forwarded-Host`, um das Anmelde-Cookie als sicher zu markieren und zu prüfen, woher Anfragen kommen. Ohne sie werden diese Header ignoriert — jeder könnte sie senden.
- **Nutze HTTPS**, wenn der Server von außen erreichbar ist: Das Passwort und die Schlüssel der Apps reisen mit jeder Anfrage.

## Für App-Entwickler

Der gesamte Ablauf, dem eine App folgt — Erkennung, Koppeln, Synchronisieren der Bibliothek, Streaming, Melden von Wiedergaben — steht im [Vertrag für mobile Clients](../mobile-client-contract.md), und jeder Endpunkt steht in der [API-Referenz](../api-reference.md#server-and-sign-in).
