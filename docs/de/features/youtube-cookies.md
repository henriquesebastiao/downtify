---
icon: lucide/cookie
---

# YouTube-Cookies

Downtify holt sein Audio von YouTube. Meistens klappt das anonym — aber nicht immer:

- **Explizite / altersbeschränkte Titel.** YouTube liefert diese nur an ein angemeldetes Erwachsenenkonto. Ohne Cookies schlägt der Download fehl.
- **Bot-Prüfungen.** Bei Rechenzentrums-IPs (VPS, manche VPNs) antwortet YouTube regelmäßig mit „Melde dich an, um zu bestätigen, dass du kein Bot bist“ statt mit Audio.

Mit einer `cookies.txt` lässt sich beides beheben: yt-dlp spricht dann mit YouTube so, wie es deine angemeldete Browsersitzung tut.

## Eine cookies.txt hochladen (empfohlen)

1. Installiere eine Erweiterung zum Cookie-Export: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome/Edge) oder [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox)
2. Öffne `youtube.com` **angemeldet in deinem Google-Konto** und exportiere die Cookies dieser Seite — die Datei muss im **Netscape**-Format vorliegen
3. Öffne in Downtify **Einstellungen** (⚙️) → **YouTube-Cookies** → **cookies.txt hochladen**

Die Datei wird beim Hochladen geprüft — eine Datei, die kein Netscape-Cookie-Jar ist, wird sofort abgelehnt, statt still alle späteren Downloads zu stören. Enthält sie keine `youtube.com`- oder `google.com`-Cookies, erhältst du eine Warnung, denn das bedeutet meist, dass sie aus dem falschen Tab exportiert wurde.

Nach dem Hochladen kannst du sie auf demselben Bildschirm **ersetzen** (eine andere Datei hochladen) oder **löschen**.

::: tip Das ist der plattformunabhängige Weg
Das Hochladen über die Weboberfläche braucht keine Bind-Mounts, keine Dateipfade und keine Shell — deshalb funktioniert es auch auf Docker Desktop für Windows, wo das Einbinden einer `cookies.txt` in den Container bekanntermaßen mühsam ist.
:::

## Wo sie gespeichert wird

Die hochgeladene Datei wird als `cookies.txt` im Datenverzeichnis von Downtify (standardmäßig `/data`) abgelegt — demselben Volume, das `settings.json` und die Datenbank der Playlist-Überwachung enthält. Sie **übersteht deshalb Container-Updates**: Ein neues Image zu ziehen und den Container neu zu erstellen, behält deine Cookies, solange `/data` ein benanntes Volume oder ein Bind-Mount bleibt.

## Stattdessen eine Umgebungsvariable nutzen

Die bereits vorhandene Variable [`DOWNTIFY_COOKIES_FILE`](../getting-started/environment-variables.md#anti-bot-youtube) funktioniert weiterhin und **hat Vorrang**:

```yaml
services:
  downtify:
    volumes:
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

Ist sie gesetzt, zeigt der Einstellungsbildschirm den Cookie-Bereich gesperrt und lehnt Uploads und Löschungen ab — die Bereitstellung besitzt diese Konfiguration, und Downtify darf keine Datei überschreiben, die es nicht verwaltet. Entferne die Variable (und erstelle den Container neu), um Cookies stattdessen über die Weboberfläche zu verwalten.

`DOWNTIFY_COOKIES_FROM_BROWSER` liest Cookies direkt aus einem Browserprofil, doch dafür muss der Cookie-Speicher des Browsers *innerhalb* des Containers erreichbar sein, weshalb es in Docker selten nutzbar ist.

## Funktionsfähig halten

- Cookies laufen ab. Schlagen altersbeschränkte Downloads wieder fehl, exportiere eine frische Datei und lade sie als Ersatz hoch.
- Ein Export aus einem **privaten/Inkognito-Fenster**, das du danach schließt, ergibt eine langlebigere Sitzung, weil das Schließen eines normalen Fensters die exportierte Sitzung ungültig machen kann.
- Manche Regionen verlangen eine vollständige Identitätsprüfung des Google-Kontos, bevor YouTube überhaupt altersbeschränkte Inhalte ausliefert. Angemeldet zu sein reicht nicht immer.

::: warning Behandle die Datei wie ein Passwort
Eine `cookies.txt` enthält aktive Sitzungstokens deines Google-Kontos. Wer sie lesen kann, kann auf YouTube in deinem Namen handeln. Downtify speichert sie, wo das Dateisystem es unterstützt, mit Berechtigungen nur für den Besitzer und gibt ihren Inhalt nie über die API preis — nur ob eine konfiguriert ist, ihre Größe und wann sie sich geändert hat. Nutze ein Wegwerf-Google-Konto, wenn du dein Hauptkonto nicht riskieren möchtest.
:::
