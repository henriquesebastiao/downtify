---
icon: lucide/settings
---

# Variables d’environnement

Toutes les variables d’environnement sont facultatives. Downtify fonctionne tout de suite sans aucune d’elles.

## Essentielles

| Variable | Valeur par défaut | Description |
|----------|---------|-------------|
| `DOWNTIFY_PORT` | _(non définie)_ | Port sur lequel le serveur écoute (dans le conteneur). Non définie : le port choisi dans **Paramètres → Serveur → Port**, sinon `8000`. Définie, elle l’emporte et le champ des Paramètres est verrouillé. Modifiez la partie gauche de l’association de ports pour exposer un autre port de l’hôte. Voir [Changer le port](../features/server.md#changing-the-port). |
| `DOWNLOAD_DIR` | `/downloads` | Répertoire où les fichiers audio sont enregistrés. À modifier si vous montez votre bibliothèque à un autre chemin. |
| `HOST` | `0.0.0.0` | Adresse d’écoute du serveur web. |
| `DOWNTIFY_LOG_LEVEL` | `info` | Niveau de journalisation de l’application (`debug`, `info`, `warning`, …). |
| `TZ` | `UTC` | Fuseau horaire local (nom IANA, par ex. `America/Sao_Paulo`), utilisé pour interpréter `DOWNTIFY_MONITOR_SYNC_TIME` ci-dessous. |

## Surveillance de playlists

| Variable | Valeur par défaut | Description |
|----------|---------|-------------|
| `DOWNTIFY_MONITOR_SYNC_TIME` | _(non définie)_ | Heure de la journée (`HH:MM` sur 24 h, dans le fuseau de `TZ` ci-dessus) à laquelle doivent s’exécuter les synchronisations de la [Surveillance de playlists](../features/playlist-monitor.md#choosing-a-daily-sync-time) dont l’intervalle est d’un jour ou plus (chaque jour, semaine, 2 semaines, mois). Laissez-la non définie pour synchroniser exactement un intervalle après la vérification précédente, quelle que soit l’heure. |

```yaml
environment:
  - TZ=America/Sao_Paulo
  - DOWNTIFY_MONITOR_SYNC_TIME=03:00
```

## Applications mobiles et connexion

Voir [Applications mobiles](../features/mobile-apps.md) et [Utilisateurs et connexion](../features/users.md). La connexion est obligatoire sauf si `DOWNTIFY_DISABLE_AUTH` vaut `true` ; `DOWNTIFY_REQUIRE_SIGN_IN` des versions antérieures n’est plus utilisée (un avertissement est consigné tant qu’elle est définie).

| Variable | Valeur par défaut | Description |
|----------|---------|-------------|
| `DOWNTIFY_DISABLE_AUTH` | `false` | `true` désactive les comptes : personne ne se connecte, et quiconque atteint le serveur l’utilise en tant qu’administrateur. La page de connexion, les boutons de déconnexion, **Paramètres → Utilisateurs** et la partie compte de **Paramètres → Général** disparaissent. Les applications associées continuent de fonctionner. Remettez `false` (ou supprimez-la) et la connexion est de nouveau exigée, avec les comptes tels qu’ils étaient. Voir [Utilisateurs et connexion](../features/users.md#turning-accounts-off). |
| `DOWNTIFY_TRUSTED_PROXIES` | _(non définie)_ | Adresses ou réseaux de votre proxy inverse, séparés par des virgules (par ex. `172.18.0.0/16,10.0.0.5`). Seules les requêtes issues de ceux-ci voient leurs en-têtes `X-Forwarded-For`, `X-Forwarded-Proto` et `X-Forwarded-Host` pris en compte — pour l’adresse client sur laquelle les tentatives de connexion et d’association sont limitées, l’indicateur secure du cookie de connexion et la vérification de même origine. Non définie : ces en-têtes sont ignorés. |
| `DOWNTIFY_DISCOVERY` | `true` | `false` cesse d’annoncer le serveur sur le réseau local (mDNS, `_downtify._tcp`), ce que les applications utilisent pour le lister sous *Trouvés sur ce réseau*. Dans le réseau bridge de Docker, l’annonce n’atteint de toute façon pas le LAN — voir [Docker Compose](docker-compose.md#finding-the-server-from-the-apps). |
| `DOWNTIFY_TRANSCODE_CACHE_MB` | `2048` | Taille maximale, en Mo, sous laquelle est maintenu le cache des copies transcodées (`/data/transcode_cache`) ; les copies lues le moins récemment partent en premier. |
| `DOWNTIFY_TRANSCODE_CONCURRENCY` | `2` | Combien de morceaux sont transcodés à la fois pour les qualités de streaming plus petites des applications. |
| `DOWNTIFY_STREAM_CACHE_MB` | `1024` | Taille maximale, en Mo, sous laquelle est maintenu le cache de l’audio diffusé (`/data/stream_cache`) ; les copies lues le moins récemment partent en premier. La diffusion via le serveur est ce qui lit les titres non téléchargés là où le navigateur lui-même ne peut pas joindre YouTube. |
| `DOWNTIFY_STREAM_CONCURRENCY` | `2` | Combien de téléchargements de diffusion peuvent s’exécuter en même temps. |

## Contrôle de santé

L’image intègre un [`HEALTHCHECK` Docker](https://docs.docker.com/reference/dockerfile/#healthcheck) — aucun `--health-cmd` personnalisé n’est nécessaire. Il interroge `GET /api/health` sur le port du conteneur lui-même toutes les 30 secondes (délai d’attente de 5 secondes, 20 secondes de grâce au démarrage, 3 essais avant que le conteneur soit marqué comme non sain). `docker ps` et `docker inspect` affichent le résultat, et des outils comme le `condition: service_healthy` de Compose ou Watchtower peuvent s’en servir.

| Variable | Valeur par défaut | Description |
|----------|---------|-------------|
| `DOWNTIFY_HEALTHCHECK` | `1` | Mettez `0` pour désactiver le contrôle intégré — il indique alors toujours « sain » sans contacter le serveur. À utiliser si un contrôle externe/au niveau de l’orchestrateur (par ex. une liveness probe Kubernetes) doit être le seul à décider de la santé du conteneur. |

```yaml
environment:
  - DOWNTIFY_HEALTHCHECK=0
```

## Anti-bot / YouTube

YouTube met périodiquement à l’épreuve les téléchargeurs automatisés. Ces variables vous donnent des portes de sortie quand les valeurs par défaut cessent de fonctionner.

| Variable | Valeur par défaut | Description |
|----------|---------|-------------|
| `DOWNTIFY_FORCE_IPV4` | _(non définie)_ | Mettez `1` pour forcer yt-dlp à n’utiliser que l’IPv4. Utile quand votre hôte a une adresse IPv6 défaillante ou limitée. |
| `DOWNTIFY_YT_PLAYER_CLIENTS` | `ios,android,web_embedded,mweb,web,tv` | Liste, séparée par des virgules, des clients de lecteur yt-dlp à essayer, dans l’ordre. La liste par défaut de Downtify privilégie déjà les clients qui fonctionnent sans runtime JavaScript. Ne la modifiez que si vous savez qu’un client précis est bloqué. |
| `DOWNTIFY_YT_PO_TOKEN` | _(non définie)_ | Jetons Proof-of-Origin pour yt-dlp, séparés par des virgules, chacun sous la forme `<client>.<context>+<token>` (par ex. `mweb.gvs+ABC123`). Nécessaires uniquement si YouTube se met à exiger des PO Tokens pour les clients que vous utilisez. |
| `DOWNTIFY_COOKIES_FILE` | _(non définie)_ | Chemin d’un `cookies.txt` au format Netscape **dans le conteneur**. Permet à yt-dlp de s’authentifier comme une vraie session de navigateur — nécessaire pour les titres explicites/soumis à une limite d’âge et chaque fois que YouTube impose une barrière de connexion. Prioritaire sur un fichier envoyé dans l’interface web, et rend cette section de l’interface en lecture seule. Voir [Cookies YouTube](../features/youtube-cookies.md). |
| `DOWNTIFY_COOKIES_FROM_BROWSER` | _(non définie)_ | Nom du navigateur dont extraire les cookies (par ex. `chrome`, `firefox`). Exige que le magasin de cookies du navigateur soit accessible dans le conteneur ; c’est donc rarement utilisable avec Docker. |

::: tip Vous n’en avez probablement pas besoin
Vous pouvez envoyer un `cookies.txt` directement depuis **Paramètres → Cookies YouTube** dans l’interface web. Il est stocké dans `/data` (il survit donc aux mises à jour du conteneur), n’a besoin ni de bind mount ni de chemin de conteneur, et fonctionne de la même façon sous Windows, macOS et Linux. Les variables ci-dessus restent prises en charge pour les déploiements qui préfèrent gérer le fichier eux-mêmes.
:::

## Exemple : Docker Compose avec réglages anti-bot

```yaml
services:
  downtify:
    image: ghcr.io/henriquesebastiao/downtify:latest
    ports:
      - '8000:8000'
    volumes:
      - ./downloads:/downloads
      - downtify_data:/data
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_FORCE_IPV4=1
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
    restart: unless-stopped
```

## Obtenir un cookies.txt

Utilisez une extension de navigateur comme [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome) ou [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox). Exportez depuis `youtube.com` connecté à un vrai compte Google, puis envoyez le fichier dans **Paramètres → Cookies YouTube** ou montez-le dans le conteneur comme indiqué ci-dessus.

Voir [Cookies YouTube](../features/youtube-cookies.md) pour le pas-à-pas complet, et [Dépannage](../troubleshooting.md) quand les téléchargements échouent encore.

::: warning
Gardez votre `cookies.txt` privé — il contient des jetons de session qui donnent accès à votre compte Google.
:::
