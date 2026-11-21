---
icon: lucide/file-code
---

# Docker Compose

Docker Compose ist der empfohlene Weg, Downtify für dauerhafte Home-Server-Setups zu betreiben. Es macht Updates, Backups und Konfigurationsänderungen einfach.

## Minimales Setup

Erstelle eine Datei `docker-compose.yml`. Sie betreibt Downtify mit PostgreSQL, die Datenbank läuft in einem Dienst `postgres` daneben (siehe [Datenbank](../database.md)):

```yaml
services:
  downtify:
    container_name: downtify
    image: ghcr.io/henriquesebastiao/downtify:latest
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    environment:
      DATABASE_URL: postgresql://downtify:${POSTGRES_PASSWORD:-downtify}@postgres:5432/downtify

  postgres:
    container_name: downtify-postgres
    image: 'postgres:17-alpine'
    restart: unless-stopped
    environment:
      POSTGRES_USER: downtify
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-downtify}
      POSTGRES_DB: downtify
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U downtify -d downtify']
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s

volumes:
  downtify_data:
  pgdata:
```

Setze `POSTGRES_PASSWORD` vor dem ersten Start in einer `.env`-Datei neben der Compose-Datei (siehe [Umgebungsvariablen](environment-variables.md#database)). Um stattdessen die SQLite-Dateien zu behalten, entferne `DATABASE_URL`, den Dienst `postgres` und den Block `depends_on`.

Starte es:

```bash
docker compose up -d
```

Öffne **[http://localhost:8000](http://localhost:8000)**.

## Mit slskd (Soulseek)

Um [slskd als Audioquelle](../features/slskd-navidrome.md) zu nutzen, binde auch den Download-Ordner von slskd in Downtify ein — **denselben Host-Ordner**, in den dein slskd-Container schreibt:

```yaml
services:
  downtify:
    # ...
    volumes:
      - ./downloads:/downloads
      - /path/to/slskd/downloads:/slskd
      - downtify_data:/data
```

Aktiviere dann unter **Einstellungen → Audioquellen → slskd** slskd, gib seine URL (z. B. `http://slskd:5030`, wenn beide Container ein Docker-Netzwerk teilen) und den API-Schlüssel ein und setze den Download-Ordner auf `/slskd`.

## Vorhandene Musikordner

Damit die Bibliothek eine Sammlung übernimmt, die du bereits auf dem Host hast, [binde sie](../features/external-library.md) auf dieselbe Weise ein und gib den **Container**-Pfad unter **Einstellungen → Bibliothek** ein:

```yaml
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

## Den Server aus den Apps finden

Die [mobilen Apps](../features/mobile-apps.md#finding-the-server-on-your-network) listen Downtify-Server in deinem Netzwerk per mDNS auf. Im Standard-Bridge-Netzwerk von Docker verlässt diese Ankündigung Docker nie, daher sehen Smartphones sie nicht. Damit sie erscheint, betreibe den Container im Netzwerk des Hosts — die `ports:`-Zuordnung gilt dann nicht mehr, und Downtify lauscht direkt auf `DOWNTIFY_PORT`:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    network_mode: host
    environment:
      - DOWNTIFY_PORT=8000
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped
```

Andernfalls gib einfach die Adresse des Servers in der App ein (`http://<Host-IP>:8000`); nichts anderes hängt von der Erkennung ab.

## Eigener Port

Ist Port 8000 schon belegt, ordne einen anderen Host-Port zu und setze die Umgebungsvariable `DOWNTIFY_PORT`, damit der Container intern auf demselben Port lauscht:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '9090:30321'
    environment:
      - DOWNTIFY_PORT=30321
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped
```

Du kannst den Port auch unter **Einstellungen → Server → Port** wählen, statt `DOWNTIFY_PORT` zu setzen (die, wenn gesetzt, Vorrang vor den Einstellungen hat). Ändere im Standard-Bridge-Netzwerk die `ports:`-Zuordnung auf denselben Port und erstelle den Container neu — siehe [Port ändern](../features/server.md#changing-the-port).

## Mit eigenem DNS (empfohlen)

Manche Internetanbieter und Firmennetzwerke blockieren YouTube. Explizite DNS-Resolver erhöhen die Zuverlässigkeit:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    dns:
      - 1.1.1.1
      - 1.0.0.1
    restart: unless-stopped
```

## Aktualisieren

```bash
docker compose pull
docker compose up -d
```

Deine Musik und deine Einstellungen bleiben in den Volumes erhalten.

## Volumes

| Pfad in der Compose-Datei | Zweck |
|------------------------------|---------|
| `./downloads:/downloads` | Heruntergeladene Audiodateien (lokales Verzeichnis) |
| `downtify_data:/data` | Einstellungen, Caches und die SQLite-Dateien (benanntes Volume) |
| `pgdata:/var/lib/postgresql/data` | Die PostgreSQL-Datenbank, im Dienst `postgres` |

Du kannst das benannte Volume durch einen lokalen Pfad (`./data:/data`) ersetzen, wenn du es lieber selbst verwaltest.
