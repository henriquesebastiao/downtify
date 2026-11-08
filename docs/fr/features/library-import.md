---
icon: lucide/import
---

# Import de bibliothèque (CSV)

Vous avez déjà exporté votre bibliothèque depuis un autre service ? Importez le CSV et mettez tous les titres en file de téléchargement d’un coup, au lieu d’ajouter les morceaux un à un.

## Exportateurs pris en charge

| Outil | Remarques |
|------|-------|
| [Soundiiz](https://soundiiz.com/) | |
| [TuneMyMusic](https://www.tunemymusic.com/) | |
| [Exportify](https://github.com/watsonbox/exportify) | |

Downtify ne fige le schéma exact de colonnes d’aucun outil. Il compare plutôt la ligne d’en-tête du CSV, sans tenir compte de la casse, à un ensemble d’alias connus (`Title` / `Track` / `Track Title` / `Track Name` / `Song` / …, `Artist` / `Artists` / `Artist Name` / `Artist Name(s)` / … et `Album` / `Album Name` / `Album Title` / …), de sorte que les exports de n’importe lequel des trois — ou d’un CSV fait main avec les mêmes noms de colonnes — fonctionnent sans rien renommer.

Le titre et l’artiste sont obligatoires. L’album est lu quand il est présent et enregistré comme nom d’album du titre (File, correspondance et tags du fichier). Les autres colonnes que certains exportateurs ajoutent (ISRC, URI de titre Spotify, durée) sont ignorées. Chaque ligne est résolue comme une recherche libre, via YouTube Music.

## Comment importer

1. Sur la page d’accueil, cliquez sur **Importer un CSV (Soundiiz, Exportify…)**, sous la zone de recherche.
2. Choisissez votre fichier `.csv` exporté.

Le fichier est lu entièrement dans votre navigateur et envoyé au serveur en texte brut — il n’est jamais envoyé ailleurs. Downtify l’analyse, met en file toutes les lignes reconnues, et vous arrivez sur la File de téléchargement où la progression arrive par WebSocket exactement comme pour n’importe quel autre téléchargement par lot.

Le lot importé prend le nom du fichier (son nom sans `.csv`) et, comme tout autre téléchargement de playlist, reçoit un [fichier M3U](m3u-export.md) si ce réglage est activé.

## Limites et gestion des erreurs

- Jusqu’à **2 000 lignes** par fichier. Découpez les exports plus gros en plusieurs fichiers.
- Les lignes sans titre ou sans artiste sont ignorées en silence. Une colonne d’album absente ou une cellule d’album vide ne pose pas de problème — YouTube Music peut encore renseigner l’album plus tard.
- Plusieurs artistes dans une même cellule (séparés par `,` ou `;`) sont répartis en liste.
- Si l’en-tête ne contient aucune colonne titre/artiste reconnaissable, l’import entier est refusé d’emblée avec une erreur nommant les colonnes trouvées — rien n’est mis en file.

## Éviter les limites de débit

Importer une grande bibliothèque met en file beaucoup de recherches et de téléchargements YouTube Music en peu de temps, ce qui expose facilement à une limitation. Avant d’importer un gros fichier, envisagez de réduire **[Téléchargements simultanés](download-settings.md#parallel-downloads)** et d’activer **[Pause entre téléchargements](download-settings.md#delay-between-downloads)** dans les Paramètres.

## API

Voir [`POST /api/download/csv`](../api-reference.md#post-apidownloadcsv) dans la référence de l’API pour l’endpoint sous-jacent.
