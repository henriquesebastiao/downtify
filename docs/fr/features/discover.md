---
icon: lucide/compass
---

# Découvrir

Des artistes que vous n’avez pas encore, suggérés à partir de ceux que vous avez. Ouvrez **Découvrir** dans la barre latérale (sur téléphone : **Plus → Découvrir**). La zone de recherche en haut est le [Finder](finder.md), une recherche uniquement sur Deezer : chercher affiche ses résultats à la place des suggestions, et la vider les ramène.

Aucun compte ni clé d’API n’est nécessaire : les suggestions viennent de la liste publique d’« artistes similaires » de [Deezer](https://www.deezer.com/), qui fonctionne sans connexion.

## Comment les suggestions sont choisies

1. **Vos artistes sont pondérés.** Chaque artiste de votre bibliothèque compte un peu, et compte davantage pour chacun de ces critères, du plus au moins important :
    - combien de fois vous l’**écoutez** dans le lecteur de Downtify (les écoutes récentes comptent plus que celles d’il y a des mois),
    - combien de ses morceaux vous avez **aimés**,
    - combien de ses morceaux sont **dans votre bibliothèque**.

    Le poids s’aplatit en grandissant, si bien qu’un artiste avec 400 morceaux de discographie n’écrase pas un que vous écoutez tous les jours.
2. **Les 15 premiers sont recherchés sur Deezer**, qui renvoie pour chacun les artistes que ses auditeurs aiment aussi.
3. **Chaque artiste suggéré reçoit des points** de chacun de vos artistes qui le suggère — plus d’un artiste plus pesant, et plus il est haut dans la liste de Deezer. Un artiste vers lequel plusieurs de vos favoris pointent passe devant un seul mentionné par un seul d’entre eux. Sous chaque suggestion, *Parce que vous aimez …* nomme les artistes dont elle provient.

Les artistes déjà dans votre bibliothèque et ceux que vous avez [masqués](#hiding-artists) ne sont jamais suggérés.

Cliquez sur la photo d’une suggestion pour ouvrir l’artiste dans les colonnes du [Finder](finder.md) — son profil, toute sa discographie et les titres de n’importe quel album, le tout depuis Deezer. Le menu **⋯** d’une suggestion propose aussi **Trouver des titres** (les titres de l’artiste, affichés comme une recherche du [Finder](finder.md)), **Ouvrir sur Deezer** et **Pas intéressé**. La page affiche les 12 meilleurs artistes ; **Tout afficher** liste toutes les suggestions (jusqu’à 48).

## Albums et playlists

Sous les artistes, construits à partir d’eux :

| Section | Contenu |
|---------|--------------|
| **Albums pour vous** | L’album le plus connu de chacun des 12 premiers artistes suggérés |
| **Plus de vos artistes** | Jusqu’à deux albums populaires de chacun de vos 6 artistes les plus pesants qui ne sont pas encore dans votre bibliothèque |
| **Playlists pour vous** | L’essentiel de chaque artiste suggéré : la playlist **`100% <artiste>`** de Deezer (choisie par ses éditeurs), puis la **`This Is <artiste>`** de Spotify |

Elles arrivent en deux temps :

1. **Deezer d’abord.** La discographie de chaque artiste est lue sur Deezer : un album complet passe avant un single ou un EP et, parmi eux, celui qui a le plus de fans. Cette réponse est rapide et remplit les étagères.
2. **Puis Spotify.** Quelques secondes plus tard, les choix de Spotify pour les mêmes artistes (issus de sa recherche) sont ajoutés **à la fin** de chaque étagère — des espaces réservés montrent où ils apparaîtront pendant le chargement, et rien de ce qui est déjà sur la page ne bouge. Un album choisi par les deux services n’apparaît qu’une fois. Chaque album Spotify est cherché sur Deezer par artiste et titre ; quand Deezer l’a, il s’ouvre dans le Finder comme les autres.

Une petite icône dans le coin inférieur gauche de la pochette de chaque album et playlist indique de quel service elle vient :

- **Deezer** — un album s’ouvre dans les colonnes du [Finder](finder.md), avec ses titres prêts à être lus en entier et téléchargés.
- **Spotify** — Deezer n’a pas cet album ; il ouvre donc la même page qu’un lien Spotify collé.

Les playlists — celles de Deezer comme celles de Spotify — ouvrent toujours cette page, où vous pouvez **écouter leurs morceaux en entier** avant d’en télécharger (voir [Écouter des morceaux avant de les télécharger](top-songs.md#playing-songs-before-downloading)), puis tout télécharger, seulement les nouveaux morceaux, ou une sélection.

Tout est conservé une semaine, comme les artistes similaires, et la correspondance d’un album Spotify sur Deezer un mois (une semaine quand Deezer ne l’avait pas, au cas où il serait ajouté). Un album déjà dans votre bibliothèque (comparé par artiste et titre, donc `Dummy (Deluxe Edition)` compte comme `Dummy`) et une playlist déjà téléchargée sont exclus ; masquer un artiste retire aussi ses albums et ses playlists.

## Ce qui compte comme une écoute

Un morceau compte une fois par lecture, une fois que **la moitié** (ou **quatre minutes**, pour les morceaux longs) a réellement été jouée — sauter au milieu ne compte pas, et les morceaux de moins de 30 secondes ne comptent jamais. Les épisodes de podcast ne comptent pas.

Les écoutes sont conservées sur le serveur, donc ce que vous écoutez sur votre téléphone façonne aussi les suggestions sur votre ordinateur. Pour repartir de zéro, ouvrez **Artistes masqués → Effacer l’historique d’écoute** ; votre bibliothèque et vos morceaux aimés restent tels quels.

## Masquer des artistes

**⋯ → Pas intéressé** sur une suggestion masque définitivement cet artiste de Découvrir (le message qui apparaît propose **Annuler**). Pour masquer un artiste avant qu’il soit suggéré — un dont vous ne voulez simplement pas entendre parler — ouvrez **Artistes masqués** et tapez son nom.

La même liste affiche tous les artistes masqués, avec **Afficher à nouveau** pour en reprendre un. Les noms sont comparés sans tenir compte de la casse ni des caractères qu’un nom de fichier ne peut pas contenir, donc masquer `AC/DC` masque aussi `ACDC`.

## Bon à savoir

- **Les suggestions sont mises en cache une semaine.** Les réponses de Deezer et de Spotify pour chacun de vos artistes sont conservées 7 jours, donc rouvrir Découvrir est instantané et ne coûte pas une série de requêtes. **Actualiser** reclasse avec votre bibliothèque, vos mentions J’aime et vos écoutes les plus récentes ; un artiste dont la semaine est écoulée est de nouveau recherché.
- **Si Deezer est inaccessible** (ou limite les requêtes) pour certains de vos artistes, la page affiche quand même ce qu’elle a pu construire et indique que la liste est plus courte que d’habitude — réessayez plus tard. Une recherche échouée n’est jamais retenue comme « pas d’artistes similaires ».
- **Un artiste que Deezer ne connaît pas** n’ajoute simplement rien ; il n’est pas recherché de nouveau avant la fin de sa semaine.
- Seuls les *noms* d’artistes et d’albums quittent votre serveur (sous forme de recherches Deezer et Spotify). Rien de ce que vous écoutez n’est envoyé nulle part.

## API

Voir [Découvrir](../api-reference.md#discover) dans la référence de l’API.
