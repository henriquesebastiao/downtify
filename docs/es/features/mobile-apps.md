---
icon: lucide/smartphone
---

# Apps móviles

Downtify puede dar servicio a apps en tu teléfono: navegan por la biblioteca y la reproducen en streaming directamente desde tu servidor, y guardan canciones en el teléfono para escucharlas sin conexión. Todo lo que necesita una app se configura en **Ajustes → Apps**: la vinculación de teléfonos y el nombre del servidor. Quién puede usar el servidor lo deciden las cuentas de [Usuarios e inicio de sesión](users.md).

::: warning La app sigue en desarrollo
**Ajustes → Apps** está marcado como *Experimental*. La parte del servidor descrita en esta página está terminada y funciona, pero **todavía no se ha publicado ninguna versión de la app Android**, así que por ahora no hay nada que instalar, y los detalles de la vinculación y el streaming aún pueden cambiar entre versiones de Downtify.

La app se desarrolla en abierto en [henriquesebastiao/downtify-android](https://github.com/henriquesebastiao/downtify-android). Cualquier otra cosa puede construirse sobre la misma API — consulta el [contrato del cliente móvil](../mobile-client-contract.md).
:::

## Iniciar sesión desde la app

Escribe la dirección del servidor (o elígelo en **Encontrados en esta red**) e inicia sesión con **el mismo usuario y contraseña** que en la página web. El teléfono aparece en **Apps vinculadas**, igual que si lo hubieras vinculado con un código más abajo: reproduce como tú, guarda una clave propia (la contraseña no se guarda en el teléfono) y **Desvincular** lo detiene.

Las contraseñas erróneas tienen límite de intentos junto con el inicio de sesión de la página web. Mientras las cuentas están desactivadas (`DOWNTIFY_DISABLE_AUTH`) no hay con qué iniciar sesión: vincúlalo con un código.

## Vincular un teléfono

Vincular no necesita contraseña en el teléfono: útil cuando la página web ya está abierta, o en un teléfono en el que prefieres no escribir tu contraseña.

1. Abre **Ajustes → Apps** y pulsa **Vincular un teléfono**.
2. En la app, elige **Escanear el código** y apunta la cámara al código QR — o escribe el código de 8 caracteres que aparece debajo (`K7QM-2XPD`; da igual mayúsculas o guiones).
3. El diálogo confirma cuándo el teléfono está vinculado, y aparece en **Apps vinculadas**.

El teléfono se vincula a **tu cuenta**: reproduce como tú y aparece en tu actividad. Cualquiera con una cuenta puede vincular sus propios teléfonos.

Un código funciona **una vez**, durante **cinco minutos**, y probar códigos erróneos tiene límite de intentos. El teléfono recibe una clave propia que conserva; el servidor solo guarda un hash de ella.

**Apps vinculadas** lista tus teléfonos (un admin ve los de todos, con el dueño de cada uno) con su plataforma, cuándo se vio por última vez y desde qué dirección. **Desvincular** detiene un teléfono al instante — su próxima petición falla, se cierra una conexión abierta y los enlaces que compartió (consulta [Transmisión (cast)](#casting)) dejan de funcionar. Para volver a usarlo, vincúlalo de nuevo.

## Qué puede hacer una app vinculada

Las apps vinculadas pueden navegar, reproducir, dar «me gusta», guardar canciones sin conexión y pedir al servidor que descargue música — pero no cambiar ajustes ni credenciales ni borrar archivos; eso requiere la página web, con la sesión iniciada como admin.

**Ajustes → Apps → Cerrar sesión en todas partes** desvincula todas tus apps y cierra tu sesión en todos los navegadores, incluido este. El inicio de sesión, las cuentas y la contraseña olvidada están en [Usuarios e inicio de sesión](users.md).

## Encontrar el servidor en tu red

El servidor se anuncia en la red local (mDNS / Bonjour, como `_downtify._tcp`), así que una app lo lista en **Encontrados en esta red** — nombre, dirección y versión — sin escribir nada. El nombre es el definido en **Ajustes → Apps → Nombre del servidor** (el hostname de la máquina hasta que lo cambies).

::: info La red por defecto de Docker oculta el anuncio
En la red *bridge* por defecto de Docker, el anuncio se queda dentro de Docker y los teléfonos no lo ven. O ejecutas el contenedor con `network_mode: host` (consulta [Docker Compose](../getting-started/docker-compose.md#finding-the-server-from-the-apps)), o escribes la dirección del servidor en la app — todo lo demás funciona igual.
:::

Define `DOWNTIFY_DISCOVERY=false` para dejar de anunciar.

## Calidad del streaming

Las apps reproducen los archivos tal cual (**Original**) o piden al servidor una copia más pequeña: Opus, AAC o MP3 a 96–320 kbps — útil con datos móviles. El servidor hace esa copia con ffmpeg la primera vez que se reproduce una canción así (unos segundos para una canción típica) y la conserva, así que buscar dentro de la canción funciona como en cualquier archivo y la siguiente reproducción es instantánea.

- Un archivo que ya es lo bastante pequeño (un archivo con pérdidas a un bitrate igual o inferior al pedido) se emite tal cual, nunca se recodifica.
- Las copias se guardan en `/data/transcode_cache`, 2 GB como máximo por defecto; las reproducidas hace más tiempo salen primero. Se hacen como mucho dos a la vez. Ambos límites son [variables de entorno](../getting-started/environment-variables.md#mobile-apps-and-sign-in).
- Si el teléfono abandona mientras se hace una copia, el servidor deja de hacerla.

## Transmisión (cast)

Las apps pueden enviar una canción a un Chromecast u otro reproductor que obtiene el audio por su cuenta. La app recibe del servidor un enlace que sirve para esa canción durante un tiempo limitado (una hora por defecto) y solo mientras el teléfono siga vinculado; ninguna clave del teléfono va dentro.

## Detrás de un proxy inverso

Si Downtify está detrás de nginx, Caddy, Traefik o similar (para HTTPS, o para acceder desde fuera):

- **Deja pasar el WebSocket.** `/api/ws` necesita que se reenvíen las cabeceras `Upgrade`/`Connection` (Caddy y Traefik lo hacen por defecto; nginx necesita `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";`).
- **Deja pasar las peticiones Range** sin cambios y no pongas en búfer las respuestas de audio (nginx: `proxy_buffering off;` para `/api/v1/` y `/downloads/`), o buscar dentro de la canción y los archivos grandes se resienten.
- **Dile a Downtify en qué proxy confiar.** Define `DOWNTIFY_TRUSTED_PROXIES` con la dirección del proxy (p. ej. `172.18.0.0/16`). Solo entonces usa Downtify `X-Forwarded-For` para la dirección del cliente (límites de intentos, «visto por última vez» en Apps vinculadas) y `X-Forwarded-Proto`/`X-Forwarded-Host` para marcar la cookie de sesión como segura y comprobar de dónde vienen las peticiones. Sin ello, esas cabeceras se ignoran — cualquiera podría enviarlas.
- **Usa HTTPS** cuando el servidor sea accesible desde fuera: la contraseña y las claves de las apps viajan en cada petición.

## Para desarrolladores de apps

Todo el flujo que sigue una app — descubrimiento, vinculación, sincronización de la biblioteca, streaming, informe de reproducciones — está en el [contrato del cliente móvil](../mobile-client-contract.md), y cada endpoint está en la [referencia de la API](../api-reference.md#server-and-sign-in).
