---
icon: lucide/hand-heart
---

# Mitwirken

Beiträge sind willkommen — Fehlerberichte, Funktionswünsche, Code und Übersetzungen helfen alle. Übersetzungen können die App, diese Dokumentation oder beides betreffen: siehe [Übersetzen](#translating).

## Issues und Funktionswünsche

Nutze den [GitHub-Issue-Tracker](https://github.com/henriquesebastiao/downtify/issues). Suche vor dem Eröffnen einer neuen Issue unter den bestehenden, um Dubletten zu vermeiden.

Gib bei Fehlerberichten an:

- Downtify-Version
- Wie du es installiert hast (Docker run, Docker Compose, Umbrel, …)
- Schritte zur Reproduktion
- Was du erwartet hast und was passiert ist
- Relevante Logs

## Entwicklungsumgebung

### Voraussetzungen

- Python 3.15+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (Python-Paketmanager)
- ffmpeg (muss im `PATH` liegen)

### Klonen und installieren

```bash
git clone https://github.com/henriquesebastiao/downtify.git
cd downtify

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Im Entwicklungsmodus starten

```bash
# Terminal 1 — backend
uv run python main.py

# Terminal 2 — frontend dev server (hot reload)
cd frontend && npm run dev
```

Der Frontend-Entwicklungsserver leitet API-Anfragen an das Backend weiter, du musst also nur die Vite-URL öffnen (normalerweise `http://localhost:5173`).

### Die Tests ausführen

```bash
uv run pytest
```

### Das Frontend für die Produktion bauen

```bash
cd frontend && npm run build
```

Die kompilierten Dateien landen in `frontend/dist/` und werden vom Backend ausgeliefert.

### An der Dokumentation arbeiten

Die Dokumentation besteht aus Markdown-Dateien in `docs/`, die mit [VitePress](https://vitepress.dev/) und einem eigenen Theme (in `docs/.vitepress/`), das seine Design-Tokens mit der Web-App teilt, zu einer statischen Seite gebaut werden.

```bash
make doc         # dev server with hot reload
make doc-build   # production build into docs/.vitepress/dist
```

Verlinke andere Seiten mit relativen `.md`-Pfaden (`[Songtexte](lyrics.md)`) und nutze `::: tip Titel` … `:::` für Hinweisboxen (`info`, `tip`, `warning`, `danger`). Neue Seiten kommen in `docs/.vitepress/nav.mjs` in die Seitenleiste (mit ihrem Titel in der Datei jeder Sprache in `docs/.vitepress/locales/`). Der Build schlägt bei toten Links und bei Links auf nicht vorhandene Überschriften fehl.

Die englischen Seiten in `docs/` sind die Quelle; jede andere Sprache spiegelt sie in einem eigenen Ordner (`docs/pt-BR/…`). Du musst die Übersetzungen nicht aktualisieren, wenn du eine englische Seite änderst — Übersetzer ziehen nach —, aber führe `npm test` in `docs/` aus: Eine neue Seite braucht in jeder Sprache einen nur englischen Platzhalter (`npm run i18n -- stubs`), und die Tests melden, wenn er fehlt.

## Projektstruktur

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

## Übersetzen

Downtify hat zwei Dinge zu übersetzen, und du kannst eines davon übernehmen — oder beide:

| Du übersetzt | Wo | Anleitung |
|---------------|-------|-------|
| **Die App** (ihre Oberfläche) | `frontend/src/i18n/locales/<code>.js` | [Die App übersetzen](features/internationalization.md#translating-the-app) |
| **Die Dokumentation** (diese Seiten) | `docs/<code>/` und `docs/.vitepress/locales/<code>.mjs` | [Die Dokumentation übersetzen](features/internationalization.md#translating-the-documentation) |

Sie sind unabhängig: Eine Sprache kann in der einen sein und noch nicht in der anderen, und ein Pull Request kann nur eine App-Übersetzung, nur Dokumentation oder beides enthalten. Teilarbeit ist willkommen — unübersetzte Texte fallen in der App auf Englisch zurück, und unübersetzte Seiten bleiben in der Dokumentation Englisch.

Schnellstart für die Dokumentation, aus `docs/`:

```bash
npm run i18n -- status pt-BR                    # coverage of a language
npm run i18n -- start pt-BR features/users.md   # copy an English page to translate
npm test                                        # check the structure of what you translated
```

Siehe [Internationalisierung](features/internationalization.md) für die Details: was unverändert bleibt, wie du eine ganz neue Sprache hinzufügst und wie du Schaltflächennamen so übersetzt, dass sie zur App passen.

## Pull Requests

- Forke das Repository und erstelle einen Branch von `main`
- Halte die Änderungen fokussiert — eine Funktion oder ein Fix pro PR
- Füge Tests hinzu oder aktualisiere sie, wenn du Backend-Logik anfasst
- Führe vor dem Einreichen `uv run pytest` aus
- Eröffne den PR gegen `main`

Wenn Downtify dir nützlich war, denk darüber nach, einen Stern auf GitHub zu hinterlassen — das hilft dem Projekt zu wachsen.
