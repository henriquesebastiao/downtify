# Analyses rythmiques incrémentales

DCLAP et les profils rythmiques sont deux inventaires différents. `GET /api/v1/music-ai/dj/analysis`, réservé à l’administration, compte les vecteurs DCLAP et les profils DJ correspondant au catalogue observé, au modèle courant, à l’empreinte du morceau et à sa version de source. Il distingue tempo, temps, mesures, tonalité suffisamment confiante, niveau, énergie, confiance et points candidats. Un champ absent est compté comme manquant ; un vecteur DCLAP ne prouve jamais une analyse rythmique.

Le diagnostic lit uniquement la base dérivée. Il ne parcourt pas la collection, ne charge pas de modèle et ne renvoie pas de chemin ni de titre privé.

## File et reprise

Le flux de révisions natif reste la source du catalogue. L’indexeur sélectionne au plus 200 contrôles de sources par passe ; il n’utilise pas un parcours NAS supplémentaire. Les écoutes récentes et favoris gardent leur priorité. La file `rhythm` possède ses propres identités incluant modèle, morceau, empreinte, version de source et génération. Les profils valides et les travaux déjà en attente ne sont pas replanifiés. L’indexation rythmique fonctionne aussi lorsque les fonctions DCLAP sont désactivées.

Le worker prend le bail partagé de calcul en catégorie `analysis`. Une demande DJ ou la pression mémoire/IO empêche son admission. Les opérations natives, la pause d’analyse, la désactivation du module ou une génération périmée interrompent les checkpoints. Une interruption coopérative remet le travail en attente sans consommer de tentative ; les erreurs transitoires utilisent le backoff existant. Le résultat n’est enregistré que si le bail, le catalogue, la version et les préférences sont encore valides.

Les fichiers originaux restent des entrées en lecture seule. Chaque tentative dispose d’un espace privé distinct, dérivé du bail, supprimé après traitement. Le contrôle supplémentaire du dimanche à 02 h Europe/Paris a un rattrapage et une clé hebdomadaire stable pendant le changement d’heure. Il remet les échecs en attente et conserve les analyses réussies.

## Ressources et déploiement

`docker-compose.rhythm.example.yml` est un exemple opt-in : profil `rhythm-analysis`, image identique au worker DJ testé, 0,5 CPU, 1 536 Mio, réseau désactivé, racine en lecture seule, aucun port et collections en lecture seule. Les chemins doivent correspondre à la stack existante ; ce fichier ne prouve pas que ces budgets sont déployés. Le cache dérivé partagé reste borné à 5 Gio. Le service ne doit pas être ajouté en parallèle d’un autre service faisant déjà le même travail.

La ligne de commande est `python -m downtify.music_ai.dj_worker preanalyze` avec les mêmes arguments de base, modèles, racines et cache que le worker DJ. Aucun modèle n’est téléchargé. Les modules et préférences restent désactivés par défaut.

## État de validation

La suite complète du backend comporte 3 606 tests réussis et deux essais de vrais modèles exclus dans l’environnement de développement. Douze tests audio utilisent réellement FFmpeg. Les scénarios de reprise, priorité DJ/native, catalogue modifié et dimanche avec changement d’heure sont automatisés. Les mesures de couverture réelle, CPU/RAM/IO, premier son, heure continue et appareil restent à effectuer sur la candidate isolée avant bascule.


## Modèle résident et annulation

L’inférence utilise un processus résident sérialisé. Les instances small0 et final0 sont construites à la demande puis conservées entre les titres ; aucune nouvelle famille de modèle ni aucun téléchargement de poids n’est ajouté. Les échanges JSON ont un identifiant de requête, une borne de 16 Kio en entrée, 2 Mio en sortie et un délai maximal. Les réponses incompatibles, périmées ou tardives ne sont pas adoptées. Une annulation ferme le groupe du processus et de ses décodeurs ; le prochain travail utilise un processus neuf. La désactivation libère le modèle résident. Les résultats de profils déjà valides restent réutilisés sans inférence.

Les temps de beats bruts et les points candidats issus des mesures sont conservés avec le profil. Un point candidat n’est pas une preuve de phrase musicale ou de transition qualifiée. Cette extension change la révision de l’analyse rythmique ; les profils incomplets de l’ancienne révision sont complétés une fois. Les vecteurs DCLAP restent inchangés et le contrôle hebdomadaire ne relance pas les réussites de la révision courante.

Le code d’inférence de la version utilisée, beat-this 1.1.0, a été vérifié dans son wheel officiel (SHA256 `3f2b2d1e027c6dac380bf80c71555e3c28a4036a7f1af20129a945915a72a645`). Référence du projet : https://github.com/CPJKU/beat_this. Les tests de protocole et les doublures de modèles vérifient la réutilisation, la sérialisation et l’annulation ; ils ne démontrent pas la mémoire réelle ni le débit des poids sur le serveur. Les deux tests d’intégration des vrais modèles restent à exécuter dans l’image isolée.
