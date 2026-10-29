---
icon: lucide/eye
---

# Suivi de playlists

Le Suivi de playlists surveille vos playlists Spotify, Deezer (publiques) et YouTube Music préférées — et les artistes que vous suivez — et télécharge automatiquement les nouveaux morceaux et les nouvelles sorties dès qu’ils apparaissent, sans rien faire.

Il y a deux types de surveillance, chacun dans son onglet de la page Surveillance (**Playlists** et **Artistes**, à `/monitor/playlists` et `/monitor/artists`) :

| Surveillance | Collez | Télécharge |
|-------|-------|-----------|
| **Playlist** | L’URL d’une playlist Spotify, d’une playlist Deezer publique ou d’une playlist YouTube Music | Chaque morceau de la playlist, puis tout morceau ajouté plus tard |
| **Artiste** | L’URL d’un **artiste** Spotify, ou d’un artiste YouTube Music | Toute la discographie de l’artiste, puis chaque nouvelle sortie |

Chaque surveillance affiche sous son nom le lien qu’elle suit, et un badge **Spotify**, **Deezer** ou **YouTube Music** indiquant le service d’où elle a été ajoutée.

Voir [Suivi d’artistes](#artist-watch) pour savoir comment elles fonctionnent.

Les surveillances appartiennent à qui les a créées : chaque compte suit ses propres playlists et artistes (la même URL surveillée deux fois est balayée deux fois), et un passage attribue ses téléchargements au propriétaire de la surveillance. Un admin les voit toutes.

## Comment ça marche

Downtify garde une tâche d’arrière-plan qui s’exécute toutes les 60 secondes. À chaque passage, il vérifie si chaque surveillance activée doit être inspectée (selon son intervalle configuré). Quand une *playlist* est due, Downtify :

1. Récupère la liste complète des morceaux sur Spotify, Deezer ou YouTube Music
2. La compare à l’ensemble des morceaux déjà téléchargés
3. Télécharge les nouveaux morceaux avec le même pipeline qu’un téléchargement manuel
4. Met à jour le fichier M3U de la playlist (si la génération de M3U est activée)

La première vérification, qui démarre dès que vous ajoutez la surveillance, télécharge tout ce qui est déjà dans la playlist ; les suivantes ne téléchargent que ce qui a été ajouté depuis. Le « déjà téléchargé » est consigné dans une petite base SQLite (`downtify_monitor.db` sous `/data`), et non en consultant le dossier de téléchargements — si bien que déplacer un fichier téléchargé ailleurs sur le disque (dans votre propre organisation de bibliothèque, un autre disque, n’importe où) ne fait **pas** croire à Downtify qu’il manque, et il n’est pas retéléchargé à la vérification suivante.

Un passage distinct s’exécute toutes les heures et vérifie si le fichier de chaque morceau téléchargé est toujours là. Les fichiers réellement supprimés (par opposition à ceux que vous avez déplacés) sont oubliés à ce moment-là, si bien que le morceau redevient éligible au téléchargement — à la vérification suivante de la surveillance après ce passage horaire, pas instantanément.

Une surveillance n’est jamais vérifiée deux fois en même temps. Ajouter une surveillance lance sa première vérification immédiatement ; si cette vérification est encore en train de télécharger quand le passage planifié suivant arrive, le passage ignore la surveillance au lieu de lancer un second téléchargement chevauchant des mêmes morceaux.

## Ajouter une playlist

1. Ouvrez **Surveillance** dans la barre latérale (sur téléphone : **Plus → Surveillance**) et restez sur l’onglet **Playlists**
2. Collez l’URL d’une playlist :
    - Spotify : `https://open.spotify.com/playlist/…`
    - Playlist Deezer publique : `https://www.deezer.com/playlist/…` (les liens avec un préfixe de langue fonctionnent aussi)
    - YouTube Music : `https://music.youtube.com/playlist?list=…` (un lien `www.youtube.com/playlist?list=…` fonctionne aussi)
3. Choisissez un intervalle de vérification (de 15 minutes à une fois par mois)
4. Cliquez sur **Surveiller la playlist**

Chaque onglet a sa propre zone. Coller un lien d’artiste dans l’onglet Playlists (ou un lien de playlist dans Artistes) n’ajoute rien : la page indique de quel type de lien il s’agit et propose de le déplacer vers le bon onglet.

Vous pouvez aussi commencer à surveiller depuis la page d’une playlist : collez son lien dans la barre de recherche et utilisez **Surveiller les nouveaux titres** (ou **Surveiller les nouvelles sorties** sur un artiste YouTube Music). Les playlists téléchargées dans la Bibliothèque proposent la même action dans leur menu **⋯**. Les surveillances ajoutées ainsi utilisent un intervalle de 6 heures — modifiez-le sur la page Surveillance.

## Playlists Deezer

Les playlists Deezer publiques se surveillent comme les autres : collez le lien dans l’onglet **Playlists**, utilisez **Surveiller les nouveaux titres** sur la page de la playlist, ou choisissez **Surveiller les nouveaux titres** dans le menu **⋯** d’une carte de playlist des [Classements](charts.md). Aucun compte Deezer n’est nécessaire, et tous les morceaux sont récupérés, quelle que soit la longueur de la playlist. Les morceaux se téléchargent via vos [sources audio](download-settings.md) comme tout autre lien Deezer, et la playlist obtient son fichier M3U, sa pochette et son entrée dans la Bibliothèque comme une playlist Spotify — même avec les fichiers M3U désactivés, la Bibliothèque retient quels morceaux en font partie. Seules les playlists publiques peuvent être surveillées, et un lien d’**artiste** Deezer peut être téléchargé mais pas surveillé.

## Playlists YouTube Music

Utilisez une playlist YouTube Music pour des morceaux qui ne sont pas sur Spotify : remixes, lives, reprises, uploads de chaînes promotionnelles. Chaque morceau est téléchargé depuis **la vidéo exacte de la playlist**. Downtify ne le recherche pas de nouveau, donc ce que vous obtenez est ce que vous avez ajouté à la playlist.

- **Tous les morceaux sont récupérés**, quelle que soit la longueur de la playlist. Les vidéos supprimées ou privées sont ignorées.
- **Les morceaux que YouTube Music grise sont quand même téléchargés.** Les playlists créées par des convertisseurs et des importeurs (Soundiiz, TuneMyMusic et consorts) listent souvent des morceaux comme de simples uploads YouTube que YouTube Music affiche comme indisponibles et sans identifiant de morceau. Downtify retrouve la vidéo à partir de la miniature de l’entrée et la télécharge comme n’importe quelle autre, si bien qu’une telle playlist ne ressort pas vide. Une vidéo réellement supprimée ou rendue privée ne peut pas être téléchargée : quand YouTube Music la signale ainsi, elle est ignorée, et quand il ne donne qu’une miniature, le morceau apparaît en échec dans la file.
- **L’artiste et le titre viennent du titre de la vidéo.** Beaucoup d’entrées de playlist sont des uploads attribués à la chaîne qui les a publiés (par ex. `MrSuicideSheep`), et le vrai crédit est dans le titre, comme `Bronze Whale - Patterns`. Pour tout ce qui n’est pas une sortie de catalogue, Downtify sépare `Artiste - Titre` dans le nom de fichier et les tags. Il retire aussi des suffixes comme `(Official Video)` ou `[Lyrics]`. Une partie après le tiret qui nomme une version (`Yellow - Live at Glastonbury`) reste dans le titre. Les morceaux de catalogue (audio officiel, ou tout ce qui est classé sous un album) gardent l’artiste et le titre propres à YouTube Music.
- **Tout lien `list=` n’est pas une playlist.** Le lien `OLAK5uy_…` d’un album est toujours téléchargé comme un album. Un lien `watch?v=…&list=…` est le seul morceau qui jouait. Un mix radio (`list=RD…`) n’a pas de liste de morceaux fixe et ne peut pas être surveillé.

## Suivi d’artistes

Au lieu de construire une playlist par artiste, collez un lien d’artiste et Downtify suit tout son catalogue. Ajoutez-en un depuis l’onglet **Artistes** de la page Surveillance — collez l’URL, choisissez un intervalle, cliquez sur **Surveiller l’artiste**. Les surveillances d’artistes affichent un nombre de sorties au lieu d’un nombre de morceaux.

URL acceptées :

- Une URL d’artiste Spotify (`https://open.spotify.com/artist/…`)
- Une URL d’artiste YouTube Music, par chaîne (`https://music.youtube.com/channel/UC…`) ou par handle (`https://music.youtube.com/@HenriqueeJuliano`)

Un handle est résolu vers la chaîne de l’artiste quand vous ajoutez la surveillance, si bien que le même artiste collé par handle et par URL de chaîne est reconnu comme une seule surveillance. Un handle qui n’appartient pas à un artiste YouTube Music est rejeté.

À chaque passage, Downtify liste la discographie de l’artiste, la compare aux sorties qu’il a déjà traitées et télécharge chaque morceau de tout ce qui est nouveau. Un passage en régime établi coûte une seule requête — les listes de morceaux ne sont récupérées que pour les sorties qu’il n’a pas encore vues.

::: info Pourquoi la discographie vient de YouTube Music
L’intégration publique de Spotify expose le nom d’un artiste et un aperçu de ses morceaux les plus populaires, mais **pas** sa discographie — la lire exigerait des identifiants de l’API Spotify, que Downtify n’utilise délibérément pas. Un lien d’artiste Spotify est donc résolu vers son nom et apparié au même artiste sur YouTube Music, d’où l’audio est aussi récupéré. L’avantage : toute sortie que Downtify peut voir est une sortie qu’il peut réellement télécharger. Le compromis : le lien suit l’artiste YouTube Music qui porte exactement ce nom (casse et ponctuation mises à part), la meilleure correspondance de YouTube Music quand plusieurs le partagent. Pour un nom courant, vérifiez que la surveillance est bien l’artiste voulu, sinon collez directement l’URL de l’artiste YouTube Music. Un artiste Spotify dont aucun artiste YouTube Music ne porte exactement le nom ne peut être ajouté que de cette façon : Downtify ne devine pas.
:::

::: warning Le premier passage télécharge tout le catalogue ancien
Ajouter un artiste met en file **toutes** ses sorties, ce qui, pour un artiste prolifique, peut représenter des centaines d’albums et de singles. Définissez la **[Pause entre téléchargements](download-settings.md#delay-between-downloads)** avant d’ajouter un lot d’artistes, sinon vous serez très probablement limité en débit — ou activez **Nouvelles sorties uniquement** (ci-dessous) pour ignorer complètement le catalogue ancien.
:::

### Choisir ce qu’il faut télécharger

Sous la zone de lien de l’onglet **Artistes** (et dans la boîte de dialogue **Modifier** d’une surveillance), deux options décident de ce que télécharge une surveillance d’artiste :

| Option | Ce qu’elle fait |
|--------|--------------|
| **Télécharger : Albums / Singles / EP** | Seules les sorties des types cochés sont téléchargées. Les trois sont activés par défaut ; au moins un doit rester activé. Le type est l’étiquette propre de YouTube Music pour chaque sortie — une sortie qu’il n’étiquette pas compte comme un album. |
| **Nouvelles sorties uniquement** | Tout ce que l’artiste a déjà sorti quand la surveillance démarre est ignoré ; seul ce qui sort après est téléchargé. Désactivé par défaut. |

Comment elles se comportent quand vous les modifiez plus tard :

- **Activer un type** télécharge les sorties de ce type à la prochaine vérification de la surveillance — y compris son catalogue ancien, sauf si **Nouvelles sorties uniquement** est activé (alors seulement celles sorties depuis le début de la surveillance, ou depuis l’activation de l’option). Les sorties d’un type désactivé ne sont jamais enregistrées, donc rien n’est perdu à désactiver un type pour un temps.
- **Activer Nouvelles sorties uniquement** sur une surveillance existante enregistre comme ignoré tout ce qui est déjà sorti à ce moment ; les sorties déjà téléchargées restent telles quelles.
- **La désactiver** télécharge à la vérification suivante les sorties qu’elle avait ignorées (des types cochés).
- Enregistrer l’une ou l’autre option dans la boîte de dialogue **Modifier** vérifie la surveillance aussitôt, au lieu d’attendre sa prochaine vérification planifiée.

« Ignorer » les sorties existantes nécessite un regard réussi sur la discographie de l’artiste : si YouTube Music renvoie une liste vide (ce qui est plus souvent un raté qu’un artiste sans rien de sorti), rien n’est enregistré et la vérification suivante réessaie, si bien qu’une mauvaise réponse ne peut jamais faire télécharger le catalogue ancien plus tard. Pointer une surveillance **Nouvelles sorties uniquement** vers un autre artiste ignore de la même façon le catalogue ancien de cet artiste.

La liste de la Surveillance affiche les filtres d’une surveillance sous son lien quand ils ne sont pas ceux par défaut (par ex. **Albums** · **Nouveautés uniquement**).

Une sortie n’est enregistrée comme traitée que lorsque chacun de ses morceaux est réglé, si bien qu’un morceau qui échoue sur une erreur transitoire est réessayé au passage suivant au lieu d’être ignoré pour toujours. Les morceaux déjà téléchargés ne sont jamais récupérés deux fois.

Les surveillances d’artistes ne génèrent pas de fichiers M3U — les morceaux sont rangés selon vos réglages d’[organisation des fichiers](file-organization.md) plutôt que comme une playlist.

### Artistes suggérés

Sous la liste des surveillances d’artistes, l’onglet **Artistes** suggère des artistes à suivre, en deux listes :

| Liste | Qui y figure |
|-------|--------------|
| **D’après vos écoutes** | Les artistes que vous écoutez le plus : vos propres écoutes, celles que compte [Découvrir](discover.md). Les écoutes récentes comptent davantage : le poids d’une écoute est divisé par deux tous les 45 jours, si bien qu’un artiste beaucoup écouté l’an dernier passe derrière un artiste que vous écoutez chaque jour en ce moment. |
| **D’après votre bibliothèque** | Les artistes qui ont le plus de morceaux, puis d’albums, dans la bibliothèque que vous voyez. |

Les artistes que vous surveillez déjà (surveillances en pause comprises) et les noms de compilations comme **Various Artists** sont écartés. Chaque liste affiche 20 artistes à la fois ; **Afficher plus** charge les suivants. Les listes sont les vôtres, y compris pour un admin : les écoutes d’un autre compte n’y apparaissent jamais. Un artiste qu’un admin a masqué aux utilisateurs reste hors des listes d’un utilisateur, comme il reste hors de sa Bibliothèque.

Charger les listes ne lance aucune recherche. **Suivre** cherche le nom sur YouTube Music, où une surveillance d’artiste suit l’artiste :

- quand un seul artiste y porte ce nom, la surveillance est ajoutée tout de suite, avec l’intervalle et les options **Télécharger** / **Nouvelles sorties uniquement** choisis dans le cadre au-dessus ;
- sinon (homonymes, ou aucun artiste portant exactement ce nom), une fenêtre montre les artistes YouTube Music trouvés, chacun avec sa photo et un lien vers son profil. Choisissez-en un avec **Suivre cet artiste**, ou **Coller un lien** pour coller vous-même le lien de l’artiste dans le cadre au-dessus.

Les suggestions ne font que choisir l’artiste à surveiller : les morceaux se téléchargent toujours depuis vos [sources audio](download-settings.md), comme d’habitude.

### Depuis la page d’un artiste dans la Bibliothèque

La page d’un artiste dans la Bibliothèque (`/library/artist`) a un bouton **Surveiller l’artiste**, pour suivre un artiste que vous avez déjà sans chercher son lien. Il cherche le nom sur YouTube Music de la même façon que **Suivre** ci-dessus :

- quand un seul artiste y porte ce nom, la surveillance est ajoutée tout de suite. Elle est vérifiée chaque jour et a **Nouvelles sorties uniquement** activé, puisque la bibliothèque contient déjà sa musique plus ancienne ;
- sinon (homonymes, aucun artiste portant exactement ce nom, ou la recherche a échoué), une fenêtre montre les artistes YouTube Music trouvés, chacun avec sa photo et un lien vers son profil, plus un champ pour le lien d’un artiste Spotify ou YouTube Music. Les options **Télécharger** et **Nouvelles sorties uniquement** en haut s’appliquent à celui que vous suivez.

Une fois la surveillance ajoutée par le serveur, le bouton devient un lien vers **Surveillance**, où vous changez l’intervalle et les options ; un refus (l’artiste est déjà surveillé, par exemple) s’affiche dans la fenêtre. Il n’apparaît pas en [mode bibliothèque seule](library-only.md) ni sur la page **Various Artists**.

## Intervalles de vérification

| Étiquette | Minutes | Idéal pour |
|-------|---------|----------|
| Toutes les 15 min | 15 | Playlists mises à jour fréquemment |
| Toutes les 30 min | 30 | |
| Toutes les heures | 60 (par défaut) | La plupart des playlists |
| Toutes les 3 heures | 180 | |
| Toutes les 6 heures | 360 | |
| Toutes les 12 heures | 720 | |
| Chaque jour | 1 440 | Playlists qui changent lentement |
| Chaque semaine | 10 080 | Playlists mises à jour chaque semaine |
| Toutes les 2 semaines | 20 160 | |
| Chaque mois | 43 200 | Archives ou playlists rarement mises à jour |

Vous pouvez changer l’intervalle d’une playlist existante à tout moment depuis la carte de surveillance, sans la retirer ni la rajouter.

## Gérer les playlists surveillées

Chaque onglet liste uniquement son propre type de surveillance. Au-dessus de la liste :

- **Filtrer** — saisissez une partie d’un nom ou du lien (par ex. un identifiant de playlist) pour restreindre la liste
- **Tout / En pause** — n’afficher que les surveillances en pause
- **Tout vérifier** — vérifier toutes les surveillances actives de l’onglet courant
- Un bandeau avec le nombre de titres arrivés sur la période choisie (**7 jours**, **30 jours** ou **90 jours**) et, pour toutes les surveillances, combien de titres elles ont, la place qu’ils prennent (**Sur le disque**) et combien sont **Dans plusieurs surveillances** — voir [Activité et stockage par surveillance](#activity-and-storage-per-watch)

Sur chaque ligne :

- Interrupteur **Actif** — mettre en pause ou reprendre la surveillance sans la retirer
- **Vérifications** — à quelle fréquence elle est vérifiée
- **Vérifier maintenant** (↻) — la vérifier immédiatement, hors planning
- **Activité** — les nouveaux titres sur la période choisie, la moyenne par semaine et si ce rythme monte ou baisse ; cliquez pour ouvrir la page de la surveillance
- **Stockage** — la place des titres que seule cette surveillance a, plus le nombre qu’elle partage avec d’autres
- **Modifier** (✎) — voir et changer le lien, l’intervalle et l’état actif de la surveillance (voir [Modifier une surveillance](#editing-a-watch))
- **⋯** — **Activité et titres** (la page de la surveillance), pause/reprise, copier le lien, ouvrir l’original, ou **Arrêter la surveillance** (l’enregistrement est supprimé ; les fichiers téléchargés sont conservés)

**Activité** et **Stockage** sont des colonnes comme les autres : masquez-les ou redimensionnez-les depuis **Colonnes**.

### Modifier une surveillance

Cliquez sur le nom d’une surveillance ou sur son bouton **Modifier**. La boîte de dialogue affiche le lien complet suivi, avec **Copier le lien** et **Ouvrir l’original**, ainsi que la date d’ajout de la surveillance, sa dernière vérification et son nombre de morceaux ou de sorties. Vous pouvez changer :

- **Lien** — doit être du même type (une playlist pour une surveillance de playlist, un artiste pour une surveillance d’artiste) :
    - Un autre lien vers la **même** playlist ou le même artiste (par exemple avec un autre code de partage `?si=`, ou le lien YouTube Music au lieu de celui de `www.youtube.com`) ne met à jour que l’adresse enregistrée. Rien d’autre ne change.
    - Un lien vers une playlist ou un artiste **différent** y pointe la surveillance. La surveillance garde son intervalle et son état actif, mais prend le nouveau nom et repart de zéro : son historique de téléchargements ou de sorties est effacé et, si elle est active, elle est vérifiée aussitôt. Les morceaux déjà dans votre bibliothèque ne sont pas retéléchargés, et les fichiers de la cible précédente restent où ils sont.
    - Un lien vers quelque chose de déjà surveillé est refusé.
- **Vérifier toutes les** et **Actif**.

C’est pratique pour des playlists « vivantes » qu’on remplace : ouvrez la surveillance pour vérifier quelle playlist elle suit vraiment, et collez la nouvelle si elle a changé.

## Tri

Le contrôle **Trier par** au-dessus de la liste ordonne l’onglet courant par :

| Champ | Remarques |
|-------|-------|
| Date d’ajout | Par défaut — plus récentes d’abord |
| Nom | Alphabétique |
| Dernière vérification | Vérifiées le plus récemment d’abord ; jamais vérifiées en dernier |
| Fréquence | Moins fréquentes (intervalle le plus long) d’abord |
| Nombre de morceaux / sorties | Plus nombreux d’abord |
| Activité récente | Nouveaux titres sur la période choisie |
| Rythme moyen | Nouveaux titres par jour sur la période |
| Croissance du stockage | Place prise par les nouveaux titres de la période |
| Stockage propre | Place des titres qu’aucune autre surveillance n’a |
| Titres téléchargés | Titres sur le disque que la surveillance a elle-même téléchargés |

Le bouton à côté bascule entre l’ordre croissant et décroissant. Le choix est mémorisé dans le navigateur et ne change que la liste — pas l’ordre de vérification ni le planning.

## Choisir une heure de synchronisation quotidienne

Par défaut, une playlist vérifiée chaque jour (ou semaine / 2 semaines / mois) se synchronise à l’heure à laquelle elle a été ajoutée ou vérifiée pour la dernière fois — il n’y a pas d’heure du jour garantie. Pour fixer les synchronisations d’un jour ou plus à une heure précise (par ex. de nuit à 3 h plutôt qu’à n’importe quelle heure), définissez la variable d’environnement `DOWNTIFY_MONITOR_SYNC_TIME` avec `TZ`. Voir [Variables d’environnement](../getting-started/environment-variables.md#playlist-monitor) pour la référence complète.

- Ne concerne que les intervalles d’un jour complet ou plus — les intervalles plus courts (15 min – 12 h) ne sont pas concernés, car les ancrer sur une seule heure quotidienne casserait leur cadence.
- La toute première vérification après l’ajout d’une playlist s’exécute toujours immédiatement, quel que soit ce réglage.

## Enrichissement des métadonnées par morceau

Les entrées de l’intégration de playlist Spotify n’ont pas l’année de sortie et utilisent la pochette de la playlist au lieu de la pochette de l’album de chaque morceau. Downtify récupère de nouveau chaque nouveau morceau individuellement pour obtenir la bonne pochette et la bonne année avant de télécharger — en retombant sur les données au niveau de la playlist si la récupération par morceau échoue. Les entrées de playlist YouTube Music sautent cette étape : chacune porte déjà les métadonnées de sa propre vidéo.

## Intégration M3U

Le M3U de la playlist est réécrit **après la fin de chaque morceau**, si bien qu’il grandit au fil du téléchargement du passage au lieu d’apparaître seulement quand tout est terminé. La playlist est lisible dès le premier morceau, et un téléchargement lent ou bloqué plus loin dans la liste ne retient jamais les morceaux déjà arrivés. Une réécriture finale à la fin du passage résout tout de nouveau par rapport au système de fichiers.

Les téléchargements manuels de playlists/albums et les imports CSV se comportent de même. Voir [Export M3U](m3u-export.md#when-it-is-written) pour les détails.

Avec [Enregistrer la pochette de la playlist](playlist-cover-art.md) activé, la pochette est récupérée une fois par passage qui a des morceaux à télécharger — avant le premier d’entre eux, pour que le dossier ressemble à la playlist pendant qu’il se remplit. Un passage qui ne trouve rien de nouveau ne la récupère pas de nouveau.

## Ce qui arrive aux morceaux qui quittent une playlist

Les playlists « vivantes » (le *Top 50* de Spotify, *Découvertes de la semaine*, classements éditoriaux) changent chaque semaine. Downtify traite une surveillance comme une **source de nouvelle musique**, jamais comme quelque chose qui gouverne ce que vous gardez :

- **Les fichiers audio téléchargés ne sont jamais supprimés par une surveillance.** Ni quand un morceau quitte la playlist, ni quand il quitte toutes les playlists que vous surveillez, ni quand la playlist elle-même rétrécit, ni quand vous appuyez sur **Arrêter la surveillance**.
- **Seule la playlist suit la playlist.** À chaque passage, le [fichier M3U](m3u-export.md) est réécrit à partir des morceaux actuels de la playlist, dans son ordre actuel, si bien qu’un morceau sorti disparaît du M3U. Son fichier reste dans le dossier, et reste dans votre bibliothèque, consultable et lisible — y compris via Navidrome, Jellyfin ou tout ce qui est pointé sur le même dossier.
- **Un morceau qui n’est dans aucune playlist reste un morceau.** Rien ne balaie les fichiers « orphelins ».

Cela fait d’une playlist de classement un flux de découverte utilisable : de nouveaux morceaux arrivent automatiquement, et ce qu’ils laissent derrière eux s’accumule dans votre bibliothèque.

```
Top 50 - USA        →  new song appears   →  Downtify downloads it
                    →  song drops out     →  M3U updated, file kept
```

Les seules choses qui suppriment de l’audio sont celles que vous demandez explicitement : **Supprimer** sur un morceau ou une sélection dans la Bibliothèque, supprimer une playlist depuis la Bibliothèque (ce qui supprime bien ses morceaux — après confirmation), ou retirer vous-même des fichiers du système de fichiers.

Pour retirer de la playlist un titre dont vous ne voulez pas, et qu’il n’y revienne à aucune vérification, masquez-le : voir [Titres masqués d’une playlist](hidden-playlist-songs.md). Son fichier reste dans votre bibliothèque.

::: info Supprimer une surveillance vs supprimer une playlist
**Arrêter la surveillance** (dans le menu ⋯ de la surveillance) ne fait qu’oublier la surveillance : rien ne change sur le disque. **Supprimer** sur une playlist de la page **Bibliothèque** est l’action destructrice — elle retire les morceaux de cette playlist, son M3U et son entrée de catalogue.
:::

Si un fichier disparaît vraiment — vous l’avez sorti du dossier de téléchargements ou supprimé à la main —, un passage horaire s’en aperçoit et oublie l’enregistrement qu’en avait Downtify, si bien que la vérification suivante d’une surveillance qui liste encore le morceau le télécharge de nouveau. Un fichier simplement *déplacé* dans le dossier de téléchargements est toujours retrouvé et n’est pas retéléchargé.

## Stockage

L’état du moniteur est stocké dans une base SQLite à `/data/downtify_monitor.db`. La base consigne :

- Chaque surveillance (type, identifiant de playlist Spotify ou YouTube Music ou identifiant de chaîne YouTube Music, nom, URL, intervalle, état activé, heure de la dernière vérification). Le fait qu’une surveillance soit Spotify ou YouTube Music se lit dans son URL enregistrée, donc aucune colonne supplémentaire n’est nécessaire.
- Chaque morceau téléchargé avec succès par surveillance, y compris le nom de fichier sur disque
- Pour les surveillances d’artistes, les sorties déjà traitées, de sorte qu’un passage ne récupère les listes de morceaux que pour les sorties réellement nouvelles — y compris celles que **Nouvelles sorties uniquement** a ignorées, marquées comme telles pour que la désactivation puisse les ramener — plus les types de sorties de la surveillance et si elle est en nouvelles sorties uniquement
- Chaque morceau ajouté par une surveillance (`watch_events`) : quand, le fichier, quel fournisseur audio l’a récupéré, si la surveillance l’a téléchargé ou l’a trouvé déjà dans la bibliothèque, et s’il est venu avec sa première vérification. Ces lignes gardent l’id, le nom et le propriétaire de la surveillance tels qu’ils étaient, et lui survivent : arrêter ou rediriger une surveillance les conserve, ses titres disent donc toujours d’où ils viennent
- Les morceaux que chaque surveillance n’arrive toujours pas à télécharger (`watch_failures`), jusqu’à ce que l’un réussisse, quitte la playlist ou que la surveillance soit redirigée

Les bases créées avant le Suivi d’artistes sont migrées automatiquement au démarrage ; les lignes existantes continuent de fonctionner comme des surveillances de playlists. Les morceaux enregistrés avant que Downtify garde l’historique ci-dessus y sont ajoutés une fois, au premier démarrage, avec un résultat inconnu (**Avant le suivi**) — ceux du premier jour d’une surveillance comptent comme sa première vérification.

## Activité et stockage par surveillance

La page Surveillance et la page de chaque surveillance (**Activité et titres** dans le menu **⋯** d’une surveillance, ou un clic sur son **Activité**) indiquent quelles surveillances font grossir votre bibliothèque — pratique avec beaucoup de surveillances, ou pour comprendre pourquoi un mix généré a apporté des titres inattendus.

**Ce qui compte comme activité.** Seuls comptent les titres qu’une surveillance a vraiment ajoutés : ceux qu’elle a téléchargés. Ceux qu’elle a trouvés déjà dans votre bibliothèque (une autre surveillance, ou un téléchargement de votre part, les avait) comptent à part comme **Déjà dans la bibliothèque**, tout comme ce qu’apporte sa première vérification, quand elle télécharge tout ce que la playlist contenait déjà. Une playlist statique paraît donc inactive même si sa première vérification a téléchargé 300 titres, et un mix qui ajoute 15 titres par semaine affiche 15 par semaine. Les morceaux enregistrés avant que Downtify garde cet historique comptent comme ajoutés, et la page indique combien il y en a.

Sur la période choisie (7, 30 ou 90 jours, mémorisée dans le navigateur) une surveillance affiche :

| Nombre | Ce que c’est |
|--------|------------|
| Nouveaux titres | Les titres ajoutés sur la période |
| Par jour / Par semaine / Par mois | Le rythme moyen sur la période — ou depuis le début de la surveillance, si c’est plus récent |
| Tendance | Si le rythme monte (**En ajoute plus ces derniers temps**), baisse (**En ajoute moins ces derniers temps**) ou reste stable, d’après les nouveaux titres par jour (7 jours) ou par semaine (30 et 90 jours) ; **Trop récente pour le dire** tant qu’il y en a moins de trois à comparer |
| Croissance du stockage | Place des nouveaux titres de la période encore sur le disque |

**Stockage.** Un fichier est stocké une seule fois, quel que soit le nombre de surveillances qui l’ont, et les chiffres en tiennent compte : **Uniquement ici** est la place des titres qu’aucune autre surveillance n’a (ce que libérerait l’arrêt de la surveillance et la suppression de ses titres), **Partagés** les titres que d’autres surveillances ont aussi, et le bandeau de la page Surveillance compte chaque fichier une fois. Les surveillances des autres comptes comptent pour savoir si un fichier est partagé, mais ne sont pas nommées.

La page d’une surveillance affiche aussi :

- **Titres sur le disque**, **Téléchargés par elle**, **Déjà dans la bibliothèque** et **En échec** — comment ses titres sont arrivés, et combien échouent encore au téléchargement (listés plus bas, avec le nombre d’essais et la dernière erreur)
- **D’où vient l’audio** — YouTube Music, YouTube, Soulseek (slskd) ou Deemix, par titre sur le disque
- **Titres de cette surveillance** — tous ses titres, du plus récent au plus ancien, y compris ceux qui ont depuis quitté la playlist, avec des filtres (**30 derniers jours** — ou la période choisie —, **Téléchargés par elle**, **Déjà dans la bibliothèque**, **Avant le suivi**). Sélectionnez des titres pour les écouter, les mettre en file d’attente, les ajouter à une playlist, les télécharger en ZIP ou les supprimer — par exemple pour faire le ménage dans ce qu’un mix a apporté la semaine passée
- **Ouvrir dans la bibliothèque** (la page de la playlist, ou celle de l’artiste pour une surveillance d’artiste), **Ouvrir l’original** et **Vérifier maintenant**

L’id de la surveillance (`#12`) est affiché à côté de son nom, pour distinguer deux surveillances du même lien — deux comptes qui suivent la même playlist, par exemple.

## D’où vient un titre

**D’où il vient** dans le menu d’un titre (partout dans la bibliothèque) indique quelle surveillance l’a téléchargé en premier, quand et avec quel fournisseur — **Première vérification** s’il est venu avec la première vérification — et liste toutes les surveillances qui l’ont maintenant, chacune avec son id, son propriétaire (pour un admin), quand elle a reçu le titre et comment : **L’a téléchargé**, **Déjà dans la bibliothèque** ou **Avant le suivi**. C’est un seul fichier : les surveillances qui partagent un titre pointent toutes vers la même copie.

De là, **Activité et titres** ouvre la page de la surveillance et **Ouvrir dans la bibliothèque** sa playlist. Une surveillance arrêtée, ou qui suit désormais un autre lien, reste nommée comme origine des titres qu’elle a téléchargés. Pour un titre enregistré avant que cet historique existe, c’est la première surveillance qui l’a enregistré qui est affichée, marquée **Probablement**. Un titre qu’aucune surveillance n’a téléchargé (un que vous avez téléchargé vous-même) l’indique.

Un utilisateur voit ses propres surveillances par leur nom ; un titre téléchargé par la surveillance d’un autre compte n’indique que cela, et quand.
