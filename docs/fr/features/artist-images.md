---
icon: lucide/image
---

# Photo, bannière et bio de l’artiste

Downtify peut afficher une vraie photo de profil, une bannière et une biographie pour chaque artiste de votre Bibliothèque, au lieu d’une initiale générée et d’aucun texte. Cela se remplit tout seul la première fois que vous ouvrez la page d’un nouvel artiste, ou dès que l’un de ses morceaux finit de se télécharger ; ensuite, vous choisissez vous-même une autre photo/bannière, récupérez de nouveau ou rédigez votre propre bio, et renseignez les liens sociaux à la main.

La possibilité de modifier est toujours disponible sur la page de chaque artiste de la Bibliothèque, sans réglage à activer d’abord.

::: info À propos de « Obtenir automatiquement les photos d’artiste » / « Obtenir automatiquement les bannières d’artiste » dans les Paramètres
**Paramètres → Téléchargements et fichiers → Obtenir automatiquement les photos d’artiste / Obtenir automatiquement les bannières d’artiste** décident si Downtify peut enregistrer de lui-même la photo/bannière d’un artiste — cela arrive la première fois que vous ouvrez la page d’un artiste et quand l’un de ses morceaux finit de se télécharger (voir [La première fois que vous ouvrez un nouvel artiste](#the-first-time-you-open-a-new-artist) et [Quand un téléchargement se termine](#when-a-download-finishes)). Les photos sont activées par défaut, les bannières désactivées. Ils ne limitent jamais la boîte de dialogue de modification : vous pouvez toujours choisir une photo ou une bannière à la main, quoi qu’ils disent.
:::

## La boîte de dialogue de modification

**Quand un artiste a une bannière définie, sa photo ronde est masquée dans l’en-tête de la page** — la bannière seule suffit généralement, et afficher les deux faisait chargé. La photo n’a pas disparu pour autant : elle est toujours là pour être modifiée, à un onglet de distance.

Sur la page d’un artiste dans la Bibliothèque (`/library/artist?name=…`), survolez la photo ronde (quand elle est affichée) pour un bouton **Modifier la photo**, ou la zone de la bannière pour un bouton **Modifier l’artiste** — les deux ouvrent la même boîte de dialogue : la photo actuelle de l’artiste en haut et, dessous, un menu à quatre onglets. Elle s’ouvre sur **Profil** ou **Bannière** selon le bouton cliqué (par défaut **Bannière**, puisque la photo n’est pas toujours visible pour cliquer).

- **Profil** / **Bannière** — choisissez une image de la même façon pour l’un ou l’autre :
  - **Rechercher par nom** — cherche sur YouTube Music et Deezer une photo d’artiste correspondante (les artistes Deezer qui n’ont que son image générique de remplacement sont écartés). Saisissez autre chose pour chercher un autre nom, ou un lien direct d’image `http(s)://` pour l’utiliser comme candidat ponctuel.
  - **Envoyer depuis votre ordinateur** — n’importe quel fichier image.
  - **Retirer la photo / Retirer la bannière** — affiché seulement une fois l’image de l’onglet actif enregistrée ; demande confirmation, puis supprime le fichier auxiliaire (sidecar).

  Chaque carte de résultat de recherche porte un badge indiquant sa provenance. En choisir une la télécharge et l’enregistre aussitôt. La carte dont l’image est celle actuellement enregistrée est marquée d’une bordure verte et d’une coche, séparément sur les onglets Profil et Bannière - pour que vous voyiez d’un coup d’œil lequel des candidats vous utilisez. Une photo que vous avez envoyée, ou une enregistrée avant que Downtify ne commence à s’en souvenir, n’a pas de carte à marquer.
- **Bio** — une zone de texte simple avec la bio actuellement enregistrée (vide s’il n’y en a pas), pour l’écrire ou la modifier vous-même. Enregistrer écrase directement le texte actuel. Un bouton ⚡ **Récupérer la bio depuis Streams** au-dessus de la zone peut la remplir depuis Apple Music/Deezer au lieu de la saisir à la main — voir [Récupérer une bio automatiquement](#fetching-a-bio-automatically) ci-dessous.
- **Réseaux sociaux** — liens Twitter/X, Instagram, Facebook, YouTube et site web, modifiables directement. Enregistrer remplace toujours les cinq champs par ce que contient le formulaire, même un champ laissé vide. Récupérer une bio ne touche jamais un lien que vous avez renseigné : les liens sociaux de Deezer ne remplissent que les champs encore vides (Deezer ne connaît pas tous les réseaux, donc complétez le reste à la main et il reste ainsi).

## La première fois que vous ouvrez un nouvel artiste

Ouvrir la page d’un artiste de la Bibliothèque initialise automatiquement son profil, mais seulement si rien n’a encore été enregistré pour lui - chaque visite après la première est un no-op rapide, si bien que cela ne se répète jamais et ne ralentit rien une fois fait.

- **Photo et bannière** — depuis Spotify (voir [Spotify](#spotify) ci-dessous), en se rabattant sur une correspondance exacte du nom sur YouTube Music quand Spotify n’a rien. Seulement si vous avez activé **Obtenir automatiquement les photos d’artiste** et/ou **Obtenir automatiquement les bannières d’artiste** dans les Paramètres (les deux sont désactivés par défaut, et chacun est indépendant) ; la boîte de dialogue de modification peut toujours définir l’une ou l’autre à la main.
- **Bio, origine, année de formation, genre, indicateur de groupe, couleur de bannière, liens sociaux, artistes similaires et identifiants de plateformes** — récupérés depuis Apple Music et Deezer comme le décrit [Récupérer une bio automatiquement](#fetching-a-bio-automatically) ci-dessous.

Si Apple Music ou Deezer **échoue** pendant ce temps (injoignable, ou au-delà de sa limite de requêtes), rien n’est enregistré - ni la bio, ni une photo - et la page n’affiche simplement pas encore de profil, si bien que la visite suivante réessaie. Seul un service répondant qu’il ne connaît pas l’artiste compte comme une réponse : le profil est alors constitué avec ce que l’autre avait. La partie Spotify (les artistes similaires) n’empêche jamais un profil d’être créé.

## Quand un téléchargement se termine

La même initialisation s’exécute en arrière-plan quand l’un des morceaux d’un artiste finit de se télécharger - que vous l’ayez lancé dans l’application ou qu’un passage du [Suivi de playlists](playlist-monitor.md) l’ait fait - si cet artiste n’a pas encore de profil, si bien que les artistes que vous téléchargez sont prêts avant même que vous n’ouvriez leur page. Cela ne ralentit jamais le téléchargement : l’artiste est mis en file et renseigné quelques secondes plus tard, deux artistes à la fois, et un artiste déjà en file n’est pas remis en file quel que soit le nombre de ses morceaux qui arrivent (une playlist de cinquante morceaux d’un même artiste ne l’initialise qu’une fois). Les morceaux déjà dans votre bibliothèque ne sont pas retéléchargés et ne déclenchent rien.

- **Quel artiste** — celui sous lequel le fichier est rangé : l’artiste de l’album, sinon le premier artiste crédité. `Various Artists` est ignoré.
- **Langue** — la bio et le genre arrivent dans la langue de l’interface web, que la page conserve sur le serveur (voir [Internationalisation](internationalization.md)) ; tant qu’une page ne l’a pas indiquée, en anglais.
- **Photo et bannière** — seulement comme **Obtenir automatiquement les photos d’artiste** / **Obtenir automatiquement les bannières d’artiste** le permettent, lus à ce moment-là, si bien que changer un réglage s’applique dès le morceau suivant.
- **Top songs** — ne sont pas créés ainsi ; ils attendent la page de l’artiste (voir [Top songs](top-songs.md)).

Si rien n’a pu être trouvé nulle part pour un artiste donné, cela ne s’exécute quand même qu’une fois - il ne réessaie pas à chaque visite ultérieure. Utilisez la boîte de dialogue de modification pour choisir une photo/bannière à la main ou réessayer le bouton de récupération à tout moment ensuite.

## L’onglet Liens

Un artiste avec au moins un lien enregistré obtient un onglet **Liens**, juste avant **Bio** (qui reste le dernier onglet), avec un compteur. Il les liste sous forme de cartes, sur n’importe quel écran et que l’artiste ait une bannière ou non : d’abord les **Plateformes de streaming**, puis les **Réseaux sociaux**. Chaque carte affiche le nom et l’adresse du site et l’ouvre dans un nouvel onglet. Seul ce qui est réellement enregistré est listé, et un artiste sans lien n’a pas d’onglet Liens (`?tab=links` ouvre alors le premier onglet).

- **Plateformes de streaming** — Spotify, YouTube Music, Deezer et Apple Music, construites à partir du `platforms_id` du profil : chaque identifiant enregistré transformé en lien (par ex. un identifiant Deezer enregistré devient un lien vers la page Deezer de cet artiste). Les identifiants sont tous résolus automatiquement la première fois qu’une bio est récupérée, par correspondance exacte du nom sur chaque plateforme (celui de Spotify vient de l’un des propres morceaux Spotify de l’artiste quand il y en a un, ce qui ne peut pas désigner un homonyme). Vous pouvez aussi en ajouter ou en corriger un à la main dans le JSON du profil de l’artiste (voir ci-dessous).
- **Réseaux sociaux** — Twitter/X, Instagram, Facebook, YouTube et site web : une carte par champ non vide de l’onglet Réseaux sociaux ci-dessus. Seules les adresses web sont ouvertes : un lien saisi sans `https://` le reçoit, et tout ce qui a un autre type d’adresse (une `javascript:`, par exemple) est ignoré.

## Spotify

Spotify n’apparaît jamais comme source de recherche en texte libre, mais le sélecteur comme l’initialisation automatique de la première visite (voir ci-dessus) y retrouvent quand même l’artiste. Ils vérifient d’abord quelques-uns des propres morceaux déjà téléchargés de l’artiste : si l’un a été téléchargé depuis Spotify, Downtify connaît déjà l’identifiant Spotify de ce morceau et résout l’image directement - la voie la plus fiable, puisqu’elle ne peut pas atterrir sur un autre artiste du même nom. Quand aucun morceau ne vient de Spotify (disons qu’ils ont été téléchargés depuis YouTube), l’artiste est cherché par nom exact (sans tenir compte de la casse - une correspondance approximative n’est jamais utilisée). Dans le sélecteur, ce candidat apparaît en premier, libellé **Spotify**.

La recherche par nom utilise la zone de recherche du lecteur web de Spotify, donc elle dépend d’un identifiant interne que Spotify peut changer ; si cela arrive, Downtify se rabat sur YouTube Music pour la photo/bannière et laisse l’identifiant Spotify vide, plutôt que d’échouer.

La photo et la bannière sont des images réellement différentes sur Spotify, résolues différemment : la photo carrée vient de la page d’intégration publique de l’artiste, tandis que la bannière large vient des données de la page d’artiste de Spotify (que l’intégration n’expose pas du tout). Tout artiste n’a pas de bannière définie - quand il n’en a pas, aucun candidat Spotify n’est proposé pour le sélecteur de bannière, plutôt que de se rabattre sur la photo carrée.

Un artiste sans morceaux d’origine Spotify n’obtient simplement aucun candidat Spotify — cherchez sur YouTube Music/Deezer, collez un lien ou envoyez une image.

## Récupérer une bio automatiquement

Sous l’en-tête, la page de l’artiste affiche une courte biographie, en lecture seule — vide tant qu’aucune n’est enregistrée. Pour la remplir, ouvrez l’onglet **Bio** de la boîte de dialogue de modification et cliquez sur **Récupérer depuis Apple Music** ou **Récupérer depuis Deezer** au-dessus de la zone de texte (voir [Choisir la source](#choosing-the-source)), ce qui charge la bio de ce service dans la zone pour que vous la relisiez et l’enregistriez. L’initialisation automatique de la première visite, qui enregistre d’elle-même, recherche l’artiste sur Apple Music par correspondance exacte du nom (avec la même recherche par nom que l’appli Musique d’Apple) et récupère sa bio, son origine, son année de formation, son genre, son indicateur de groupe et la couleur d’accent de la bannière - le texte (bio et genre) dans la langue actuelle de votre interface - puis enregistre le résultat. Le genre (Apple Music en donne un par artiste, par ex. « Hard rock ») s’affiche sous forme d’une petite pastille en haut de l’onglet Bio de la page de l’artiste, à côté de l’origine et de l’année de formation. Apple Music indique si l’artiste est un groupe : pour un groupe, cette date se lit « Formé en 1995 », et pour un artiste solo - dont la date est généralement une date de naissance - « Né le 27 septembre 1984 » (traduit dans toutes les langues de l’interface ; un artiste dont l’indicateur de groupe est inconnu reste « Formé en »). La date elle-même est affichée comme Apple Music l’a donnée, donc elle garde la langue de la récupération. Si Apple Music n’a pas de correspondance exacte, ou en a une mais sans texte de bio dans votre langue, Deezer est essayé ensuite comme source de bio secondaire - il apporte aussi des liens sociaux et des noms d’artistes similaires (« les fans aiment aussi ») (les artistes similaires sont enregistrés dans le fichier de profil de l’artiste mais pas encore affichés nulle part, réservés pour un ajout futur), en remplissant aussi l’onglet Réseaux sociaux. Seulement si aucune des deux sources n’a quoi que ce soit, vous voyez une erreur plutôt qu’une bio devinée/erronée.

Les bios éditoriales d’Apple Music ne sont pas écrites pour chaque artiste dans chaque langue - quand une langue manque pour un artiste précis, la bio de Deezer (s’il en a une) est utilisée à la place, tandis que l’origine/l’année de formation/l’indicateur de groupe viennent toujours d’Apple Music puisque ces faits ne sont pas du texte traduit (le genre n’est jamais que celui d’Apple Music, donc il reste vide quand Apple n’a pas de correspondance). Quelques langues (le bulgare, au moment de l’écriture) ne sont pas proposées par Apple Music du tout et retombent toujours sur sa bio dans la langue par défaut.

Une bio est stockée dans le JSON de l’artiste en texte brut - sans balises HTML et sans puces : une ligne vide sépare les paragraphes, et chaque puce `•` d’une bio Apple Music (qu’Apple sépare par un simple saut de ligne) devient un paragraphe à part. Les bios HTML de Deezer sont aplaties de la même façon (chaque paragraphe devient un paragraphe séparé par une ligne vide, toute autre balise est supprimée). La page de l’artiste affiche chaque paragraphe séparément et garde les sauts de ligne simples à l’intérieur, et la zone de texte de l’onglet Bio édite exactement ce texte.

Une récupération de ce genre ne s’exécute que quand vous cliquez sur le bouton - elle n’écrase rien d’elle-même après l’initialisation automatique de la première visite décrite ci-dessus. Seulement la première fois (initialisation automatique ou clic manuel), elle a besoin de chercher par nom : les identifiants d’artiste Apple Music et Deezer résolus sont ensuite mis en cache dans le fichier de profil de l’artiste, si bien que récupérer de nouveau ne fait que relire directement les mêmes artistes.

Pour effacer une bio enregistrée, ouvrez l’onglet Bio, videz la zone de texte et Enregistrez - l’origine, l’année de formation, le genre, l’indicateur de groupe, les liens sociaux, les artistes similaires et les identifiants de plateformes en cache restent intacts.

## Choisir la source

L’onglet Bio a deux liens au-dessus de la zone de texte, pour que vous choisissiez quelle biographie se lit le mieux :

- **Récupérer depuis Apple Music** — charge la bio éditoriale d’Apple Music dans la zone de texte. Si Apple Music n’en a aucune pour cet artiste dans votre langue, vous obtenez une erreur plutôt qu’un substitut.
- **Récupérer depuis Deezer** — charge la bio de Deezer, même quand Apple Music en a une. Si Deezer n’en a aucune, vous obtenez une erreur.

Cliquer sur un lien **ne fait que remplir la zone de texte** - rien n’est enregistré tant que vous n’appuyez pas sur **Enregistrer**, si bien que vous pouvez la lire, la modifier ou essayer d’abord l’autre service, et fermer la boîte de dialogue sans enregistrer laisse la bio actuelle telle quelle. Seul le texte de la bio est chargé : l’origine, l’année de formation, le genre, les liens sociaux, les artistes similaires et les identifiants de plateformes ne sont pas touchés par ces liens (c’est l’initialisation automatique de la première visite qui les remplit). L’initialisation ne vous demande pas quel service : elle utilise la bio d’Apple Music et ne se rabat sur celle de Deezer que quand Apple Music n’en a aucune.

## Où vont les fichiers

```
<downloads>/.metadata/ArtistImage/<Artist>.jpg
<downloads>/.metadata/ArtistBannerImage/<Artist>.banner.jpg
<downloads>/.metadata/ArtistData/<Artist>.json
<downloads>/.metadata/ArtistTopSongs/<Artist>.topsongs.json
```

Un fichier par artiste, nommé d’après lui (assaini comme le sont les noms de fichiers de morceaux) — pas d’enregistrement en base de données, donc la présence du fichier sur disque est ce que vérifie la page de l’artiste. Enregistrer une nouvelle photo/bannière écrase la précédente (l’interface web évite d’afficher sa copie de l’ancienne : l’URL de chaque image enregistrée porte la date de modification du fichier, si bien qu’une photo remplacée est récupérée de nouveau tandis qu’une photo intacte reste en cache), et `ArtistData/<Artist>.json` contient les données de bio/réseaux sociaux/artistes similaires/identifiants de plateformes décrites ci-dessus, plus, dans `current_cover` et `current_cover_banner`, quelle image est la photo/bannière actuelle : le chemin de l’URL d’où elle a été téléchargée (hôte et query omis, pour que la même image d’une autre adresse CDN corresponde encore), ou `upload` pour une que vous avez envoyée. C’est ce que la boîte de dialogue de modification compare à chaque candidat pour marquer celui qui est utilisé. Ce sont de simples fichiers dans votre dossier de téléchargements, donc des services comme Navidrome peuvent les lire directement si vous les pointez vers le même emplacement.

Les noms d’artistes sont appariés comme le disque les conserve : Downtify range `AC/DC` sous `ACDC`, car un nom de fichier ne peut pas contenir de `/`, et un morceau sans tag d’artiste prend son artiste dans ce nom de fichier - si bien que le même artiste peut apparaître comme `AC/DC` ou `ACDC`. Toute recherche par nom (Spotify, Deezer, YouTube Music et Apple Music) ignore la casse et les caractères qu’un nom de fichier ne peut pas contenir, si bien que les deux graphies trouvent le même artiste, et partagent les mêmes fichiers ci-dessus. Un nom qui diffère par autre chose - `AC/DC Tribute`, par exemple - est toujours un autre artiste et ne correspond jamais.

`platforms_id` reconnaît les clés `spotify`, `youtubemusic`, `deezer` et `applemusic`, toutes résolues automatiquement - Spotify à partir de l’un des propres morceaux Spotify de l’artiste ou, à défaut, par nom exact ; les autres par nom exact. Récupérer la bio renseigne aussi un identifiant Spotify manquant, si bien qu’un artiste ouvert avant que cela existe obtient son icône Spotify après une récupération. Un identifiant déjà enregistré n’est jamais remplacé, et vous pouvez toujours modifier directement le fichier JSON pour en définir un à la main.

## Hors périmètre

Choisir une photo/bannière ici ne touche jamais au pipeline de téléchargement — cela n’a aucun effet sur ce qui est intégré aux tags de vos propres fichiers audio, et télécharger un morceau ne récupère jamais automatiquement une image d’artiste.

L’onglet *Similaires* affiche une photo aussi pour les artistes que vous ne possédez pas, tout comme la grille *Artistes* de la Bibliothèque, la page propre de l’artiste, l’onglet *Artistes* de la Surveillance (l’artiste que vous surveillez, dans la liste et dans sa boîte de dialogue de modification) et les artistes de [Découvrir](discover.md) et du [Finder](finder.md) — où la page a déjà l’image Deezer de l’artiste, donc aucune recherche par nom n’est nécessaire, et une photo que vous avez enregistrée pour l’artiste s’affiche à la place — pour tout artiste dont vous n’avez pas choisi la photo (la Bibliothèque et la page propre de l’artiste utilisent l’une des pochettes de morceaux de l’artiste quand Deezer n’en a aucune ; la Surveillance n’a pas de morceau, donc elle affiche les initiales) - seulement une vraie : un artiste dont Deezer n’a pas de photo (il sert une image de remplacement générique) obtient l’initiale habituelle - mais c’est uniquement pour l’affichage : le serveur relaie l’image de Deezer à votre navigateur (qui la met en cache trois heures) sans l’enregistrer, et elle ne devient jamais la photo ou la bannière d’un artiste. Seules les vraies réponses sont conservées : si Deezer est injoignable ou si vous dépassez sa limite de requêtes à ce moment-là, la tuile affiche l’initiale (ou la pochette du morceau) pour l’instant et rien n’est mémorisé, si bien que la photo apparaît la prochaine fois que vous ouvrez la page. Les photos ne sont écrites sur disque que pour les artistes pour lesquels vous en avez défini une vous-même, ou dont la photo/bannière a été enregistrée à la première visite comme décrit ci-dessus (quand les Paramètres le permettent). Voir [`GET /api/artists/photo-proxy`](../api-reference.md#get-apiartistsphoto-proxy).
