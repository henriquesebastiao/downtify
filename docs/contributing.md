---
icon: lucide/hand-heart
---

# Contributing

Contributions are welcome — bug reports, feature requests, code and translations all help. Translations can be of the app, of this documentation, or of both: see [Translating](#translating).

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

- Python 3.15+
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

### Work on the documentation

The docs are Markdown files in `docs/`, built into a static site with [VitePress](https://vitepress.dev/) and a custom theme (in `docs/.vitepress/`) that shares its design tokens with the web app.

```bash
make doc         # dev server with hot reload
make doc-build   # production build into docs/.vitepress/dist
```

Link to other pages with relative `.md` paths (`[Lyrics](lyrics.md)`), and use `::: tip Title` … `:::` for callouts (`info`, `tip`, `warning`, `danger`). New pages go in the sidebar in `docs/.vitepress/nav.mjs` (with their title in each language's file in `docs/.vitepress/locales/`). The build fails on dead links and on links to headings that don't exist.

The English pages in `docs/` are the source; every other language mirrors them in a folder of its own (`docs/pt-BR/…`). You don't have to update the translations when you change an English page — translators follow up — but do run `npm test` in `docs/`: a new page needs an English-only stub in each language (`npm run i18n -- stubs`), and the tests say so if it's missing.

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
├── docs/              # This documentation (Markdown + VitePress site)
│   ├── <page>.md      # English, the source
│   ├── pt-BR/ …       # One folder per translated language, same file names
│   └── .vitepress/
│       └── locales/   # Each language's site text and sidebar titles
├── main.py            # Entry point
├── Dockerfile
└── docker-compose.yml
```

## Translating

Downtify has two things to translate, and you can take either one — or both:

| You translate | Where | Guide |
|---------------|-------|-------|
| **The app** (its interface) | `frontend/src/i18n/locales/<code>.js` | [Translating the app](features/internationalization.md#translating-the-app) |
| **The documentation** (these pages) | `docs/<code>/` and `docs/.vitepress/locales/<code>.mjs` | [Translating the documentation](features/internationalization.md#translating-the-documentation) |

They are independent: a language can be in one and not yet in the other, and a pull request can contain just an app translation, just documentation, or both. Partial work is welcome — untranslated strings fall back to English in the app, and untranslated pages stay in English in the documentation.

Quick start for the documentation, from `docs/`:

```bash
npm run i18n -- status pt-BR                    # coverage of a language
npm run i18n -- start pt-BR features/users.md   # copy an English page to translate
npm test                                        # check the structure of what you translated
```

See [Internationalization](features/internationalization.md) for the details: what to keep as it is, how to add a whole new language, and how to translate button names so they match the app.

## Pull requests

- Fork the repository and create a branch from `main`
- Keep changes focused — one feature or fix per PR
- Add or update tests when touching backend logic
- Run `uv run pytest` before submitting
- Open the PR against `main`

If Downtify has been useful to you, consider leaving a star on GitHub — it helps the project grow.
