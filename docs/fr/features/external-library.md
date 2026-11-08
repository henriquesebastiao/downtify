---
icon: lucide/folder-plus
---

# Dossiers de musique existants

La Bibliothèque de Downtify est construite à partir des fichiers qu’il a téléchargés — plus les **dossiers supplémentaires** que vous lui indiquez. Ces dossiers ne sont pas copiés dans `/downloads`. Downtify lit les tags de chaque fichier (titre, artiste, album, numéro de piste, année), ignore les morceaux que vous avez déjà, et range le reste sous l’artiste correspondant dans la Bibliothèque et le lecteur.

## Ajouter des dossiers

1. Montez le dossier de l’hôte dans le conteneur (Docker). Le chemin que vous saisissez dans les Paramètres est celui **à l’intérieur du conteneur**, même règle que pour le [dossier de téléchargement de slskd](slskd-navidrome.md).
2. Ouvrez **Paramètres → Bibliothèque**.
3. Sous **Dossiers de musique existants**, ajoutez un ou plusieurs chemins (par exemple `/music/collection`). Le champ suggère des répertoires au fil de la saisie.
4. Cliquez sur **Enregistrer** si vous voulez les conserver sans synchroniser tout de suite, ou sur **Synchroniser les dossiers** — cela enregistre la liste et lance l’analyse immédiatement.

```yaml
services:
  downtify:
    volumes:
      - ./downloads:/downloads
      - /path/on/host/to/mp3s:/music/collection
      - downtify_data:/data
```

Le dossier dans les Paramètres est alors `/music/collection`.

::: warning Les fichiers restent où ils sont
La synchronisation ne copie pas de fichiers dans `/downloads`. Quand le dossier est accessible en écriture, elle **écrit** dans ces fichiers les mêmes extras qu’un téléchargement : paroles (et un fichier annexe `.lrc` — à côté du fichier ou dans le dossier choisi dans les Paramètres), une pochette si le fichier n’en a pas, et le genre d’iTunes lorsque c’est possible. Une synchronisation ultérieure écrit un fichier annexe manquant même si les paroles sont déjà dans les tags, et **déplace** un `.lrc` existant vers l’emplacement actuellement choisi dans les Paramètres quand ce fichier source est accessible en écriture. Supprimer un titre depuis la Bibliothèque supprime toujours ce fichier sur le disque.
:::

::: tip Montages en lecture seule
Montez la collection en `:ro` si vous ne voulez pas que Downtify réécrive les MP3. La synchronisation les indexe quand même. Mettez les fichiers `.lrc` dans le [dossier de paroles](lyrics.md#sidecar-lrc-file) (désactivez **Garder le .lrc à côté de l’audio**). Les pochettes manquantes sont enregistrées dans `/data/cover_cache` (le point de terminaison des pochettes de la Bibliothèque), pas dans le MP3. Le genre d’iTunes est stocké dans la base de métadonnées de la bibliothèque de Downtify, pas dans le fichier. Un `.lrc` déjà présent à côté d’un fichier en lecture seule est **copié** dans le dossier de paroles et laissé en place.
:::

## Ce que fait la synchronisation

1. Parcourt chaque dossier configuré à la recherche d’audio lisible (les mêmes formats que le reste de la bibliothèque : MP3, M4A, FLAC, OGG, WAV, AAC, OPUS).
2. Lit les tags intégrés. Un fichier sans titre/artiste se rabat sur `Artiste - Titre` dans le nom du fichier, comme les autres lignes de la bibliothèque.
3. **Ignore** un fichier quand la bibliothèque a déjà ce morceau (même artiste + titre, et durée à quelques secondes près lorsque les deux sont connues) — qu’il ait été téléchargé par Downtify ou qu’il vienne d’un autre dossier supplémentaire.
4. **Associe les artistes** aux noms déjà présents dans la bibliothèque (`The Beatles` et `Beatles` deviennent un seul artiste). Les noms qui ne correspondent à aucun artiste connu apparaissent comme un nouvel artiste. Les nouveaux artistes sont mis en file pour le même enrichissement de profil (photo/bio quand ces réglages sont activés) qu’un téléchargement terminé.
5. **Étiquette comme un téléchargement** quand le dossier est accessible en écriture. Pour chaque titre importé, il utilise les mêmes fournisseurs de paroles, la même recherche de pochette (seulement si le fichier n’a pas de visuel) et la même recherche de genre iTunes qu’un téléchargement. Les paroles vont dans le fichier ; un fichier annexe `.lrc` est écrit à côté de l’audio ou dans le [dossier de paroles](lyrics.md#sidecar-lrc-file) choisi dans les Paramètres. La pochette et le genre suivent les [Réglages de téléchargement](download-settings.md) (`download_cover_art`, `download_lyrics`). Sur un montage en **lecture seule**, le MP3 n’est pas réécrit : une pochette manquante est stockée dans `/data/cover_cache`, le genre est stocké dans le catalogue de la bibliothèque, et les fichiers `.lrc` vont dans le dossier de paroles si vous en avez choisi un. Les recherches s’exécutent par lots de **Téléchargements simultanés** ; une **Pause entre les recherches de synchro** dans Paramètres → Téléchargements et fichiers attend entre ces lots pour que les gros dossiers n’atteignent pas les limites de débit des fournisseurs.
6. Invalide le cache des chemins de la bibliothèque pour que la page de la Bibliothèque et le lecteur voient le résultat sans attendre le court TTL d’analyse habituel.

La synchronisation s’exécute **en arrière-plan**. Vous pouvez quitter les Paramètres ; y revenir pendant qu’elle travaille encore montre qu’elle synchronise toujours. Une fois terminée, les Paramètres affichent le **dernier journal de synchronisation** (importés / doublons / erreurs, plus des notes sur les paroles/pochettes).

Relancez **Synchroniser les dossiers** après avoir déposé d’autres fichiers dans ces dossiers. Enregistrer la liste des dossiers sans synchroniser les inclut quand même à la prochaine analyse de la bibliothèque (environ une minute, ou le prochain téléchargement/la prochaine suppression).

Retirer un dossier de la liste le **dissocie** : ces titres quittent la Bibliothèque et le lecteur, et les extras créés par Downtify (fichiers annexes `.lrc`, pochettes en cache) sont supprimés. Les fichiers audio sur le disque restent en place.

Les dossiers qui n’existent pas ou ne sont pas lisibles sont signalés après la synchronisation ; les autres sont analysés quand même.

## Chemins de la bibliothèque

Les fichiers des dossiers supplémentaires utilisent un chemin virtuel `ext/<id>/…` (l’id est un hash du chemin du dossier, ce qui permet de réordonner la liste). Le lecteur et `GET /media/…` utilisent ce chemin, comme `slskd/…` pour les fichiers Soulseek laissés en place.

Un dossier qui se trouve déjà **dans** `/downloads` (ou le dossier source de slskd) est ignoré ici — cette arborescence est déjà la bibliothèque.

## API

| Méthode | Chemin                        | Description                                                                      |
| ------ | ----------------------------- | -------------------------------------------------------------------------------- |
| `POST` | `/api/library/external/sync`  | Lance une analyse en arrière-plan. Un corps facultatif `{folders: ["/path", …]}` est d’abord enregistré. |
| `GET`  | `/api/library/external/sync`  | Tâche en cours, ou dernier journal terminé.                                      |
| `POST` | `/api/library/external/unmap` | Retire un dossier de la bibliothèque sans supprimer l’audio.                     |

Voir la [référence de l’API](../api-reference.md#post-apilibraryexternalsync) pour la forme de la réponse.

## Dossier principal de la bibliothèque

Choisissez **Paramètres → Bibliothèque → Dossier principal** pour privilégier l’un des
dossiers externes enregistrés. La valeur par défaut conserve le comportement existant.
L’artiste, le titre complet (version comprise) et l’album doivent correspondre ;
des métadonnées inconnues ne masquent pas un autre fichier. Une source sélectionnée peut représenter
un enregistrement dont l’autre copie comprend des intros ou des outros de clip.

C’est une préférence d’affichage, pas une migration. Les fichiers sources, les chemins de playlists
enregistrés, la propriété, les likes et les règles de visibilité ne sont ni réécrits ni supprimés.
Les badges de playlist sont combinés sur le représentant affiché ; les playlists enregistrées
explicitement lisent toujours leurs chemins d’origine. Les albums et versions différents du
dossier choisi restent séparés. Un dossier vide ou indisponible se rabat sur le reste de la bibliothèque.
Le retirer réinitialise la préférence.
