---
icon: lucide/file-headphone
---

# Organización de archivos

Un servidor nuevo organiza los archivos por artista y álbum (`Artista/Álbum/…`): **Organizar por artista** y **Organizar por álbum** vienen activados por defecto. Desactívalos para obtener la estructura plana de abajo. Los servidores configurados antes de este valor predeterminado conservan la elección que tenían.

## Estructura plana (ambos desactivados)

Las canciones sueltas y las búsquedas de YouTube van directamente a la raíz de la carpeta de descargas. Las canciones de playlists y álbumes van a una subcarpeta por playlist o por álbum:

```
downloads/
├── My Playlist/
│   ├── My Playlist.m3u
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── Tame Impala - The Less I Know The Better.mp3
└── The Night Owls - R U Awake.mp3       ← canción suelta
```

## Organizar por artista

Con **Ajustes → Descargas y archivos → Organizar por artista** activado (el valor predeterminado), todas las canciones — incluidas las descargas de playlists y álbumes — se agrupan en una subcarpeta con el nombre del artista principal:

```
downloads/
├── The Night Owls/
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── The Night Owls - R U Awake.mp3
├── Tame Impala/
│   └── Tame Impala - The Less I Know The Better.mp3
└── Playlists/
    └── My Playlist.m3u
```

Esta estructura es compatible con servidores multimedia (Jellyfin, Navidrome, Plex) y gestores de bibliotecas (Beets) que esperan una organización de carpetas `Artista/Canción.ext`.

## M3U y carpetas de artista

Cuando *Organizar por artista* está activado y descargas una playlist de Spotify con la generación de M3U también activada, el M3U se coloca en `<downloads>/Playlists/<nombre-de-la-playlist>.m3u` en lugar de dentro de la subcarpeta de la playlist. Esto se debe a que las canciones ahora están repartidas por varias carpetas de artistas. Las rutas relativas dentro del M3U siguen resolviéndose correctamente dondequiera que montes la biblioteca.

## Cambiar el ajuste

El ajuste surte efecto de inmediato para todas las descargas **nuevas**. Los archivos que ya están en disco no se mueven.

## Eliminar una canción limpia las carpetas vacías

Eliminar una canción desde la página de la Biblioteca también elimina su carpeta de playlist, artista o álbum una vez que queda vacía — y sigue subiendo por las carpetas superiores que hayan quedado vacías (por ejemplo, la carpeta del artista cuando desaparece su último álbum), deteniéndose en la propia carpeta de descargas, que nunca se elimina. Una carpeta que aún contiene cualquier otra cosa — otra canción, un `.m3u`, un `cover.jpg` aún en uso — se deja en paz.

## Seleccionar y eliminar varias canciones a la vez

La lista de canciones de la Biblioteca tiene una casilla en cada canción, además de una casilla **Seleccionar todo** que selecciona todas las canciones que coinciden con el filtro actual (consulta la [página de la Biblioteca](library-catalog.md#library-page)). **Eliminar de la biblioteca** en la barra de selección las elimina todas en una sola petición (`DELETE /delete/batch`, consulta la [Referencia de la API](../api-reference.md)), con la misma limpieza por canción (`.lrc`, `cover.jpg` huérfano, carpetas vacías) que al eliminar una canción cada vez.

Para eliminar un álbum o una playlist entera, ábrelo y elige **Eliminar** en su menú **⋯**. Para todo lo de un artista, escribe su nombre en el filtro de la lista de canciones, luego **Seleccionar todo** y elimina.
