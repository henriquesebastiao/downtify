---
icon: lucide/hard-drive
---

# Réglages du serveur

**Paramètres → Serveur** regroupe le fonctionnement du serveur lui-même. Seuls les administrateurs le voient (voir [Utilisateurs et connexion](users.md#admins-and-users)).

## Changer le port

Downtify écoute sur le port **8000**. Un administrateur peut en choisir un autre dans **Paramètres → Serveur → Port** (1024–65535) :

- **Enregistrer** le conserve pour le prochain démarrage du serveur.
- **Enregistrer et redémarrer** redémarre aussitôt le serveur sur ce port. Les téléchargements en cours s’arrêtent, et les pages et applications se reconnectent. Une page ouverte à l’adresse du serveur lui-même (par ex. `http://nas:8000`) attend le serveur et ouvre la nouvelle adresse toute seule ; vous restez connecté.

Quand le port vient de la variable d’environnement `DOWNTIFY_PORT` (ou `PORT`) ou de `--port` en ligne de commande — qui l’emportent toujours —, le champ affiche le port utilisé mais n’est pas modifiable, et la page indique laquelle le définit. Supprimez-la (et redémarrez) pour choisir le port dans les Paramètres.

::: warning Le réseau bridge de Docker associe un port fixe
Dans la configuration Docker par défaut (`ports: - '8000:8000'`), le port du conteneur doit correspondre à l’association. Après l’avoir changé dans les Paramètres, modifiez l’association pour le nouveau port (`'9000:9000'`) et recréez le conteneur — ou lancez avec `network_mode: host`. Sinon, Downtify est inaccessible. Pour y revenir, définissez `DOWNTIFY_PORT` sur l’ancien port : il l’emporte sur les Paramètres.
:::

Derrière un [proxy inverse](mobile-apps.md#behind-a-reverse-proxy), pointez aussi le proxy vers le nouveau port. Les [applications associées](mobile-apps.md) utilisent l’adresse qui leur a été donnée : après un changement de port, saisissez la nouvelle dans l’application.
