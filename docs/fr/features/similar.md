---
icon: lucide/sparkles
---

# Similaires

**Similaires** trouve des titres qui sonnent comme celui que vous indiquez, à partir du mix radio de YouTube Music lui-même — ce que YouTube joue après votre titre. Sans clé d’API, sans configuration.

## Utilisation

Ouvrez **Similaires** depuis la barre latérale (sous **Classements**, ou dans la feuille **Plus** sur téléphone). Saisissez l’**Artiste** ou le **Titre** (l’un des deux suffit — un artiste seul part de son plus gros tube), puis **Trouver des similaires** :

Vous n’avez même pas besoin de saisir : chaque ligne de titre de l’application porte un bouton **Similaires** (l’icône de baguette à côté du bouton de téléchargement, pleine comme lui dans Recherche, Classements et Découvrir — dans Titres les plus écoutés et les liens collés, c’est une icône discrète, et un élément du menu contextuel sur les titres de la Bibliothèque, d’Album, d’Artiste et de Playlist). Il ouvre cette page en lançant déjà la recherche pour ce titre. Les résultats se lisent aussi en entier directement depuis la ligne, sans rien télécharger.

- **Lecture intégrale** — touchez la pochette et le titre est diffusé depuis ce serveur directement dans le lecteur intégré, qu’il soit téléchargé ou non.
- **Télécharger** — chaque ligne porte déjà sa vidéo et se télécharge tout de suite : Downtify met la correspondance en file par le même [pipeline de correspondance](../how-it-works.md) que tous les autres téléchargements. Ensuite, la ligne affiche la progression de ce téléchargement, puis une coche une fois le titre dans votre bibliothèque.
- **Liste sans fin** — faire défiler jusqu’au bout charge la page suivante à partir du mix du dernier titre, et la lecture au-delà de la dernière ligne continue d’allonger la file de la même façon, sans fin.

## API

Voir [`GET /api/similar/tracks`](../api-reference.md#get-apisimilartracks) dans la Référence de l’API.
