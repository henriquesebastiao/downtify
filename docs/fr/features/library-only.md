---
title: Mode bibliothèque seule
icon: lucide/library
---

# Mode bibliothèque seule

Un administrateur peut activer **Paramètres → Général → Utiliser uniquement la bibliothèque**.
Le réglage est désactivé par défaut et s’applique à tous les comptes et appareils.

La recherche utilise les titres, artistes et albums de la bibliothèque accessible.
Les écrans, la navigation et le lecteur gardent leur présentation habituelle.
Découvrir et Classements proposent les morceaux, albums, artistes et playlists
de la bibliothèque. Les morceaux similaires
sont classés selon les tags artiste, album et, lorsqu’il est disponible, genre.
Ce rapprochement ne constitue pas une analyse acoustique. Le morceau de départ
et les doublons sont exclus. Une référence inconnue ou une bibliothèque sans
rapprochement donne un résultat vide, sans recours à une radio extérieure.
Les règles existantes de masquage restent appliquées. Les dossiers de musique
ajoutés au serveur, y compris ceux montés en lecture seule, font partie de la bibliothèque.

Les recherches et liens externes, aperçus, flux (même en cache), téléchargements,
remplacements et améliorations en ligne sont refusés. Les suivis automatiques
et le rafraîchissement Spotify attendent la désactivation du mode, sans suppression
de leur configuration ni consommation de leur travail en attente.

## Activer le mode

Terminez les opérations externes en cours avant l’activation. Un refus HTTP 409
signale qu’il faut attendre leur fin et réenregistrer le réglage. Aucun traitement
n’est annulé et le réglage n’est pas partiellement appliqué. Aucun audio n’est supprimé.

Le serveur applique immédiatement la règle. Les clients à jour reçoivent un événement
`music_policy_changed`, vérifient aussi le réglage toutes les 15 secondes et à la
reconnexion, et retirent les résultats et éléments de file externes. Les pistes
locales restantes gardent leur ordre. Un ancien client ne peut plus appeler les
routes musicales externes, mais seul un client à jour peut arrêter un audio
extérieur qu’il avait déjà mis en mémoire.

## Android et écoute sans connexion

Android conserve le dernier réglage reçu du serveur et recherche dans sa bibliothèque
synchronisée. Les fichiers de cette bibliothèque déjà téléchargés sur le téléphone
restent lisibles. Sans copie locale, le téléphone doit encore joindre le serveur.
Les morceaux similaires sont demandés au serveur et calculés dans sa bibliothèque.

Ce réglage est distinct des téléchargements hors ligne du téléphone. Il ne constitue
pas un pare-feu Internet du serveur : les contrôles de version et les opérations
d’administration non musicales sont indépendants.

## Compatibilité API

Le champ API est `library_only`, booléen strict, ajouté à `/api/server/info`
et aux paramètres. Les serveurs plus anciens sans ce champ gardent le comportement
habituel. Les réponses musicales locales portent `source: "library"` et `file`,
sans URL externe. Les routes musicales externes répondent HTTP 409.
