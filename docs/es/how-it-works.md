---
icon: lucide/cog
---

# Cómo funciona

El pipeline de descarga de Downtify tiene tres etapas:

```
Spotify embed  →  YouTube Music search  →  yt-dlp + ffmpeg + mutagen
  (metadata)         (audio match)          (download & tag)
```

## 1. Metadatos — extracción de la página de inserción de Spotify

Cuando pegas una URL de Spotify, Downtify obtiene la página pública `open.spotify.com/embed` de esa canción, álbum o playlist. No hace falta cuenta de Spotify, clave de API ni suscripción Premium — la página de inserción es de acceso público.

Para las **canciones**, la inserción devuelve: título, artista(s), nombre del álbum, año de lanzamiento, duración y la URL de la portada.

Para **álbumes y playlists**, devuelve la lista de canciones. Las inserciones de playlist están limitadas a unas 50–100 entradas, así que Downtify también pide la lista completa al endpoint anónimo `api.spotify.com` de Spotify, con paginación, para manejar playlists de cientos de canciones.

::: info Enriquecimiento de metadatos por canción
Las entradas de playlist en la inserción no traen el año de lanzamiento y usan la portada de la playlist en lugar de la portada del álbum de cada canción. Para el [Monitor de playlists](features/playlist-monitor.md), Downtify vuelve a pedir cada canción nueva individualmente para obtener la portada y el año correctos antes de descargarla.
:::

## 2. Coincidencia de audio — YouTube Music y luego YouTube

Downtify usa [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) para buscar en YouTube Music la mejor coincidencia de audio. La consulta se construye con el título de la canción y el nombre del artista.

Un resultado solo se acepta si su título se parece al original y comparte al menos un artista. El sufijo de versión con guion de Spotify y el entre paréntesis de YouTube Music se tratan como iguales (`Tubarões - Ao Vivo` coincide con `Tubarões (Ao Vivo)`), y un crédito de artistas que YouTube Music agrupa en una sola entrada (`A, B, and C`) se separa antes de comparar. Un «The» inicial en los nombres de artista se ignora (`Eden Project` coincide con `The Eden Project`), y un título puede coincidir con una parte del título de la subida separada por ` - ` (`くちづけDiamond - Kuchizuke Diamond`, `Game OST - Song Title - Artist`) siempre que las demás partes no indiquen una versión distinta. Las versiones de karaoke, cover, instrumental, acelerada/ralentizada, en directo (incl. `Ao Vivo`/`En Vivo`), acústica, remix y en otro idioma (p. ej., `(Spanish Version)`) se rechazan salvo que la propia canción de origen sea esa versión. Entre los resultados restantes gana el de duración más cercana a la de Spotify, con una bonificación si coincide el nombre del álbum. Si ningún resultado cumple, la búsqueda se repite con las palabras en el otro orden (`<título> <artista>` en lugar de `<artista> <título>`) — YouTube Music ordena los resultados de forma distinta según el orden de las palabras, y algunas canciones solo aparecen cerca de la cabeza de una forma. Si eso tampoco encuentra nada y se conoce el álbum, se examina directamente la lista de canciones del álbum.

### Alternativa: YouTube estándar

Algunas canciones faltan en YouTube Music, o allí solo existen como otra grabación. Por eso también se busca en YouTube estándar cuando:

- YouTube Music **no tiene ninguna coincidencia aceptable**, o
- la duración de su mejor coincidencia difiere **más de 10 segundos** de la de Spotify — un fuerte indicio de que es otra grabación (p. ej., una versión doblada con el mismo título).

Los resultados de YouTube estándar pasan por las mismas comprobaciones de título, artista y versión, y nunca se aceptan con más de 30 segundos de diferencia respecto a la duración de Spotify. Un resultado de YouTube solo sustituye a una coincidencia débil de YouTube Music cuando su duración es estrictamente más cercana; si no, se conserva la de YouTube Music, ya que sus subidas de catálogo suelen tener el audio más limpio.

Si ninguno de los dos sitios tiene una coincidencia aceptable, la canción falla con `Could not find a YouTube match for '<title>'` en lugar de descargar la canción equivocada.

Para las URL de YouTube introducidas directamente, este paso se omite — Downtify descarga ese vídeo concreto.

::: info Enlaces de Deezer
Un enlace de canción/álbum/playlist/artista de Deezer pegado (`deezer.com/track/…`) funciona como uno de Spotify: la API REST pública de Deezer aporta título, artista(s), álbum y portada, cada canción se emite completa desde YouTube antes de que descargues, y este mismo paso la empareja en YouTube Music/YouTube. Downtify no tiene un resolutor de discografías de Deezer propio más allá de lo que ya devuelve la API de Deezer, así que un enlace de Deezer se descarga y (en el caso de una playlist) obtiene su propio M3U y portada, pero no puede ser vigilado por el [Monitor de playlists](features/playlist-monitor.md).
:::

## 3. Descarga y etiquetado — yt-dlp + ffmpeg + mutagen

### Descarga

[yt-dlp](https://github.com/yt-dlp/yt-dlp) descarga el audio de YouTube. Downtify lo configura para probar varios clientes de reproductor en orden (`ios`, `android`, `web_embedded`, `mweb`, `web`, `tv`) y sortear los desafíos de detección de bots de YouTube. Consulta [Variables de entorno](getting-started/environment-variables.md) para ver opciones anti-bot avanzadas.

### Conversión

[ffmpeg](https://ffmpeg.org/) convierte el audio en bruto al formato elegido (MP3, FLAC, M4A, OGG u OPUS) con la tasa de bits elegida.

### Etiquetado

[mutagen](https://mutagen.readthedocs.io/) escribe los metadatos en el archivo convertido:

| Etiqueta | Escrita |
|-----|---------|
| Título | Sí |
| Artista(s) | Sí |
| Álbum | Sí |
| Año | Sí |
| Carátula (JPEG) | Sí |
| Letras (simples + sincronizadas) | Sí, si lrclib devuelve un resultado |
| Marca de explícito | Sí, cuando la canción está marcada como explícita (consulta [Marca de contenido explícito](features/explicit-marker.md)) |

Las etiquetas ID3/Vorbis/MP4 exactas dependen del formato de salida. Consulta [Letras](features/lyrics.md) para ver cómo se incrustan las letras.

## Progreso en tiempo real

Downtify transmite el progreso de las descargas al navegador mediante una conexión **WebSocket** (`/api/ws`). A medida que yt-dlp informa del progreso, el servidor envía actualizaciones de porcentaje y estado a todos los clientes conectados. Así ves avanzar la barra de progreso en tiempo real — sin polling, sin recargar la página.

## Nombres de archivo y organización

El nombre del archivo de salida se construye a partir de la plantilla configurada en Ajustes (por defecto: `{artists} - {title}`). Los caracteres no válidos en nombres de archivo se eliminan.

Cuando *Organizar por artista* está activado, el archivo se coloca dentro de una subcarpeta con el nombre del artista principal. En caso contrario, las canciones sueltas van a la raíz del directorio de descargas y las canciones de playlists/álbumes van a una subcarpeta por playlist o álbum.
