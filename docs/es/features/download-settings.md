---
icon: lucide/sliders-horizontal
---

# Ajustes de descarga

Abre **Ajustes** en la barra lateral (en el móvil: **Más → Ajustes**). La página se divide en secciones — General, Fuentes de audio, Descargas y archivos, Etiquetas y letras, Navidrome, Biblioteca y Acerca de. Los cambios quedan pendientes hasta que pulses **Guardar cambios** en la barra que aparece abajo; salir de la página con cambios sin guardar pregunta antes. Los ajustes se guardan en disco y sobreviven a los reinicios del contenedor.

## Formato

| Formato | Extensión | Notas |
|--------|-----------|-------|
| MP3 | `.mp3` | Por defecto. Compatibilidad universal. |
| FLAC | `.flac` | Sin pérdidas. El ajuste de bitrate se ignora. |
| M4A | `.m4a` | AAC en un contenedor MPEG-4. Bueno para dispositivos Apple. |
| OGG | `.ogg` | Ogg Vorbis. Formato abierto, buena relación calidad/tamaño. |
| OPUS | `.opus` | Mejor compresión con bitrates bajos. |

## Bitrate

Disponible para formatos con pérdidas (MP3, M4A, OGG, OPUS). FLAC ignora este ajuste.

| Opción | Kbps |
|--------|------|
| Bajo | 128 |
| Medio | 192 |
| Alto | 256 |
| Máximo | **320** (por defecto) |

El audio descargado se codifica al bitrate que elijas, en todos los formatos con pérdidas. Si el audio que sirve YouTube ya tiene el códec de destino a más o menos ese bitrate (p. ej. su flujo AAC de ~128 kbps para **M4A @ 128**), se conserva tal cual en lugar de recodificarse, ya que recodificar solo perdería calidad.

::: info Un bitrate más alto no añade calidad
El audio de YouTube llega como mucho a **128–160 kbps** (AAC u Opus), y Downtify siempre descarga el mejor flujo disponible. Codificarlo a 256 o 320 kbps da archivos más grandes que conservan fielmente esa fuente, pero no pueden recuperar detalle que la fuente nunca tuvo. Elige un bitrate más bajo si el tamaño de los archivos te importa más.
:::

## Plantilla del nombre de archivo

La plantilla de nombre de archivo por defecto es:

```
{artists} - {title}
```

Que produce nombres como `The Night Owls - Do I Still Recall.mp3`.

Tokens disponibles:

| Token | Descripción |
|-------|-------------|
| `{title}` | Título de la canción |
| `{artists}` | Nombres de los artistas separados por comas |
| `{album}` | Nombre del álbum |
| `{tracknumber}` | Posición de la canción en su álbum, con ceros a la izquierda hasta 2 dígitos (p. ej. `01`, `12`). Vacío cuando la fuente no tiene número de canción (p. ej. un resultado de texto libre/búsqueda de YouTube). |
| `{year}` | Año de lanzamiento (p. ej. `2025`). Vacío cuando la fuente no tiene fecha de lanzamiento (p. ej. un resultado de texto libre/búsqueda de YouTube). |

La plantilla también puede incluir `/` para crear subcarpetas. Por ejemplo, para organizar una biblioteca como `Artista/Álbum (2025)/01 - Título.mp3` — útil al descargar una discografía completa, ya que cada álbum acaba en su propia carpeta junto con su año de lanzamiento:

```
{artists}/{album} ({year})/{tracknumber} - {title}
```

::: info
Esto es independiente de las opciones **Organizar por artista** / **Organizar por álbum** de abajo — esas llevan las descargas de playlists/álbumes a carpetas compartidas por artista o por álbum en toda tu biblioteca. `{tracknumber}` y `{year}` solo permiten que una plantilla como la anterior construya ese mismo diseño a mano, canción a canción, sin activar esas opciones.
:::

## Descargas simultáneas

Controla cuántas canciones se descargan a la vez. Elige un valor predefinido (1, 2, 3, 5, 8) o escribe cualquier valor personalizado de **1 a 30** en el campo numérico junto a ellos.

| Valor | Comportamiento |
|-------|-----------|
| **1** | Secuencial — una canción cada vez (lo más seguro, menor uso de recursos) |
| **3** | Por defecto. Buen equilibrio entre velocidad y estabilidad. |
| **8** | Más rápido para playlists grandes |
| **hasta 30** | Lo mejor para conexiones muy rápidas; usa más CPU y ancho de banda, y aumenta la probabilidad de que YouTube te limite. |

El límite se aplica a toda descarga por lotes — descargas de playlists/álbumes, el endpoint de la cola por lotes y las [importaciones de biblioteca](library-import.md) por CSV — y a las consultas de la sincronización de **[Carpetas de música existentes](external-library.md)** (letras, portadas, género). **No** se aplica a los barridos del Monitor de playlists, que descargan las canciones nuevas de una en una. Cambiar este valor en Ajustes surte efecto de inmediato sin reiniciar; el servidor limita cualquier valor fuera de `1–30`.

## Pausa entre descargas

Hace que Downtify espere un número configurable de segundos al terminar una canción antes de empezar la siguiente, en lugar de lanzar las peticiones seguidas.

| Valor | Comportamiento |
|-------|-----------|
| **0** | Por defecto — desactivado, sin espera. |
| **5 / 15 / 30 / 60** | Valores predefinidos, o escribe cualquier valor personalizado de **0 a 300 segundos**. |

Se aplica a las descargas de playlists, álbumes y lotes, a las [importaciones de biblioteca](library-import.md) por CSV y a los barridos automáticos del Monitor de playlists. Se omite en la descarga manual de una sola canción (no hay una "siguiente" que esperar) y tras la *última* canción de cualquier lote, para que una tanda no acabe con una espera inútil.

Combinada con un valor menor de **Descargas simultáneas**, es la herramienta principal para evitar el límite de peticiones de YouTube al descargar una playlist grande o una biblioteca importada sin supervisión.

## Pausa entre consultas de sincronización

La misma idea, pero para las **[Carpetas de música existentes](external-library.md)** en lugar de las descargas. La sincronización busca letras, portadas que faltan y género en lotes de **[Descargas simultáneas](#parallel-downloads)** canciones a la vez, y luego espera este número de segundos antes del siguiente lote. Por defecto **0** (las consultas siguen ejecutándose a la vez, aún limitadas por Descargas simultáneas). Usa unos segundos en una colección grande para que LRCLIB, las fuentes de portadas e iTunes no reciban todo de golpe.

## Descargar portadas

Controla si Downtify incrusta la portada del álbum. Activado por defecto. Desactívalo para omitir por completo la búsqueda de portadas — el resto de etiquetas (título, artista, álbum, año, letra) se incrustan con normalidad, pero los archivos pesan menos y se descargan algo más rápido, ya que nunca se pide ni se escribe la imagen de portada.

Desactivarlo también omite la escritura del `cover.jpg` independiente que produce la opción *Organizar por álbum* (consulta [Organización de archivos](file-organization.md)), y el [reproductor](player.md) y la biblioteca no mostrarán portada en las canciones descargadas así (en su lugar, el icono de nota musical).

Ese `cover.jpg` lo comparten todas las canciones de la carpeta del álbum. Borrar una canción desde la página Biblioteca también lo elimina, pero solo cuando es la **última** canción que queda en esa carpeta — mientras siga ahí otra canción del mismo álbum, la portada se queda.

## Resolución de la portada

Solo importa cuando **Descargar portadas** (arriba) está activado. Fija el tamaño objetivo (ancho y alto, en píxeles) que Downtify pide para la portada incrustada procedente de **YouTube Music** o **Deezer**. Elige un valor predefinido (300, 600, 800, 1000, 1200) o arrastra el control deslizante de **300 a 1200**; el valor actual en píxeles aparece a su lado. Por defecto es 600.

Es útil al alimentar tu biblioteca a un servidor multimedia como Plex, que muestra portadas con más resolución de la que Downtify incrusta por defecto.

Las dos fuentes aplican el ajuste de forma distinta, ya que solo una de ellas puede redimensionarse realmente bajo demanda:

- Las miniaturas de **YouTube Music** se pueden redimensionar editando su URL — comprobado contra el CDN real, los valores altos devuelven de verdad más detalle (no solo ampliación) en la mayoría de portadas, hasta la resolución de la propia imagen de origen.
- **Deezer** solo ofrece cuatro tamaños fijos para la portada de cualquier canción, álbum, artista o playlist (56, 250, 500 y 1000 px) — no hay tamaño intermedio que pedir. Downtify elige el menor de esos cuatro que aún sea al menos tan grande como el valor configurado (pedir 300 px da la de 500 px, ya que no existe un tamaño exacto de 300 px); pedir más de 1000 px también da la de 1000 px, la mayor de Deezer.

::: info Las portadas procedentes de Spotify no se ven afectadas
Downtify ya incrusta la **mayor** portada que ofrece la API de embed pública de Spotify para canciones/álbumes/playlists resueltos por Spotify — no hay un tamaño mayor que pedir. Este ajuste solo eleva el techo para las canciones resueltas por YouTube Music (búsqueda de texto libre, URL de YouTube y cualquier canción de Spotify reasignada a YouTube Music para el audio en sí) o por Deezer (un enlace de Deezer pegado, o una canción de las [Listas de éxitos](charts.md)).
:::

Cambiar este valor en Ajustes surte efecto de inmediato, incluso en la página de búsqueda abierta en ese momento — no obliga a volver a descargar nada que ya esté en disco.

## Sobrescribir archivos existentes

Activado por defecto, como el comportamiento histórico de Downtify: toda descarga pasa por el pipeline (obtención del audio, etiquetado, portada, letra) y sobrescribe lo que ya haya en la ruta de salida calculada.

### Qué significa realmente «de nuevo»

Activado, una nueva descarga es una **ejecución completamente nueva**, no una reparación del archivo existente. Downtify no mira lo que ya tienes: busca en tus [fuentes de audio](#audio-provider) en el orden configurado — así que, si slskd es la primera, se prueba slskd primero, no solo como alternativa —, obtiene el audio de la que responda y escribe sobre él las etiquetas, la portada y la letra de hoy.

Eso tiene una consecuencia que conviene conocer antes de volver a descargar una biblioteca grande:

::: warning Un formato distinto deja atrás el archivo antiguo
El archivo nuevo se escribe en la ruta que produce la [plantilla del nombre de archivo](#output-filename-template), con la extensión del audio **nuevo**. Downtify sobrescribe el archivo antiguo solo cuando ambos terminan con la misma extensión.

Así, volver a descargar `Artista - Canción.mp3` cuando slskd responde con un FLAC te da **ambos**: `Artista - Canción.mp3` (el antiguo, intacto) y `Artista - Canción.flac`. Con [Dejar los archivos de slskd en su sitio](slskd-navidrome.md#leave-files-in-place) activado — lo predeterminado —, el archivo de slskd ni siquiera se copia a tu carpeta de descargas, así que el antiguo se queda exactamente donde estaba y el nuevo vive en `slskd/`.

No se pierde nada, pero obtienes duplicados. Para reemplazar de verdad un archivo, consulta [Reemplazar audio](replace-audio.md), que conserva la ruta, el formato y las etiquetas.
:::

### La portada viene de Spotify o YouTube Music, no del archivo

Cualquier arte que lleve el audio descargado — incluida una portada de alta resolución incrustada en un archivo de slskd — se **descarta y se sustituye** durante el etiquetado. Downtify siempre incrusta la portada que obtiene para la canción de Spotify o YouTube Music, a la [resolución de la portada](#cover-art-resolution) que configuraste (600 px por defecto). Lo mismo vale para el título, los artistas, el álbum y el resto de etiquetas: las etiquetas propias de la fuente no se conservan.

Si lo que quieres son portadas más grandes en archivos que ya tienes, volver a descargar es el camino largo. [Mejorar biblioteca](library-upgrade.md) hace justo eso — compara la portada incrustada de cada archivo con la de Spotify, iTunes y YouTube Music, escribe la más grande, completa letras y etiquetas que faltan y nunca toca el audio.

Desactívalo para no descargar nunca una canción que ya está en disco. Importa sobre todo al descargar una playlist, importar una [biblioteca por CSV](library-import.md) o dejar que el [Monitor de playlists](playlist-monitor.md) sincronice playlists que comparten canciones entre sí o con canciones que ya están en tu biblioteca — con la opción activada, cada uno de esos duplicados se descarga otra vez.

Desactivada, Downtify busca la canción **en cualquier parte de la carpeta de descargas**, no solo donde iría la nueva descarga:

- la raíz de la biblioteca (descargas de canciones sueltas),
- la carpeta de cualquier playlist (descargas de playlists, importaciones por CSV, Monitor de playlists),
- una carpeta de artista/álbum, o el diseño plano de antes de activar o desactivar *Organizar por artista/álbum*.

Una canción cuenta como ya descargada cuando un archivo de audio (`.mp3`, `.flac`, `.m4a`, `.ogg`, `.opus`) tiene el nombre que le corresponde según la [plantilla del nombre de archivo](#output-filename-template), comparado sin distinguir mayúsculas de minúsculas. Un archivo `.lrc` de letra suelto no cuenta. Si la plantilla contiene carpetas (p. ej. `{artists}/{title}`), esas carpetas también deben coincidir, para que la canción de otro artista con el mismo título no se confunda con esta. Como los archivos no llevan el ID de canción de Spotify/YouTube, la coincidencia es por nombre: un archivo que renombraste, o guardado con otra plantilla de nombre, no se reconocerá.

Cuando se omite una canción:

- No se obtiene nada: ni audio, ni portada, ni letra, ni reetiquetado. En las canciones de Spotify, la comprobación se ejecuta incluso antes de la búsqueda en YouTube Music, así que las canciones ya descargadas no cuestan ninguna petición de búsqueda.
- La cola muestra la canción como terminada, y los [archivos M3U](m3u-export.md) de las playlists apuntan al archivo existente allí donde esté (p. ej. `../Artista - Título.mp3`), así que la playlist sigue sonando completa.
- Si la misma canción entra en la cola dos veces a la vez (listada dos veces en una playlist, o en dos playlists que se descargan en paralelo), solo se descarga una copia. La otra la espera y luego se omite.

## Canciones largas

**Ajustes → Descargas y archivos → Duración máxima** limita la duración de las canciones para descargas *y* streams por igual (por defecto **10 minutos**, `0` admite todo). Las canciones más largas se rechazan antes de obtener nada, con el error de cola *«no se descargan canciones de más de …»* — los mixes y subidas de una hora nunca son lo que debería ser una canción de la biblioteca. El mismo límite protege el streaming: una canción más larga se rechaza con un `400` (quien conoce su duración la pasa en `duration`, y el archivo en caché se comprueba de todos modos), así que las subidas largas tampoco se acumulan en la caché de streaming. Los archivos ya descargados y los episodios de podcast (que suelen ser más largos) no se ven afectados.

## Proveedor de audio

El proveedor de audio por defecto es **YouTube Music**. Downtify usa [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) para buscar la mejor coincidencia comparando la duración de la canción. Cuando YouTube Music no tiene una coincidencia aceptable, o solo una cuya duración se aleja mucho (probablemente otra grabación), Downtify recurre automáticamente a buscar en YouTube estándar — consulta [Cómo funciona](../how-it-works.md#fallback-to-standard-youtube).

**Ajustes → Fuentes de audio** también puede usar solo **YouTube** estándar, o **slskd** (Soulseek), como lista ordenada de alternativas — consulta [slskd y Navidrome](slskd-navidrome.md#audio-sources-and-fallback-order).

### Forzar una fuente de audio concreta

Si Downtify elige el vídeo equivocado de YouTube Music (p. ej. una versión cover en lugar del original), puedes sustituirlo por canción:

**Opción A — pega directamente una URL de YouTube Music**

Pega `https://music.youtube.com/watch?v=…` (o una URL normal `youtube.com/watch?v=…`) en la barra de búsqueda y pulsa descargar. Downtify obtiene el audio de ese vídeo exacto.

::: info
Al descargar mediante una URL de YouTube, los metadatos (título, artista, portada) vienen de YouTube y no de Spotify. Para etiquetas limpias, usa la Opción B.
:::

**Opción B — forzar el audio de una canción que falló**

1. En la **Cola de descargas**, haz clic en **Forzar fuente de audio** bajo una canción fallida.
2. Pega una URL de YouTube o YouTube Music en el campo que aparece.
3. Pulsa **Enter** o haz clic en **Aplicar**.

Downtify vuelve a descargar la canción usando ese vídeo exacto y conserva todos los metadatos de Spotify (título, artista, álbum, portada, letra).

## Metadatos incrustados

Downtify incrusta las siguientes etiquetas en cada archivo descargado, sea cual sea el formato:

| Etiqueta | Fuente |
|-----|--------|
| Título | Embed de Spotify |
| Artista(s) | Embed de Spotify |
| Álbum | Embed de Spotify — en una descarga de canción suelta, el álbum que nombra la página pública de la canción en Spotify (el embed de la canción en sí no trae ninguno) |
| Año | Embed de Spotify (consulta a nivel de canción) |
| Portada | Embed de Spotify (portada a nivel de canción) para canciones resueltas por Spotify; miniatura de YouTube Music o portada de Deezer en los demás casos. Opcional — consulta [Descargar portadas](#download-cover-art) y [Resolución de la portada](#cover-art-resolution) |
| Letra | lrclib (si está activado) |
