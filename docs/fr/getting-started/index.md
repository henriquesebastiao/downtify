---
icon: lucide/play
---

# Premiers pas

Downtify est une application web auto-hébergée qui télécharge de la musique depuis Spotify — sans clé d’API, sans compte, sans abonnement Premium. Tout tourne dans un seul conteneur Docker.

## Ce qu’il vous faut

- **Docker** (ou Docker Compose) — la seule exigence sur la machine hôte
- Une machine avec un accès à internet
- Un volume ou un répertoire où enregistrer votre musique

## Choisissez votre installation

<div class="doc-cards">

- <DocIcon name="docker" /> **Docker run**

  Le moyen le plus rapide de démarrer. Une commande, et c’est en ligne en moins d’une minute.

  [Installation →](installation.md)

- <DocIcon name="file-code" /> **Docker Compose**

  Recommandé pour une installation durable. Plus facile à mettre à jour et à gérer.

  [Docker Compose →](docker-compose.md)

- <DocIcon name="house" /> **Installation en un clic**

  Vous utilisez Umbrel, CasaOS ou HomeDock OS ? Installez directement depuis leurs boutiques d’applications.

  [Installation en un clic →](one-click.md)

</div>

## Étapes suivantes

Une fois Downtify lancé, ouvrez [http://localhost:8000](http://localhost:8000) dans votre navigateur. Collez l’URL d’un titre, d’un album ou d’une playlist Spotify dans la barre de recherche et cliquez sur **Télécharger**.

Parcourez le reste de la documentation pour découvrir les [réglages de téléchargement](../features/download-settings.md), la [surveillance de playlists](../features/playlist-monitor.md), le [lecteur intégré](../features/player.md) et bien plus.
