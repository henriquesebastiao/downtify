---
icon: lucide/download
---

# Instalación

La forma más rápida de ejecutar Downtify es con un único comando `docker run`. No hacen falta Python, Node.js ni otras dependencias del sistema en el host — todo viene dentro de la imagen.

## Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) instalado y en ejecución

## Docker run

```bash
docker run -d \
  --name downtify \
  -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Sustituye `/path/to/music` por el directorio donde quieras guardar tu música.

Cuando el contenedor arranque, abre **[http://localhost:8000](http://localhost:8000)** en tu navegador.

## Volúmenes

| Volumen | Finalidad |
|--------|---------|
| `/downloads` | Archivos de audio descargados |
| `/data` | Base de datos de la aplicación y ajustes persistentes |

Ambos volúmenes persisten entre reinicios y actualizaciones del contenedor. El volumen `/downloads` puede ser cualquier directorio de tu máquina anfitriona o un volumen de Docker con nombre.

## Puerto personalizado

Para exponer Downtify en otro puerto del host, cambia el lado izquierdo de `-p`:

```bash
docker run -d \
  --name downtify \
  -p 9090:8000 \           # host:contenedor
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Después abre **[http://localhost:9090](http://localhost:9090)**.

## Actualización

Descarga la última imagen y vuelve a crear el contenedor:

```bash
docker pull ghcr.io/henriquesebastiao/downtify
docker stop downtify && docker rm downtify
docker run -d --name downtify -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Tu música y tus ajustes se conservan en los volúmenes.

## ¿Y ahora qué?

- **[Docker Compose](docker-compose.md)** — forma más sencilla de gestionar el contenedor a largo plazo
- **[Variables de entorno](environment-variables.md)** — ajusta el comportamiento anti-bot y otras opciones avanzadas
- **[Ajustes de descarga](../features/download-settings.md)** — elige el formato y la tasa de bits
