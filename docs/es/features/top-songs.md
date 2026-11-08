---
icon: lucide/star
---

# Top Songs

Algunos artistas tienen catálogos enormes en los que solo unas pocas canciones importan. En lugar de coger enlaces canción por canción, o descargar una playlist «This is…» de más de 50 canciones por las pocas que de verdad quieres, pega el enlace del propio artista y elige entre sus canciones más populares.

## Cómo usarlo

1. Pega un enlace de artista en el cuadro de búsqueda o en la pantalla de Inicio:
   - **Spotify**: `https://open.spotify.com/artist/…`
   - **YouTube Music**: `https://music.youtube.com/channel/UC…` o `https://music.youtube.com/@handle`
   - **Deezer**: `https://www.deezer.com/artist/…`
2. Se abre la **página del artista** con su foto y nombre, y lista sus lanzamientos (álbumes, sencillos, EP y recopilaciones, cuando el servicio los tiene), del más nuevo al más antiguo en Spotify y Deezer; haz clic en uno para ver sus canciones o descargarlo. Junto a un botón **Top Songs**, los artistas de Spotify y YouTube Music también tienen **Vigilar lanzamientos nuevos** — los de Deezer no, porque el [Monitor de playlists](playlist-monitor.md) no admite Deezer.
3. **Top Songs** abre la lista de sus canciones más populares, en el orden en que las clasifica el servicio. En Spotify y YouTube Music, una insignia con un ojo muestra cuántas veces se ha reproducido cada canción, abreviado como lo hace tu idioma (`1,5 bi` en portugués, `1.5B` en inglés) — la de Spotify es verde y la de YouTube Music, roja. YouTube Music solo informa una cifra redondeada (`1.2B plays`), así que la suya es una aproximación; Downtify la lee de la misma petición a YouTube Music que lista las canciones, más una petición para las reproducciones. El ranking «top» del propio Deezer no tiene cifra pública de reproducciones que mostrar, así que sus canciones se listan sin insignia. Las cinco primeras ya vienen marcadas; marca más o desmarca cualquiera, y pulsa **Descargar seleccionadas**.

### Escuchar canciones antes de descargar

En la página Top Songs, y en la que abre un enlace de **álbum** o **playlist** pegado, cada canción suena entera: pasa el ratón por su fila y el número se convierte en un botón de reproducir (en el móvil el botón de reproducir está siempre); púlsalo y la canción se emite desde YouTube directamente al reproductor integrado. Púlsalo de nuevo para pausar, o el botón de otra fila para cambiar. Una canción que ya está en tu biblioteca suena desde la biblioteca, con las demás canciones descargadas de la lista en cola después de ella.

El streaming sale de este servidor, nunca del navegador directamente a YouTube: la fila se resuelve a su vídeo de YouTube (el propio, para una canción de YouTube Music; si no, la coincidencia más cercana de la búsqueda) y el servidor descarga el audio una vez a su caché de streaming y luego reproduce el archivo en caché (consulta [`GET /api/stream/file`](../api-reference.md#get-apistreamfile)). Solo el servidor necesita que YouTube sea alcanzable, y una canción con restricción de edad necesita cookies de YouTube (consulta [Cookies de YouTube](youtube-cookies.md)) igual que una descarga.

## Fuentes

| Fuente | Qué significa «top songs» | Canciones listadas |
|--------|------------------------|--------------|
| Spotify | El estante **Popular** del propio artista, las mismas canciones que se muestran arriba en su página de Spotify | Hasta 10 |
| YouTube Music | La playlist **Top songs** del artista, ordenada por popularidad | Las primeras 50 |
| Deezer | El ranking **top** del propio artista (el mismo estante que `deezer.com` muestra en su página) | Las primeras 50 |

El embed público de Spotify no tiene discografía, así que Downtify lee los lanzamientos de la consulta de discografía del propio reproductor web de Spotify, la misma API no pública que usa para los nombres de álbum. Si Spotify la cambia, Downtify recurre a una lista más corta (todos los álbumes, pero solo los diez sencillos más recientes) y, si eso falla, no muestra lanzamientos. Las canciones de Spotify pasan por el pipeline habitual de metadatos y luego coincidencia de audio, con el nombre del álbum adjunto de antemano; la descarga completa el resto (número de canción, año) como con cualquier canción de Spotify. Las canciones de YouTube Music quedan fijadas a su propio vídeo, como cualquier otro enlace de YouTube Music. Deezer tiene un endpoint público de discografía de verdad, así que su lista de lanzamientos no necesita alternativa; sus canciones pasan por el mismo pipeline de metadatos y luego coincidencia de audio que las de Spotify, con un fragmento de vista previa de 30 segundos adjunto cuando Deezer lo ofrece.

## En la página de un artista en la Biblioteca

Un artista que Downtify conoce en Spotify (consulta [Foto, banner y biografía del artista](artist-images.md)) también obtiene una pestaña **Top songs** en su página de tu Biblioteca, junto a Canciones y A los fans también les gusta. Lista las primeras **5** de sus canciones más populares de Spotify como una lista mínima, como los resultados de búsqueda, bajo encabezados de columna (#, Título, Álbum, duración): número, portada, título, artista, álbum y duración. Una canción que no está en tu biblioteca tiene un botón de **descarga** a la derecha (con su progreso mientras se descarga); una vez descargada, pasa a la etiqueta **En la biblioteca**, y la canción se puede reproducir como en la página de un álbum: el número se convierte en un botón de reproducir al pasar el ratón, la portada reproduce, y un doble clic o un toque también reproducen. Reproducir una pone en cola las demás canciones descargadas de la lista después de ella, en orden de ranking, y la canción que suena queda resaltada. Una canción que aún no está descargada se **emite entera**: pasa el ratón por su fila y donde está el número aparece un botón de reproducir; púlsalo (o la portada) y suena en el reproductor integrado como una descargada (consulta [Escuchar canciones antes de descargar](#playing-songs-before-downloading)). Debajo de la lista, **Ver más canciones populares** abre este artista en la página Top Songs descrita arriba, donde viven la selección, el interruptor **Crear playlist** y la descarga de varias a la vez. La pestaña solo aparece cuando se conoce el id de Spotify del artista, lo que ocurre la primera vez que se abre su página; las canciones se piden en ese momento, así que el contador de la pestaña se rellena solo unos segundos después, estés donde estés en la página.

Leer la portada, el álbum y las reproducciones de una canción lleva unos segundos, así que Downtify guarda las cinco canciones en un archivo por artista, `<downloads>/.metadata/ArtistTopSongs/<Artista>.topsongs.json`, creado en segundo plano la primera vez que se abre la página del artista. Se considera fiable durante **7 días**: abrir la pestaña lee el archivo al instante, y cuando es más antiguo se muestra la lista vieja de inmediato mientras se obtiene una nueva por detrás — la página la cambia sola en unos segundos, sin molestar a una canción que se esté descargando o reproduciendo. El archivo solo guarda las canciones, su portada, los enlaces a los fragmentos y las reproducciones — nunca el audio ni las imágenes, y nunca si una canción está en tu biblioteca, lo que se calcula en vivo. Es una caché: bórrala cuando quieras y se vuelve a crear.

## Crear una playlist

El interruptor **Crear playlist** de la página Top Songs empieza **desactivado** la primera vez que abres un artista, y empieza **activado** cuando ya existe en tu biblioteca una playlist llamada **Top Songs of {artist}**, para que las descargas posteriores sigan añadiendo a ella. Cambia el interruptor y tu elección se mantiene mientras sigas en esa página. Desactivado, las canciones se descargan como cualquier otra canción suelta: directamente a tu carpeta de descargas, o a tus carpetas de artista/álbum cuando la [Organización de archivos](file-organization.md) está activada, sin carpeta propia, sin M3U y sin foto del artista.

Actívalo y Downtify las trata como una playlist llamada **Top Songs of {artist}**. Dónde va depende de la Organización de archivos:

| Organizar por artista / álbum | Canciones | M3U y portada |
|---|---|---|
| Ambos desactivados | En una carpeta llamada `Top Songs of {artist}` | En esa misma carpeta |
| Uno o ambos activados | Archivadas según esos ajustes: `<Artista>/`, `<Álbum>/` o `<Artista>/<Álbum>/`. No hay carpeta `Top Songs of {artist}`. | En `Playlists/`, como `Top Songs of {artist}.m3u` y `.jpg` |

En ambos casos:

- la [playlist M3U](m3u-export.md) lista las canciones **en el orden del ranking del artista**, aunque solo hayas marcado algunas;
- la foto del artista se guarda junto al M3U como su portada, si **Guardar la portada de la playlist** está activado (consulta [Portada de la playlist](playlist-cover-art.md)). No hay un ajuste aparte para esto.

## Limitaciones conocidas

::: warning Mezclar Spotify y YouTube Music para el mismo artista
El M3U de **Top Songs of {artist}** se mantiene sincronizado desde el [catálogo de playlists](library-catalog.md), que se indexa por ids de canción de Spotify. Si descargas las top songs de un artista desde **Spotify** y más tarde desde **YouTube Music** (o al revés), los archivos del segundo lote se descargan bien, pero la siguiente actualización del M3U los quita del archivo de la playlist, porque los ids de YouTube Music no caben en ese formato. Añadir más canciones de la **misma** fuente no se ve afectado.
:::

::: info Nombres de álbum de las canciones de Spotify
La página de artista de Spotify no dice de qué álbum es una canción. Downtify obtiene los nombres de álbum y las reproducciones de la misma API del reproductor de Spotify que usa para leer playlists completas: una petición extra por artista, más una por cada álbum que esa petición no lista. Esa API no es pública, así que si Spotify la cambia, la columna **Álbum** queda vacía en las canciones de Spotify y desaparece la insignia de reproducciones; las canciones se siguen descargando, pero Downtify tiene entonces que recuperar el álbum de su coincidencia en YouTube Music, que a menudo falla, dejando el archivo sin etiqueta de álbum y, con [Organizar por álbum](file-organization.md) activado, en una carpeta de álbum `unknown`. Las top songs de YouTube Music ya traen su álbum. Si las reproducciones dejan de llegar, en cualquiera de las fuentes, la insignia simplemente no aparece.
:::

## API

Consulta [`GET /api/artists/top_songs/url`](../api-reference.md#get-apiartiststop_songsurl) en la Referencia de la API.
