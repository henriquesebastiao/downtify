---
icon: lucide/file-code
---

# Docker Compose

Для постоянной установки на домашнем сервере рекомендуется запускать Downtify через Docker Compose: обновления, резервные копии и смена настроек становятся проще.

## Минимальная настройка

Создайте файл `docker-compose.yml`. Он запускает Downtify на PostgreSQL, с базой данных в сервисе `postgres` рядом (см. [База данных](../database.md)):

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

Перед первым запуском задайте `POSTGRES_PASSWORD` в файле `.env` рядом с файлом Compose (см. [Переменные окружения](environment-variables.md#database)). Чтобы вместо этого оставить файлы SQLite, уберите `DATABASE_URL`, сервис `postgres` и блок `depends_on`.

Запустите:

```bash
docker compose up -d
```

Откройте **[http://localhost:8000](http://localhost:8000)**.

## С slskd (Soulseek)

Чтобы использовать [slskd как аудио источник](../features/slskd-navidrome.md), смонтируйте папку загрузок slskd и в Downtify — **ту же папку хоста**, куда пишет контейнер slskd:

```yaml
services:
  downtify:
    # ...
    volumes:
      - ./downloads:/downloads
      - /path/to/slskd/downloads:/slskd
      - downtify_data:/data
```

Затем в **Настройки → Аудио источники → slskd** включите slskd, укажите его URL (например, `http://slskd:5030`, если оба контейнера в одной сети Docker) и API-ключ, а в качестве папки загрузок задайте `/slskd`.

## Существующие папки с музыкой

Чтобы Библиотека увидела коллекцию, которая уже есть на хосте, [смонтируйте её](../features/external-library.md) так же и введите **путь внутри контейнера** в **Настройки → Библиотека**:

```yaml
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

## Как приложения находят сервер

[Мобильные приложения](../features/mobile-apps.md#finding-the-server-on-your-network) находят серверы Downtify в вашей сети через mDNS. В стандартной сети Docker (bridge) такое объявление не покидает Docker, и телефоны его не видят. Чтобы оно было видно, запустите контейнер в сети хоста — тогда правило `ports:` больше не действует, и Downtify слушает порт прямо из `DOWNTIFY_PORT`:

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

Иначе просто введите адрес сервера в приложении (`http://<IP хоста>:8000`): больше от обнаружения ничего не зависит.

## Другой порт

Если порт 8000 уже занят, отдайте другому порту хоста и задайте переменную окружения `DOWNTIFY_PORT`, чтобы контейнер слушал внутри тот же порт:

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

Порт можно выбрать и в **Настройки → Сервер → Порт** вместо `DOWNTIFY_PORT` (которая при задании перебивает Настройки). В стандартной сети bridge измените правило `ports:` на тот же порт и пересоздайте контейнер — см. [Смена порта](../features/server.md#changing-the-port).

## С явным DNS (рекомендуется)

Некоторые провайдеры и корпоративные сети блокируют YouTube. Явные DNS-резолверы делают работу надёжнее:

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

## Обновление

```bash
docker compose pull
docker compose up -d
```

Музыка и настройки остаются в томах.

`latest` всегда следует за новейшим релизом. Каждый релиз также публикуется под полной версией и под своими минорной и мажорной линиями, так что `ghcr.io/henriquesebastiao/downtify:3.12.0` никогда не меняется, `:3.12` получает только исправления этой линии, а `:3` переходит на каждый релиз 3.x. Те же теги есть на Docker Hub (`henriquesebastiao/downtify`).

## Тома

| Путь в compose-файле | Назначение |
|------------------------------|---------|
| `./downloads:/downloads` | Скачанные аудиофайлы (локальная папка) |
| `downtify_data:/data` | Настройки, кэши и файлы SQLite (именованный том) |
| `pgdata:/var/lib/postgresql/data` | База данных PostgreSQL, в сервисе `postgres` |

Именованный том можно заменить локальным путём (`./data:/data`), если хотите управлять им сами.
