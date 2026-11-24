---
icon: lucide/mic-vocal
---

# Letras

Downtify busca letras mientras se descarga una canción y las incrusta en el archivo, además de un archivo auxiliar `.lrc` cuando están sincronizadas con el tiempo.

## Activar las letras

Las letras están **activadas por defecto**. Desactívalas en **Ajustes → Etiquetas y letras → Descargar letras**.

## Proveedores y orden de prueba

Los catálogos difieren: una canción que un proveedor no conoce suele estar en otro. Por eso Downtify mantiene una lista ordenada de proveedores y los prueba de uno en uno, deteniéndose en el primero que tenga algo.

| Proveedor | Letras | Notas |
|----------|--------|-------|
| **[LRCLIB](https://lrclib.net)** | Simples y sincronizadas | Base de datos comunitaria gratuita, sin clave. Coincidencia por título, artista principal, álbum y duración. Si así no encuentra nada sincronizado, también se prueba su búsqueda; un resultado vale si título, artista y duración (con pocos segundos de diferencia) coinciden. |
| **NetEase Cloud Music** | Normalmente sincronizadas | Catálogo grande, fuerte en lanzamientos asiáticos y a menudo también en occidentales. Coincidencia por título, artista y duración; un resultado cuyo artista se escribe distinto (chino tradicional frente a simplificado, por ejemplo) solo se acepta cuando el título y la duración coinciden. |
| **Kugou Music** | Sincronizadas | Catálogo grande, fuerte en lanzamientos chinos y con muchos occidentales. Se empareja como NetEase; se quitan la línea del título y los créditos de composición del principio. |

En **Ajustes → Etiquetas y letras → Proveedores** puedes arrastrar los proveedores al orden que prefieras, o usar las flechas, y desactivar cualquiera de ellos. Al menos uno queda activado; para dejar de buscar letras por completo, usa el interruptor **Descargar letras**. Un proveedor añadido en una actualización empieza desactivado si ya habías guardado tu propia lista: actívalo ahí.

### Solo letras sincronizadas

**Ajustes → Etiquetas y letras → Solo letras sincronizadas** (desactivado por defecto) conserva solo letras con marcas de tiempo: si un proveedor solo tiene letra simple para una canción, cuenta como nada y se pregunta al siguiente. [Mejorar biblioteca](library-upgrade.md) cuenta entonces también como sin letra una pista que solo tiene letra simple. Las letras sincronizadas que ya tenga un archivo cuentan siempre: un archivo `.lrc` al lado, letras con marcas de tiempo en sus etiquetas o un marco ID3 `SYLT` (como a veces traen archivos de otras apps). Con el ajuste activado, la letra sincronizada que encuentra Downtify reemplaza la simple: en el archivo `.lrc` y en la etiqueta de letra del propio archivo, así los reproductores que solo leen las etiquetas también la muestran sincronizada. El escaneo indica además cuántas de las pistas sin letra solo tenían letra simple.

### Buscar letras para pistas que no tienen

**Biblioteca → Mejorar biblioteca → Escanear y buscar letras** escanea la biblioteca en busca de pistas sin letra y las busca enseguida, con una barra de progreso. Al terminar indica cuántas pistas consiguieron letra, para cuántas no se encontró y cuántas fallaron. Consulta [Mejorar biblioteca](library-upgrade.md#while-it-runs).

::: info ¿Y Genius, Musixmatch y AZLyrics?
No están disponibles, y Downtify ya no los ofrece:

- **AZLyrics** prohíbe el uso por terceros de sus letras en la propia página.
- La API de escritorio de **Musixmatch** responde con un token vacío salvo que tengas credenciales que no entrega a las aplicaciones.
- El `robots.txt` de **Genius** no permite el endpoint de búsqueda necesario para encontrar la página de una canción.

Los ajustes guardados que aún los nombran siguen funcionando: los nombres se ignoran, y una lista que se queda sin nada más vuelve a los proveedores predeterminados.
:::

## Omitir proveedores que no tenían nada

Tras una búsqueda, Downtify registra para cada canción qué proveedores respondieron y cuáles volvieron vacíos, en `downtify_library.db` dentro de `/data`.

A un proveedor que no tenía nada para una canción no se le vuelve a preguntar por ella durante **30 días**, para que las redescargas y los grandes repasos de la biblioteca no repitan las mismas búsquedas fallidas. Pasado ese tiempo se vuelve a probar, ya que los catálogos crecen. Un proveedor que *sí* tenía letra nunca se omite, así que un archivo redescargado la recupera.

## Incrustación

| Formato | Etiqueta de letra simple | Etiqueta de letra sincronizada |
|--------|-----------------|------------------|
| MP3 | `USLT` (ID3) | `USLT` con marcas de tiempo |
| FLAC | `LYRICS` (comentario Vorbis) | `LYRICS` con contenido LRC |
| M4A | `©lyr` | `©lyr` con contenido LRC |
| OGG / OPUS | `LYRICS` (comentario Vorbis) | `LYRICS` con contenido LRC |

## Archivo auxiliar .lrc

Cuando hay letras sincronizadas, Downtify también guarda un archivo `.lrc`. Por defecto está **junto al audio** con el mismo nombre base. En **Ajustes → Etiquetas y letras** puedes desactivarlo y elegir en su lugar una **carpeta de letras** (por defecto `/data/lyrics`). Esa carpeta debe estar **fuera** de `/downloads`, del árbol de slskd y de cualquier carpeta de música adicional — la ruta relativa del audio se recrea dentro de ella (`Artista/Álbum/canción.lrc`). Los reproductores que leen letras externas (y el [reproductor integrado](player.md#now-playing)) siguen encontrando el archivo auxiliar. Cambiar este ajuste y ejecutar **Sincronizar** en una carpeta adicional copia los `.lrc` existentes a la nueva ubicación; el archivo de origen se elimina cuando ese árbol es escribible, y se deja en su sitio en un montaje de solo lectura. Se escribe un archivo auxiliar aunque las letras ya estén incrustadas en las etiquetas.

Eliminar la canción desde la página de la Biblioteca elimina el `.lrc` (junto al archivo y en la carpeta dedicada) junto con el audio, así que la letra nunca queda como un archivo huérfano.

## Ajustar la sincronía

Las letras encontradas en internet a veces van un poco adelantadas o atrasadas respecto al audio descargado: otra edición de la canción, una introducción más larga. Para corregir una canción, reprodúcela, abre **Reproduciendo → Letra** y pulsa el botón del cronómetro arriba a la derecha de la letra, **Ajustar sincronía de la letra**:

- **−** muestra la letra antes y **+** después, una décima de segundo por pulsación, hasta un minuto en cada sentido. La letra sigue el nuevo tiempo al instante, así que puedes probarlo mientras suena la canción.
- **Guardar** lo escribe en los archivos de la canción; **Restablecer** vuelve al tiempo guardado.

Guardar reescribe las propias marcas de tiempo, en el `.lrc` y, cuando las etiquetas del archivo tienen letra sincronizada, también en ellas (incluidos los marcos `SYLT` de MP3). Así la corrección también se ve en otros reproductores que leen el `.lrc` o las etiquetas, y en las apps. Un archivo de solo lectura conserva sus etiquetas; solo cambia el `.lrc`. Una línea `[offset:N]` en un `.lrc` se incorpora a los tiempos al guardar, y el reproductor de Downtify ya la respeta antes.

El botón solo aparece en canciones de la biblioteca con letra sincronizada. Cualquier usuario con sesión iniciada puede ajustarla; el cambio aparece en el [registro de actividad](users.md#activity) como **Sincronía de letras ajustada**. El endpoint es [`POST /api/library/lyrics/offset`](../api-reference.md#post-apilibrarylyricsoffset).

## Cuando no se encuentra nada

Si ningún proveedor tiene la canción, la descarga continúa con normalidad — el archivo de audio se guarda sin letras y no se genera ningún error.
