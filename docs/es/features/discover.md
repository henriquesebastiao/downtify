---
icon: lucide/compass
---

# Descubrir

Artistas que aún no tienes, sugeridos a partir de los que sí tienes. Abre **Descubrir** en la barra lateral (en el móvil: **Más → Descubrir**). El cuadro de búsqueda de arriba es el [Finder](finder.md), una búsqueda solo de Deezer: al buscar se muestran sus resultados en lugar de las sugerencias, y al vaciarlo vuelven.

No hace falta cuenta ni clave de API: las sugerencias salen de la lista pública de «artistas similares» de [Deezer](https://www.deezer.com/), que funciona sin iniciar sesión.

## Cómo se eligen las sugerencias

1. **Se pondera a tus artistas.** Cada artista de tu biblioteca cuenta algo, y cuenta más por cada uno de estos puntos, de mayor a menor:
    - cuántas veces los **escuchas** en el reproductor de Downtify (lo escuchado recientemente pesa más que lo de hace meses),
    - cuántas de sus canciones te **gustan**,
    - cuántas de sus canciones están **en tu biblioteca**.

    El peso se aplana a medida que crece, así que un artista con 400 canciones de discografía no ahoga a uno que reproduces todos los días.
2. **Se consulta en Deezer a los 15 primeros**, que devuelve para cada uno los artistas que también gustan a sus oyentes.
3. **Cada artista sugerido recibe puntos** de cada uno de tus artistas que lo sugiere — más de un artista de más peso, y más cuanto más arriba esté en la lista de Deezer. Un artista al que apuntan varios de tus favoritos queda por encima de uno que solo menciona uno de ellos. Bajo cada sugerencia, *Porque te gusta …* nombra los artistas de los que viene.

Los artistas que ya están en tu biblioteca y los que has [ocultado](#hiding-artists) nunca se sugieren.

Haz clic en la foto de una sugerencia para abrir al artista en las columnas del [Finder](finder.md) — su perfil, toda la discografía y las canciones de cualquier álbum, todo de Deezer. El menú **⋯** de una sugerencia también tiene **Buscar canciones** (las canciones del artista, mostradas como una búsqueda del [Finder](finder.md)), **Abrir en Deezer** y **No me interesa**. La página muestra los 12 mejores artistas; **Mostrar todo** lista todas las sugerencias (hasta 48).

## Álbumes y playlists

Debajo de los artistas, construidos a partir de ellos:

| Sección | Qué contiene |
|---------|--------------|
| **Álbumes para ti** | El álbum más conocido de cada uno de los 12 mejores artistas sugeridos |
| **Más de tus artistas** | Hasta dos álbumes populares de cada uno de tus 6 artistas de más peso que aún no están en tu biblioteca |
| **Playlists para ti** | Lo esencial de cada artista sugerido: la playlist **`100% <artista>`** del propio Deezer (elegida por sus editores) y luego la **`This Is <artista>`** del propio Spotify |

Llegan en dos pasos:

1. **Primero Deezer.** La discografía de cada artista se lee de Deezer: un álbum completo va antes que un sencillo o EP y, entre ellos, el que tiene más fans. Esta respuesta es rápida y llena las estanterías.
2. **Después Spotify.** Unos segundos más tarde, las elecciones del propio Spotify para los mismos artistas (de su búsqueda) se añaden **al final** de cada estantería — unos marcadores indican dónde aparecerán mientras cargan, y nada de lo que ya está en la página se mueve. Un álbum que eligen ambos servicios aparece una vez. Cada álbum de Spotify se busca en Deezer por artista y título; cuando Deezer lo tiene, se abre en el Finder como los demás.

Un pequeño icono en la esquina inferior izquierda de la portada de cada álbum y playlist indica de qué servicio viene:

- **Deezer** — un álbum se abre en las columnas del [Finder](finder.md), con sus canciones listas para reproducirse enteras y descargarse.
- **Spotify** — Deezer no tiene ese álbum, así que abre la misma página que un enlace de Spotify pegado.

Las playlists — tanto las de Deezer como las de Spotify — siempre abren esa página, donde puedes **escuchar sus canciones enteras** antes de descargar ninguna (consulta [Escuchar canciones antes de descargar](top-songs.md#playing-songs-before-downloading)) y luego descargarlo todo, solo las canciones nuevas o una selección.

Todo se guarda durante una semana, como los artistas similares, y la coincidencia de un álbum de Spotify en Deezer durante un mes (una semana cuando Deezer no lo tenía, por si lo añaden). Un álbum que ya está en tu biblioteca (comparado por artista y título, así que `Dummy (Deluxe Edition)` cuenta como `Dummy`) y una playlist que ya has descargado quedan fuera; ocultar a un artista también retira sus álbumes y playlists.

## Qué cuenta como una escucha

Una canción cuenta una vez por reproducción, cuando se ha reproducido de verdad **la mitad** (o **cuatro minutos**, en las canciones largas) — saltar a la mitad no cuenta, y las canciones de menos de 30 segundos nunca cuentan. Los episodios de podcast no cuentan.

Las escuchas se guardan en el servidor, así que lo que reproduces en el móvil también da forma a las sugerencias en el ordenador. Para empezar de cero, abre **Artistas ocultos → Borrar historial de escucha**; tu biblioteca y las canciones que te gustan se quedan como están.

## Ocultar artistas

**⋯ → No me interesa** en una sugerencia oculta a ese artista de Descubrir para siempre (el aviso que aparece tiene un **Deshacer**). Para ocultar a un artista antes de que se sugiera — uno del que simplemente no quieres saber nada — abre **Artistas ocultos** y escribe el nombre.

La misma lista muestra todos los artistas ocultos, con **Volver a mostrar** para recuperar uno. Los nombres se comparan sin distinguir mayúsculas de minúsculas e ignorando los caracteres que un nombre de archivo no admite, así que ocultar `AC/DC` también oculta `ACDC`.

## Conviene saber

- **Las sugerencias se guardan en caché una semana.** Las respuestas de Deezer y Spotify para cada uno de tus artistas se conservan 7 días, así que volver a abrir Descubrir es instantáneo y no cuesta una tanda de peticiones. **Actualizar** reordena con tu biblioteca, tus «me gusta» y tus escuchas más recientes; un artista cuya semana ha terminado se consulta de nuevo.
- **Si no se puede contactar con Deezer** (o limita las peticiones) para algunos de tus artistas, la página muestra igualmente lo que pudo construir y avisa de que la lista es más corta de lo habitual — inténtalo más tarde. Una consulta fallida nunca se recuerda como «sin artistas similares».
- **Un artista que Deezer no conoce** simplemente no aporta nada; no se vuelve a buscar hasta que termina su semana.
- Solo los *nombres* de artistas y álbumes salen de tu servidor (como búsquedas en Deezer y Spotify). Nada de lo que reproduces se envía a ningún sitio.

## API

Consulta [Descubrir](../api-reference.md#discover) en la referencia de la API.
