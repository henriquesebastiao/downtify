---
icon: lucide/trending-up
---

# Listas de éxitos

**Listas de éxitos** muestra la lista global del propio Deezer — sin filtro de género, lo que está en tendencia en todo el mundo ahora mismo — sin necesidad de cuenta ni clave de API de Deezer.

## Cómo usarlo

Abre **Listas de éxitos** desde la barra lateral (o la hoja **Más** en el móvil). Cuatro pestañas leen de la misma lista: **Canciones**, **Álbumes**, **Artistas** y **Playlists**.

- **Canciones** — una lista ordenada. Pulsa una (o toca su fila) para reproducirla completa desde YouTube, directamente en el reproductor integrado, antes de descargarla. Descargar una fila funciona igual que un resultado de búsqueda: Downtify busca en YouTube Music (y, si no, en YouTube estándar) la mejor coincidencia para el título, el artista y la duración de la canción, con el mismo [pipeline de coincidencia](../how-it-works.md) que usa cualquier otra descarga. Una vez descargada, la fila reproduce la de tu biblioteca en lugar de emitirla en streaming.
- **Álbumes**, **Artistas** y **Playlists** — cuadrículas de portadas. Al hacer clic en una se resuelve ([`GET /api/url/resolve`](../api-reference.md#get-apiurlresolve)) exactamente como si hubieras pegado ese enlace de Deezer en el cuadro de búsqueda: se carga su lista de canciones, lista para elegir y descargar.

## Por qué las canciones se descargan (y se reproducen completas) directamente desde aquí, pero los álbumes, artistas y playlists abren primero una página

Una canción de la lista no necesita un paso de resolución para descargarse: Deezer ya da su título, artista y nombre de álbum, lo que basta para buscarla y emparejarla en YouTube, igual que un resultado de búsqueda de texto libre. Un álbum, artista o playlist sí lo necesita — convertir su enlace en una lista de canciones —, por eso su tarjeta abre esa página resuelta en lugar de descargar directamente desde la cuadrícula. Reproducir una fila de canción emite en streaming completa desde YouTube (nunca para álbumes, artistas o playlists) — el mismo streaming que usa cualquier fila de canción, solo que alimentado con el título y el artista de la lista.

## Vigilar o guardar una playlist de la lista

Cada tarjeta de playlist tiene un menú **⋯** sobre su portada, con las dos cosas que ofrece su página además de descargar:

- **Vigilar canciones nuevas** añade una vigilancia del [Monitor de playlists](playlist-monitor.md#deezer-playlists), comprobada cada 6 horas: la primera comprobación descarga lo que la playlist tiene ahora, las siguientes lo que se le añada. Cambia el intervalo, pausa o detén la vigilancia en la página **Monitor**.
- **Añadir a mis listas** abre el selector de playlists con las canciones de la playlist que **ya están en tu biblioteca**, para añadirlas a una de tus playlists o a una nueva con su nombre. No se descarga nada, y tu playlist no sigue a la de la lista después — para eso están el botón de descarga o **Vigilar canciones nuevas**. Si ninguna de sus canciones está todavía en la biblioteca, te lo dice.

## API

Consulta [`GET /api/discover/chart`](../api-reference.md#get-apidiscoverchart) en la Referencia de la API.
