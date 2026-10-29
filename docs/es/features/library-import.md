---
icon: lucide/import
---

# Importar biblioteca (CSV)

¿Ya exportaste tu biblioteca de otro servicio? Importa el CSV y pon en cola todas las canciones para descargar de una vez, en lugar de añadirlas una a una.

## Exportadores compatibles

| Herramienta | Notas |
|------|-------|
| [Soundiiz](https://soundiiz.com/) | |
| [TuneMyMusic](https://www.tunemymusic.com/) | |
| [Exportify](https://github.com/watsonbox/exportify) | |

Downtify no fija el esquema exacto de columnas de ninguna herramienta. En su lugar, compara la fila de encabezado del CSV, sin distinguir mayúsculas de minúsculas, con un conjunto de alias conocidos (`Title` / `Track` / `Track Title` / `Track Name` / `Song` / …, `Artist` / `Artists` / `Artist Name` / `Artist Name(s)` / … y `Album` / `Album Name` / `Album Title` / …), de modo que las exportaciones de cualquiera de las tres — o de un CSV hecho a mano con los mismos nombres de columna — funcionan sin renombrar nada.

El título y el artista son obligatorios. El álbum se lee cuando existe y se guarda como el nombre del álbum de la canción (Cola, coincidencia y etiquetas del archivo). Otras columnas que incluyen algunos exportadores (ISRC, un URI de canción de Spotify, duración) se ignoran. Cada fila se resuelve igual que una búsqueda de texto libre, a través de YouTube Music.

## Cómo importar

1. En la página de inicio, haz clic en **Importa un CSV (Soundiiz, Exportify…)**, debajo del cuadro de búsqueda.
2. Elige tu archivo `.csv` exportado.

El archivo se lee por completo en tu navegador y se envía al servidor como texto plano — nunca se sube a ningún otro sitio. Downtify lo analiza, pone en cola todas las filas reconocidas y llegas a la Cola de descargas, donde el progreso llega por WebSocket exactamente igual que en cualquier otra descarga por lotes.

El lote importado recibe el nombre del archivo (su nombre sin `.csv`) y, como cualquier otra descarga de playlist, obtiene un [archivo M3U](m3u-export.md) si ese ajuste está activado.

## Límites y gestión de errores

- Hasta **2000 filas** por archivo. Divide las exportaciones mayores en varios archivos.
- Las filas sin título o sin artista se omiten en silencio. Una columna de álbum ausente o una celda de álbum en blanco no es problema — YouTube Music aún puede completar el álbum más tarde.
- Varios artistas en una celda (separados por `,` o `;`) se separan en una lista.
- Si el encabezado no contiene una columna reconocible de título/artista, toda la importación se rechaza de entrada con un error que nombra las columnas que sí encontró — no se pone nada en cola.

## Evitar límites de peticiones

Importar una biblioteca grande pone en cola muchas búsquedas y descargas de YouTube Music en poco tiempo, lo que facilita que te limiten. Antes de importar un archivo grande, considera reducir **[Descargas simultáneas](download-settings.md#parallel-downloads)** y activar **[Pausa entre descargas](download-settings.md#delay-between-downloads)** en Ajustes.

## API

Consulta [`POST /api/download/csv`](../api-reference.md#post-apidownloadcsv) en la referencia de la API para ver el endpoint subyacente.
