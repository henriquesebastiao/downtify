---
icon: lucide/mic
---

# Podcasts

Abonnez-vous à une émission et ses nouveaux épisodes se téléchargent tout seuls — sans recoller un lien chaque semaine. Les podcasts sont traités de bout en bout différemment de la musique : un épisode est déjà un fichier audio fini, à une URL `<enclosure>` RSS, donc ni correspondance YouTube ni transcodage, juste un téléchargement et une écriture de tags.

Ouvrez **Podcasts** dans la barre latérale (sur téléphone : **Plus → Podcasts**).

Les abonnements appartiennent à celui qui s’abonne : chaque compte suit ses propres émissions (le même flux abonné deux fois atterrit dans deux dossiers), avec ses propres épisodes, positions de reprise et masquages. Un admin voit tous les abonnements.

## S’abonner

Collez l’un de ceux-ci dans la zone **Ajouter un podcast**, ou saisissez un nom pour chercher :

| Entrée | Ce qui se passe |
|-------|--------------|
| L’URL du flux RSS d’un podcast | Récupérée et analysée directement |
| Un lien d’émission Spotify (`open.spotify.com/show/…`) | Le nom de l’émission est lu sur Spotify, puis rapproché de son flux RSS public via l’annuaire de podcasts d’iTunes |
| Un lien d’épisode Spotify (`open.spotify.com/episode/…`) | Comme un lien d’émission, et l’épisode précis est mis en évidence si son titre peut être retrouvé dans le flux |
| Le nom d’une émission (texte libre) | Recherché dans l’annuaire de podcasts d’iTunes |

::: info Les émissions exclusives à Spotify ne peuvent pas être téléchargées
Une émission qui n’existe que sur Spotify (sans flux public) est signalée comme telle — Downtify ne devine pas et ne se rabat pas sur autre chose. Cherchez l’émission par son nom pour vérifier avant de la supposer exclusive.
:::

Avant de confirmer, vous choisissez :

- **Garder** — voir [Combien d’épisodes sont téléchargés](#how-many-episodes-are-downloaded) ci-dessous.
- **Intervalle** — la fréquence de vérification du flux pour de nouveaux épisodes, de toutes les 15 minutes à une fois par mois. Les abonnements sont vérifiés sur le même calendrier et par le même passage en arrière-plan que le [Suivi de playlists](playlist-monitor.md) — pour lui, ce n’est qu’un autre type de surveillance.

## Combien d’épisodes sont téléchargés

Le réglage **Garder** a deux comportements distincts, choisis une fois par émission :

- **Chaque nouvel épisode** — ne télécharge tout de suite que l’épisode le plus récent (s’abonner n’est pas une invitation à tirer tout le catalogue ancien d’une émission), puis télécharge les nouveaux épisodes qui apparaissent à chaque vérification. Rien n’est jamais supprimé automatiquement.
- **Les *N* derniers épisodes** — une fenêtre glissante. Après chaque vérification (y compris la première), les *N* épisodes publiés le plus récemment sont téléchargés, et tout épisode téléchargé plus ancien est supprimé pour faire de la place. Augmenter *N* plus tard rend ces épisodes supprimés à nouveau téléchargeables ; un épisode que vous avez vous-même retiré avec **Retirer le téléchargement** ne revient jamais ainsi — voir [Retirer des épisodes](#removing-episodes).

Modifiez **Garder** et l’intervalle à tout moment depuis la page de l’émission.

## Épisodes

La page d’une émission liste ses épisodes, du plus récent au plus ancien, chacun avec sa date de publication et sa durée. Un épisode non couvert par la politique de conservation apparaît quand même ici — touchez **Télécharger** pour prendre uniquement celui-là, aussi ancien soit-il.

### Retirer des épisodes

Le menu **⋯** de chaque épisode propose **Retirer le téléchargement**, qui supprime le fichier mais garde l’épisode dans la liste. Un fichier d’épisode peut disparaître de deux façons, avec des résultats différents :

| Comment | Revient automatiquement ? |
|-----|----|
| La conservation l’a écarté (un épisode plus ancien hors de la fenêtre « garder les N derniers ») | Oui, si vous augmentez de nouveau **Garder** |
| Vous avez choisi **Retirer le téléchargement** vous-même | Non — retéléchargez-le à la main quand vous voulez |

### Marquer comme écouté

Utilisez le menu **⋯** d’un épisode pour le marquer comme écouté ou non écouté à la main, ou laissez-le simplement se jouer jusqu’au bout — un épisode dans les dernières secondes de sa durée est marqué comme écouté tout seul.

## Lire des épisodes

Les épisodes se lisent dans le même lecteur intégré que la musique, avec quelques différences qui n’apparaissent que sur un épisode de podcast :

- **Reculer de 15 s / avancer de 30 s** à la place d’aléatoire et de répétition, qui ne s’appliquent pas à un seul épisode.
- **Vitesse de lecture** (0,75× à 2×), à côté de la minuterie de mise en veille.
- La **position de reprise** est enregistrée sur le serveur toutes les ~10 secondes de lecture et une fois de plus à la pause ; fermer l’onglet — ou ouvrir Downtify sur un autre appareil — reprend donc l’épisode près de l’endroit où vous l’avez laissé. La liste d’épisodes d’une émission affiche une indication « Reprendre à … » pour tout ce qui est à moitié écouté.

Le cœur (titres aimés) et « aller à l’album/l’artiste » ne s’appliquent pas aux épisodes et n’apparaissent pas sur l’un d’eux.

## Bibliothèque

Les podcasts ont leur propre place — ils n’apparaissent jamais comme morceaux, albums ou artistes dans la **Bibliothèque**, et un passage d’[Améliorer la bibliothèque](library-upgrade.md) les laisse entièrement de côté (un épisode n’a pas d’identifiant de morceau Spotify pour rafraîchir ses tags, ni de paroles distinctes à chercher).

Les fichiers d’épisodes restent sous le même volume de téléchargements, dans `Podcasts/<Émission>/<date> - <Épisode>.<ext>`, si bien que tout serveur multimédia pointé sur votre bibliothèque les voit aussi.

## Tags

Downtify écrit ce que les applications de podcast et les serveurs multimédias lisent déjà pour un épisode : le titre, l’émission comme album, l’auteur de l’émission comme artiste, l’année de publication, les numéros d’épisode/de saison, l’image propre de l’émission (la plus grande entre l’image du flux et celle d’iTunes, même idée que la [pochette des morceaux](download-settings.md#cover-art-resolution)) et la description de l’épisode comme commentaire. Les notes de l’émission sont stockées en texte brut — Downtify en retire le HTML au lieu de l’afficher.

## Bon à savoir

- **Pas de podcasts vidéo.** Un épisode dont la seule pièce jointe est un fichier vidéo est entièrement ignoré ; seul l’audio est pris en charge.
- **Pas de chapitres.** Les flux qui incluent des marqueurs de chapitre ne les ont pas encore dans Downtify.
- **Non reflété dans Navidrome.** Contrairement aux playlists, les abonnements aux podcasts ne sont pas poussés dans une bibliothèque Navidrome — les épisodes sont de simples fichiers que votre serveur multimédia voit déjà de lui-même.
- Se désabonner (**⋯ → Se désabonner**) supprime par défaut les épisodes téléchargés ; choisissez **Se désabonner, garder les épisodes téléchargés** pour laisser les fichiers en place.

## API

`POST /api/podcasts/resolve`, `GET /api/podcasts/search`, `POST /api/podcasts/subscribe`, `GET/PATCH/DELETE /api/podcasts/shows/{id}`, `GET /api/podcasts/shows/{id}/episodes`, `POST /api/podcasts/episodes/{id}/download`, `DELETE /api/podcasts/episodes/{id}` et `PUT /api/podcasts/episodes/{id}/playback`. Voir la [référence de l’API](../api-reference.md#podcasts).
