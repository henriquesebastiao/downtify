---
icon: lucide/settings
---

# Umgebungsvariablen

Alle Umgebungsvariablen sind optional. Downtify funktioniert ohne sie sofort.

## Grundlegendes

| Variable | Standard | Beschreibung |
|----------|---------|-------------|
| `DOWNTIFY_PORT` | _(nicht gesetzt)_ | Port, auf dem der Server lauscht (im Container). Nicht gesetzt: der unter **Einstellungen → Server → Port** gewählte Port, sonst `8000`. Gesetzt, hat sie Vorrang und das Feld in den Einstellungen ist gesperrt. Ändere die linke Seite der Port-Zuordnung, um einen anderen Host-Port bereitzustellen. Siehe [Port ändern](../features/server.md#changing-the-port). |
| `DOWNLOAD_DIR` | `/downloads` | Verzeichnis, in dem Audiodateien gespeichert werden. Überschreiben, wenn du deine Bibliothek an einem eigenen Pfad einbindest. |
| `HOST` | `0.0.0.0` | Bind-Adresse des Webservers. |
| `DOWNTIFY_LOG_LEVEL` | `info` | Log-Level der Anwendung (`debug`, `info`, `warning`, …). |
| `TZ` | `UTC` | Lokale Zeitzone (IANA-Name, z. B. `America/Sao_Paulo`), nötig zur Auswertung von `DOWNTIFY_MONITOR_SYNC_TIME` weiter unten. |

## Playlist-Überwachung

| Variable | Standard | Beschreibung |
|----------|---------|-------------|
| `DOWNTIFY_MONITOR_SYNC_TIME` | _(nicht gesetzt)_ | Uhrzeit (24 h `HH:MM`, in der Zeitzone von `TZ` oben), zu der Synchronisierungen der [Playlist-Überwachung](../features/playlist-monitor.md#choosing-a-daily-sync-time) mit einem Intervall ab einem Tag (täglich, wöchentlich, alle 2 Wochen, monatlich) laufen sollen. Nicht gesetzt: Es wird genau ein Intervall nach der vorherigen Prüfung synchronisiert, egal zu welcher Uhrzeit das fällt. |

```yaml
environment:
  - TZ=America/Sao_Paulo
  - DOWNTIFY_MONITOR_SYNC_TIME=03:00
```

## Mobile Apps und Anmeldung

Siehe [Mobile Apps](../features/mobile-apps.md) und [Benutzer und Anmeldung](../features/users.md). Die Anmeldung ist Pflicht, es sei denn `DOWNTIFY_DISABLE_AUTH` ist `true`; `DOWNTIFY_REQUIRE_SIGN_IN` aus früheren Versionen wird nicht mehr verwendet (solange sie gesetzt ist, wird eine Warnung protokolliert).

| Variable | Standard | Beschreibung |
|----------|---------|-------------|
| `DOWNTIFY_DISABLE_AUTH` | `false` | `true` schaltet Konten ab: Niemand meldet sich an, und wer den Server erreicht, nutzt ihn als Admin. Die Anmeldeseite, die Abmelde-Schaltflächen, **Einstellungen → Benutzer** und der Konto-Teil von **Einstellungen → Allgemein** verschwinden. Gekoppelte Apps funktionieren weiter. Setze sie zurück auf `false` (oder entferne sie), und die Anmeldung ist wieder Pflicht, mit den Konten wie zuvor. Siehe [Benutzer und Anmeldung](../features/users.md#turning-accounts-off). |
| `DOWNTIFY_TRUSTED_PROXIES` | _(nicht gesetzt)_ | Kommagetrennte Adressen oder Netzwerke deines Reverse-Proxys (z. B. `172.18.0.0/16,10.0.0.5`). Nur bei Anfragen von diesen werden die Header `X-Forwarded-For`, `X-Forwarded-Proto` und `X-Forwarded-Host` geglaubt — für die Client-Adresse, nach der Anmelde- und Kopplungsversuche begrenzt werden, das Secure-Flag des Anmelde-Cookies und die Same-Site-Prüfung. Nicht gesetzt: Diese Header werden ignoriert. |
| `DOWNTIFY_DISCOVERY` | `true` | `false` beendet das Ankündigen des Servers im lokalen Netzwerk (mDNS, `_downtify._tcp`), womit die Apps ihn unter *In diesem Netzwerk gefunden* auflisten. Im Bridge-Netzwerk von Docker erreicht die Ankündigung das LAN ohnehin nicht — siehe [Docker Compose](docker-compose.md#finding-the-server-from-the-apps). |
| `DOWNTIFY_TRANSCODE_CACHE_MB` | `2048` | Maximale Größe in MB, unter der der Cache transkodierter Kopien (`/data/transcode_cache`) gehalten wird; die am längsten nicht gespielten Kopien fliegen zuerst raus. |
| `DOWNTIFY_TRANSCODE_CONCURRENCY` | `2` | Wie viele Songs gleichzeitig für die kleineren Streaming-Qualitäten der Apps transkodiert werden. |
| `DOWNTIFY_STREAM_CACHE_MB` | `1024` | Maximale Größe in MB, unter der der Cache gestreamten Audios (`/data/stream_cache`) gehalten wird; die am längsten nicht gespielten Kopien fliegen zuerst raus. Das Streaming über den Server spielt nicht heruntergeladene Titel dort ab, wo der Browser selbst YouTube nicht erreicht. |
| `DOWNTIFY_STREAM_CONCURRENCY` | `2` | Wie viele Stream-Downloads gleichzeitig laufen dürfen. |

## Musik-Papierkorb

Siehe [Musik-Papierkorb](../features/music-trash.md). Aus, solange keine dieser Variablen gesetzt ist.

| Variable | Standard | Beschreibung |
|----------|---------|-------------|
| `DOWNTIFY_TRASH` | `false` | `true` schaltet den Musik-Papierkorb für den Download-Ordner ein: Entfernte Titel kommen 30 Tage lang in einen Papierkorb, und Downtify verschiebt die Dateien selbst. Solange er an ist, entfernen nur Admins Titel. |
| `DOWNTIFY_TRASH_CONFIG` | _(nicht gesetzt)_ | Pfad (im Container) einer JSON-Datei mit den Ordnern, die der Papierkorb abdeckt, und wo sein Worker läuft (`embedded` oder `external`). Hat Vorrang vor `DOWNTIFY_TRASH`. Eine unlesbare Datei verhindert den Serverstart. Siehe [Die Konfigurationsdatei](../features/music-trash.md#the-configuration-file). |

## Health-Check

Das Image hat einen eingebauten [Docker-`HEALTHCHECK`](https://docs.docker.com/reference/dockerfile/#healthcheck) — ein eigenes `--health-cmd` ist nicht nötig. Er fragt alle 30 Sekunden `GET /api/health` auf dem Port des Containers selbst ab (5 Sekunden Timeout, 20 Sekunden Gnadenfrist beim Start, 3 Wiederholungen, bevor der Container als „unhealthy“ gilt). `docker ps` und `docker inspect` zeigen das Ergebnis, und Werkzeuge wie `condition: service_healthy` in Compose oder Watchtower können darauf reagieren.

| Variable | Standard | Beschreibung |
|----------|---------|-------------|
| `DOWNTIFY_HEALTHCHECK` | `1` | Auf `0` setzen, um die eingebaute Prüfung auszuschalten — sie meldet dann immer „healthy“, ohne den Server zu kontaktieren. Nutze das, wenn eine externe Prüfung bzw. eine auf Orchestrator-Ebene (z. B. eine Kubernetes-Liveness-Probe) allein über die Gesundheit des Containers entscheiden soll. |

```yaml
environment:
  - DOWNTIFY_HEALTHCHECK=0
```

## Anti-Bot / YouTube

YouTube stellt automatisierte Downloader regelmäßig auf die Probe. Diese Variablen geben dir Notausgänge, wenn die Standardwerte nicht mehr funktionieren.

| Variable | Standard | Beschreibung |
|----------|---------|-------------|
| `DOWNTIFY_FORCE_IPV4` | _(nicht gesetzt)_ | Auf `1` setzen, damit yt-dlp nur IPv4 nutzt. Nützlich, wenn dein Host eine defekte oder ratenbegrenzte IPv6-Adresse hat. |
| `DOWNTIFY_YT_PLAYER_CLIENTS` | `ios,android,web_embedded,mweb,web,tv` | Kommagetrennte Liste der zu probierenden yt-dlp-Player-Clients, der Reihe nach. Die Standardliste von Downtify bevorzugt bereits Clients, die ohne JavaScript-Runtime funktionieren. Nur ändern, wenn du weißt, dass ein bestimmter Client blockiert wird. |
| `DOWNTIFY_YT_PO_TOKEN` | _(nicht gesetzt)_ | Kommagetrennte Proof-of-Origin-Tokens für yt-dlp, jedes in der Form `<client>.<context>+<token>` (z. B. `mweb.gvs+ABC123`). Nur nötig, wenn YouTube für die genutzten Clients PO-Tokens verlangt. |
| `DOWNTIFY_COOKIES_FILE` | _(nicht gesetzt)_ | Pfad zu einer `cookies.txt` im Netscape-Format **im Container**. Lässt yt-dlp sich wie eine echte Browsersitzung authentifizieren — nötig für explizite/altersbeschränkte Titel und immer dann, wenn YouTube eine Anmeldeschranke erzwingt. Hat Vorrang vor einer in der Weboberfläche hochgeladenen Datei und macht diesen Bereich der Oberfläche schreibgeschützt. Siehe [YouTube-Cookies](../features/youtube-cookies.md). |
| `DOWNTIFY_COOKIES_FROM_BROWSER` | _(nicht gesetzt)_ | Name des Browsers, aus dem Cookies gelesen werden (z. B. `chrome`, `firefox`). Setzt voraus, dass der Cookie-Speicher des Browsers im Container erreichbar ist, daher in Docker selten nutzbar. |

::: tip Du brauchst sie wahrscheinlich nicht
Du kannst eine `cookies.txt` direkt unter **Einstellungen → YouTube-Cookies** in der Weboberfläche hochladen. Sie wird in `/data` gespeichert (übersteht also Container-Updates), braucht weder Bind-Mount noch Container-Pfad und funktioniert unter Windows, macOS und Linux gleich. Die obigen Variablen bleiben für Bereitstellungen unterstützt, die die Datei lieber selbst verwalten.
:::

## Beispiel: Docker Compose mit Anti-Bot-Einstellungen

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_FORCE_IPV4=1
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
    restart: unless-stopped
```

## Eine cookies.txt besorgen

Nutze eine Browsererweiterung wie [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome) oder [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox). Exportiere von `youtube.com`, angemeldet in einem echten Google-Konto, und lade die Datei dann unter **Einstellungen → YouTube-Cookies** hoch oder binde sie wie oben gezeigt in den Container ein.

Den vollständigen Ablauf findest du unter [YouTube-Cookies](../features/youtube-cookies.md), und [Fehlerbehebung](../troubleshooting.md), wenn Downloads weiterhin fehlschlagen.

::: warning
Halte deine `cookies.txt` privat — sie enthält Sitzungstokens, die Zugriff auf dein Google-Konto gewähren.
:::
