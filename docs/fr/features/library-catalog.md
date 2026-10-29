---
icon: lucide/library
---

# Catalogue de la bibliothèque et synchronisation des chemins

Downtify tient un petit **catalogue** des fichiers sous `/downloads` (le dossier slskd, quand les [fichiers slskd sont laissés en place](slskd-navidrome.md#leave-files-in-place), et les [dossiers supplémentaires](external-library.md) que vous ajoutez dans les Paramètres) pour que la page Bibliothèque, le lecteur, l’export M3U, la synchro Navidrome et la détection des doublons restent cohérents quand des fichiers bougent ou que des playlists grandissent.

## Ce qui est stocké

| Stockage | Emplacement | Rôle |
|-------|----------|---------|
| **Index des morceaux** | `/data/downtify_library.db` | Associe les identifiants de morceaux Spotify aux chemins de la bibliothèque, pour reconnaître un morceau déjà sur le disque |
| **Catalogue de playlists** | `/data/downtify_library.db` | Quels morceaux appartiennent à chaque playlist Spotify téléchargée |
| **Téléchargements de playlists** | `/data/downtify_library.db` | Téléchargements de playlists Spotify suivis et un cache de leurs listes de morceaux Spotify |
| **Index Navidrome** | `/data/downtify_library.db` | Identifiants de morceaux Navidrome par fichier |
| **Cache des métadonnées de la bibliothèque** | `/data/downtify_library.db` | Titre, artiste, tous les artistes crédités, album, artiste de l’album, numéro de piste, année, durée et taille de pochette par fichier pour `GET /tracks`, relus seulement quand la date de modification ou la taille d’un fichier change |
| **Passages d’amélioration** | `/data/downtify_library.db` | La file d’[amélioration de la bibliothèque](library-upgrade.md) et la date de dernière vérification de chaque morceau, pour qu’un passage survive à un redémarrage |
| **Cache d’analyse des chemins** | RAM, plus un instantané dans `/data/downtify_library.db` | Lignes consolidées de `GET /tracks`, listes de playlists et paires de chemins. Les routes de l’interface servent cet instantané sans parcourir le disque. Chaque téléchargement terminé est **fusionné dans l’instantané aussitôt** (pour qu’un nouvel artiste apparaisse sans attendre). Une suppression **retire aussitôt ces fichiers de l’instantané** (pour qu’un album disparaisse de la grille sans attendre). Un parcours complet de l’arborescence s’exécute en arrière-plan quelques secondes après que la file de téléchargement est inactive — pas sur une minuterie fixe. `GET /list?refresh=true` abandonne l’instantané et réanalyse maintenant. |
| **Éléments masqués** | `/data/downtify_library.db` | Les morceaux, albums et artistes qu’un admin a [masqués aux utilisateurs](users.md#hiding-from-users) |
| **Cache des pochettes** | `/data/cover_cache` (facultatif) | Images de pochette extraites pour `GET /cover` |

Les fichiers sont appariés malgré les déplacements par une **clé de contenu** — un hash du nom et de la taille du fichier. Déplacer un fichier vers un autre dossier conserve sa clé ; le remplacer par un autre fichier lui en donne une nouvelle.

## Paramètres → Bibliothèque

### Mettre les pochettes en cache sur le disque

Activé, Downtify garde les images de pochette extraites sous `/data/cover_cache`, pour que la Bibliothèque et le lecteur ne relisent pas les tags à chaque vignette. Peut être désactivé à tout moment ; cela ne coûte que de l’espace disque.

### Réparer les chemins

À utiliser après avoir **déplacé ou renommé des fichiers sur le disque** en dehors de Downtify, ou les avoir supprimés à la main.

1. Ouvrez **Paramètres → Bibliothèque → Réparer les chemins**.
2. Downtify analyse les dossiers de la bibliothèque et :
    - **met à jour les chemins** dans l’index des morceaux et le catalogue de playlists quand un fichier n’est plus où il était mais que le même fichier (même clé de contenu) est trouvé ailleurs ;
    - **supprime les entrées périmées** des fichiers qui n’existent plus ;
    - **indexe** les anciennes entrées enregistrées avant l’existence des clés de contenu ;
    - **fait suivre les [titres likés](liked-songs.md#keeping-likes-in-step-with-the-files)** vers leur nouvel emplacement.
3. Si **Générer le M3U** et/ou **Créer les playlists dans Navidrome** sont activés, les playlists concernées sont réécrites.

Cela ne s’exécute que lorsque vous appuyez sur le bouton (ou appelez `POST /api/library/reconcile`) — jamais selon un calendrier.

### Dossiers de musique existants

Pour lire une collection que Downtify n’a pas téléchargée, ajoutez les dossiers dans **Paramètres → Bibliothèque** et appuyez sur **Synchroniser les dossiers**. Les fichiers restent sur le disque ; les tags sont lus et les artistes appariés. Voir [Dossiers de musique existants](external-library.md).

::: warning
Réécrire une playlist supprime les fichiers de la bibliothèque dont les tags ne correspondent clairement pas au morceau Spotify pour lequel ils sont enregistrés — voir [slskd et Navidrome](slskd-navidrome.md#playlist-sync).
:::

::: info Suppressions vs déplacements
Supprimer des morceaux depuis la page **Bibliothèque** nettoie déjà le catalogue et réécrit en arrière-plan les fichiers M3U et les playlists Navidrome concernés ; il n’y a donc rien à réparer ensuite.
:::

## Page Bibliothèque

La page Bibliothèque a quatre onglets — **Albums**, **Artistes**, **Playlists** et **Titres** :

- **Albums, artistes et playlists** s’affichent en grille de pochettes ou en liste compacte (le choix est mémorisé), avec un filtre texte et un tri par ajout récent, nom, artiste, année ou nombre de morceaux. Les albums et artistes sont construits à partir des tags de chaque fichier (artiste de l’album, album, année), si bien qu’ils ne dépendent pas de l’organisation des fichiers sur le disque. Une compilation — artiste de l’album `Various Artists`, avec l’indicateur de compilation — reste un seul album sous Albums, tandis que ses morceaux sont sur les pages de leurs artistes. Un morceau tagué `Various Artists` sans cet indicateur (comme les anciennes versions taguaient tout morceau à plusieurs artistes, y compris un duo comme `Zé Neto & Cristiano`) est regroupé selon son premier artiste. Un morceau sans tag d’album apparaît sous Titres et son artiste, pas sous Albums.
- **Artistes** liste chaque artiste auquel un morceau appartient — son artiste de l’album, ou pour une compilation (ou un fichier sans artiste de l’album) son premier artiste. La page de cet artiste comprend aussi les morceaux où il est invité, marqués **Invité** ; son onglet Albums ne montre que ses propres albums (il est masqué s’il n’y en a aucun). Un nom qui n’est jamais crédité qu’à côté d’un autre n’a pas de page à lui : les tags peuvent nommer les membres d’un duo un par un (`Henrique; Juliano`, comme YouTube Music crédite certains duos et comme les écrivaient d’anciennes versions de Downtify), et une page par membre serait un artiste qui n’existe pas. **Various Artists** n’est pas listé : les morceaux d’une compilation sont sur les pages de leurs artistes, et l’album lui-même reste sous Albums.
- Partout où un morceau affiche ses artistes — listes de morceaux, l’écran En cours de lecture, le Finder et les lignes de titres populaires — chaque nom mène à la page de l’artiste dans la Bibliothèque, ou à une recherche quand la Bibliothèque n’a pas de page pour lui. Sur ces lignes, le nom de l’album mène aussi à cet album dans la Bibliothèque, ou à une recherche quand la Bibliothèque ne l’a pas. Découvrir et son Finder ne vous envoient jamais vers Rechercher : là, un artiste ou un album que la Bibliothèque n’a pas est du texte simple. Les artistes viennent du tag `ARTISTS` du fichier (voir [Plusieurs artistes et compilations](file-organization.md#several-artists-and-compilations)), donc un nom comme *Earth, Wind & Fire* n’est jamais coupé sur sa virgule ; un fichier sans ce tag voit son texte d’artiste découpé sur `;`, ` / ` ou `, `, sauf si ce texte est aussi l’artiste de l’album du fichier, ou si les noms obtenus forment l’artiste de l’album (`Henrique; Juliano` sur un album de `Henrique, Juliano`) — c’est alors un seul nom.
- **Playlists** sont les playlists téléchargées avec un [fichier M3U](m3u-export.md), les playlists que vous créez avec **Nouvelle playlist** (modifiables), plus les [téléchargements de playlists](slskd-navidrome.md#playlist-downloads) suivis qui n’ont pas encore de M3U. Les playlists importées de Spotify/YouTube restent en lecture seule tant que vous ne les [détachez](#detach-an-imported-playlist) pas. Les playlists que d’autres [partagent avec vous](users.md#sharing-playlists) sont listées sous la grille, à part des vôtres. Une fois que vous avez [liké](liked-songs.md) un morceau, *Titres likés* est listé en premier. Une playlist que vous avez créée utilise une mosaïque d’au plus quatre pochettes de morceaux ; les playlists importées gardent l’image enregistrée avec le M3U.
- **Titres** est un tableau triable (titre, album, format, date d’ajout, durée) avec un filtre texte, un filtre de format et des cases à cocher — cliquez sur l’une, puis Maj+clic sur une autre pour sélectionner une plage. Triez-le en cliquant sur un en-tête de colonne, ou avec le menu **Trier par** au-dessus du tableau (la seule façon sur téléphone, où les en-têtes sont masqués) : ajoutés récemment ou plus anciens d’abord, titre, artiste ou album de A à Z ou de Z à A, plus longs ou plus courts d’abord. Le choix est mémorisé.

Les morceaux d’une playlist ont le même menu **Trier par**, avec **Ordre de la playlist** (l’ordre propre de la playlist, par lequel elle commence) ajouté aux choix ; cliquer sur un en-tête de colonne fonctionne aussi. **Lire** et la liste de morceaux suivent l’ordre que vous avez choisi, et le choix est mémorisé, pour chaque playlist.

Ouvrir un album, un artiste ou une playlist affiche ses morceaux avec **Lire**, **Aléatoire** et **Ajouter à la file**. **Télécharger en ZIP** est un bouton sur la page d’une playlist et se trouve dans le menu **⋯** sur celle d’un album. Une playlist que vous avez créée a aussi **Ajouter des titres**, **Renommer** et **Partager…** (voir [partager des playlists](users.md#sharing-playlists)) ; une importée a **Partager…** et **Détacher de la source** (ci-dessous) ; la page d’une playlist téléchargée indique combien de ses morceaux sont téléchargés, liste les manquants avec **Télécharger les manquants**, et propose **Surveiller les nouveaux titres**. **Supprimer la playlist** est dans le menu **⋯** : les playlists importées suppriment l’audio ; une playlist que vous avez créée ne supprime que la playlist.

### Rechercher dans une playlist

Une longue playlist n’affiche que les titres visibles à l’écran, si bien que la recherche du navigateur (`Ctrl` + `F`) ne voit pas le reste. Le champ **Rechercher dans cette playlist**, au-dessus des titres, les parcourt tous : titre, artiste, album et nom de fichier, sans tenir compte de la casse ni des accents. Sur la page d’une playlist, `Ctrl` / `⌘` + `F` y place le curseur (appuyez de nouveau dans le champ pour la recherche du navigateur), et `Esc` le vide.

Juste à côté, des filtres restreignent la liste. Chacun indique combien de titres il contient et n’apparaît que s’il en a :

| Filtre | Affiche |
|--------|---------|
| **Tous** | Tous les titres téléchargés de la playlist |
| **Manquants** | Les titres de la playlist d’origine qui ne sont pas encore dans la bibliothèque (téléchargements de playlists Spotify), avec l’état de leur téléchargement — recherchés sur Spotify quand vous choisissez le filtre |
| **Échoués** | Les titres manquants dont le téléchargement a échoué, chacun avec un bouton pour réessayer — une fois **Manquants** consulté |
| **YouTube Music**, **Soulseek (slskd)**, **Deemix**… | Les titres récupérés par cette source. Downtify s’en souvient pour les titres téléchargés à partir de maintenant ; les plus anciens comptent comme **Source inconnue**, sauf les fichiers slskd laissés en place et les titres de vos propres dossiers |
| **Absents de Navidrome** | Avec la [synchronisation Navidrome](slskd-navidrome.md) activée, les titres que Downtify n’a pas encore associés à un titre de Navidrome |

La recherche et un filtre se combinent, et le nombre de titres affichés apparaît en dessous. Chaque titre garde son numéro dans la playlist, et le tri, la lecture et le menu de chaque titre portent sur ce qui est affiché.

### Détacher une playlist importée

Une playlist importée depuis un lien Spotify ou YouTube Music ne peut pas être modifiée, car Downtify la tient synchronisée avec sa source. Pour en mettre une en ordre — retirer un morceau qui n’y a pas sa place, en ajouter un qui l’a — ouvrez-la et choisissez **Détacher de la source**. Elle devient une playlist comme celles que vous créez : ses morceaux et son propriétaire restent tels quels, et vous obtenez **Ajouter des titres**, **Renommer** et la suppression de morceaux. En échange, le lien avec sa source est coupé : elle n’est plus mise à jour depuis Spotify ou YouTube Music, sa surveillance du [Suivi de playlists](playlist-monitor.md) (si elle en avait une) est retirée, et son suivi des « morceaux manquants » disparaît. Les morceaux déjà téléchargés ne sont jamais touchés, et son image reste jusqu’à votre première modification, où une mosaïque de ses morceaux la remplace. Détacher ne peut pas être annulé depuis l’application ; télécharger de nouveau le lien crée une nouvelle playlist importée.

Tous les comptes voient la même bibliothèque : ce qu’un admin [masque aux utilisateurs](users.md#hiding-from-users) est écarté pour eux, et un admin voit tout, avec un œil barré sur ce qui est masqué. Les admins masquent et affichent depuis le menu `…` d’un morceau, album ou artiste, ou depuis la barre de sélection dans **Titres**.

**Télécharger en ZIP** enregistre les morceaux sélectionnés sur l’appareil depuis lequel vous naviguez sous forme d’un seul ZIP, en conservant leur organisation en dossiers — pratique quand Downtify tourne sur un serveur domestique et que vous voulez un lot de morceaux en local. Combinez-le avec **Tout sélectionner** pour emporter tout ce que montre le filtre actuel. L’archive est construite pendant le téléchargement, donc rien n’est écrit sur le disque du serveur, et elle est plafonnée à 2000 morceaux par téléchargement.

## API

| Méthode | Chemin | Description |
|--------|------|-------------|
| `GET` | `/list?refresh=true` | Chemins de la bibliothèque, en contournant le cache d’analyse des chemins |
| `GET` | `/api/library/summary` | Compteurs de la page d’accueil et albums récents, sans la liste complète des morceaux |
| `GET` | `/api/library/albums` | Vignettes d’albums (compteurs + fichier de pochette), sans tous les morceaux |
| `GET` | `/api/library/artists` | Vignettes d’artistes (compteurs + fichier de pochette) pour la Bibliothèque et Découvrir |
| `GET` `POST` | `/api/library/visibility` | Admins : ce qui est masqué aux utilisateurs, et masquer / afficher des éléments |
| `POST` | `/api/library/lookup` | Lignes de la bibliothèque pour les morceaux de recherche/liens déjà téléchargés |
| `GET` | `/tracks` | Morceaux de la bibliothèque avec tags. `?playlist=`, `?artist=`, `?album=`, `?q=` et `?limit=` renvoient un sous-ensemble |
| `GET` | `/media/{path}` | Sert un fichier de la bibliothèque, y compris les chemins `slskd/…` et `ext/…` |
| `GET` | `/playlist-cover?file=…` | Sert la [pochette](playlist-cover-art.md) propre d’une playlist, indiquée comme `cover` par `/playlists` |
| `POST` | `/api/library/archive` | Prépare un ZIP des morceaux sélectionnés (renvoie un ticket à usage unique) |
| `GET` | `/api/library/archive/{token}` | Diffuse ce ZIP vers le navigateur |
| `DELETE` | `/api/library/playlist?playlist_name=…` | Supprime les morceaux, le M3U et le catalogue d’une playlist importée — ou seulement le M3U d’une playlist que vous avez créée |
| `POST` | `/api/library/playlists` | Crée une playlist modifiable vide |
| `POST` | `/api/library/playlists/tracks` | Ajoute ou retire des fichiers de la bibliothèque sur une playlist que vous avez créée |
| `POST` | `/api/library/playlists/rename` | Renomme une playlist que vous avez créée |
| `PUT` | `/api/library/playlists/visibility` | [Partage une playlist](users.md#sharing-playlists) qui vous appartient, en lecture seule |
| `POST` | `/api/library/playlists/copy` | Enregistre une copie d’une playlist que vous pouvez ouvrir comme une playlist modifiable à vous |
| `POST` | `/api/library/playlists/detach` | Transforme une playlist importée en playlist modifiable |
| `POST` | `/api/library/reconcile` | Répare les chemins de la bibliothèque, puis actualise les playlists M3U/Navidrome |
| `POST` | `/api/library/external/sync` | Lance une analyse en arrière-plan des dossiers de musique supplémentaires |
| `GET` | `/api/library/external/sync` | Synchro de dossiers supplémentaires en cours, ou le dernier journal terminé |
| `POST` | `/api/library/external/unmap` | Retire un dossier supplémentaire de la bibliothèque sans supprimer l’audio |
| `GET`/`POST` | `/api/library/upgrade…` | Analyse et répare ce qui est déjà téléchargé — voir [Améliorer la bibliothèque](library-upgrade.md#api) |

Voir la [référence de l’API](../api-reference.md#library) pour les formes des requêtes et des réponses.
