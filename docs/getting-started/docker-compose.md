---
icon: lucide/file-code
---

# Docker Compose

Docker Compose is the recommended way to run Downtify for persistent home-server setups. It makes updates, backups and configuration changes easy.

## Minimal setup

Create a `docker-compose.yml` file:

```yaml
services:
  downtify:
    container_name: downtify
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
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

To use [slskd as an audio source](../features/slskd-navidrome.md), mount slskd's download folder into Downtify too — the **same host folder** your slskd container writes to:

```yaml
services:
  downtify:
    # ...
    volumes:
      - ./downloads:/downloads
      - /path/to/slskd/downloads:/slskd
      - downtify_data:/data
```

Then, in **Settings → slskd (Soulseek)**, enable slskd, enter its URL (e.g. `http://slskd:5030` when both containers share a Docker network) and API key, and set the download folder to `/slskd`.

## Finding the server from the apps

The [mobile apps](../features/mobile-apps.md#finding-the-server-on-your-network) list Downtify servers on your network through mDNS. In Docker's default bridge network that announcement never leaves Docker, so phones don't see it. To have it listed, run the container on the host's network — the `ports:` mapping then no longer applies, and Downtify listens on `DOWNTIFY_PORT` directly:

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

Otherwise just type the server's address into the app (`http://<host IP>:8000`); nothing else depends on discovery.

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
