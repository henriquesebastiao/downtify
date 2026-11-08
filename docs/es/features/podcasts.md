---
icon: lucide/mic
---

# Podcasts

Suscríbete a un programa y sus episodios nuevos se descargan solos — sin volver a pegar un enlace cada semana. Los podcasts se tratan de principio a fin de forma distinta a la música: un episodio ya es un archivo de audio terminado en una URL `<enclosure>` de RSS, así que no hay coincidencia en YouTube ni transcodificación, solo una descarga y la escritura de etiquetas.

Abre **Podcasts** en la barra lateral (en el móvil: **Más → Podcasts**).

Las suscripciones pertenecen a quien se suscribe: cada cuenta sigue sus propios programas (el mismo feed suscrito dos veces acaba en dos carpetas), con sus propios episodios, posiciones de reanudación y descartes. Un admin ve todas las suscripciones.

## Suscribirse

Pega una de estas en el cuadro **Añadir un podcast**, o escribe un nombre para buscar:

| Entrada | Qué ocurre |
|-------|--------------|
| La URL del feed RSS de un podcast | Se obtiene y se analiza directamente |
| Un enlace de programa de Spotify (`open.spotify.com/show/…`) | El nombre del programa se lee de Spotify y luego se asocia a su feed RSS público mediante el directorio de podcasts de iTunes |
| Un enlace de episodio de Spotify (`open.spotify.com/episode/…`) | Igual que un enlace de programa, y el episodio concreto se resalta si su título se puede encontrar en el feed |
| El nombre de un programa (texto libre) | Se busca en el directorio de podcasts de iTunes |

::: info Los programas exclusivos de Spotify no se pueden descargar
Un programa que solo existe en Spotify (sin feed público) se informa como tal — Downtify no adivina ni recurre a otra cosa. Busca el programa por nombre para comprobarlo antes de dar por hecho que es exclusivo.
:::

Antes de confirmar, eliges:

- **Conservar** — consulta [Cuántos episodios se descargan](#how-many-episodes-are-downloaded) más abajo.
- **Intervalo** — cada cuánto se comprueba el feed en busca de episodios nuevos, de cada 15 minutos a una vez al mes. Las suscripciones se comprueban con el mismo calendario y el mismo barrido en segundo plano que el [Monitor de playlists](playlist-monitor.md) — para él son solo otro tipo de vigilancia.

## Cuántos episodios se descargan

El ajuste **Conservar** tiene dos comportamientos distintos, que se elige una vez por programa:

- **Cada episodio nuevo** — descarga al momento solo el episodio más reciente (suscribirse no es una invitación a traer todo el catálogo antiguo de un programa) y luego descarga los episodios nuevos que aparezcan en cada comprobación. Nunca se borra nada automáticamente.
- **Últimos *N* episodios** — una ventana móvil. Tras cada comprobación (incluida la primera), se descargan los *N* episodios publicados más recientemente, y cualquier episodio descargado más antiguo se elimina para hacer sitio. Subir *N* más tarde hace que esos episodios eliminados vuelvan a poder descargarse; un episodio que tú mismo quitaste con **Quitar descarga** nunca vuelve por esta vía — consulta [Quitar episodios](#removing-episodes).

Cambia **Conservar** y el intervalo cuando quieras desde la página del programa.

## Episodios

La página de un programa lista sus episodios, del más nuevo al más antiguo, cada uno con su fecha de publicación y duración. Un episodio no cubierto por la política de retención sigue apareciendo aquí — toca **Descargar** para traer solo ese, por antiguo que sea.

### Quitar episodios

El menú **⋯** de cada episodio tiene **Quitar descarga**, que borra el archivo pero mantiene el episodio en la lista. Hay dos formas de que desaparezca el archivo de un episodio, con resultados distintos:

| Cómo | ¿Vuelve automáticamente? |
|-----|----|
| La retención lo sacó (un episodio más antiguo fuera de la ventana «conservar los últimos N») | Sí, si vuelves a subir **Conservar** |
| Elegiste tú **Quitar descarga** | No — descárgalo de nuevo a mano cuando quieras |

### Marcar como reproducido

Usa el menú **⋯** de un episodio para marcarlo como reproducido o sin reproducir a mano, o déjalo sonar hasta el final — un episodio en los últimos segundos de su duración se marca como reproducido solo.

## Reproducir episodios

Los episodios suenan en el mismo reproductor integrado que la música, con algunas diferencias que solo aparecen en un episodio de podcast:

- **Retroceder 15 s / avanzar 30 s** en lugar de aleatorio y repetir, que no se aplican a un solo episodio.
- **Velocidad de reproducción** (0,75× a 2×), junto al temporizador de apagado.
- La **posición de reanudación** se guarda en el servidor cada ~10 segundos de reproducción y una vez más al pausar, así que cerrar la pestaña — o abrir Downtify en otro dispositivo — retoma el episodio cerca de donde lo dejaste. La lista de episodios de un programa muestra una pista «Reanudar en …» para lo que está a medias.

El corazón (canciones que te gustan) e «ir al álbum/artista» no se aplican a los episodios y no aparecen en uno.

## Biblioteca

Los podcasts tienen su propio sitio — nunca aparecen como canciones, álbumes o artistas en la **Biblioteca**, y una ejecución de [Mejorar biblioteca](library-upgrade.md) los deja en paz por completo (un episodio no tiene ID de canción de Spotify de donde refrescar etiquetas, ni letra aparte que buscar).

Los archivos de los episodios siguen estando bajo el mismo volumen de descargas, en `Podcasts/<Programa>/<fecha> - <Episodio>.<ext>`, así que cualquier servidor multimedia apuntado a tu biblioteca también los ve.

## Etiquetas

Downtify escribe lo que las apps de podcast y los servidores multimedia ya leen de un episodio: título, el programa como álbum, el autor del programa como artista, el año de publicación, números de episodio/temporada, la portada del propio programa (la mayor entre la imagen del feed y la de iTunes, la misma idea que la [portada de música](download-settings.md#cover-art-resolution)) y la descripción del episodio como comentario. Las notas del programa se guardan como texto plano — Downtify les quita el HTML en lugar de renderizarlo.

## Conviene saber

- **Sin podcasts en vídeo.** Un episodio cuyo único adjunto es un archivo de vídeo se omite por completo; solo se admite audio.
- **Sin capítulos.** Los feeds que incluyen marcadores de capítulo aún no los tienen en Downtify.
- **No se refleja en Navidrome.** A diferencia de las playlists, las suscripciones a podcasts no se envían a una biblioteca de Navidrome — los episodios son archivos normales que tu servidor multimedia ya ve por su cuenta.
- Cancelar la suscripción (**⋯ → Cancelar suscripción**) elimina los episodios descargados por defecto; elige **Cancelar suscripción, conservar episodios descargados** para dejar los archivos en su sitio.

## API

`POST /api/podcasts/resolve`, `GET /api/podcasts/search`, `POST /api/podcasts/subscribe`, `GET/PATCH/DELETE /api/podcasts/shows/{id}`, `GET /api/podcasts/shows/{id}/episodes`, `POST /api/podcasts/episodes/{id}/download`, `DELETE /api/podcasts/episodes/{id}` y `PUT /api/podcasts/episodes/{id}/playback`. Consulta la [referencia de la API](../api-reference.md#podcasts).
