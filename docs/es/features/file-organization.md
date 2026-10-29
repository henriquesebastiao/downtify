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

Con **Ajustes → Descargas y archivos → Organizar por artista** activado (el valor predeterminado), todas las canciones — incluidas las descargas de playlists y álbumes — se agrupan en una subcarpeta con el nombre del artista del álbum (consulta [Varios artistas y recopilatorios](#several-artists-and-compilations)):

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

## Varios artistas y recopilatorios

Una canción a menudo acredita a varios artistas. Downtify los guarda todos en la etiqueta **Artista** del archivo y además escribe cada uno por separado en una etiqueta **ARTISTS** (`TXXX:ARTISTS` en MP3), para que un reproductor nunca tenga que partir un nombre como `Earth, Wind & Fire` por su coma. La carpeta, en cambio, pertenece a un solo artista: el **artista del álbum**, o en un recopilatorio el primer artista de la canción.

- El artista del álbum es el artista que la fuente (Spotify, YouTube Music o Deezer) acredita para el **álbum**, el mismo en todas sus canciones, y se escribe en la etiqueta **Artista del álbum**. Si la fuente no lo dice, es el primer artista de la canción.
- Un dúo o un grupo es un solo artista. YouTube Music acredita a algunos por sus integrantes, uno por entrada (`Henrique & Juliano` llega como `Henrique` y `Juliano`, en el álbum y en cada canción — a veces en el otro orden, `Mateus` y `Jorge` para `Jorge & Mateus`). Cada nombre acreditado enlaza a un canal de YouTube Music; cuando el enlace de un integrante lleva a un canal con el nombre del grupo entero, formado por los nombres acreditados junto a él, Downtify vuelve a unir esos nombres en el nombre del grupo: la carpeta y las etiquetas **Artista del álbum**, **Artista** y **ARTISTS** dicen `Henrique & Juliano`. Una colaboración real (cada artista en su propio canal) conserva a todos los artistas. Cuando YouTube Music no enlaza a ningún integrante con el canal del grupo, los nombres quedan separados; aun así, la Biblioteca no da página a un nombre que solo aparece acreditado junto a otro (consulta [Catálogo de la biblioteca](library-catalog.md#library-page)).
- Un invitado nunca lo cambia. *The Girl Is Mine*, con un invitado en *Thriller* de Michael Jackson, queda en `Michael Jackson/Thriller/`, y el sencillo *Lady Marmalade* (Christina Aguilera, Lil' Kim, Mýa, P!nk) va a `Christina Aguilera/`.
- Solo un álbum que la propia fuente acredita a **Various Artists** (una banda sonora, un "Now That's What I Call…") es un recopilatorio — salvo que [lo marques tú](#marking-an-album-as-various-artists). Una canción suelta de YouTube Music nunca lo es: YouTube Music archiva el mismo audio en varios lanzamientos y puede mostrar cualquiera como su álbum, a menudo un recopilatorio, así que solo cuenta la descarga de un álbum entero de YouTube Music. Sus canciones reciben "Various Artists" como artista del álbum más la marca de recopilatorio (`TCMP` en MP3, `COMPILATION` en FLAC/Ogg/Opus, `cpil` en M4A). Eso mantiene el álbum entero en Navidrome y otros servidores multimedia, que agrupan los álbumes por estas etiquetas y no por carpeta. En el disco, sin embargo, **Organizar por artista** nunca crea una carpeta `Various Artists`: cada canción va a la carpeta de su primer artista.
- Las versiones antiguas de Downtify etiquetaban **Various Artists** cualquier canción con varios artistas, sin la marca de recopilatorio. La Biblioteca sigue listando esa canción en el álbum de su primer artista, como antes; **Marcar como Varios artistas** convierte el álbum en un recopilatorio real.

```
downloads/
├── Christina Aguilera/
│   ├── Lady Marmalade/
│   │   └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
│   └── Moulin Rouge/                  ← de la banda sonora (un recopilatorio)
│       └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
└── David Bowie/
    └── Moulin Rouge/                  ← misma banda sonora
        └── David Bowie - Nature Boy.mp3
```

*Lady Marmalade* del sencillo y de la banda sonora de *Moulin Rouge* son dos lanzamientos, cada uno archivado con su propio álbum. Las canciones de la banda sonora se reparten por las carpetas de sus artistas, pero etiquetadas como un recopilatorio "Various Artists", así que la Biblioteca y los servidores multimedia siguen mostrando *Moulin Rouge* como un solo álbum.

### Marcar un álbum como Varios artistas

Una fuente puede acreditar un lanzamiento a un solo artista cuando pertenece a varios por igual — Deezer lista el sencillo *Lady Marmalade* solo bajo Christina Aguilera. Un administrador lo corrige desde la página del álbum en la Biblioteca, con el botón **Marcar como Varios artistas** junto a **Añadir a la cola**.

- Cada canción del álbum recibe "Various Artists" como artista del álbum y la marca de recopilatorio. Nada más cambia en los archivos, y se quedan donde están (las canciones de un recopilatorio ya van a la carpeta de su primer artista). Cada archivo se reescribe mediante una copia de trabajo, conserva su fecha de modificación y queda intacto si la reescritura falla.
- En la Biblioteca, el álbum pasa a aparecer por **Various Artists** en **Álbumes** (cada canción sigue en la página de su artista), y la página del álbum lo sigue.
- Downtify recuerda el álbum: una canción suya descargada más tarde recibe las mismas etiquetas.
- En un recopilatorio, el mismo botón dice **Desmarcar como Varios artistas**: deshace la marca y devuelve el artista del álbum que tenía. También funciona en un álbum que su fuente hizo recopilatorio; entonces el artista del álbum pasa a ser el artista que la mayoría de sus canciones lista primero, y las descargas posteriores de ese álbum ya no se marcan.

Solo los administradores ven el botón. Los servidores multimedia recogen el cambio en su próximo escaneo de la biblioteca.

## M3U y carpetas de artista

Cuando *Organizar por artista* está activado y descargas una playlist de Spotify con la generación de M3U también activada, el M3U se coloca en `<downloads>/Playlists/<nombre-de-la-playlist>.m3u` en lugar de dentro de la subcarpeta de la playlist. Esto se debe a que las canciones ahora están repartidas por varias carpetas de artistas. Las rutas relativas dentro del M3U siguen resolviéndose correctamente dondequiera que montes la biblioteca.

## Cambiar el ajuste

El ajuste surte efecto de inmediato para todas las descargas **nuevas**. Los archivos que ya están en disco no se mueven.

## Eliminar una canción limpia las carpetas vacías

Eliminar una canción desde la página de la Biblioteca también elimina su carpeta de playlist, artista o álbum una vez que queda vacía — y sigue subiendo por las carpetas superiores que hayan quedado vacías (por ejemplo, la carpeta del artista cuando desaparece su último álbum), deteniéndose en la propia carpeta de descargas, que nunca se elimina. Una carpeta que aún contiene cualquier otra cosa — otra canción, un `.m3u`, un `cover.jpg` aún en uso — se deja en paz.

## Seleccionar y eliminar varias canciones a la vez

La lista de canciones de la Biblioteca tiene una casilla en cada canción, además de una casilla **Seleccionar todo** que selecciona todas las canciones que coinciden con el filtro actual (consulta la [página de la Biblioteca](library-catalog.md#library-page)). **Eliminar de la biblioteca** en la barra de selección las elimina todas en una sola petición (`DELETE /delete/batch`, consulta la [Referencia de la API](../api-reference.md)), con la misma limpieza por canción (`.lrc`, `cover.jpg` huérfano, carpetas vacías) que al eliminar una canción cada vez.

Para eliminar un álbum o una playlist entera, ábrelo y elige **Eliminar** en su menú **⋯**. Para todo lo de un artista, escribe su nombre en el filtro de la lista de canciones, luego **Seleccionar todo** y elimina.
