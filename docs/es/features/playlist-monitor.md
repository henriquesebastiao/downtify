---
icon: lucide/eye
---

# Monitor de playlists

El Monitor de playlists vigila tus playlists favoritas de Spotify y YouTube Music — y los artistas que sigues — y descarga automáticamente las canciones y los lanzamientos nuevos según aparecen, sin que tengas que hacer nada.

Hay dos tipos de vigilancia, cada uno en su pestaña de la página Monitor (**Playlists** y **Artistas**, en `/monitor/playlists` y `/monitor/artists`):

| Vigilancia | Pega | Descarga |
|-------|-------|-----------|
| **Playlist** | La URL de una playlist de Spotify o YouTube Music | Todas las canciones de la playlist, y luego cualquiera añadida más tarde |
| **Artista** | La URL de un **artista** de Spotify, o de un artista de YouTube Music | Toda la discografía del artista, y luego cada lanzamiento nuevo |

Cada vigilancia muestra bajo su nombre el enlace que sigue, y una insignia **Spotify** o **YouTube Music** con el servicio desde el que se añadió.

Consulta [Vigilancia de artistas](#artist-watch) para ver cómo funcionan.

Las vigilancias pertenecen a quien las creó: cada cuenta sigue sus propias playlists y artistas (la misma URL vigilada dos veces se barre dos veces), y un barrido atribuye sus descargas al dueño de la vigilancia. Un admin ve todas.

## Cómo funciona

Downtify mantiene una tarea en segundo plano que se ejecuta cada 60 segundos. En cada barrido comprueba si cada vigilancia activa debe inspeccionarse ya (según su intervalo configurado). Cuando le toca a una *playlist*, Downtify:

1. Obtiene la lista completa de canciones de Spotify o YouTube Music
2. La compara con el conjunto de canciones ya descargadas
3. Descarga las canciones nuevas con el mismo pipeline que una descarga manual
4. Actualiza el archivo M3U de la playlist (si la generación de M3U está activada)

La primera comprobación, que empieza en cuanto añades la vigilancia, descarga todo lo que ya hay en la playlist; las siguientes descargan solo lo añadido desde entonces. Lo «ya descargado» se registra en una pequeña base de datos SQLite (`downtify_monitor.db` en `/data`), no mirando la carpeta de descargas — así que mover un archivo descargado a otro sitio del disco (a tu propia organización de biblioteca, otra unidad, donde sea) **no** hace que Downtify crea que falta y lo vuelva a descargar en la siguiente comprobación.

Un barrido aparte se ejecuta cada hora y comprueba si el archivo de cada canción descargada sigue ahí. Los archivos realmente borrados (a diferencia de los movidos) se olvidan en ese momento, así que la canción vuelve a poder descargarse — en la siguiente comprobación de la vigilancia tras ese barrido horario, no al instante.

Una vigilancia nunca se comprueba dos veces a la vez. Añadir una vigilancia inicia su primera comprobación de inmediato; si esa comprobación sigue descargando cuando llega el siguiente barrido programado, el barrido omite la vigilancia en lugar de iniciar una segunda descarga solapada de las mismas canciones.

## Añadir una playlist

1. Abre **Monitor** en la barra lateral (en el móvil: **Más → Monitor**) y quédate en la pestaña **Playlists**
2. Pega la URL de una playlist:
    - Spotify: `https://open.spotify.com/playlist/…`
    - YouTube Music: `https://music.youtube.com/playlist?list=…` (un enlace `www.youtube.com/playlist?list=…` también sirve)
3. Elige un intervalo de comprobación (de 15 minutos a una vez al mes)
4. Haz clic en **Vigilar playlist**

Cada pestaña tiene su propio cuadro. Pegar un enlace de artista en la pestaña Playlists (o de playlist en Artistas) no añade nada: la página dice qué tipo de enlace es y se ofrece a moverlo a la pestaña correcta.

También puedes empezar a vigilar desde la página de una playlist: pega su enlace en la barra de búsqueda y usa **Vigilar canciones nuevas** (o **Vigilar lanzamientos nuevos** en un artista de YouTube Music). Las playlists descargadas en la Biblioteca ofrecen la misma acción en su menú **⋯**. Las vigilancias añadidas así usan un intervalo de 6 horas — cámbialo en la página Monitor.

## Playlists de YouTube Music

Usa una playlist de YouTube Music para canciones que no están en Spotify: remixes, directos, versiones, subidas de canales promocionales. Cada canción se descarga del **vídeo exacto de la playlist**. Downtify no vuelve a buscarlo, así que lo que obtienes es lo que añadiste a la playlist.

- **Se obtienen todas las canciones**, por larga que sea la playlist. Los vídeos eliminados o privados se omiten.
- **Las canciones que YouTube Music marca en gris se descargan igualmente.** Las playlists hechas por conversores e importadores (Soundiiz, TuneMyMusic y similares) suelen listar canciones como subidas normales de YouTube que YouTube Music muestra como no disponibles y sin id de canción. Downtify encuentra el vídeo a partir de la miniatura de la entrada y lo descarga como cualquier otro, así que una playlist así no sale vacía. Un vídeo realmente eliminado o hecho privado no se puede descargar: cuando YouTube Music lo marca así, se omite, y cuando solo da una miniatura, la canción aparece como fallida en la cola.
- **Artista y título salen del título del vídeo.** Muchas entradas de playlist son subidas acreditadas al canal que las publicó (p. ej. `MrSuicideSheep`), y el crédito real está en el título, como `Bronze Whale - Patterns`. Para todo lo que no es un lanzamiento de catálogo, Downtify separa `Artista - Título` en el nombre del archivo y las etiquetas. También quita sufijos como `(Official Video)` o `[Lyrics]`. La parte tras el guion que nombra una versión (`Yellow - Live at Glastonbury`) se queda en el título. Las canciones de catálogo (audio oficial, o cualquier cosa archivada bajo un álbum) conservan el artista y el título propios de YouTube Music.
- **No todo enlace `list=` es una playlist.** El enlace `OLAK5uy_…` de un álbum se sigue descargando como álbum. Un enlace `watch?v=…&list=…` es la única canción que estaba sonando. Una mezcla de radio (`list=RD…`) no tiene una lista fija de canciones y no se puede vigilar.

## Vigilancia de artistas

En lugar de armar una playlist por artista, pega un enlace de artista y Downtify sigue todo su catálogo. Añade uno desde la pestaña **Artistas** de la página Monitor — pega la URL, elige un intervalo, haz clic en **Vigilar artista**. Las vigilancias de artistas muestran un número de lanzamientos en lugar de un número de canciones.

URL aceptadas:

- Una URL de artista de Spotify (`https://open.spotify.com/artist/…`)
- Una URL de artista de YouTube Music, por canal (`https://music.youtube.com/channel/UC…`) o por handle (`https://music.youtube.com/@HenriqueeJuliano`)

Un handle se resuelve al canal del artista cuando añades la vigilancia, así que el mismo artista pegado por handle y por URL de canal se reconoce como una sola vigilancia. Un handle que no pertenece a un artista de YouTube Music se rechaza.

En cada barrido, Downtify lista la discografía del artista, la compara con los lanzamientos que ya ha procesado y descarga todas las canciones de lo que sea nuevo. Un barrido en régimen estable cuesta una sola petición — las listas de canciones solo se obtienen para lanzamientos que no ha visto antes.

::: info Por qué la discografía viene de YouTube Music
El embed público de Spotify expone el nombre de un artista y una vista previa de sus canciones más populares, pero **no** su discografía — leerla exigiría credenciales de la API de Spotify, que Downtify deliberadamente no usa. Así que un enlace de artista de Spotify se resuelve a su nombre y se asocia al mismo artista en YouTube Music, que es también de donde se obtiene el audio. La ventaja: todo lanzamiento que Downtify puede ver es uno que realmente puede descargar. El inconveniente: para un artista de nombre ambiguo, comprueba que el nombre resuelto de la vigilancia es el artista que querías — pega directamente la URL del artista de YouTube Music si eligió el equivocado.
:::

::: warning El primer barrido descarga todo el catálogo antiguo
Añadir un artista pone en cola **todos** sus lanzamientos, que para un artista prolífico pueden ser cientos de álbumes y sencillos. Define la **[Pausa entre descargas](download-settings.md#delay-between-downloads)** antes de añadir un lote de artistas, o es muy probable que te limiten el ritmo — o activa **Solo lanzamientos nuevos** (abajo) para saltarte por completo el catálogo antiguo.
:::

### Elegir qué descargar

Bajo el cuadro de enlace de la pestaña **Artistas** (y en el diálogo **Editar** de una vigilancia), dos opciones deciden qué descarga una vigilancia de artista:

| Opción | Qué hace |
|--------|--------------|
| **Descargar: Álbumes / Sencillos / EP** | Solo se descargan los lanzamientos de los tipos marcados. Los tres vienen activados por defecto; al menos uno debe seguir activado. El tipo es la propia etiqueta de YouTube Music para cada lanzamiento — un lanzamiento que no etiqueta cuenta como álbum. |
| **Solo lanzamientos nuevos** | Se omite todo lo que el artista ya había publicado cuando empieza la vigilancia; solo se descarga lo que salga después. Desactivado por defecto. |

Cómo se comportan cuando las cambias después:

- **Activar un tipo** descarga los lanzamientos de ese tipo la próxima vez que se comprueba la vigilancia — también su catálogo antiguo, salvo que **Solo lanzamientos nuevos** esté activado (entonces solo los publicados desde que empezó la vigilancia, o desde que se activó la opción). Los lanzamientos de un tipo desactivado nunca se registran, así que no se pierde nada por desactivar un tipo durante un tiempo.
- **Activar Solo lanzamientos nuevos** en una vigilancia existente registra como omitido todo lo publicado hasta ese momento; los lanzamientos ya descargados se quedan como están.
- **Desactivarla** descarga en la siguiente comprobación los lanzamientos que omitió (de los tipos marcados).
- Guardar cualquiera de las dos opciones en el diálogo **Editar** comprueba la vigilancia al instante, en lugar de esperar a su siguiente comprobación programada.

«Omitir» los lanzamientos existentes requiere un vistazo correcto a la discografía del artista: si YouTube Music devuelve una lista vacía (lo cual suele ser más un contratiempo que un artista sin nada publicado), no se registra nada y la siguiente comprobación lo intenta de nuevo, así que una respuesta mala nunca puede hacer que el catálogo antiguo se descargue después. Apuntar una vigilancia de **Solo lanzamientos nuevos** a otro artista omite el catálogo antiguo de ese artista del mismo modo.

La lista del Monitor muestra los filtros de una vigilancia bajo su enlace cuando no son los predeterminados (p. ej. **Álbumes** · **Solo nuevos**).

Un lanzamiento solo se registra como procesado cuando todas sus canciones están resueltas, así que una canción que falla por un error transitorio se reintenta en el siguiente barrido en lugar de omitirse para siempre. Las canciones que ya se descargaron nunca se obtienen dos veces.

Las vigilancias de artistas no generan archivos M3U — las canciones se organizan según tus ajustes de [organización de archivos](file-organization.md) y no como una playlist.

## Intervalos de comprobación

| Etiqueta | Minutos | Ideal para |
|-------|---------|----------|
| Cada 15 min | 15 | Playlists que se actualizan a menudo |
| Cada 30 min | 30 | |
| Cada hora | 60 (por defecto) | La mayoría de las playlists |
| Cada 3 horas | 180 | |
| Cada 6 horas | 360 | |
| Cada 12 horas | 720 | |
| Cada día | 1 440 | Playlists que cambian despacio |
| Cada semana | 10 080 | Playlists actualizadas semanalmente |
| Cada 2 semanas | 20 160 | |
| Cada mes | 43 200 | Archivo o playlists que rara vez se actualizan |

Puedes cambiar el intervalo de una playlist existente en cualquier momento desde la tarjeta del monitor, sin quitarla y volver a añadirla.

## Gestionar las playlists vigiladas

Cada pestaña lista solo su propio tipo de vigilancia. Sobre la lista:

- **Filtrar** — escribe parte de un nombre o del enlace (p. ej. un id de playlist) para acotar la lista
- **Todo / En pausa** — muestra solo las vigilancias en pausa
- **Comprobar todo ahora** — comprueba todas las vigilancias activas de la pestaña actual
- Una franja con cuántas canciones llegaron en el periodo elegido (**7 días**, **30 días** o **90 días**) y, sumando todas las vigilancias, cuántas canciones tienen, el espacio que ocupan (**En disco**) y cuántas están **En más de una vigilancia** — consulta [Actividad y almacenamiento por vigilancia](#activity-and-storage-per-watch)

En cada fila:

- Interruptor **Activo** — pausa o reanuda la vigilancia sin quitarla
- **Comprobaciones** — con qué frecuencia se comprueba
- **Comprobar ahora** (↻) — la comprueba de inmediato, fuera del calendario
- **Actividad** — canciones nuevas en el periodo elegido, la media por semana y si ese ritmo sube o baja; haz clic para abrir la página de la vigilancia
- **Almacenamiento** — el espacio de las canciones que solo tiene esta vigilancia, y cuántas comparte con otras
- **Editar** (✎) — ve y cambia el enlace, el intervalo y el estado activo de la vigilancia (consulta [Editar una vigilancia](#editing-a-watch))
- **⋯** — **Actividad y canciones** (la página de la vigilancia), pausar/reanudar, copiar el enlace, abrir el original o **Dejar de vigilar** (se borra el registro; los archivos descargados se conservan)

**Actividad** y **Almacenamiento** son columnas como las demás: ocúltalas o cambia su ancho desde **Columnas**.

### Editar una vigilancia

Haz clic en el nombre de una vigilancia o en su botón **Editar**. El diálogo muestra el enlace completo que se sigue, con **Copiar enlace** y **Abrir original**, además de cuándo se añadió la vigilancia, cuándo se comprobó por última vez y cuántas canciones o lanzamientos tiene. Puedes cambiar:

- **Enlace** — debe ser el mismo tipo de enlace (una playlist para una vigilancia de playlist, un artista para una de artista):
    - Otro enlace a la **misma** playlist o artista (por ejemplo con otro código de compartir `?si=`, o el enlace de YouTube Music en lugar del de `www.youtube.com`) solo actualiza la dirección guardada. Nada más cambia.
    - Un enlace a una playlist o artista **distintos** apunta la vigilancia hacia él. La vigilancia conserva su intervalo y estado activo, pero toma el nuevo nombre y empieza de cero: se borra su historial de descargas o lanzamientos y, si está activa, se comprueba de inmediato. Las canciones que ya están en tu biblioteca no se descargan de nuevo, y los archivos del destino anterior se quedan donde están.
    - Un enlace a algo que ya se vigila se rechaza.
- **Comprobar cada** y **Activo**.

Esto es útil para playlists «en vivo» que se reemplazan: abre la vigilancia para comprobar qué playlist sigue realmente, y pega la nueva si cambió.

## Ordenación

El control **Ordenar por** sobre la lista ordena la pestaña actual por:

| Campo | Notas |
|-------|-------|
| Fecha de alta | Por defecto — más nuevas primero |
| Nombre | Alfabético |
| Última comprobación | Las comprobadas hace menos primero; las nunca comprobadas, al final |
| Frecuencia | Menos frecuentes (intervalo más largo) primero |
| Número de canciones / lanzamientos | Más primero |
| Actividad reciente | Canciones nuevas en el periodo elegido |
| Ritmo medio | Canciones nuevas al día en el periodo |
| Crecimiento del almacenamiento | Espacio de las canciones nuevas del periodo |
| Almacenamiento solo suyo | Espacio de las canciones que ninguna otra vigilancia tiene |
| Canciones descargadas | Canciones en disco que descargó la propia vigilancia |

El botón de al lado alterna entre orden ascendente y descendente. La elección se recuerda en el navegador y solo cambia la lista — no el orden de comprobación ni el calendario.

## Elegir una hora de sincronización diaria

Por defecto, una playlist comprobada cada día (o semana / 2 semanas / mes) se sincroniza a la hora a la que se añadió originalmente o se comprobó por última vez — no hay una hora del día garantizada. Para fijar las sincronizaciones de un día o más a una hora concreta (p. ej. ejecutarlas de madrugada a las 3:00 en lugar de a cualquier hora), define la variable de entorno `DOWNTIFY_MONITOR_SYNC_TIME` junto con `TZ`. Consulta [Variables de entorno](../getting-started/environment-variables.md#playlist-monitor) para la referencia completa.

- Solo afecta a intervalos de un día completo o más — los intervalos más cortos (15 min – 12 h) no se ven afectados, ya que anclarlos a una única hora diaria rompería su cadencia.
- La primerísima comprobación tras añadir una playlist siempre se ejecuta de inmediato, sea cual sea este ajuste.

## Enriquecimiento de metadatos por canción

Las entradas del embed de playlist de Spotify carecen del año de lanzamiento y usan la portada de la playlist en lugar de la portada del álbum de cada canción. Downtify vuelve a obtener cada canción nueva individualmente para conseguir la portada y el año correctos antes de descargar — recurriendo a los datos a nivel de playlist si falla la obtención por canción. Las entradas de playlist de YouTube Music se saltan este paso: cada una ya trae los metadatos de su propio vídeo.

## Integración con M3U

El M3U de la playlist se reescribe **después de que termine cada canción**, así que crece a medida que el barrido descarga, en lugar de aparecer solo cuando todo termina. La playlist es reproducible desde la primera canción, y una descarga lenta o colgada más abajo en la lista nunca retiene las canciones que ya llegaron. Una reescritura final al terminar el barrido vuelve a resolver todo contra el sistema de archivos.

Las descargas manuales de playlists/álbumes y las importaciones por CSV se comportan igual. Consulta [Exportación M3U](m3u-export.md#when-it-is-written) para ver los detalles.

Con [Guardar la portada de la playlist](playlist-cover-art.md) activado, la portada se obtiene una vez por barrido que tiene canciones por descargar — antes de la primera, para que la carpeta se parezca a la playlist mientras se llena. Un barrido que no encuentra nada nuevo no vuelve a obtenerla.

## Qué pasa con las canciones que salen de una playlist

Las playlists «en vivo» (el *Top 50* de Spotify, *Descubrimiento semanal*, listas editoriales) cambian cada semana. Downtify trata una vigilancia como una **fuente de música nueva**, nunca como algo que gobierna lo que conservas:

- **Una vigilancia nunca borra archivos de audio descargados.** Ni cuando una canción sale de la playlist, ni cuando sale de todas las playlists que vigilas, ni cuando la propia playlist se encoge, ni cuando pulsas **Dejar de vigilar**.
- **Solo la playlist sigue a la playlist.** En cada barrido, el [archivo M3U](m3u-export.md) se reescribe a partir de las canciones actuales de la playlist, en su orden actual, así que una canción que salió desaparece del M3U. Su archivo se queda en la carpeta y en tu biblioteca, buscable y reproducible — también a través de Navidrome, Jellyfin o cualquier cosa apuntada a la misma carpeta.
- **Una canción que no está en ninguna playlist sigue siendo una canción.** Nada barre en busca de archivos «huérfanos».

Eso hace que una playlist de listas de éxitos sirva como feed de descubrimiento: llegan canciones nuevas automáticamente, y lo que dejan atrás se acumula como tu biblioteca.

```
Top 50 - USA        →  new song appears   →  Downtify downloads it
                    →  song drops out     →  M3U updated, file kept
```

Lo único que borra audio es lo que pides explícitamente: **Eliminar** en una canción o una selección de la Biblioteca, eliminar una playlist desde la Biblioteca (que sí elimina sus canciones — y pregunta antes), o quitar archivos tú mismo del sistema de archivos.

Para quitar de la playlist una canción que no quieres, y que no vuelva en cada comprobación, ocúltala: consulta [Canciones ocultas de una playlist](hidden-playlist-songs.md). Su archivo sigue en tu biblioteca.

::: info Eliminar una vigilancia vs. eliminar una playlist
**Dejar de vigilar** (en el menú ⋯ de la vigilancia) solo olvida la vigilancia: nada cambia en el disco. **Eliminar** en una playlist de la página **Biblioteca** es lo destructivo — quita las canciones de esa playlist, su M3U y su entrada de catálogo.
:::

Si un archivo desaparece de verdad — lo sacaste de la carpeta de descargas, o lo borraste a mano —, un barrido horario lo nota y olvida el registro que Downtify tenía de él, así que la siguiente comprobación de una vigilancia que aún lista la canción la descarga de nuevo. Un archivo simplemente *movido* dentro de la carpeta de descargas se sigue encontrando y no se vuelve a descargar.

## Almacenamiento

El estado del monitor se guarda en una base de datos SQLite en `/data/downtify_monitor.db`. La base de datos registra:

- Cada vigilancia (tipo, id de playlist de Spotify o YouTube Music o id de canal de YouTube Music, nombre, URL, intervalo, estado activo, hora de la última comprobación). Si una vigilancia es de Spotify o de YouTube Music se lee de su URL guardada, así que no hace falta una columna extra.
- Cada canción descargada con éxito por vigilancia, incluido el nombre del archivo en disco
- Para las vigilancias de artistas, los lanzamientos ya procesados, de modo que un barrido solo obtiene listas de canciones de los realmente nuevos — incluidos los que **Solo lanzamientos nuevos** omitió, marcados como tales para que desactivarla pueda traerlos de vuelta — además de los tipos de lanzamiento de la vigilancia y si es de solo lanzamientos nuevos
- Cada pista que añadió una vigilancia (`watch_events`): cuándo, el archivo, qué proveedor de audio la obtuvo, si la vigilancia la descargó o la encontró ya en la biblioteca, y si llegó con su primera comprobación. Estas filas guardan el id, el nombre y el dueño de la vigilancia tal como eran, y la sobreviven: dejar de vigilar o redirigir una vigilancia las conserva, así que sus canciones siguen diciendo de dónde vinieron
- Las pistas que cada vigilancia sigue sin poder descargar (`watch_failures`), hasta que una funciona, sale de la playlist o la vigilancia se redirige

Las bases de datos creadas antes de la Vigilancia de artistas se migran automáticamente al iniciar; las filas existentes siguen funcionando como vigilancias de playlists. Las pistas registradas antes de que Downtify guardara el historial anterior se añaden a él una vez, en el primer arranque, con un resultado desconocido (**Antes del registro**) — las del primer día de una vigilancia cuentan como su primera comprobación.

## Actividad y almacenamiento por vigilancia

La página Monitor y la página de cada vigilancia (**Actividad y canciones** en el menú **⋯** de una vigilancia, o un clic en su **Actividad**) muestran qué vigilancias hacen crecer tu biblioteca — útil con muchas vigilancias, o para averiguar por qué un mix generado trajo canciones que no esperabas.

**Qué cuenta como actividad.** Solo cuentan las canciones que una vigilancia añadió de verdad: las que descargó. Las que encontró ya en tu biblioteca (otra vigilancia, o una descarga tuya, ya las tenía) cuentan aparte como **Ya en la biblioteca**, igual que lo que trajo su primera comprobación, cuando descarga todo lo que la playlist ya tenía. Así, una playlist estática aparece inactiva aunque su primera comprobación descargara 300 canciones, y un mix que añade 15 canciones por semana aparece como 15 por semana. Las pistas registradas antes de que Downtify guardara este historial cuentan como añadidas, y la página dice cuántas son.

En el periodo elegido (7, 30 o 90 días, recordado en el navegador) una vigilancia muestra:

| Número | Qué es |
|--------|------------|
| Canciones nuevas | Canciones que añadió en el periodo |
| Al día / A la semana / Al mes | El ritmo medio en el periodo — o desde que empezó la vigilancia, si es más reciente |
| Tendencia | Si el ritmo sube (**Añade más últimamente**), baja (**Añade menos últimamente**) o se mantiene, según las canciones nuevas por día (7 días) o por semana (30 y 90 días); **Aún es pronto para saberlo** mientras haya menos de tres para comparar |
| Crecimiento del almacenamiento | Espacio de las canciones nuevas del periodo que siguen en el disco |

**Almacenamiento.** Un archivo se guarda una vez, lo tengan cuantas vigilancias lo tengan, y los números lo reflejan: **Solo en esta vigilancia** es el espacio de las canciones que ninguna otra vigilancia tiene (lo que liberaría dejar de vigilar y borrar sus canciones), **Compartidas** las canciones que también tienen otras vigilancias, y la franja de la página Monitor cuenta cada archivo una vez. Las vigilancias de otras cuentas cuentan para saber si un archivo es compartido, pero no se nombran.

La página de una vigilancia también muestra:

- **Canciones en disco**, **Descargadas por ella**, **Ya en la biblioteca** y **Con fallos** — cómo llegaron sus canciones, y cuántas siguen fallando al descargar (listadas más abajo, con el número de intentos y el último error)
- **De dónde vino el audio** — YouTube Music, YouTube, Soulseek (slskd) o Deemix, por canción en disco
- **Canciones de esta vigilancia** — todas las canciones que tiene, de la más reciente a la más antigua, incluidas las que ya salieron de la playlist, con filtros (**Últimos 30 días** — o el periodo elegido —, **Descargadas por ella**, **Ya en la biblioteca**, **Antes del registro**). Selecciona canciones para reproducirlas, ponerlas en cola, añadirlas a una playlist, descargarlas como ZIP o eliminarlas — por ejemplo, para limpiar lo que un mix trajo la última semana
- **Abrir en la Biblioteca** (la página de la playlist, o la del artista en una vigilancia de artista), **Abrir original** y **Comprobar ahora**

El id de la vigilancia (`#12`) aparece junto a su nombre, así que dos vigilancias del mismo enlace — dos cuentas que siguen una playlist, por ejemplo — se pueden distinguir.

## De dónde viene una canción

**De dónde viene** en el menú de una canción (en cualquier lugar de la Biblioteca) dice qué vigilancia la descargó primero, cuándo y con qué proveedor — **Primera comprobación** si llegó con la primera comprobación — y lista todas las vigilancias que la tienen ahora, cada una con su id, dueño (para un admin), cuándo recibió la canción y cómo: **La descargó**, **Ya en la biblioteca** o **Antes del registro**. Es un solo archivo: las vigilancias que comparten una canción apuntan todas a la misma copia.

Desde ahí, **Actividad y canciones** abre la página de la vigilancia y **Abrir en la Biblioteca** su playlist. Una vigilancia que se dejó, o que ahora sigue otro enlace, sigue apareciendo como origen de las canciones que descargó. Para una canción registrada antes de que existiera este historial, aparece la primera vigilancia que la registró, marcada como **Probablemente**. Una canción que ninguna vigilancia descargó (una que descargaste tú) lo dice.

Un usuario ve sus propias vigilancias por su nombre; una canción que descargó la vigilancia de otra cuenta solo dice eso, y cuándo.
