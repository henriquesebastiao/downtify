---
layout: home
title: Downtify
titleTemplate: "Загрузчик Spotify и музыкальный плеер на вашем сервере"
description: "Самостоятельно размещаемый загрузчик Spotify со встроенным плеером. Вставьте ссылку Spotify, YouTube Music, Deezer или SoundCloud и получите MP3 или FLAC с тегами. Без API-ключей."
icon: lucide/house
hero:
  eyebrow: Самостоятельно размещаемый загрузчик музыки
  headline:
    - Вставьте ссылку.
    - Получите музыку.
  lead: Самостоятельно размещаемый загрузчик музыки со встроенным плеером. Вставьте ссылку Spotify, YouTube Music, Deezer или SoundCloud и получите библиотеку с безупречными тегами, готовую к прослушиванию в браузере, на телефоне или в вашем медиасервере.
  note: Без аккаунта Spotify, без API-ключей, без Premium.
  actions:
    - text: Начать
      link: /getting-started/installation/
      primary: true
    - text: Исходный код на GitHub
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Релиз
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Загрузки Docker
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&label=docker%20pulls&color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Звёзды GitHub
      src: https://img.shields.io/github/stars/henriquesebastiao/downtify?style=flat&label=stars&color=1AD05C
      link: https://star-history.com/#henriquesebastiao/downtify&Date
    - alt: Лицензия
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
video:
  src: /assets/media/downtify-demo.mp4
  poster: /assets/media/downtify-demo-poster.webp
  label: 'Downtify за 44 секунды: вставьте ссылку на плейлист, скачайте его в один клик, держите его в актуальном состоянии и слушайте с синхронизированными текстами — на компьютере и на телефоне.'
why:
  - icon: link
    title: Достаточно одной ссылки
    text: Вставьте песню, альбом, целый плейлист или артиста из Spotify, YouTube Music, Deezer или SoundCloud — или просто напишите, что хотите послушать. Downtify найдёт аудио и принесёт его домой.
    link: /how-it-works/
  - icon: tag
    title: Файлы, которые стоит хранить
    text: В каждом файле есть обложка, все указанные артисты, альбом, год, номер трека и текст песни — синхронизированный, если он существует. MP3, FLAC, M4A, OGG или Opus — или исходное аудио ровно таким, каким оно пришло.
    link: /features/download-settings/
  - icon: music
    title: Ваш собственный стриминговый сервис
    text: Полноценный плеер в браузере с синхронизированными текстами, караоке, очередью, любимыми песнями, плейлистами и подкастами. Приложения для Android и iOS берут вашу библиотеку с собой, в том числе офлайн.
    link: /features/player/
  - icon: radar
    title: Настроил и забыл
    text: Следите за плейлистами и артистами. Новые песни и новые релизы скачиваются сами, по выбранному вами расписанию.
    link: /features/playlist-monitor/
  - icon: server
    title: Создан для домашнего сервера
    text: Один образ Docker для amd64 и arm64, SQLite или PostgreSQL, аккаунты для всех домашних с необязательным единым входом и плейлисты, которые подхватывают Jellyfin, Navidrome и Plex.
    link: /getting-started/
  - icon: shield
    title: Без подвохов
    text: Ни API-ключа Spotify, ни аккаунта разработчика, ни Premium. В приложении нет рекламы, аналитики и ничего платного. Оно бесплатное и с открытым исходным кодом.
    link: /contributing/
showcase:
  - shot: now-playing
    label: Сейчас играет
    caption: Текст следует за песней строка за строкой, рядом с обложкой и тем, что будет дальше.
    alt: Полноэкранный вид «Сейчас играет» с обложкой альбома, синхронизированным текстом с выделенной текущей строкой и очередью.
  - shot: karaoke
    label: Караоке
    caption: Крупный текст, заполняющийся по мере исполнения каждой строки, — можно открыть на втором экране.
    alt: Вид караоке с крупным текстом, заполняющимся на подвижном фоне в цветах обложки.
  - shot: home
    label: Главная
    caption: Вставьте ссылку или поищите что-то новое — и продолжите с того места, где остановились.
    alt: Главная страница с полем для ссылки или поиска, статистикой библиотеки, играющим альбомом и недавно добавленными альбомами.
  - shot: library
    label: Библиотека
    caption: Альбомы, артисты, плейлисты и треки, отсортированные и отфильтрованные как вам удобно.
    alt: Страница Библиотеки с сеткой обложек альбомов и вкладками альбомов, артистов, плейлистов и треков.
  - shot: playlist
    label: Плейлисты
    caption: Собственные плейлисты со своей обложкой — слушайте, делитесь или скачивайте ZIP-архивом.
    alt: Страница плейлиста с обложкой, кнопками и песнями с альбомом, форматом и датой выхода.
  - shot: phones
    label: На телефоне
    caption: То же приложение на телефоне, устанавливается из браузера.
    alt: Downtify на трёх телефонах — главная страница, «Сейчас играет» и Библиотека.
pipeline:
  - icon: link
    title: Вставьте ссылку
    text: Spotify, YouTube Music, Deezer или SoundCloud. Или просто напишите название песни.
  - icon: search
    title: Поиск аудио
    text: Ближайшее совпадение в YouTube Music, проверенное по длительности. Другие источники — по желанию.
  - icon: download
    title: Загрузка и теги
    text: yt-dlp и ffmpeg скачивают его. Обложка, текст и теги записываются в файл.
  - icon: music
    title: Слушайте где угодно
    text: В браузере, на телефоне или в Jellyfin, Navidrome и Plex.
quickStart:
  - text: Руководство по установке
    link: /getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /getting-started/docker-compose/
  - text: Установка в один клик
    link: /getting-started/one-click/
apps:
  - icon: smartphone
    title: Downtify для Android
    text: Официальное приложение. Находит ваш сервер в сети, стримит в исходном качестве по Wi-Fi и в меньшем — по мобильной сети, хранит песни офлайн и работает с Android Auto. Пока в тестировании, на GitHub Releases и в Obtainium.
    link: https://github.com/henriquesebastiao/downtify-android
  - icon: tablet-smartphone
    title: Downtify для iOS
    text: Создано участником сообщества для iPhone и iPad (iOS 17 или новее), с офлайн-песнями и управлением с экрана блокировки. Публичная бета — в TestFlight.
    link: https://github.com/michaelmoskie/Downtify-IOS-Client
community:
  - text: Звезда на GitHub
    link: https://github.com/henriquesebastiao/downtify
    icon: star
    primary: true
  - text: Спонсировать
    link: https://github.com/sponsors/henriquesebastiao
    icon: heart
  - text: Переводить
    link: /features/internationalization/
    icon: languages
  - text: Участвовать
    link: /contributing/
    icon: git-pull-request
---

## Почему Downtify

<HomeHighlights :items="$frontmatter.why" />

## Поближе

<HomeShowcase :items="$frontmatter.showcase" />

## Как это работает

Downtify не нужен API-ключ Spotify, и он никогда ничего не скачивает из Spotify. Он узнаёт, на что указывает ссылка, из публичных источников, выбирает аудио в YouTube Music, длительность которого совпадает лучше всего, скачивает его через `yt-dlp`, конвертирует через `ffmpeg` и записывает теги через `mutagen` — всё в одном Docker-контейнере. Когда хорошего совпадения нет, подключается YouTube, а SoundCloud, Soulseek и Deemix — если вы их включите. [Каждый шаг подробно](how-it-works.md).

<HomePipeline :steps="$frontmatter.pipeline" />

## Что можно вставить

| Источник      | Что работает                       | Пример                              |
| ------------- | ---------------------------------- | ----------------------------------- |
| Spotify       | Треки, альбомы, плейлисты, артисты | `open.spotify.com/playlist/…`       |
| YouTube Music | Песни, альбомы, плейлисты, артисты | `music.youtube.com/playlist?list=…` |
| YouTube       | Видео                              | `youtube.com/watch?v=…`             |
| Deezer        | Треки, альбомы, плейлисты, артисты | `deezer.com/album/…`                |
| SoundCloud    | Треки                              | `soundcloud.com/artist/track`       |
| Поиск         | Что угодно, что вы бы написали     | `The Night Owls Do I Still Recall`  |
| CSV           | Экспорт библиотеки                 | Soundiiz, TuneMyMusic, Exportify    |

## Всё, что он умеет

У каждой возможности есть своя страница, где объяснена каждая настройка. [Все возможности одним списком](features/index.md).

<HomeFeatures />

## Запуск за минуту

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Откройте [`localhost:8000`](http://localhost:8000), войдите как **admin** с паролем **downtify** и вставьте ссылку. Сразу смените этот пароль в **Настройки → Общие**. Ваша музыка попадёт в `/path/to/music` — со всеми тегами.

<HomeActions :actions="$frontmatter.quickStart" />

## Частые вопросы

::: details Нужен ли аккаунт Spotify, Premium или API-ключ?
Нет. Downtify читает сведения о треках, альбомах и плейлистах с публичных embed-страниц Spotify, так что никакие учётные данные ему не нужны, а аудио никогда не берётся из Spotify. См. [Как это работает](how-it-works.md).
:::

::: details Откуда берётся аудио и насколько оно хорошее?
По умолчанию из YouTube Music: результат, длительность которого лучше всего совпадает с песней, а запасной вариант — YouTube. Выберите MP3, FLAC, M4A, OGG или Opus с нужным битрейтом или сохраните лучшее аудио источника без перекодирования. Файлы без потерь приходят из источников, которые вы добавляете сами: вашего собственного сервера [Soulseek (slskd)](features/slskd-navidrome.md), файлы которого сохраняют исходный формат, или сервера [Deemix](features/deemix.md). См. [Настройки загрузок](features/download-settings.md).
:::

::: details Работает ли он с Jellyfin, Navidrome или Plex?
Да. Файлы размечены так, как ожидают медиасерверы, разложены по папкам `Artist/Album/`, и для каждого плейлиста создаётся стандартный файл M3U, который они подхватывают. Navidrome также может получать синхронизированные плейлисты и рейтинги из Deezer. См. [Организация файлов](features/file-organization.md) и [Экспорт M3U](features/m3u-export.md).
:::

::: details Запустится ли он на Raspberry Pi или NAS?
Образ собран и для `amd64`, и для `arm64`, а Umbrel, CasaOS и HomeDock OS устанавливают его в один клик. См. [Установка в один клик](getting-started/one-click.md).
:::

::: details YouTube пишет «Sign in to confirm you're not a bot». Что делать?
Загрузите `cookies.txt` в **Настройки → Куки YouTube**; затем Downtify сам поддерживает этот сеанс. Если YouTube всё равно ограничивает вас, увеличьте _Паузу между загрузками_, уменьшите _Параллельные загрузки_, а затем попробуйте `DOWNTIFY_FORCE_IPV4=1`. См. [Решение проблем](troubleshooting.md) и [Куки YouTube](features/youtube-cookies.md).
:::

## Возьмите с собой

<HomeHighlights :items="$frontmatter.apps" />

Любой другой клиент может использовать тот же API: см. [контракт мобильного клиента](mobile-client-contract.md).

<div class="home-cta">

## Сделано открыто

Downtify бесплатный и с открытым исходным кодом. Код писали больше 35 человек, переводчики из сообщества перевели его на 13 языков, а многие возможности начались с идеи, которую кто-то открыл как issue. Если он заслужил место на вашем сервере, поставьте ему звезду на GitHub, расскажите другу, который держит свой сервер, или поддержите разработку: это помогает оплачивать время, которое уходит на каждый релиз.

<HomeActions :actions="$frontmatter.community" />

</div>
