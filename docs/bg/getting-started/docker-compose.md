---
icon: lucide/file-code
---

# Docker Compose

Docker Compose е препоръчителният начин да пускате Downtify при постоянни домашни сървърни настройки. Улеснява обновяванията, архивите и промените в конфигурацията.

## Минимална настройка

Създайте файл `docker-compose.yml`. Той пуска Downtify върху PostgreSQL, като базата данни е в услуга `postgres` до него (вижте [База данни](../database.md)):

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

Задайте `POSTGRES_PASSWORD` във файл `.env` до файла Compose преди първото стартиране (вижте [Променливи на средата](environment-variables.md#database)). За да запазите SQLite файловете, премахнете `DATABASE_URL`, услугата `postgres` и блока `depends_on`.

Стартирайте го:

```bash
docker compose up -d
```

Отворете **[http://localhost:8000](http://localhost:8000)**.

## С slskd (Soulseek)

За да ползвате [slskd като аудио източник](../features/slskd-navidrome.md), монтирайте в Downtify и папката за изтегляния на slskd — **същата папка на хоста**, в която пише вашият slskd контейнер:

```yaml
services:
  downtify:
    # ...
    volumes:
      - ./downloads:/downloads
      - /path/to/slskd/downloads:/slskd
      - downtify_data:/data
```

След това в **Настройки → Аудио източници → slskd** включете slskd, въведете неговия URL (напр. `http://slskd:5030`, когато двата контейнера споделят Docker мрежа) и API ключа и задайте папката за изтегляне на `/slskd`.

## Съществуващи папки с музика

За да вземе Библиотеката колекция, която вече пазите на хоста, [монтирайте я](../features/external-library.md) по същия начин и въведете пътя **в контейнера** в **Настройки → Библиотека**:

```yaml
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

## Намиране на сървъра от приложенията

[Мобилните приложения](../features/mobile-apps.md#finding-the-server-on-your-network) изброяват Downtify сървърите във вашата мрежа чрез mDNS. В стандартната bridge мрежа на Docker това обявяване никога не напуска Docker, затова телефоните не го виждат. За да се показва, пуснете контейнера в мрежата на хоста — съпоставянето `ports:` тогава не важи и Downtify слуша директно на `DOWNTIFY_PORT`:

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

Иначе просто въведете адреса на сървъра в приложението (`http://<IP на хоста>:8000`); нищо друго не зависи от откриването.

## Собствен порт

Ако порт 8000 вече е зает, съпоставете друг порт на хоста и задайте променливата на средата `DOWNTIFY_PORT`, така че контейнерът да слуша вътрешно на същия порт:

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

Можете да изберете порта и в **Настройки → Сървър → Порт**, вместо да задавате `DOWNTIFY_PORT` (която, когато е зададена, има предимство пред Настройките). В стандартната bridge мрежа променете съпоставянето `ports:` на същия порт и пресъздайте контейнера — вижте [Смяна на порта](../features/server.md#changing-the-port).

## С персонализиран DNS (препоръчително)

Някои интернет доставчици и корпоративни мрежи блокират YouTube. Добавянето на изрични DNS резолвъри подобрява надеждността:

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

## Обновяване

```bash
docker compose pull
docker compose up -d
```

Музиката и настройките ви се запазват в томовете.

## Томове

| Път във файла compose | Предназначение |
|------------------------------|---------|
| `./downloads:/downloads` | Изтеглени аудио файлове (локална директория) |
| `downtify_data:/data` | Настройки, кешове и SQLite файловете (именуван том) |
| `pgdata:/var/lib/postgresql/data` | PostgreSQL базата данни, в услугата `postgres` |

Можете да замените именувания том с локален път (`./data:/data`), ако предпочитате сами да го управлявате.
