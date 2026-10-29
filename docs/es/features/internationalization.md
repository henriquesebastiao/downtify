---
icon: lucide/languages
---

# Internacionalización

Downtify se traduce en dos lugares independientes: la **app** (su interfaz) y esta **documentación**. El idioma por defecto de ambos es el **inglés**, con otros nueve idiomas incluidos de serie.

## Cambiar de idioma

### La app

Ve a **Ajustes → Idioma** y elige tu idioma preferido. La elección se guarda en el `localStorage` del navegador y se aplica al instante sin recargar la página. La página también se lo comunica al servidor (la entrada `ui_language` de `settings.json`, consulta [`POST /api/settings/update`](../api-reference.md#post-apisettingsupdate)), en cada carga y cada vez que lo cambias, para que el trabajo que se ejecuta sin un navegador conozca tu idioma - la biografía de un artista, obtenida en segundo plano cuando termina de descargarse una de sus canciones, llega en él (consulta [Cuando termina una descarga](artist-images.md#when-a-download-finishes)). No tienes que hacer nada: si elegiste un idioma antes de que esto existiera, se recoge la próxima vez que abras Downtify. Con varios navegadores configurados en idiomas distintos, gana el último que cargó o lo cambió.

### La documentación

La documentación se abre en el idioma que prefiere tu navegador, cuando está traducida a él, y en inglés en caso contrario. El **botón del globo** a la derecha de la barra superior cambia el idioma en cualquier momento y te mantiene en la misma página (y sección). Tu elección se recuerda en el navegador y, a partir de entonces, prevalece sobre el idioma del navegador hasta que elijas otro.

Una página que aún no está traducida muestra un aviso y el texto en inglés, así que todos los idiomas tienen siempre todas las páginas.

## Idiomas disponibles

| Código | Idioma | App | Docs |
| ------- | ------------------ | --- | ---- |
| `en` | English (predeterminado) | ✓ | ✓ |
| `es` | Español | ✓ | ✓ |
| `pt-BR` | Português (Brasil) | ✓ | ✓ |
| `fr` | Français | ✓ | ✓ |
| `tr` | Türkçe | ✓ | ✓ |
| `el` | Ελληνικά | ✓ | ✓ |
| `hu` | Magyar | ✓ | ✓ |
| `bg` | Български | ✓ | ✓ |
| `de` | Deutsch | ✓ | ✓ |
| `ko` | 한국어 | ✓ | ✓ |

Las páginas de referencia pensadas para desarrolladores — la [referencia de la API](../api-reference.md), el [contrato del cliente móvil](../mobile-client-contract.md) y el changelog — se quedan en inglés en todos los idiomas.

## Contribuir con una traducción

Puedes traducir la app, la documentación o ambas. Son trabajos separados con archivos separados, así que un pull request puede contener uno de los dos — o un idioma puede añadirse primero a uno y después al otro.

| Traduces | Dónde están los archivos | Está listo cuando |
| ------------- | ------------------- | --------- |
| **Solo la app** | `frontend/src/i18n/locales/<code>.js` | el idioma aparece en **Ajustes → Idioma** |
| **Solo la documentación** | `docs/.vitepress/locales/<code>.mjs` y las páginas Markdown en `docs/<code>/` | el idioma aparece en el menú del globo de la documentación |
| **Ambas** | todo lo anterior | ambas |

Un idioma no tiene que existir en la app para añadirse a la documentación, ni al revés.

## Traducir la app

Añadir una traducción a la app es un proceso de tres pasos:

### 1. Copia el archivo de idioma en inglés

Los archivos de idioma están en `frontend/src/i18n/locales/`. Cada archivo exporta un único objeto cuyas claves siguen la estructura de `en.js`. Usa una [etiqueta de idioma IETF](https://en.wikipedia.org/wiki/IETF_language_tag) como nombre del archivo.

```bash
cp frontend/src/i18n/locales/en.js frontend/src/i18n/locales/it.js
```

### 2. Traduce los valores

Deja sin cambios las claves, los marcadores de posición (p. ej. `{count}`, `{name}`, `{file}`) y la forma general — solo deben cambiar los textos del lado derecho. Define `language.name` como el nombre **nativo** del idioma (`"Français"`, `"Deutsch"`, …) — es la etiqueta que se muestra en el selector de idioma.

### 3. Registra el idioma

Añade un import y una entrada a `AVAILABLE_LOCALES` en `frontend/src/i18n/index.js`:

```js
import it from './locales/it.js'

export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English', messages: en },
  { code: 'es', name: 'Español', messages: es },
  // …
  { code: 'it', name: 'Italiano', messages: it }, // new
]
```

Recompila el frontend y tu idioma aparecerá automáticamente en **Ajustes → Idioma**:

```bash
cd frontend && npm run build
```

### Consejos para traducir la app

- Las claves que faltan vuelven al inglés, así que las traducciones parciales funcionan bien — envía un PR con lo que tengas.
- Los textos que dependen de un número son objetos con formas plurales, p. ej. `tracks: { one: '{count} track', other: '{count} tracks' }`. La forma se elige con [`Intl.PluralRules`](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Intl/PluralRules) del navegador para tu idioma, así que añade las formas que use tu idioma (`zero`, `one`, `two`, `few`, `many`, `other`) — `other` es obligatoria. Los números se formatean automáticamente para el idioma.
- Los marcadores como `{count}` o `{file}` deben dejarse sin cambios; se sustituyen en tiempo de ejecución.
- Mantén los textos concisos — la interfaz está muy ajustada y las traducciones muy largas pueden romperse de forma rara.
- Tras traducir, ejecuta `npm run dev` desde `frontend/` y recorre todas las páginas en tu idioma para detectar lo que se desborde o suene raro en contexto.

## Traducir la documentación

El inglés es la fuente: está en `docs/`. Cada uno de los demás idiomas tiene una carpeta con el nombre de su código (`docs/pt-BR/`) con **los mismos nombres de archivo** que el inglés, más un archivo para los textos del propio sitio (`docs/.vitepress/locales/pt-BR.mjs`: los títulos de la barra lateral, el cuadro de búsqueda, el pie, las etiquetas de los avisos). Una página que aún no está traducida es un pequeño borrador que muestra un aviso e incluye la página en inglés.

### Traducir una página de un idioma existente

Desde `docs/`:

```bash
npm install
npm run i18n -- status pt-BR           # what is translated, what is English-only, what is out of date
npm run i18n -- start pt-BR features/users.md
```

`start` reemplaza el borrador `docs/pt-BR/features/users.md` por una copia de la página en inglés. Tradúcela en su sitio y luego compruébala:

```bash
npm test             # the translated pages must keep the English page's structure
npm run dev          # read it in the browser, in your language
```

Abre un pull request cuando la página se lea bien; el trabajo parcial también es bienvenido — las páginas que no has tocado simplemente siguen en inglés.

### Añadir un idioma a la documentación

1. Copia `docs/.vitepress/locales/en.mjs` a `docs/.vitepress/locales/<code>.mjs` y tradúcelo: el `name` nativo, los textos del sitio (`ui`), las etiquetas de los avisos (`containers`) y los títulos de la barra lateral (`nav`).
2. Regístralo en `docs/.vitepress/locales/index.mjs`.
3. Crea las páginas, como borradores solo en inglés: `npm run i18n -- stubs <code>`.
4. Traduce las páginas de una en una con `npm run i18n -- start <code> <page>`.

El idioma aparece en el menú del globo y en la detección del idioma del navegador en cuanto se registra.

### Qué conservar y qué traducir

- **Traduce** el texto, los encabezados, las celdas de las tablas, los títulos de los avisos y los valores `title`/`text` del front matter de la página de inicio.
- **Conserva tal cual** los bloques de código, el `código` en línea, las URL, las variables de entorno, las rutas y nombres de campo de la API, los nombres de archivos y carpetas, y las claves del front matter y los valores de `icon:` y `link:`. Traducir un comentario dentro de un bloque de código está bien.
- **Enlaces**: conserva exactamente los enlaces relativos `.md` de la página en inglés (`[Letras](lyrics.md#sidecar-lrc-file)`). Un enlace a una página que solo está en inglés sigue funcionando. En la página de inicio, los enlaces se escriben con el prefijo del idioma (`/pt-BR/features/player/`).
- **Encabezados**: conserva los mismos encabezados, en el mismo orden y en los mismos niveles. Los enlaces a una sección (`#sidecar-lrc-file`) siguen funcionando en todos los idiomas porque la página traducida reutiliza los ids de encabezado del inglés — nunca escribes ni traduces un id.
- **Nombres de botones y ajustes**: la app tiene su propia traducción de cada etiqueta. Úsala, en negrita, para que la página coincida con lo que el lector ve en pantalla: busca la etiqueta en `frontend/src/i18n/locales/<code>.js`. Si la app aún no está traducida a ese idioma, conserva la etiqueta en inglés.
- **Avisos** (`::: tip Título`): conserva el tipo (`info`, `tip`, `warning`, `danger`) y traduce el título. Un aviso sin título lleva como etiqueta la palabra de `containers` en el archivo del idioma.
- **Tono**: escribe para el lector de ese idioma — las páginas son guías, no versiones palabra por palabra.

### Mantener las traducciones al día

Cuando cambia una página en inglés, sus traducciones no tienen que cambiar en el mismo pull request: una página traducida sigue funcionando, y `npm run i18n -- status <code>` lista las páginas cuya fuente en inglés cambió después de traducirse. Actualizarlas es una buena primera contribución.

Las pruebas (`npm test` en `docs/`) comprueban que todos los idiomas tienen todas las páginas y todos los textos del sitio, y que una página traducida sigue teniendo los encabezados, bloques de código, tablas, avisos y enlaces de la página en inglés.
