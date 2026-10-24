---
icon: lucide/hand-heart
---

# Contribuir

Las contribuciones son bienvenidas — informes de errores, solicitudes de funciones, código y traducciones ayudan. Las traducciones pueden ser de la app, de esta documentación o de ambas: consulta [Traducir](#translating).

## Issues y solicitudes de funciones

Usa el [rastreador de issues de GitHub](https://github.com/henriquesebastiao/downtify/issues). Antes de abrir una issue nueva, busca entre las existentes para evitar duplicados.

En los informes de errores, incluye:

- Versión de Downtify
- Cómo lo instalaste (Docker run, Docker Compose, Umbrel, …)
- Pasos para reproducirlo
- Lo que esperabas frente a lo que ocurrió
- Cualquier log relevante

## Entorno de desarrollo

### Requisitos previos

- Python 3.15+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (gestor de paquetes de Python)
- ffmpeg (debe estar en el `PATH`)

### Clonar e instalar

```bash
git clone https://github.com/henriquesebastiao/downtify.git
cd downtify

# Python dependencies
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Ejecutar en modo de desarrollo

```bash
# Terminal 1 — backend
uv run python main.py

# Terminal 2 — frontend dev server (hot reload)
cd frontend && npm run dev
```

El servidor de desarrollo del frontend redirige las peticiones de API al backend, así que solo necesitas abrir la URL de Vite (normalmente `http://localhost:5173`).

### Ejecutar las pruebas

```bash
uv run pytest
```

### Compilar el frontend para producción

```bash
cd frontend && npm run build
```

Los archivos compilados quedan en `frontend/dist/` y los sirve el backend.

### Trabajar en la documentación

La documentación son archivos Markdown en `docs/`, convertidos en un sitio estático con [VitePress](https://vitepress.dev/) y un tema personalizado (en `docs/.vitepress/`) que comparte sus tokens de diseño con la app web.

```bash
make doc         # dev server with hot reload
make doc-build   # production build into docs/.vitepress/dist
```

Enlaza a otras páginas con rutas `.md` relativas (`[Letras](lyrics.md)`) y usa `::: tip Título` … `:::` para los avisos (`info`, `tip`, `warning`, `danger`). Las páginas nuevas van en la barra lateral en `docs/.vitepress/nav.mjs` (con su título en el archivo de cada idioma en `docs/.vitepress/locales/`). La compilación falla con enlaces rotos y con enlaces a encabezados que no existen.

Las páginas en inglés de `docs/` son la fuente; cada uno de los demás idiomas las refleja en su propia carpeta (`docs/pt-BR/…`). No tienes que actualizar las traducciones al cambiar una página en inglés — los traductores les dan seguimiento —, pero ejecuta `npm test` en `docs/`: una página nueva necesita un borrador solo en inglés en cada idioma (`npm run i18n -- stubs`), y las pruebas avisan si falta.

## Estructura del proyecto

```
downtify/
├── downtify/          # Python backend
│   ├── api.py         # FastAPI router
│   ├── downloader.py  # yt-dlp + mutagen pipeline
│   ├── spotify.py     # Spotify embed scraping
│   ├── providers.py   # YouTube Music search
│   ├── monitor.py     # Playlist monitor
│   ├── lyrics.py      # lrclib integration
│   └── m3u.py         # M3U generation
├── frontend/          # Vue 3 + Vite frontend
│   └── src/
│       └── i18n/      # Translation files
├── docs/              # This documentation (Markdown + VitePress site)
│   ├── <page>.md      # English, the source
│   ├── pt-BR/ …       # One folder per translated language, same file names
│   └── .vitepress/
│       └── locales/   # Each language's site text and sidebar titles
├── main.py            # Entry point
├── Dockerfile
└── docker-compose.yml
```

## Traducir

Downtify tiene dos cosas que traducir, y puedes tomar cualquiera — o las dos:

| Traduces | Dónde | Guía |
|---------------|-------|-------|
| **La app** (su interfaz) | `frontend/src/i18n/locales/<code>.js` | [Traducir la app](features/internationalization.md#translating-the-app) |
| **La documentación** (estas páginas) | `docs/<code>/` y `docs/.vitepress/locales/<code>.mjs` | [Traducir la documentación](features/internationalization.md#translating-the-documentation) |

Son independientes: un idioma puede estar en una y aún no en la otra, y un pull request puede contener solo la traducción de la app, solo la documentación o ambas. El trabajo parcial es bienvenido — los textos sin traducir vuelven al inglés en la app, y las páginas sin traducir siguen en inglés en la documentación.

Inicio rápido para la documentación, desde `docs/`:

```bash
npm run i18n -- status pt-BR                    # coverage of a language
npm run i18n -- start pt-BR features/users.md   # copy an English page to translate
npm test                                        # check the structure of what you translated
```

Consulta [Internacionalización](features/internationalization.md) para los detalles: qué conservar tal cual, cómo añadir un idioma nuevo entero y cómo traducir los nombres de los botones para que coincidan con los de la app.

## Pull requests

- Haz un fork del repositorio y crea una rama desde `main`
- Mantén los cambios acotados — una función o corrección por PR
- Añade o actualiza pruebas al tocar la lógica del backend
- Ejecuta `uv run pytest` antes de enviar
- Abre el PR contra `main`

Si Downtify te ha sido útil, considera dejar una estrella en GitHub — ayuda a que el proyecto crezca.
