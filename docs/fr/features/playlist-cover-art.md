---
icon: lucide/image
---

# Pochettes de playlists

Downtify peut enregistrer la pochette propre à une playlist à côté de son [fichier M3U](m3u-export.md), afin que les serveurs multimédias et les navigateurs de fichiers affichent le vrai visuel de la playlist plutôt qu’une icône générique.

Activé par défaut. Désactivez-le dans **Paramètres → Téléchargements et fichiers → Enregistrer la pochette de la playlist**.

## Où va le fichier

La pochette est écrite avec le **même nom et dans le même dossier que le M3U de la playlist**, avec l’extension `.jpg` :

```
<downloads>/<nom-de-la-playlist>/<nom-de-la-playlist>.m3u
<downloads>/<nom-de-la-playlist>/<nom-de-la-playlist>.jpg
```

Avec *Classer par artiste* ou *Classer par album* activé, les titres sont répartis dans des dossiers d’artistes et le M3U va dans un répertoire central `Playlists/` (voir [Organisation des fichiers](file-organization.md)) — la pochette le suit :

```
<downloads>/Playlists/<nom-de-la-playlist>.m3u
<downloads>/Playlists/<nom-de-la-playlist>.jpg
```

::: info Il faut le M3U
Avec **Écrire des playlists M3U** désactivé, aucune pochette n’est enregistrée non plus : Downtify place l’image d’après le chemin du M3U ; sans lui, il n’y a nulle part où la mettre. Le réglage est masqué tant que l’écriture de M3U est désactivée.
:::

## Sources et résolution

| Source | Résolution |
|--------|-----------|
| **Spotify** | La plus grande image que sa page d’intégration publique propose pour la playlist — la même que celle déjà utilisée pour les pochettes des titres |
| **YouTube Music** | Toujours demandée en 1200×1200, indépendamment de la [Résolution des pochettes](download-settings.md#cover-art-resolution), qui n’affecte que les pochettes par titre |

Les deux services servent du JPEG pour ces URL même lorsque l’image d’origine était un PNG ; le fichier est donc toujours enregistré en `.jpg`.

## Quand elle est téléchargée

**Avant les titres**, dans les deux cas — le dossier ressemble déjà à la playlist pendant qu’il se remplit, et un serveur multimédia qui analyse en plein téléchargement y trouve le visuel plutôt qu’un dossier nu :

- **Un téléchargement manuel de playlist** — une fois, dès que le nom de la playlist est résolu, avant le début du premier titre.
- **[Surveillance de playlists](playlist-monitor.md)** — une fois par passage qui a quelque chose à télécharger, avant le premier titre de ce passage. Un passage qui ne trouve rien de nouveau ne la récupère pas à nouveau.

Un échec de résolution ou de téléchargement de la pochette (erreur réseau, playlist sans visuel) est consigné et ignoré — il ne retarde ni ne fait échouer jamais le téléchargement lui-même.

## Dans l’interface de Downtify

Une playlist qui a son propre visuel (téléchargée avec une playlist Spotify ou YouTube) l’affiche partout où la Bibliothèque liste les playlists — la grille, la page de la playlist, la barre latérale et le lecteur. Les playlists qui n’en ont pas, et celles que vous créez dans la Bibliothèque, affichent une mosaïque d’au plus quatre pochettes de titres distinctes : deux côte à côte, trois sous forme d’une grande tuile à gauche et de deux tuiles empilées à droite, quatre en grille 2×2. Le même collage est écrit sous le nom `<nom-de-la-playlist>.jpg` à côté du M3U d’une playlist manuelle pour que Navidrome le voie aussi, et il est refait à chaque ajout ou retrait de titres.

## Navidrome

Rien à configurer : Navidrome résout le visuel des playlists à partir d’une **image annexe** — un fichier portant le nom de la playlist, dans le même dossier — ce qui est exactement ce que Downtify écrit. Tant que le dossier de musique de Navidrome couvre votre dossier de téléchargements, le visuel apparaît à son prochain scan. Aucun appel d’API de Downtify n’est impliqué. Voir [slskd et Navidrome](slskd-navidrome.md#navidrome).

## Nettoyage

Supprimer une playlist depuis la page de la Bibliothèque supprime sa pochette en même temps que son M3U et ses titres — voir [Supprimer une playlist](slskd-navidrome.md#deleting-a-playlist).
