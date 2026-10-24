---
icon: lucide/hand-heart
---

# Принос

Приносите са добре дошли — доклади за грешки, заявки за функции, код и преводи помагат. Преводите могат да са на приложението, на тази документация или и на двете: вижте [Превод](#translating).

## Проблеми и заявки за функции

Ползвайте [системата за проследяване на проблеми в GitHub](https://github.com/henriquesebastiao/downtify/issues). Преди да отворите нов проблем, потърсете сред съществуващите, за да избегнете дубликати.

В докладите за грешки включете:

- Версия на Downtify
- Как сте го инсталирали (Docker run, Docker Compose, Umbrel, …)
- Стъпки за възпроизвеждане
- Какво сте очаквали и какво се е случило
- Всички относими логове

## Среда за разработка

### Предварителни изисквания

- Python 3.15+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (мениджър на пакети за Python)
- ffmpeg (трябва да е в `PATH`)

### Клониране и инсталиране

```bash
git clone https://github.com/henriquesebastiao/downtify.git
cd downtify

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Стартиране в режим на разработка

```bash
# Terminal 1 — backend
uv run python main.py

# Terminal 2 — frontend dev server (hot reload)
cd frontend && npm run dev
```

Сървърът за разработка на frontend препраща API заявките към backend, така че трябва само да отворите URL адреса на Vite (обикновено `http://localhost:5173`).

### Стартиране на тестовете

```bash
uv run pytest
```

### Изграждане на frontend за продукция

```bash
cd frontend && npm run build
```

Компилираните файлове попадат във `frontend/dist/` и се обслужват от backend.

### Работа по документацията

Документацията са Markdown файлове в `docs/`, изградени в статичен сайт с [VitePress](https://vitepress.dev/) и собствена тема (в `docs/.vitepress/`), която споделя дизайн токените си с уеб приложението.

```bash
make doc         # dev server with hot reload
make doc-build   # production build into docs/.vitepress/dist
```

Правете връзки към други страници с относителни `.md` пътища (`[Текстове](lyrics.md)`) и ползвайте `::: tip Заглавие` … `:::` за кутиите (`info`, `tip`, `warning`, `danger`). Новите страници се добавят в страничната лента в `docs/.vitepress/nav.mjs` (със заглавието им във файла на всеки език в `docs/.vitepress/locales/`). Изграждането се проваля при мъртви връзки и при връзки към заглавия, които не съществуват.

Английските страници в `docs/` са източникът; всеки друг език ги отразява в собствена папка (`docs/pt-BR/…`). Не е нужно да обновявате преводите, когато променяте английска страница — преводачите наваксват —, но стартирайте `npm test` в `docs/`: нова страница се нуждае от заготовка само на английски във всеки език (`npm run i18n -- stubs`), а тестовете казват, ако липсва.

## Структура на проекта

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

## Превод

Downtify има две неща за превеждане и можете да вземете което и да е — или и двете:

| Превеждате | Къде | Ръководство |
|---------------|-------|-------|
| **Приложението** (интерфейса му) | `frontend/src/i18n/locales/<code>.js` | [Превод на приложението](features/internationalization.md#translating-the-app) |
| **Документацията** (тези страници) | `docs/<code>/` и `docs/.vitepress/locales/<code>.mjs` | [Превод на документацията](features/internationalization.md#translating-the-documentation) |

Те са независими: един език може да е в едното и още да не е в другото, а pull request може да съдържа само превод на приложението, само документация или и двете. Частичната работа е добре дошла — непреведените низове в приложението се връщат към английски, а непреведените страници в документацията остават на английски.

Бърз старт за документацията, от `docs/`:

```bash
npm run i18n -- status pt-BR                    # coverage of a language
npm run i18n -- start pt-BR features/users.md   # copy an English page to translate
npm test                                        # check the structure of what you translated
```

Вижте [Интернационализация](features/internationalization.md) за подробностите: какво да се запази както е, как да добавите изцяло нов език и как да превеждате имената на бутони, за да съвпадат с тези в приложението.

## Pull requests

- Направете fork на хранилището и създайте клон от `main`
- Дръжте промените фокусирани — една функция или поправка на PR
- Добавяйте или обновявайте тестове, когато пипате логиката на backend
- Стартирайте `uv run pytest` преди изпращане
- Отворете PR към `main`

Ако Downtify ви е бил полезен, помислете да оставите звезда в GitHub — това помага на проекта да расте.
