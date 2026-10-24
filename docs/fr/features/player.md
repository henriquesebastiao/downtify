---
icon: lucide/headphones
---

# Lecteur intégré

Downtify inclut un lecteur web pour écouter votre musique téléchargée sans application séparée. Appuyez sur lecture sur n’importe quel morceau, album, artiste ou playlist de la Bibliothèque — ou sur un téléchargement terminé de la File — et le lecteur démarre.

## Barre du lecteur

Tant qu’un morceau est chargé, une barre du lecteur flotte en bas de chaque page : pochette, titre et artiste, aléatoire, précédent, lecture/pause, suivant, répétition, temps écoulé/total, et raccourcis vers les panneaux des paroles et de la suite (celui des paroles peut être [masqué](#hiding-the-lyrics)). Sur grand écran, elle a aussi un curseur de volume et une barre de recherche le long de son bord supérieur ; sur téléphone, elle se réduit à l’essentiel et affiche une fine ligne de progression.

À côté du titre, un cœur permet d’[aimer le morceau](liked-songs.md) ; le téléphone l’omet de la barre pour laisser de la place au titre, et le place dans **Lecture en cours** et dans les listes de morceaux.

Cliquez sur le titre ou la pochette, ou sur le bouton d’agrandissement, pour ouvrir **Lecture en cours**.

## Lecture en cours

Une vue plein écran teintée de couleurs tirées de la pochette de l’album actuel :

- **Grande pochette**, titre et artiste (cliquez sur l’artiste ou sur l’étiquette *Lecture depuis* pour aller à cet artiste, album ou playlist), avec un cœur à côté du titre pour [aimer le morceau](liked-songs.md). La pochette et les paroles se réduisent avec la fenêtre — y compris quand vous ne changez que sa hauteur — pour rester sous l’en-tête.
- **Barre de recherche** — cliquez ou faites glisser, ou utilisez les flèches quand elle a le focus. Pendant la lecture d’un morceau, de douces vagues dérivent sur la partie jouée dans des couleurs tirées de la pochette de l’album ; elles se figent à plat en pause, et restent immobiles si votre système demande une animation réduite
- **Commandes de lecture** — aléatoire, précédent, lecture/pause, suivant, répétition (désactivée → tout répéter → répéter un)
- **Volume** avec bouton muet, enregistré entre les sessions. Masqué sur téléphone, où les boutons matériels règlent le niveau
- **Minuterie de veille** — arrête la lecture au bout de 15, 30, 45, 60 ou 90 minutes, ou à la fin du morceau en cours. Le temps restant s’affiche à côté du bouton de la minuterie
- **Infos du fichier** — format et taille du fichier en lecture

Quatre panneaux se placent à côté de la pochette sur grand écran, ou la remplacent sur téléphone :

- **Paroles** — les paroles synchronisées mettent en évidence la ligne actuelle et défilent avec le morceau ; cliquez sur une ligne pour y aller. Les paroles simples s’affichent telles quelles. Les paroles viennent du fichier `.lrc` à côté du morceau, ou de celles intégrées à ses tags — voir [Paroles](lyrics.md). Vous pouvez masquer ce panneau — voir [Masquer les paroles](#hiding-the-lyrics).
- **À suivre** — la file de lecture. Faites glisser les morceaux pour les réordonner, retirez des morceaux isolés, ou videz tout ce qui suit l’actuel.
- **Détails** — titre, artiste, album, numéro de piste, année, durée, format, taille, date d’ajout et chemin du fichier.
- **Égaliseur** — façonnez le son avec dix bandes de fréquences ; voir [Égaliseur](#equalizer).

Lecture en cours fait partie de l’adresse de la page (`?np=1`, plus `&panel=lyrics|queue|details|equalizer`), si bien que le bouton Retour du navigateur le ferme et qu’un rechargement le garde ouvert.

## Masquer les paroles

Vous préférez la pochette et la file sans les mots ? Désactivez **Paramètres → Général → Lecteur → Afficher les paroles dans le lecteur**. Cela s’applique aussitôt et retire tout ce qui mène aux paroles dans le lecteur :

- le panneau **Paroles** et son onglet (sur téléphone, son bouton dans le pied de Lecture en cours) ;
- le bouton des paroles dans la barre du lecteur ;
- le raccourci `L`, qui disparaît aussi de la liste des raccourcis (`?`).

Lecture en cours s’ouvre alors sur **À suivre**. Un lien vers `&panel=lyrics` datant d’avant la désactivation y atterrit aussi, plutôt que sur un onglet vide. Le lecteur ne demande même pas les paroles d’un morceau tant qu’elles sont masquées.

::: info Masquer n’est pas supprimer
Cela ne change que ce que le lecteur affiche. Vos fichiers gardent les paroles que Downtify y a intégrées, et les fichiers `.lrc` à côté restent en place, si bien que les serveurs multimédias et les autres lecteurs les voient toujours. Les téléchargements continuent aussi à récupérer les paroles — c’est le réglage séparé **Télécharger les paroles** sous **Tags et paroles** (voir [Paroles](lyrics.md)).
:::

Comme le thème et l’égaliseur, le choix est enregistré dans le navigateur (`localStorage`), donc par appareil et par navigateur, pas par serveur Downtify — vous pouvez masquer les paroles sur un téléphone et les garder sur un ordinateur.

## Égaliseur

Un égaliseur graphique à dix bandes, dans le panneau **Égaliseur** de Lecture en cours (ou appuyez sur `E`). Il est marqué **Expérimental** : il peut encore changer, et mal se comporter dans certains navigateurs (voir [Compatibilité des navigateurs](#browser-support)).

- **Bandes** à 31, 62, 125, 250, 500 Hz et 1, 2, 4, 8, 16 kHz, chacune ±12 dB par pas de 0,5 dB. Les bandes de 31 Hz et 16 kHz sont des shelves ; elles relèvent ou coupent donc aussi tout ce qui est en dessous / au-dessus. Faites glisser une bande, ou donnez-lui le focus et utilisez les flèches (`Page Up`/`Page Down` pour 1 dB, `Home`/`End` pour les limites) ; un double-clic la remet à 0.
- **Préréglages** — Neutre, Basses renforcées, Aigus renforcés, Voix, Rock, Électro et Acoustique. Déplacer ensuite n’importe quelle bande transforme le préréglage en **Personnalisé**.
- **Préampli** — ±12 dB par-dessus le reste.
- **Interrupteur** et **Réinitialiser** (retour à Neutre, préampli 0, désactivé). Déplacer une bande ou choisir un préréglage active aussi l’égaliseur.
- La courbe derrière les curseurs est la réponse combinée de toutes les bandes.

Renforcer des bandes pousserait la musique forte au-delà de la pleine échelle et la distordrait ; Downtify baisse donc automatiquement le volume du plus grand renforcement de la courbe — le panneau indique de combien. Cela maintient le pic à 0 dB, si bien qu’un préréglage renforcé remodèle le son au lieu de simplement le rendre plus fort. Monter le préampli au-dessus de 0 dB supprime cette marge de sécurité, et le panneau avertit que les passages forts peuvent distordre.

Les réglages sont enregistrés dans le navigateur (`localStorage`) et s’appliquent à tout ce que vous écoutez, dans tous les onglets, jusqu’à ce que vous les changiez. Ils sont par navigateur, pas par serveur Downtify.

### Compatibilité des navigateurs

L’égaliseur utilise la Web Audio API, disponible dans tous les navigateurs actuels. Tant que vous ne l’activez pas, la lecture ne touche pas du tout à Web Audio. Une fois activé, l’audio du reste de la visite passe par lui — le désactiver ne fait qu’aplatir toutes les bandes.

::: warning Safari sur iPhone et iPad
iOS peut suspendre Web Audio quand l’écran se verrouille ou que vous changez d’application, ce qui arrête la lecture tant que l’égaliseur est activé. Si vous écoutez écran éteint, désactivez l’égaliseur et rechargez la page.
:::

## Construire la file

Lire un album, un artiste, une playlist ou la liste de morceaux met ces morceaux en file d’attente dans l’ordre, à partir de celui que vous avez choisi. **Aléatoire** sur une collection la démarre dans un ordre aléatoire. Les morceaux que vous n’avez pas téléchargés se lisent en entier directement dans la file, servis depuis le cache de diffusion du serveur : pendant qu’un morceau joue, le suivant est déjà préparé un morceau à l’avance, si bien que la lecture traverse les lignes non téléchargées sans s’arrêter — même là où le navigateur lui-même ne peut pas joindre YouTube. Un morceau diffusé n’est jamais enregistré, aimé ni mémorisé d’un rechargement à l’autre.

Le menu de chaque morceau (le bouton **⋯**, ou clic droit sur ordinateur) propose :

- **Lire ensuite** — insère juste après le morceau actuel
- **Ajouter à la file** — ajoute à la fin
- **Aller à l’album** / **Aller à l’artiste**
- **Enregistrer sur cet appareil** — télécharge le fichier via le navigateur
- **Supprimer de la bibliothèque**

Les mêmes actions s’appliquent à une sélection de plusieurs morceaux dans la Bibliothèque.

La file, le morceau actuel, sa position, l’aléatoire et la répétition sont mémorisés, si bien que rouvrir Downtify reprend là où vous vous étiez arrêté (les files de plus de 2000 morceaux ne sont pas mémorisées). Les fichiers supprimés sortent automatiquement de la file.

## Clavier et touches multimédias

| Touche | Action |
|-----|--------|
| `Space` | Lecture / pause |
| `←` / `→` | Avancer/reculer de 5 secondes |
| `Shift` + `←` / `→` | Morceau précédent / suivant |
| `↑` / `↓` | Volume |
| `M` | Muet |
| `S` | Aléatoire |
| `R` | Répétition |
| `L` | Ouvrir les paroles (sauf si [masquées](#hiding-the-lyrics)) |
| `Q` | Ouvrir À suivre |
| `E` | Ouvrir l’égaliseur |
| `Ctrl` / `⌘` + `K` ou `/` | Rechercher |
| `G` puis `L` / `D` | Aller à la bibliothèque / la file |
| `Esc` | Fermer Lecture en cours |
| `?` | Afficher tous les raccourcis |

Les raccourcis sont ignorés pendant que vous saisissez dans un champ ou qu’une boîte de dialogue est ouverte.

Le lecteur signale aussi le morceau en cours au système d’exploitation (Media Session), si bien que les commandes de l’écran de verrouillage, les boutons du casque et les touches multimédias du clavier fonctionnent, avec la pochette affichée là où le système le permet.

## Comment ça marche

Les morceaux viennent de la liste de la bibliothèque (`GET /tracks`), qui lit titre, artiste, album, numéro de piste, année et durée dans les tags de chaque fichier. Les fichiers sont servis depuis le montage statique `/downloads` ; les téléchargements slskd [laissés en place](slskd-navidrome.md#leave-files-in-place) sont lus via `/media/slskd/…`. La pochette vient de `/cover` et les paroles de `/lyrics` — voir la [référence de l’API](../api-reference.md#file-management).

La lecture utilise l’audio HTML5 natif du navigateur. Pas de plugins, pas de processus supplémentaires.

## Formats pris en charge

Le lecteur peut lire n’importe quel format que le moteur audio HTML5 de votre navigateur prend en charge. Cela inclut généralement MP3, M4A/AAC, OGG et OPUS dans tous les navigateurs modernes. La prise en charge du FLAC varie — Chrome et Edge la gèrent nativement ; Firefox et Safari peut-être pas.
