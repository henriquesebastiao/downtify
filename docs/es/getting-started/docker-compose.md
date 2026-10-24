---
icon: lucide/file-code
---

# Docker Compose

Docker Compose es la forma recomendada de ejecutar Downtify en servidores domésticos permanentes. Facilita las actualizaciones, las copias de seguridad y los cambios de configuración.

## Configuración mínima

Crea un archivo `docker-compose.yml`:

```yaml
services:
  downtify:
    container_name: downtify
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped

volumes:
  downtify_data:
```

Arráncalo:

```bash
docker compose up -d
```

Abre **[http://localhost:8000](http://localhost:8000)**.

## Con slskd (Soulseek)

Para usar [slskd como fuente de audio](../features/slskd-navidrome.md), monta también en Downtify la carpeta de descargas de slskd — la **misma carpeta del host** en la que escribe tu contenedor de slskd:

```yaml
services:
  downtify:
    # ...
    volumes:
      - ./downloads:/downloads
      - /path/to/slskd/downloads:/slskd
      - downtify_data:/data
```

Después, en **Ajustes → Fuentes de audio → slskd**, activa slskd, introduce su URL (p. ej., `http://slskd:5030` cuando ambos contenedores comparten una red de Docker) y la clave de API, y establece la carpeta de descargas en `/slskd`.

## Carpetas de música existentes

Para que la Biblioteca reconozca una colección que ya tienes en el host, [móntala](../features/external-library.md) de la misma manera e introduce la ruta **del contenedor** en **Ajustes → Biblioteca**:

```yaml
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

## Encontrar el servidor desde las apps

Las [apps móviles](../features/mobile-apps.md#finding-the-server-on-your-network) listan los servidores Downtify de tu red mediante mDNS. En la red bridge predeterminada de Docker ese anuncio nunca sale de Docker, así que los teléfonos no lo ven. Para que aparezca, ejecuta el contenedor en la red del host — la asignación `ports:` deja de aplicarse y Downtify escucha directamente en `DOWNTIFY_PORT`:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    network_mode: host
    environment:
      - DOWNTIFY_PORT=8000
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped
```

Si no, basta con escribir la dirección del servidor en la app (`http://<IP del host>:8000`); nada más depende del descubrimiento.

## Puerto personalizado

Si el puerto 8000 ya está en uso, asigna otro puerto del host y define la variable de entorno `DOWNTIFY_PORT` para que el contenedor escuche internamente en el mismo puerto:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '9090:30321'
    environment:
      - DOWNTIFY_PORT=30321
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    restart: unless-stopped
```

También puedes elegir el puerto en **Ajustes → Servidor → Puerto** en lugar de definir `DOWNTIFY_PORT` (que, cuando está definida, tiene prioridad sobre Ajustes). En la red bridge predeterminada, cambia la asignación `ports:` al mismo puerto y vuelve a crear el contenedor — consulta [Cambiar el puerto](../features/server.md#changing-the-port).

## Con DNS personalizado (recomendado)

Algunos proveedores de internet y redes corporativas bloquean YouTube. Añadir resolutores DNS explícitos mejora la fiabilidad:

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
    dns:
      - 1.1.1.1
      - 1.0.0.1
    restart: unless-stopped
```

## Actualización

```bash
docker compose pull
docker compose up -d
```

Tu música y tus ajustes se conservan en los volúmenes.

## Volúmenes

| Ruta dentro del archivo compose | Finalidad |
|------------------------------|---------|
| `./downloads:/downloads` | Archivos de audio descargados (directorio local) |
| `downtify_data:/data` | Base de datos y ajustes de la aplicación (volumen con nombre) |

Puedes sustituir el volumen con nombre por una ruta local (`./data:/data`) si prefieres gestionarlo tú mismo.
