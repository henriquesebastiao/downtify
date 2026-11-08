---
icon: lucide/life-buoy
---

# Dépannage

Les problèmes courants et ce qui les résout. La plupart des échecs de téléchargement se ramènent à l’une des deux premières entrées.

## Un titre au contenu explicite ne se télécharge pas

**Symptôme** — le téléchargement échoue et la file affiche un message indiquant que le titre est soumis à une limite d’âge, ou (sur les anciennes versions) une erreur brute du type :

```
Error: ERROR: [youtube] <id>: Sign in to confirm your age.
This video may be inappropriate for some users.
```

**Cause** — YouTube ne sert les titres soumis à une limite d’âge (explicites) qu’à un compte adulte connecté. Downtify télécharge anonymement par défaut ; YouTube refuse donc.

**Solution** — fournissez des cookies YouTube : **Paramètres** (⚙️) → **Cookies YouTube** → **Envoyer cookies.txt**. Voir [Cookies YouTube](features/youtube-cookies.md) pour savoir comment exporter le fichier.

Si cela échoue encore avec des cookies configurés, les cookies sont périmés ou le compte lui-même n’a pas terminé la vérification d’âge de Google. Exportez un nouveau fichier depuis un navigateur connecté à un compte vérifié et envoyez-le à nouveau.

## Les téléchargements échouent, expirent ou ne démarrent jamais

**Symptôme** — les téléchargements échouent pour des titres a priori ordinaires, parfois avec « Connectez-vous pour confirmer que vous n’êtes pas un robot » ou une erreur de format/d’extraction.

**Cause** — YouTube limite et met à l’épreuve les requêtes qu’il juge automatisées. C’est bien plus fréquent sur un VPS ou derrière un VPN que sur une connexion domestique.

**Solution**, par ordre d’efficacité habituelle :

1. **Envoyez un `cookies.txt`** ([Cookies YouTube](features/youtube-cookies.md)). Une session authentifiée est bien moins souvent mise à l’épreuve. C’est la correction la plus efficace.
2. **Ajoutez une pause entre les téléchargements** — **Paramètres** → *Pause entre téléchargements* (essayez 5–15 s) et réduisez les *Téléchargements simultanés*. Bombarder YouTube avec toute une playlist d’un coup est ce qui déclenche la limitation.
3. **Forcez l’IPv4** — définissez `DOWNTIFY_FORCE_IPV4=1` si votre hôte annonce l’IPv6 mais ne sait pas réellement l’acheminer (cela se manifeste par des erreurs DNS/`EAI_AGAIN`).
4. **Mettez l’image à jour** — `docker compose pull && docker compose up -d`. YouTube change souvent ses défenses et chaque version embarque un `yt-dlp` plus récent.

## Un cookies.txt sous Windows / Docker Desktop n’est pas pris en compte

**Symptôme** — `DOWNTIFY_COOKIES_FILE` est définie mais Downtify se comporte comme s’il n’y avait pas de cookies.

**Cause** — le chemin est un chemin *du conteneur*. Un chemin Windows comme `C:\Users\me\cookies.txt` ne signifie rien dans le conteneur, et le fichier doit être monté avant que la variable puisse le désigner.

**Solution** — laissez tomber la variable et envoyez le fichier via **Paramètres** → **Cookies YouTube**. Cette voie n’a besoin d’aucun montage et fonctionne de la même façon sur toutes les plateformes.

Si vous préférez garder la variable, montez le fichier et pointez vers la cible du montage, pas vers le chemin de l’hôte :

```yaml
volumes:
  - ./cookies.txt:/cookies.txt:ro
environment:
  - DOWNTIFY_COOKIES_FILE=/cookies.txt
```

## Le bouton d’envoi des cookies est grisé

`DOWNTIFY_COOKIES_FILE` est définie : ce déploiement gère donc son propre fichier de cookies et l’interface web reste volontairement en lecture seule. Supprimez la variable (et recréez le conteneur) pour gérer les cookies depuis l’interface.

## Les cookies envoyés ont disparu après la mise à jour du conteneur

Le fichier envoyé se trouve dans le répertoire de données de Downtify (`/data`). Si ce répertoire n’est ni un volume nommé ni un bind mount, tout ce qu’il contient — réglages et base de données de la Surveillance de playlists compris — est perdu quand le conteneur est recréé :

```yaml
volumes:
  - ./downloads:/downloads
  - downtify_data:/data   # ← gardez ceci
```

## « cookies.txt is invalid » à l’envoi

Downtify valide le fichier à l’envoi. Ce doit être un cookie jar **Netscape** : un cookie par ligne, champs séparés par des tabulations, éventuellement avec des commentaires `#`. Un export JSON, un tableur ou un en-tête `Cookie:` copié est refusé.

Utilisez une extension de navigateur qui exporte au format Netscape (voir [Cookies YouTube](features/youtube-cookies.md)) et exportez pendant que l’onglet est sur `youtube.com`.

## Une playlist retélécharge des titres que j’ai déjà

Downtify enregistre chaque titre téléchargé automatiquement dans sa base de données ; déplacer des fichiers ailleurs sur le disque ne déclenche donc pas de retéléchargement. Un titre n’est retéléchargé qu’après qu’une vérification horaire a constaté que son fichier manque réellement dans le répertoire de téléchargements. Voir [Surveillance de playlists](features/playlist-monitor.md#how-it-works).

Si des fichiers disparaissent à chaque redémarrage, le volume `/downloads` n’est pas persistant — même solution que ci-dessus.

## « Could not find a YouTube match for '…' »

Ni YouTube Music ni YouTube standard n’ont renvoyé de résultat passant les vérifications du comparateur — titre ressemblant à la source, au moins un artiste en commun, pas une version karaoké/reprise/live/dans une autre langue, et durée à 30 secondes ou moins de celle de Spotify. Voir [Comment ça marche](how-it-works.md#fallback-to-standard-youtube).

Cela signifie généralement que le morceau n’est vraiment pas sur YouTube, ou n’y est publié que sous un titre ou un crédit d’artiste très différent. Si vous trouvez vous-même la bonne vidéo, collez son URL YouTube dans la barre de recherche pour télécharger précisément cette vidéo.

## L’audio téléchargé a de mauvaises métadonnées ou une mauvaise pochette

Downtify récupère les métadonnées depuis Spotify et fait correspondre l’audio sur YouTube Music. Un décalage signifie généralement que la correspondance est tombée sur une reprise, un remix ou une version live. Télécharger depuis le lien de l’**album** Spotify plutôt que depuis un résultat de recherche donne beaucoup plus d’éléments au comparateur (numéro de piste, album, type de sortie).

## Toujours bloqué ?

Ouvrez une issue sur [github.com/henriquesebastiao/downtify/issues](https://github.com/henriquesebastiao/downtify/issues) avec :

- la version de Downtify (affichée en bas de la barre latérale et dans **Paramètres → À propos**),
- les journaux du conteneur autour de l’échec (`docker compose logs downtify`),
- et si des cookies sont configurés.
