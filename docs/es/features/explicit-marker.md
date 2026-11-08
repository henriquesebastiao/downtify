---
icon: lucide/shield-alert
---

# Marca de contenido explícito

Una canción con letra explícita — lenguaje no apto para niños — lleva una pequeña **E** junto a su título, como en Spotify. Aparece dondequiera que te encuentres con la canción, antes y después de descargarla, y se queda con el archivo.

## Dónde la ves

- **Resultados de búsqueda, enlaces pegados, Listas de éxitos y el Buscador** — en cualquier canción que el servicio indique que es explícita. Lo sabes antes de descargar.
- **La Biblioteca** — en la pestaña Canciones, en las páginas de álbum, artista y playlist, y en el selector de «añadir canciones».
- **El reproductor** — junto al título en la barra del reproductor, en **Reproduciendo** y en **A continuación**.

Pasa el ratón por la **E** (o deja que un lector de pantalla la lea) para ver «Explícito».

## De dónde viene la marca

La decide el servicio del que descargas: Spotify, YouTube Music y Deezer marcan cada uno sus canciones explícitas, y Downtify usa lo que diga el que elegiste. Cuando Downtify descarga una canción de YouTube Music, la marca describe el **vídeo que realmente descarga**: si la canción es explícita en Spotify pero Downtify emparejó una edición limpia, el archivo no se marca, y si Spotify la da por limpia pero la coincidencia es explícita, sí se marca.

Una canción que el servicio no marca no recibe marca alguna — lo que no es lo mismo que estar certificada como limpia, y Downtify nunca escribe una marca de «limpia».

## En el archivo

La marca se escribe en las etiquetas del archivo, como lo hace iTunes, para que los servidores multimedia y reproductores que la entienden también puedan usarla. Navidrome lee exactamente estas etiquetas como el estado explícito de una canción.

| Formato | Etiqueta |
|--------|-----|
| MP3 | Marco de texto `ITUNESADVISORY` (`TXXX`), valor `1` |
| FLAC, OGG, OPUS | Comentario `ITUNESADVISORY`, valor `1` |
| M4A | Átomo `rtng`, valor `1` |

Los archivos que ya tenías se leen igual: todo lo que iTunes, MusicBrainz Picard u otro editor de etiquetas haya marcado con `1` (o el antiguo `4`) también muestra la **E**, incluidas las canciones de [carpetas adicionales](external-library.md).

::: info Canciones descargadas antes de esta versión
Los archivos que Downtify escribió antes de que existiera la marca no tienen nada en las etiquetas, así que no muestran la **E**, aunque la canción sea explícita. Descarga la canción de nuevo con [Reemplazar audio](replace-audio.md) o desde cero para marcarla. Un archivo conserva su marca cuando [Mejorar la biblioteca](library-upgrade.md) o Reemplazar audio lo reescribe: la marca solo se añade, nunca se borra.
:::

La primera vez que la Biblioteca se carga tras actualizar, Downtify vuelve a leer las etiquetas de todos los archivos para buscar la marca, como hizo cuando aprendió a mostrar códec y género. En una biblioteca grande en un disco lento tarda un momento, una sola vez.

## Para quien desarrolla apps

El [contrato del cliente móvil](../mobile-client-contract.md) y la [referencia de la API](../api-reference.md#get-tracks) describen el campo `explicit`: `true` en las canciones explícitas, ausente en las demás.
