---
icon: lucide/hand-heart
---

# Contributing

Contributions are welcome — bug reports, feature requests, code and translations all help.

## Issues and feature requests

Use the [GitHub issue tracker](https://github.com/henriquesebastiao/downtify/issues). Before opening a new issue, search existing ones to avoid duplicates.

For bug reports, include:

- Downtify version
- How you installed it (Docker run, Docker Compose, Umbrel, …)
- Steps to reproduce
- What you expected vs. what happened
- Any relevant logs

## Development setup

### Prerequisites

- Python 3.13+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- ffmpeg (must be on `PATH`)

### Clone and install

```bash
git clone https://github.com/henriquesebastiao/downtify.git
cd downtify

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Run in development mode

```bash
# Terminal 1 — backend
uv run python main.py

# Terminal 2 — frontend dev server (hot reload)
cd frontend && npm run dev
```

The frontend dev server proxies API requests to the backend, so you only need to open the Vite URL (usually `http://localhost:5173`).

### Run the tests

```bash
uv run pytest
```

### Build the frontend for production

```bash
cd frontend && npm run build
```

The compiled assets land in `frontend/dist/` and are served by the backend.

## Project structure

```
downtify/
├── downtify/          # Python backend
│   ├── api.py         # FastAPI router
│   ├── downloader.py  # yt-dlp + mutagen pipeline
│   ├── spotify.py     # Spotify embed scraping
│   ├── providers.py   # YouTube Music search
│   ├── monitor.py     # Playlist monitor
│   ├── lyrics.py      # lrclib integration
│   └── m3u.py         # M3U generation
├── frontend/          # Vue 3 + Vite frontend
│   └── src/
│       └── i18n/      # Translation files
├── main.py            # Entry point
├── Dockerfile
└── docker-compose.yml
```

## Adding a translation

See the [Internationalization](features/internationalization.md) page for a step-by-step guide.

## Pull requests

- Fork the repository and create a branch from `main`
- Keep changes focused — one feature or fix per PR
- Add or update tests when touching backend logic
- Run `uv run pytest` before submitting
- Open the PR against `main`

If Downtify has been useful to you, consider leaving a star on GitHub — it helps the project grow.
