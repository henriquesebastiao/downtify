---
icon: lucide/mic-vocal
---

# Letras

Downtify busca letras mientras se descarga una canción y las incrusta en el archivo, además de un archivo auxiliar `.lrc` cuando están sincronizadas con el tiempo.

## Activar las letras

Las letras están **activadas por defecto**. Desactívalas en **Ajustes → Etiquetas y letras → Descargar letras**.

## Proveedores y orden de prueba

Los catálogos difieren: una canción que un proveedor no conoce suele estar en otro. Por eso Downtify mantiene una lista ordenada de proveedores y los prueba de uno en uno, deteniéndose en el primero que tenga algo.

| Proveedor | Letras | Notas |
|----------|--------|-------|
| **[LRCLIB](https://lrclib.net)** | Simples y sincronizadas | Base de datos comunitaria gratuita, sin clave. Coincidencia por título, artista principal, álbum y duración. |
| **NetEase Cloud Music** | Normalmente sincronizadas | Catálogo grande, fuerte en lanzamientos asiáticos y a menudo también en occidentales. Coincidencia por título, artista y duración; un resultado cuyo artista se escribe distinto (chino tradicional frente a simplificado, por ejemplo) solo se acepta cuando el título y la duración coinciden. |

En **Ajustes → Etiquetas y letras → Proveedores** puedes arrastrar los proveedores al orden que prefieras, o usar las flechas, y desactivar cualquiera de ellos. Al menos uno queda activado; para dejar de buscar letras por completo, usa el interruptor **Descargar letras**.

::: info ¿Y Genius, Musixmatch y AZLyrics?
No están disponibles, y Downtify ya no los ofrece:

- **AZLyrics** prohíbe el uso por terceros de sus letras en la propia página.
- La API de escritorio de **Musixmatch** responde con un token vacío salvo que tengas credenciales que no entrega a las aplicaciones.
- El `robots.txt` de **Genius** no permite el endpoint de búsqueda necesario para encontrar la página de una canción.

Los ajustes guardados que aún los nombran siguen funcionando: los nombres se ignoran, y una lista que se queda sin nada más vuelve a los proveedores predeterminados.
:::

## Omitir proveedores que no tenían nada

Tras una búsqueda, Downtify registra para cada canción qué proveedores respondieron y cuáles volvieron vacíos, en `downtify_library.db` dentro de `/data`.

A un proveedor que no tenía nada para una canción no se le vuelve a preguntar por ella durante **30 días**, para que las redescargas y los grandes repasos de la biblioteca no repitan las mismas búsquedas fallidas. Pasado ese tiempo se vuelve a probar, ya que los catálogos crecen. Un proveedor que *sí* tenía letra nunca se omite, así que un archivo redescargado la recupera.

## Incrustación

| Formato | Etiqueta de letra simple | Etiqueta de letra sincronizada |
|--------|-----------------|------------------|
| MP3 | `USLT` (ID3) | `USLT` con marcas de tiempo |
| FLAC | `LYRICS` (comentario Vorbis) | `LYRICS` con contenido LRC |
| M4A | `©lyr` | `©lyr` con contenido LRC |
| OGG / OPUS | `LYRICS` (comentario Vorbis) | `LYRICS` con contenido LRC |

## Archivo auxiliar .lrc

Cuando hay letras sincronizadas, Downtify también guarda un archivo `.lrc`. Por defecto está **junto al audio** con el mismo nombre base. En **Ajustes → Etiquetas y letras** puedes desactivarlo y elegir en su lugar una **carpeta de letras** (por defecto `/data/lyrics`). Esa carpeta debe estar **fuera** de `/downloads`, del árbol de slskd y de cualquier carpeta de música adicional — la ruta relativa del audio se recrea dentro de ella (`Artista/Álbum/canción.lrc`). Los reproductores que leen letras externas (y el [reproductor integrado](player.md#now-playing)) siguen encontrando el archivo auxiliar. Cambiar este ajuste y ejecutar **Sincronizar** en una carpeta adicional copia los `.lrc` existentes a la nueva ubicación; el archivo de origen se elimina cuando ese árbol es escribible, y se deja en su sitio en un montaje de solo lectura. Se escribe un archivo auxiliar aunque las letras ya estén incrustadas en las etiquetas.

Eliminar la canción desde la página de la Biblioteca elimina el `.lrc` (junto al archivo y en la carpeta dedicada) junto con el audio, así que la letra nunca queda como un archivo huérfano.

## Cuando no se encuentra nada

Si ningún proveedor tiene la canción, la descarga continúa con normalidad — el archivo de audio se guarda sin letras y no se genera ningún error.
