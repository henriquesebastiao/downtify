---
icon: lucide/smartphone
---

# Applications mobiles

Downtify peut servir des applications sur votre téléphone : elles parcourent la bibliothèque et la diffusent directement depuis votre serveur, et gardent des morceaux sur le téléphone pour l’écoute hors ligne. Tout ce dont une application a besoin se règle dans **Paramètres → Applications** : l’association des téléphones et le nom du serveur. Qui peut utiliser le serveur est défini par les comptes de [Utilisateurs et connexion](users.md).

::: warning L’application est encore en développement
**Paramètres → Applications** est marqué *Expérimental*. La partie serveur décrite sur cette page est terminée et fonctionne, mais **aucune version de l’application Android n’a encore été publiée** ; il n’y a donc rien à installer pour l’instant, et les détails de l’association et de la diffusion peuvent encore changer d’une version de Downtify à l’autre.

L’application est développée en ouvert sur [henriquesebastiao/downtify-android](https://github.com/henriquesebastiao/downtify-android). Tout autre client peut être construit sur la même API — voir le [contrat du client mobile](../mobile-client-contract.md).
:::

## Se connecter depuis l’application

Saisissez l’adresse du serveur (ou choisissez-le sous **Trouvés sur ce réseau**), puis connectez-vous avec **les mêmes nom d’utilisateur et mot de passe** que sur la page web. Le téléphone apparaît sous **Applications associées**, exactement comme si vous l’aviez associé avec un code ci-dessous : il lit en tant que vous, garde une clé qui lui est propre (le mot de passe n’est pas stocké sur le téléphone) et **Dissocier** l’arrête.

Les mauvais mots de passe sont limités en même temps que la connexion de la page web. Tant que les comptes sont désactivés (`DOWNTIFY_DISABLE_AUTH`), il n’y a rien avec quoi se connecter : associez-le avec un code.

## Associer un téléphone

L’association ne demande aucun mot de passe sur le téléphone : pratique quand la page web est déjà ouverte, ou sur un téléphone où vous préférez ne pas saisir votre mot de passe.

1. Ouvrez **Paramètres → Applications** et appuyez sur **Associer un téléphone**.
2. Dans l’application, choisissez **Scanner le code** et pointez la caméra vers le QR code — ou saisissez le code de 8 caractères affiché dessous (`K7QM-2XPD` ; casse et tirets sans importance).
3. La boîte de dialogue confirme quand le téléphone est associé, et il apparaît sous **Applications associées**.

Le téléphone est associé à **votre compte** : il lit en tant que vous et apparaît dans votre activité. Toute personne avec un compte peut associer ses propres téléphones.

Un code ne fonctionne qu’**une seule fois**, pendant **cinq minutes**, et l’essai de mauvais codes est limité. Le téléphone reçoit une clé qui lui est propre et qu’il conserve ; le serveur n’en stocke qu’un hash.

**Applications associées** liste vos téléphones (un admin voit ceux de tout le monde, avec le propriétaire de chacun) avec leur plateforme, la date de dernière vue et l’adresse d’où. **Dissocier** arrête un téléphone immédiatement — sa prochaine requête échoue, une connexion ouverte est fermée et les liens qu’il a partagés (voir [Diffusion (cast)](#casting)) cessent de fonctionner. Pour le réutiliser, associez-le de nouveau.

## Ce qu’une application associée peut faire

Les applications associées peuvent parcourir, lire, aimer, garder des morceaux hors ligne et demander au serveur de télécharger de la musique — mais pas modifier les paramètres ni les identifiants ni supprimer des fichiers ; cela exige la page web, connecté en tant qu’admin.

**Paramètres → Applications → Se déconnecter partout** dissocie toutes vos applications et vous déconnecte de tous les navigateurs, celui-ci compris. La connexion, les comptes et le mot de passe oublié sont décrits dans [Utilisateurs et connexion](users.md).

## Trouver le serveur sur votre réseau

Le serveur s’annonce sur le réseau local (mDNS / Bonjour, en tant que `_downtify._tcp`), si bien qu’une application le liste sous **Trouvés sur ce réseau** — nom, adresse et version — sans rien saisir. Le nom est celui défini sous **Paramètres → Applications → Nom du serveur** (le nom d’hôte de la machine jusqu’à ce que vous le changiez).

::: info Le réseau par défaut de Docker masque l’annonce
Dans le réseau *bridge* par défaut de Docker, l’annonce reste à l’intérieur de Docker et les téléphones ne la voient pas. Lancez le conteneur avec `network_mode: host` (voir [Docker Compose](../getting-started/docker-compose.md#finding-the-server-from-the-apps)), ou saisissez l’adresse du serveur dans l’application — tout le reste fonctionne pareil.
:::

Définissez `DOWNTIFY_DISCOVERY=false` pour cesser d’annoncer.

## Qualité de diffusion

Les applications lisent les fichiers tels quels (**Original**) ou demandent au serveur une copie plus petite : Opus, AAC ou MP3 à 96–320 kbps — utile sur données mobiles. Le serveur fait cette copie avec ffmpeg la première fois qu’un morceau est lu ainsi (quelques secondes pour un morceau classique) et la conserve, si bien que la recherche dans le morceau fonctionne comme dans n’importe quel fichier et que la lecture suivante est instantanée.

- Un fichier déjà assez petit (un fichier avec perte à un débit égal ou inférieur à celui demandé) est diffusé tel quel, jamais ré-encodé.
- Les copies sont conservées dans `/data/transcode_cache`, 2 Go au maximum par défaut ; les moins récemment lues partent en premier. Deux au plus sont faites en même temps. Les deux limites sont des [variables d’environnement](../getting-started/environment-variables.md#mobile-apps-and-sign-in).
- Si le téléphone abandonne pendant qu’une copie est en cours, le serveur cesse de la faire.

## Diffusion (cast)

Les applications peuvent envoyer un morceau vers un Chromecast ou un autre lecteur qui récupère l’audio lui-même. L’application obtient du serveur un lien valable pour ce seul morceau pendant une durée limitée (une heure par défaut) et seulement tant que le téléphone reste associé ; aucune clé du téléphone n’y figure.

## Derrière un proxy inverse

Si Downtify se trouve derrière nginx, Caddy, Traefik ou équivalent (pour le HTTPS, ou pour y accéder de l’extérieur) :

- **Laissez passer le WebSocket.** `/api/ws` exige que les en-têtes `Upgrade`/`Connection` soient transmis (Caddy et Traefik le font par défaut ; nginx a besoin de `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";`).
- **Laissez passer les requêtes Range** telles quelles et ne mettez pas les réponses audio en mémoire tampon (nginx : `proxy_buffering off;` pour `/api/v1/` et `/downloads/`), sinon la recherche dans les morceaux et les gros fichiers en pâtissent.
- **Indiquez à Downtify quel proxy croire.** Définissez `DOWNTIFY_TRUSTED_PROXIES` sur l’adresse du proxy (par ex. `172.18.0.0/16`). Seulement alors Downtify utilise `X-Forwarded-For` pour l’adresse du client (limites de tentatives, « dernière vue » dans Applications associées) et `X-Forwarded-Proto`/`X-Forwarded-Host` pour marquer le cookie de connexion comme sécurisé et vérifier d’où viennent les requêtes. Sans cela, ces en-têtes sont ignorés — n’importe qui pourrait les envoyer.
- **Utilisez le HTTPS** quand le serveur est accessible de l’extérieur : le mot de passe et les clés des applications circulent à chaque requête.

## Pour les développeurs d’applications

Tout le parcours d’une application — découverte, association, synchronisation de la bibliothèque, diffusion, signalement des lectures — est décrit dans le [contrat du client mobile](../mobile-client-contract.md), et chaque endpoint figure dans la [référence de l’API](../api-reference.md#server-and-sign-in).
