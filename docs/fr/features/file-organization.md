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

Avec **Paramètres → Téléchargements et fichiers → Classer par artiste** activé (par défaut), tous les titres — y compris les téléchargements de playlists et d’albums — sont regroupés dans un sous-dossier portant le nom de l’artiste principal :

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

## M3U et dossiers d’artistes

Quand *Classer par artiste* est activé et que vous téléchargez une playlist Spotify avec la génération de M3U également activée, le M3U est placé dans `<downloads>/Playlists/<nom-de-la-playlist>.m3u` plutôt que dans le sous-dossier de la playlist. C’est parce que les titres sont désormais répartis dans plusieurs dossiers d’artistes. Les chemins relatifs à l’intérieur du M3U se résolvent toujours correctement, où que vous montiez la bibliothèque.

## Changer le réglage

Le réglage prend effet immédiatement pour tous les **nouveaux** téléchargements. Les fichiers déjà sur le disque ne sont pas déplacés.

## Supprimer un titre nettoie les dossiers vides

Supprimer un titre depuis la page de la Bibliothèque supprime aussi son dossier de playlist, d’artiste ou d’album une fois vide — et continue de remonter dans les dossiers parents devenus vides (par exemple le dossier de l’artiste après la disparition de son dernier album), en s’arrêtant au dossier de téléchargements lui-même, qui n’est jamais supprimé. Un dossier qui contient encore autre chose — un autre titre, un `.m3u`, un `cover.jpg` encore utilisé — est laissé tranquille.

## Sélectionner et supprimer plusieurs titres à la fois

La liste des titres de la Bibliothèque a une case à cocher sur chaque titre, plus une case **Tout sélectionner** qui sélectionne tous les titres correspondant au filtre actuel (voir la [page Bibliothèque](library-catalog.md#library-page)). **Supprimer de la bibliothèque** dans la barre de sélection les supprime tous en une seule requête (`DELETE /delete/batch`, voir la [Référence de l’API](../api-reference.md)), avec le même nettoyage par titre (`.lrc`, `cover.jpg` orphelin, dossiers vides) que pour la suppression d’un titre à la fois.

Pour supprimer un album ou une playlist entière, ouvrez-le et choisissez **Supprimer** dans son menu **⋯**. Pour tout ce qui concerne un artiste, saisissez son nom dans le filtre de la liste des titres, puis **Tout sélectionner** et supprimez.
