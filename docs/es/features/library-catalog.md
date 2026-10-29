---
icon: lucide/library
---

# Catálogo de la biblioteca y sincronización de rutas

Downtify mantiene un pequeño **catálogo** de los archivos bajo `/downloads` (la carpeta de slskd, cuando los [archivos de slskd se dejan en su sitio](slskd-navidrome.md#leave-files-in-place), y las [carpetas extra](external-library.md) que añades en Ajustes) para que la página Biblioteca, el reproductor, la exportación M3U, la sincronización con Navidrome y la detección de duplicados sigan siendo coherentes cuando se mueven archivos o crecen las playlists.

## Qué se guarda

| Almacén | Ubicación | Finalidad |
|-------|----------|---------|
| **Índice de canciones** | `/data/downtify_library.db` | Asocia ids de canción de Spotify con rutas de la biblioteca, para reconocer una canción que ya está en disco |
| **Catálogo de playlists** | `/data/downtify_library.db` | Qué canciones pertenecen a cada playlist de Spotify descargada |
| **Descargas de playlists** | `/data/downtify_library.db` | Descargas de playlists de Spotify seguidas y una caché de sus listas de canciones de Spotify |
| **Índice de Navidrome** | `/data/downtify_library.db` | Ids de canciones de Navidrome por archivo |
| **Caché de metadatos de la biblioteca** | `/data/downtify_library.db` | Título, artista, todos los artistas acreditados, álbum, artista del álbum, número de canción, año, duración y tamaño de portada por archivo para `GET /tracks`, releído solo cuando cambia la fecha de modificación o el tamaño de un archivo |
| **Ejecuciones de mejora** | `/data/downtify_library.db` | La cola de [mejora de la biblioteca](library-upgrade.md) y cuándo se comprobó por última vez cada canción, para que una ejecución sobreviva a un reinicio |
| **Caché de escaneo de rutas** | RAM, más una instantánea en `/data/downtify_library.db` | Filas plegadas de `GET /tracks`, listados de playlists y pares de rutas. Las rutas de la interfaz sirven esta instantánea sin recorrer el disco. Cada descarga terminada se **fusiona con la instantánea al instante** (para que un artista nuevo aparezca sin esperar). Un borrado **saca esos archivos de la instantánea al instante** (para que un álbum desaparezca de la cuadrícula sin esperar). Un recorrido completo del árbol se ejecuta en segundo plano unos segundos después de que la cola de descargas queda inactiva — no con un temporizador fijo. `GET /list?refresh=true` descarta la instantánea y vuelve a escanear ahora. |
| **Elementos ocultos** | `/data/downtify_library.db` | Las canciones, álbumes y artistas que un admin [ocultó a los usuarios](users.md#hiding-from-users) |
| **Caché de portadas** | `/data/cover_cache` (opcional) | Imágenes de portada extraídas para `GET /cover` |

Los archivos se asocian tras moverse mediante una **clave de contenido** — un hash del nombre y tamaño del archivo. Mover un archivo a otra carpeta conserva su clave; reemplazarlo por otro archivo le da una nueva.

## Ajustes → Biblioteca

### Guardar portadas en caché en disco

Cuando está activado, Downtify guarda las imágenes de portada extraídas en `/data/cover_cache`, para que la Biblioteca y el reproductor no relean las etiquetas por cada miniatura. Se puede desactivar en cualquier momento; solo cuesta espacio en disco.

### Reparar rutas de la biblioteca

Úsalo después de **mover o renombrar archivos en disco** fuera de Downtify, o de borrarlos a mano.

1. Abre **Ajustes → Biblioteca → Reparar rutas de la biblioteca**.
2. Downtify escanea las carpetas de la biblioteca y:
    - **actualiza las rutas** en el índice de canciones y el catálogo de playlists cuando un archivo ya no está donde estaba pero se encuentra el mismo archivo (misma clave de contenido) en otro sitio;
    - **elimina las entradas obsoletas** de archivos que ya no existen;
    - **indexa** entradas antiguas guardadas antes de que existieran las claves de contenido;
    - **lleva las [canciones que te gustan](liked-songs.md#keeping-likes-in-step-with-the-files)** a su nueva ubicación.
3. Si **Generar M3U** y/o **Crear playlists en Navidrome** están activados, se reescriben las playlists afectadas.

Solo se ejecuta cuando pulsas el botón (o llamas a `POST /api/library/reconcile`) — nunca con un calendario.

### Carpetas de música existentes

Para reproducir una colección que Downtify no descargó, añade las carpetas en **Ajustes → Biblioteca** y pulsa **Sincronizar carpetas**. Los archivos se quedan en disco; se leen las etiquetas y se asocian los artistas. Consulta [Carpetas de música existentes](external-library.md).

::: warning
Reescribir una playlist borra archivos de la biblioteca cuyas etiquetas claramente no coinciden con la canción de Spotify para la que están registrados — consulta [slskd y Navidrome](slskd-navidrome.md#playlist-sync).
:::

::: info Borrados vs. movimientos
Borrar canciones desde la página **Biblioteca** ya limpia el catálogo y reescribe en segundo plano los archivos M3U y las playlists de Navidrome afectados, así que no hay nada que reparar después.
:::

## Página Biblioteca

La página Biblioteca tiene cuatro pestañas — **Álbumes**, **Artistas**, **Playlists** y **Canciones**:

- **Álbumes, artistas y playlists** se muestran como una cuadrícula de portadas o una lista compacta (el interruptor se recuerda), con un filtro de texto y ordenación por añadidos recientemente, nombre, artista, año o número de canciones. Los álbumes y artistas se construyen a partir de las etiquetas de cada archivo (artista del álbum, álbum, año), así que no dependen de cómo estén organizados los archivos en disco. Un recopilatorio — artista del álbum `Various Artists`, con la marca de recopilatorio — queda como un solo álbum en Álbumes, mientras que sus canciones están en las páginas de sus artistas. Una canción etiquetada `Various Artists` sin esa marca (como las versiones antiguas etiquetaban cualquier canción con varios artistas, incluido un dúo como `Zé Neto & Cristiano`) se agrupa por su primer artista. Una canción sin etiqueta de álbum aparece en Canciones y en su artista, no en Álbumes.
- **Artistas** lista cada artista al que pertenece una canción — su artista del álbum, o en un recopilatorio (o un archivo sin artista del álbum) su primer artista. La página de ese artista incluye también las canciones en las que es invitado, marcadas con **Colaboración**; su pestaña Álbumes solo muestra álbumes propios (y se oculta si no hay ninguno). Un nombre que solo aparece acreditado junto a otro no tiene página propia: las etiquetas pueden nombrar a los integrantes de un dúo uno a uno (`Henrique; Juliano`, como YouTube Music acredita a algunos dúos y como los escribían versiones antiguas de Downtify), y una página para cada integrante sería un artista que no existe. **Various Artists** no aparece: las canciones de un recopilatorio están en las páginas de sus artistas, y el álbum sigue en Álbumes.
- Allí donde una canción muestra sus artistas — listas de canciones, la pantalla Reproduciendo, el Finder y las filas de canciones populares — cada nombre enlaza a la página del artista en la Biblioteca, o a una búsqueda si la Biblioteca no tiene página suya. En esas filas el nombre del álbum también enlaza a ese álbum en la Biblioteca, o a una búsqueda si la Biblioteca no lo tiene. Descubrir y su Finder nunca te envían a Buscar: allí, un artista o álbum que la Biblioteca no tiene es texto plano. Los artistas salen de la etiqueta `ARTISTS` del archivo (consulta [Varios artistas y recopilatorios](file-organization.md#several-artists-and-compilations)), así que un nombre como *Earth, Wind & Fire* nunca se parte por su coma; un archivo sin esa etiqueta tiene su texto de artista partido por `;`, ` / ` o `, `, salvo que ese texto sea también el artista del álbum del archivo, o que los nombres resultantes formen el artista del álbum (`Henrique; Juliano` en un álbum de `Henrique, Juliano`) — entonces es un solo nombre.
- **Playlists** son las playlists descargadas con un [archivo M3U](m3u-export.md), las playlists que creas con **Nueva playlist** (editables), además de las [descargas de playlists](slskd-navidrome.md#playlist-downloads) seguidas que aún no tienen M3U. Las playlists importadas de Spotify/YouTube siguen siendo de solo lectura hasta que las [desvinculas](#detach-an-imported-playlist). Las playlists que otras personas [comparten contigo](users.md#sharing-playlists) se listan bajo la cuadrícula, aparte de las tuyas. Cuando has dado [«me gusta»](liked-songs.md) a una canción, *Canciones que me gustan* aparece primero. Una playlist creada por ti usa un mosaico de hasta cuatro portadas de canciones; las importadas conservan la imagen guardada con el M3U.
- **Canciones** es una tabla ordenable (título, álbum, formato, fecha de adición, duración) con filtro de texto, filtro de formato y casillas — haz clic en una y luego Mayús+clic en otra para seleccionar un rango. Ordénala haciendo clic en el encabezado de una columna, o con el menú **Ordenar por** sobre la tabla (la única forma en el móvil, donde los encabezados están ocultos): añadidas recientemente o más antiguas primero, título, artista o álbum de A–Z o Z–A, más largas o más cortas primero. La elección se recuerda.

Las canciones de una playlist tienen el mismo menú **Ordenar por**, con **Orden de la lista** (el orden propio de la playlist, que es por donde empieza) añadido a las opciones; hacer clic en un encabezado de columna también funciona. **Reproducir** y la lista de canciones siguen el orden que elegiste, y la elección se recuerda, para toda playlist.

Abrir un álbum, artista o playlist muestra sus canciones con **Reproducir**, **Aleatorio** y **Añadir a la cola**. **Descargar como ZIP** es un botón en la página de una playlist y está en el menú **⋯** en la de un álbum. Una playlist creada por ti también tiene **Añadir canciones**, **Renombrar** y **Compartir…** (consulta [compartir playlists](users.md#sharing-playlists)); una importada tiene **Compartir…** y **Desvincular del origen** (abajo); la página de una playlist descargada muestra cuántas de sus canciones están descargadas, lista las que faltan con **Descargar las que faltan** y ofrece **Vigilar canciones nuevas**. **Eliminar playlist** está en el menú **⋯**: las playlists importadas eliminan el audio; una playlist creada por ti solo quita la playlist.

### Buscar en una playlist

Una playlist larga solo dibuja las canciones que están en pantalla, así que la búsqueda del propio navegador (`Ctrl` + `F`) no ve el resto. El cuadro **Buscar en esta playlist**, encima de las canciones, busca en todas ellas: título, artista, álbum y nombre de archivo, sin distinguir mayúsculas ni acentos. En la página de una playlist, `Ctrl` / `⌘` + `F` pone el cursor ahí (púlsalo otra vez dentro del cuadro para la búsqueda del navegador), y `Esc` lo vacía.

Al lado, unos filtros acotan la lista. Cada uno muestra cuántas canciones tiene y solo aparece cuando tiene alguna:

| Filtro | Muestra |
|--------|---------|
| **Todas** | Todas las canciones descargadas de la playlist |
| **Faltan** | Canciones de la playlist de origen que aún no están en la biblioteca (descargas de playlists de Spotify), con el estado de su descarga; se consultan en Spotify al elegir el filtro |
| **Fallidas** | Las canciones que faltan cuya descarga falló, cada una con el botón de reintentar, una vez consultado **Faltan** |
| **YouTube Music**, **Soulseek (slskd)**, **Deemix**… | Las canciones que descargó esa fuente. Downtify lo recuerda para las canciones descargadas desde ahora; las anteriores cuentan como **Origen desconocido**, salvo los archivos de slskd dejados en su sitio y las canciones de tus propias carpetas |
| **Fuera de Navidrome** | Con la [sincronización con Navidrome](slskd-navidrome.md) activada, las canciones que Downtify aún no ha emparejado con una canción de Navidrome |

La búsqueda y un filtro funcionan juntos, y el número de canciones mostradas aparece debajo. Cada canción conserva su número en la playlist, y ordenar, reproducir y el menú de cada canción actúan sobre lo que se muestra.

### Desvincular una playlist importada

Una playlist importada de un enlace de Spotify o YouTube Music no se puede editar, porque Downtify la mantiene sincronizada con su origen. Para ordenar una — quitar una canción que no pertenece, añadir una que sí — ábrela y elige **Desvincular del origen**. Pasa a ser una playlist como las que creas: sus canciones y propietario se quedan como están, y obtienes **Añadir canciones**, **Renombrar** y quitar canciones. A cambio se corta el vínculo con su origen: deja de actualizarse desde Spotify o YouTube Music, se elimina su vigilancia del [Monitor de playlists](playlist-monitor.md) (si la tenía) y desaparece su seguimiento de «canciones que faltan». Las canciones ya descargadas nunca se tocan, y su imagen se queda hasta tu primera edición, cuando la sustituye un mosaico de sus canciones. Desvincular no se puede deshacer desde la app; descargar el enlace de nuevo crea una nueva playlist importada.

Todas las cuentas ven la misma biblioteca: lo que un admin [oculta a los usuarios](users.md#hiding-from-users) queda fuera para ellos, y un admin lo ve todo con un ojo tachado en lo que está oculto. Los admins ocultan y muestran desde el menú `…` de una canción, álbum o artista, o desde la barra de selección en **Canciones**.

**Descargar como ZIP** guarda las canciones seleccionadas en el dispositivo desde el que navegas como un único ZIP, conservando su estructura de carpetas — útil cuando Downtify corre en un servidor doméstico y quieres un lote de canciones en local. Combínalo con **Seleccionar todo** para llevarte todo lo que muestra el filtro actual. El archivo se construye mientras se descarga, así que no se escribe nada en el disco del servidor, y está limitado a 2000 canciones por descarga.

## API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/list?refresh=true` | Rutas de la biblioteca, saltándose la caché de escaneo de rutas |
| `GET` | `/api/library/summary` | Recuentos de la página de Inicio y álbumes recientes, sin la lista completa de canciones |
| `GET` | `/api/library/albums` | Mosaicos de álbumes (recuentos + archivo de portada), sin todas las canciones |
| `GET` | `/api/library/artists` | Mosaicos de artistas (recuentos + archivo de portada) para la Biblioteca y Descubrir |
| `GET` `POST` | `/api/library/visibility` | Admins: qué está oculto a los usuarios, y ocultar / mostrar elementos |
| `POST` | `/api/library/lookup` | Filas de la biblioteca para canciones de búsqueda/enlaces ya descargadas |
| `GET` | `/tracks` | Canciones de la biblioteca con etiquetas. `?playlist=`, `?artist=`, `?album=`, `?q=` y `?limit=` devuelven un subconjunto |
| `GET` | `/media/{path}` | Sirve un archivo de la biblioteca, incluidas rutas `slskd/…` y `ext/…` |
| `GET` | `/playlist-cover?file=…` | Sirve la [portada](playlist-cover-art.md) propia de una playlist, informada como `cover` por `/playlists` |
| `POST` | `/api/library/archive` | Prepara un ZIP de las canciones seleccionadas (devuelve un ticket de un solo uso) |
| `GET` | `/api/library/archive/{token}` | Emite ese ZIP al navegador |
| `DELETE` | `/api/library/playlist?playlist_name=…` | Elimina las canciones, el M3U y el catálogo de una playlist importada — o solo el M3U de una playlist que creaste |
| `POST` | `/api/library/playlists` | Crea una playlist editable vacía |
| `POST` | `/api/library/playlists/tracks` | Añade o quita archivos de la biblioteca en una playlist que creaste |
| `POST` | `/api/library/playlists/rename` | Renombra una playlist que creaste |
| `PUT` | `/api/library/playlists/visibility` | [Comparte una playlist](users.md#sharing-playlists) tuya, solo lectura |
| `POST` | `/api/library/playlists/copy` | Guarda una copia de una playlist que puedes abrir como una editable propia |
| `POST` | `/api/library/playlists/detach` | Convierte una playlist importada en una editable |
| `POST` | `/api/library/reconcile` | Repara las rutas de la biblioteca y luego actualiza las playlists de M3U/Navidrome |
| `POST` | `/api/library/external/sync` | Inicia un escaneo en segundo plano de las carpetas de música extra |
| `GET` | `/api/library/external/sync` | Sincronización de carpetas extra en curso, o el último registro terminado |
| `POST` | `/api/library/external/unmap` | Quita una carpeta extra de la biblioteca sin borrar audio |
| `GET`/`POST` | `/api/library/upgrade…` | Escanea y repara lo que ya está descargado — consulta [Mejorar biblioteca](library-upgrade.md#api) |

Consulta la [referencia de la API](../api-reference.md#library) para ver los formatos de petición y respuesta.
