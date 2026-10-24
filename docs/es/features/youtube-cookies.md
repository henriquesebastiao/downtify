---
icon: lucide/cookie
---

# Cookies de YouTube

Downtify obtiene su audio de YouTube. La mayoría de las veces funciona de forma anónima — pero no siempre:

- **Canciones explícitas / con restricción de edad.** YouTube solo las sirve a una cuenta de adulto con sesión iniciada. Sin cookies, la descarga falla.
- **Desafíos anti-bot.** En IP de centros de datos (VPS, algunas VPN), YouTube responde periódicamente con «Inicia sesión para confirmar que no eres un bot» en lugar de audio.

Aportar un `cookies.txt` arregla ambos: yt-dlp pasa a hablar con YouTube como lo hace tu sesión iniciada en el navegador.

## Subir un cookies.txt (recomendado)

1. Instala una extensión para exportar cookies: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome/Edge) o [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox)
2. Abre `youtube.com` **con la sesión iniciada en tu cuenta de Google** y exporta las cookies de ese sitio — el archivo debe estar en formato **Netscape**
3. En Downtify, abre **Ajustes** (⚙️) → **Cookies de YouTube** → **Subir cookies.txt**

El archivo se valida al subirlo — un archivo que no sea un cookie jar Netscape se rechaza de inmediato en lugar de romper en silencio todas las descargas posteriores. Si no contiene cookies de `youtube.com` ni de `google.com`, recibes un aviso, ya que normalmente significa que se exportó desde la pestaña equivocada.

Una vez subido, puedes **reemplazarlo** (subiendo otro archivo) o **eliminarlo** desde la misma pantalla.

::: tip Esta es la vía independiente de la plataforma
Subirlo desde la interfaz web no necesita bind mounts, ni rutas de archivo ni shell — por eso funciona en Docker Desktop para Windows, donde montar un `cookies.txt` en el contenedor es notoriamente incómodo.
:::

## Dónde se guarda

El archivo subido se escribe como `cookies.txt` dentro del directorio de datos de Downtify (`/data` por defecto) — el mismo volumen que contiene `settings.json` y la base de datos del Monitor de playlists. Por eso **sobrevive a las actualizaciones del contenedor**: descargar una imagen nueva y recrear el contenedor conserva tus cookies, mientras `/data` siga siendo un volumen con nombre o un bind mount.

## Usar una variable de entorno en su lugar

La variable [`DOWNTIFY_COOKIES_FILE`](../getting-started/environment-variables.md#anti-bot-youtube), que ya existía, sigue funcionando y **tiene prioridad**:

```yaml
services:
  downtify:
    volumes:
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

Cuando está definida, la pantalla de ajustes muestra la sección de cookies bloqueada y rechaza subidas y eliminaciones — el despliegue es dueño de esa configuración, y Downtify no debe sobrescribir un archivo que no gestiona. Quita la variable (y recrea el contenedor) para gestionar las cookies desde la interfaz web.

`DOWNTIFY_COOKIES_FROM_BROWSER` lee las cookies directamente de un perfil del navegador, pero eso exige que el almacén de cookies del navegador sea accesible *dentro* del contenedor, así que rara vez se puede usar en Docker.

## Mantenerlas funcionando

- Las cookies caducan. Si las descargas con restricción de edad vuelven a fallar, exporta un archivo nuevo y súbelo como reemplazo.
- Exportar desde una **ventana privada/incógnito** que luego cierras produce una sesión más duradera, porque cerrar una ventana normal puede invalidar la sesión exportada.
- Algunas regiones exigen una verificación de identidad completa en la cuenta de Google antes de que YouTube sirva contenido con restricción de edad. Haber iniciado sesión no siempre basta.

::: warning Trata el archivo como una contraseña
Un `cookies.txt` contiene tokens de sesión activos de tu cuenta de Google. Quien pueda leerlo puede actuar como tú en YouTube. Downtify lo guarda con permisos solo para el propietario donde el sistema de archivos lo permite, y nunca expone su contenido por la API — solo si hay uno configurado, su tamaño y cuándo cambió. Usa una cuenta de Google desechable si prefieres no arriesgar la principal.
:::
