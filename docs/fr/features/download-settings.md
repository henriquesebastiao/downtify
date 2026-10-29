---
icon: lucide/sliders-horizontal
---

# Paramètres de téléchargement

Ouvrez **Paramètres** dans la barre latérale (sur téléphone : **Plus → Paramètres**). La page est divisée en sections — Général, Sources audio, Téléchargements et fichiers, Tags et paroles, Navidrome, Bibliothèque et À propos. Les modifications sont conservées jusqu’à ce que vous appuyiez sur **Enregistrer** dans la barre qui apparaît en bas ; quitter la page avec des modifications non enregistrées demande d’abord confirmation. Les paramètres sont enregistrés sur disque et survivent aux redémarrages du conteneur.

## Format

| Format | Extension | Remarques |
|--------|-----------|-------|
| MP3 | `.mp3` | Par défaut. Compatibilité universelle. |
| FLAC | `.flac` | Sans perte. Le réglage du débit est ignoré. |
| M4A | `.m4a` | AAC dans un conteneur MPEG-4. Bien pour les appareils Apple. |
| OGG | `.ogg` | Ogg Vorbis. Format ouvert, bon rapport qualité/taille. |
| OPUS | `.opus` | Meilleure compression à faible débit. |

## Débit

Disponible pour les formats avec perte (MP3, M4A, OGG, OPUS). Le FLAC ignore ce réglage.

| Option | Kbps |
|--------|------|
| Faible | 128 |
| Moyen | 192 |
| Élevé | 256 |
| Maximal | **320** (par défaut) |

L’audio téléchargé est encodé au débit choisi, pour tous les formats avec perte. Si l’audio servi par YouTube a déjà le codec cible à peu près à ce débit (par ex. son flux AAC d’environ 128 kbps pour **M4A @ 128**), il est conservé tel quel au lieu d’être ré-encodé, puisqu’un ré-encodage ne ferait que perdre en qualité.

::: info Un débit plus élevé n’ajoute pas de qualité
L’audio de YouTube plafonne à environ **128–160 kbps** (AAC ou Opus), et Downtify télécharge toujours le meilleur flux disponible. L’encoder à 256 ou 320 kbps donne des fichiers plus gros qui préservent fidèlement cette source, mais ne peut pas restituer des détails que la source n’a jamais eus. Choisissez un débit plus bas si la taille des fichiers compte davantage pour vous.
:::

## Modèle de nom de fichier

Le modèle de nom de fichier par défaut est :

```
{artists} - {title}
```

Ce qui produit des noms comme `The Night Owls - Do I Still Recall.mp3`.

Jetons disponibles :

| Jeton | Description |
|-------|-------------|
| `{title}` | Titre du morceau |
| `{artists}` | Tous les artistes crédités, séparés par des virgules (par ex. `Christina Aguilera, Lil' Kim, Mýa, P!nk`) |
| `{artist}` | Le premier artiste crédité seulement (par ex. `Christina Aguilera`). Un nom qui contient une virgule, comme `Earth, Wind & Fire`, reste entier. |
| `{album}` | Nom de l’album |
| `{tracknumber}` | Position du morceau dans son album, complétée par un zéro sur 2 chiffres (par ex. `01`, `12`). Vide quand la source n’a pas de numéro de piste (par ex. un résultat de texte libre/recherche YouTube). |
| `{year}` | Année de sortie (par ex. `2025`). Vide quand la source n’a pas de date de sortie (par ex. un résultat de texte libre/recherche YouTube). |

Le modèle peut aussi contenir `/` pour créer des sous-dossiers. Par exemple, pour organiser une bibliothèque en `Artiste/Album (2025)/01 - Titre.mp3` — pratique pour télécharger une discographie complète, puisque chaque album atterrit dans son propre dossier avec son année de sortie :

```
{artist}/{album} ({year})/{tracknumber} - {title}
```

Utilisez `{artist}` plutôt que `{artists}` dans un dossier : avec `{artists}`, un morceau avec des invités obtient son propre dossier (`Christina Aguilera, Lil' Kim, Mýa, P!nk/`) au lieu d’atterrir dans celui du premier artiste.

::: info
Ceci est indépendant des options **Classer par artiste** / **Classer par album** — celles-ci dirigent les téléchargements de playlists/albums vers des dossiers partagés par artiste ou par album dans toute votre bibliothèque (voir [Organisation des fichiers](file-organization.md)). `{tracknumber}` et `{year}` permettent simplement à un modèle comme celui ci-dessus de construire cette même organisation à la main, morceau par morceau, sans activer ces options.
:::

::: tip Compilations
Le modèle s’applique à un morceau d’une compilation multi-artistes comme à n’importe quel autre : `{artist}` est le premier artiste du morceau lui-même, jamais « Various Artists ». Voir [Plusieurs artistes et compilations](file-organization.md#several-artists-and-compilations).
:::

## Téléchargements simultanés

Contrôle combien de morceaux sont téléchargés en même temps. Choisissez une valeur prédéfinie (1, 2, 3, 5, 8) ou saisissez une valeur personnalisée de **1 à 30** dans le champ numérique à côté.

| Valeur | Comportement |
|-------|-----------|
| **1** | Séquentiel — un morceau à la fois (le plus sûr, utilisation de ressources minimale) |
| **3** | Par défaut. Bon équilibre entre vitesse et stabilité. |
| **8** | Plus rapide pour les grandes playlists |
| **jusqu’à 30** | Idéal pour les connexions très rapides ; utilise plus de CPU et de bande passante, et augmente le risque que YouTube vous limite. |

La limite s’applique à tout téléchargement par lot — téléchargements de playlists/albums, endpoint de file par lot et [imports de bibliothèque](library-import.md) CSV — et aux recherches de la synchronisation des **[Dossiers de musique existants](external-library.md)** (paroles, pochettes, genre). Elle ne s’applique **pas** aux passages du Suivi de playlists, qui téléchargent les nouveaux morceaux un par un. Modifier cette valeur dans les Paramètres prend effet immédiatement sans redémarrage ; le serveur ramène toute valeur hors de `1–30` dans cet intervalle.

## Pause entre téléchargements

Fait attendre Downtify un nombre de secondes configurable après avoir terminé un morceau avant de commencer le suivant, au lieu d’enchaîner les requêtes.

| Valeur | Comportement |
|-------|-----------|
| **0** | Par défaut — désactivé, aucune attente. |
| **5 / 15 / 30 / 60** | Valeurs prédéfinies, ou saisissez une valeur personnalisée de **0 à 300 secondes**. |

S’applique aux téléchargements de playlists, d’albums et de lots, aux [imports de bibliothèque](library-import.md) CSV et aux passages automatiques du Suivi de playlists. Ignoré pour le téléchargement manuel d’un seul morceau (il n’y a pas de « suivant » à attendre), et après le *dernier* morceau de tout lot pour qu’une exécution ne se termine pas par une attente inutile.

Associé à une valeur plus basse de **Téléchargements simultanés**, c’est le principal outil pour éviter la limitation de débit de YouTube lors du téléchargement sans surveillance d’une grande playlist ou d’une bibliothèque importée.

## Pause entre les recherches de synchro

Même idée, mais pour les **[Dossiers de musique existants](external-library.md)** plutôt que pour les téléchargements. La synchronisation cherche paroles, pochettes manquantes et genre par lots de **[Téléchargements simultanés](#parallel-downloads)** morceaux à la fois, puis attend ce nombre de secondes avant le lot suivant. Par défaut **0** (les recherches continuent à s’exécuter simultanément, toujours plafonnées par Téléchargements simultanés). Utilisez quelques secondes sur une grande collection pour que LRCLIB, les sources de pochettes et iTunes ne soient pas sollicités tous à la fois.

## Télécharger les pochettes

Contrôle si Downtify intègre la pochette de l’album. Activé par défaut. Désactivez-le pour ignorer entièrement la récupération des pochettes — tous les autres tags (titre, artiste, album, année, paroles) sont toujours intégrés normalement, mais les fichiers sont plus petits et se téléchargent un peu plus vite puisque l’image de pochette n’est jamais demandée ni écrite.

Le désactiver évite aussi d’écrire le `cover.jpg` autonome que produit l’option *Classer par album* (voir [Organisation des fichiers](file-organization.md)), et le [lecteur](player.md) comme la bibliothèque n’afficheront aucune image pour les morceaux téléchargés ainsi (l’icône de note de musique à la place).

Ce `cover.jpg` est partagé par tous les morceaux du dossier de l’album. Supprimer un morceau depuis la page Bibliothèque le supprime aussi, mais seulement quand c’est le **dernier** morceau restant dans ce dossier — tant qu’un autre morceau du même album est encore là, la pochette reste.

## Résolution des pochettes

Utile seulement quand **Télécharger les pochettes** (ci-dessus) est activé. Définit la taille cible (largeur et hauteur, en pixels) que Downtify demande pour la pochette intégrée provenant de **YouTube Music** ou de **Deezer**. Choisissez une valeur prédéfinie (300, 600, 800, 1000, 1200) ou faites glisser le curseur de **300 à 1200** ; la valeur actuelle en pixels s’affiche à côté. La valeur par défaut est 600.

C’est utile pour alimenter un serveur multimédia comme Plex, qui affiche les pochettes dans une résolution supérieure à celle que Downtify intègre par défaut.

Les deux sources appliquent le réglage différemment, puisqu’une seule d’entre elles peut réellement être redimensionnée à la demande :

- Les miniatures de **YouTube Music** peuvent être redimensionnées en modifiant leur URL — vérifié sur le CDN réel, les valeurs élevées renvoient vraiment plus de détail (pas seulement un agrandissement) pour la plupart des pochettes, jusqu’à la résolution de l’image source elle-même.
- **Deezer** ne propose que quatre tailles fixes pour la pochette de tout morceau, album, artiste ou playlist (56, 250, 500 et 1000 px) — il n’y a pas de taille intermédiaire à demander. Downtify choisit la plus petite de ces quatre qui soit encore au moins aussi grande que la valeur configurée (demander 300 px donne celle de 500 px, faute de taille exacte de 300 px) ; demander plus de 1000 px donne aussi celle de 1000 px, la plus grande de Deezer.

::: info Les pochettes issues de Spotify ne sont pas concernées
Downtify intègre déjà la **plus grande** pochette que l’API d’intégration publique de Spotify propose pour les morceaux/albums/playlists résolus par Spotify — il n’y a pas de taille supérieure à demander. Ce réglage ne relève le plafond que pour les morceaux résolus par YouTube Music (recherche en texte libre, URL YouTube, et tout morceau Spotify rapproché de YouTube Music pour l’audio proprement dit) ou par Deezer (un lien Deezer collé, ou un morceau des [Classements](charts.md)).
:::

Modifier cette valeur dans les Paramètres prend effet immédiatement, y compris pour la page de recherche actuellement ouverte — cela n’oblige pas à retélécharger quoi que ce soit déjà présent sur le disque.

## Écraser les fichiers existants

Activé par défaut, conformément au comportement historique de Downtify : chaque téléchargement passe par le pipeline (récupération de l’audio, tags, pochette, paroles) et écrase tout fichier déjà présent au chemin de sortie calculé.

### Ce que « à nouveau » signifie vraiment

Activé, un nouveau téléchargement est une **exécution entièrement neuve**, pas une réparation du fichier existant. Downtify ne regarde pas ce que vous avez déjà : il interroge vos [sources audio](#audio-provider) dans l’ordre configuré — donc si slskd est en premier, slskd est essayé en premier, pas seulement en repli —, récupère l’audio de la source qui répond et y écrit les tags, la pochette et les paroles du jour.

Cela a une conséquence à connaître avant de retélécharger une grande bibliothèque :

::: warning Un format différent laisse l’ancien fichier derrière
Le nouveau fichier est écrit au chemin que produit le [modèle de nom de fichier](#output-filename-template), avec l’extension du **nouvel** audio. Downtify n’écrase l’ancien fichier que si les deux ont la même extension.

Ainsi, retélécharger `Artiste - Morceau.mp3` quand slskd répond avec un FLAC vous donne **les deux** : `Artiste - Morceau.mp3` (l’ancien, intact) et `Artiste - Morceau.flac`. Avec [Laisser les fichiers slskd en place](slskd-navidrome.md#leave-files-in-place) activé — le réglage par défaut —, le fichier slskd n’est même pas copié dans votre dossier de téléchargements : l’ancien reste exactement où il était et le nouveau se trouve sous `slskd/`.

Rien n’est perdu, mais vous obtenez des doublons. Pour vraiment remplacer un fichier, voir [Remplacer l’audio](replace-audio.md), qui conserve le chemin, le format et les tags.
:::

### La pochette vient de Spotify ou de YouTube Music, pas du fichier

Toute image que porte l’audio téléchargé — y compris une pochette haute résolution intégrée dans un fichier slskd — est **écartée et remplacée** lors du tagging. Downtify intègre toujours la pochette qu’il récupère pour le morceau auprès de Spotify ou de YouTube Music, à la [résolution des pochettes](#cover-art-resolution) que vous avez configurée (600 px par défaut). Il en va de même pour le titre, les artistes, l’album et le reste des tags : les tags propres à la source ne sont pas conservés.

Si ce que vous voulez, ce sont de plus grandes pochettes sur des fichiers que vous avez déjà, retélécharger est le chemin le plus long. [Améliorer la bibliothèque](library-upgrade.md) fait exactement cela — elle compare la pochette intégrée de chaque fichier à celles de Spotify, iTunes et YouTube Music, écrit la plus grande, complète les paroles et tags manquants, et ne touche jamais à l’audio.

Désactivez-le pour ne jamais télécharger un morceau déjà présent sur le disque. C’est surtout utile pour télécharger une playlist, importer une [bibliothèque CSV](library-import.md) ou laisser le [Suivi de playlists](playlist-monitor.md) synchroniser des playlists qui partagent des morceaux entre elles ou avec des morceaux déjà dans votre bibliothèque — option activée, chacun de ces doublons est retéléchargé.

Désactivée, Downtify cherche le morceau **n’importe où dans le dossier de téléchargements**, pas seulement là où irait le nouveau téléchargement :

- la racine de la bibliothèque (téléchargements de morceaux seuls),
- le dossier de n’importe quelle playlist (téléchargements de playlists, imports CSV, Suivi de playlists),
- un dossier artiste/album, ou l’organisation à plat d’avant l’activation ou la désactivation de *Classer par artiste/album*.

Un morceau compte comme déjà téléchargé lorsqu’un fichier audio (`.mp3`, `.flac`, `.m4a`, `.ogg`, `.opus`) porte le nom que produit pour lui le [modèle de nom de fichier](#output-filename-template), comparé sans tenir compte de la casse. Un fichier de paroles `.lrc` seul ne compte pas. Si le modèle contient des dossiers (par ex. `{artists}/{title}`), ces dossiers doivent eux aussi correspondre, afin que le morceau d’un autre artiste portant le même titre ne soit pas pris pour celui-ci. Comme les fichiers ne portent pas d’identifiant de morceau Spotify/YouTube, la correspondance se fait par nom : un fichier renommé, ou enregistré avec un autre modèle de nom de fichier, ne sera pas reconnu.

Quand un morceau est ignoré :

- Rien n’est récupéré : ni audio, ni pochette, ni paroles, ni nouveau tagging. Pour les morceaux Spotify, la vérification a lieu avant même la recherche sur YouTube Music, donc les morceaux déjà téléchargés ne coûtent aucune requête de recherche.
- La file affiche le morceau comme terminé, et les [fichiers M3U](m3u-export.md) des playlists pointent vers le fichier existant où qu’il se trouve (par ex. `../Artiste - Titre.mp3`), de sorte que la playlist se lit toujours en entier.
- Si le même morceau est mis en file deux fois en même temps (présent deux fois dans une playlist, ou dans deux playlists téléchargées en parallèle), une seule copie est téléchargée. L’autre l’attend puis est ignorée.

## Morceaux longs

**Paramètres → Téléchargements et fichiers → Durée maximale** plafonne la durée des morceaux pour les téléchargements *et* les diffusions (par défaut **10 minutes**, `0` accepte tout). Les morceaux plus longs sont refusés avant que quoi que ce soit soit récupéré, avec l’erreur de file *« les morceaux de plus de … ne sont pas téléchargés »* — les mix et uploads d’une heure ne sont jamais ce qu’un morceau de bibliothèque devrait être. Le même plafond protège la diffusion : un morceau plus long est refusé avec un `400` (les appelants qui connaissent sa durée la passent dans `duration`, et le fichier en cache est de toute façon sondé), si bien que les longs uploads ne s’accumulent pas non plus dans le cache de diffusion. Les fichiers déjà téléchargés et les épisodes de podcast (souvent plus longs) ne sont pas concernés.

## Fournisseur audio

Le fournisseur audio par défaut est **YouTube Music**. Downtify utilise [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) pour chercher la meilleure correspondance en comparant la durée du morceau. Quand YouTube Music n’a pas de correspondance acceptable, ou seulement une dont la durée est très différente (probablement un autre enregistrement), Downtify se rabat automatiquement sur une recherche sur YouTube standard — voir [Comment ça marche](../how-it-works.md#fallback-to-standard-youtube).

**Paramètres → Sources audio** peut aussi n’utiliser que **YouTube** standard, ou **slskd** (Soulseek), comme liste de repli ordonnée — voir [slskd et Navidrome](slskd-navidrome.md#audio-sources-and-fallback-order).

### Forcer une source audio précise

Si Downtify choisit la mauvaise vidéo YouTube Music (par ex. une reprise au lieu de l’original), vous pouvez la remplacer morceau par morceau :

**Option A — collez directement une URL YouTube Music**

Collez `https://music.youtube.com/watch?v=…` (ou une URL ordinaire `youtube.com/watch?v=…`) dans la barre de recherche et lancez le téléchargement. Downtify récupère l’audio de cette vidéo précise.

::: info
Lors d’un téléchargement par URL YouTube, les métadonnées (titre, artiste, pochette) viennent de YouTube plutôt que de Spotify. Pour des tags propres, utilisez l’Option B.
:::

**Option B — forcer l’audio d’un morceau en échec**

1. Dans la **File de téléchargement**, cliquez sur **Forcer la source audio** sous un morceau en échec.
2. Collez une URL YouTube ou YouTube Music dans le champ qui apparaît.
3. Appuyez sur **Entrée** ou cliquez sur **Appliquer**.

Downtify retélécharge le morceau avec cette vidéo précise tout en conservant toutes les métadonnées Spotify (titre, artiste, album, pochette, paroles).

## Métadonnées intégrées

Downtify intègre les tags suivants dans chaque fichier téléchargé, quel que soit le format :

| Tag | Source |
|-----|--------|
| Titre | Embed Spotify |
| Artiste(s) | Embed Spotify |
| Album | Embed Spotify — pour un téléchargement de morceau seul, l’album que nomme la page publique Spotify du morceau (l’embed du morceau lui-même n’en a pas) |
| Année | Embed Spotify (récupération au niveau du morceau) |
| Pochette | Embed Spotify (pochette au niveau du morceau) pour les morceaux résolus par Spotify ; miniature YouTube Music ou pochette Deezer sinon. Facultatif — voir [Télécharger les pochettes](#download-cover-art) et [Résolution des pochettes](#cover-art-resolution) |
| Paroles | lrclib (si activé) |
