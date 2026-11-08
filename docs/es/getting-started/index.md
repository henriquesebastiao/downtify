---
icon: lucide/play
---

# Primeros pasos

Downtify es una aplicación web autoalojada que descarga música de Spotify — sin claves de API, sin cuenta, sin necesidad de una suscripción Premium. Todo funciona dentro de un único contenedor de Docker.

## Qué necesitas

- **Docker** (o Docker Compose) — el único requisito en la máquina anfitriona
- Una máquina con acceso a internet
- Un volumen o directorio donde guardar tu música

## Elige cómo instalarlo

<div class="doc-cards">

- <DocIcon name="docker" /> **Docker run**

  La forma más rápida de empezar. Un comando y listo en menos de un minuto.

  [Instalación →](installation.md)

- <DocIcon name="file-code" /> **Docker Compose**

  Recomendado para instalaciones permanentes. Más fácil de actualizar y de gestionar.

  [Docker Compose →](docker-compose.md)

- <DocIcon name="house" /> **Instalación con un clic**

  ¿Usas Umbrel, CasaOS o HomeDock OS? Instálalo directamente desde sus tiendas de aplicaciones.

  [Instalación con un clic →](one-click.md)

</div>

## Siguientes pasos

Cuando Downtify esté funcionando, abre [http://localhost:8000](http://localhost:8000) en tu navegador. Pega la URL de una canción, un álbum o una playlist de Spotify en la barra de búsqueda y pulsa **Descargar**.

Explora el resto de la documentación para conocer los [ajustes de descarga](../features/download-settings.md), el [monitor de playlists](../features/playlist-monitor.md), el [reproductor integrado](../features/player.md) y mucho más.
