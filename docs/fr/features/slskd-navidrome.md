---
icon: lucide/share-2
---

# slskd et Navidrome

Deux intégrations facultatives pour les bibliothèques auto-hébergées :

- **[slskd](https://github.com/slskd/slskd)** — téléchargez des morceaux du réseau Soulseek via votre propre serveur slskd, comme source audio supplémentaire à côté de YouTube Music et YouTube.
- **[Navidrome](https://www.navidrome.org/)** — répliquez dans Navidrome les playlists que vous téléchargez, pour qu’elles apparaissent dans n’importe quel client Subsonic.

Les deux sont désactivées par défaut et se configurent dans **Paramètres**.

## Sources audio et ordre de repli

**Paramètres → Sources audio** est une liste ordonnée. Touchez une source pour l’ajouter ou la retirer ; avec plus d’une sélectionnée, utilisez les flèches pour les réordonner. Chaque morceau essaie les sources dans cet ordre et s’arrête à la première qui fournit de l’audio :

| Source | Ce qu’elle fait |
|--------|-------------|
| **YouTube Music** | Celle par défaut. Cherche sur YouTube Music, en se rabattant sur YouTube standard quand il n’y a pas de correspondance acceptable — voir [Comment ça marche](../how-it-works.md#fallback-to-standard-youtube). |
| **YouTube** | Cherche uniquement sur YouTube standard. |
| **slskd** | Cherche sur Soulseek via slskd et télécharge le fichier qui correspond le mieux. |

Activer slskd le place en premier dans la liste. Si slskd finit par être la seule source, YouTube Music et YouTube sont quand même essayés après lui, si bien qu’un morceau que slskd ne trouve pas se télécharge quand même. La file de téléchargement indique quelle source a servi chaque morceau.

## slskd

### Configuration

1. Lancez slskd et créez une clé d’API pour Downtify (voir la documentation de slskd).
2. Montez le dossier de téléchargements de slskd dans le conteneur Downtify — le même dossier de l’hôte que celui où slskd écrit. Voir [Docker Compose → Avec slskd](../getting-started/docker-compose.md#with-slskd-soulseek).
3. Dans **Paramètres → slskd (Soulseek)**, activez slskd et renseignez :
    - **URL de slskd** — par ex. `http://slskd:5030` quand les deux conteneurs partagent un réseau Docker.
    - **Clé d’API**.
    - **Dossier de téléchargements** — le chemin *dans le conteneur Downtify* où ce dossier est monté (par défaut `/slskd`), pas le chemin de l’hôte.

L’enregistrement est refusé avec un message d’erreur si slskd est activé sans URL ou clé d’API.

### Tester la connexion

Appuyez sur **Tester la connexion** sous les champs pour les vérifier avant d’enregistrer — il utilise ce qui est saisi dans le formulaire, enregistré ou non, et ne modifie rien. Il indique :

| Résultat | Ce que cela signifie |
|--------|---------------|
| **Connecté à slskd 0.21.4.** | L’adresse est correcte et la clé d’API a été acceptée |
| **slskd est connecté à Soulseek.** / **n’est pas connecté** | Si slskd lui-même est connecté au réseau Soulseek. Sinon, les recherches ne trouvent rien tant qu’il ne l’est pas — un avertissement, puisque les réglages eux-mêmes sont corrects |
| **Downtify peut lire `/slskd`.** / **ne peut pas lire** | Si le dossier de téléchargements ci-dessus existe dans *ce* conteneur et est lisible. La cause habituelle d’un avertissement est un dossier non monté — voir [Configuration](#setup) |
| **slskd a rejeté la clé d’API.** | Le serveur a répondu, mais pas à cette clé |
| **Impossible de joindre … / n’a pas répondu à temps.** | Mauvaise adresse ou mauvais port, le serveur est arrêté, ou il n’est pas joignable depuis le conteneur Downtify |
| **Ne ressemble pas à slskd.** | Quelque chose a répondu, mais pas slskd — souvent un mauvais port, ou un chemin de base manquant dans l’adresse |
| **Le certificat HTTPS n’est pas approuvé.** | Utilisez `http://` sur votre propre réseau, ou un certificat d’une autorité approuvée ; Downtify ne contourne pas la vérification des certificats |

Modifier un champ efface le dernier résultat, puisqu’il ne décrit plus ce qui est dans le formulaire. Le bouton reste désactivé tant que l’adresse et la clé ne sont pas renseignées.

### Comment un morceau est apparié

Downtify cherche dans slskd avec le titre et l’artiste du morceau et classe les résultats selon la proximité du nom de fichier et de la durée avec le morceau. À correspondance égale, il préfère le MP3, puis le FLAC, et ignore les fichiers qui annoncent un débit inférieur à 256 kbps. Il essaie jusqu’à cinq candidats, l’un après l’autre. Quand un transfert se termine, Downtify vérifie les tags et la durée du fichier par rapport au morceau avant de le conserver.

Si rien d’acceptable ne se présente, que le transfert ne se termine pas dans le **Délai total**, ou qu’il reste en file chez le pair distant sans progresser plus longtemps que le **Délai en file**, Downtify passe à la source audio suivante.

### Laisser les fichiers en place

Avec **Laisser les fichiers slskd en place** activé (par défaut), le fichier téléchargé reste dans le dossier de slskd : Downtify y écrit les métadonnées, la pochette et les paroles, et l’enregistre dans la bibliothèque sous un chemin `slskd/…`. La Bibliothèque, le lecteur et les fichiers M3U utilisent ce chemin, servi via `/media/slskd/…`.

Désactivez-le pour copier le fichier à côté de vos autres téléchargements, selon votre modèle de nom de fichier et les réglages d’[organisation des fichiers](file-organization.md).
Le transfert lui-même reste dans le dossier slskd ; [Stockage et utilisation](storage-usage.md#the-library-not-its-working-copies) compte ces copies à part de la bibliothèque, comme *copies de travail slskd*, pour que vous voyiez la place qu’elles prennent.

::: info
Les fichiers slskd gardent leur format d’origine — ils ne sont pas transcodés vers le format choisi dans les Paramètres.
:::

## Navidrome

### Configuration

1. Assurez-vous que le dossier de musique de Navidrome inclut le dossier de téléchargements de Downtify (et le dossier de slskd, si vous laissez les fichiers slskd en place). Navidrome ne peut ajouter des morceaux à une playlist qu’après les avoir analysés.
2. Dans **Paramètres → Navidrome**, activez Navidrome et saisissez son URL, son nom d’utilisateur et son mot de passe.
3. Facultativement, ajoutez un nom d’utilisateur et un mot de passe d’**admin**. Downtify demande alors à Navidrome d’analyser la bibliothèque avant d’apparier les nouveaux morceaux, au lieu d’attendre l’analyse planifiée de Navidrome.

### Tester la connexion

Appuyez sur **Tester la connexion** sous les champs pour les vérifier avant d’enregistrer — il utilise ce qui est saisi dans le formulaire, enregistré ou non, et ne modifie rien. Il indique :

| Résultat | Ce que cela signifie |
|--------|---------------|
| **Connecté à navidrome 0.53.3.** | L’adresse est correcte et le nom d’utilisateur et le mot de passe ont été acceptés |
| **Ce compte peut lancer des analyses de la bibliothèque.** | Le compte utilisé pour les analyses est admin. C’est le nom d’utilisateur admin que vous avez renseigné, ou le normal si vous l’avez laissé vide |
| **Ce compte ne peut pas lancer d’analyses de la bibliothèque.** | Navidrome ne laisse que les admins lancer une analyse, et ne le dit pas quand Downtify essaie — les nouveaux morceaux apparaissent simplement en retard. Renseignez un nom d’utilisateur et un mot de passe d’admin |
| **Le compte admin n’est pas admin.** | L’identifiant admin saisi fonctionne mais appartient à un utilisateur normal |
| **Navidrome a rejeté le nom d’utilisateur ou le mot de passe admin.** | L’identifiant du compte d’analyse est faux ; l’identifiant principal est signalé séparément |
| **Navidrome a rejeté le nom d’utilisateur ou le mot de passe.** | Le serveur a répondu, mais pas à cet identifiant |
| **Impossible de joindre … / n’a pas répondu à temps.** | Mauvaise adresse ou mauvais port, le serveur est arrêté, ou il n’est pas joignable depuis le conteneur Downtify |
| **Ne ressemble pas à Navidrome.** | Quelque chose a répondu, mais pas l’API Subsonic — souvent un mauvais port, ou une URL de base manquante dans l’adresse |
| **Le certificat HTTPS n’est pas approuvé.** | Utilisez `http://` sur votre propre réseau, ou un certificat d’une autorité approuvée ; Downtify ne contourne pas la vérification des certificats |

Les droits d’analyse sont seulement consultés — le test ne lance jamais d’analyse. Modifier un champ efface le dernier résultat, et le bouton reste désactivé tant que l’adresse, le nom d’utilisateur et le mot de passe ne sont pas renseignés.

::: info Rien n’est renvoyé à la page
La réponse ne contient que ce qui a été trouvé — une version, un chemin, un état — jamais votre mot de passe ni la requête faite par Downtify.
:::

### Synchronisation des playlists

La réplication est configurée par les admins (Paramètres → Navidrome) ; les comptes ordinaires ne peuvent pas créer de miroirs, mais leurs téléchargements sont répliqués comme ceux de tout le monde une fois l’intégration activée.

Avec **Créer les playlists dans Navidrome** activé, Downtify crée (ou met à jour) une playlist Navidrome du même nom après :

- la fin du téléchargement d’une playlist Spotify,
- l’ajout de morceaux par un passage du [Suivi de playlists](playlist-monitor.md),
- la suppression de morceaux de la Bibliothèque, ou la [réparation des chemins de la bibliothèque](library-catalog.md#fix-library-paths).

Les morceaux sont appariés aux titres de Navidrome d’abord par chemin, puis par tags. **Rendre publiques les playlists Navidrome** contrôle la visibilité de la playlist dans Navidrome.

::: warning Les fichiers dont les tags ne correspondent pas à la playlist sont supprimés
Quand une playlist est actualisée (après des suppressions, **Réparer les chemins** ou **Télécharger les manquants** sur une playlist déjà complète), un fichier de la bibliothèque enregistré pour un morceau Spotify est **supprimé du disque** si son titre/artiste intégré ne correspond clairement pas à ce morceau — Downtify le traite comme un mauvais téléchargement. Gardez-le à l’esprit si vous modifiez les tags à la main.
:::

### Pochette de playlist

Rien à configurer : avec [Enregistrer la pochette de la playlist](playlist-cover-art.md) activé, Navidrome récupère le `.jpg` que Downtify écrit à côté du M3U de la playlist comme **image auxiliaire (sidecar)** — sa propre façon de résoudre l’image des playlists — tant que son dossier de musique couvre ce fichier. Downtify ne fait aucun appel d’API pour cela.

## Téléchargements de playlists

La page **Bibliothèque** liste sous **Téléchargements de playlists** les playlists Spotify que vous avez téléchargées via Downtify. Dépliez-la pour voir, pour chaque playlist, combien de morceaux sont dans votre bibliothèque par rapport à la liste actuelle des morceaux Spotify. De là, vous pouvez :

- **Télécharger les manquants** — met en file seulement les morceaux pas encore dans votre bibliothèque.
- **Lire** les morceaux déjà téléchargés.
- Déplier une playlist pour voir et télécharger individuellement les morceaux manquants.
- **Supprimer** la playlist — voir ci-dessous.

### Supprimer une playlist

Supprimer une playlist (depuis ce panneau, ou avec **Supprimer la playlist** à côté du filtre de playlists de la Bibliothèque) retire du disque chaque morceau qui lui est enregistré — **y compris les morceaux que d’autres playlists contiennent aussi** — ainsi que son fichier M3U et la [pochette](playlist-cover-art.md) enregistrée à côté, et cesse de la suivre. Les autres playlists qui partageaient ces morceaux voient leur M3U et leur playlist Navidrome réécrits en arrière-plan.
