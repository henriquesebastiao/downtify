---
title: Deemix
icon: lucide/music
---

# Source audio Deemix

Deemix est une source audio facultative, désactivée par défaut. Configurez-la dans
**Paramètres → Sources audio**, sous slskd, et activez-la dans l’ordre des sources.
Elle nécessite votre propre serveur Deemix compatible et un compte Deezer ayant droit
à la qualité demandée. Elle ne fournit pas d’abonnement et n’en contourne aucun.

## Identifiants et dossiers partagés

Gardez le mode de connexion normal par session de Deemix. N’activez pas le mode
mono-utilisateur sur un serveur non protégé : son endpoint de connexion renvoie l’ARL partagé.

Montez dans Downtify un fichier privé contenant votre ARL Deezer, lisible uniquement
par son compte de service, et définissez `DOWNTIFY_DEEMIX_ARL_FILE` sur ce chemin.
L’ARL n’est lu qu’à l’ouverture d’une session par cookie. Il n’est jamais stocké dans
les réglages, renvoyé au navigateur ni consigné dans les journaux. Traitez-le comme un mot de passe ;
obtenez-le et remplacez-le en privé, pas dans des issues ni dans un chat. L’intégration
ne modifie jamais la connexion ni les réglages de téléchargement de Deemix à l’échelle du serveur.
Le test de connexion ne met aucun téléchargement en file.

| Réglage                       | Rôle                                                               |
| ----------------------------- | ------------------------------------------------------------------ |
| URL du serveur                | Adresse interne de Deemix, par ex. `http://deemix:6595`            |
| Dossier de téléchargement dans Deemix | Généralement `/downloads`                                  |
| Même dossier dans Downtify    | Bind mount partagé, par ex. `/deemix` ; la lecture seule est prise en charge |
| Qualité                       | MP3 128, MP3 320 ou FLAC ; les droits non pris en charge échouent explicitement |

Le dossier partagé est enregistré comme dossier de bibliothèque externe à l’enregistrement.
Les fichiers y restent, dans l’organisation artiste/album de Deemix. Downtify conserve
leur format, leurs tags, leurs pochettes et leurs fichiers annexes `.lrc` sans les réécrire.
Les paroles intégrées et les `.lrc` de même nom sont lus par le lecteur.
Aucun audio ni aucune parole n’est supprimé, déplacé ou généré par cette intégration.

Un lien de titre Deezer sélectionne cet enregistrement. Les téléchargements entre catalogues exigent
une correspondance exacte et sans ambiguïté d’artiste/titre, avec album et durée concordants
lorsqu’ils sont fournis. Une correspondance ambiguë passe à la source activée suivante.
La fin de la file de Deemix est suivie d’une vérification du fichier et de la durée/qualité.
L’intégration ne vide, n’annule ni ne modifie jamais les tâches Deemix manuelles.
Les liens YouTube explicites conservent leur comportement actuel de téléchargement direct.

Cette source ne remplace ni ne supprime automatiquement un titre existant de la
bibliothèque. La déduplication de la bibliothèque et le remplacement manuel de l’audio restent distincts.
