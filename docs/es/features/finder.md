---
icon: lucide/columns-3
---

# Finder

**Finder** es una forma de explorar el catálogo de Deezer antes de descargar. Buscas en Deezer, abres un artista y lo recorres en tres columnas una al lado de otra, como la vista de columnas del Finder de macOS: el artista, su discografía y las canciones de un álbum. No necesita cuenta de Deezer ni clave de API.

## Búsqueda

Abre **Descubrir** en la barra lateral (en el móvil: **Más → Descubrir**): el cuadro de búsqueda del Finder está arriba de la página, con tus búsquedas recientes del Finder a su lado. Buscar sustituye las sugerencias de Descubrir por lo encontrado — canciones, álbumes y artistas, con los filtros **Todo / Canciones / Álbumes / Artistas** como en la página de Búsqueda normal, pero solo de Deezer. Vacía el cuadro (la **×**) o vuelve atrás para ver de nuevo las sugerencias; una búsqueda reciente se repite con un clic, y **Limpiar** las olvida todas. Las búsquedas recientes se guardan solo en este navegador.

**Buscar canciones**, en el menú **⋯** de un artista que sugiere Descubrir, muestra aquí las canciones de ese artista como una búsqueda: se busca en Deezer el nombre del artista y solo se listan las canciones de ese mismo artista — identificadas por su id de Deezer, de modo que un homónimo o una canción que solo se llame así quedan fuera —, hasta las primeras centenas.

- Las **canciones** se reproducen enteras en streaming y se descargan como cualquier resultado de búsqueda. Downtify localiza la canción en YouTube Music (con YouTube como alternativa) por título, artista y duración. Hacer clic en el título de una canción abre su álbum en la vista de columnas, con la canción resaltada.
- Los **álbumes** se abren en su artista, con ese álbum seleccionado. El botón de descarga de la portada pone en cola el álbum entero.
- Los **artistas** abren la vista de columnas en ese artista.

## La vista de columnas

| Columna | Qué muestra |
| --- | --- |
| **Artista** | La foto del artista y el número de álbumes, su biografía en el idioma de la interfaz (desplegable), sus 10 canciones más populares y «Fans también escuchan» (artistas relacionados). |
| **Discografía** | Todos los álbumes, sencillos, EP y recopilaciones, del más reciente al más antiguo, con portada, título, tipo de lanzamiento, año y número de canciones. Los filtros separan por tipo de lanzamiento. |
| **Canciones** | La portada y el título del álbum seleccionado, su artista, año, número de canciones y duración. Un panel de información lista la fecha de lanzamiento, el sello, los géneros, los créditos y el UPC. Debajo están las canciones del álbum: cada una se reproduce entera en streaming hasta que se descarga y después suena desde tu biblioteca, con un botón **Descargar álbum** para ponerlas todas en cola. |

Hacer clic en una canción popular selecciona su álbum y resalta la canción; ambas columnas se desplazan suavemente hasta mostrarse (al instante si el sistema está configurado para reducir el movimiento), y en cuanto las canciones del álbum están en pantalla la canción empieza a sonar entera — en streaming, o la propia canción si ya está en tu biblioteca. Volver a hacer clic mientras suena no la pausa; abrir la página desde un enlace que apunta a una canción no inicia nada. Hacer clic en un artista relacionado abre ese artista, y el botón de retroceso del navegador vuelve al anterior. La barra de ruta sobre las columnas (**Descubrir › artista › álbum**) lleva de vuelta a la búsqueda (o a Descubrir, cuando las columnas no se abrieron desde una) o solo al artista. Lo que está abierto se guarda en la URL, así que sobrevive a una recarga y se puede añadir a marcadores.

En pantallas anchas, arrastra el borde entre dos columnas para ensanchar o estrechar una, o enfócalo y usa las flechas del teclado. Un doble clic restablece los anchos por defecto. El botón de flecha en la parte superior de las columnas de artista y discografía contrae la columna a solo sus imágenes: la foto del artista, las portadas de sus canciones populares y las fotos de los artistas relacionados, o las portadas de los álbumes. Cada imagen sigue funcionando como su fila completa, y su nombre se muestra al pasar el ratón. Los anchos y las columnas contraídas solo duran mientras estás en la página: nunca se guardan, así que recargar o salir del Finder los restablece.

En el móvil, las columnas están una al lado de otra y se desliza entre ellas. Elegir un álbum desliza hasta sus canciones.

::: info Por qué el número de canciones aparece un momento después
El listado de discografía de Deezer no incluye el número de canciones, así que Downtify pide el de cada álbum por separado, unos pocos álbumes a la vez, manteniéndose por debajo del límite de Deezer de 50 peticiones cada 5 segundos. Los números aparecen mientras miras y se recuerdan hasta que Downtify se reinicia. Un álbum cuyo número no pudo obtenerse muestra `…`.
:::

## API

Consulta [`GET /api/finder/search`](../api-reference.md#get-apifindersearch) y los endpoints siguientes en la Referencia de la API.
