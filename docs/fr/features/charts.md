---
icon: lucide/trending-up
---

# Classements

**Classements** affiche le classement mondial de Deezer lui-même — sans filtre de genre, ce qui est en tendance partout dans le monde en ce moment — sans compte ni clé d’API Deezer.

## Utilisation

Ouvrez **Classements** depuis la barre latérale (ou la feuille **Plus** sur téléphone). Quatre onglets lisent le même classement : **Titres**, **Albums**, **Artistes** et **Playlists**.

- **Titres** — une liste classée. Appuyez sur l’un d’eux (ou touchez sa ligne) pour l’écouter en entier depuis YouTube, directement dans le lecteur intégré, avant de le télécharger. Télécharger une ligne fonctionne comme un résultat de recherche : Downtify cherche sur YouTube Music (puis sur YouTube standard) la meilleure correspondance avec le titre, l’artiste et la durée du morceau, par le même [pipeline de correspondance](../how-it-works.md) que tous les autres téléchargements. Une fois le titre téléchargé, sa ligne lit celui de votre bibliothèque au lieu de le diffuser.
- **Albums**, **Artistes** et **Playlists** — des grilles de pochettes. Un clic le résout ([`GET /api/url/resolve`](../api-reference.md#get-apiurlresolve)) exactement comme si vous aviez collé ce lien Deezer dans la zone de recherche : sa liste de titres se charge, prête à être choisie et téléchargée.

## Pourquoi les titres se téléchargent (et se lisent en entier) directement d’ici, alors que les albums, artistes et playlists ouvrent d’abord une page

Un titre du classement n’a pas besoin d’étape de résolution pour être téléchargé : Deezer donne déjà son titre, son artiste et le nom de l’album, ce qui suffit pour le chercher et le faire correspondre sur YouTube, comme pour un résultat de recherche libre. Un album, un artiste ou une playlist en a besoin — transformer son lien en liste de titres —, si bien que sa carte ouvre cette page résolue au lieu de télécharger directement depuis la grille. Lire une ligne de titre le diffuse en entier depuis YouTube (jamais pour les albums, artistes ou playlists) — la même diffusion que toute ligne de titre, simplement alimentée avec le titre et l’artiste du classement.

## API

Voir [`GET /api/discover/chart`](../api-reference.md#get-apidiscoverchart) dans la Référence de l’API.
