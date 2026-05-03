---
icon: lucide/play
---

# Getting Started

Downtify is a self-hosted web app that downloads music from Spotify — no API keys, no account, no Premium subscription required. Everything runs inside a single Docker container.

## What you need

- **Docker** (or Docker Compose) — the only requirement on the host machine
- A machine with internet access
- A volume/directory where you want your music saved

## Choose your setup

<div class="grid cards" markdown>

-   :material-docker: **Docker run**

    ---

    The fastest way to get started. One command, up in under a minute.

    [Installation →](installation.md)

-   :material-file-code: **Docker Compose**

    ---

    Recommended for persistent setups. Easier to update and manage.

    [Docker Compose →](docker-compose.md)

-   :material-home: **One-click install**

    ---

    Running Umbrel, CasaOS or HomeDock OS? Install directly from their app stores.

    [One-click install →](one-click.md)

</div>

## Next steps

Once Downtify is running, open [http://localhost:8000](http://localhost:8000) in your browser. Paste a Spotify track, album or playlist URL into the search bar and hit **Download**.

Explore the rest of the documentation to learn about [download settings](../features/download-settings.md), the [playlist monitor](../features/playlist-monitor.md), the [built-in player](../features/player.md), and more.
