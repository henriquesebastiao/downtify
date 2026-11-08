---
icon: lucide/heart
---

# Canciones que me gustan

Toca el corazón de una canción para marcarla como favorita. En cuanto una canción te gusta, Downtify mantiene una playlist **Canciones que me gustan** con todas las que has marcado, de modo que tus favoritas quedan a un clic — en Downtify y en cualquier servidor multimedia apuntado a tu biblioteca.

No hay nada que activar.

Los corazones pertenecen a quien los tocó: en un servidor con varias cuentas cada persona tiene sus propias canciones favoritas (consulta [Usuarios e inicio de sesión](users.md#your-library)). El archivo de la playlist en disco contiene los corazones de los administradores; los «me gusta» de todos los demás viven en la base de datos de la biblioteca y funcionan igual en las apps.


## Marcar una canción

El corazón está junto a cada canción de tu biblioteca — descargas y canciones de [carpetas de música existentes](external-library.md):

- en las listas de canciones — Biblioteca, álbumes, artistas y playlists;
- en la [barra del reproductor](player.md#player-bar) (en pantallas de 640 px de ancho o más);
- en [Reproduciendo ahora](player.md#now-playing), junto al título de la canción.

Tócalo para marcarla y tócalo otra vez para quitar la marca. Se rellena en verde y el cambio llega al servidor al instante, así que un corazón tocado en el móvil también está en tu ordenador — las pestañas y los dispositivos abiertos se actualizan solos.

Solo se pueden marcar canciones de tu biblioteca. Un resultado de búsqueda que aún no has descargado no tiene corazón; descárgalo primero.

## La playlist

El primer «me gusta» crea la playlist, y un aviso breve ofrece abrirla. Aparece como cualquier otra playlist — en la barra lateral, en la página de Inicio y en **Biblioteca → Playlists** —, pero siempre la **primera**, con un corazón en lugar de portada. Sus canciones están ordenadas con la marcada más recientemente arriba.

Al quitar el último «me gusta» se elimina de nuevo la playlist; no queda por ahí unas **Canciones que me gustan** vacías.

El título sigue tu [idioma](internationalization.md). En disco, la playlist es un [archivo M3U](m3u-export.md) sencillo con un nombre fijo:

```
<downloads>/Playlists/Downtify Liked Songs.m3u
```

Por eso Jellyfin, Navidrome, Plex y compañía también la muestran: leen el mismo archivo. El nombre está reservado a propósito. Las playlists de Spotify llamadas *Liked Songs* son habituales, y una playlist descargada con ese nombre habría acabado escribiendo en el mismo archivo.

## Quitar todos los «me gusta»

Abre la playlist, luego **⋯ → Quitar todos los «me gusta»** y confirma. Se borran todos los corazones y la playlist desaparece.

::: info Tus canciones se quedan
Quitar los «me gusta» nunca borra audio. Solo se eliminan los corazones y la playlist — los archivos siguen en tu biblioteca. Es distinto de eliminar una playlist descargada, que elimina sus canciones; **Canciones que me gustan** nunca se trata así. Pedir que se elimine (en la app o a través de la [API](../api-reference.md#delete-apilibraryplaylist)) solo borra los «me gusta».
:::

## Mantener los «me gusta» al día con los archivos

Un «me gusta» sigue al archivo al que se dio:

| Qué le pasa al archivo | Qué le pasa al «me gusta» |
|--------------------------|--------------------------|
| Eliminas la canción en Downtify | El «me gusta» se va con ella y la playlist se reescribe |
| La mueves y ejecutas [Corregir rutas de la biblioteca](library-catalog.md#fix-library-paths) | El «me gusta» sigue al archivo a su nuevo lugar |
| Desaparece fuera de Downtify (una unidad desmontada, un borrado manual) | El «me gusta» se conserva, pero la canción queda fuera de la playlist hasta que vuelva |

Conservar el «me gusta» de un archivo ausente significa que una unidad desconectada no te cuesta tus corazones. Si borraste archivos a mano y quieres que se vayan también los «me gusta», usa **Quitar todos los «me gusta»**, o quita la marca a las canciones antes de borrarlas.

## Conviene saber

- Los «me gusta» se guardan en la base de datos de la biblioteca (`downtify_library.db`, en tu volumen `/data`), no en los archivos de audio. No se escribe nada en las etiquetas de la canción.
- Downtify no crea la playlist en [Navidrome](slskd-navidrome.md). Es un archivo M3U sencillo, así que lo que un servidor multimedia haga con él depende de cómo lea ese servidor los archivos M3U.
- El [archivo de la playlist](m3u-export.md) se escribe incluso con *Escribir playlists M3U* desactivado en los ajustes de descarga: la playlist es el objetivo de la función.

## API

`GET /api/likes`, `PUT /api/likes` y `POST /api/likes/clear`, además de un indicador `liked` en [`GET /playlists`](../api-reference.md#get-playlists). Consulta la [referencia de la API](../api-reference.md#likes).
