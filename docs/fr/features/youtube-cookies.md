---
icon: lucide/cookie
---

# Cookies YouTube

Downtify récupère son audio sur YouTube. La plupart du temps, cela fonctionne de façon anonyme — mais pas toujours :

- **Titres explicites / soumis à une limite d’âge.** YouTube ne les sert qu’à un compte adulte connecté. Sans cookies, le téléchargement échoue.
- **Défis anti-bot.** Sur des IP de centres de données (VPS, certains VPN), YouTube répond périodiquement « Connectez-vous pour confirmer que vous n’êtes pas un robot » au lieu de l’audio.

Fournir un `cookies.txt` règle les deux : yt-dlp parle alors à YouTube comme le fait votre session connectée dans le navigateur.

## Envoyer un cookies.txt (recommandé)

1. Installez une extension d’export de cookies : [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome/Edge) ou [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox)
2. Ouvrez `youtube.com` **connecté à votre compte Google** et exportez les cookies de ce site — le fichier doit être au format **Netscape**
3. Dans Downtify, ouvrez **Paramètres** (⚙️) → **Cookies YouTube** → **Envoyer cookies.txt**

Le fichier est validé à l’envoi — un fichier qui n’est pas un cookie jar Netscape est refusé immédiatement plutôt que de casser en silence tous les téléchargements suivants. S’il ne contient aucun cookie `youtube.com` ou `google.com`, vous recevez un avertissement, car cela signifie généralement qu’il a été exporté depuis le mauvais onglet.

Une fois envoyé, vous pouvez le **remplacer** (en envoyant un autre fichier) ou le **supprimer** depuis le même écran.

::: tip C’est la voie indépendante de la plateforme
Envoyer via l’interface web ne demande ni bind mount, ni chemin de fichier, ni shell — ce qui permet de l’utiliser sur Docker Desktop pour Windows, où monter un `cookies.txt` dans le conteneur est réputé pénible.
:::

## Où il est stocké

Le fichier envoyé est écrit sous le nom `cookies.txt` dans le répertoire de données de Downtify (`/data` par défaut) — le même volume que celui qui contient `settings.json` et la base de données de la Surveillance de playlists. Il **survit donc aux mises à jour du conteneur** : récupérer une nouvelle image et recréer le conteneur conserve vos cookies, tant que `/data` reste un volume nommé ou un bind mount.

## Utiliser plutôt une variable d’environnement

La variable [`DOWNTIFY_COOKIES_FILE`](../getting-started/environment-variables.md#anti-bot-youtube), qui existait déjà, fonctionne toujours et **est prioritaire** :

```yaml
services:
  downtify:
    volumes:
      - ./cookies.txt:/cookies.txt
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

Montez-le en écriture (sans `:ro`) pour que l’entretien puisse y enregistrer les cookies renouvelés ; un fichier en lecture seule reste utilisé, mais se périme comme avant.

Lorsqu’elle est définie, l’écran des paramètres affiche la section des cookies verrouillée et refuse les envois et suppressions — le déploiement est propriétaire de cette configuration, et Downtify ne doit pas écraser un fichier qu’il ne gère pas. Supprimez la variable (et recréez le conteneur) pour gérer les cookies depuis l’interface web.

`DOWNTIFY_COOKIES_FROM_BROWSER` lit les cookies directement dans un profil de navigateur, mais cela exige que le magasin de cookies du navigateur soit accessible *dans* le conteneur ; c’est donc rarement utilisable avec Docker.

## Les garder fonctionnels

Les cookies exportés n’expirent pas à une date fixe. La session Google est un ensemble de cookies qui change sans cesse : l’onglet d’où ils viennent fait tourner `__Secure-1PSIDTS`, `SIDCC` et les autres toutes les quelques minutes, et une copie qui n’apprend jamais les nouvelles valeurs finit par être refusée. yt-dlp journalise alors « The provided YouTube account cookies are no longer valid ». Derrière un VPN ou une IP de datacenter, YouTube est plus strict : cela peut arriver en quelques heures.

Downtify garde lui-même le fichier envoyé connecté :

- **Chaque téléchargement enregistre les nouvelles valeurs.** yt-dlp reçoit une copie privée du fichier pour chaque téléchargement ; à la fin, les cookies que YouTube a changés pendant celui-ci sont réintégrés dans le `cookies.txt` stocké, sans annuler une valeur plus récente enregistrée entre-temps par un autre téléchargement.
- **Un entretien les rafraîchit à intervalle régulier.** Toutes les 15 minutes (`DOWNTIFY_COOKIES_REFRESH_MINUTES`, `0` le désactive), Downtify demande à Google de faire tourner les cookies de session — la même requête que le navigateur —, ouvre `youtube.com` avec eux et enregistre ce qui a changé. Même un serveur qui ne télécharge rien pendant des jours garde une session vivante.
- **L’écran des paramètres affiche le résultat.** **Paramètres → Cookies YouTube** indique *Connecté*, *Déconnecté*, *Aucun compte* (le fichier ne contient pas de session Google, seulement des cookies de visiteur) ou *Échec de la vérification*, la date de la dernière vérification et celle du dernier contrôle anti-bot de YouTube. *Vérifier* lance l’entretien immédiatement. Un nouvel envoi est vérifié quelques secondes après son enregistrement.

Ce qui reste à votre charge :

- **Exportez depuis une fenêtre privée, puis fermez-la.** Connectez-vous à YouTube dans une fenêtre privée, ouvrez `youtube.com/robots.txt` dans cet onglet, exportez les cookies, puis fermez la fenêtre. Un onglet que vous continuez d’utiliser fait tourner la session lui-même, et la copie de Downtify est déconnectée en quelques minutes. Évitez si possible d’utiliser le même compte dans une fenêtre normale en même temps.
- **Envoyez un nouveau fichier quand l’écran indique *Déconnecté*.** Google peut toujours mettre fin à la session (changement de mot de passe, « se déconnecter de tous les appareils », contrôle de sécurité). Le journal le dit aussi : `YouTube cookies are signed out`.
- Certaines régions exigent une vérification complète d’identité sur le compte Google avant que YouTube ne serve le moindre contenu soumis à une limite d’âge. Être connecté ne suffit pas toujours.

::: info Pourquoi il n’y a pas de bouton « Se connecter avec Google »
Downtify ne peut pas se connecter à Google à votre place. Google bloque les connexions scriptées et les navigateurs headless (« Ce navigateur ou cette application ne sont peut-être pas sécurisés »), demande la validation en deux étapes et des confirmations sur l’appareil, et YouTube n’accepte plus OAuth pour les clients tiers comme yt-dlp. Un formulaire de connexion dans Downtify impliquerait aussi de lui confier votre mot de passe Google. Garder vivante une session exportée est la partie qui peut être automatisée.
:::

::: tip Contrôles anti-bot sans compte
« Sign in to confirm you're not a bot » dépend de l’adresse IP, pas de l’absence de cookies. S’il revient sans cesse derrière un VPN, changer de serveur ou de pays de sortie aide souvent plus que de nouveaux cookies. Des cookies utilisés pour beaucoup de téléchargements augmentent aussi le risque que YouTube limite ce compte : un compte jetable est le choix le plus sûr.
:::

::: warning Traitez le fichier comme un mot de passe
Un `cookies.txt` contient des jetons de session actifs de votre compte Google. Quiconque peut le lire peut agir en votre nom sur YouTube. Downtify le stocke avec des permissions réservées au propriétaire là où le système de fichiers le permet, et n’expose jamais son contenu via l’API — seulement s’il y en a un de configuré, sa taille et la date de son dernier changement. Utilisez un compte Google jetable si vous préférez ne pas risquer le principal.
:::
