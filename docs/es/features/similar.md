---
icon: lucide/sparkles
---

# Similares

**Similares** encuentra canciones que suenan como la que indiques, a partir de la mezcla de radio del propio YouTube Music — lo que YouTube reproduce después de tu canción. Sin clave de API ni configuración.

## Cómo usarlo

Abre **Similares** desde la barra lateral (debajo de **Listas de éxitos**, o en la hoja **Más** en el móvil). Escribe el **Artista** o la **Canción** (basta con uno de los dos — solo el artista parte de su mayor éxito) y pulsa **Buscar similares**:

Tampoco hace falta escribir: cada fila de canción de la app lleva un botón **Similares** (el icono de varita junto al botón de descargar, relleno como él en Búsqueda, Listas de éxitos y Descubrir — en Canciones más populares y en los enlaces pegados es un icono discreto, y un elemento del menú contextual en las canciones de Biblioteca, Álbum, Artista y Playlist). Abre esta página ya buscando esa canción. Los resultados también se reproducen completos desde la propia fila, sin descargar nada.

- **Reproducir completa** — toca la portada y la canción se emite desde este servidor directamente al reproductor integrado, esté descargada o no.
- **Descargar** — cada fila ya lleva su vídeo y descarga al instante: Downtify pone en cola la coincidencia por el mismo [pipeline de coincidencia](../how-it-works.md) que usa cualquier otra descarga. Desde ese momento la fila muestra el progreso de esa descarga y, cuando la canción está en tu biblioteca, una marca de verificación.
- **Lista infinita** — al desplazarte hasta el final se carga la siguiente página a partir de la mezcla de la última canción, y la reproducción más allá de la última fila sigue ampliando la cola del mismo modo, sin fin.

## API

Consulta [`GET /api/similar/tracks`](../api-reference.md#get-apisimilartracks) en la Referencia de la API.
