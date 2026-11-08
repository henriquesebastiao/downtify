---
icon: lucide/replace
---

# Reemplazar audio

Downtify elige automáticamente el audio de cada canción, y a veces elige el equivocado: otra canción con el mismo nombre, una versión en directo, un remix o una subida con una intro larga. **Reemplazar audio** te deja elegir la versión correcta a mano. La canción conserva su lugar en todas partes — sus playlists, archivos M3U, «me gusta» y apps vinculadas — y solo cambia el audio.

Solo los administradores pueden reemplazar audio (consulta [Usuarios e inicio de sesión](users.md#admins-and-users)).

## Reemplazar el audio de una canción

1. En la **Biblioteca**, abre el menú de la canción (clic derecho, o el botón **⋯**) y elige **Reemplazar audio…**.
2. Downtify busca «Artista - Título» en **YouTube Music** y en **YouTube** y lista lo que encuentra. Cambia la búsqueda, o pega un enlace de YouTube o YouTube Music a un vídeo o canción, para obtener exactamente la subida que quieres.
3. Elige una versión. Cada una muestra de dónde viene y cuánto dura, junto a la duración de tu archivo. Una versión a menos de 3 segundos de la duración de tu archivo aparece resaltada. El botón ↗ la abre en YouTube, para que puedas escucharla antes de elegir.
4. Pulsa **Reemplazar audio**. El reemplazo se ejecuta como una descarga: muestra su progreso en el diálogo y en la **Cola**, y el diálogo indica cuándo ha terminado.

Si falla (el vídeo no está disponible, o YouTube pide iniciar sesión — consulta [Cookies de YouTube](youtube-cookies.md)), tu archivo queda exactamente como estaba. **Reintentar** en la Cola prueba el mismo vídeo otra vez, y pegar otro enlace allí reemplaza con ese.

## Qué permanece igual

- **El archivo.** El audio nuevo se escribe en la misma ruta, en el mismo formato: un `.mp3` sigue siendo MP3 (con la tasa de bits elegida en [Ajustes de descarga](download-settings.md)), un `.flac` sigue siendo FLAC, y así sucesivamente. Así, toda playlist, archivo M3U, canción favorita, entrada de Navidrome y app vinculada que apunta al archivo sigue apuntando a él.
- **Las etiquetas.** Título, artistas, álbum, número de pista, año, carátula, letra incrustada y todas las demás etiquetas se copian del archivo antiguo al audio nuevo tal cual. El archivo auxiliar `.lrc` no se toca. La letra sincronizada se ajustó al audio antiguo: si la versión nueva empieza en otro punto, puede desfasarse.
- **La fecha.** El archivo conserva su fecha de modificación, así que no salta al principio de «Añadido recientemente».

Solo se pueden reemplazar archivos `.mp3`, `.flac`, `.m4a`, `.ogg` y `.opus` — los formatos que escribe Downtify.

## Cómo funciona

El vídeo elegido se descarga junto al archivo con un nombre temporal que la biblioteca ignora (`<nombre>.downtify-upgrade.<ext>`), se convierte al formato del archivo, se comprueba que sea audio legible, se le dan las etiquetas del archivo antiguo y solo entonces se mueve sobre el antiguo. La API está en la [referencia de la API](../api-reference.md#get-apilibraryreplacecandidates).
