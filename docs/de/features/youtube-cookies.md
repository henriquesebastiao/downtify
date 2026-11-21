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
      - ./cookies.txt:/cookies.txt
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

Binde sie beschreibbar ein (ohne `:ro`), damit die Erneuerung die rotierten Cookies darin speichern kann; eine schreibgeschützte Datei wird weiter genutzt, veraltet aber wie bisher.

Ist sie gesetzt, zeigt der Einstellungsbildschirm den Cookie-Bereich gesperrt und lehnt Uploads und Löschungen ab — die Bereitstellung besitzt diese Konfiguration, und Downtify darf keine Datei überschreiben, die es nicht verwaltet. Entferne die Variable (und erstelle den Container neu), um Cookies stattdessen über die Weboberfläche zu verwalten.

`DOWNTIFY_COOKIES_FROM_BROWSER` liest Cookies direkt aus einem Browserprofil, doch dafür muss der Cookie-Speicher des Browsers *innerhalb* des Containers erreichbar sein, weshalb es in Docker selten nutzbar ist.

## Funktionsfähig halten

Exportierte Cookies laufen nicht an einem festen Datum ab. Die Google-Sitzung besteht aus Cookies, die sich ständig ändern: Der Tab, aus dem sie stammen, rotiert `__Secure-1PSIDTS`, `SIDCC` und Co. alle paar Minuten, und eine Kopie, die die neuen Werte nie erfährt, wird irgendwann abgelehnt. yt-dlp meldet dann „The provided YouTube account cookies are no longer valid“. Über ein VPN oder eine Rechenzentrums-IP ist YouTube strenger, dann kann das schon nach ein paar Stunden passieren.

Downtify hält die hochgeladene Datei selbst angemeldet:

- **Jeder Download speichert die neuen Werte.** yt-dlp bekommt für jeden Download eine private Kopie der Datei; danach werden die Cookies, die YouTube währenddessen geändert hat, in die gespeicherte `cookies.txt` zurückgeschrieben, ohne einen neueren Wert zu überschreiben, den ein anderer Download inzwischen gespeichert hat.
- **Eine Erneuerung frischt sie regelmäßig auf.** Alle 15 Minuten (`DOWNTIFY_COOKIES_REFRESH_MINUTES`, `0` schaltet sie ab) bittet Downtify Google, die Sitzungscookies zu rotieren – dieselbe Anfrage, die der Browser stellt –, öffnet `youtube.com` damit und speichert, was sich geändert hat. Selbst ein Server, der tagelang nichts herunterlädt, behält so eine gültige Sitzung.
- **Die Einstellungen zeigen das Ergebnis.** **Einstellungen → YouTube-Cookies** zeigt *Angemeldet*, *Abgemeldet*, *Kein Konto* (die Datei enthält keine Google-Sitzung, nur Besucher-Cookies) oder *Prüfung fehlgeschlagen*, wann zuletzt geprüft wurde und wann YouTube zuletzt eine Bot-Prüfung verlangt hat. *Jetzt prüfen* startet die Erneuerung sofort. Eine neue Datei wird wenige Sekunden nach dem Hochladen geprüft.

Was du weiterhin selbst tun musst:

- **Aus einem privaten Fenster exportieren und es schließen.** Melde dich in einem privaten Fenster bei YouTube an, öffne in diesem Tab `youtube.com/robots.txt`, exportiere die Cookies und schließe das Fenster. Ein Tab, den du weiter benutzt, rotiert die Sitzung selbst, und Downtifys Kopie wird innerhalb von Minuten abgemeldet. Nutze dasselbe Konto möglichst nicht gleichzeitig in einem normalen Fenster.
- **Eine neue Datei hochladen, wenn dort *Abgemeldet* steht.** Google kann die Sitzung trotzdem beenden (Passwortänderung, „Von allen Geräten abmelden“, eine Sicherheitsprüfung). Das Log sagt es auch: `YouTube cookies are signed out`.
- Manche Regionen verlangen eine vollständige Identitätsprüfung des Google-Kontos, bevor YouTube überhaupt altersbeschränkte Inhalte ausliefert. Angemeldet zu sein reicht nicht immer.

::: info Warum es keinen „Mit Google anmelden“-Button gibt
Downtify kann sich nicht für dich bei Google anmelden. Google blockiert skriptgesteuerte und Headless-Anmeldungen („Dieser Browser oder diese App ist möglicherweise nicht sicher“), verlangt Bestätigung in zwei Schritten und Geräteabfragen, und YouTube akzeptiert kein OAuth mehr von Drittanbieter-Clients wie yt-dlp. Ein Anmeldeformular in Downtify würde außerdem bedeuten, ihm dein Google-Passwort zu geben. Eine exportierte Sitzung am Leben zu halten ist der Teil, der sich automatisieren lässt.
:::

::: tip Bot-Prüfungen ohne Konto
„Sign in to confirm you're not a bot“ hängt von der IP-Adresse ab, nicht von fehlenden Cookies. Taucht es über ein VPN immer wieder auf, hilft ein anderer VPN-Server oder ein anderes Ausgangsland oft mehr als neue Cookies. Cookies, die für viele Downloads benutzt werden, erhöhen außerdem das Risiko, dass YouTube das Konto einschränkt – ein Wegwerfkonto ist die sicherere Wahl.
:::

::: warning Behandle die Datei wie ein Passwort
Eine `cookies.txt` enthält aktive Sitzungstokens deines Google-Kontos. Wer sie lesen kann, kann auf YouTube in deinem Namen handeln. Downtify speichert sie, wo das Dateisystem es unterstützt, mit Berechtigungen nur für den Besitzer und gibt ihren Inhalt nie über die API preis — nur ob eine konfiguriert ist, ihre Größe und wann sie sich geändert hat. Nutze ein Wegwerf-Google-Konto, wenn du dein Hauptkonto nicht riskieren möchtest.
:::
