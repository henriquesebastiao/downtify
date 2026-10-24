---
icon: lucide/image
---

# Foto, banner y biografía del artista

Downtify puede mostrar una foto de perfil real, un banner y una biografía de cada artista de tu Biblioteca, en lugar de una inicial generada y ningún texto. Esto se rellena solo la primera vez que abres la página de un artista nuevo, o en cuanto termina de descargarse una de sus canciones; después, eliges tú otra foto/banner, vuelves a obtener o escribes tu propia biografía y rellenas a mano los enlaces sociales.

La opción de edición siempre está disponible en la página de cada artista de la Biblioteca, sin tener que activar antes ningún ajuste.

::: info Sobre «Obtener fotos de artista automáticamente» / «Obtener banners de artista automáticamente» en Ajustes
**Ajustes → Descargas y archivos → Obtener fotos de artista automáticamente / Obtener banners de artista automáticamente** deciden si Downtify puede guardar por su cuenta la foto/banner de un artista — eso ocurre la primera vez que abres la página de un artista y cuando termina de descargarse una de sus canciones (consulta [La primera vez que abres un artista nuevo](#the-first-time-you-open-a-new-artist) y [Cuando termina una descarga](#when-a-download-finishes)). Las fotos vienen activadas por defecto, los banners desactivados. Nunca limitan el diálogo de edición: siempre puedes elegir una foto o banner a mano, digan lo que digan.
:::

## El diálogo de edición

**Cuando un artista tiene un banner definido, su foto redonda se oculta en la cabecera de la página** — el banner solo suele bastar, y mostrar ambos quedaba recargado. La foto no ha desaparecido, sin embargo: sigue ahí para editarla, a una pestaña de distancia.

En la página de un artista de la Biblioteca (`/library/artist?name=…`), pasa el ratón por la foto redonda (cuando se muestra) para ver un botón **Editar foto**, o por la zona del banner para ver un botón **Editar artista** — ambos abren el mismo diálogo: la foto actual del artista arriba y, debajo, un menú con cuatro pestañas. Se abre en **Perfil** o **Banner** según el botón en el que hiciste clic (por defecto **Banner**, ya que la foto no siempre es visible para hacer clic).

- **Perfil** / **Banner** — elige una imagen del mismo modo en cualquiera de los dos:
  - **Buscar por nombre** — busca en YouTube Music y Deezer una foto del artista que coincida (los artistas de Deezer que solo tienen su imagen genérica de relleno se dejan fuera). Escribe otra cosa para buscar otro nombre, o un enlace directo de imagen `http(s)://` para usarlo como candidato suelto.
  - **Subir desde tu ordenador** — cualquier archivo de imagen.
  - **Quitar foto / Quitar banner** — solo se muestra una vez guardada la imagen de la pestaña activa; pide confirmación y luego borra el archivo auxiliar (sidecar).

  Cada tarjeta de resultado de búsqueda lleva una insignia de dónde vino. Elegir una la descarga y la guarda al instante. La tarjeta cuya imagen es la guardada actualmente se marca con un borde verde y una marca de verificación, en las pestañas Perfil y Banner por separado — así ves de un vistazo cuál de los candidatos estás usando. Una foto que subiste, o una guardada antes de que Downtify empezara a recordarlo, no tiene tarjeta que marcar.
- **Bio** — un cuadro de texto simple con la biografía guardada actualmente (en blanco si no hay), para escribirla o editarla tú. Guardar sobrescribe directamente el texto actual. Un botón ⚡ **Obtener bio de Streams** sobre el cuadro puede rellenarlo con datos de Apple Music/Deezer en lugar de escribirlo a mano — consulta [Obtener una biografía automáticamente](#fetching-a-bio-automatically) más abajo.
- **Redes sociales** — enlaces de Twitter/X, Instagram, Facebook, YouTube y sitio web, editables directamente. Guardar siempre sustituye los cinco campos por lo que tiene el formulario, incluso un campo que dejes en blanco. Obtener una biografía nunca toca un enlace que hayas rellenado: los enlaces sociales de Deezer solo rellenan campos aún vacíos (Deezer no conoce todas las redes, así que completa el resto a mano y se queda así).

## La primera vez que abres un artista nuevo

Abrir la página de un artista de la Biblioteca siembra su perfil automáticamente, pero solo si aún no se ha guardado nada para él — cada visita después de la primera es una operación nula rápida, así que esto nunca se repite ni ralentiza nada una vez ejecutado.

- **Foto y banner** — de Spotify (consulta [Spotify](#spotify) más abajo), recurriendo a una coincidencia exacta de nombre en YouTube Music cuando Spotify no tiene nada. Solo cuando has activado **Obtener fotos de artista automáticamente** y/o **Obtener banners de artista automáticamente** en Ajustes (ambos desactivados por defecto, y cada uno es independiente); el diálogo de edición siempre puede definir cualquiera de los dos a mano.
- **Bio, origen, año de formación, género, indicador de grupo, color del banner, enlaces sociales, artistas relacionados e ids de plataformas** — obtenidos de Apple Music y Deezer como describe [Obtener una biografía automáticamente](#fetching-a-bio-automatically) más abajo.

Si Apple Music o Deezer **falla** mientras esto se ejecuta (inalcanzable, o superado su límite de peticiones), no se guarda nada — ni la bio ni una foto — y la página simplemente no muestra perfil aún, así que la siguiente visita lo intenta de nuevo. Solo cuenta como respuesta que un servicio conteste que no conoce al artista: el perfil se hace entonces con lo que tuviera el otro. La parte de Spotify (los artistas relacionados) nunca impide que se haga un perfil.

## Cuando termina una descarga

La misma siembra se ejecuta en segundo plano cuando termina de descargarse una canción de un artista — la hayas iniciado en la app o un barrido del [Monitor de playlists](playlist-monitor.md) — si ese artista aún no tiene perfil, así que los artistas que descargas están listos antes de que abras su página. Nunca ralentiza la descarga: el artista se pone en cola y se rellena unos segundos después, dos artistas a la vez, y uno que ya está en cola no se vuelve a poner por muchas canciones suyas que lleguen (una playlist de cincuenta canciones de un artista lo siembra una vez). Las canciones que ya estaban en tu biblioteca no se descargan de nuevo y no inician nada.

- **Qué artista** — aquel bajo el que se archiva el archivo: el artista del álbum, si no el primer artista acreditado. `Various Artists` se omite.
- **Idioma** — la bio y el género llegan en el idioma de la interfaz web, que la página mantiene en el servidor (consulta [Internacionalización](internationalization.md)); hasta que una página se lo haya dicho, en inglés.
- **Foto y banner** — solo según permitan **Obtener fotos de artista automáticamente** / **Obtener banners de artista automáticamente**, leídos en ese momento, así que cambiar un ajuste se aplica ya a la siguiente canción.
- **Top songs** — no se hacen así; esperan a la página del artista (consulta [Top songs](top-songs.md)).

Si no se pudo encontrar nada en ningún sitio para un artista, esto igualmente solo se ejecuta una vez — no reintenta en cada visita posterior. Usa el diálogo de edición para elegir una foto/banner a mano o probar de nuevo el botón de obtener en cualquier momento después.

## La pestaña Enlaces

Un artista con al menos un enlace guardado obtiene una pestaña **Enlaces**, justo antes de **Bio** (que sigue siendo la última pestaña), con un contador de cuántos. Los lista como tarjetas, en cualquier pantalla y tenga o no banner el artista: primero **Plataformas de streaming**, luego **Redes sociales**. Cada tarjeta muestra el nombre y la dirección del sitio y lo abre en una pestaña nueva. Solo se lista lo que realmente está guardado, y un artista sin enlaces no tiene pestaña Enlaces (`?tab=links` para él abre la primera pestaña).

- **Plataformas de streaming** — Spotify, YouTube Music, Deezer y Apple Music, construidas a partir del `platforms_id` del perfil: cada id guardado convertido en un enlace (p. ej. un id de Deezer guardado se convierte en un enlace a la página de ese artista en Deezer). Los ids se resuelven todos automáticamente la primera vez que se obtiene una bio, por coincidencia exacta de nombre en cada plataforma (el de Spotify sale de una de las propias canciones del artista en Spotify cuando la hay, lo cual no puede elegir a un homónimo). También puedes añadir o corregir uno a mano en el JSON del perfil del artista (ver abajo).
- **Redes sociales** — Twitter/X, Instagram, Facebook, YouTube y sitio web: una tarjeta por cada campo no vacío de la pestaña Redes sociales de arriba. Solo se abren direcciones web: a un enlace escrito sin `https://` se le añade, y cualquier cosa con otro tipo de dirección (una `javascript:`, por ejemplo) se ignora.

## Spotify

Spotify nunca aparece como fuente de búsqueda de texto libre, pero tanto el selector como la siembra automática de la primera visita (ver arriba) aún encuentran allí al artista. Primero comprueban algunas de las propias canciones ya descargadas del artista: si una se descargó de Spotify, Downtify ya conoce el id de esa canción en Spotify y resuelve la imagen directamente — la ruta más fiable, ya que no puede caer en otro artista con el mismo nombre. Cuando ninguna canción vino de Spotify (digamos que se descargaron de YouTube), se busca al artista por nombre exacto (sin distinguir mayúsculas — una coincidencia aproximada nunca se usa). En el selector, este candidato aparece primero, etiquetado **Spotify**.

La búsqueda por nombre usa el cuadro de búsqueda del propio reproductor web de Spotify, así que depende de un identificador interno que Spotify puede cambiar; si eso ocurre, Downtify recurre a YouTube Music para la foto/banner y deja vacío el id de Spotify, en lugar de fallar.

La foto y el banner son imágenes realmente distintas en Spotify, resueltas de formas distintas: la foto cuadrada sale de la página de embed pública del artista, mientras que el banner ancho sale de los datos de la propia página del artista de Spotify (que el embed no expone en absoluto). No todo artista tiene un banner definido — cuando no lo tiene, no se ofrece ningún candidato de Spotify para el selector de banner, en lugar de recurrir a la foto cuadrada.

Un artista sin canciones procedentes de Spotify simplemente no obtiene ningún candidato de Spotify — busca en YouTube Music/Deezer, pega un enlace o sube una imagen.

## Obtener una biografía automáticamente

Bajo la cabecera, la página del artista muestra una biografía corta, de solo lectura — vacía hasta que se guarde una. Para rellenarla, abre la pestaña **Bio** del diálogo de edición y haz clic en **Obtener de Apple Music** o **Obtener de Deezer** sobre el cuadro de texto (consulta [Elegir la fuente](#choosing-the-source)), que carga la bio de ese servicio en el cuadro para que la revises y guardes. La siembra automática de la primera visita, que guarda por su cuenta, busca al artista en Apple Music por coincidencia exacta de nombre (usando la misma búsqueda por nombre que usa la propia app Música de Apple) y obtiene su bio, origen, año de formación, género, indicador de grupo y color de acento del banner — el texto (bio y género) en el idioma actual de tu interfaz — y guarda el resultado. El género (Apple Music da uno por artista, p. ej. «Hard rock») se muestra como una pequeña píldora en la parte superior de la pestaña Bio de la página del artista, junto al origen y al año de formación. Apple Music indica si el artista es un grupo: para un grupo esa fecha se lee «Formado en 1995», y para un artista en solitario — cuya fecha suele ser de nacimiento — «Nacido el 27 de septiembre de 1984» (traducido a todos los idiomas de la interfaz; un artista cuyo indicador de grupo no se conoce se queda en «Formado en»). La fecha en sí se muestra tal como la dio Apple Music, así que conserva el idioma de la obtención. Si Apple Music no tiene coincidencia exacta, o la tiene pero sin texto de bio en tu idioma, se prueba Deezer a continuación como fuente secundaria de bio — también aporta enlaces sociales y nombres de artistas relacionados de «a los fans también les gusta» (los artistas relacionados se guardan en el archivo de perfil del artista pero aún no se muestran en ningún sitio, reservados para una futura incorporación), rellenando también la pestaña Redes sociales. Solo si ninguna de las dos fuentes tiene nada ves un error en lugar de una bio adivinada/errónea.

Las biografías editoriales de Apple Music no están escritas para todos los artistas en todos los idiomas — cuando falta un idioma para un artista concreto, se usa la bio de Deezer (si la tiene), mientras que origen/año de formación/indicador de grupo siguen viniendo de Apple Music, ya que esos datos no son texto traducido (el género es siempre solo de Apple Music, así que queda vacío cuando Apple no tiene coincidencia). Unos pocos idiomas (el búlgaro, en el momento de escribir esto) no los ofrece Apple Music en absoluto y siempre recurren a su bio en el idioma predeterminado.

Una bio se guarda en el JSON del artista como texto plano — sin etiquetas HTML ni caracteres de viñeta: una línea en blanco separa los párrafos, y cada viñeta `•` de una bio de Apple Music (que Apple separa con un único salto de línea) se convierte en un párrafo propio. Las bios en HTML de Deezer se aplanan del mismo modo (cada párrafo pasa a ser uno separado por línea en blanco, cualquier otra etiqueta se descarta). La página del artista muestra cada párrafo por separado y conserva los saltos de línea simples dentro de él, y el cuadro de texto de la pestaña Bio edita exactamente ese texto.

Volver a obtener así solo se ejecuta cuando haces clic en el botón — no sobrescribe nada por su cuenta tras la siembra automática de la primera visita descrita arriba. Solo la primera vez (sea la siembra automática o un clic manual) necesita buscar por nombre: los ids de artista de Apple Music y Deezer resueltos quedan en caché en el archivo de perfil del artista después, así que obtener de nuevo solo relee directamente los mismos artistas.

Para borrar una bio guardada, abre la pestaña Bio, vacía el cuadro de texto y Guarda — origen, año de formación, género, indicador de grupo, enlaces sociales, artistas relacionados y los ids de plataformas en caché quedan intactos.

## Elegir la fuente

La pestaña Bio tiene dos enlaces sobre el cuadro de texto, para que elijas qué biografía se lee mejor:

- **Obtener de Apple Music** — carga la bio editorial de Apple Music en el cuadro de texto. Si Apple Music no tiene ninguna para este artista en tu idioma, obtienes un error en lugar de un sustituto.
- **Obtener de Deezer** — carga la bio de Deezer, incluso cuando Apple Music tiene una. Si Deezer no tiene ninguna, obtienes un error.

Hacer clic en un enlace **solo rellena el cuadro de texto** — no se guarda nada hasta que pulsas **Guardar**, así que puedes leerla, editarla o probar primero el otro servicio, y cerrar el diálogo sin guardar deja la bio actual como estaba. Solo se carga el texto de la bio: el origen, el año de formación, el género, los enlaces sociales, los artistas relacionados y los ids de plataformas no los tocan estos enlaces (la siembra automática de la primera visita es lo que los rellena). La siembra no te pregunta qué servicio: usa la bio de Apple Music y recurre a la de Deezer solo cuando Apple Music no tiene ninguna.

## Dónde van los archivos

```
<downloads>/.metadata/ArtistImage/<Artist>.jpg
<downloads>/.metadata/ArtistBannerImage/<Artist>.banner.jpg
<downloads>/.metadata/ArtistData/<Artist>.json
<downloads>/.metadata/ArtistTopSongs/<Artist>.topsongs.json
```

Un archivo por artista, con su nombre (saneado igual que los nombres de archivo de las canciones) — sin registro en base de datos, así que la presencia del archivo en disco es lo que comprueba la página del artista. Guardar una foto/banner nuevo sobrescribe el anterior (la interfaz web evita que se siga mostrando su copia de la antigua: la URL de cada imagen guardada lleva la fecha de modificación del archivo, así que una foto sustituida se vuelve a obtener mientras una intacta sigue en caché), y `ArtistData/<Artist>.json` guarda los datos de bio/redes sociales/artistas relacionados/ids de plataformas descritos arriba, además de, en `current_cover` y `current_cover_banner`, cuál es la imagen de la foto/banner actual: la ruta de la URL desde la que se descargó (sin host ni query, para que la misma imagen de otra dirección de CDN siga coincidiendo), o `upload` para una que subiste. Es con lo que el diálogo de edición compara cada candidato para marcar el que está en uso. Son archivos normales bajo tu carpeta de descargas, así que servicios como Navidrome pueden leerlos directamente si los apuntas a la misma ubicación.

Los nombres de artistas se comparan como los guarda el disco: Downtify archiva `AC/DC` como `ACDC`, porque un nombre de archivo no puede contener `/`, y una canción sin etiqueta de artista toma su artista de ese nombre de archivo — así que el mismo artista puede aparecer como `AC/DC` o `ACDC`. Toda búsqueda por nombre (Spotify, Deezer, YouTube Music y Apple Music) ignora mayúsculas y los caracteres que un nombre de archivo no admite, así que ambas grafías encuentran al mismo artista, y ambas comparten los mismos archivos de arriba. Un nombre que difiere en cualquier otra cosa — `AC/DC Tribute`, por ejemplo — sigue siendo otro artista y nunca coincide.

`platforms_id` reconoce las claves `spotify`, `youtubemusic`, `deezer` y `applemusic`, todas resueltas automáticamente — la de Spotify a partir de una de las propias canciones del artista en Spotify o, si no, por nombre exacto; las demás por nombre exacto. Obtener la bio también rellena un id de Spotify que falte, así que un artista abierto antes de que esto existiera obtiene su icono de Spotify tras una obtención. Un id ya guardado nunca se sustituye, y aún puedes editar el archivo JSON directamente para definir uno a mano.

## Fuera de alcance

Elegir aquí una foto/banner nunca toca el pipeline de descarga — no tiene efecto sobre lo que se incrusta en las etiquetas de tus propios archivos de audio, y descargar una canción nunca obtiene una imagen de artista automáticamente.

La pestaña *Relacionados* muestra una foto también para artistas que no tienes, y lo mismo hacen la cuadrícula de *Artistas* de la Biblioteca, la página del propio artista, la pestaña *Artistas* del Monitor (el artista que estás vigilando, en la lista y en su diálogo de edición) y los artistas de [Descubrir](discover.md) y del [Finder](finder.md) — donde la página ya tiene la imagen del artista en Deezer, así que no hace falta buscar por nombre, y en su lugar se muestra una foto que hayas guardado para el artista — para todo artista para el que no has elegido una foto (la Biblioteca y la página del propio artista usan una de las portadas de canciones del artista cuando Deezer no tiene ninguna; el Monitor no tiene canción, así que muestra las iniciales) - solo una real: un artista para el que Deezer no tiene foto (sirve una imagen de relleno genérica) obtiene la inicial de siempre - pero es solo para mostrar: el servidor retransmite la imagen de Deezer a tu navegador (que la guarda en caché tres horas) sin guardarla, y nunca se convierte en la foto o banner de un artista. Solo se conservan las respuestas reales: si no se puede contactar con Deezer o has superado su límite de peticiones en ese momento, el mosaico muestra la inicial (o la portada de la canción) por ahora y no se recuerda nada, así que la foto aparece la próxima vez que abras la página. Las fotos solo se escriben en disco para artistas para los que tú mismo definiste una, o cuya foto/banner se guardó en la primera visita como se ha descrito arriba (cuando los Ajustes lo permiten). Consulta [`GET /api/artists/photo-proxy`](../api-reference.md#get-apiartistsphoto-proxy).
