---
icon: lucide/cog
---

# Comment ça marche

Le pipeline de téléchargement de Downtify comporte trois étapes :

```
Spotify embed  →  YouTube Music search  →  yt-dlp + ffmpeg + mutagen
  (metadata)         (audio match)          (download & tag)
```

## 1. Métadonnées — extraction de la page d’intégration Spotify

Quand vous collez une URL Spotify, Downtify récupère la page publique `open.spotify.com/embed` de ce titre, album ou playlist. Aucun compte Spotify, aucune clé d’API ni abonnement Premium n’est nécessaire — la page d’intégration est publiquement accessible.

Pour les **titres**, l’intégration renvoie : titre, artiste(s), nom de l’album, année de sortie, durée et URL de la pochette.

Pour les **albums et playlists**, elle renvoie la liste des titres. Les intégrations de playlist sont plafonnées à environ 50–100 entrées ; Downtify demande donc aussi la liste complète au point de terminaison anonyme `api.spotify.com` de Spotify, avec pagination, pour gérer les playlists de plusieurs centaines de morceaux.

::: info Enrichissement des métadonnées par titre
Les entrées de playlist dans l’intégration n’ont pas l’année de sortie et utilisent la pochette de la playlist au lieu de la pochette d’album de chaque titre. Pour la [Surveillance de playlists](features/playlist-monitor.md), Downtify récupère à nouveau chaque nouveau titre individuellement afin d’obtenir la bonne pochette et la bonne année avant de télécharger.
:::

## 2. Correspondance audio — YouTube Music, puis YouTube

Downtify utilise [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) pour chercher sur YouTube Music la meilleure correspondance audio. La requête est construite à partir du titre du morceau et du nom de l’artiste.

Un résultat n’est accepté que si son titre ressemble au titre source et s’il partage au moins un artiste. Le suffixe de version à tiret de Spotify et celui entre parenthèses de YouTube Music sont traités comme identiques (`Tubarões - Ao Vivo` correspond à `Tubarões (Ao Vivo)`), et un crédit d’artistes que YouTube Music regroupe en une seule entrée (`A, B, and C`) est éclaté avant la comparaison. Un « The » initial dans les noms d’artistes est ignoré (`Eden Project` correspond à `The Eden Project`), et un titre peut correspondre à une partie du titre d’une mise en ligne séparée par ` - ` (`くちづけDiamond - Kuchizuke Diamond`, `Game OST - Song Title - Artist`) tant que les autres parties ne désignent pas une version différente. Les versions karaoké, reprise, instrumentale, accélérée/ralentie, live (y compris `Ao Vivo`/`En Vivo`), acoustique, remix et dans une autre langue (par ex. `(Spanish Version)`) sont rejetées, sauf si le morceau source est lui-même cette version. Parmi les résultats restants, celui dont la durée est la plus proche de celle de Spotify l’emporte, avec un bonus pour un nom d’album concordant. Si aucun résultat ne convient, la recherche est refaite avec les mots dans l’autre ordre (`<titre> <artiste>` au lieu de `<artiste> <titre>`) — YouTube Music classe les résultats différemment selon l’ordre des mots, et certains morceaux n’apparaissent près du haut que d’une façon. Si cela ne donne rien non plus et que l’album est connu, la liste des titres de l’album est parcourue directement.

### Repli sur YouTube standard

Certains morceaux manquent sur YouTube Music, ou n’y existent que sous la forme d’un autre enregistrement. YouTube standard est donc aussi interrogé lorsque :

- YouTube Music n’a **aucune correspondance acceptable**, ou
- la durée de sa meilleure correspondance s’écarte de **plus de 10 secondes** de celle de Spotify — un fort indice qu’il s’agit d’un autre enregistrement (par ex. une version doublée portant le même titre).

Les résultats de YouTube standard passent les mêmes vérifications de titre, d’artiste et de version, et ne sont jamais acceptés au-delà de 30 secondes d’écart avec la durée de Spotify. Un résultat YouTube ne remplace une correspondance YouTube Music faible que si sa durée est strictement plus proche ; sinon la correspondance YouTube Music est conservée, car ses mises en ligne de catalogue ont en général l’audio le plus propre.

Si aucun des deux sites n’a de correspondance acceptable, le titre échoue avec `Could not find a YouTube match for '<title>'` plutôt que de télécharger le mauvais morceau.

Pour les URL YouTube saisies directement, cette étape est ignorée — Downtify télécharge cette vidéo précise.

::: info Liens Deezer
Un lien Deezer de titre/album/playlist/artiste collé (`deezer.com/track/…`) fonctionne comme un lien Spotify : l’API REST publique de Deezer fournit titre, artiste(s), album et pochette, chaque titre est diffusé en entier depuis YouTube avant que vous ne le téléchargiez, et cette même étape le fait correspondre sur YouTube Music/YouTube. Downtify n’a pas de résolveur de discographie Deezer propre au-delà de ce que renvoie déjà l’API de Deezer ; un lien Deezer se télécharge donc et (pour une playlist) obtient son propre M3U et sa pochette, mais ne peut pas être surveillé par la [Surveillance de playlists](features/playlist-monitor.md).
:::

## 3. Téléchargement et tags — yt-dlp + ffmpeg + mutagen

### Téléchargement

[yt-dlp](https://github.com/yt-dlp/yt-dlp) télécharge l’audio depuis YouTube. Downtify le configure pour essayer plusieurs clients de lecteur dans l’ordre (`ios`, `android`, `web_embedded`, `mweb`, `web`, `tv`) afin de contourner les défis de détection de bots de YouTube. Voir [Variables d’environnement](getting-started/environment-variables.md) pour les options anti-bot avancées.

### Conversion

[ffmpeg](https://ffmpeg.org/) convertit l’audio brut dans le format choisi (MP3, FLAC, M4A, OGG ou OPUS) au débit choisi.

### Étiquetage

[mutagen](https://mutagen.readthedocs.io/) écrit les métadonnées dans le fichier converti :

| Tag | Écrit |
|-----|---------|
| Titre | Oui |
| Artiste(s) | Oui, tous les artistes crédités, aussi un par valeur dans un tag `ARTISTS` |
| Artiste de l’album | Oui, l’artiste de l’album tel que la source le crédite, sinon le premier artiste |
| Indicateur de compilation | Seulement pour un album que la source crédite à « Various Artists », ou qu’un administrateur marque comme tel |
| Album | Oui |
| Année | Oui |
| Pochette (JPEG) | Oui |
| Paroles (simples + synchronisées) | Oui, si lrclib renvoie un résultat |
| Marque explicite | Oui, quand le morceau est signalé comme explicite (voir [Marque de contenu explicite](features/explicit-marker.md)) |

Les tags ID3/Vorbis/MP4 exacts dépendent du format de sortie. Voir [Paroles](features/lyrics.md) pour savoir comment les paroles sont intégrées.

## Progression en temps réel

Downtify diffuse la progression des téléchargements vers le navigateur via une connexion **WebSocket** (`/api/ws`). À mesure que yt-dlp signale l’avancement, le serveur diffuse des mises à jour de pourcentage et d’état à tous les clients connectés. Vous voyez donc la barre de progression avancer en temps réel — sans polling, sans rechargement de la page.

## Nom des fichiers et organisation

Le nom du fichier de sortie est construit à partir du modèle configuré dans les Paramètres (par défaut : `{artists} - {title}`). Les caractères invalides dans les noms de fichiers sont supprimés.

Quand *Classer par artiste* est activé, le fichier est placé dans un sous-dossier portant le nom de l’artiste de l’album — ou, pour un titre d’une compilation multi-artistes, de son premier artiste. Sinon, les titres seuls vont à la racine du répertoire de téléchargements et les titres de playlists/albums vont dans un sous-dossier par playlist ou par album. Voir [Plusieurs artistes et compilations](features/file-organization.md#several-artists-and-compilations).
