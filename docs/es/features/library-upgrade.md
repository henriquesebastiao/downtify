---
icon: lucide/wand-sparkles
---

# Mejorar biblioteca

Una biblioteca formada con el tiempo arrastra lo que cada versión de Downtify podía hacer cuando se descargó una canción: la portada más pequeña que ofrecía una fuente, sin letra, etiquetas sin álbum ni año. **Mejorar biblioteca** mira lo que ya está en disco y repara solo lo que va atrasado — sin volver a descargar y sin nada que arreglar a mano.

Ábrelo desde **Biblioteca → Mejorar biblioteca**.

::: info Las mejoras predeterminadas solo reescriben etiquetas
El modo predeterminado reescribe **portadas, letras y etiquetas**. La [sustitución por Deemix](#deemix-recording-replacement) opcional es un modo de escaneo aparte, desactivado por defecto. Usa [Reemplazar audio](replace-audio.md) para elegir manualmente otra versión.
:::

## Cómo funciona

1. **Escaneo.** Downtify lee todas las canciones de la biblioteca e informa de lo que va atrasado, por categoría. No se escribe nada.
2. **Elegir.** Cada categoría para la que el escaneo encontró algo se lista con su número de canciones y un interruptor. Desmarca lo que no quieras.
3. **Mejorar.** Las canciones elegidas entran en una cola que se recorre de una en una. Puedes pausar, reanudar o detenerla, y sobrevive a un reinicio.

## Qué repara

| Categoría | Qué hace | Dónde busca |
|---|---|---|
| **Mejorar portadas** | Sustituye una portada menor que el tamaño objetivo | Spotify, Apple Music (iTunes), YouTube Music |
| **Añadir letras que faltan** | Rellena la letra de las canciones que no la tienen, incrustada y como archivo `.lrc` | Tus [proveedores de letras](lyrics.md), en tu orden |
| **Actualizar etiquetas** | Rellena álbum, artista del álbum, fecha de lanzamiento y número de canción — incluido el álbum que les falta a las descargas antiguas de canciones sueltas | Spotify |

Una canción cuenta como atrasada cuando:

- el lado menor de su portada incrustada es **menor que el tamaño objetivo** (una canción sin portada también cuenta);
- no tiene **ni** letra incrustada **ni** archivo `.lrc` (junto al archivo o en la carpeta de letras de Ajustes);
- falta **álbum**, **artista del álbum**, **año** o **número de canción** en sus etiquetas.

**Actualizar etiquetas** solo funciona para canciones de las que Downtify aún tiene el ID de canción de Spotify — las que descargó de un enlace de Spotify, guardadas en el [índice de canciones](library-catalog.md#what-gets-stored). Las demás canciones entran en la cola pero vuelven como _Nada que hacer_.

## Opciones

### Mejorar portadas menores de

`300px` · `500px` · **`600px`** · `1000px` · `1200px`

Las portadas de este tamaño o mayores se dejan en paz. Downtify solo escribe una portada **estrictamente mayor** que la que ya está en el archivo, así que ejecutar una mejora dos veces nunca reescribe nada en vano.

De dónde vienen los tamaños:

| Fuente | Tamaño típico |
|---|---|
| **Apple Music (iTunes)** | 1200px o más |
| **Spotify** | hasta 640px |
| **YouTube Music** | hasta el ajuste de [resolución de la portada](download-settings.md), ~1200px como máximo |

Por eso también una biblioteca descargada antes suele quedarse en 300–640px: Spotify publica sus portadas en tamaños fijos, y el mayor que ofrece es 640px.

### Origen de las portadas

| Elección | Comportamiento |
|---|---|
| **La mayor resolución disponible** (predeterminado) | Pregunta a todas las fuentes y se queda con la imagen más grande |
| **Preferir Spotify** / **Preferir Apple Music** / **Preferir YouTube Music** | Usa esa fuente cuando tiene algo; las demás solo sirven de alternativa para cuando no tiene nada |

### No volver a revisar una canción durante

`Revisar siempre todas las canciones` · `7 días` · **`30 días`** · `90 días` · `365 días`

Tras mirar una canción, el siguiente escaneo la salta durante este tiempo, para que una segunda ejecución sobre una biblioteca grande no pregunte a las mismas fuentes por las mismas canciones otra vez.

La memoria se guarda **por canción y por categoría**, lo que hace funcionar las ejecuciones parciales: reparar solo las portadas de 16.000 canciones no dice nada de si alguien buscó alguna vez sus letras, así que una ejecución de letras posterior sigue considerándolas todas. Un escaneo también registra las categorías que examinó y para las que no encontró nada que hacer — mirar y no encontrar nada es una comprobación como cualquier otra.

Downtify recuerda, por cada canción y categoría: cuándo se comprobó, la versión de Downtify que la comprobó y — para portadas — la mayor portada encontrada y de dónde vino. Qué proveedores de letras ya se consultaron se guarda aparte, por canción y proveedor (consulta [Letras](lyrics.md)).

Dos cosas siempre la anulan:

- una **versión más nueva de Downtify** revisa todo de nuevo, ya que puede asociar o etiquetar mejor que la anterior;
- elegir **Revisar siempre todas las canciones** ignora la memoria en ese escaneo.

Cuando un escaneo no encuentra nada que hacer _porque_ todo se comprobó hace poco, lo dice y se ofrece a ejecutarse otra vez sin la memoria, en lugar de dejarte con un «nada que mejorar» sin explicación.

## Mientras se ejecuta

El panel de progreso muestra las canciones hechas de la cola, una cifra aproximada de datos (`8.4 GB of 51.3 GB`) y cuántas se mejoraron, no tenían nada que hacer o fallaron. Cada canción muestra lo que está haciendo — _Identificando_, _Buscando portada_, _Buscando letra_, _Escribiendo el archivo_ — y termina con lo que cambió, p. ej. `artwork 1200px (itunes)`.

**Pausar** se detiene tras la canción en curso y conserva la cola. **Detener** descarta el resto; las canciones ya mejoradas siguen mejoradas. Puedes salir de la página — la ejecución sigue, y cualquier otra pestaña abierta la sigue.

La cola vive en `/data/downtify_library.db`, así que **reiniciar Downtify (o el contenedor) a mitad de ejecución la retoma** donde se quedó. Una canción que estaba en curso cuando el proceso murió vuelve a la cola.

## No se pierde nada si una mejora falla

Toda escritura va a una copia de trabajo junto al original (`<nombre>.downtify-upgrade.<ext>`). La copia tiene que abrirse como audio de la misma duración antes de colocarse en su sitio; si no, se descarta y el original queda intacto. Ese archivo nunca aparece como una canción propia, y desaparece en cuanto la canción termina.

Se **conserva la fecha de modificación original**, así que mejorar una biblioteca no reordena _Añadido recientemente_.

### Carpetas de música de solo lectura

Una mejora reescribe etiquetas en el sitio, así que las canciones de un sistema de archivos de solo lectura se **omiten**, con una explicación, antes de buscar metadatos, portadas o letras. Siguen siendo reproducibles y están en sus playlists; sus archivos y permisos de montaje no cambian. Una canción de solo lectura omitida no se recuerda como comprobada con éxito, así que puede considerarse de nuevo si su carpeta pasa a ser escribible. Los errores inesperados de permisos, espacio en disco y E/S siguen apareciendo como fallos.

Esto difiere del [enriquecimiento de carpetas existentes](external-library.md), que puede guardar portadas y letras por separado en la carpeta de datos de Downtify sin reescribir archivos de audio protegidos.

## Por qué no se reemplaza el audio

Las mejoras ordinarias de etiquetas no reemplazan el audio. El modo aparte de abajo exige metadatos exactos de la grabación y referencia de publicación; las versiones inciertas quedan para revisión manual.

## Sustitución de grabaciones por Deemix

Tras activar y probar la [fuente Deemix](deemix.md), **Mejorar biblioteca** ofrece dos interruptores independientes antes de escanear:

- **Use verified Deemix recordings**: escanea las descargas originales de Downtify, incluidas las copias ocultas por una colección externa preferida. Asocia exactamente artista, título/versión completo y álbum; rechaza resultados ambiguos del catálogo. La duración del clip antiguo no se usa para rechazar una grabación correcta del catálogo. Verifica las etiquetas descargadas, la duración del catálogo, la calidad elegida y la decodificación completa con FFmpeg.
- **Remove old Downtify audio after import**: además, elimina cada original sin cambios tras la publicación. Está desactivado por defecto. Conservar los originales aun así actualiza playlists y favoritos a la grabación de Deemix.

Este escaneo produce una categoría de **audio** en lugar de tareas de portada/letra/etiquetas. Deemix es dueño de los archivos de salida, la portada, el diseño de álbumes y las letras nativas. Downtify los lee en el sitio. Las letras nativas o incrustadas existentes se conservan; solo las letras ausentes pueden complementarse en una carpeta de letras dedicada y escribible, sin reescribir el audio. Un original sin pérdidas de mayor calidad se conserva cuando Deemix está configurado para MP3.

La publicación ocurre una vez por lote. Los comentarios del M3U, los marcadores manuales y el orden de las canciones se conservan; luego las rutas del catálogo, las pertenencias a playlists, los «me gusta» de todos los usuarios, la propiedad y las reglas de canciones ocultas se mueven en una sola transacción SQLite. Los ids de Navidrome en caché de los archivos antiguos se invalidan para una nueva búsqueda nativa. Los ids móviles ya emitidos y las URL de reproducción antiguas conservan alias de solo lectura hacia el reemplazo registrado; las mutaciones nunca usan esos alias de URL.

Recibos duraderos en la base de datos de la biblioteca registran los valores SHA-256 de origen/destino y el estado de la publicación. Los orígenes permanecen hasta que el reemplazo y las referencias se verifican. Un montaje cambiado o ausente, un archivo editado, una referencia externa de solo lectura en una playlist, una reproducción activa o un fallo en la publicación del catálogo detienen la limpieza con un motivo visible. Pausar/reanudar y reiniciar reutilizan los recibos. No hay barrido general de duplicados ni limpieza por antigüedad: solo son elegibles los originales verificados en la carpeta de descargas de Downtify. Las descargas manuales de Deemix/slskd, los originales externos, los directorios y los sidecars nunca se borran. Una vez eliminado un original, revertir el contenedor no restaura ese archivo; restáuralo desde tu copia de seguridad de almacenamiento si hace falta.

Para consumidores de NAS cuyos nombres de montaje difieren de las rutas de Docker, un administrador puede definir `DOWNTIFY_DEEMIX_M3U_ROOT` con un alias del contenedor que resuelva a la raíz de Deemix. Las rutas relativas del M3U usan ese alias (por ejemplo `/Download` asignado a `/music/existing`). El opcional `DOWNTIFY_LIBRARY_READY_MARKERS` es un objeto JSON de rutas de marcadores y el texto esperado, comprobado antes de la preparación y de la limpieza. Un marcador ausente falla por seguridad. Ninguna de las variables es necesaria para el modo predeterminado.

La API de escaneo acepta `replace_audio_deemix: true`, opcionalmente `delete_replaced_audio: true`, y opcionalmente `files: ["relative/original.mp3"]` para un piloto acotado. Iniciar ese escaneo selecciona `categories: ["audio"]`. El estado de la ejecución incluye recuentos de reemplazos y un `finalization_error` cuando la publicación se detiene. Ningún archivo de origen se elimina solo porque un elemento de la cola de Deemix diga completado.

### Revisar una grabación incierta

Una tarea de audio omitida o fallida ofrece **Choose a Deezer recording**. Pega el enlace exacto de una canción, previsualiza su artista, álbum y duración, y elige **Analyze this choice**. Esto solo prepara un nuevo escaneo de una sola canción; confirma ese escaneo para iniciar el reemplazo. El asociador automático predeterminado nunca adivina un álbum diferente.

Esta elección explícita puede corregir una etiqueta de álbum antigua, pero el título/versión completo y el artista deben coincidir. Un original explícito conocido no puede convertirse silenciosamente en una versión limpia. La grabación elegida pasa las mismas comprobaciones de duración, calidad, decodificación, referencia y eliminación. Una elección distinta no puede reutilizar silenciosamente un recibo ya preparado. La carga avanzada del escaneo registra la elección como `deemix_recordings: {"relative/original.mp3": "123456"}`; está acotada a ese archivo y guardada para reinicio/reanudación.

## API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/library/upgrade` | Estado de la ejecución, recuentos de la cola y lo que encontró el escaneo |
| `GET` | `/api/library/upgrade/jobs` | Filas por canción (`status`, `stage`, `detail`) |
| `POST` | `/api/library/upgrade/scan` | Escanea la biblioteca; no escribe nada |
| `POST` | `/api/library/upgrade/start` | Inicia la ejecución para las `categories` elegidas |
| `POST` | `/api/library/upgrade/pause` | Se detiene tras la canción actual, conserva la cola |
| `POST` | `/api/library/upgrade/resume` | Continúa una ejecución en pausa |
| `POST` | `/api/library/upgrade/cancel` | Descarta el resto de la cola |

El progreso también se envía por el [WebSocket](../api-reference.md#websocket) como `{"type": "library_upgrade", "upgrade": {…}}`.

Consulta la [referencia de la API](../api-reference.md#library) para ver los formatos de petición y respuesta.
