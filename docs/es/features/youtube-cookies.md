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
      - ./cookies.txt:/cookies.txt
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

Móntalo con escritura (sin `:ro`) para que el mantenimiento pueda guardar en él las cookies rotadas; un archivo de solo lectura se sigue usando, pero caduca como antes.

Cuando está definida, la pantalla de ajustes muestra la sección de cookies bloqueada y rechaza subidas y eliminaciones — el despliegue es dueño de esa configuración, y Downtify no debe sobrescribir un archivo que no gestiona. Quita la variable (y recrea el contenedor) para gestionar las cookies desde la interfaz web.

`DOWNTIFY_COOKIES_FROM_BROWSER` lee las cookies directamente de un perfil del navegador, pero eso exige que el almacén de cookies del navegador sea accesible *dentro* del contenedor, así que rara vez se puede usar en Docker.

## Mantenerlas funcionando

Las cookies exportadas no caducan en una fecha fija. La sesión de Google es un conjunto de cookies que cambia sin parar: la pestaña de la que salieron rota `__Secure-1PSIDTS`, `SIDCC` y compañía cada pocos minutos, y una copia que nunca recibe los valores nuevos acaba rechazada. yt-dlp registra entonces "The provided YouTube account cookies are no longer valid". En una VPN o una IP de centro de datos YouTube es más estricto, así que puede pasar en un par de horas.

Downtify mantiene la sesión del archivo subido por sí solo:

- **Cada descarga guarda los valores nuevos.** yt-dlp recibe una copia privada del archivo en cada descarga; al terminar, las cookies que YouTube cambió durante ella vuelven al `cookies.txt` guardado, sin deshacer un valor más nuevo que otra descarga guardó mientras tanto.
- **Un mantenimiento las renueva periódicamente.** Cada 15 minutos (`DOWNTIFY_COOKIES_REFRESH_MINUTES`, `0` lo desactiva) Downtify pide a Google que rote las cookies de sesión —la misma petición que hace el navegador—, abre `youtube.com` con ellas y guarda lo que cambió. Incluso un servidor que pasa días sin descargar nada mantiene viva la sesión.
- **La pantalla de ajustes muestra el resultado.** **Ajustes → Cookies de YouTube** muestra *Sesión iniciada*, *Sesión cerrada*, *Sin cuenta* (el archivo no tiene sesión de Google, solo cookies de visitante) o *Error al comprobar*, cuándo se comprobó por última vez y cuándo YouTube pidió por última vez una verificación de bot. *Comprobar ahora* ejecuta el mantenimiento al momento. Una subida nueva se comprueba unos segundos después de guardarse.

Lo que sigue dependiendo de ti:

- **Exporta desde una ventana privada y ciérrala.** Inicia sesión en YouTube en una ventana privada, abre `youtube.com/robots.txt` en esa pestaña, exporta las cookies y cierra la ventana. Una pestaña que sigues usando rota la sesión por su cuenta y la copia de Downtify queda fuera en minutos. Si puedes, no uses la misma cuenta en una ventana normal a la vez.
- **Sube un archivo nuevo cuando la pantalla diga *Sesión cerrada*.** Google aún puede terminar la sesión (un cambio de contraseña, "cerrar sesión en todos los dispositivos", una revisión de seguridad). El log también lo dice: `YouTube cookies are signed out`.
- Algunas regiones exigen una verificación completa de identidad en la cuenta de Google antes de que YouTube sirva cualquier contenido con restricción de edad. Tener la sesión iniciada no siempre basta.

::: info Por qué no hay un botón "Iniciar sesión con Google"
Downtify no puede iniciar sesión en Google por ti. Google bloquea los inicios de sesión por script y en navegadores headless ("Este navegador o aplicación puede no ser seguro"), pide verificación en dos pasos y confirmaciones en el dispositivo, y YouTube ya no acepta OAuth de clientes de terceros como yt-dlp. Un formulario de inicio de sesión en Downtify también supondría entregarle tu contraseña de Google. Mantener viva una sesión exportada es la parte que se puede automatizar.
:::

::: tip Verificaciones de bot sin cuenta
"Sign in to confirm you're not a bot" depende de la dirección IP, no de que falten cookies. Si aparece una y otra vez con una VPN, cambiar de servidor o de país de salida suele ayudar más que unas cookies nuevas. Usar cookies en muchas descargas también aumenta la probabilidad de que YouTube limite esa cuenta, así que una cuenta desechable es la opción más segura.
:::

::: warning Trata el archivo como una contraseña
Un `cookies.txt` contiene tokens de sesión activos de tu cuenta de Google. Quien pueda leerlo puede actuar como tú en YouTube. Downtify lo guarda con permisos solo para el propietario donde el sistema de archivos lo permite, y nunca expone su contenido por la API — solo si hay uno configurado, su tamaño y cuándo cambió. Usa una cuenta de Google desechable si prefieres no arriesgar la principal.
:::
