---
layout: home
title: Downtify
titleTemplate: "Descargador de Spotify y reproductor de música autoalojado"
description: "Descargador de Spotify autoalojado con reproductor. Pega un enlace de Spotify, YouTube Music, Deezer o SoundCloud y obtén MP3 o FLAC etiquetados. Sin claves de API."
icon: lucide/house
hero:
  eyebrow: Descargador de música autoalojado
  headline:
    - Pega un enlace.
    - Llévate la música.
  lead: Un descargador de música autoalojado con reproductor integrado. Pega un enlace de Spotify, YouTube Music, Deezer o SoundCloud y obtén una biblioteca perfectamente etiquetada, lista para sonar en el navegador, en el móvil o en tu servidor multimedia.
  note: Sin cuenta de Spotify, sin claves de API, sin Premium.
  actions:
    - text: Empezar
      link: /es/getting-started/installation/
      primary: true
    - text: Código fuente en GitHub
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Versión
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Descargas de Docker
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&label=docker%20pulls&color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Estrellas en GitHub
      src: https://img.shields.io/github/stars/henriquesebastiao/downtify?style=flat&label=stars&color=1AD05C
      link: https://star-history.com/#henriquesebastiao/downtify&Date
    - alt: Licencia
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
video:
  src: /assets/media/downtify-demo.mp4
  poster: /assets/media/downtify-demo-poster.webp
  label: 'Downtify en 44 segundos: pega el enlace de una playlist, descárgala con un clic, mantenla sincronizada y escúchala con letras sincronizadas, en el ordenador y en el móvil.'
why:
  - icon: link
    title: Con un enlace basta
    text: Pega una canción, un álbum, una playlist entera o un artista de Spotify, YouTube Music, Deezer o SoundCloud, o simplemente escribe lo que quieres escuchar. Downtify encuentra el audio y se lo trae a casa.
    link: /es/how-it-works/
  - icon: tag
    title: Archivos que vale la pena guardar
    text: Cada archivo lleva su portada, todos los artistas acreditados, el álbum, el año, el número de pista y la letra, sincronizada cuando existe. MP3, FLAC, M4A, OGG u Opus, o el audio de la fuente tal cual llegó.
    link: /es/features/download-settings/
  - icon: music
    title: Tu propio servicio de streaming
    text: Un reproductor completo en el navegador, con letras sincronizadas, karaoke, cola, canciones que te gustan, playlists y podcasts. Las apps para Android e iOS se llevan tu biblioteca contigo, también sin conexión.
    link: /es/features/player/
  - icon: radar
    title: Configúralo y olvídate
    text: Sigue playlists y artistas. Las canciones y los lanzamientos nuevos se descargan solos, con la frecuencia que elijas.
    link: /es/features/playlist-monitor/
  - icon: server
    title: Hecho para tu servidor doméstico
    text: Una imagen de Docker para amd64 y arm64, SQLite o PostgreSQL, cuentas para todos en casa con inicio de sesión único opcional y playlists que Jellyfin, Navidrome y Plex reconocen.
    link: /es/getting-started/
  - icon: shield
    title: Sin ataduras
    text: Sin clave de API de Spotify, sin cuenta de desarrollador, sin Premium. La app no tiene anuncios, ni analíticas, ni nada de pago. Es libre y de código abierto.
    link: /es/contributing/
showcase:
  - shot: now-playing
    label: Reproduciendo
    caption: La letra sigue a la canción, línea a línea, junto a la portada y lo que suena después.
    alt: La vista a pantalla completa de Reproduciendo, con la portada del álbum, la letra sincronizada con la línea actual resaltada y la cola.
  - shot: karaoke
    label: Karaoke
    caption: Letras grandes que se rellenan a medida que se canta cada línea, listas para abrirse en una segunda pantalla.
    alt: La vista de karaoke, con letras grandes que se rellenan sobre un fondo en movimiento con los colores de la portada.
  - shot: home
    label: Inicio
    caption: Pega un enlace o busca algo nuevo, y sigue donde lo dejaste.
    alt: La página de inicio, con un cuadro para pegar un enlace o buscar, las estadísticas de la biblioteca, el álbum que suena y los álbumes añadidos recientemente.
  - shot: library
    label: Biblioteca
    caption: Álbumes, artistas, playlists y canciones, ordenados y filtrados a tu manera.
    alt: La página Biblioteca, con una cuadrícula de portadas de álbumes y pestañas para álbumes, artistas, playlists y canciones.
  - shot: playlist
    label: Playlists
    caption: Tus propias playlists, con su propia portada, para escuchar, compartir o descargar como ZIP.
    alt: Una página de playlist, con su portada, sus botones y sus canciones con álbum, formato y fecha de lanzamiento.
  - shot: phones
    label: En el móvil
    caption: La misma app en tu móvil, instalable desde el navegador.
    alt: Downtify en tres móviles, con la página de inicio, Reproduciendo y la Biblioteca.
pipeline:
  - icon: link
    title: Pega un enlace
    text: Spotify, YouTube Music, Deezer o SoundCloud. O simplemente escribe una canción.
  - icon: search
    title: Encuentra el audio
    text: La coincidencia más cercana en YouTube Music, comprobada por la duración. Otras fuentes, si las quieres.
  - icon: download
    title: Descarga y etiqueta
    text: yt-dlp y ffmpeg lo descargan. La portada, la letra y las etiquetas van dentro del archivo.
  - icon: music
    title: Escucha donde quieras
    text: En el navegador, en el móvil o en Jellyfin, Navidrome y Plex.
quickStart:
  - text: Guía de instalación
    link: /es/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /es/getting-started/docker-compose/
  - text: Instalación en un clic
    link: /es/getting-started/one-click/
apps:
  - icon: smartphone
    title: Downtify para Android
    text: La app oficial. Encuentra tu servidor en la red, emite en calidad original por Wi-Fi y en una menor con datos móviles, guarda canciones sin conexión y funciona con Android Auto. Aún en pruebas, en GitHub Releases y Obtainium.
    link: https://github.com/henriquesebastiao/downtify-android
  - icon: tablet-smartphone
    title: Downtify para iOS
    text: Hecha por un miembro de la comunidad para iPhone y iPad (iOS 17 o posterior), con canciones sin conexión y controles en la pantalla de bloqueo. La beta pública está en TestFlight.
    link: https://github.com/michaelmoskie/Downtify-IOS-Client
community:
  - text: Estrella en GitHub
    link: https://github.com/henriquesebastiao/downtify
    icon: star
    primary: true
  - text: Patrocinar
    link: https://github.com/sponsors/henriquesebastiao
    icon: heart
  - text: Traducir
    link: /es/features/internationalization/
    icon: languages
  - text: Contribuir
    link: /es/contributing/
    icon: git-pull-request
---

## Por qué Downtify

<HomeHighlights :items="$frontmatter.why" />

## Un vistazo más de cerca

<HomeShowcase :items="$frontmatter.showcase" />

## Cómo funciona

Downtify no necesita ninguna clave de API de Spotify y nunca descarga nada de Spotify. Averigua en fuentes públicas a qué apunta un enlace, elige el audio de YouTube Music cuya duración mejor coincide, lo descarga con `yt-dlp`, lo convierte con `ffmpeg` y lo etiqueta con `mutagen`, todo en un único contenedor Docker. YouTube entra cuando nada coincide bien, y SoundCloud, Soulseek y Deemix se suman si los activas. [Cada paso, en detalle](how-it-works.md).

<HomePipeline :steps="$frontmatter.pipeline" />

## Qué puedes pegar

| Fuente        | Qué funciona                          | Ejemplo                             |
| ------------- | ------------------------------------- | ----------------------------------- |
| Spotify       | Canciones, álbumes, playlists, artistas | `open.spotify.com/playlist/…`     |
| YouTube Music | Canciones, álbumes, playlists, artistas | `music.youtube.com/playlist?list=…` |
| YouTube       | Vídeos                                | `youtube.com/watch?v=…`             |
| Deezer        | Canciones, álbumes, playlists, artistas | `deezer.com/album/…`              |
| SoundCloud    | Canciones                             | `soundcloud.com/artist/track`       |
| Búsqueda      | Lo que escribirías                    | `The Night Owls Do I Still Recall`  |
| CSV           | Exportaciones de bibliotecas          | Soundiiz, TuneMyMusic, Exportify    |

## Todo lo que hace

Cada función tiene su propia página, con todas las opciones explicadas. [Todas las funciones de un vistazo](features/index.md).

<HomeFeatures />

## En marcha en un minuto

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Abre [`localhost:8000`](http://localhost:8000), inicia sesión como **admin** con la contraseña **downtify** y pega un enlace. Cambia esa contraseña en **Ajustes → General** enseguida. Tu música llega a `/path/to/music`, con sus etiquetas.

<HomeActions :actions="$frontmatter.quickStart" />

## Preguntas frecuentes

::: details ¿Necesito una cuenta de Spotify, Premium o una clave de API?
No. Downtify lee los datos de canciones, álbumes y playlists en las páginas públicas de inserción (embed) de Spotify, así que no necesita credenciales de ningún tipo, y el audio nunca viene de Spotify. Consulta [Cómo funciona](how-it-works.md).
:::

::: details ¿De dónde sale el audio y qué calidad tiene?
De YouTube Music por defecto: el resultado cuya duración mejor coincide con la canción, con YouTube como alternativa. Elige MP3, FLAC, M4A, OGG u Opus con la tasa de bits que quieras, o conserva el mejor audio de la fuente sin recodificarlo. Los archivos sin pérdida vienen de fuentes que añades tú: tu propio servidor de [Soulseek (slskd)](features/slskd-navidrome.md), cuyos archivos conservan su formato original, o un servidor [Deemix](features/deemix.md). Consulta [Ajustes de descarga](features/download-settings.md).
:::

::: details ¿Funciona con Jellyfin, Navidrome o Plex?
Sí. Los archivos se etiquetan como esperan los servidores multimedia, se guardan en carpetas `Artista/Álbum/` y cada playlist tiene un archivo M3U estándar que reconocen. Navidrome también puede recibir las playlists sincronizadas y valoraciones a partir de Deezer. Consulta [Organización de archivos](features/file-organization.md) y [Exportación M3U](features/m3u-export.md).
:::

::: details ¿Funciona en una Raspberry Pi o en un NAS?
La imagen se publica para `amd64` y `arm64`, y Umbrel, CasaOS y HomeDock OS la instalan con un clic. Consulta [Instalación en un clic](getting-started/one-click.md).
:::

::: details YouTube dice "Sign in to confirm you're not a bot". ¿Y ahora?
Sube un `cookies.txt` en **Ajustes → Cookies de YouTube**; Downtify mantiene esa sesión iniciada por su cuenta. Si YouTube sigue limitándote, aumenta la _Pausa entre descargas_, reduce las _Descargas simultáneas_ y después prueba `DOWNTIFY_FORCE_IPV4=1`. Consulta [Solución de problemas](troubleshooting.md) y [Cookies de YouTube](features/youtube-cookies.md).
:::

## Llévala contigo

<HomeHighlights :items="$frontmatter.apps" />

Cualquier otro cliente puede usar la misma API: consulta el [contrato del cliente móvil](mobile-client-contract.md).

<div class="home-cta">

## Hecho en abierto

Downtify es libre y de código abierto. Más de 35 personas han aportado código, los traductores de la comunidad lo han llevado a 12 idiomas y muchas funciones empezaron como una idea que alguien abrió en una issue. Si se ha ganado un sitio en tu servidor, dale una estrella en GitHub, cuéntaselo a un amigo que también aloje sus propios servicios o patrocina su desarrollo: ayuda a pagar el tiempo que lleva cada versión.

<HomeActions :actions="$frontmatter.community" />

</div>
