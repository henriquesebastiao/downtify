---
icon: lucide/headphones
---

# Reproductor integrado

Downtify incluye un reproductor web para que escuches tu música descargada sin una app aparte. Pulsa reproducir en cualquier canción, álbum, artista o playlist de la Biblioteca — o en una descarga terminada de la Cola — y el reproductor arranca.

## Barra del reproductor

Mientras hay una canción cargada, una barra del reproductor flota al pie de todas las páginas: portada, título y artista, aleatorio, anterior, reproducir/pausa, siguiente, repetir, tiempo transcurrido/total y atajos a los paneles de letra y de a continuación (el de la letra se puede [ocultar](#hiding-the-lyrics)). En pantallas anchas también tiene un control de volumen y una barra de búsqueda a lo largo de su borde superior; en el móvil se reduce a lo esencial y muestra una fina línea de progreso.

Junto al título hay un corazón para [marcar la canción como me gusta](liked-songs.md); el móvil lo deja fuera de la barra para dejar sitio al título, y lo tiene en **Reproduciendo** y en las listas de canciones.

Haz clic en el título o la portada, o en el botón de expandir, para abrir **Reproduciendo**.

## Reproduciendo

Una vista a pantalla completa teñida con colores tomados de la portada del álbum actual:

- **Portada grande**, título y artista (haz clic en el artista o en la etiqueta *Reproduciendo desde* para ir a ese artista, álbum o playlist), con un corazón junto al título para [marcar la canción como me gusta](liked-songs.md). La portada y la letra se encogen con la ventana — también cuando solo cambias su altura — para quedar debajo de la cabecera.
- **Barra de búsqueda** — haz clic o arrastra, o usa las flechas cuando tenga el foco. Mientras suena una canción, suaves ondas se desplazan sobre la parte reproducida con colores tomados de la portada del álbum; se aplanan al pausar y se quedan quietas si tu sistema pide movimiento reducido
- **Controles de reproducción** — aleatorio, anterior, reproducir/pausa, siguiente, repetir (desactivado → repetir todo → repetir una)
- **Volumen** con botón de silencio, guardado entre sesiones. Oculto en el móvil, donde los botones físicos controlan el nivel
- **Temporizador** — detiene la reproducción en 15, 30, 45, 60 o 90 minutos, o al final de la canción actual. El tiempo restante aparece junto al botón del temporizador
- **Información del archivo** — formato y tamaño del archivo en reproducción

Cuatro paneles están junto a la portada en pantallas anchas, o la sustituyen en el móvil:

- **Letra** — las letras sincronizadas resaltan la línea actual y se desplazan con la canción; haz clic en una línea para saltar a ella. Las letras sin sincronizar se muestran tal cual. La letra viene del archivo `.lrc` junto a la canción, o de la incrustada en sus etiquetas — consulta [Letras](lyrics.md). Puedes ocultar este panel — consulta [Ocultar la letra](#hiding-the-lyrics).
- **A continuación** — la cola de reproducción. Arrastra canciones para reordenarlas, quita canciones sueltas o borra todo lo que hay después de la actual.
- **Detalles** — título, artista, álbum, número de canción, año, duración, formato, tamaño, fecha de adición y ruta del archivo.
- **Ecualizador** — da forma al sonido con diez bandas de frecuencia; consulta [Ecualizador](#equalizer).

Reproduciendo forma parte de la dirección de la página (`?np=1`, más `&panel=lyrics|queue|details|equalizer`), así que el botón Atrás del navegador lo cierra y una recarga lo mantiene abierto.

## Ocultar la letra

¿Prefieres la portada y la cola sin las palabras? Desactiva **Ajustes → General → Reproductor → Mostrar letras en el reproductor**. Se aplica al instante y quita todo lo que lleva a la letra en el reproductor:

- el panel **Letra** y su pestaña (en el móvil, su botón en el pie de Reproduciendo);
- el botón de letra de la barra del reproductor;
- el atajo `L`, que también desaparece de la lista de atajos (`?`).

Reproduciendo se abre entonces en **A continuación**. Un enlace a `&panel=lyrics` de antes de desactivarlo también aterriza ahí, en lugar de en una pestaña vacía. El reproductor ni siquiera pide la letra de una canción mientras está oculta.

::: info Ocultar no es borrar
Esto solo cambia lo que muestra el reproductor. Tus archivos conservan la letra que Downtify incrustó en ellos, y los archivos `.lrc` junto a ellos se quedan en su sitio, así que los servidores multimedia y otros reproductores los siguen viendo. Las descargas también siguen obteniendo letras — eso es el ajuste aparte **Descargar letras** en **Etiquetas y letras** (consulta [Letras](lyrics.md)).
:::

Igual que el tema y el ecualizador, la elección se guarda en el navegador (`localStorage`), así que es por dispositivo y por navegador, no por servidor Downtify — puedes ocultar la letra en el móvil y mantenerla en el ordenador.

## Ecualizador

Un ecualizador gráfico de diez bandas, en el panel **Ecualizador** de Reproduciendo (o pulsa `E`). Está marcado como **Experimental**: puede cambiar y puede fallar en algunos navegadores (consulta [Compatibilidad de navegadores](#browser-support)).

- **Bandas** en 31, 62, 125, 250, 500 Hz y 1, 2, 4, 8, 16 kHz, cada una ±12 dB en pasos de 0,5 dB. Las bandas de 31 Hz y 16 kHz son shelves, así que también suben o bajan todo lo que está por debajo / por encima. Arrastra una banda, o dale el foco y usa las flechas (`Page Up`/`Page Down` para 1 dB, `Home`/`End` para los límites); el doble clic la restablece a 0.
- **Preajustes** — Plano, Refuerzo de graves, Refuerzo de agudos, Voz, Rock, Electrónica y Acústica. Mover cualquier banda después convierte el preajuste en **Personalizado**.
- **Preamplificador** — ±12 dB sobre todo lo demás.
- **Interruptor de encendido** y **Restablecer** (vuelve a Plano, preamplificador 0, apagado). Mover una banda o elegir un preajuste también enciende el ecualizador.
- La curva detrás de los deslizadores es la respuesta combinada de todas las bandas.

Reforzar bandas empujaría la música fuerte más allá del fondo de escala y la distorsionaría, así que Downtify baja automáticamente el volumen en el mayor refuerzo de la curva — el panel dice cuánto. Eso mantiene el pico en 0 dB, de modo que un preajuste reforzado remodela el sonido en lugar de solo subirlo. Subir el preamplificador por encima de 0 dB quita ese margen de seguridad, y el panel avisa de que los pasajes fuertes pueden distorsionar.

Los ajustes se guardan en el navegador (`localStorage`) y se aplican a todo lo que reproduces, en todas las pestañas, hasta que los cambies. Son por navegador, no por servidor Downtify.

### Compatibilidad de navegadores

El ecualizador usa la Web Audio API, disponible en todos los navegadores actuales. Hasta que lo enciendes, la reproducción ni toca Web Audio. Una vez encendido, el audio del resto de la visita pasa por él — apagarlo solo aplana todas las bandas.

::: warning Safari en iPhone y iPad
iOS puede pausar Web Audio cuando la pantalla se bloquea o cambias de app, lo que detiene la reproducción con el ecualizador encendido. Si escuchas con la pantalla apagada, apaga el ecualizador y recarga la página.
:::

## Armar la cola

Reproducir un álbum, artista, playlist o la lista de canciones pone esas canciones en cola en orden, empezando por la que elegiste. **Aleatorio** en una colección la empieza en orden aleatorio. Las canciones que no has descargado suenan enteras directamente en la cola, servidas desde la caché de streaming del servidor: mientras suena una, la siguiente ya se está preparando con una canción de antelación, así que la reproducción atraviesa filas sin descargar sin detenerse — incluso donde el propio navegador no llega a YouTube. Una canción emitida en streaming nunca se guarda, ni se marca como me gusta, ni se recuerda tras recargar.

El menú de cada canción (el botón **⋯**, o clic derecho en el ordenador) tiene:

- **Reproducir a continuación** — inserta justo después de la canción actual
- **Añadir a la cola** — añade al final
- **Ir al álbum** / **Ir al artista**
- **Guardar en este dispositivo** — descarga el archivo a través del navegador
- **Eliminar de la biblioteca**

Las mismas acciones valen para una selección de varias canciones en la Biblioteca.

La cola, la canción actual, su posición, el aleatorio y la repetición se recuerdan, así que al reabrir Downtify se retoma donde lo dejaste (las colas de más de 2000 canciones no se recuerdan). Los archivos eliminados salen de la cola automáticamente.

## Teclado y teclas multimedia

| Tecla | Acción |
|-----|--------|
| `Space` | Reproducir / pausa |
| `←` / `→` | Avanzar/retroceder 5 segundos |
| `Shift` + `←` / `→` | Canción anterior / siguiente |
| `↑` / `↓` | Volumen |
| `M` | Silencio |
| `S` | Aleatorio |
| `R` | Repetir |
| `L` | Abrir la letra (salvo que esté [oculta](#hiding-the-lyrics)) |
| `Q` | Abrir a continuación |
| `E` | Abrir el ecualizador |
| `Ctrl` / `⌘` + `K` o `/` | Buscar |
| `G` y luego `L` / `D` | Ir a la biblioteca / cola |
| `Esc` | Cerrar Reproduciendo |
| `?` | Mostrar todos los atajos |

Los atajos se ignoran mientras escribes en un campo o hay un diálogo abierto.

El reproductor también informa de la canción actual al sistema operativo (Media Session), así que funcionan los controles de la pantalla de bloqueo, los botones de los auriculares y las teclas multimedia del teclado, con la portada mostrada donde el sistema lo admita.

## Cómo funciona

Las canciones vienen del listado de la biblioteca (`GET /tracks`), que lee título, artista, álbum, número de canción, año y duración de las etiquetas de cada archivo. Los archivos se sirven desde el montaje estático `/downloads`; las descargas de slskd [dejadas en su sitio](slskd-navidrome.md#leave-files-in-place) se reproducen a través de `/media/slskd/…`. La portada viene de `/cover` y la letra de `/lyrics` — consulta la [referencia de la API](../api-reference.md#file-management).

La reproducción usa el audio HTML5 nativo del navegador. Sin plugins, sin procesos extra.

## Formatos admitidos

El reproductor puede reproducir cualquier formato que admita el motor de audio HTML5 de tu navegador. Normalmente incluye MP3, M4A/AAC, OGG y OPUS en todos los navegadores modernos. La compatibilidad con FLAC varía — Chrome y Edge la admiten de forma nativa; Firefox y Safari quizá no.
