---
icon: lucide/download
---

# Установка

Быстрее всего запустить Downtify одной командой `docker run`. На хосте не нужны ни Python, ни Node.js, ни другие системные зависимости — всё уже внутри образа.

## Предварительные требования

- [Docker](https://docs.docker.com/get-docker/) — установленный и запущенный

## Docker run

```bash
docker run -d \
  --name downtify \
  -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Замените `/path/to/music` на папку, куда должна сохраняться музыка.

Когда контейнер запустится, откройте в браузере **[http://localhost:8000](http://localhost:8000)**.

## Тома

| Том | Назначение |
|--------|---------|
| `/downloads` | Скачанные аудиофайлы |
| `/data` | База данных приложения и постоянные настройки |

Оба тома сохраняются при перезапусках и обновлениях контейнера. В `/downloads` можно смонтировать любую папку хоста или назвать том Docker.

## Другой порт

Чтобы открыть Downtify на другом порту хоста, измените левую часть `-p`:

```bash
docker run -d \
  --name downtify \
  -p 9090:8000 \           # host:container
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Затем откройте **[http://localhost:9090](http://localhost:9090)**.

## Обновление

Скачайте свежий образ и пересоздайте контейнер:

```bash
docker pull ghcr.io/henriquesebastiao/downtify
docker stop downtify && docker rm downtify
docker run -d --name downtify -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Музыка и настройки остаются в томах.

## Что дальше?

- **[Docker Compose](docker-compose.md)** — удобнее для долгой работы с контейнером
- **[Переменные окружения](environment-variables.md)** — настройка защиты от ботов и других тонких параметров
- **[Настройки загрузок](../features/download-settings.md)** — выберите формат и битрейт
