---
icon: lucide/sparkles
---

# Funciones

Downtify cubre todo lo que necesitas para crear y mantener una biblioteca de música local a partir de Spotify.

## Resumen

| Función | Qué hace |
|---------|-------------|
| [Listas de éxitos](charts.md) | Explora la lista global de Deezer y descarga lo que está en tendencia |
| [Similares](similar.md) | Indica un artista o una canción; YouTube Music responde con canciones parecidas que se reproducen completas y se pueden descargar, sin clave |
| [Buscador](finder.md) | Busca en Deezer y luego explora un artista, sus álbumes y las canciones de cualquier álbum en columnas |
| [Ajustes de descarga](download-settings.md) | Elige el formato (MP3/FLAC/M4A/OGG/OPUS), la tasa de bits, las descargas simultáneas y la pausa entre descargas |
| [Cola de descargas](download-queue.md) | Pausa las descargas antes de cambiar ajustes o actualizar: las que están en curso terminan, no empieza ninguna nueva y las canciones en espera sobreviven a un reinicio |
| [Monitor de playlists](playlist-monitor.md) | Vigila playlists y artistas de Spotify o YouTube Music y descarga automáticamente canciones y lanzamientos nuevos |
| [Canciones ocultas de una playlist](hidden-playlist-songs.md) | Quita de una playlist descargada o vigilada las canciones que no quieres y mantenlas fuera; los archivos siguen en la biblioteca |
| [Canciones más populares](top-songs.md) | Pega el enlace de un artista y descarga sus canciones más populares, opcionalmente como playlist |
| [Importar biblioteca (CSV)](library-import.md) | Importa una exportación de Soundiiz, TuneMyMusic o Exportify y pon todo en cola |
| [Reproductor integrado](player.md) | Reproduce tu biblioteca en el navegador: gestión de la cola, letras sincronizadas, temporizador de apagado, teclado y teclas multimedia |
| [Canciones que me gustan](liked-songs.md) | Dale un corazón a una canción para marcarla; una playlist con todo lo que te gusta aparece sola |
| [Podcasts](podcasts.md) | Suscríbete a un programa por feed RSS, enlace de Spotify o nombre; los episodios nuevos se descargan y etiquetan solos |
| [Usuarios e inicio de sesión](users.md) | Inicio de sesión con usuario y contraseña (`admin` / `downtify` en un servidor nuevo), cuentas de administrador y de usuario normal, preferencias por usuario y un registro de actividad con inicios de sesión y lo que escucha cada uno |
| [Marca de contenido explícito](explicit-marker.md) | La «E» junto a las canciones con letra explícita — en la búsqueda, la Biblioteca y el reproductor — y en las etiquetas del archivo |
| [Reemplazar audio](replace-audio.md) | ¿Canción o versión equivocada? Elige la correcta en YouTube Music o YouTube; el archivo conserva su nombre, etiquetas y playlists |
| [Ajustes del servidor](server.md) | El puerto en el que escucha Downtify, cambiado desde Ajustes (administradores), con reinicio inmediato si quieres |
| [Apps móviles](mobile-apps.md) | Vincula apps de móvil por código QR y emite la biblioteca hacia ellas (original o transcodificada) |
| [Descubrir](discover.md) | Artistas, álbumes y playlists que aún no tienes, sugeridos a partir de tu biblioteca, tus «me gusta» y lo que escuchas; oculta los que no quieras |
| [slskd y Navidrome](slskd-navidrome.md) | Descarga de Soulseek mediante slskd, refleja playlists en Navidrome y haz seguimiento de las descargas de playlists |
| [Catálogo de la biblioteca y sincronización de rutas](library-catalog.md) | Cómo Downtify sigue los archivos y playlists de la biblioteca, las playlists que creas en la Biblioteca y la corrección de rutas tras mover archivos |
| [Carpetas de música existentes](external-library.md) | Apunta Downtify a carpetas de audio que ya tienes; la sincronización lee las etiquetas, empareja artistas y omite las canciones que ya están en la biblioteca |
| [Mejorar la biblioteca](library-upgrade.md) | Escanea la música ya descargada y repara portadas pequeñas, letras que faltan y etiquetas incompletas |
| [Exportación M3U](m3u-export.md) | Archivos de playlist generados automáticamente para Jellyfin, Navidrome, Plex y cualquier app multimedia |
| [Portadas de playlists](playlist-cover-art.md) | Guarda la imagen de portada de la propia playlist junto a su archivo M3U |
| [Foto, banner y bio del artista](artist-images.md) | Elige una foto y un banner reales para un artista de YouTube Music, Deezer, Spotify o una subida propia, y obtén su bio, origen y enlaces de Apple Music y Deezer, automáticamente o a demanda |
| [Apoyar al artista](support-artists.md) | Encuentra dónde comprar una canción, un álbum o un artista: el artículo en la iTunes Store con su precio, Bandcamp y Qobuz, la web del artista |
| [Organización de archivos](file-organization.md) | Estructura plana o subcarpetas por artista |
| [Letras](lyrics.md) | Descarga e incrusta letras automáticamente (simples y sincronizadas); `.lrc` junto al archivo o en una carpeta que elijas |
| [Cookies de YouTube](youtube-cookies.md) | Sube un `cookies.txt` desde la interfaz web para descargar canciones explícitas/con restricción de edad |
| [Internacionalización](internationalization.md) | Inglés y nueve idiomas más de serie, y la documentación en todos ellos |
| [Avisos de actualización](updates.md) | Comprobación cada hora en los Releases de GitHub; aparece un aviso en la barra lateral cuando hay una versión más reciente |

## Tipos de entrada

Downtify acepta varios tipos de entrada en la barra de búsqueda:

| Entrada | Ejemplo |
|-------|---------|
| URL de canción, álbum, playlist o artista de Spotify | `https://open.spotify.com/track/…` |
| URL de YouTube / YouTube Music | `https://www.youtube.com/watch?v=…` |
| URL de playlist o artista de YouTube Music | `https://music.youtube.com/playlist?list=…` |
| URL de canción, álbum, playlist o artista de Deezer | `https://www.deezer.com/track/…` |
| Búsqueda de texto libre | `The Night Owls Do I Still Recall` |

Las búsquedas de texto libre van directamente a YouTube Music — no hace falta un enlace de Spotify.
