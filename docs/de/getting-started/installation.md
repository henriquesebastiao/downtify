---
icon: lucide/download
---

# Installation

Der schnellste Weg, Downtify zu betreiben, ist ein einziger `docker run`-Befehl. Auf dem Host werden weder Python noch Node.js oder andere Systemabhängigkeiten benötigt — alles steckt im Image.

## Voraussetzungen

- [Docker](https://docs.docker.com/get-docker/) installiert und gestartet

## Docker run

```bash
docker run -d \
  --name downtify \
  -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Ersetze `/path/to/music` durch das Verzeichnis, in dem deine Musik gespeichert werden soll.

Sobald der Container läuft, öffne **[http://localhost:8000](http://localhost:8000)** im Browser.

## Volumes

| Volume | Zweck |
|--------|---------|
| `/downloads` | Heruntergeladene Audiodateien |
| `/data` | Anwendungsdatenbank und dauerhafte Einstellungen |

Beide Volumes bleiben über Container-Neustarts und -Updates hinweg erhalten. Das Volume `/downloads` kann ein beliebiges Verzeichnis auf deinem Host oder ein benanntes Docker-Volume sein.

## Eigener Port

Um Downtify auf einem anderen Host-Port bereitzustellen, ändere die linke Seite von `-p`:

```bash
docker run -d \
  --name downtify \
  -p 9090:8000 \           # Host:Container
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Öffne dann **[http://localhost:9090](http://localhost:9090)**.

## Aktualisieren

Ziehe das neueste Image und erstelle den Container neu:

```bash
docker pull ghcr.io/henriquesebastiao/downtify
docker stop downtify && docker rm downtify
docker run -d --name downtify -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Deine Musik und deine Einstellungen bleiben in den Volumes erhalten.

## Wie geht es weiter?

- **[Docker Compose](docker-compose.md)** — einfachere Verwaltung des Containers auf Dauer
- **[Umgebungsvariablen](environment-variables.md)** — Anti-Bot-Verhalten und weitere erweiterte Optionen anpassen
- **[Download-Einstellungen](../features/download-settings.md)** — Format und Bitrate wählen
