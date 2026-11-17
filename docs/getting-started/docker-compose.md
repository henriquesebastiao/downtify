---
icon: lucide/file-code
---

# Docker Compose

Docker Compose is the recommended way to run Downtify for persistent home-server setups. It makes updates, backups and configuration changes easy.

## Minimal setup

Create a `docker-compose.yml` file. It runs Downtify on PostgreSQL, with the database in a `postgres` service next to it (see [Database](../database.md)):

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

Set `POSTGRES_PASSWORD` in a `.env` file next to the Compose file before the first start (see [Environment variables](environment-variables.md#database)). To keep the SQLite files instead, remove `DATABASE_URL`, the `postgres` service and the `depends_on` block.

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

Then, in **Settings → Audio sources → slskd**, enable slskd, enter its URL (e.g. `http://slskd:5030` when both containers share a Docker network) and API key, and set the download folder to `/slskd`.

## Existing music folders

To have the Library pick up a collection you already keep on the host, [mount it](../features/external-library.md) the same way and type the **container** path in **Settings → Library**:

```yaml
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

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

You can also choose the port in **Settings → Server → Port** instead of setting `DOWNTIFY_PORT` (which, when set, wins over Settings). In the default bridge network, change the `ports:` mapping to the same port and recreate the container — see [Changing the port](../features/server.md#changing-the-port).

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

`latest` always follows the newest release. Every release is also published under its full version and its minor and major lines, so `ghcr.io/henriquesebastiao/downtify:3.12.0` never changes, `:3.12` gets only that line's fixes and `:3` moves to every 3.x release. The same tags exist on Docker Hub (`henriquesebastiao/downtify`).

## Volumes

| Path inside the compose file | Purpose |
|------------------------------|---------|
| `./downloads:/downloads` | Downloaded audio files (local directory) |
| `downtify_data:/data` | Settings, caches and the SQLite files (named volume) |
| `pgdata:/var/lib/postgresql/data` | The PostgreSQL database, in the `postgres` service |

You can replace the named volume with a local path (`./data:/data`) if you prefer to manage it yourself.
