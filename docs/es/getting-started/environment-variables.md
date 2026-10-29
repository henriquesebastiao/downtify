---
icon: lucide/settings
---

# Variables de entorno

Todas las variables de entorno son opcionales. Downtify funciona de inmediato sin ninguna de ellas.

## Principales

| Variable | Valor por defecto | Descripción |
|----------|---------|-------------|
| `DOWNTIFY_PORT` | _(sin definir)_ | Puerto en el que escucha el servidor (dentro del contenedor). Sin definir: el puerto elegido en **Ajustes → Servidor → Puerto**, o si no `8000`. Definida, tiene prioridad y el campo de Ajustes queda bloqueado. Cambia el lado izquierdo de la asignación de puertos para exponer otro puerto del host. Consulta [Cambiar el puerto](../features/server.md#changing-the-port). |
| `DOWNLOAD_DIR` | `/downloads` | Directorio donde se guardan los archivos de audio. Cámbialo si montas tu biblioteca en otra ruta. |
| `HOST` | `0.0.0.0` | Dirección de enlace del servidor web. |
| `DOWNTIFY_LOG_LEVEL` | `info` | Nivel de log de la aplicación (`debug`, `info`, `warning`, …). |
| `TZ` | `UTC` | Zona horaria local (nombre IANA, p. ej. `America/Sao_Paulo`), usada para interpretar `DOWNTIFY_MONITOR_SYNC_TIME` más abajo. |

## Monitor de playlists

| Variable | Valor por defecto | Descripción |
|----------|---------|-------------|
| `DOWNTIFY_MONITOR_SYNC_TIME` | _(sin definir)_ | Hora del día (`HH:MM` en 24 h, en la zona de `TZ` indicada arriba) a la que deben ejecutarse las sincronizaciones del [Monitor de playlists](../features/playlist-monitor.md#choosing-a-daily-sync-time) con un intervalo de un día o más (cada día, semana, 2 semanas, mes). Déjala sin definir para sincronizar exactamente un intervalo después de la comprobación anterior, caiga a la hora que caiga. |

```yaml
environment:
  - TZ=America/Sao_Paulo
  - DOWNTIFY_MONITOR_SYNC_TIME=03:00
```

## Apps móviles e inicio de sesión

Consulta [Apps móviles](../features/mobile-apps.md) y [Usuarios e inicio de sesión](../features/users.md). Iniciar sesión es obligatorio salvo que `DOWNTIFY_DISABLE_AUTH` sea `true`; `DOWNTIFY_REQUIRE_SIGN_IN` de versiones anteriores ya no se usa (se registra un aviso mientras esté definida).

| Variable | Valor por defecto | Descripción |
|----------|---------|-------------|
| `DOWNTIFY_DISABLE_AUTH` | `false` | `true` desactiva las cuentas: nadie inicia sesión, y quien llegue al servidor lo usa como administrador. La página de inicio de sesión, los botones de cerrar sesión, **Ajustes → Usuarios** y la parte de cuenta de **Ajustes → General** desaparecen. Las apps vinculadas siguen funcionando. Vuelve a `false` (o quítala) y se vuelve a exigir el inicio de sesión, con las cuentas tal como estaban. Consulta [Usuarios e inicio de sesión](../features/users.md#turning-accounts-off). |
| `DOWNTIFY_TRUSTED_PROXIES` | _(sin definir)_ | Direcciones o redes de tu proxy inverso, separadas por comas (p. ej. `172.18.0.0/16,10.0.0.5`). Solo las peticiones procedentes de ellas tienen sus cabeceras `X-Forwarded-For`, `X-Forwarded-Proto` y `X-Forwarded-Host` tomadas en cuenta — para la dirección del cliente por la que se limitan los intentos de inicio de sesión y de vinculación, la marca secure de la cookie de sesión y la comprobación de mismo origen. Sin definir: esas cabeceras se ignoran. |
| `DOWNTIFY_DISCOVERY` | `true` | `false` deja de anunciar el servidor en la red local (mDNS, `_downtify._tcp`), que las apps usan para listarlo en *Encontrados en esta red*. En la red bridge de Docker el anuncio no llega a la LAN de todos modos — consulta [Docker Compose](docker-compose.md#finding-the-server-from-the-apps). |
| `DOWNTIFY_TRANSCODE_CACHE_MB` | `2048` | Tamaño máximo, en MB, al que se mantiene la caché de copias transcodificadas (`/data/transcode_cache`); las copias reproducidas hace más tiempo salen primero. |
| `DOWNTIFY_TRANSCODE_CONCURRENCY` | `2` | Cuántas canciones se transcodifican a la vez para las calidades de streaming más pequeñas de las apps. |
| `DOWNTIFY_STREAM_CACHE_MB` | `1024` | Tamaño máximo, en MB, al que se mantiene la caché de audio emitido en streaming (`/data/stream_cache`); las copias reproducidas hace más tiempo salen primero. El streaming a través del servidor es lo que reproduce canciones sin descargar donde el propio navegador no llega a YouTube. |
| `DOWNTIFY_STREAM_CONCURRENCY` | `2` | Cuántas descargas de streaming pueden ejecutarse a la vez. |

## Papelera de música

Consulta [Papelera de música](../features/music-trash.md). Desactivada salvo que se defina una de estas.

| Variable | Predeterminado | Descripción |
|----------|---------|-------------|
| `DOWNTIFY_TRASH` | `false` | `true` activa la papelera de música para la carpeta de descargas: quitar canciones las mueve a una papelera que se guarda 30 días, y el propio Downtify mueve los archivos. Mientras está activa, solo los administradores quitan canciones. |
| `DOWNTIFY_TRASH_CONFIG` | _(sin definir)_ | Ruta, dentro del contenedor, de un archivo JSON con las carpetas que cubre la papelera y dónde se ejecuta su worker (`embedded` o `external`). Tiene prioridad sobre `DOWNTIFY_TRASH`. Un archivo que no se puede leer impide que el servidor arranque. Consulta [El archivo de configuración](../features/music-trash.md#the-configuration-file). |

## Comprobación de estado

La imagen incluye un [`HEALTHCHECK` de Docker](https://docs.docker.com/reference/dockerfile/#healthcheck) integrado — no hace falta un `--health-cmd` propio. Consulta `GET /api/health` en el puerto del propio contenedor cada 30 segundos (timeout de 5 segundos, 20 segundos de margen en el arranque, 3 reintentos antes de marcar el contenedor como no saludable). `docker ps` y `docker inspect` muestran el resultado, y herramientas como el `condition: service_healthy` de Compose o Watchtower pueden actuar en consecuencia.

| Variable | Valor por defecto | Descripción |
|----------|---------|-------------|
| `DOWNTIFY_HEALTHCHECK` | `1` | Ponla a `0` para desactivar la comprobación integrada — pasa a informar siempre «saludable» sin contactar con el servidor. Úsala si una comprobación externa o del orquestador (p. ej. una liveness probe de Kubernetes) debe ser la única que decida la salud del contenedor. |

```yaml
environment:
  - DOWNTIFY_HEALTHCHECK=0
```

## Anti-bot / YouTube

YouTube desafía periódicamente a los descargadores automatizados. Estas variables te dan salidas de emergencia cuando los valores por defecto dejan de funcionar.

| Variable | Valor por defecto | Descripción |
|----------|---------|-------------|
| `DOWNTIFY_FORCE_IPV4` | _(sin definir)_ | Ponla a `1` para forzar a yt-dlp a usar solo IPv4. Útil cuando tu host tiene una dirección IPv6 rota o limitada. |
| `DOWNTIFY_YT_PLAYER_CLIENTS` | `ios,android,web_embedded,mweb,web,tv` | Lista, separada por comas, de los clientes de reproductor de yt-dlp que se probarán, en orden. La lista por defecto de Downtify ya favorece clientes que funcionan sin un runtime de JavaScript. Cámbiala solo si sabes que un cliente concreto está bloqueado. |
| `DOWNTIFY_YT_PO_TOKEN` | _(sin definir)_ | Tokens Proof-of-Origin para yt-dlp, separados por comas, cada uno con la forma `<client>.<context>+<token>` (p. ej. `mweb.gvs+ABC123`). Solo hacen falta si YouTube empieza a exigir PO Tokens para los clientes que usas. |
| `DOWNTIFY_COOKIES_FILE` | _(sin definir)_ | Ruta de un `cookies.txt` en formato Netscape **dentro del contenedor**. Permite a yt-dlp autenticarse como una sesión real de navegador — necesario para canciones explícitas/con restricción de edad y siempre que YouTube imponga un muro de inicio de sesión. Tiene prioridad sobre un archivo subido en la interfaz web y deja esa sección de la interfaz de solo lectura. Consulta [Cookies de YouTube](../features/youtube-cookies.md). |
| `DOWNTIFY_COOKIES_FROM_BROWSER` | _(sin definir)_ | Nombre del navegador del que extraer las cookies (p. ej. `chrome`, `firefox`). Requiere que el almacén de cookies del navegador sea accesible dentro del contenedor, así que rara vez se puede usar en Docker. |

::: tip Probablemente no las necesites
Puedes subir un `cookies.txt` directamente desde **Ajustes → Cookies de YouTube** en la interfaz web. Se guarda en `/data` (así que sobrevive a las actualizaciones del contenedor), no necesita bind mount ni ruta del contenedor y funciona igual en Windows, macOS y Linux. Las variables de arriba siguen admitidas para despliegues que prefieren gestionar el archivo ellos mismos.
:::

## Ejemplo: Docker Compose con ajustes anti-bot

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_FORCE_IPV4=1
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
    restart: unless-stopped
```

## Obtener un cookies.txt

Usa una extensión del navegador como [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome) o [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox). Exporta desde `youtube.com` con la sesión iniciada en una cuenta de Google real y luego sube el archivo en **Ajustes → Cookies de YouTube** o móntalo en el contenedor como se muestra arriba.

Consulta [Cookies de YouTube](../features/youtube-cookies.md) para ver el paso a paso completo y [Solución de problemas](../troubleshooting.md) cuando las descargas sigan fallando.

::: warning
Mantén tu `cookies.txt` en privado — contiene tokens de sesión que dan acceso a tu cuenta de Google.
:::
