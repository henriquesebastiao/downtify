---
icon: lucide/columns-3
---

# Finder

**Finder** est une façon d’explorer le catalogue de Deezer avant de télécharger. Vous cherchez sur Deezer, ouvrez un artiste et le parcourez en trois colonnes côte à côte, comme l’affichage en colonnes du Finder de macOS : l’artiste, sa discographie et les titres d’un album. Aucun compte Deezer ni clé d’API n’est nécessaire.

## Recherche

Ouvrez **Découvrir** dans la barre latérale (sur téléphone : **Plus → Découvrir**) : la zone de recherche du Finder est en haut de la page, avec vos recherches récentes du Finder à côté. Chercher remplace les suggestions de Découvrir par ce qui a été trouvé — titres, albums et artistes, avec les filtres **Tout / Titres / Albums / Artistes** comme sur la page de Recherche habituelle, mais uniquement depuis Deezer. Videz la zone (le **×**) ou revenez en arrière pour revoir les suggestions ; une recherche récente se relance en un clic, et **Effacer** les oublie toutes. Les recherches récentes ne sont conservées que dans ce navigateur.

**Trouver des titres**, dans le menu **⋯** d’un artiste suggéré par Découvrir, affiche ici les titres de cet artiste comme une recherche : Deezer est interrogé avec le nom de l’artiste, et seuls les titres de cet artiste précis — repérés par son identifiant Deezer, si bien qu’un homonyme ou un titre qui porte simplement ce nom est écarté — sont listés, jusqu’aux premières centaines.

- Les **titres** sont diffusés en entier et se téléchargent comme n’importe quel résultat de recherche. Downtify retrouve le titre sur YouTube Music (avec YouTube en repli) d’après le titre, l’artiste et la durée. Cliquer sur le titre d’un morceau ouvre son album dans l’affichage en colonnes, le morceau étant mis en évidence.
- Les **albums** s’ouvrent sur leur artiste, avec cet album sélectionné. Le bouton de téléchargement sur la pochette met l’album entier en file d’attente.
- Les **artistes** ouvrent l’affichage en colonnes sur cet artiste.

## L’affichage en colonnes

| Colonne | Ce qu’elle montre |
| --- | --- |
| **Artiste** | La photo de l’artiste et son nombre d’albums, sa biographie dans la langue de l’interface (dépliable), ses 10 titres les plus populaires et « Les fans aiment aussi » (artistes similaires). |
| **Discographie** | Tous les albums, singles, EP et compilations, du plus récent au plus ancien, avec pochette, titre, type de sortie, année et nombre de titres. Des puces filtrent par type de sortie. |
| **Titres** | La pochette et le titre de l’album sélectionné, son artiste, son année, son nombre de titres et sa durée. Un panneau d’informations indique la date de sortie, le label, les genres, les crédits et l’UPC. En dessous figurent les titres de l’album : chacun est diffusé en entier jusqu’à son téléchargement, puis lu depuis votre bibliothèque, avec un bouton **Télécharger l’album** pour tous les mettre en file d’attente. |

Cliquer sur un titre populaire sélectionne son album et met le titre en évidence ; les deux colonnes défilent en douceur pour les amener à l’écran (instantanément si le système est réglé pour réduire les animations), et dès que les titres de l’album sont affichés, le titre se lance en entier — diffusé, ou le morceau lui-même s’il est déjà dans votre bibliothèque. Cliquer de nouveau pendant la lecture ne le met pas en pause ; ouvrir la page depuis un lien qui pointe vers un titre ne lance rien. Cliquer sur un artiste similaire ouvre cet artiste, et le bouton retour du navigateur ramène au précédent. La barre de chemin au-dessus des colonnes (**Découvrir › artiste › album**) ramène à la recherche (ou à Découvrir, quand les colonnes n’ont pas été ouvertes depuis une recherche) ou à l’artiste seul. Ce qui est ouvert est enregistré dans l’URL : cela survit à un rechargement et peut être mis en favori.

Sur grand écran, faites glisser le bord entre deux colonnes pour en élargir ou en rétrécir une, ou donnez-lui le focus et utilisez les flèches du clavier. Un double-clic rétablit les largeurs par défaut. Le bouton fléché en haut des colonnes artiste et discographie réduit la colonne à ses seules images : la photo de l’artiste, les pochettes de ses titres populaires et les photos des artistes similaires, ou les pochettes des albums. Chaque image fonctionne toujours comme sa ligne complète, et son nom s’affiche au survol. Les largeurs et les colonnes réduites ne durent que le temps de votre présence sur la page : elles ne sont jamais enregistrées, donc un rechargement ou une sortie du Finder les réinitialise.

Sur téléphone, les colonnes sont côte à côte et vous glissez de l’une à l’autre. Choisir un album vous amène à ses titres.

::: info Pourquoi le nombre de titres apparaît un instant plus tard
La liste de la discographie de Deezer n’indique pas le nombre de titres ; Downtify demande donc celui de chaque album séparément, quelques albums à la fois, en restant sous la limite de Deezer de 50 requêtes toutes les 5 secondes. Les nombres apparaissent pendant que vous regardez et sont conservés jusqu’au redémarrage de Downtify. Un album dont le nombre n’a pas pu être récupéré affiche `…`.
:::

## API

Voir [`GET /api/finder/search`](../api-reference.md#get-apifindersearch) et les endpoints suivants dans la Référence de l’API.
