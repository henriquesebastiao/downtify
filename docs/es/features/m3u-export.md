---
icon: lucide/list-music
---

# Exportación M3U

Downtify genera automáticamente un archivo de playlist `EXTM3U` estándar cada vez que se descarga una playlist de Spotify — ya sea manualmente o mediante el [Monitor de playlists](playlist-monitor.md).

## Ubicación del archivo

| Situación | Ruta del M3U |
|-----------|---------|
| Playlist descargada normalmente | `<downloads>/<nombre-de-la-playlist>/<nombre-de-la-playlist>.m3u` |
| Playlist descargada con *Organizar por artista* activado | `<downloads>/Playlists/<nombre-de-la-playlist>.m3u` |

Con *Organizar por artista* activado, las canciones se reparten por varias carpetas de artistas, así que el M3U se coloca en un directorio central `Playlists/` en lugar de la subcarpeta de la playlist.

Las [canciones que me gustan](liked-songs.md) también se escriben en `Playlists/Downtify Liked Songs.m3u`, sea cual sea la organización y esté o no activado *Generar playlists M3U*.

## Rutas relativas

Las rutas de las canciones dentro del M3U se escriben **relativas al propio archivo M3U**, no como rutas absolutas. Esto significa que el mismo archivo funciona tanto leído desde dentro del contenedor de Downtify (`/downloads/…`) como desde otro consumidor que monte la misma biblioteca en otra raíz — por ejemplo, Jellyfin en `/nas/music/…`. Basta con apuntar tu servidor multimedia al mismo punto de montaje de la biblioteca y la playlist aparecerá como una unidad.

## Activar / desactivar

La generación de M3U se controla en **Ajustes → Descargas y archivos → Generar playlists M3U** (activada por defecto). Desactivarla omite por completo la creación del M3U; el resto del flujo de descarga no cambia.

## Portada

Justo debajo de ese ajuste, **Guardar la portada de la playlist** (activada por defecto) escribe la imagen de portada de la propia playlist junto a su M3U, con el mismo nombre — antes que las canciones, para que la carpeta parezca la playlist desde el principio. Downtify muestra entonces esa imagen para la playlist en lugar de una cuadrícula con las portadas de sus canciones. Una playlist que creas en la Biblioteca recibe un mosaico de hasta cuatro portadas de canciones, escrito del mismo modo. Consulta [Portadas de playlists](playlist-cover-art.md).

## Cuándo se escribe

El M3U se reescribe **después de que termine de descargarse cada canción**, así que el archivo de la playlist crece conforme avanza la descarga en lugar de aparecer de golpe al final. Esto se aplica a las descargas de playlists y álbumes, a las [importaciones de CSV](library-import.md) y a los barridos del [Monitor de playlists](playlist-monitor.md#m3u-integration) por igual.

Eso significa que la playlist se puede reproducir desde que llega la primera canción, ves que la sincronización funciona sobre la marcha, y una sola descarga lenta o colgada nunca puede impedir que el M3U — o las canciones que ya terminaron — aparezca.

Una reescritura final se ejecuta cuando termina toda la tanda. Resuelve cada canción contra el sistema de archivos (en lugar de contra la lista en memoria de lo que descargó esta tanda), por lo que también recoge archivos de tandas anteriores y corrige cualquier cosa que haya cambiado en disco durante la ejecución.

Cada escritura lista las canciones en **el orden de la playlist**, no en el orden en que terminaron las descargas, así que un M3U escrito a medias sigue bien ordenado.

::: info Canciones que ya están en disco
Las canciones descargadas en una tanda anterior permanecen en el M3U todo el tiempo — se incluyen desde la primera escritura, no solo en la final.
:::

## Regeneración

El M3U se regenera desde cero en cada ejecución — volver a pegar la misma URL de playlist produce un archivo completo y en orden, incluidas las canciones que faltaban en ejecuciones anteriores.

Las canciones que fallaron al descargarse o que no tuvieron coincidencia en YouTube Music se omiten en silencio.

## Compatibilidad

El archivo generado usa:

- Codificación UTF-8, sin BOM
- Saltos de línea LF
- El formato estándar `#EXTM3U` / `#EXTINF`

Es compatible con Jellyfin, Navidrome, Plex, VLC, Kodi, Sonos y cualquier otro reproductor o servidor multimedia que consuma playlists M3U estándar.

## Playlists que creas

**Biblioteca → Playlists → Nueva playlist** escribe el mismo tipo de M3U en `Playlists/`, con una línea extra `#EXTDOWNTIFY:manual` para que Downtify la distinga de una playlist descargada de Spotify/YouTube. Puedes renombrarla y añadir o quitar canciones (incluidas las de [carpetas adicionales](external-library.md)). Eliminar esa playlist, eliminar una canción o desasignar una carpeta adicional actualiza el M3U; el audio solo se elimina cuando eliminas la propia canción o una playlist importada.

### Añadir canciones a una playlist

Los administradores pueden poner canciones en una de estas playlists, o en una nueva, desde varios sitios:

- **El menú ⋯ de una canción** (en cualquier lista de canciones) → **Añadir a playlist**.
- **Selecciona varias canciones** en la Biblioteca y pulsa **Añadir a playlist**.
- **El menú ⋯ de un álbum** → **Añadir a playlist** añade todas las canciones del álbum.
- **El menú ⋯ de un artista** (en la página del artista) → **Añadir a playlist** añade todo lo que el artista tiene en tu biblioteca, álbum por álbum.

Cada menú lista tus playlists y una entrada **Nueva playlist…** que crea una ya con esas canciones. Una canción que la playlist ya tiene se omite, y la confirmación indica cuántas se añadieron de verdad (o que ya estaban todas). Una playlist admite como máximo 500 canciones.
