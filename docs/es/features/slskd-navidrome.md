---
icon: lucide/share-2
---

# slskd y Navidrome

Dos integraciones opcionales para bibliotecas autoalojadas:

- **[slskd](https://github.com/slskd/slskd)** — descarga canciones de la red Soulseek a través de tu propio servidor slskd, como una fuente de audio extra junto a YouTube Music y YouTube.
- **[Navidrome](https://www.navidrome.org/)** — refleja en Navidrome las playlists que descargas, para que aparezcan en cualquier cliente Subsonic.

Ambas vienen desactivadas por defecto y se configuran en **Ajustes**.

## Fuentes de audio y orden de alternativas

**Ajustes → Fuentes de audio** es una lista ordenada. Toca una fuente para añadirla o quitarla; con más de una seleccionada, usa las flechas para reordenarlas. Cada canción prueba las fuentes en ese orden y se detiene en la primera que da audio:

| Fuente | Qué hace |
|--------|-------------|
| **YouTube Music** | La predeterminada. Busca en YouTube Music y recurre a YouTube estándar cuando no hay coincidencia aceptable — consulta [Cómo funciona](../how-it-works.md#fallback-to-standard-youtube). |
| **YouTube** | Busca solo en YouTube estándar. |
| **slskd** | Busca en Soulseek a través de slskd y descarga el archivo que mejor coincida. |

Activar slskd lo pone primero en la lista. Si slskd acaba siendo la única fuente, YouTube Music y YouTube se siguen probando después de él, así que una canción que slskd no encuentra se descarga igualmente. La cola de descargas muestra qué fuente sirvió cada canción.

## slskd

### Configuración

1. Ejecuta slskd y crea una clave de API para Downtify (consulta la documentación de slskd).
2. Monta la carpeta de descargas de slskd en el contenedor de Downtify — la misma carpeta del host en la que escribe slskd. Consulta [Docker Compose → Con slskd](../getting-started/docker-compose.md#with-slskd-soulseek).
3. En **Ajustes → slskd (Soulseek)**, activa slskd y rellena:
    - **URL de slskd** — p. ej. `http://slskd:5030` cuando ambos contenedores comparten una red de Docker.
    - **Clave de API**.
    - **Carpeta de descargas** — la ruta *dentro del contenedor de Downtify* donde está montada esa carpeta (por defecto `/slskd`), no la ruta del host.

Guardar se rechaza con un mensaje de error si slskd está activado sin URL o clave de API.

### Probar la conexión

Pulsa **Probar conexión** bajo los campos para comprobarlos antes de guardar — usa lo que está escrito en el formulario, guardado o no, y no cambia nada. Informa de:

| Resultado | Qué significa |
|--------|---------------|
| **Conectado a slskd 0.21.4.** | La dirección es correcta y la clave de API fue aceptada |
| **slskd ha iniciado sesión en Soulseek.** / **no ha iniciado sesión** | Si el propio slskd está conectado a la red Soulseek. Si no lo está, las búsquedas no encuentran nada hasta que lo esté — un aviso, ya que los ajustes en sí son correctos |
| **Downtify puede leer `/slskd`.** / **no puede leer** | Si la carpeta de descargas de arriba existe dentro de *este* contenedor y es legible. La causa habitual de un aviso es una carpeta que no está montada — consulta [Configuración](#setup) |
| **slskd rechazó la clave de API.** | El servidor respondió, pero no a esta clave |
| **No se puede alcanzar … / no respondió a tiempo.** | Dirección o puerto erróneos, el servidor está caído o no es alcanzable desde el contenedor de Downtify |
| **No parece slskd.** | Algo respondió, pero no slskd — a menudo un puerto erróneo, o una ruta base que falta en la dirección |
| **El certificado HTTPS no es de confianza.** | Usa `http://` en tu propia red, o un certificado de una autoridad de confianza; Downtify no omite la comprobación de certificados |

Editar cualquier campo borra el último resultado, ya que ya no describe lo que hay en el formulario. El botón sigue desactivado hasta que se rellenan la dirección y la clave.

### Cómo se asocia una canción

Downtify busca en slskd con el título y el artista de la canción y ordena los resultados según lo bien que el nombre de archivo y la duración coinciden con la canción. Entre coincidencias igual de buenas prefiere MP3 y luego FLAC, y omite archivos que informan de un bitrate inferior a 256 kbps. Prueba hasta cinco candidatos, uno tras otro. Cuando termina una transferencia, Downtify comprueba las etiquetas y la duración del archivo con la canción antes de conservarlo.

Si no aparece nada aceptable, la transferencia no termina dentro del **Tiempo de espera total**, o se queda en cola en el par remoto sin avanzar más que el **Tiempo de espera en cola**, Downtify pasa a la siguiente fuente de audio.

### Dejar los archivos en su sitio

Con **Dejar los archivos de slskd en su sitio** activado (lo predeterminado), el archivo descargado se queda en la carpeta de slskd: Downtify escribe allí mismo los metadatos, la portada y la letra y lo registra en la biblioteca con una ruta `slskd/…`. La Biblioteca, el reproductor y los archivos M3U usan esa ruta, y se sirve a través de `/media/slskd/…`.

Desactívalo para copiar el archivo junto a tus otras descargas, siguiendo tu plantilla de nombre de archivo y los ajustes de [organización de archivos](file-organization.md).

::: info
Los archivos de slskd conservan su formato original — no se transcodifican al formato elegido en Ajustes.
:::

## Navidrome

### Configuración

1. Asegúrate de que la carpeta de música de Navidrome incluya la carpeta de descargas de Downtify (y la carpeta de slskd, si dejas los archivos de slskd en su sitio). Navidrome solo puede añadir canciones a una playlist una vez las ha escaneado.
2. En **Ajustes → Navidrome**, activa Navidrome e introduce su URL, usuario y contraseña.
3. Opcionalmente, añade un usuario y una contraseña de **admin**. Downtify entonces le pide a Navidrome que escanee la biblioteca antes de asociar canciones nuevas, en lugar de esperar al escaneo programado del propio Navidrome.

### Probar la conexión

Pulsa **Probar conexión** bajo los campos para comprobarlos antes de guardar — usa lo que está escrito en el formulario, guardado o no, y no cambia nada. Informa de:

| Resultado | Qué significa |
|--------|---------------|
| **Conectado a navidrome 0.53.3.** | La dirección es correcta y el usuario y la contraseña fueron aceptados |
| **Esta cuenta puede iniciar escaneos de la biblioteca.** | La cuenta usada para los escaneos es admin. Es el usuario admin que rellenaste, o el normal cuando lo dejaste vacío |
| **Esta cuenta no puede iniciar escaneos de la biblioteca.** | Navidrome solo deja a los admins iniciar un escaneo, y no lo dice cuando Downtify lo intenta — las canciones nuevas simplemente aparecen tarde. Rellena un usuario y una contraseña de admin |
| **La cuenta de admin no es admin.** | El inicio de sesión de admin que introdujiste funciona, pero pertenece a un usuario normal |
| **Navidrome rechazó el usuario o la contraseña de admin.** | El inicio de sesión de la cuenta de escaneo es erróneo; el principal se informa por separado |
| **Navidrome rechazó el usuario o la contraseña.** | El servidor respondió, pero no a este inicio de sesión |
| **No se puede alcanzar … / no respondió a tiempo.** | Dirección o puerto erróneos, el servidor está caído o no es alcanzable desde el contenedor de Downtify |
| **No parece Navidrome.** | Algo respondió, pero no la API Subsonic — a menudo un puerto erróneo, o una URL base que falta en la dirección |
| **El certificado HTTPS no es de confianza.** | Usa `http://` en tu propia red, o un certificado de una autoridad de confianza; Downtify no omite la comprobación de certificados |

Los derechos de escaneo solo se consultan — probar nunca inicia un escaneo. Editar cualquier campo borra el último resultado, y el botón sigue desactivado hasta que se rellenan la dirección, el usuario y la contraseña.

::: info No se devuelve nada a la página
La respuesta lleva solo lo que se encontró — una versión, una ruta, un estado — nunca tu contraseña ni la petición que hizo Downtify.
:::

### Sincronización de playlists

El reflejo lo configuran los admins (Ajustes → Navidrome); las cuentas normales no pueden crear espejos, aunque sus descargas se reflejan como las de cualquiera una vez activada la integración.

Con **Crear playlists en Navidrome** activado, Downtify crea (o actualiza) una playlist de Navidrome con el mismo nombre después de:

- terminar la descarga de una playlist de Spotify,
- que un barrido del [Monitor de playlists](playlist-monitor.md) añada canciones,
- borrar canciones de la Biblioteca, o [reparar las rutas de la biblioteca](library-catalog.md#fix-library-paths).

Las canciones se asocian a las de Navidrome primero por ruta, luego por etiquetas. **Hacer públicas las playlists de Navidrome** controla la visibilidad de la playlist en Navidrome.

::: warning Se borran los archivos cuyas etiquetas no coinciden con la playlist
Cuando se actualiza una playlist (tras borrados, **Reparar rutas de la biblioteca** o **Descargar las que faltan** en una playlist ya completa), un archivo de la biblioteca registrado para una canción de Spotify se **borra del disco** si su título/artista incrustados claramente no coinciden con esa canción — Downtify lo trata como una descarga equivocada. Tenlo en cuenta si editas etiquetas a mano.
:::

### Portada de la playlist

Nada que configurar: con [Guardar la portada de la playlist](playlist-cover-art.md) activado, Navidrome recoge el `.jpg` que Downtify escribe junto al M3U de la playlist como **imagen auxiliar (sidecar)** — su propia forma de resolver la imagen de las playlists — siempre que su carpeta de música cubra ese archivo. Downtify no hace ninguna llamada a la API para ello.

## Descargas de playlists

La página **Biblioteca** lista las playlists de Spotify que has descargado con Downtify en **Descargas de playlists**. Expándela para ver, de cada playlist, cuántas canciones están en tu biblioteca frente a la lista actual de canciones de Spotify. Desde ahí puedes:

- **Descargar las que faltan** — pone en cola solo las canciones que aún no están en tu biblioteca.
- **Reproducir** las canciones ya descargadas.
- Expandir una playlist para ver y descargar canciones que faltan una a una.
- **Eliminar** la playlist — consulta abajo.

### Eliminar una playlist

Eliminar una playlist (desde este panel, o con **Eliminar playlist** junto al filtro de playlists de la Biblioteca) borra del disco todas las canciones registradas en ella — **incluidas las canciones que otras playlists también contienen** — además de su archivo M3U y la [portada](playlist-cover-art.md) guardada a su lado, y deja de seguirla. Las demás playlists que compartían esas canciones tienen su M3U y su playlist de Navidrome reescritos en segundo plano.
