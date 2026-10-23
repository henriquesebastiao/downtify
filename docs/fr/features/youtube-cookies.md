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
      - ./cookies.txt:/cookies.txt:ro
    environment:
      - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

Lorsqu’elle est définie, l’écran des paramètres affiche la section des cookies verrouillée et refuse les envois et suppressions — le déploiement est propriétaire de cette configuration, et Downtify ne doit pas écraser un fichier qu’il ne gère pas. Supprimez la variable (et recréez le conteneur) pour gérer les cookies depuis l’interface web.

`DOWNTIFY_COOKIES_FROM_BROWSER` lit les cookies directement dans un profil de navigateur, mais cela exige que le magasin de cookies du navigateur soit accessible *dans* le conteneur ; c’est donc rarement utilisable avec Docker.

## Les garder fonctionnels

- Les cookies expirent. Si les téléchargements soumis à une limite d’âge se remettent à échouer, exportez un nouveau fichier et envoyez-le en remplacement.
- Exporter depuis une **fenêtre privée/incognito** que vous fermez ensuite donne une session plus durable, car fermer une fenêtre normale peut invalider la session exportée.
- Certaines régions exigent une vérification d’identité complète du compte Google avant que YouTube serve le moindre contenu soumis à une limite d’âge. Être connecté ne suffit pas toujours.

::: warning Traitez le fichier comme un mot de passe
Un `cookies.txt` contient des jetons de session actifs de votre compte Google. Quiconque peut le lire peut agir en votre nom sur YouTube. Downtify le stocke avec des permissions réservées au propriétaire là où le système de fichiers le permet, et n’expose jamais son contenu via l’API — seulement s’il y en a un de configuré, sa taille et la date de son dernier changement. Utilisez un compte Google jetable si vous préférez ne pas risquer le principal.
:::
