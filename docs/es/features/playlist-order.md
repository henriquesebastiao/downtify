---
icon: lucide/list-ordered
---

# Orden de las playlists y canciones repetidas

Una playlist que creaste en la Biblioteca — con **Nueva playlist**, **Guardar una copia**, [Desvincular del origen](library-catalog.md#detach-an-imported-playlist) o [una importación desde tus carpetas de música](external-playlists.md) — mantiene sus canciones en el orden que elijas y puede reproducir una canción más de una vez. Las playlists que siguen un enlace de Spotify, YouTube Music o Deezer mantienen el orden de su origen, y **Canciones que me gustan** se ordena por cuándo marcaste cada canción.

## Reordenar una playlist

1. Abre la playlist y elige **Reordenar**, junto al selector de orden que hay sobre sus canciones.
2. Mueve las canciones:
    - arrastra una fila a su nuevo sitio (con el ratón);
    - o usa las flechas de cada fila: **Subir** y **Bajar**, y en pantallas más anchas **Mover al principio** y **Mover al final**. El foco se queda en la flecha, así que puedes seguir moviendo la misma canción con el teclado.
3. Elige **Guardar orden**, o **Cancelar** para dejarla como estaba.

Al guardar, el orden de la página pasa a **Orden de la lista**, para que veas el orden que acabas de guardar. El orden se escribe en el archivo M3U de la playlist, así que los servidores multimedia que lo leen (Jellyfin, Navidrome, Plex) también lo recogen.

Pueden reordenarla su dueño, los administradores y los [editores](collaborative-playlists.md) de la playlist. Hay un par de garantías:

- **No se pierde el cambio de nadie.** Si otra persona añadió o quitó una canción mientras reordenabas, al guardar se recarga la playlist y se te pide que la ordenes de nuevo, en lugar de descartar su cambio.
- **Las canciones ocultas para ti no se mueven.** Una canción que un administrador [ocultó a los usuarios](users.md#hiding-from-users) no aparece en tu lista y conserva su sitio en la playlist cuando guardas.

## Repetir una canción

Añadir una canción que la playlist ya tiene pregunta primero:

- Desde **Añadir a la playlist** en el menú **⋯** de una canción, un diálogo avisa de que **Ya está en esta playlist**: elige **Añadir de todos modos** para añadirla otra vez al final, o **No añadir**. Si añades varias canciones a la vez, pregunta una sola vez por todas las que ya estaban; las demás se añaden en cualquier caso.
- En el diálogo **Añadir canciones** de la página de la playlist, las que ya están aparecen marcadas como **Ya añadida**. Marcar una la añade otra vez.

Cada copia es una fila propia: suena en su sitio, tiene su propio número y se puede mover por separado. **Guardar una copia** conserva las repeticiones. Una playlist admite hasta 500 canciones, copias incluidas.

## Quitar una copia

**Quitar de la playlist** en el menú **⋯** de una fila quita solo esa copia; las demás copias de la canción se quedan donde están.

## Para apps y scripts

- [`PUT /api/library/playlists/order`](../api-reference.md#put-apilibraryplaylistsorder) guarda un orden nuevo: cada canción que ve quien llama, copias incluidas, en su nuevo sitio. `409` si la playlist cambió mientras tanto.
- [`POST /api/library/playlists/tracks`](../api-reference.md#post-apilibraryplayliststracks) acepta `allow_duplicates` para añadir de nuevo una canción, responde en `already` qué canciones omitió y acepta `remove_entries` para quitar una sola copia.
- Las filas de playlist de [`GET /playlists`](../api-reference.md#get-playlists) y [`GET /api/v1/playlists`](../api-reference.md#get-apiv1playlists) listan una canción repetida una vez por copia, en orden. La app de Android muestra todas las copias; el orden se cambia desde la app web.
