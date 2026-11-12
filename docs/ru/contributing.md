---
icon: lucide/hand-heart
---

# Участие в проекте

Вклад приветствуется: полезны и сообщения об ошибках, и запросы функций, и код, и переводы. Переводить можно приложение, эту документацию или и то и другое: см. [Перевод](#translating).

## Проблемы и запросы функций

Используйте [трекер задач GitHub](https://github.com/henriquesebastiao/downtify/issues). Прежде чем открывать новую задачу, поищите существующие, чтобы избежать дублей.

Для сообщений об ошибках укажите:

- Версию Downtify
- Как вы его установили (Docker run, Docker Compose, Umbrel, …)
- Шаги воспроизведения
- Что вы ожидали и что произошло
- Любые относящиеся к делу журналы

## Настройка для разработки

### Требования

- Python 3.15+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (менеджер пакетов Python)
- ffmpeg (должен быть в `PATH`)

### Клонирование и установка

```bash
git clone https://github.com/henriquesebastiao/downtify.git
cd downtify

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Запуск в режиме разработки

```bash
# Terminal 1 — backend
uv run python main.py

# Terminal 2 — frontend dev server (hot reload)
cd frontend && npm run dev
```

Сервер разработки фронтенда проксирует API-запросы к бэкенду, поэтому достаточно открыть URL Vite (обычно `http://localhost:5173`).

### Запуск тестов

```bash
uv run pytest
```

### Сборка фронтенда для продакшена

```bash
cd frontend && npm run build
```

Скомпилированные файлы попадают в `frontend/dist/`, и их раздаёт бэкенд.

### Работа над документацией

Документация — это Markdown-файлы в `docs/`, которые собираются в статический сайт с помощью [VitePress](https://vitepress.dev/) и собственной темы (в `docs/.vitepress/`), разделяющей дизайн-токены с веб-приложением.

```bash
make doc         # dev server with hot reload
make doc-build   # production build into docs/.vitepress/dist
```

Ссылайтесь на другие страницы относительными путями `.md` (`[Тексты](lyrics.md)`), а для врезок используйте `::: tip Заголовок` … `:::` (`info`, `tip`, `warning`, `danger`). Новые страницы добавляются в боковую панель в `docs/.vitepress/nav.mjs` (с их заголовком в файле каждого языка в `docs/.vitepress/locales/`). Сборка падает на мёртвых ссылках и ссылках на несуществующие заголовки.

Английские страницы в `docs/` — источник; каждый другой язык повторяет их в собственной папке (`docs/pt-BR/…`). Меняя английскую страницу, вы не обязаны обновлять переводы — переводчики подхватят, — но запустите `npm test` в `docs/`: новой странице нужна англоязычная заглушка в каждом языке (`npm run i18n -- stubs`), и тесты скажут, если её нет.

## Структура проекта

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

## Перевод

В Downtify переводят две вещи, и вы можете взять любую из них — или обе:

| Что вы переводите | Где | Руководство |
|---------------|-------|-------|
| **Приложение** (его интерфейс) | `frontend/src/i18n/locales/<code>.js` | [Перевод приложения](features/internationalization.md#translating-the-app) |
| **Документацию** (эти страницы) | `docs/<code>/` и `docs/.vitepress/locales/<code>.mjs` | [Перевод документации](features/internationalization.md#translating-the-documentation) |

Они независимы: язык может быть в одном и ещё отсутствовать в другом, а pull request может содержать только перевод приложения, только документацию или и то и другое. Частичная работа приветствуется — непереведённые строки в приложении откатываются к английскому, а непереведённые страницы в документации остаются английскими.

Быстрый старт для документации, из `docs/`:

```bash
npm run i18n -- status pt-BR                    # coverage of a language
npm run i18n -- start pt-BR features/users.md   # copy an English page to translate
npm test                                        # check the structure of what you translated
```

Подробности — в разделе [Интернационализация](features/internationalization.md): что оставлять как есть, как добавить целый новый язык и как переводить названия кнопок в соответствии с приложением.

## Pull request'ы

- Сделайте форк репозитория и создайте ветку от `main`
- Не распыляйтесь — одна функция или исправление на PR
- Добавляйте или обновляйте тесты, когда трогаете серверную логику
- Запустите `uv run pytest` перед отправкой
- Откройте PR против `main`

Если Downtify оказался полезен, поставьте звезду на GitHub — это помогает проекту расти.
