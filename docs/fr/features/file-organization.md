---
icon: lucide/file-headphone
---

# Organisation des fichiers

Un nouveau serveur organise les fichiers par artiste et par album (`Artiste/Album/…`) : **Classer par artiste** et **Classer par album** sont tous deux activés par défaut. Désactivez-les pour obtenir la structure à plat ci-dessous. Les serveurs configurés avant ce changement de valeur par défaut gardent le choix qu’ils avaient.

## Structure à plat (les deux désactivés)

Les titres seuls et les recherches YouTube vont directement à la racine du dossier de téléchargements. Les titres de playlists et d’albums vont dans un sous-dossier par playlist ou par album :

```
downloads/
├── My Playlist/
│   ├── My Playlist.m3u
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── Tame Impala - The Less I Know The Better.mp3
└── The Night Owls - R U Awake.mp3       ← titre seul
```

## Classer par artiste

Avec **Paramètres → Téléchargements et fichiers → Classer par artiste** activé (par défaut), tous les titres — y compris les téléchargements de playlists et d’albums — sont regroupés dans un sous-dossier portant le nom de l’artiste de l’album (voir [Plusieurs artistes et compilations](#several-artists-and-compilations)) :

```
downloads/
├── The Night Owls/
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── The Night Owls - R U Awake.mp3
├── Tame Impala/
│   └── Tame Impala - The Less I Know The Better.mp3
└── Playlists/
    └── My Playlist.m3u
```

Cette structure est compatible avec les serveurs multimédias (Jellyfin, Navidrome, Plex) et les gestionnaires de bibliothèque (Beets) qui attendent une organisation de dossiers `Artiste/Titre.ext`.

## Plusieurs artistes et compilations

Un morceau crédite souvent plusieurs artistes. Downtify les garde tous dans le tag **Artiste** du fichier, et écrit aussi chacun séparément dans un tag **ARTISTS** (`TXXX:ARTISTS` en MP3), pour qu’un lecteur n’ait jamais à couper un nom comme `Earth, Wind & Fire` sur sa virgule. Le dossier, lui, appartient à un seul artiste : l’**artiste de l’album**, ou pour une compilation le premier artiste du morceau.

- L’artiste de l’album est l’artiste que la source (Spotify, YouTube Music ou Deezer) crédite pour l’**album**, le même sur tous ses morceaux, et il est écrit dans le tag **Artiste de l’album**. Quand la source ne le dit pas, c’est le premier artiste du morceau.
- Un duo ou un groupe est un seul artiste. YouTube Music crédite certains groupes par leurs membres, un par entrée (`Henrique & Juliano` revient en `Henrique` et `Juliano`, sur l’album et sur chaque morceau — parfois dans l’autre ordre, `Mateus` et `Jorge` pour `Jorge & Mateus`). Chaque nom crédité pointe vers une chaîne YouTube Music ; quand le lien d’un membre mène à une chaîne au nom du groupe entier, formé des noms crédités à côté de lui, Downtify réunit ces noms en celui du groupe : le dossier et les tags **Artiste de l’album**, **Artiste** et **ARTISTS** disent tous `Henrique & Juliano`. Une vraie collaboration (chaque artiste sur sa propre chaîne) garde tous les artistes. Quand YouTube Music ne relie aucun membre à la chaîne du groupe, les noms restent séparés ; la Bibliothèque ne donne pourtant pas de page à un nom qui n’est jamais crédité qu’à côté d’un autre (voir [Catalogue de la bibliothèque](library-catalog.md#library-page)).
- Un invité ne change jamais rien. *The Girl Is Mine*, avec un invité sur *Thriller* de Michael Jackson, reste dans `Michael Jackson/Thriller/`, et le single *Lady Marmalade* (Christina Aguilera, Lil' Kim, Mýa, P!nk) va dans `Christina Aguilera/`.
- Seul un album que la source elle-même crédite à **Various Artists** (une bande originale, un « Now That's What I Call… ») est une compilation — à moins que vous ne [le marquiez vous-même](#marking-an-album-as-various-artists). Un morceau YouTube Music seul ne l’est jamais : YouTube Music range le même audio sous plusieurs sorties et peut afficher n’importe laquelle comme son album, souvent une compilation, donc seul le téléchargement d’un album YouTube Music entier compte. Ses morceaux reçoivent « Various Artists » comme artiste de l’album plus l’indicateur de compilation (`TCMP` en MP3, `COMPILATION` en FLAC/Ogg/Opus, `cpil` en M4A). Cela garde l’album entier dans Navidrome et les autres serveurs multimédias, qui regroupent les albums par ces tags plutôt que par dossier. Sur le disque, en revanche, **Classer par artiste** ne crée jamais de dossier `Various Artists` : chaque morceau va dans le dossier de son premier artiste.
- Les anciennes versions de Downtify taguaient **Various Artists** tout morceau à plusieurs artistes, sans l’indicateur de compilation. La Bibliothèque continue de lister un tel morceau dans l’album de son premier artiste, comme avant ; **Marquer comme Artistes divers** fait de l’album une vraie compilation.

```
downloads/
├── Christina Aguilera/
│   ├── Lady Marmalade/
│   │   └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
│   └── Moulin Rouge/                  ← de la bande originale (une compilation)
│       └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
└── David Bowie/
    └── Moulin Rouge/                  ← même bande originale
        └── David Bowie - Nature Boy.mp3
```

*Lady Marmalade* du single et celui de la bande originale de *Moulin Rouge* sont deux sorties, chacune rangée avec son propre album. Les morceaux de la bande originale sont répartis dans les dossiers de leurs artistes, mais tagués comme une compilation « Various Artists », si bien que la Bibliothèque et les serveurs multimédias montrent toujours *Moulin Rouge* comme un seul album.

### Marquer un album comme Artistes divers

Une source peut créditer une sortie à un seul artiste alors qu’elle appartient à plusieurs à parts égales — Deezer range le single *Lady Marmalade* sous Christina Aguilera seule. Un administrateur peut corriger cela depuis la page de l’album dans la Bibliothèque, avec le bouton **Marquer comme Artistes divers** à côté de **Ajouter à la file**.

- Chaque morceau de l’album reçoit « Various Artists » comme artiste de l’album et l’indicateur de compilation. Rien d’autre ne change dans les fichiers, et ils restent où ils sont (les morceaux d’une compilation sont de toute façon rangés sous leur premier artiste). Chaque fichier est réécrit via une copie de travail, garde sa date de modification et reste intact si la réécriture échoue.
- Dans la Bibliothèque, l’album est alors listé par **Various Artists** sous **Albums** (chaque morceau reste sur la page de son artiste), et la page de l’album le suit.
- Downtify se souvient de l’album : un de ses morceaux téléchargé plus tard reçoit les mêmes tags.
- Sur une compilation, le même bouton indique **Ne plus marquer comme Artistes divers** : il annule le marquage et remet l’artiste de l’album d’avant. Il fonctionne aussi sur un album dont la source a fait une compilation ; l’artiste de l’album devient alors l’artiste que la plupart de ses morceaux citent en premier, et les téléchargements suivants de cet album ne sont plus marqués.

Seuls les administrateurs voient le bouton. Les serveurs multimédias prennent le changement en compte à leur prochain scan de la bibliothèque.

## M3U et dossiers d’artistes

Quand *Classer par artiste* est activé et que vous téléchargez une playlist Spotify avec la génération de M3U également activée, le M3U est placé dans `<downloads>/Playlists/<nom-de-la-playlist>.m3u` plutôt que dans le sous-dossier de la playlist. C’est parce que les titres sont désormais répartis dans plusieurs dossiers d’artistes. Les chemins relatifs à l’intérieur du M3U se résolvent toujours correctement, où que vous montiez la bibliothèque.

## Changer le réglage

Le réglage prend effet immédiatement pour tous les **nouveaux** téléchargements. Les fichiers déjà sur le disque ne sont pas déplacés.

## Supprimer un titre nettoie les dossiers vides

Supprimer un titre depuis la page de la Bibliothèque supprime aussi son dossier de playlist, d’artiste ou d’album une fois vide — et continue de remonter dans les dossiers parents devenus vides (par exemple le dossier de l’artiste après la disparition de son dernier album), en s’arrêtant au dossier de téléchargements lui-même, qui n’est jamais supprimé. Un dossier qui contient encore autre chose — un autre titre, un `.m3u`, un `cover.jpg` encore utilisé — est laissé tranquille.

## Sélectionner et supprimer plusieurs titres à la fois

La liste des titres de la Bibliothèque a une case à cocher sur chaque titre, plus une case **Tout sélectionner** qui sélectionne tous les titres correspondant au filtre actuel (voir la [page Bibliothèque](library-catalog.md#library-page)). **Supprimer de la bibliothèque** dans la barre de sélection les supprime tous en une seule requête (`DELETE /delete/batch`, voir la [Référence de l’API](../api-reference.md)), avec le même nettoyage par titre (`.lrc`, `cover.jpg` orphelin, dossiers vides) que pour la suppression d’un titre à la fois.

Pour supprimer un album ou une playlist entière, ouvrez-le et choisissez **Supprimer** dans son menu **⋯**. Pour tout ce qui concerne un artiste, saisissez son nom dans le filtre de la liste des titres, puis **Tout sélectionner** et supprimez.
