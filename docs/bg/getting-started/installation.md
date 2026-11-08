---
icon: lucide/download
---

# Инсталиране

Най-бързият начин да пуснете Downtify е с една команда `docker run`. Не са нужни Python, Node.js или други системни зависимости на хоста — всичко е в образа.

## Предварителни изисквания

- Инсталиран и работещ [Docker](https://docs.docker.com/get-docker/)

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

Сменете `/path/to/music` с директорията, в която искате да се записва музиката ви.

Когато контейнерът стартира, отворете **[http://localhost:8000](http://localhost:8000)** в браузъра си.

## Томове

| Том | Предназначение |
|--------|---------|
| `/downloads` | Изтеглени аудио файлове |
| `/data` | База данни на приложението и постоянни настройки |

И двата тома се запазват при рестарти и надграждания на контейнера. Томът `/downloads` може да е всяка директория на вашата машина или именуван Docker том.

## Собствен порт

За да направите Downtify достъпен на друг порт на хоста, променете лявата страна на `-p`:

```bash
docker run -d \
  --name downtify \
  -p 9090:8000 \           # хост:контейнер
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

След това отворете **[http://localhost:9090](http://localhost:9090)**.

## Обновяване

Изтеглете най-новия образ и пресъздайте контейнера:

```bash
docker pull ghcr.io/henriquesebastiao/downtify
docker stop downtify && docker rm downtify
docker run -d --name downtify -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Музиката и настройките ви се запазват в томовете.

## Какво следва?

- **[Docker Compose](docker-compose.md)** — по-лесен начин за управление на контейнера в дългосрочен план
- **[Променливи на средата](environment-variables.md)** — настройте anti-bot поведението и други разширени опции
- **[Настройки за сваляне](../features/download-settings.md)** — изберете формат и битрейт
