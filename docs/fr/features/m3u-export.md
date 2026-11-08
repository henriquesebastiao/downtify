---
icon: lucide/list-music
---

# Export M3U

Downtify génère automatiquement un fichier de playlist `EXTM3U` standard chaque fois qu’une playlist Spotify est téléchargée — manuellement ou via la [Surveillance de playlists](playlist-monitor.md).

## Emplacement du fichier

| Situation | Chemin du M3U |
|-----------|---------|
| Playlist téléchargée normalement | `<downloads>/<nom-de-la-playlist>/<nom-de-la-playlist>.m3u` |
| Playlist téléchargée avec *Classer par artiste* activé | `<downloads>/Playlists/<nom-de-la-playlist>.m3u` |

Quand *Classer par artiste* est activé, les titres sont répartis dans plusieurs dossiers d’artistes ; le M3U est donc placé dans un répertoire central `Playlists/` plutôt que dans le sous-dossier de la playlist.

Les [titres likés](liked-songs.md) sont eux aussi écrits dans `Playlists/Downtify Liked Songs.m3u`, quelle que soit l’organisation et que *Écrire des playlists M3U* soit activé ou non.

## Chemins relatifs

Les chemins des titres dans le M3U sont écrits **relativement au fichier M3U lui-même**, et non en chemins absolus. Le même fichier fonctionne donc qu’il soit lu depuis le conteneur Downtify (`/downloads/…`) ou depuis un autre consommateur qui monte la même bibliothèque à une autre racine — par exemple Jellyfin sous `/nas/music/…`. Il suffit de pointer votre serveur multimédia sur le même point de montage de la bibliothèque, et la playlist apparaît comme un seul ensemble.

## Activer / désactiver

La génération de M3U se règle dans **Paramètres → Téléchargements et fichiers → Écrire des playlists M3U** (activée par défaut). La désactiver supprime entièrement la création du M3U ; le reste du flux de téléchargement ne change pas.

## Pochette

Juste sous ce réglage, **Enregistrer la pochette de la playlist** (activé par défaut) écrit l’image de pochette de la playlist à côté de son M3U, sous le même nom — avant les titres, pour que le dossier ressemble à la playlist dès le départ. Downtify affiche alors cette image pour la playlist au lieu d’une grille de pochettes de ses titres. Une playlist que vous créez dans la Bibliothèque reçoit une mosaïque d’au plus quatre pochettes de titres, écrite de la même façon. Voir [Pochettes de playlists](playlist-cover-art.md).

## Quand il est écrit

Le M3U est réécrit **après la fin du téléchargement de chaque titre**, si bien que le fichier de playlist grandit au fil du téléchargement au lieu d’apparaître d’un coup à la fin. Cela vaut pour les téléchargements de playlists et d’albums, les [imports CSV](library-import.md) et les passages de la [Surveillance de playlists](playlist-monitor.md#m3u-integration).

Ainsi, la playlist est lisible dès l’arrivée du premier titre, vous voyez la synchronisation à l’œuvre, et un seul téléchargement lent ou bloqué ne peut jamais empêcher le M3U — ni les titres déjà terminés — d’apparaître.

Une réécriture finale a lieu quand toute l’exécution est terminée. Elle résout chaque titre par rapport au système de fichiers (plutôt que par rapport à la liste en mémoire de ce que cette exécution a téléchargé), ce qui récupère aussi les fichiers d’exécutions précédentes et corrige tout ce qui a changé sur le disque en cours d’exécution.

Chaque écriture liste les titres dans **l’ordre de la playlist**, et non dans l’ordre où les téléchargements se sont terminés ; un M3U partiellement écrit est donc toujours correctement ordonné.

::: info Titres déjà sur le disque
Les titres téléchargés lors d’une exécution précédente restent dans le M3U tout du long — ils sont inclus dès la première écriture, pas seulement ajoutés par la dernière.
:::

## Régénération

Le M3U est régénéré à neuf à chaque exécution — recoller la même URL de playlist produit un fichier complet et ordonné, y compris les titres qui manquaient lors des exécutions précédentes.

Les titres dont le téléchargement a échoué ou qui n’avaient aucune correspondance sur YouTube Music sont ignorés en silence.

## Compatibilité

Le fichier généré utilise :

- L’encodage UTF-8, sans BOM
- Des fins de ligne LF
- Le format standard `#EXTM3U` / `#EXTINF`

Il est compatible avec Jellyfin, Navidrome, Plex, VLC, Kodi, Sonos et tout autre lecteur ou serveur multimédia qui lit les playlists M3U standard.

## Playlists que vous créez

**Bibliothèque → Playlists → Nouvelle playlist** écrit le même type de M3U sous `Playlists/`, avec une ligne supplémentaire `#EXTDOWNTIFY:manual` pour que Downtify la distingue d’une playlist Spotify/YouTube téléchargée. Vous pouvez la renommer, et ajouter ou retirer des titres (y compris ceux de [dossiers supplémentaires](external-library.md)). Supprimer cette playlist, supprimer un titre ou retirer un dossier supplémentaire met le M3U à jour ; l’audio n’est supprimé que lorsque vous supprimez le titre lui-même ou une playlist importée.

### Ajouter des titres à une playlist

Les administrateurs peuvent mettre des titres dans l’une de ces playlists, ou dans une nouvelle, depuis plusieurs endroits :

- **Le menu ⋯ d’un titre** (dans n’importe quelle liste de titres) → **Ajouter à la playlist**.
- **Sélectionnez plusieurs titres** dans la Bibliothèque et appuyez sur **Ajouter à la playlist**.
- **Le menu ⋯ d’un album** → **Ajouter à la playlist** ajoute tous les titres de l’album.
- **Le menu ⋯ d’un artiste** (sur la page de l’artiste) → **Ajouter à la playlist** ajoute tout ce que l’artiste a dans votre bibliothèque, album par album.

Chaque menu liste vos playlists et une entrée **Nouvelle playlist…** qui en crée une contenant déjà ces titres. Un titre que la playlist a déjà est ignoré, et la confirmation indique combien ont réellement été ajoutés (ou qu’ils y étaient tous déjà). Une playlist contient au plus 500 titres.
