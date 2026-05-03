---
icon: lucide/download
---

# Installation

The quickest way to run Downtify is with a single `docker run` command. No Python, Node.js or other system dependencies needed on the host — everything is bundled inside the image.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed and running

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

Replace `/path/to/music` with the directory where you want your music saved.

Once the container starts, open **[http://localhost:8000](http://localhost:8000)** in your browser.

## Volumes

| Volume | Purpose |
|--------|---------|
| `/downloads` | Downloaded audio files |
| `/data` | Application database and persistent settings |

Both volumes persist across container restarts and upgrades. The `/downloads` volume can be any directory on your host machine or a named Docker volume.

## Custom port

To expose Downtify on a different host port, change the left side of `-p`:

```bash
docker run -d \
  --name downtify \
  -p 9090:8000 \           # host:container
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Then open **[http://localhost:9090](http://localhost:9090)**.

## Updating

Pull the latest image and recreate the container:

```bash
docker pull ghcr.io/henriquesebastiao/downtify
docker stop downtify && docker rm downtify
docker run -d --name downtify -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Your music and settings are preserved in the volumes.

## What's next?

- **[Docker Compose](docker-compose.md)** — easier way to manage the container long-term
- **[Environment variables](environment-variables.md)** — tune anti-bot behaviour and other advanced options
- **[Download settings](../features/download-settings.md)** — choose your format and bitrate
