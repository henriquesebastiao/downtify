---
icon: lucide/folder-plus
---

# Carpetas de música existentes

La Biblioteca de Downtify se construye a partir de los archivos que descargó — más las **carpetas adicionales** que le indiques. Esas carpetas no se copian a `/downloads`. Downtify lee las etiquetas de cada archivo (título, artista, álbum, número de pista, año), omite las canciones que ya tienes y coloca el resto bajo el artista correspondiente en la Biblioteca y el reproductor.

## Añadir carpetas

1. Monta la carpeta del host en el contenedor (Docker). La ruta que escribes en Ajustes es la **de dentro del contenedor**, la misma regla que la [carpeta de descargas de slskd](slskd-navidrome.md).
2. Abre **Ajustes → Biblioteca**.
3. En **Carpetas de música existentes**, añade una o más rutas (por ejemplo, `/music/collection`). El campo sugiere directorios mientras escribes.
4. Pulsa **Guardar** si quieres conservarlas sin sincronizar todavía, o **Sincronizar carpetas** — eso guarda la lista y escanea de inmediato.

```yaml
services:
  downtify:
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

Entonces la carpeta en Ajustes es `/music/collection`.

::: warning Los archivos se quedan donde están
La sincronización no copia archivos a `/downloads`. Cuando la carpeta es escribible, **sí** escribe en esos archivos los mismos extras que una descarga: letras (y un archivo auxiliar `.lrc` — junto al archivo o en la carpeta elegida en Ajustes), una portada si el archivo no tiene ninguna, y el género de iTunes cuando es posible. Una sincronización posterior escribe un archivo auxiliar que falte aunque la letra ya esté en las etiquetas, y **mueve** un `.lrc` existente a la ubicación elegida actualmente en Ajustes cuando ese archivo de origen es escribible. Eliminar una canción desde la Biblioteca sigue eliminando ese archivo en disco.
:::

::: tip Montajes de solo lectura
Monta la colección con `:ro` si no quieres que Downtify reescriba los MP3. La sincronización los sigue indexando. Pon los archivos `.lrc` en la [carpeta de letras](lyrics.md#sidecar-lrc-file) (desactiva **Guardar .lrc junto al audio**). Las portadas que falten se guardan en `/data/cover_cache` (el endpoint de portadas de la Biblioteca), no en el MP3. El género de iTunes se guarda en la base de datos de metadatos de la biblioteca de Downtify, no en el archivo. Un `.lrc` que ya está junto a un archivo de solo lectura se **copia** a la carpeta de letras y se deja donde está.
:::

## Qué hace la sincronización

1. Recorre cada carpeta configurada en busca de audio reproducible (los mismos formatos que el resto de la biblioteca: MP3, M4A, FLAC, OGG, WAV, AAC, OPUS).
2. Lee las etiquetas incrustadas. Un archivo sin título/artista recurre a `Artista - Título` en el nombre del archivo, igual que otras filas de la biblioteca.
3. **Omite** un archivo cuando la biblioteca ya tiene esa canción (mismo artista + título, y duración con una diferencia de pocos segundos cuando ambas se conocen) — tanto si la descargó Downtify como si viene de otra carpeta adicional.
4. **Empareja artistas** con nombres ya presentes en la biblioteca (`The Beatles` y `Beatles` pasan a ser un solo artista). Los nombres que no coinciden con un artista conocido aparecen como un artista nuevo. Los artistas nuevos se ponen en cola para el mismo relleno de perfil (foto/bio cuando esos ajustes están activados) que una descarga terminada.
5. **Etiqueta como una descarga** cuando la carpeta es escribible. Para cada canción importada usa los mismos proveedores de letras, la misma búsqueda de portada (solo cuando el archivo no tiene imagen) y la misma búsqueda de género de iTunes que usaría una descarga. La letra va al archivo; un archivo auxiliar `.lrc` se escribe junto al audio o en la [carpeta de letras](lyrics.md#sidecar-lrc-file) elegida en Ajustes. La portada y el género siguen los [Ajustes de descarga](download-settings.md) (`download_cover_art`, `download_lyrics`). En un montaje de **solo lectura** el MP3 no se reescribe: una portada que falte se guarda en `/data/cover_cache`, el género se guarda en el catálogo de la biblioteca y los archivos `.lrc` van a la carpeta de letras si elegiste una. Las búsquedas se ejecutan en lotes de **Descargas simultáneas**; una **Pausa entre la sincronización** en Ajustes → Descargas y archivos espera entre esos lotes para que las carpetas grandes no topen con los límites de los proveedores.
6. Invalida la caché de rutas de la biblioteca para que la página de la Biblioteca y el reproductor vean el resultado sin esperar al breve TTL de escaneo habitual.

La sincronización se ejecuta **en segundo plano**. Puedes salir de Ajustes; si vuelves mientras sigue trabajando, verás que aún está sincronizando. Cuando ha terminado, Ajustes muestra el **último registro de sincronización** (importadas / duplicadas / errores, además de notas sobre letras/portadas).

Ejecuta **Sincronizar carpetas** de nuevo después de meter más archivos en esas carpetas. Guardar la lista de carpetas sin sincronizar también las incluye en el siguiente escaneo de la biblioteca (alrededor de un minuto, o la siguiente descarga/eliminación).

Quitar una carpeta de la lista la **desasigna**: esas canciones salen de la Biblioteca y del reproductor, y los extras creados por Downtify (archivos auxiliares `.lrc`, portadas en caché) se eliminan. Los archivos de audio en disco se quedan donde están.

Las carpetas que no existen o no se pueden leer se informan tras la sincronización; las demás se siguen escaneando.

## Rutas de la biblioteca

Los archivos de carpetas adicionales usan una ruta virtual `ext/<id>/…` (el id es un hash de la ruta de la carpeta, así que la lista se puede reordenar). El reproductor y `GET /media/…` usan esa ruta, como `slskd/…` para los archivos de Soulseek dejados en su sitio.

Una carpeta que ya está **dentro** de `/downloads` (o de la carpeta de origen de slskd) se ignora aquí — ese árbol ya es la biblioteca.

## API

| Método | Ruta                          | Descripción                                                                      |
| ------ | ----------------------------- | -------------------------------------------------------------------------------- |
| `POST` | `/api/library/external/sync`  | Inicia un escaneo en segundo plano. Un cuerpo opcional `{folders: ["/path", …]}` se guarda antes. |
| `GET`  | `/api/library/external/sync`  | Trabajo en curso, o el último registro terminado.                                |
| `POST` | `/api/library/external/unmap` | Quita una carpeta de la biblioteca sin eliminar el audio.                        |

Consulta la [referencia de la API](../api-reference.md#post-apilibraryexternalsync) para ver el formato de la respuesta.

## Carpeta principal de la biblioteca

Elige **Ajustes → Biblioteca → Primary library folder** para preferir una de las
carpetas externas registradas. El valor predeterminado conserva el comportamiento existente.
Se exigen artista, título completo (incluida la versión) y álbum coincidentes;
los metadatos desconocidos no ocultan otro archivo. Un origen seleccionado puede representar
una grabación cuya otra copia incluye intros o finales de clip.

Es una preferencia de listado, no una migración. Los archivos de origen, las rutas de playlists
almacenadas, la propiedad, los «me gusta» y las reglas de visibilidad no se reescriben ni se eliminan.
Las insignias de playlist se combinan en el representante mostrado; las playlists guardadas
explícitamente siguen reproduciendo sus rutas originales. Los álbumes y versiones distintos en
la carpeta elegida siguen separados. Una carpeta vacía o no disponible recurre al resto de la biblioteca.
Quitarla restablece la preferencia.
