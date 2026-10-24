---
icon: lucide/users
---

# Utilisateurs et connexion

Toute personne qui utilise Downtify se connecte avec un **nom d’utilisateur et un mot de passe**, et chacun peut avoir son propre compte. Un admin gère les comptes dans **Paramètres → Utilisateurs** et voit ce que fait chacun dans **Paramètres → Activité**.

## Se connecter pour la première fois

Un nouveau serveur a un compte :

| Nom d’utilisateur | Mot de passe |
|----------|----------|
| `admin` | `downtify` |

Connectez-vous avec lui et **changez le mot de passe** dans **Paramètres → Général → Compte** : quiconque connaît Downtify connaît le mot de passe par défaut. Tant que vous ne l’avez pas fait, Downtify vous le rappelle après la connexion et affiche un avertissement dans les Paramètres.

::: warning Changez le mot de passe par défaut avant d’exposer le serveur
Le mot de passe par défaut ne protège rien. Changez-le avant de rendre Downtify accessible depuis l’extérieur de votre réseau domestique — et utilisez le HTTPS (voir [Derrière un proxy inverse](mobile-apps.md#behind-a-reverse-proxy)).
:::

### Mise à jour depuis une ancienne version

Un serveur qui tournait sous une version sans comptes obtient le même compte `admin`, et la page de connexion l’indique une fois — jusqu’à ce qu’un admin se connecte — avec le nom d’utilisateur et le mot de passe à utiliser :

- Si vous aviez défini un mot de passe avec l’ancienne option **Exiger la connexion**, ce mot de passe continue de fonctionner pour `admin`.
- Sinon, c’est `downtify`.

Les navigateurs connectés avant la mise à jour se reconnectent. Les téléphones associés avant restent associés, et appartiennent maintenant à `admin`.

## Admins et utilisateurs

| | Admin | Utilisateur |
|---|---|---|
| Écouter, rechercher, télécharger, aimer, Découvrir, Classements, Finder, podcasts | ✓ | ✓ |
| Associer des applications mobiles (à leur propre compte) | ✓ | ✓ |
| Paramètres → Général (leur propre compte et préférences), Applications, À propos | ✓ | ✓ |
| Tous les autres paramètres (sources, fichiers, tags, Navidrome, bibliothèque, serveur), renommer le serveur | ✓ | |
| [Partager leurs propres playlists](#sharing-playlists) (en lecture seule), suivre les publiques, enregistrer des copies | ✓ | ✓ (quand l’admin l’autorise) |
| Supprimer des fichiers et des playlists (un utilisateur seulement [ce qu’il a téléchargé](#deleting-songs) et ses propres playlists), gérer ses propres surveillances de playlists et abonnements aux podcasts, remplacer l’audio d’un morceau, modifier les photos d’artistes | ✓ | ✓ (les siens uniquement) |
| [Masquer des morceaux, albums et artistes aux utilisateurs](#hiding-from-users) | ✓ | |
| Gérer les utilisateurs, voir le journal d’activité | ✓ | |

Un utilisateur qui tente quelque chose qui exige un admin reçoit un message l’indiquant.

## Votre bibliothèque

La bibliothèque est partagée : chaque compte voit tous les morceaux que n’importe qui a téléchargés — dans la Bibliothèque, dans les résultats de recherche marqués comme téléchargés, et sur un téléphone associé. Les fichiers ne sont jamais stockés deux fois : quand deux personnes téléchargent le même morceau, il arrive une fois sur le disque, avec un propriétaire chacun.

Les mentions J’aime, les playlists (téléchargées et créées dans la Bibliothèque) et la file de téléchargement restent à vous, sauf si vous êtes admin — ou si vous [partagez une playlist](#sharing-playlists) pour que d’autres la voient. L’écoute est partagée — chacun peut lire, écouter en aperçu ou diffuser n’importe quel morceau, et ajouter ce qu’il veut à ses propres playlists. Demander un morceau que quelqu’un d’autre est déjà en train de télécharger rejoint sa tâche au lieu de le récupérer deux fois : une ligne dans la file, un téléchargement et une propriété chacun — chaque personne en attente voit sa place dans la file.

Les podcasts, les surveillances de playlists et l’historique de Découvrir fonctionnent de la même façon : chaque compte s’abonne à ses propres émissions, suit ses propres playlists et artistes, et entraîne ses propres suggestions. Un admin voit les lignes de tous les comptes. L’écoute elle-même reste partagée — chacun peut lire, écouter en aperçu ou diffuser n’importe quel morceau.

### Partager des playlists

Une playlist est privée pour son propriétaire (et les admins) jusqu’à ce que son propriétaire la partage, depuis **Partager…** sur la page de la playlist ou dans son menu **⋯**. La lecture est déjà partagée entre les comptes ; il ne s’agit ici que de savoir qui peut *voir* une liste. Toute playlist peut être partagée sauf *Titres likés*, y compris les playlists importées.

| Visibilité | Qui la voit |
|------------|-------------|
| **Privée** | Seulement le propriétaire et les admins — par défaut |
| **Certaines personnes** | Les noms d’utilisateur choisis par le propriétaire |
| **Publique** | Tout le monde sur le serveur |

Les playlists des autres ne se mélangent jamais aux vôtres. L’onglet **Playlists** de la Bibliothèque les liste en deux sections sous les vôtres, chaque entrée portant le nom de son propriétaire :

- **Partagées avec moi** — playlists qui vous sont destinées nommément, toujours affichées. Une playlist fraîchement partagée porte un repère **Nouveau** jusqu’à ce que vous l’ouvriez.
- **Playlists publiques** — les publiques de tout le monde, triées par propriétaire et par nom, avec recherche grâce au filtre de l’onglet, indiquant le propriétaire, le nombre de morceaux et si vous la suivez. La section démarre repliée, et vous pouvez la masquer entièrement avec **Paramètres › Général › Afficher les playlists publiques** (activé par défaut ; c’est le vôtre, comme le thème).

La barre latérale affiche aussi quelques-unes de celles partagées avec vous et des playlists publiques que vous suivez.

**Ce que peut faire un lecteur :** lire, mélanger, ajouter à la file, télécharger en ZIP (ou vers une application mobile ou de bureau), **Suivre** une playlist publique pour qu’elle reste dans ses listes — même avec *Afficher les playlists publiques* désactivé — et suit les changements de son propriétaire, et **Enregistrer une copie** : une playlist privée et modifiable qui lui appartient, avec les morceaux qu’il peut voir. Un lecteur ne peut pas modifier, renommer, supprimer, partager ni détacher la playlist de quelqu’un d’autre.

**Arrêter le partage :** quand le propriétaire rend de nouveau une playlist privée, ou retire quelqu’un de la liste, elle quitte aussitôt les listes de cette personne (suivie ou non) ; une playlist qui cesse d’être publique n’est plus suivie. Les copies que des gens ont déjà enregistrées leur restent. Renommer une playlist partagée la garde partagée ; la supprimer emporte le partage avec elle. Les morceaux qu’un admin [masque aux utilisateurs](#hiding-from-users) sont écartés des morceaux d’une playlist partagée pour eux, comme partout.

Un admin peut tout désactiver avec **Paramètres › Bibliothèque › Autoriser les utilisateurs à partager des playlists** (activé par défaut). Tant que c’est désactivé, tout partage est masqué et personne ne peut partager ni suivre — les partages reviennent quand c’est réactivé.

Les applications associées reçoivent les mêmes listes : [`GET /api/v1/playlists`](../api-reference.md#get-apiv1playlists) indique à qui appartient chacune et si elle est en lecture seule, et `playlists_changed` sur le WebSocket leur dit d’actualiser.

### Masquer aux utilisateurs

Les admins décident de ce que voient les autres comptes. Tout est visible pour tous jusqu’à ce qu’un admin masque quelque chose : un **morceau**, un **album** entier ou un **artiste** entier. Les éléments masqués quittent la Bibliothèque, les repères « dans la bibliothèque » de la recherche, les listes de morceaux des playlists et ce qu’un téléphone associé synchronise — pour les utilisateurs, pas pour les admins.

- **Dans la Bibliothèque**, ouvrez le menu `…` d’un morceau, album ou artiste et choisissez **Masquer aux utilisateurs** (ou **Afficher aux utilisateurs** pour annuler). Dans l’onglet Titres, sélectionnez plusieurs morceaux et utilisez **Masquer aux utilisateurs** dans la barre de sélection.
- Les admins continuent de tout voir. Ce qui est masqué porte un petit œil barré, et son infobulle dit pourquoi : masqué en propre, avec son album, ou avec son artiste.
- **Paramètres › Utilisateurs › Masqué aux utilisateurs** liste chaque artiste, album et morceau masqué, avec **Afficher aux utilisateurs** à côté de chacun.
- Un morceau masqué le reste quand il est déplacé dans un autre dossier, et quand [Améliorer la bibliothèque](library-upgrade.md) ou [Remplacer l’audio](replace-audio.md) réécrivent son fichier. Supprimer le fichier oublie la règle.
- Une règle d’album correspond à l’artiste et au titre de l’album, et une règle d’artiste à l’artiste sous lequel la Bibliothèque regroupe le morceau — les mêmes noms que ceux des onglets Albums et Artistes de la Bibliothèque.

::: info Masquer concerne ce qui est listé
Cela contrôle ce que les comptes voient dans l’application, pas qui peut récupérer un fichier dont ils connaissent déjà l’adresse. Ne l’utilisez pas pour protéger des fichiers sensibles.
:::

Masquer et afficher sont consignés dans le [journal d’activité](#activity).

### Supprimer des morceaux

Supprimer un morceau le retire du disque pour tout le monde, donc cela suit celui qui l’a téléchargé. Un admin peut tout supprimer. Un utilisateur peut supprimer un morceau qu’il a lui-même téléchargé ; quand quelqu’un d’autre a aussi téléchargé le même morceau, supprimer ne fait qu’abandonner sa propre revendication et le morceau reste dans la bibliothèque partagée. Un morceau que personne n’a téléchargé via un compte (un passage du suivi de playlists, un téléchargement d’avant les comptes, un [dossier supplémentaire](external-library.md)) ne peut être supprimé que par un admin. Supprimer une de vos playlists n’emporte jamais les fichiers de quelqu’un d’autre.

### Utilisation par compte

**Paramètres › Utilisateurs** liste, sous chaque compte, ce qu’il détient : morceaux et leur taille, mentions J’aime, playlists, téléchargements demandés et trafic dans les deux sens (récupéré en amont vs. servi aux clients), avec les totaux de tout le monde en dessous. « Morceaux » compte les morceaux qu’un compte a téléchargés, pas ce qu’il peut voir.

## Votre compte et vos préférences

**Paramètres → Général** commence par votre **Compte** : changez votre nom d’utilisateur ou votre mot de passe, ou déconnectez-vous. Vous pouvez aussi vous déconnecter depuis la barre latérale (ou **Plus** sur téléphone).

Le reste de **Général** — thème, langue, affichage des paroles dans le lecteur, albums dans les résultats de recherche — est **à vous** : il vous suit dans chaque navigateur où vous vous connectez, et ne change rien pour personne d’autre.

**Paramètres → Applications** liste les téléphones associés à votre compte (un admin voit ceux de tout le monde, avec leur propriétaire). **Se déconnecter partout** dissocie vos applications et vous déconnecte de tous les navigateurs.

## Gérer les utilisateurs

Dans **Paramètres → Utilisateurs**, un admin peut :

- **Ajouter un utilisateur** — nom d’utilisateur (3 à 32 lettres, chiffres, `.`, `-` ou `_`), mot de passe (au moins 8 caractères) et rôle.
- **Modifier** un utilisateur — le renommer, le passer admin ou utilisateur, ou lui donner un nouveau mot de passe (ce qui le déconnecte de ses navigateurs ; ses applications restent associées).
- **Supprimer** un utilisateur — ses applications sont dissociées et ses navigateurs déconnectés. Ses fichiers restent sur le disque (les admins peuvent toujours les voir) ; ses mentions J’aime, playlists, abonnements aux podcasts, surveillances, historique de suggestions et compteurs de trafic partent avec lui.
- **Déconnecter tout le monde** — chaque application de chaque utilisateur est dissociée et chaque navigateur déconnecté, le vôtre compris.

Il y a toujours au moins un admin : le dernier ne peut pas être supprimé ni passé en utilisateur, et vous ne pouvez pas supprimer votre propre compte.

## Activité

**Paramètres → Activité** (admins) affiche, comme le tableau de bord de Jellyfin :

- **En cours de lecture** — ce que joue chaque navigateur et application, par qui, où en est le morceau, et s’il est en pause. Se rafraîchit toutes les quelques secondes.
- **Historique** — connexions (et échecs, avec l’adresse d’où ils venaient), déconnexions, morceaux lus, téléchargements, mentions J’aime, fichiers supprimés, morceaux masqués ou affichés aux utilisateurs, applications associées et dissociées, comptes ajoutés, modifiés ou supprimés, mots de passe et paramètres modifiés. Filtrez par utilisateur ou par type. Les paramètres enregistrés sont listés par nom seulement, jamais par leurs valeurs. Les entrées sont conservées 90 jours.

Les applications signalent aussi ce qu’elles lisent — voir le [contrat du client mobile](../mobile-client-contract.md#8-report-plays).

## Désactiver les comptes

Un serveur que vous seul pouvez joindre — sur votre propre ordinateur, ou derrière quelque chose qui demande déjà un mot de passe — n’a peut-être pas besoin de comptes. Définissez `DOWNTIFY_DISABLE_AUTH=true` (voir [Variables d’environnement](../getting-started/environment-variables.md#mobile-apps-and-sign-in)) :

```yaml
environment:
  - DOWNTIFY_DISABLE_AUTH=true
```

Alors :

- Il n’y a plus de page de connexion : quiconque ouvre Downtify l’utilise comme premier admin (`admin` sur un nouveau serveur).
- Les boutons de déconnexion, **Paramètres → Utilisateurs**, la partie **Compte** de **Paramètres → Général** et **Se déconnecter partout** dans **Paramètres → Applications** disparaissent.
- Les téléphones peuvent toujours être associés (à cet admin), et **Paramètres → Activité** montre toujours ce qui se joue où.
- Le thème, la langue et les autres préférences de **Général** sont conservés comme ceux de cet admin.

::: warning Quiconque peut joindre le serveur peut tout faire
Avec les comptes désactivés, rien ne demande qui vous êtes : tout le monde sur votre réseau — ou sur Internet, si le port est exposé — peut modifier les paramètres, supprimer de la musique et associer un téléphone. Ne désactivez pas les comptes sur un serveur que d’autres peuvent joindre.
:::

Remettez `false` (ou supprimez-la) et la connexion est de nouveau exigée, avec les comptes, mots de passe et applications comme avant.

## Mot de passe oublié ?

Exécutez ceci sur le serveur — `admin` retrouve le mot de passe `downtify` (et est recréé comme admin s’il a été renommé ou supprimé) ; les autres comptes et les applications associées sont laissés tels quels :

```bash
docker exec downtify python main.py auth-reset
```

En dehors de Docker, exécutez `python main.py auth-reset` (ou `uv run python main.py auth-reset`) dans le dossier de Downtify. Puis connectez-vous et changez le mot de passe.

## Scripts et API

Chaque appel d’API exige maintenant des identifiants (voir la [référence de l’API](../api-reference.md#server-and-sign-in)). Un script peut se connecter avec `POST /api/auth/login` et conserver le cookie `downtify_session`, ou utiliser le jeton d’un appareil associé.
