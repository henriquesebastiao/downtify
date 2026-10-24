---
icon: lucide/sparkles
---

# Fonctionnalités

Downtify couvre tout ce qu’il faut pour construire et entretenir une bibliothèque musicale locale à partir de Spotify.

## Vue d’ensemble

| Fonctionnalité | Ce qu’elle fait |
|---------|-------------|
| [Classements](charts.md) | Parcourez le classement mondial de Deezer et téléchargez ce qui est en tendance |
| [Similaires](similar.md) | Indiquez un artiste ou un titre ; YouTube Music répond avec des titres similaires qui se lisent en entier et se téléchargent, sans clé |
| [Explorateur](finder.md) | Cherchez sur Deezer, puis parcourez un artiste, ses albums et les titres de n’importe quel album en colonnes |
| [Réglages de téléchargement](download-settings.md) | Choisissez le format (MP3/FLAC/M4A/OGG/OPUS), le débit, les téléchargements simultanés et la pause entre téléchargements |
| [Surveillance de playlists](playlist-monitor.md) | Surveillez des playlists et artistes Spotify ou YouTube Music, et téléchargez automatiquement les nouveaux titres et sorties |
| [Titres masqués d’une playlist](hidden-playlist-songs.md) | Retirez d’une playlist téléchargée ou surveillée les titres dont vous ne voulez pas, pour de bon ; les fichiers restent dans la bibliothèque |
| [Titres les plus écoutés](top-songs.md) | Collez le lien d’un artiste et téléchargez ses morceaux les plus populaires, éventuellement sous forme de playlist |
| [Import de bibliothèque (CSV)](library-import.md) | Importez un export de Soundiiz, TuneMyMusic ou Exportify et mettez le tout en file |
| [Lecteur intégré](player.md) | Écoutez votre bibliothèque dans le navigateur : gestion de la file, paroles synchronisées, minuterie de mise en veille, clavier et touches multimédias |
| [Titres likés](liked-songs.md) | Mettez un cœur à un titre pour le liker ; une playlist de tout ce que vous avez liké apparaît toute seule |
| [Podcasts](podcasts.md) | Abonnez-vous à une émission par flux RSS, lien Spotify ou nom ; les nouveaux épisodes se téléchargent et s’étiquettent tout seuls |
| [Utilisateurs et connexion](users.md) | Connexion par nom d’utilisateur et mot de passe (`admin` / `downtify` sur un nouveau serveur), comptes administrateur et utilisateur, préférences par utilisateur et journal d’activité des connexions et de ce que chacun écoute |
| [Marque de contenu explicite](explicit-marker.md) | Le « E » à côté des morceaux aux paroles explicites — dans la recherche, la Bibliothèque et le lecteur — et dans les tags du fichier |
| [Remplacer l’audio](replace-audio.md) | Mauvais morceau ou mauvaise version ? Choisissez la bonne sur YouTube Music ou YouTube ; le fichier garde son nom, ses tags et ses playlists |
| [Réglages du serveur](server.md) | Le port sur lequel Downtify écoute, modifié depuis les Paramètres (administrateurs), avec redémarrage immédiat si vous le souhaitez |
| [Applications mobiles](mobile-apps.md) | Associez des applications de téléphone par QR code et diffusez-leur la bibliothèque (d’origine ou transcodée) |
| [Découvrir](discover.md) | Artistes, albums et playlists que vous n’avez pas encore, suggérés d’après votre bibliothèque, vos likes et vos écoutes ; masquez ceux dont vous ne voulez pas |
| [slskd et Navidrome](slskd-navidrome.md) | Téléchargez depuis Soulseek via slskd, reflétez les playlists dans Navidrome et suivez les téléchargements de playlists |
| [Catalogue de la bibliothèque et synchro des chemins](library-catalog.md) | Comment Downtify suit les fichiers et playlists de la bibliothèque, les playlists que vous créez dans la Bibliothèque, et la correction des chemins après un déplacement de fichiers |
| [Dossiers de musique existants](external-library.md) | Pointez Downtify vers des dossiers d’audio que vous avez déjà ; la synchronisation lit les tags, associe les artistes et ignore les morceaux déjà dans la bibliothèque |
| [Améliorer la bibliothèque](library-upgrade.md) | Analysez la musique déjà téléchargée et réparez les petites pochettes, les paroles manquantes et les tags incomplets |
| [Export M3U](m3u-export.md) | Fichiers de playlist générés automatiquement pour Jellyfin, Navidrome, Plex et toute application multimédia |
| [Pochettes de playlists](playlist-cover-art.md) | Enregistrez l’image de pochette de la playlist à côté de son fichier M3U |
| [Photo, bannière et bio de l’artiste](artist-images.md) | Choisissez une vraie photo et une vraie bannière pour un artiste depuis YouTube Music, Deezer, Spotify ou votre propre envoi, et récupérez sa bio, son origine et ses liens depuis Apple Music et Deezer, automatiquement ou à la demande |
| [Organisation des fichiers](file-organization.md) | Structure à plat ou sous-dossiers par artiste |
| [Paroles](lyrics.md) | Téléchargez et intégrez automatiquement les paroles (simples et synchronisées) ; `.lrc` à côté du fichier ou dans un dossier de votre choix |
| [Cookies YouTube](youtube-cookies.md) | Envoyez un `cookies.txt` depuis l’interface web pour télécharger des titres explicites/soumis à une limite d’âge |
| [Internationalisation](internationalization.md) | L’anglais et neuf autres langues d’origine, et la documentation dans toutes |
| [Notifications de mise à jour](updates.md) | Vérification toutes les heures sur les Releases GitHub ; un avis apparaît dans la barre latérale quand une version plus récente est sortie |

## Types d’entrée

Downtify accepte plusieurs types d’entrée dans la barre de recherche :

| Entrée | Exemple |
|-------|---------|
| URL de titre, d’album, de playlist ou d’artiste Spotify | `https://open.spotify.com/track/…` |
| URL YouTube / YouTube Music | `https://www.youtube.com/watch?v=…` |
| URL de playlist ou d’artiste YouTube Music | `https://music.youtube.com/playlist?list=…` |
| URL de titre, d’album, de playlist ou d’artiste Deezer | `https://www.deezer.com/track/…` |
| Recherche en texte libre | `The Night Owls Do I Still Recall` |

Les recherches en texte libre sont envoyées directement à YouTube Music — aucun lien Spotify n’est nécessaire.
