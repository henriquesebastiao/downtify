---
icon: lucide/wand-sparkles
---

# Améliorer la bibliothèque

Une bibliothèque constituée au fil du temps porte ce que chaque version de Downtify savait faire quand un morceau a été téléchargé : la plus petite pochette qu’une source proposait, pas de paroles, des tags sans album ni année. **Améliorer la bibliothèque** regarde ce qui est déjà sur le disque et ne répare que ce qui est en retard — sans retélécharger, et sans rien à régler à la main.

Ouvrez-la depuis **Bibliothèque → Améliorer la bibliothèque**.

::: info Les améliorations par défaut ne réécrivent que les tags
Le mode par défaut réécrit les **pochettes, paroles et tags**. Le [remplacement par Deemix](#deemix-recording-replacement) facultatif est un mode d’analyse distinct, désactivé par défaut. Utilisez [Remplacer l’audio](replace-audio.md) pour choisir manuellement une autre version.
:::

## Comment ça marche

1. **Analyse.** Downtify lit chaque morceau de la bibliothèque et indique ce qui est en retard, par catégorie. Rien n’est écrit.
2. **Choix.** Chaque catégorie pour laquelle l’analyse a trouvé quelque chose est listée avec son nombre de morceaux et un interrupteur. Décochez ce que vous ne voulez pas.
3. **Amélioration.** Les morceaux choisis entrent dans une file traitée un par un. Vous pouvez la mettre en pause, la reprendre ou l’arrêter, et elle survit à un redémarrage.

## Ce qu’elle répare

| Catégorie | Ce qu’elle fait | Où elle cherche |
|---|---|---|
| **Améliorer les pochettes** | Remplace une pochette plus petite que la taille cible | Spotify, Apple Music (iTunes), YouTube Music |
| **Ajouter les paroles manquantes** | Renseigne les paroles des morceaux qui n’en ont pas, intégrées et en fichier `.lrc` | Vos [fournisseurs de paroles](lyrics.md), dans votre ordre |
| **Actualiser les étiquettes** | Renseigne album, artiste de l’album, date de sortie et numéro de piste — y compris l’album qui manque aux anciens téléchargements de morceaux seuls | Spotify |

Un morceau compte comme en retard quand :

- le petit côté de sa pochette intégrée est **plus petit que la taille cible** (un morceau sans aucune pochette compte aussi) ;
- il n’a **ni** paroles intégrées **ni** fichier `.lrc` (à côté du fichier ou dans le dossier des paroles des Paramètres) ;
- l’un des champs **album**, **artiste de l’album**, **année** ou **numéro de piste** manque dans ses tags.

**Actualiser les étiquettes** ne fonctionne que pour les morceaux dont Downtify a encore l’identifiant Spotify — ceux qu’il a téléchargés depuis un lien Spotify, conservés dans l’[index des morceaux](library-catalog.md#what-gets-stored). Les autres morceaux sont mis en file mais reviennent en _Rien à faire_.

## Options

### Améliorer les pochettes en dessous de

`300px` · `500px` · **`600px`** · `1000px` · `1200px`

Les pochettes de cette taille ou plus grandes sont laissées de côté. Downtify n’écrit une pochette que si elle est **strictement plus grande** que celle déjà dans le fichier, si bien qu’exécuter une amélioration deux fois ne réécrit jamais rien pour rien.

D’où viennent les tailles :

| Source | Taille typique |
|---|---|
| **Apple Music (iTunes)** | 1200px et plus |
| **Spotify** | jusqu’à 640px |
| **YouTube Music** | jusqu’au réglage de [résolution des pochettes](download-settings.md), ~1200px au maximum |

C’est aussi pourquoi une bibliothèque téléchargée auparavant reste souvent bloquée à 300–640px : Spotify publie ses pochettes en tailles fixes, et la plus grande qu’il propose est de 640px.

### Source des pochettes

| Choix | Comportement |
|---|---|
| **La plus haute résolution disponible** (par défaut) | Interroge toutes les sources et garde la plus grande image |
| **Préférer Spotify** / **Préférer Apple Music** / **Préférer YouTube Music** | Utilise cette source quand elle a quoi que ce soit ; les autres ne servent de repli que lorsqu’elle n’a rien |

### Ne pas revérifier un morceau pendant

`Toujours vérifier tous les morceaux` · `7 jours` · **`30 jours`** · `90 jours` · `365 jours`

Après qu’un morceau a été examiné, la prochaine analyse l’ignore pendant cette durée, si bien qu’un second passage sur une grande bibliothèque ne redemande pas aux mêmes sources les mêmes morceaux.

La mémoire est conservée **par morceau et par catégorie**, ce qui fait fonctionner les passages partiels : réparer seulement les pochettes de 16 000 morceaux ne dit rien sur le fait que quelqu’un ait jamais cherché leurs paroles, donc un passage « paroles » ultérieur les considère tous. Une analyse enregistre aussi les catégories qu’elle a examinées et pour lesquelles elle n’a rien trouvé à faire — regarder et ne rien trouver est une vérification comme une autre.

Downtify retient, pour chaque morceau et catégorie : quand il a été vérifié, la version de Downtify qui l’a vérifié et — pour les pochettes — la plus grande pochette trouvée et sa provenance. Les fournisseurs de paroles déjà interrogés sont conservés à part, par morceau et par fournisseur (voir [Paroles](lyrics.md)).

Deux choses la passent toujours outre :

- une **version plus récente de Downtify** revérifie tout, puisqu’elle peut apparier ou taguer mieux que la précédente ;
- choisir **Toujours vérifier tous les morceaux** ignore la mémoire pour cette analyse.

Quand une analyse ne trouve plus rien à faire _parce que_ tout a été vérifié récemment, elle le dit et propose de relancer sans la mémoire, plutôt que de vous laisser avec un « rien à améliorer » inexpliqué.

## Pendant l’exécution

Le panneau de progression montre les morceaux traités sur la file, un chiffre approximatif de données (`8.4 GB of 51.3 GB`) et combien ont été améliorés, n’avaient rien à faire ou ont échoué. Chaque morceau indique ce qu’il fait — _Identification_, _Recherche de la pochette_, _Recherche des paroles_, _Écriture du fichier_ — et se termine par ce qui a changé, par ex. `artwork 1200px (itunes)`.

**Mettre en pause** s’arrête après le morceau en cours et garde la file. **Arrêter** abandonne le reste ; les morceaux déjà améliorés le restent. Vous pouvez quitter la page — l’exécution continue, et tout autre onglet ouvert la suit.

La file vit dans `/data/downtify_library.db`, donc **redémarrer Downtify (ou le conteneur) en cours d’exécution la reprend** là où elle s’est arrêtée. Un morceau en cours quand le processus s’est arrêté est remis dans la file.

## Rien n’est perdu si une amélioration échoue

Chaque écriture va dans une copie de travail à côté de l’original (`<nom>.downtify-upgrade.<ext>`). La copie doit s’ouvrir comme un audio de même durée avant d’être mise en place ; sinon elle est jetée et l’original reste intact. Ce fichier n’apparaît jamais comme un morceau à part entière, et il disparaît dès que le morceau est terminé.

La **date de modification d’origine est conservée**, si bien qu’améliorer une bibliothèque ne rebat pas _Ajouts récents_.

### Dossiers de musique en lecture seule

Une amélioration réécrit les tags sur place, donc les morceaux d’un système de fichiers en lecture seule sont **ignorés**, avec une explication, avant la recherche de métadonnées, pochettes ou paroles. Ils restent lisibles et dans leurs playlists ; leurs fichiers et les permissions de montage restent inchangés. Un morceau en lecture seule ignoré n’est pas retenu comme vérifié avec succès, il peut donc être reconsidéré si son dossier devient accessible en écriture plus tard. Les erreurs inattendues de permission, d’espace disque et d’E/S apparaissent toujours comme des échecs.

Cela diffère de l’[enrichissement des dossiers existants](external-library.md), qui peut conserver pochettes et paroles séparément dans le dossier de données de Downtify sans réécrire des fichiers audio protégés.

## Pourquoi l’audio n’est pas remplacé

Les améliorations ordinaires de tags ne remplacent pas l’audio. Le mode distinct ci-dessous exige des métadonnées d’enregistrement exactes et une référence de publication ; les versions incertaines restent pour une revue manuelle.

## Remplacement des enregistrements par Deemix

Après avoir activé et testé la [source Deemix](deemix.md), **Améliorer la bibliothèque** propose deux interrupteurs indépendants avant l’analyse :

- **Utiliser les versions Deemix vérifiées** : analyse les téléchargements d’origine de Downtify, y compris les copies masquées par une collection externe préférée. Apparie exactement l’artiste, le titre/la version complète et l’album ; rejette les résultats ambigus du catalogue. La durée de l’ancien extrait n’est pas utilisée pour rejeter un enregistrement correct du catalogue. Vérifie les tags téléchargés, la durée du catalogue, la qualité choisie et le décodage complet par FFmpeg.
- **Nettoyer les anciennes copies Downtify après import** : supprime en plus chaque original inchangé après la publication. Désactivé par défaut. Conserver les originaux met quand même à jour playlists et favoris vers l’enregistrement Deemix.

Cette analyse produit une catégorie **audio** au lieu de tâches pochette/paroles/tags. Deemix possède les fichiers de sortie, la pochette, l’organisation des albums et les paroles natives. Downtify les lit sur place. Les paroles natives ou intégrées existantes sont conservées ; seules les paroles absentes peuvent être complétées dans un dossier de paroles dédié et accessible en écriture, sans réécrire l’audio. Un original sans perte de meilleure qualité est conservé quand Deemix est configuré pour le MP3.

La publication a lieu une fois par lot. Les commentaires M3U, les marqueurs manuels et l’ordre des morceaux sont conservés, puis les chemins du catalogue, les appartenances aux playlists, les mentions J’aime de chaque utilisateur, la propriété et les règles de morceaux masqués passent en une seule transaction SQLite. Les identifiants Navidrome en cache des anciens fichiers sont invalidés pour une nouvelle recherche native. Les identifiants mobiles déjà émis et les anciennes URL de lecture gardent des alias en lecture seule vers le remplaçant enregistré ; les mutations n’utilisent jamais ces alias d’URL.

Des reçus durables dans la base de la bibliothèque enregistrent les valeurs SHA-256 source/cible et l’état de publication. Les sources restent jusqu’à vérification du remplaçant et des références. Un montage modifié ou absent, un fichier modifié, une référence externe en lecture seule dans une playlist, une lecture active ou un échec de publication du catalogue arrêtent le nettoyage avec un motif visible. Pause/reprise et redémarrage réutilisent les reçus. Il n’y a pas de balayage général des doublons ni de nettoyage selon l’âge : seuls les originaux vérifiés dans le dossier de téléchargements de Downtify sont éligibles. Les téléchargements manuels Deemix/slskd, les originaux externes, les répertoires et les sidecars ne sont jamais supprimés. Une fois un original supprimé, revenir en arrière sur le conteneur ne restaure pas ce fichier ; restaurez-le depuis votre propre sauvegarde si besoin.

Pour les consommateurs NAS dont les noms de montage diffèrent des chemins Docker, un administrateur peut définir `DOWNTIFY_DEEMIX_M3U_ROOT` sur un alias de conteneur qui résout vers la racine de Deemix. Les chemins M3U relatifs utilisent cet alias (par exemple `/Download` associé à `/music/existing`). `DOWNTIFY_LIBRARY_READY_MARKERS`, facultatif, est un objet JSON de chemins de marqueurs et de texte attendu, vérifié avant la préparation et le nettoyage. Un marqueur manquant échoue par sécurité. Aucune des deux variables n’est requise pour le mode par défaut.

L’API d’analyse accepte `replace_audio_deemix: true`, éventuellement `delete_replaced_audio: true`, et éventuellement `files: ["relative/original.mp3"]` pour un pilote limité. Lancer cette analyse sélectionne `categories: ["audio"]`. L’état du passage inclut les compteurs de remplacement et une `finalization_error` quand la publication se met en pause. Aucun fichier source n’est supprimé simplement parce qu’un élément de la file Deemix indique terminé.

### Examiner un enregistrement incertain

Une tâche audio ignorée ou en échec propose **Choisir une piste Deezer**. Collez le lien exact d’un morceau, prévisualisez son artiste, son album et sa durée, puis choisissez **Analyser ce choix**. Cela ne prépare qu’une nouvelle analyse d’un seul morceau ; confirmez cette analyse pour lancer le remplacement. L’appariement automatique par défaut ne devine jamais un autre album.

Ce choix explicite peut corriger une ancienne étiquette d’album, mais le titre/la version complète et l’artiste doivent toujours correspondre. Un original explicite connu ne peut pas devenir silencieusement une version clean. L’enregistrement choisi subit les mêmes contrôles de durée, qualité, décodage, référence et suppression. Un autre choix ne peut pas réutiliser silencieusement un reçu déjà préparé. La charge utile avancée de l’analyse enregistre le choix sous `deemix_recordings: {"relative/original.mp3": "123456"}` ; il est propre à ce fichier et enregistré pour redémarrage/reprise.

## API

| Méthode | Chemin | Description |
|---|---|---|
| `GET` | `/api/library/upgrade` | État du passage, compteurs de la file et ce que l’analyse a trouvé |
| `GET` | `/api/library/upgrade/jobs` | Lignes par morceau (`status`, `stage`, `detail`) |
| `POST` | `/api/library/upgrade/scan` | Analyse la bibliothèque ; n’écrit rien |
| `POST` | `/api/library/upgrade/start` | Lance le passage pour les `categories` choisies |
| `POST` | `/api/library/upgrade/pause` | S’arrête après le morceau en cours, garde la file |
| `POST` | `/api/library/upgrade/resume` | Reprend un passage en pause |
| `POST` | `/api/library/upgrade/cancel` | Abandonne le reste de la file |

La progression est aussi poussée via le [WebSocket](../api-reference.md#websocket) sous la forme `{"type": "library_upgrade", "upgrade": {…}}`.

Voir la [référence de l’API](../api-reference.md#library) pour les formes des requêtes et des réponses.
