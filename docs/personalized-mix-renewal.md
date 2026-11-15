# Renouvellement des mixes personnels

Les favoris et écoutes du compte connecté guident les mixes quand la personnalisation est activée. Les artistes déjà proposés sont pénalisés, avec au plus deux titres par artiste dans chaque sélection. Rock, rap, pop et électro restent des sélections hebdomadaires fondées sur les genres de la bibliothèque ; les six humeurs ont leurs sélections quotidiennes et hebdomadaires.

« Renouveler mes mixes » demande explicitement la régénération des sélections automatiques de la période courante. Le serveur annonce `playlist_refresh: true` ; les clients plus récents cachent ce bouton sur un ancien serveur. Le POST `/api/v1/music-ai/playlists/refresh` reçoit un UUID `request_id`. Le compte vient exclusivement de l’authentification, y compris pour un administrateur.

La transaction vérifie les préférences globales et individuelles, invalide les sélections courantes des seules cadences actives et incrémente une révision. Une génération commencée avant cette révision ne peut pas publier son ancien résultat. Le worker habituel reconstruit les mixes après analyse initiale si nécessaire ; aucun parcours de fichiers, analyse audio ou rendu ne se produit dans le POST. La réponse signifie « demande acceptée », pas « nouveaux mixes déjà prêts ».

Les 32 derniers reçus par compte rendent les reprises réseau idempotentes. Les sélections retirées restent dans une mémoire de rotation limitée à 84 lots et sept jours, sans doubler les propositions encore enregistrées. Effacer le profil retire cette mémoire et les reçus. Les anciens jours et semaines, les copies stables dans les playlists natives et la file de lecture restent conservés. Le compte connecté garde son catalogue visible ; aucune proposition ne donne accès à un titre masqué.

Les recommandations instantanées tournent aussi chaque jour, ou après un renouvellement explicite, tout en gardant le classement par goûts. Les caches d’accueil sont invalidés après acceptation avec protections contre les réponses périmées et changements de compte.

Validation : tests serveur d’isolation, idempotence, bornes, absence de parcours de fichiers et invalidation concurrente ; tests réseau Android et courses de cache ; tests web d’invalidation et changement de compte. Les essais de modèles réels et sur téléphone restent distincts des tests locaux.
