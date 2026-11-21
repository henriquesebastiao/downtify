---
layout: home
title: Downtify
titleTemplate: "Téléchargeur Spotify et lecteur de musique auto-hébergé"
description: "Téléchargeur Spotify auto-hébergé avec lecteur. Collez un lien Spotify, YouTube Music, Deezer ou SoundCloud, obtenez des MP3 ou FLAC étiquetés. Sans clé d’API."
icon: lucide/house
hero:
  eyebrow: Téléchargeur de musique auto-hébergé
  headline:
    - Collez un lien.
    - Récupérez la musique.
  lead: Un téléchargeur de musique auto-hébergé avec un lecteur intégré. Collez un lien Spotify, YouTube Music, Deezer ou SoundCloud et obtenez une bibliothèque parfaitement étiquetée, prête à être écoutée dans le navigateur, sur votre téléphone ou dans votre serveur multimédia.
  note: Sans compte Spotify, sans clé d’API, sans Premium.
  actions:
    - text: Commencer
      link: /fr/getting-started/installation/
      primary: true
    - text: Code source sur GitHub
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Version
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Téléchargements Docker
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&label=docker%20pulls&color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Étoiles sur GitHub
      src: https://img.shields.io/github/stars/henriquesebastiao/downtify?style=flat&label=stars&color=1AD05C
      link: https://star-history.com/#henriquesebastiao/downtify&Date
    - alt: Licence
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
video:
  src: /assets/media/downtify-demo.mp4
  poster: /assets/media/downtify-demo-poster.webp
  label: 'Downtify en 44 secondes : collez le lien d’une playlist, téléchargez-la en un clic, gardez-la synchronisée et écoutez-la avec des paroles synchronisées, sur ordinateur et sur téléphone.'
why:
  - icon: link
    title: Un lien suffit
    text: Collez un titre, un album, une playlist entière ou un artiste depuis Spotify, YouTube Music, Deezer ou SoundCloud, ou tapez simplement ce que vous voulez écouter. Downtify trouve l’audio et le ramène à la maison.
    link: /fr/how-it-works/
  - icon: tag
    title: Des fichiers qui valent la peine d’être gardés
    text: Chaque fichier porte sa pochette, tous les artistes crédités, l’album, l’année, le numéro de piste et les paroles, synchronisées quand elles existent. MP3, FLAC, M4A, OGG ou Opus, ou l’audio de la source tel quel.
    link: /fr/features/download-settings/
  - icon: music
    title: Votre propre service de streaming
    text: Un lecteur complet dans le navigateur, avec paroles synchronisées, karaoké, file d’attente, titres likés, playlists et podcasts. Les applications Android et iOS emportent votre bibliothèque partout, même hors connexion.
    link: /fr/features/player/
  - icon: radar
    title: Réglez-le et oubliez-le
    text: Surveillez des playlists et des artistes. Les nouveaux titres et les nouvelles sorties se téléchargent tout seuls, au rythme que vous choisissez.
    link: /fr/features/playlist-monitor/
  - icon: server
    title: Fait pour votre serveur maison
    text: Une image Docker pour amd64 et arm64, SQLite ou PostgreSQL, des comptes pour toute la maison avec authentification unique en option, et des playlists que Jellyfin, Navidrome et Plex reconnaissent.
    link: /fr/getting-started/
  - icon: shield
    title: Sans contrepartie
    text: Ni clé d’API Spotify, ni compte développeur, ni Premium. L’application n’a ni publicité, ni statistiques d’usage, ni rien de payant. Elle est libre et open source.
    link: /fr/contributing/
showcase:
  - shot: now-playing
    label: Lecture en cours
    caption: Les paroles suivent la chanson, ligne par ligne, à côté de la pochette et de ce qui vient ensuite.
    alt: La vue Lecture en cours en plein écran, avec la pochette de l’album, les paroles synchronisées dont la ligne actuelle est mise en avant, et la file d’attente.
  - shot: karaoke
    label: Karaoké
    caption: De grandes paroles qui se remplissent à mesure que chaque ligne est chantée, prêtes à s’ouvrir sur un second écran.
    alt: La vue karaoké, avec de grandes paroles qui se remplissent sur un fond animé aux couleurs de la pochette.
  - shot: home
    label: Accueil
    caption: Collez un lien ou cherchez quelque chose de nouveau, et reprenez là où vous en étiez.
    alt: La page d’accueil, avec une zone pour coller un lien ou chercher, les statistiques de la bibliothèque, l’album en cours d’écoute et les albums ajoutés récemment.
  - shot: library
    label: Bibliothèque
    caption: Albums, artistes, playlists et titres, triés et filtrés comme vous voulez.
    alt: La page Bibliothèque, avec une grille de pochettes d’albums et des onglets pour les albums, les artistes, les playlists et les titres.
  - shot: playlist
    label: Playlists
    caption: Vos propres playlists, avec leur propre pochette, à écouter, partager ou télécharger en ZIP.
    alt: Une page de playlist, avec sa pochette, ses boutons et ses morceaux avec album, format et date de sortie.
  - shot: phones
    label: Sur votre téléphone
    caption: La même application sur votre téléphone, installable depuis le navigateur.
    alt: Downtify sur trois téléphones, montrant la page d’accueil, Lecture en cours et la Bibliothèque.
pipeline:
  - icon: link
    title: Collez un lien
    text: Spotify, YouTube Music, Deezer ou SoundCloud. Ou tapez simplement un titre.
  - icon: search
    title: Trouve l’audio
    text: La correspondance la plus proche sur YouTube Music, vérifiée par la durée. D’autres sources si vous le souhaitez.
  - icon: download
    title: Télécharge et étiquette
    text: yt-dlp et ffmpeg le récupèrent. Pochette, paroles et tags vont dans le fichier.
  - icon: music
    title: Écoutez partout
    text: Dans le navigateur, sur votre téléphone, ou dans Jellyfin, Navidrome et Plex.
quickStart:
  - text: Guide d’installation
    link: /fr/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /fr/getting-started/docker-compose/
  - text: Installation en un clic
    link: /fr/getting-started/one-click/
apps:
  - icon: smartphone
    title: Downtify pour Android
    text: L’application officielle. Elle trouve votre serveur sur le réseau, diffuse en qualité d’origine en Wi-Fi et en qualité réduite sur les données mobiles, garde des titres hors connexion et fonctionne avec Android Auto. Encore en test, sur GitHub Releases et Obtainium.
    link: https://github.com/henriquesebastiao/downtify-android
  - icon: tablet-smartphone
    title: Downtify pour iOS
    text: Créée par un membre de la communauté pour iPhone et iPad (iOS 17 ou plus récent), avec titres hors connexion et commandes sur l’écran verrouillé. La bêta publique est sur TestFlight.
    link: https://github.com/michaelmoskie/Downtify-IOS-Client
community:
  - text: Étoile sur GitHub
    link: https://github.com/henriquesebastiao/downtify
    icon: star
    primary: true
  - text: Sponsoriser
    link: https://github.com/sponsors/henriquesebastiao
    icon: heart
  - text: Traduire
    link: /fr/features/internationalization/
    icon: languages
  - text: Contribuer
    link: /fr/contributing/
    icon: git-pull-request
---

## Pourquoi Downtify

<HomeHighlights :items="$frontmatter.why" />

## De plus près

<HomeShowcase :items="$frontmatter.showcase" />

## Comment ça marche

Downtify n’a besoin d’aucune clé d’API Spotify et ne télécharge jamais rien depuis Spotify. Il lit dans des sources publiques ce que désigne un lien, choisit l’audio de YouTube Music dont la durée correspond le mieux, le télécharge avec `yt-dlp`, le convertit avec `ffmpeg` et l’étiquette avec `mutagen`, le tout dans un seul conteneur Docker. YouTube prend le relais quand rien ne correspond bien, et SoundCloud, Soulseek et Deemix s’ajoutent si vous les activez. [Chaque étape, en détail](how-it-works.md).

<HomePipeline :steps="$frontmatter.pipeline" />

## Ce que vous pouvez coller

| Source        | Ce qui fonctionne                   | Exemple                             |
| ------------- | ----------------------------------- | ----------------------------------- |
| Spotify       | Titres, albums, playlists, artistes | `open.spotify.com/playlist/…`       |
| YouTube Music | Titres, albums, playlists, artistes | `music.youtube.com/playlist?list=…` |
| YouTube       | Vidéos                              | `youtube.com/watch?v=…`             |
| Deezer        | Titres, albums, playlists, artistes | `deezer.com/album/…`                |
| SoundCloud    | Titres                              | `soundcloud.com/artist/track`       |
| Recherche     | Ce que vous taperiez                | `The Night Owls Do I Still Recall`  |
| CSV           | Exports de bibliothèque             | Soundiiz, TuneMyMusic, Exportify    |

## Tout ce qu’il fait

Chaque fonctionnalité a sa propre page, avec toutes les options expliquées. [Toutes les fonctionnalités d’un coup d’œil](features/index.md).

<HomeFeatures />

## Prêt en une minute

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Ouvrez [`localhost:8000`](http://localhost:8000), connectez-vous en tant que **admin** avec le mot de passe **downtify** et collez un lien. Changez ce mot de passe dans **Paramètres → Général** sans attendre. Votre musique arrive dans `/path/to/music`, tags compris.

<HomeActions :actions="$frontmatter.quickStart" />

## Questions fréquentes

::: details Faut-il un compte Spotify, Premium ou une clé d’API ?
Non. Downtify lit les informations des titres, albums et playlists dans les pages d’intégration (embed) publiques de Spotify : il n’a besoin d’aucun identifiant, et l’audio ne vient jamais de Spotify. Voir [Comment ça marche](how-it-works.md).
:::

::: details D’où vient l’audio, et quelle est sa qualité ?
De YouTube Music par défaut : le résultat dont la durée correspond le mieux au morceau, avec YouTube en solution de repli. Choisissez MP3, FLAC, M4A, OGG ou Opus au débit voulu, ou gardez le meilleur audio de la source sans le réencoder. Les fichiers sans perte viennent de sources que vous ajoutez vous-même : votre propre serveur [Soulseek (slskd)](features/slskd-navidrome.md), dont les fichiers gardent leur format d’origine, ou un serveur [Deemix](features/deemix.md). Voir [Réglages de téléchargement](features/download-settings.md).
:::

::: details Est-ce que ça marche avec Jellyfin, Navidrome ou Plex ?
Oui. Les fichiers sont étiquetés comme les serveurs multimédias l’attendent, rangés dans des dossiers `Artiste/Album/`, et chaque playlist a un fichier M3U standard qu’ils reconnaissent. Navidrome peut aussi recevoir les playlists synchronisées et des notes tirées de Deezer. Voir [Organisation des fichiers](features/file-organization.md) et [Export M3U](features/m3u-export.md).
:::

::: details Est-ce que ça tourne sur un Raspberry Pi ou un NAS ?
L’image est publiée pour `amd64` et `arm64`, et Umbrel, CasaOS et HomeDock OS l’installent en un clic. Voir [Installation en un clic](getting-started/one-click.md).
:::

::: details YouTube affiche « Sign in to confirm you're not a bot ». Que faire ?
Envoyez un `cookies.txt` dans **Paramètres → Cookies YouTube** ; Downtify garde ensuite cette session connectée tout seul. Si YouTube vous limite encore, augmentez la _Pause entre téléchargements_, réduisez les _Téléchargements simultanés_, puis essayez `DOWNTIFY_FORCE_IPV4=1`. Voir [Dépannage](troubleshooting.md) et [Cookies YouTube](features/youtube-cookies.md).
:::

## Emportez-le partout

<HomeHighlights :items="$frontmatter.apps" />

Tout autre client peut utiliser la même API : voir le [contrat du client mobile](mobile-client-contract.md).

<div class="home-cta">

## Fait au grand jour

Downtify est libre et open source. Plus de 35 personnes ont contribué au code, des traducteurs de la communauté l’ont porté en 12 langues, et beaucoup de fonctionnalités sont nées d’une idée ouverte dans une issue. S’il a gagné sa place sur votre serveur, mettez-lui une étoile sur GitHub, parlez-en à un ami qui héberge ses propres services, ou sponsorisez son développement : cela aide à financer le temps que demande chaque version.

<HomeActions :actions="$frontmatter.community" />

</div>
