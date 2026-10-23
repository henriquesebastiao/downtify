---
icon: lucide/file-code
---

# Docker Compose

Docker Compose est la méthode recommandée pour exécuter Downtify sur un serveur domestique permanent. Il facilite les mises à jour, les sauvegardes et les changements de configuration.

## Configuration minimale

Créez un fichier `docker-compose.yml` :

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

Démarrez-le :

```bash
docker compose up -d
```

Ouvrez **[http://localhost:8000](http://localhost:8000)**.

## Avec slskd (Soulseek)

Pour utiliser [slskd comme source audio](../features/slskd-navidrome.md), montez aussi le dossier de téléchargements de slskd dans Downtify — le **même dossier de l’hôte** que celui où écrit votre conteneur slskd :

```yaml
services:
  downtify:
    # ...
    volumes:
      - ./downloads:/downloads
      - /path/to/slskd/downloads:/slskd
      - downtify_data:/data
```

Puis, dans **Paramètres → Sources audio → slskd**, activez slskd, saisissez son URL (par ex. `http://slskd:5030` quand les deux conteneurs partagent un réseau Docker) et sa clé d’API, et définissez le dossier de téléchargement sur `/slskd`.

## Dossiers de musique existants

Pour que la Bibliothèque prenne en compte une collection que vous gardez déjà sur l’hôte, [montez-la](../features/external-library.md) de la même façon et saisissez le chemin **du conteneur** dans **Paramètres → Bibliothèque** :

```yaml
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

## Trouver le serveur depuis les applications

Les [applications mobiles](../features/mobile-apps.md#finding-the-server-on-your-network) listent les serveurs Downtify de votre réseau via mDNS. Dans le réseau bridge par défaut de Docker, cette annonce ne quitte jamais Docker, donc les téléphones ne la voient pas. Pour qu’elle apparaisse, exécutez le conteneur sur le réseau de l’hôte — l’association `ports:` ne s’applique alors plus, et Downtify écoute directement sur `DOWNTIFY_PORT` :

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

Sinon, saisissez simplement l’adresse du serveur dans l’application (`http://<IP de l’hôte>:8000`) ; rien d’autre ne dépend de la découverte.

## Port personnalisé

Si le port 8000 est déjà utilisé, associez un autre port de l’hôte et définissez la variable d’environnement `DOWNTIFY_PORT` pour que le conteneur écoute en interne sur le même port :

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

Vous pouvez aussi choisir le port dans **Paramètres → Serveur → Port** au lieu de définir `DOWNTIFY_PORT` (qui, lorsqu’elle est définie, l’emporte sur les Paramètres). Dans le réseau bridge par défaut, changez l’association `ports:` pour le même port et recréez le conteneur — voir [Changer le port](../features/server.md#changing-the-port).

## Avec un DNS personnalisé (recommandé)

Certains fournisseurs d’accès et réseaux d’entreprise bloquent YouTube. Ajouter des résolveurs DNS explicites améliore la fiabilité :

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

## Mise à jour

```bash
docker compose pull
docker compose up -d
```

Votre musique et vos réglages sont conservés dans les volumes.

## Volumes

| Chemin dans le fichier compose | Rôle |
|------------------------------|---------|
| `./downloads:/downloads` | Fichiers audio téléchargés (répertoire local) |
| `downtify_data:/data` | Base de données et réglages de l’application (volume nommé) |

Vous pouvez remplacer le volume nommé par un chemin local (`./data:/data`) si vous préférez le gérer vous-même.
