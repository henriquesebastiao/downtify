---
icon: lucide/download
---

# Notifications de mise à jour

Downtify consulte sa propre [page de Releases GitHub](https://github.com/henriquesebastiao/downtify/releases) une fois par heure. Quand une version plus récente est disponible, un avis apparaît en bas de la barre latérale sur chaque page — sur téléphone, un point sur l’onglet **Plus** et une ligne en haut de sa feuille — ainsi que dans **Paramètres → À propos** :

> ✦ Mise à jour 3.0.1 disponible

Cliquez dessus pour ouvrir cette version sur GitHub.

## Fonctionnement

- Une tâche d’arrière-plan du backend (`downtify/update_check.py`) récupère la dernière version via l’API de GitHub une fois dès le démarrage, puis toutes les heures. C’est du « lancer et oublier » : rien dans l’interface ne l’attend.
- L’interface web lit le résultat mis en cache depuis `GET /api/check_update` (voir la [Référence de l’API](../api-reference.md)) une fois par heure et affiche l’avis quand une version plus récente est trouvée.
- Les versions sont comparées numériquement (`2.10.0` < `2.9.0` est faux, contrairement à une simple comparaison de chaînes), et un préfixe `v` facultatif sur le tag de la release est ignoré.

## Si GitHub est injoignable

Une vérification qui échoue (hôte hors ligne, limite de requêtes GitHub) est consignée dans le journal et simplement retentée au prochain passage horaire — le résultat précédent, s’il existe, reste valable d’ici là. La vérification ne bloque jamais rien d’autre dans Downtify ; aucune erreur n’est montrée à l’utilisateur.

## Rien n’est téléchargé automatiquement

Cela ne fait que vous *signaler* qu’une nouvelle version existe — Downtify ne se met pas à jour tout seul. Pour mettre à jour, récupérez la nouvelle image et recréez le conteneur :

```bash
docker compose pull
docker compose up -d
```
