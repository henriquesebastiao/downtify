---
icon: lucide/life-buoy
---

# Solución de problemas

Problemas habituales y qué los arregla. La mayoría de los fallos de descarga se reducen a una de las dos primeras entradas.

## Una canción con contenido explícito no se descarga

**Síntoma** — la descarga falla y la cola muestra un mensaje sobre que la canción tiene restricción de edad, o (en versiones antiguas) un error en bruto como:

```
Error: ERROR: [youtube] <id>: Sign in to confirm your age.
This video may be inappropriate for some users.
```

**Causa** — YouTube solo sirve canciones con restricción de edad (explícitas) a una cuenta de adulto con sesión iniciada. Downtify descarga de forma anónima por defecto, así que YouTube se niega.

**Solución** — aporta cookies de YouTube: **Ajustes** (⚙️) → **Cookies de YouTube** → **Subir cookies.txt**. Consulta [Cookies de YouTube](features/youtube-cookies.md) para saber cómo exportar el archivo.

Si sigue fallando con las cookies configuradas, las cookies están caducadas o la propia cuenta no ha completado la verificación de edad de Google. Exporta un archivo nuevo desde un navegador con sesión iniciada en una cuenta verificada y súbelo de nuevo.

## Las descargas fallan, caducan o nunca empiezan

**Síntoma** — las descargas fallan con canciones aparentemente normales, a veces con «Inicia sesión para confirmar que no eres un bot» o un error de formato/extracción.

**Causa** — YouTube limita y desafía las peticiones que considera automatizadas. Es mucho más habitual en un VPS o detrás de una VPN que en una conexión doméstica.

**Solución**, por orden de lo mucho que suele ayudar:

1. **Sube un `cookies.txt`** ([Cookies de YouTube](features/youtube-cookies.md)). Una sesión autenticada recibe desafíos con mucha menos frecuencia. Es la corrección más eficaz.
2. **Añade una pausa entre descargas** — **Ajustes** → *Pausa entre descargas* (prueba 5–15 s) y reduce las *Descargas simultáneas*. Bombardear YouTube con una playlist entera de golpe es lo que activa la limitación.
3. **Fuerza IPv4** — define `DOWNTIFY_FORCE_IPV4=1` si tu host anuncia IPv6 pero en realidad no puede enrutarlo (aparece como errores de DNS/`EAI_AGAIN`).
4. **Actualiza la imagen** — `docker compose pull && docker compose up -d`. YouTube cambia sus defensas a menudo y cada versión trae un `yt-dlp` más reciente.

## No se reconoce un cookies.txt en Windows / Docker Desktop

**Síntoma** — `DOWNTIFY_COOKIES_FILE` está definida pero Downtify se comporta como si no hubiera cookies.

**Causa** — la ruta es una ruta *del contenedor*. Una ruta de Windows como `C:\Users\me\cookies.txt` no significa nada dentro del contenedor, y el archivo tiene que estar montado antes de que la variable pueda apuntar a él.

**Solución** — prescinde de la variable y sube el archivo por **Ajustes** → **Cookies de YouTube**. Esa vía no necesita montajes y funciona igual en todas las plataformas.

Si prefieres conservar la variable, monta el archivo y apunta al destino del montaje, no a la ruta del host:

```yaml
volumes:
  - ./cookies.txt:/cookies.txt:ro
environment:
  - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

## El botón de subir cookies aparece atenuado

`DOWNTIFY_COOKIES_FILE` está definida, así que ese despliegue gestiona su propio archivo de cookies y la interfaz web queda de solo lectura a propósito. Quita la variable (y vuelve a crear el contenedor) para gestionar las cookies desde la interfaz.

## Las cookies subidas desaparecieron tras actualizar el contenedor

El archivo subido está en el directorio de datos de Downtify (`/data`). Si ese directorio no es un volumen con nombre ni un bind mount, todo lo que contiene — los ajustes y la base de datos del Monitor de playlists incluidos — se pierde cuando se vuelve a crear el contenedor:

```yaml
volumes:
  - ./downloads:/downloads
  - downtify_data:/data   # ← conserva esto
```

## «cookies.txt is invalid» al subir

Downtify valida el archivo al subirlo. Debe ser un cookie jar **Netscape**: una cookie por línea, campos separados por tabuladores, opcionalmente con comentarios `#`. Se rechaza una exportación JSON, una hoja de cálculo o una cabecera `Cookie:` copiada.

Usa una extensión del navegador que exporte en formato Netscape (consulta [Cookies de YouTube](features/youtube-cookies.md)) y exporta con la pestaña en `youtube.com`.

## Una playlist vuelve a descargar canciones que ya tengo

Downtify registra cada canción descargada automáticamente en su base de datos, así que mover archivos a otro lugar del disco no provoca una redescarga. Una canción solo se vuelve a descargar después de que una comprobación horaria encuentre su archivo realmente ausente del directorio de descargas. Consulta [Monitor de playlists](features/playlist-monitor.md#how-it-works).

Si los archivos desaparecen en cada reinicio, el volumen `/downloads` no es persistente — misma solución que arriba.

## «Could not find a YouTube match for '…'»

Ni YouTube Music ni YouTube estándar devolvieron un resultado que pasara las comprobaciones del comparador — título parecido al original, al menos un artista en común, no ser versión de karaoke/cover/en directo/en otro idioma y duración a 30 segundos como máximo de la de Spotify. Consulta [Cómo funciona](how-it-works.md#fallback-to-standard-youtube).

Esto suele significar que la canción realmente no está en YouTube, o que solo se subió con un título o crédito de artista muy distinto. Si encuentras el vídeo correcto tú mismo, pega su URL de YouTube en la barra de búsqueda para descargar exactamente ese vídeo.

## El audio descargado tiene metadatos o portada equivocados

Downtify obtiene los metadatos de Spotify y empareja el audio en YouTube Music. Un desajuste suele significar que la coincidencia cayó en un cover, remix o versión en directo. Descargar desde el enlace del **álbum** de Spotify en lugar de un resultado de búsqueda da al comparador mucha más información (número de pista, álbum, tipo de lanzamiento).

## ¿Sigues atascado?

Abre un issue en [github.com/henriquesebastiao/downtify/issues](https://github.com/henriquesebastiao/downtify/issues) con:

- la versión de Downtify (se muestra al final de la barra lateral y en **Ajustes → Acerca de**),
- los registros del contenedor alrededor del fallo (`docker compose logs downtify`),
- y si hay cookies configuradas.
