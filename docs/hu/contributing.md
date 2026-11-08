---
icon: lucide/hand-heart
---

# Közreműködés

A hozzájárulásokat szívesen fogadjuk — hibajelentések, funkciókérések, kód és fordítások mind segítenek. A fordítások szólhatnak az alkalmazásról, erről a dokumentációról, vagy mindkettőről: lásd: [Fordítás](#translating).

## Issue-k és funkciókérések

Használd a [GitHub issue-követőt](https://github.com/henriquesebastiao/downtify/issues). Új issue megnyitása előtt keress a meglévők között a duplikátumok elkerülése végett.

Hibajelentésekhez add meg:

- A Downtify verzióját
- Hogyan telepítetted (Docker run, Docker Compose, Umbrel, …)
- A reprodukálás lépéseit
- Mit vártál, és mi történt
- Az esetleges releváns naplókat

## Fejlesztői környezet

### Előfeltételek

- Python 3.15+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (Python-csomagkezelő)
- ffmpeg (a `PATH`-on kell lennie)

### Klónozás és telepítés

```bash
git clone https://github.com/henriquesebastiao/downtify.git
cd downtify

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Futtatás fejlesztői módban

```bash
# Terminal 1 — backend
uv run python main.py

# Terminal 2 — frontend dev server (hot reload)
cd frontend && npm run dev
```

A frontend fejlesztői szervere az API-kéréseket a backendhez továbbítja, így elég a Vite URL-jét megnyitnod (általában `http://localhost:5173`).

### A tesztek futtatása

```bash
uv run pytest
```

### A frontend építése éles használatra

```bash
cd frontend && npm run build
```

A lefordított fájlok a `frontend/dist/` mappába kerülnek, és a backend szolgálja ki őket.

### Munka a dokumentáción

A dokumentáció Markdown-fájlok a `docs/` mappában, amelyeket a [VitePress](https://vitepress.dev/) és egy egyedi téma (a `docs/.vitepress/` mappában) épít statikus oldallá; a téma a tervezési tokenjeit megosztja a webalkalmazással.

```bash
make doc         # dev server with hot reload
make doc-build   # production build into docs/.vitepress/dist
```

Más oldalakra relatív `.md` útvonalakkal hivatkozz (`[Dalszövegek](lyrics.md)`), és a kiemelő dobozokhoz használd a `::: tip Cím` … `:::` szerkezetet (`info`, `tip`, `warning`, `danger`). Az új oldalak az oldalsávba a `docs/.vitepress/nav.mjs` fájlban kerülnek (a címükkel együtt az egyes nyelvek fájljában a `docs/.vitepress/locales/` alatt). Az építés elbukik holt hivatkozásokon és nem létező címsorokra mutató hivatkozásokon.

A `docs/` angol oldalai a forrás; minden más nyelv a saját mappájában tükrözi őket (`docs/pt-BR/…`). Egy angol oldal módosításakor nem kell a fordításokat frissítened — a fordítók követik —, de futtasd az `npm test` parancsot a `docs/` mappában: egy új oldalhoz minden nyelvben kell egy csak angol vázlat (`npm run i18n -- stubs`), és a tesztek jelzik, ha hiányzik.

## A projekt szerkezete

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

## Fordítás

A Downtifynak két lefordítandó dolga van, és bármelyiket — vagy mindkettőt — elvállalhatod:

| Amit fordítasz | Hol | Útmutató |
|---------------|-------|-------|
| **Az alkalmazás** (a felülete) | `frontend/src/i18n/locales/<code>.js` | [Az alkalmazás fordítása](features/internationalization.md#translating-the-app) |
| **A dokumentáció** (ezek az oldalak) | `docs/<code>/` és `docs/.vitepress/locales/<code>.mjs` | [A dokumentáció fordítása](features/internationalization.md#translating-the-documentation) |

Függetlenek: egy nyelv lehet az egyikben, és a másikban még nem, egy pull request pedig tartalmazhat csak alkalmazásfordítást, csak dokumentációt, vagy mindkettőt. A részleges munka is szívesen látott — a le nem fordított szövegek az alkalmazásban angolra esnek vissza, a le nem fordított oldalak pedig a dokumentációban angolul maradnak.

Gyors kezdés a dokumentációhoz, a `docs/` mappából:

```bash
npm run i18n -- status pt-BR                    # coverage of a language
npm run i18n -- start pt-BR features/users.md   # copy an English page to translate
npm test                                        # check the structure of what you translated
```

A részletekért lásd: [Nemzetköziesítés](features/internationalization.md): mit kell változatlanul hagyni, hogyan adj hozzá egy teljesen új nyelvet, és hogyan fordítsd a gombneveket úgy, hogy egyezzenek az alkalmazáséval.

## Pull requestek

- Forkold a tárolót, és hozz létre egy ágat a `main`-ből
- Tartsd fókuszban a változtatásokat — egy PR egy funkció vagy javítás
- Backend-logika módosításakor adj hozzá vagy frissíts teszteket
- Beküldés előtt futtasd az `uv run pytest` parancsot
- A PR-t a `main` ellen nyisd meg

Ha a Downtify hasznos volt számodra, fontold meg, hogy hagysz egy csillagot a GitHubon — ez segít a projektnek növekedni.
