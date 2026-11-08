---
icon: lucide/shield-alert
---

# Marque de contenu explicite

Un morceau aux paroles explicites — un langage qui n’est pas destiné aux enfants — porte un petit **E** à côté de son titre, comme sur Spotify. Il apparaît partout où vous rencontrez le morceau, avant et après le téléchargement, et il reste avec le fichier.

## Où vous la voyez

- **Résultats de recherche, liens collés, Classements et l’Explorateur** — sur tout morceau que le service déclare explicite. Vous le savez avant de télécharger.
- **La Bibliothèque** — dans l’onglet Titres, sur les pages d’album, d’artiste et de playlist, et dans le sélecteur « ajouter des titres ».
- **Le lecteur** — à côté du titre dans la barre du lecteur, dans **Lecture en cours** et dans **À suivre**.

Survolez le **E** (ou laissez un lecteur d’écran le lire) pour voir « Explicite ».

## D’où vient la marque

C’est le service depuis lequel vous téléchargez qui décide : Spotify, YouTube Music et Deezer signalent chacun leurs morceaux explicites, et Downtify utilise ce que dit celui que vous avez choisi. Quand Downtify télécharge un morceau depuis YouTube Music, la marque décrit la **vidéo qu’il télécharge réellement** : si le morceau est explicite sur Spotify mais que Downtify a trouvé une version propre, le fichier n’est pas marqué ; et si Spotify le juge propre mais que la correspondance est explicite, il l’est.

Un morceau que le service ne signale pas ne reçoit aucune marque — ce qui n’équivaut pas à être certifié propre, et Downtify n’écrit jamais de marque « propre ».

## Dans le fichier

La marque est écrite dans les tags du fichier, comme le fait iTunes, afin que les serveurs multimédias et lecteurs qui la comprennent puissent aussi l’utiliser. Navidrome lit exactement ces tags comme statut explicite d’un titre.

| Format | Tag |
|--------|-----|
| MP3 | Cadre de texte `ITUNESADVISORY` (`TXXX`), valeur `1` |
| FLAC, OGG, OPUS | Commentaire `ITUNESADVISORY`, valeur `1` |
| M4A | Atome `rtng`, valeur `1` |

Les fichiers que vous aviez déjà sont lus de la même façon : tout ce qu’iTunes, MusicBrainz Picard ou un autre outil de tags a marqué `1` (ou l’ancien `4`) affiche aussi le **E**, y compris les morceaux de [dossiers supplémentaires](external-library.md).

::: info Morceaux téléchargés avant cette version
Les fichiers écrits par Downtify avant l’existence de la marque n’ont rien dans leurs tags, donc ils n’affichent pas de **E**, même si le morceau est explicite. Retéléchargez le morceau avec [Remplacer l’audio](replace-audio.md) ou depuis zéro pour le marquer. Un fichier garde sa marque quand [Améliorer la bibliothèque](library-upgrade.md) ou Remplacer l’audio le réécrit : la marque n’est qu’ajoutée, jamais effacée.
:::

La première fois que la Bibliothèque se charge après la mise à jour, Downtify relit les tags de chaque fichier pour chercher la marque, comme lorsqu’il a appris à afficher le codec et le genre. Sur une grosse bibliothèque sur un disque lent, cela prend un moment, une seule fois.

## Pour les développeurs d’applications

Le [contrat du client mobile](../mobile-client-contract.md) et la [référence de l’API](../api-reference.md#get-tracks) décrivent le champ `explicit` : `true` sur les titres explicites, absent sinon.
