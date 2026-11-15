---
icon: lucide/replace
---

# Remplacer l’audio

Downtify choisit automatiquement l’audio de chaque morceau, et il lui arrive de choisir le mauvais : un autre morceau du même nom, une version live, un remix ou une mise en ligne avec une longue intro. **Remplacer l’audio** vous laisse choisir la bonne version à la main. Le titre garde sa place partout — ses playlists, fichiers M3U, likes et applications associées — et seul l’audio change.

Seuls les administrateurs peuvent remplacer l’audio (voir [Utilisateurs et connexion](users.md#admins-and-users)).

## Remplacer l’audio d’un titre

1. Dans la **Bibliothèque**, ouvrez le menu du titre (clic droit, ou le bouton **⋯**) et choisissez **Remplacer l’audio…**.
2. Downtify cherche « Artiste - Titre » sur **YouTube Music** et **YouTube**, et liste ce qu’il trouve. Modifiez la recherche, ou collez un lien YouTube ou YouTube Music vers une vidéo ou un morceau, pour obtenir exactement la mise en ligne voulue.
3. Choisissez une version. Chacune indique d’où elle vient et sa durée, à côté de la durée de votre fichier. Une version à moins de 3 secondes de la durée de votre fichier est mise en évidence. Le bouton ↗ l’ouvre sur YouTube, pour l’écouter avant de choisir.
4. Appuyez sur **Remplacer l’audio**. Le remplacement s’exécute comme un téléchargement : il affiche sa progression dans la boîte de dialogue et dans la **File**, et la boîte de dialogue indique quand c’est terminé.

En cas d’échec (la vidéo est indisponible, ou YouTube demande de se connecter — voir [Cookies YouTube](youtube-cookies.md)), votre fichier reste exactement tel qu’il était. **Réessayer** dans la File retente la même vidéo, et coller un autre lien à cet endroit remplace avec celui-là.

## Utiliser un fichier de votre appareil

Si la bonne version n’est pas sur YouTube (un rip de CD, un téléchargement Soulseek, un fichier qu’on vous a envoyé), utilisez votre propre fichier :

1. Dans la boîte de dialogue, sous **Ou utilisez un fichier de votre appareil**, appuyez sur **Choisir un fichier…** et choisissez le fichier audio.
2. Appuyez sur **Remplacer l’audio**. Le fichier est envoyé, vérifié comme audio lisible, et reçoit les tags de l’ancien fichier.

Un fichier dans le format du morceau (un `.mp3` pour un `.mp3`) est utilisé exactement tel quel. Un autre format (`.mp3`, `.flac`, `.m4a`, `.ogg`, `.opus`, `.wav`, `.aiff`, `.aac` ou `.webm`) est converti dans le format du morceau, au débit choisi dans les [Paramètres de téléchargement](download-settings.md) : utilisez donc le même format quand vous l’avez. Cela fonctionne aussi en mode bibliothèque seule, puisque rien n’est récupéré sur Internet.

## Les téléchargements laissent un fichier remplacé tranquille

Avec **Retélécharger si le fichier existe** activé, un téléchargement ultérieur de la même chanson (depuis une autre playlist surveillée, le suivi d’un artiste ou le téléchargement d’une playlist) écraserait votre remplacement par ce que trouve la recherche automatique. Downtify retient donc chaque fichier dont vous avez remplacé l’audio, d’une façon ou de l’autre, et un tel téléchargement le compte comme déjà téléchargé. [Améliorer la bibliothèque](library-upgrade.md) ne remplace pas non plus son audio ; sa pochette, ses paroles et ses tags peuvent toujours être améliorés.

La boîte de dialogue indique quand l’audio d’un morceau a été remplacé à la main. **Laisser les téléchargements le remplacer** lève cette protection pour ce fichier.

## Ce qui reste identique

- **Le fichier.** Le nouvel audio est écrit au même chemin, dans le même format : un `.mp3` reste du MP3 (au débit choisi dans les [Réglages de téléchargement](download-settings.md)), un `.flac` reste du FLAC, et ainsi de suite. Ainsi, chaque playlist, fichier M3U, titre liké, entrée Navidrome et application associée qui pointe vers le fichier continue d’y pointer.
- **Les tags.** Titre, artistes, album, numéro de piste, année, pochette, paroles intégrées et tous les autres tags sont copiés tels quels de l’ancien fichier vers le nouvel audio. Le fichier annexe `.lrc` n’est pas touché. Les paroles synchronisées avaient été calées sur l’ancien audio : si la nouvelle version démarre à un autre endroit, elles peuvent être décalées.
- **La date.** Le fichier garde sa date de modification, il ne saute donc pas en tête de « Ajouts récents ».

Seuls les fichiers `.mp3`, `.flac`, `.m4a`, `.ogg` et `.opus` — les formats que Downtify écrit — peuvent être remplacés.

## Fonctionnement

La vidéo choisie est téléchargée à côté du fichier sous un nom temporaire que la bibliothèque ignore (`<nom>.downtify-upgrade.<ext>`), convertie au format du fichier, vérifiée comme étant de l’audio lisible, dotée des tags de l’ancien fichier, et seulement alors déplacée par-dessus l’ancien. L’API se trouve dans la [référence de l’API](../api-reference.md#get-apilibraryreplacecandidates).
