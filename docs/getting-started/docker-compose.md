---
icon: lucide/file-code
---

# Docker Compose

Docker Compose is the recommended way to run Downtify for persistent home-server setups. It makes updates, backups and configuration changes easy.

## Minimal setup

Copy the repository example (recommended for 2.7.x + slskd):

```bash
cp docker-compose.example.yml docker-compose.yml
# Edit host paths in docker-compose.yml
docker compose pull
docker compose up -d
```

[`docker-compose.example.yml`](../../docker-compose.example.yml) uses **`dx616b/spoti-to-navidrome:2.7.8`**, maps `/downloads` and `/slskd`, and listens on port `30321` inside the container (`8000:30321` on the host).

Or create a minimal `docker-compose.yml` manually:

```yaml
services:
  downtify:
    container_name: downtify
    image: dx616b/spoti-to-navidrome:2.7.8
    ports:
      - '8000:30321'
    environment:
      - DOWNTIFY_PORT=30321
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped

volumes:
  downtify_data:
```

Start it:

```bash
docker compose up -d
```

Open **[http://localhost:8000](http://localhost:8000)**.

## With slskd (Soulseek)

Add a second volume so Downtify and slskd share the same Soulseek download folder:

```yaml
    volumes:
      - ./downloads:/downloads
      - ./slskd:/slskd
      - downtify_data:/data
```

In Downtify **Settings → slskd**: enable slskd, set **Base URL** to your slskd API (e.g. `http://slskd:5030` on a shared Docker network), **API key**, and **folder path** `/slskd`. Mount that same host directory on your slskd container.

Upstream image without this fork: `ghcr.io/henriquesebastiao/downtify:latest`.

## Custom port

If port 8000 is already in use, map a different host port and set the `DOWNTIFY_PORT` environment variable so the container listens on the same port internally:

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

## With custom DNS (recommended)

Some ISPs and corporate networks block YouTube. Adding explicit DNS resolvers improves reliability:

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

## Updating

```bash
docker compose pull
docker compose up -d
```

Your music and settings are preserved in the volumes.

## Volumes

| Path inside the compose file | Purpose |
|------------------------------|---------|
| `./downloads:/downloads` | Downloaded audio files (local directory) |
| `downtify_data:/data` | Application database and settings (named volume) |

You can replace the named volume with a local path (`./data:/data`) if you prefer to manage it yourself.
