---
icon: lucide/star
---

# Top Songs

Certains artistes ont des catalogues énormes où seule une poignée de morceaux compte. Au lieu de récupérer les liens morceau par morceau, ou de télécharger une playlist « This is… » de plus de 50 morceaux pour les quelques titres que vous voulez vraiment, collez le lien de l’artiste lui-même et choisissez parmi ses morceaux les plus populaires.

## Comment l’utiliser

1. Collez un lien d’artiste dans la zone de recherche ou sur l’écran d’Accueil :
   - **Spotify** : `https://open.spotify.com/artist/…`
   - **YouTube Music** : `https://music.youtube.com/channel/UC…` ou `https://music.youtube.com/@handle`
   - **Deezer** : `https://www.deezer.com/artist/…`
2. La **page de l’artiste** s’ouvre avec sa photo et son nom, et liste ses sorties (albums, singles, EP et compilations, quand le service les a), de la plus récente à la plus ancienne sur Spotify et Deezer ; cliquez sur l’une pour voir ses morceaux ou la télécharger. À côté d’un bouton **Top Songs**, les artistes Spotify et YouTube Music ont aussi **Surveiller les nouvelles sorties** — pas ceux de Deezer, car le [Suivi de playlists](playlist-monitor.md) ne gère pas Deezer.
3. **Top Songs** ouvre la liste de ses morceaux les plus populaires, dans l’ordre où le service les classe. Pour Spotify et YouTube Music, un badge avec un œil indique combien de fois chaque morceau a été écouté, abrégé comme le fait votre langue (`1,5 bi` en portugais, `1.5B` en anglais) — celui de Spotify est vert, celui de YouTube Music est rouge. YouTube Music ne donne qu’un chiffre arrondi (`1.2B plays`), donc le sien est une approximation ; Downtify le lit dans la même requête YouTube Music qui liste les morceaux, plus une requête pour les nombres d’écoutes. Le classement « top » propre à Deezer n’a pas de chiffre public d’écoutes à afficher, ses morceaux sont donc listés sans badge. Les cinq premiers sont déjà cochés ; cochez-en d’autres ou décochez-en, puis appuyez sur **Télécharger la sélection**.

### Écouter des morceaux avant de les télécharger

Sur la page Top Songs, et sur la page qu’ouvre un lien d’**album** ou de **playlist** collé, chaque morceau se lit en entier : survolez sa ligne et le numéro devient un bouton de lecture (sur téléphone, le bouton de lecture est toujours là) ; appuyez dessus et le morceau est diffusé de YouTube directement dans le lecteur intégré. Appuyez de nouveau pour mettre en pause, ou sur le bouton d’une autre ligne pour changer. Un morceau déjà dans votre bibliothèque est lu depuis la bibliothèque, les autres morceaux téléchargés de la liste étant mis en file d’attente après lui.

Une diffusion est servie par ce serveur, jamais du navigateur directement vers YouTube : la ligne est résolue vers sa vidéo YouTube (la sienne, pour un morceau YouTube Music, sinon la correspondance de recherche la plus proche) et le serveur télécharge l’audio une fois dans son cache de diffusion, puis lit le fichier en cache (voir [`GET /api/stream/file`](../api-reference.md#get-apistreamfile)). Seul le serveur a besoin que YouTube soit joignable, et un titre soumis à une limite d’âge a besoin des cookies YouTube (voir [Cookies YouTube](youtube-cookies.md)) comme un téléchargement.

## Sources

| Source | Ce que « top songs » signifie | Morceaux listés |
|--------|------------------------|--------------|
| Spotify | Le rayon **Populaire** de l’artiste, les mêmes titres affichés en haut de sa page Spotify | Jusqu’à 10 |
| YouTube Music | La playlist **Top songs** de l’artiste, classée par popularité | Les 50 premiers |
| Deezer | Le classement **top** propre à l’artiste (le même rayon que `deezer.com` affiche sur sa page) | Les 50 premiers |

L’intégration publique de Spotify n’a pas de discographie ; Downtify lit donc les sorties dans la requête de discographie du lecteur web de Spotify, la même API non publique qu’il utilise pour les noms d’album. Si Spotify la modifie, Downtify se rabat sur une liste plus courte (tous les albums, mais seulement les dix singles les plus récents) et, à défaut, n’affiche aucune sortie. Les morceaux Spotify passent par le pipeline habituel métadonnées puis correspondance audio, avec leur nom d’album joint d’avance ; le téléchargement complète le reste (numéro de piste, année) comme pour n’importe quel morceau Spotify. Les morceaux YouTube Music sont épinglés à leur propre vidéo, comme tout autre lien YouTube Music. Deezer a un vrai point d’accès public de discographie, donc sa liste de sorties n’a pas besoin de repli ; ses morceaux passent par le même pipeline métadonnées puis correspondance audio que ceux de Spotify, avec un extrait d’aperçu de 30 secondes joint quand Deezer en propose un.

## Sur la page d’un artiste dans la Bibliothèque

Un artiste que Downtify connaît sur Spotify (voir [Photo, bannière et bio de l’artiste](artist-images.md)) obtient aussi un onglet **Top songs** sur sa page dans votre Bibliothèque, à côté de Titres et Les fans aiment aussi. Il liste les **5** premiers de ses morceaux populaires Spotify sous forme de liste minimale, comme les résultats de recherche, sous des en-têtes de colonnes (#, Titre, Album, durée) : numéro, pochette, titre, artiste, album et durée. Un morceau qui n’est pas dans votre bibliothèque a un bouton de **téléchargement** à droite (avec sa progression pendant le téléchargement) ; une fois téléchargé, il devient l’étiquette **Dans la bibliothèque**, et le morceau peut être lu comme sur la page d’un album : le numéro devient un bouton de lecture au survol, la pochette lance la lecture, et un double-clic ou un toucher aussi. En lire un met en file d’attente les autres morceaux téléchargés de la liste après lui, dans l’ordre du classement, et le morceau en cours est mis en évidence. Un morceau pas encore téléchargé est **diffusé en entier** : survolez sa ligne et, à la place du numéro, un bouton de lecture apparaît ; appuyez dessus (ou sur la pochette) et il est lu dans le lecteur intégré comme un morceau téléchargé (voir [Écouter des morceaux avant de les télécharger](#playing-songs-before-downloading)). Sous la liste, **Voir plus de titres populaires** ouvre cet artiste sur la page Top Songs décrite plus haut, où se trouvent la sélection, le commutateur **Créer la playlist** et le téléchargement de plusieurs à la fois. L’onglet n’apparaît que quand l’identifiant Spotify de l’artiste est connu, ce qui arrive la première fois que sa page est ouverte ; les morceaux sont demandés à ce moment-là, si bien que le compteur de l’onglet se remplit tout seul quelques secondes plus tard, où que vous soyez sur la page.

Lire la pochette, l’album et le nombre d’écoutes d’un morceau prend quelques secondes ; Downtify garde donc les cinq morceaux dans un fichier par artiste, `<downloads>/.metadata/ArtistTopSongs/<Artiste>.topsongs.json`, créé en arrière-plan la première fois que la page de l’artiste est ouverte. Il est considéré valide **7 jours** : ouvrir l’onglet lit le fichier aussitôt, et quand il est plus ancien, l’ancienne liste s’affiche tout de suite pendant qu’une nouvelle est récupérée derrière — la page la remplace d’elle-même en quelques secondes, sans déranger un morceau en cours de téléchargement ou de lecture. Le fichier ne contient que les morceaux, leurs pochettes, les liens des extraits et les nombres d’écoutes — jamais l’audio ni les images, et jamais le fait qu’un morceau soit dans votre bibliothèque, calculé en direct. C’est un cache : supprimez-le quand vous voulez, il est recréé.

## Créer une playlist

Le commutateur **Créer la playlist** de la page Top Songs est **désactivé** la première fois que vous ouvrez un artiste, et **activé** dès qu’une playlist nommée **Top Songs of {artist}** existe déjà dans votre bibliothèque, afin que les téléchargements suivants continuent à s’y ajouter. Basculez le commutateur et votre choix reste tant que vous êtes sur cette page. Désactivé, les morceaux se téléchargent comme n’importe quel autre morceau isolé : directement dans votre dossier de téléchargements, ou dans vos dossiers artiste/album quand l’[Organisation des fichiers](file-organization.md) est activée, sans dossier propre, sans M3U et sans photo d’artiste.

Activez-le et Downtify les traite comme une playlist nommée **Top Songs of {artist}**. L’endroit où elle va dépend de l’Organisation des fichiers :

| Classer par artiste / album | Morceaux | M3U et pochette |
|---|---|---|
| Les deux désactivés | Dans un dossier nommé `Top Songs of {artist}` | Dans ce même dossier |
| L’un ou les deux activés | Rangés selon ces réglages : `<Artiste>/`, `<Album>/` ou `<Artiste>/<Album>/`. Il n’y a pas de dossier `Top Songs of {artist}`. | Dans `Playlists/`, sous les noms `Top Songs of {artist}.m3u` et `.jpg` |

Dans les deux cas :

- la [playlist M3U](m3u-export.md) liste les morceaux **dans l’ordre du classement de l’artiste**, même si vous n’en avez coché que certains ;
- la photo de l’artiste est enregistrée à côté du M3U comme pochette, si **Enregistrer la pochette de la playlist** est activé (voir [Pochette de playlist](playlist-cover-art.md)). Il n’y a pas de réglage distinct pour cela.

## Limitations connues

::: warning Mélanger Spotify et YouTube Music pour le même artiste
Le M3U de **Top Songs of {artist}** est tenu à jour à partir du [catalogue de playlists](library-catalog.md), indexé par identifiants de morceaux Spotify. Si vous téléchargez les top songs d’un artiste depuis **Spotify** puis depuis **YouTube Music** (ou l’inverse), les fichiers du second lot se téléchargent correctement, mais la prochaine actualisation du M3U les retire du fichier de la playlist, car les identifiants YouTube Music n’entrent pas dans ce format. Ajouter d’autres morceaux de la **même** source n’est pas concerné.
:::

::: info Noms d’album des morceaux Spotify
La page d’artiste de Spotify n’indique pas de quel album vient un morceau. Downtify obtient les noms d’album et les nombres d’écoutes de la même API du lecteur Spotify qu’il utilise pour lire les playlists complètes : une requête de plus par artiste, plus une pour chaque album que cette requête ne liste pas. Cette API n’est pas publique ; si Spotify la modifie, la colonne **Album** reste vide pour les morceaux Spotify et le badge d’écoutes disparaît ; les morceaux se téléchargent quand même, mais Downtify doit alors retrouver l’album à partir de sa correspondance YouTube Music, ce qui échoue souvent, laissant le fichier sans tag d’album et, avec [Classer par album](file-organization.md) activé, dans un dossier d’album `unknown`. Les top songs de YouTube Music portent déjà leur album. Si les nombres d’écoutes cessent d’arriver, pour l’une ou l’autre source, le badge n’apparaît simplement pas.
:::

## API

Voir [`GET /api/artists/top_songs/url`](../api-reference.md#get-apiartiststop_songsurl) dans la Référence de l’API.
