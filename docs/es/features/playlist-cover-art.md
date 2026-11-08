---
icon: lucide/image
---

# Portadas de playlists

Downtify puede guardar la portada de la propia playlist junto a su [archivo M3U](m3u-export.md), para que los servidores multimedia y los exploradores de archivos muestren la imagen real de la playlist en lugar de un icono genérico.

Activado por defecto. Desactívalo en **Ajustes → Descargas y archivos → Guardar la portada de la playlist**.

## Dónde va el archivo

La portada se escribe con el **mismo nombre y en la misma carpeta que el M3U de la playlist**, con la extensión `.jpg`:

```
<downloads>/<nombre-de-la-playlist>/<nombre-de-la-playlist>.m3u
<downloads>/<nombre-de-la-playlist>/<nombre-de-la-playlist>.jpg
```

Con *Organizar por artista* u *Organizar por álbum* activado, las canciones se reparten por carpetas de artistas y el M3U va a un directorio central `Playlists/` (consulta [Organización de archivos](file-organization.md)) — la portada lo acompaña:

```
<downloads>/Playlists/<nombre-de-la-playlist>.m3u
<downloads>/Playlists/<nombre-de-la-playlist>.jpg
```

::: info Necesita el M3U
Con **Generar playlists M3U** desactivado, tampoco se guarda ninguna portada: Downtify coloca la imagen según la ruta del M3U, así que sin él no hay dónde ponerla. El ajuste se oculta mientras la escritura de M3U está desactivada.
:::

## Fuentes y resolución

| Fuente | Resolución |
|--------|-----------|
| **Spotify** | La imagen más grande que ofrece su página pública de inserción para la playlist — la misma que ya se usa para las portadas de las canciones |
| **YouTube Music** | Siempre solicitada a 1200×1200, independientemente de la [Resolución de la portada](download-settings.md#cover-art-resolution), que solo afecta a las portadas por canción |

Ambos servicios sirven JPEG para estas URL aunque la imagen original fuera un PNG, así que el archivo siempre se guarda como `.jpg`.

## Cuándo se descarga

**Antes que las canciones**, en ambos casos — la carpeta ya se parece a la playlist mientras se llena, y un servidor multimedia que escanee a mitad de la descarga encuentra la imagen en lugar de una carpeta vacía:

- **Una descarga manual de playlist** — una vez, en cuanto se resuelve el nombre de la playlist, antes de que empiece la primera canción.
- **[Monitor de playlists](playlist-monitor.md)** — una vez por barrido que tenga algo que descargar, antes de la primera canción de ese barrido. Un barrido que no encuentra nada nuevo no la vuelve a obtener.

Si no se puede resolver o descargar la portada (un error de red, una playlist sin imagen), se registra en el log y se omite — nunca retrasa ni hace fallar la propia descarga.

## En la interfaz de Downtify

Una playlist que tiene su propia imagen (descargada con una playlist de Spotify o YouTube) la muestra dondequiera que la Biblioteca lista playlists — la cuadrícula, la página de la playlist, la barra lateral y el reproductor. Las playlists sin ella, y las que creas en la Biblioteca, muestran un mosaico de hasta cuatro portadas de canciones distintas: dos una junto a otra, tres como un bloque alto a la izquierda y dos apilados a la derecha, cuatro en una cuadrícula de 2×2. El mismo collage se escribe como `<nombre-de-la-playlist>.jpg` junto al M3U de una playlist manual para que Navidrome también lo vea, y se rehace cada vez que añades o quitas canciones.

## Navidrome

No hay nada que configurar: Navidrome resuelve la imagen de las playlists a partir de una **imagen auxiliar** — un archivo con el nombre de la playlist, en la misma carpeta — que es exactamente lo que escribe Downtify. Mientras la carpeta de música de Navidrome abarque tu carpeta de descargas, la imagen aparece en su siguiente escaneo. No interviene ninguna llamada de API de Downtify. Consulta [slskd y Navidrome](slskd-navidrome.md#navidrome).

## Limpieza

Eliminar una playlist desde la página de la Biblioteca elimina su portada junto con su M3U y sus canciones — consulta [Eliminar una playlist](slskd-navidrome.md#deleting-a-playlist).
