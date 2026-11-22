---
layout: home
title: Downtify
titleTemplate: "Сваляне от Spotify и музикален плейър на ваш сървър"
description: "Сваляне от Spotify на ваш сървър, с вграден плейър. Поставете линк от Spotify, YouTube Music, Deezer или SoundCloud и вземете MP3 или FLAC с тагове. Без API ключове."
icon: lucide/house
hero:
  eyebrow: Самостоятелно хостван инструмент за сваляне на музика
  headline:
    - Поставете линк.
    - Вземете музиката.
  lead: Самостоятелно хостван инструмент за сваляне на музика с вграден плейър. Поставете линк от Spotify, YouTube Music, Deezer или SoundCloud и получете перфектно етикетирана библиотека, готова за слушане в браузъра, на телефона или в медийния ви сървър.
  note: Без акаунт в Spotify, без API ключове, без Premium.
  actions:
    - text: Започнете
      link: /bg/getting-started/installation/
      primary: true
    - text: Изходен код в GitHub
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Версия
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Docker изтегляния
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&label=docker%20pulls&color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Звезди в GitHub
      src: https://img.shields.io/github/stars/henriquesebastiao/downtify?style=flat&label=stars&color=1AD05C
      link: https://star-history.com/#henriquesebastiao/downtify&Date
    - alt: Лиценз
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
video:
  src: /assets/media/downtify-demo.mp4
  poster: /assets/media/downtify-demo-poster.webp
  label: 'Downtify за 44 секунди: поставете линк към плейлист, изтеглете го с едно щракване, поддържайте го синхронизиран и го слушайте със синхронизирани текстове, на компютъра и на телефона.'
why:
  - icon: link
    title: Един линк стига
    text: Поставете песен, албум, цял плейлист или изпълнител от Spotify, YouTube Music, Deezer или SoundCloud, или просто напишете какво искате да чуете. Downtify намира аудиото и го носи у дома.
    link: /bg/how-it-works/
  - icon: tag
    title: Файлове, които си струва да пазите
    text: Всеки файл носи корицата си, всички посочени изпълнители, албума, годината, номера на песента и текста, синхронизиран, когато го има. MP3, FLAC, M4A, OGG или Opus, или аудиото на източника точно както е дошло.
    link: /bg/features/download-settings/
  - icon: music
    title: Ваша собствена стрийминг услуга
    text: Пълноценен плейър в браузъра, със синхронизирани текстове, караоке, опашка, харесани песни, плейлисти и подкасти. Приложенията за Android и iOS носят библиотеката ви навсякъде, и офлайн.
    link: /bg/features/player/
  - icon: radar
    title: Настройте и забравете
    text: Следете плейлисти и изпълнители. Новите песни и новите издания се изтеглят сами, с честотата, която изберете.
    link: /bg/features/playlist-monitor/
  - icon: server
    title: Създаден за домашния ви сървър
    text: Един Docker образ за amd64 и arm64, SQLite или PostgreSQL, акаунти за всички вкъщи с единен вход по избор и плейлисти, които Jellyfin, Navidrome и Plex разпознават.
    link: /bg/getting-started/
  - icon: shield
    title: Без уловки
    text: Без API ключ за Spotify, без акаунт за разработчици, без Premium. Приложението няма реклами, статистика за използването и нищо платено. То е свободно и с отворен код.
    link: /bg/contributing/
showcase:
  - shot: now-playing
    label: Сега звучи
    caption: Текстът следва песента ред по ред, до корицата и следващите песни.
    alt: Изгледът Сега звучи на цял екран, с корицата на албума, синхронизиран текст с осветен текущ ред и опашката.
  - shot: karaoke
    label: Караоке
    caption: Големи текстове, които се запълват, докато се пее всеки ред, готови за отваряне на втори екран.
    alt: Изгледът караоке, с големи текстове, които се запълват върху движещ се фон в цветовете на корицата.
  - shot: home
    label: Начало
    caption: Поставете линк или потърсете нещо ново и продължете оттам, докъдето сте стигнали.
    alt: Началната страница, с поле за поставяне на линк или търсене, статистика на библиотеката, звучащия албум и наскоро добавени албуми.
  - shot: library
    label: Библиотека
    caption: Албуми, изпълнители, плейлисти и песни, подредени и филтрирани както искате.
    alt: Страницата Библиотека, с решетка от корици на албуми и раздели за албуми, изпълнители, плейлисти и песни.
  - shot: playlist
    label: Плейлисти
    caption: Ваши собствени плейлисти със собствена корица, за слушане, споделяне или изтегляне като ZIP.
    alt: Страница на плейлист, с корицата, бутоните и песните с албум, формат и дата на издаване.
  - shot: phones
    label: На телефона
    caption: Същото приложение на телефона ви, инсталирано от браузъра.
    alt: Downtify на три телефона, с началната страница, Сега звучи и Библиотеката.
pipeline:
  - icon: link
    title: Поставете линк
    text: Spotify, YouTube Music, Deezer или SoundCloud. Или просто напишете песен.
  - icon: search
    title: Намира аудиото
    text: Най-близкото съвпадение в YouTube Music, проверено по дължина. Други източници, ако искате.
  - icon: download
    title: Изтегля и етикетира
    text: yt-dlp и ffmpeg го изтеглят. Корицата, текстът и таговете влизат във файла.
  - icon: music
    title: Слушайте навсякъде
    text: В браузъра, на телефона или в Jellyfin, Navidrome и Plex.
quickStart:
  - text: Ръководство за инсталиране
    link: /bg/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /bg/getting-started/docker-compose/
  - text: Инсталиране с едно щракване
    link: /bg/getting-started/one-click/
apps:
  - icon: smartphone
    title: Downtify за Android
    text: Официалното приложение. Намира сървъра ви в мрежата, стриймва в оригинално качество по Wi-Fi и в по-ниско с мобилни данни, пази песни офлайн и работи с Android Auto. Все още в тестове, в GitHub Releases и Obtainium.
    link: https://github.com/henriquesebastiao/downtify-android
  - icon: tablet-smartphone
    title: Downtify за iOS
    text: Направено от член на общността за iPhone и iPad (iOS 17 или по-нова), с офлайн песни и управление от заключения екран. Публичната бета е в TestFlight.
    link: https://github.com/michaelmoskie/Downtify-IOS-Client
community:
  - text: Звезда в GitHub
    link: https://github.com/henriquesebastiao/downtify
    icon: star
    primary: true
  - text: Спонсорирайте
    link: https://github.com/sponsors/henriquesebastiao
    icon: heart
  - text: Превеждайте
    link: /bg/features/internationalization/
    icon: languages
  - text: Допринесете
    link: /bg/contributing/
    icon: git-pull-request
---

## Защо Downtify

<HomeHighlights :items="$frontmatter.why" />

## По-отблизо

<HomeShowcase :items="$frontmatter.showcase" />

## Как работи

Downtify не се нуждае от API ключ за Spotify и никога не изтегля нищо от Spotify. Чете от публични източници към какво сочи даден линк, избира аудиото в YouTube Music с най-близка дължина, изтегля го с `yt-dlp`, преобразува го с `ffmpeg` и го етикетира с `mutagen`, всичко в един Docker контейнер. YouTube се включва, когато нищо не съвпада добре, а SoundCloud, Soulseek и Deemix се присъединяват, ако ги включите. [Всяка стъпка подробно](how-it-works.md).

<HomePipeline :steps="$frontmatter.pipeline" />

## Какво можете да поставите

| Източник      | Какво работи                              | Пример                              |
| ------------- | ----------------------------------------- | ----------------------------------- |
| Spotify       | Песни, албуми, плейлисти, изпълнители     | `open.spotify.com/playlist/…`       |
| YouTube Music | Песни, албуми, плейлисти, изпълнители     | `music.youtube.com/playlist?list=…` |
| YouTube       | Видеоклипове                              | `youtube.com/watch?v=…`             |
| Deezer        | Песни, албуми, плейлисти, изпълнители     | `deezer.com/album/…`                |
| SoundCloud    | Песни                                     | `soundcloud.com/artist/track`       |
| Търсене       | Каквото бихте написали                    | `The Night Owls Do I Still Recall`  |
| CSV           | Експорти на библиотеки                    | Soundiiz, TuneMyMusic, Exportify    |

## Всичко, което прави

Всяка функция има своя страница с обяснение на всяка настройка. [Всички функции с един поглед](features/index.md).

<HomeFeatures />

## Готово за минута

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Отворете [`localhost:8000`](http://localhost:8000), влезте като **admin** с паролата **downtify** и поставете линк. Сменете тази парола веднага в **Настройки → Общи**. Музиката ви пристига в `/path/to/music`, заедно с таговете.

<HomeActions :actions="$frontmatter.quickStart" />

## Често задавани въпроси

::: details Трябва ли ми акаунт в Spotify, Premium или API ключ?
Не. Downtify чете данните за песни, албуми и плейлисти от публичните страници за вграждане (embed) на Spotify, затова не му трябват никакви идентификационни данни, а аудиото никога не идва от Spotify. Вижте [Как работи](how-it-works.md).
:::

::: details Откъде идва аудиото и какво е качеството му?
По подразбиране от YouTube Music: резултатът, чиято дължина най-добре съвпада с песента, с YouTube като резервен вариант. Изберете MP3, FLAC, M4A, OGG или Opus с желания битрейт или запазете най-доброто аудио на източника без прекодиране. Файловете без загуби идват от източници, които добавяте сами: собствения ви сървър [Soulseek (slskd)](features/slskd-navidrome.md), чиито файлове запазват оригиналния си формат, или сървър [Deemix](features/deemix.md). Вижте [Настройки за сваляне](features/download-settings.md).
:::

::: details Работи ли с Jellyfin, Navidrome или Plex?
Да. Файловете се етикетират така, както медийните сървъри очакват, подреждат се в папки `Изпълнител/Албум/`, а всеки плейлист получава стандартен M3U файл, който те разпознават. Navidrome може също да получава синхронизирани плейлисти и оценки от Deezer. Вижте [Организация на файловете](features/file-organization.md) и [M3U експорт](features/m3u-export.md).
:::

::: details Ще работи ли на Raspberry Pi или NAS?
Образът се издава за `amd64` и `arm64`, а Umbrel, CasaOS и HomeDock OS го инсталират с едно щракване. Вижте [Инсталиране с едно щракване](getting-started/one-click.md).
:::

::: details YouTube казва „Sign in to confirm you're not a bot“. Какво сега?
Качете `cookies.txt` в **Настройки → Бисквитки за YouTube**; след това Downtify сам поддържа тази сесия вписана. Ако YouTube все още ви ограничава, увеличете _Пауза между изтеглянията_, намалете _Едновременни изтегляния_ и после опитайте `DOWNTIFY_FORCE_IPV4=1`. Вижте [Отстраняване на проблеми](troubleshooting.md) и [Бисквитки за YouTube](features/youtube-cookies.md).
:::

## Вземете го със себе си

<HomeHighlights :items="$frontmatter.apps" />

Всеки друг клиент може да ползва същия API: вижте [договора за мобилни клиенти](mobile-client-contract.md).

<div class="home-cta">

## Създаден открито

Downtify е свободен и с отворен код. Над 35 души са допринесли с код, преводачи от общността са го превели на 12 езика, а много функции са започнали като идея, която някой е отворил като issue. Ако си е спечелил място на сървъра ви, дайте му звезда в GitHub, разкажете за него на приятел, който сам хоства услугите си, или спонсорирайте разработката му: това помага да се плати времето, което отива във всяка версия.

<HomeActions :actions="$frontmatter.community" />

</div>
