---
icon: lucide/download
---

# Installation

Le moyen le plus rapide de lancer Downtify est une simple commande `docker run`. Aucun Python, Node.js ni autre dépendance système n’est nécessaire sur l’hôte — tout est inclus dans l’image.

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) installé et en cours d’exécution

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

Remplacez `/path/to/music` par le répertoire où vous voulez enregistrer votre musique.

Une fois le conteneur démarré, ouvrez **[http://localhost:8000](http://localhost:8000)** dans votre navigateur.

## Volumes

| Volume | Rôle |
|--------|---------|
| `/downloads` | Fichiers audio téléchargés |
| `/data` | Base de données de l’application et réglages persistants |

Les deux volumes persistent d’un redémarrage et d’une mise à jour du conteneur à l’autre. Le volume `/downloads` peut être n’importe quel répertoire de votre machine hôte ou un volume Docker nommé.

## Port personnalisé

Pour exposer Downtify sur un autre port de l’hôte, changez la partie gauche de `-p` :

```bash
docker run -d \
  --name downtify \
  -p 9090:8000 \           # hôte:conteneur
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  ghcr.io/henriquesebastiao/downtify
```

Ouvrez ensuite **[http://localhost:9090](http://localhost:9090)**.

## Mise à jour

Récupérez la dernière image et recréez le conteneur :

```bash
docker pull ghcr.io/henriquesebastiao/downtify
docker stop downtify && docker rm downtify
docker run -d --name downtify -p 8000:8000 \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Votre musique et vos réglages sont conservés dans les volumes.

## Et ensuite ?

- **[Docker Compose](docker-compose.md)** — moyen plus simple de gérer le conteneur sur le long terme
- **[Variables d’environnement](environment-variables.md)** — réglez le comportement anti-bot et d’autres options avancées
- **[Réglages de téléchargement](../features/download-settings.md)** — choisissez votre format et votre débit
