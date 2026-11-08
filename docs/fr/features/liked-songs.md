---
icon: lucide/heart
---

# Titres likés

Touchez le cœur d’un titre pour le liker. Dès qu’un titre est liké, Downtify tient à jour une playlist **Titres likés** avec tous ceux que vous avez likés, de sorte que vos favoris sont à un clic — dans Downtify comme dans tout serveur multimédia pointé sur votre bibliothèque.

Il n’y a rien à activer.

Les cœurs appartiennent à celui qui les a touchés : sur un serveur avec plusieurs comptes, chacun a ses propres titres likés (voir [Utilisateurs et connexion](users.md#your-library)). Le fichier de playlist sur le disque contient les cœurs des administrateurs ; les likes de tous les autres vivent dans la base de données de la bibliothèque et fonctionnent de la même façon dans les applications.


## Liker un titre

Le cœur se trouve à côté de chaque titre de votre bibliothèque — téléchargements et morceaux issus de [dossiers de musique existants](external-library.md) :

- dans les listes de titres — Bibliothèque, albums, artistes et playlists ;
- dans la [barre du lecteur](player.md#player-bar) (sur les écrans d’au moins 640 px de large) ;
- dans [En cours de lecture](player.md#now-playing), à côté du titre du morceau.

Touchez-le pour liker, touchez-le encore pour retirer le like. Il se remplit en vert et le changement est aussitôt sur le serveur : un cœur touché sur votre téléphone est donc aussi sur votre ordinateur — les onglets et appareils ouverts suivent d’eux-mêmes.

Seuls les titres de votre bibliothèque peuvent être likés. Un résultat de recherche pas encore téléchargé n’a pas de cœur ; téléchargez-le d’abord.

## La playlist

Le premier like crée la playlist, et un court avis propose de l’ouvrir. Elle est listée comme n’importe quelle autre playlist — dans la barre latérale, sur la page d’Accueil et dans **Bibliothèque → Playlists** —, mais toujours **en premier**, avec un cœur à la place de la pochette. Ses titres sont classés avec le plus récemment liké en haut.

Retirer le dernier like supprime à nouveau la playlist ; il ne reste pas de **Titres likés** vide qui traîne.

Le titre suit votre [langue](internationalization.md). Sur le disque, la playlist est un simple [fichier M3U](m3u-export.md) au nom fixe :

```
<downloads>/Playlists/Downtify Liked Songs.m3u
```

C’est pourquoi Jellyfin, Navidrome, Plex et consorts l’affichent aussi : ils lisent le même fichier. Le nom est réservé exprès. Les playlists Spotify appelées *Liked Songs* sont courantes, et une playlist téléchargée sous ce nom aurait sinon écrit dans le même fichier.

## Retirer tous les likes

Ouvrez la playlist, puis **⋯ → Retirer tous les likes**, et confirmez. Tous les cœurs sont effacés et la playlist disparaît.

::: info Vos titres restent
Retirer des likes ne supprime jamais d’audio. Seuls les cœurs et la playlist sont supprimés — les fichiers restent dans votre bibliothèque. C’est différent de supprimer une playlist téléchargée, qui supprime ses titres ; **Titres likés** n’est jamais traitée ainsi. Demander à la supprimer (dans l’application ou via l’[API](../api-reference.md#delete-apilibraryplaylist)) ne fait qu’effacer les likes.
:::

## Garder les likes en phase avec les fichiers

Un like suit le fichier auquel il a été donné :

| Ce qui arrive au fichier | Ce qui arrive au like |
|--------------------------|--------------------------|
| Vous supprimez le titre dans Downtify | Le like part avec lui, et la playlist est réécrite |
| Vous le déplacez et lancez [Corriger les chemins de la bibliothèque](library-catalog.md#fix-library-paths) | Le like suit le fichier vers son nouvel emplacement |
| Il disparaît hors de Downtify (disque démonté, suppression manuelle) | Le like est conservé, mais le titre est écarté de la playlist jusqu’à son retour |

Conserver le like d’un fichier manquant signifie qu’un disque débranché ne vous coûte pas vos cœurs. Si vous avez supprimé des fichiers à la main et voulez aussi effacer les likes, utilisez **Retirer tous les likes**, ou retirez le like des titres avant de les supprimer.

## Bon à savoir

- Les likes sont stockés dans la base de données de la bibliothèque (`downtify_library.db`, dans votre volume `/data`), pas dans les fichiers audio. Rien n’est écrit dans les tags d’un titre.
- La playlist n’est pas créée dans [Navidrome](slskd-navidrome.md) par Downtify. C’est un simple fichier M3U : ce qu’un serveur multimédia en fait dépend de la façon dont il lit les fichiers M3U.
- Le [fichier de playlist](m3u-export.md) est écrit même quand *Écrire des playlists M3U* est désactivé dans les réglages de téléchargement : la playlist est l’objet de la fonctionnalité.

## API

`GET /api/likes`, `PUT /api/likes` et `POST /api/likes/clear`, plus un indicateur `liked` sur [`GET /playlists`](../api-reference.md#get-playlists). Voir la [référence de l’API](../api-reference.md#likes).
