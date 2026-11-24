---
icon: lucide/mic-vocal
---

# Paroles

Downtify cherche les paroles pendant le téléchargement d’un titre et les intègre au fichier, ainsi qu’un fichier annexe `.lrc` lorsqu’elles sont synchronisées dans le temps.

## Activer les paroles

Les paroles sont **activées par défaut**. Désactivez-les dans **Paramètres → Tags et paroles → Télécharger les paroles**.

## Fournisseurs et ordre d’essai

Les catalogues diffèrent : un morceau qu’un fournisseur ne connaît pas figure souvent chez un autre. Downtify tient donc une liste ordonnée de fournisseurs et les essaie un par un, en s’arrêtant au premier qui a quelque chose.

| Fournisseur | Paroles | Remarques |
|----------|--------|-------|
| **[LRCLIB](https://lrclib.net)** | Simples et synchronisées | Base de données communautaire gratuite, sans clé. Correspondance sur le titre, l’artiste principal, l’album et la durée. Si cela ne trouve rien de synchronisé, sa recherche est essayée aussi ; un résultat est retenu si le titre, l’artiste et la durée (à quelques secondes près) concordent. |
| **NetEase Cloud Music** | Généralement synchronisées | Grand catalogue, fort sur les sorties asiatiques et souvent aussi sur les occidentales. Correspondance sur le titre, l’artiste et la durée ; un résultat dont l’artiste est orthographié autrement (chinois traditionnel ou simplifié, par exemple) n’est accepté que lorsque le titre et la durée concordent tous deux. |
| **Kugou Music** | Synchronisées | Grand catalogue, fort sur les sorties chinoises et avec beaucoup de sorties occidentales. Correspondance comme pour NetEase ; la ligne de titre et les crédits d’écriture du début sont retirés. |

Dans **Paramètres → Tags et paroles → Fournisseurs**, vous pouvez faire glisser les fournisseurs dans l’ordre de votre choix, ou utiliser les flèches, et en désactiver. Au moins un reste activé ; pour cesser entièrement de chercher des paroles, utilisez l’interrupteur **Télécharger les paroles**. Un fournisseur ajouté par une mise à jour démarre désactivé si vous aviez déjà enregistré votre propre liste : activez-le là.

### Paroles synchronisées uniquement

**Paramètres → Tags et paroles → Paroles synchronisées uniquement** (désactivé par défaut) ne garde que les paroles horodatées : un fournisseur qui n’a que des paroles simples pour une chanson compte comme n’ayant rien, et le suivant est interrogé. [Améliorer la bibliothèque](library-upgrade.md) compte alors aussi comme sans paroles un titre qui n’a que des paroles simples. Les paroles synchronisées qu’un fichier a déjà comptent toujours : un fichier `.lrc` à côté, des paroles horodatées dans ses tags ou une trame ID3 `SYLT` (comme en ont parfois les fichiers d’autres applis). Avec le réglage activé, les paroles synchronisées trouvées remplacent les paroles simples : dans le fichier `.lrc` et dans le tag de paroles du fichier lui-même, pour que les lecteurs qui ne lisent que les tags les affichent aussi synchronisées. L’analyse indique aussi combien de titres sans paroles n’avaient que des paroles simples.

### Trouver des paroles pour les titres qui n’en ont pas

**Bibliothèque → Améliorer la bibliothèque → Analyser et trouver les paroles** cherche dans la bibliothèque les titres sans paroles et leur trouve des paroles aussitôt, avec une barre de progression. À la fin, il indique combien de titres ont reçu des paroles, pour combien aucune n’a été trouvée et combien ont échoué. Voir [Améliorer la bibliothèque](library-upgrade.md#while-it-runs).

::: info Et Genius, Musixmatch et AZLyrics ?
Ils ne sont pas disponibles, et Downtify ne les propose plus :

- **AZLyrics** interdit l’utilisation par des tiers de ses paroles dans la page elle-même.
- L’API de bureau de **Musixmatch** répond par un jeton vide sauf si vous avez des identifiants qu’elle ne remet pas aux applications.
- Le `robots.txt` de **Genius** interdit le point de terminaison de recherche nécessaire pour trouver la page d’un morceau.

Les réglages enregistrés qui les nomment encore continuent de fonctionner : les noms sont ignorés, et une liste qui ne contient plus rien d’autre revient aux fournisseurs par défaut.
:::

## Ignorer les fournisseurs qui n’avaient rien

Après une recherche, Downtify enregistre pour chaque morceau quels fournisseurs ont répondu et lesquels sont revenus à vide, dans `downtify_library.db` sous `/data`.

Un fournisseur qui n’avait rien pour un morceau n’est pas réinterrogé à son sujet pendant **30 jours**, afin que les retéléchargements et les grands passages sur la bibliothèque ne répètent pas les mêmes recherches infructueuses. Passé ce délai, il est réessayé, car les catalogues grandissent. Un fournisseur qui *avait* des paroles n’est jamais ignoré, si bien qu’un fichier retéléchargé les retrouve.

## Intégration

| Format | Tag de paroles simples | Tag de paroles synchronisées |
|--------|-----------------|------------------|
| MP3 | `USLT` (ID3) | `USLT` avec horodatages |
| FLAC | `LYRICS` (commentaire Vorbis) | `LYRICS` avec contenu LRC |
| M4A | `©lyr` | `©lyr` avec contenu LRC |
| OGG / OPUS | `LYRICS` (commentaire Vorbis) | `LYRICS` avec contenu LRC |

## Fichier annexe .lrc

Quand des paroles synchronisées sont disponibles, Downtify enregistre aussi un fichier `.lrc`. Par défaut il se trouve **à côté de l’audio**, avec le même nom de base. Dans **Paramètres → Tags et paroles**, vous pouvez le désactiver et choisir à la place un **dossier de paroles** (par défaut `/data/lyrics`). Ce dossier doit être **en dehors** de `/downloads`, de l’arborescence slskd et de tout dossier de musique supplémentaire — le chemin relatif de l’audio y est recréé (`Artiste/Album/titre.lrc`). Les lecteurs qui lisent des paroles externes (et le [lecteur intégré](player.md#now-playing)) trouvent toujours le fichier annexe. Modifier ce réglage et lancer **Synchroniser** sur un dossier supplémentaire copie les `.lrc` existants vers le nouvel emplacement ; le fichier source est supprimé quand cette arborescence est accessible en écriture, et laissé en place sur un montage en lecture seule. Un fichier annexe est écrit même si les paroles sont déjà intégrées dans les tags.

Supprimer le titre depuis la page de la Bibliothèque supprime le `.lrc` (à côté du fichier et dans le dossier dédié) en même temps que l’audio, de sorte que les paroles ne restent jamais sous forme de fichier orphelin.

## Ajuster la synchronisation

Les paroles trouvées en ligne sont parfois un peu en avance ou en retard sur l’audio téléchargé : une autre version du morceau, une intro plus longue. Pour corriger un morceau, lancez-le, ouvrez **Lecture en cours → Paroles** et appuyez sur le bouton chronomètre en haut à droite des paroles, **Ajuster la synchronisation des paroles** :

- **−** affiche les paroles plus tôt et **+** plus tard, un dixième de seconde par appui, jusqu’à une minute dans chaque sens. Les paroles suivent le nouveau timing tout de suite : vous pouvez essayer pendant la lecture.
- **Enregistrer** l’écrit dans les fichiers du morceau ; **Réinitialiser** revient au timing enregistré.

L’enregistrement réécrit les horodatages eux-mêmes, dans le fichier `.lrc` et, quand les tags du fichier contiennent des paroles synchronisées, dans ceux-ci aussi (trames `SYLT` des MP3 comprises). La correction se voit donc aussi dans les autres lecteurs qui lisent le `.lrc` ou les tags, et dans les applis. Un fichier en lecture seule garde ses tags ; seul le `.lrc` change. Une ligne `[offset:N]` dans un `.lrc` est intégrée aux horodatages à l’enregistrement, et le lecteur de Downtify la respecte en attendant.

Le bouton n’apparaît que pour les morceaux de la bibliothèque avec des paroles synchronisées. Tout utilisateur connecté peut les ajuster ; la modification apparaît dans le [journal d’activité](users.md#activity) comme **Synchronisation des paroles ajustée**. L’endpoint est [`POST /api/library/lyrics/offset`](../api-reference.md#post-apilibrarylyricsoffset).

## Quand rien n’est trouvé

Si aucun fournisseur n’a le morceau, le téléchargement se poursuit normalement — le fichier audio est enregistré sans paroles, et aucune erreur n’est levée.
