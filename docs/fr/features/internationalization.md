---
icon: lucide/languages
---

# Internationalisation

Downtify est traduit à deux endroits indépendants : l’**application** (son interface) et cette **documentation**. La langue par défaut des deux est l’**anglais**, avec neuf autres langues incluses d’office.

## Changer de langue

### L’application

Allez dans **Paramètres → Langue** et choisissez votre langue préférée. Le choix est enregistré dans le `localStorage` du navigateur et appliqué instantanément sans recharger la page. La page l’indique aussi au serveur (l’entrée `ui_language` de `settings.json`, voir [`POST /api/settings/update`](../api-reference.md#post-apisettingsupdate)), à chaque chargement et à chaque changement, pour que le travail qui s’exécute sans navigateur connaisse votre langue - la bio d’un artiste, récupérée en arrière-plan quand l’un de ses morceaux finit de se télécharger, arrive dans cette langue (voir [Quand un téléchargement se termine](artist-images.md#when-a-download-finishes)). Rien à faire de votre côté : si vous aviez choisi une langue avant que cela existe, elle est reprise à la prochaine ouverture de Downtify. Avec plusieurs navigateurs réglés sur des langues différentes, le dernier qui a chargé ou changé la langue l’emporte.

### La documentation

La documentation s’ouvre dans la langue préférée de votre navigateur, quand elle y est traduite, et en anglais sinon. Le **bouton globe** à droite de la barre supérieure change la langue à tout moment et vous garde sur la même page (et la même section). Votre choix est mémorisé dans le navigateur et, dès lors, l’emporte sur la langue du navigateur jusqu’à ce que vous en choisissiez une autre.

Une page pas encore traduite affiche une note et le texte anglais, si bien que chaque langue a toujours toutes les pages.

## Langues disponibles

| Code | Langue | App | Docs |
| ------- | ------------------ | --- | ---- |
| `en` | English (par défaut) | ✓ | ✓ |
| `es` | Español | ✓ | ✓ |
| `pt-BR` | Português (Brasil) | ✓ | ✓ |
| `fr` | Français | ✓ | ✓ |
| `tr` | Türkçe | ✓ | ✓ |
| `el` | Ελληνικά | ✓ | ✓ |
| `hu` | Magyar | ✓ | ✓ |
| `bg` | Български | ✓ | ✓ |
| `de` | Deutsch | ✓ | ✓ |
| `ko` | 한국어 | ✓ | ✓ |

Les pages de référence destinées aux développeurs — la [référence de l’API](../api-reference.md), le [contrat du client mobile](../mobile-client-contract.md) et le journal des modifications — restent en anglais dans toutes les langues.

## Contribuer une traduction

Vous pouvez traduire l’application, la documentation, ou les deux. Ce sont des travaux distincts avec des fichiers distincts, si bien qu’une pull request peut contenir l’un ou l’autre — ou qu’une langue peut être ajoutée d’abord à l’un puis à l’autre plus tard.

| Vous traduisez | Où sont les fichiers | C’est terminé quand |
| ------------- | ------------------- | --------- |
| **L’application seulement** | `frontend/src/i18n/locales/<code>.js` | la langue apparaît dans **Paramètres → Langue** |
| **La documentation seulement** | `docs/.vitepress/locales/<code>.mjs` et les pages Markdown dans `docs/<code>/` | la langue apparaît dans le menu globe de la documentation |
| **Les deux** | tout ce qui précède | les deux |

Une langue n’a pas besoin d’exister dans l’application pour être ajoutée à la documentation, ni l’inverse.

## Traduire l’application

Ajouter une traduction à l’application se fait en trois étapes :

### 1. Copiez le fichier de langue anglais

Les fichiers de langue se trouvent dans `frontend/src/i18n/locales/`. Chaque fichier exporte un seul objet dont les clés suivent la structure de `en.js`. Utilisez une [balise de langue IETF](https://en.wikipedia.org/wiki/IETF_language_tag) comme nom de fichier.

```bash
cp frontend/src/i18n/locales/en.js frontend/src/i18n/locales/it.js
```

### 2. Traduisez les valeurs

Gardez inchangés les clés, les jetons de substitution (par ex. `{count}`, `{name}`, `{file}`) et la forme générale — seules les chaînes du côté droit doivent changer. Définissez `language.name` sur le nom **natif** de la langue (`"Français"`, `"Deutsch"`, …) — c’est l’étiquette affichée dans le sélecteur de langue.

### 3. Enregistrez la langue

Ajoutez un import et une entrée à `AVAILABLE_LOCALES` dans `frontend/src/i18n/index.js` :

```js
import it from './locales/it.js'

export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English', messages: en },
  { code: 'es', name: 'Español', messages: es },
  // …
  { code: 'it', name: 'Italiano', messages: it }, // new
]
```

Recompilez le frontend et votre langue apparaîtra automatiquement dans **Paramètres → Langue** :

```bash
cd frontend && npm run build
```

### Conseils pour traduire l’application

- Les clés manquantes retombent sur l’anglais, donc les traductions partielles fonctionnent très bien — soumettez une PR avec ce que vous avez.
- Les chaînes qui dépendent d’un nombre sont des objets avec des formes de pluriel, par ex. `tracks: { one: '{count} track', other: '{count} tracks' }`. La forme est choisie avec [`Intl.PluralRules`](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Intl/PluralRules) du navigateur pour votre langue ; ajoutez donc les formes qu’utilise votre langue (`zero`, `one`, `two`, `few`, `many`, `other`) — `other` est obligatoire. Les nombres sont formatés automatiquement pour la langue.
- Les jetons de substitution comme `{count}` ou `{file}` doivent rester inchangés ; ils sont remplacés à l’exécution.
- Gardez les chaînes concises — l’interface est serrée et des traductions très longues peuvent se replier de façon disgracieuse.
- Après avoir traduit, lancez `npm run dev` depuis `frontend/` et parcourez chaque page dans votre langue pour repérer ce qui déborde ou sonne bizarrement en contexte.

## Traduire la documentation

L’anglais est la source : il se trouve dans `docs/`. Chaque autre langue a un dossier portant son code (`docs/pt-BR/`) avec **les mêmes noms de fichiers** que l’anglais, plus un fichier pour les textes du site lui-même (`docs/.vitepress/locales/pt-BR.mjs` : les titres de la barre latérale, la zone de recherche, le pied de page, les étiquettes des encadrés). Une page pas encore traduite est une petite ébauche qui affiche une note et inclut la page anglaise.

### Traduire une page d’une langue existante

Depuis `docs/` :

```bash
npm install
npm run i18n -- status pt-BR           # what is translated, what is English-only, what is out of date
npm run i18n -- start pt-BR features/users.md
```

`start` remplace l’ébauche `docs/pt-BR/features/users.md` par une copie de la page anglaise. Traduisez-la sur place, puis vérifiez :

```bash
npm test             # the translated pages must keep the English page's structure
npm run dev          # read it in the browser, in your language
```

Ouvrez une pull request quand la page se lit bien ; le travail partiel est bienvenu aussi — les pages que vous n’avez pas touchées restent simplement en anglais.

### Ajouter une langue à la documentation

1. Copiez `docs/.vitepress/locales/en.mjs` vers `docs/.vitepress/locales/<code>.mjs` et traduisez-le : le `name` natif, les textes du site (`ui`), les étiquettes des encadrés (`containers`) et les titres de la barre latérale (`nav`).
2. Enregistrez-la dans `docs/.vitepress/locales/index.mjs`.
3. Créez les pages, comme ébauches en anglais seulement : `npm run i18n -- stubs <code>`.
4. Traduisez les pages une à une avec `npm run i18n -- start <code> <page>`.

La langue apparaît dans le menu globe et dans la détection de la langue du navigateur dès qu’elle est enregistrée.

### Ce qu’il faut garder, et ce qu’il faut traduire

- **Traduisez** le texte, les titres, les cellules des tableaux, les titres des encadrés et les valeurs `title`/`text` dans le front matter de la page d’accueil.
- **Gardez tel quel** les blocs de code, le `code` en ligne, les URL, les variables d’environnement, les chemins et noms de champs d’API, les noms de fichiers et de dossiers, ainsi que les clés du front matter et les valeurs de `icon:` et `link:`. Traduire un commentaire dans un bloc de code est acceptable.
- **Liens** : gardez exactement les liens relatifs `.md` de la page anglaise (`[Paroles](lyrics.md#sidecar-lrc-file)`). Un lien vers une page qui n’existe qu’en anglais fonctionne toujours. Sur la page d’accueil, les liens s’écrivent avec le préfixe de langue (`/pt-BR/features/player/`).
- **Titres** : gardez les mêmes titres, dans le même ordre et aux mêmes niveaux. Les liens vers une section (`#sidecar-lrc-file`) continuent de fonctionner dans toutes les langues car la page traduite réutilise les identifiants de titres anglais — vous n’écrivez ni ne traduisez jamais d’identifiant.
- **Noms des boutons et des réglages** : l’application a sa propre traduction de chaque étiquette. Utilisez-la, en gras, pour que la page corresponde à ce que le lecteur voit à l’écran : cherchez l’étiquette dans `frontend/src/i18n/locales/<code>.js`. Si l’application n’est pas encore traduite dans cette langue, gardez l’étiquette anglaise.
- **Encadrés** (`::: tip Titre`) : gardez le type (`info`, `tip`, `warning`, `danger`) et traduisez le titre. Un encadré sans titre porte pour étiquette le mot de `containers` dans le fichier de la langue.
- **Ton** : écrivez pour le lecteur de cette langue — les pages sont des guides, pas des transpositions mot à mot.

### Garder les traductions à jour

Quand une page anglaise change, ses traductions n’ont pas à changer dans la même pull request : une page traduite continue de fonctionner, et `npm run i18n -- status <code>` liste les pages dont la source anglaise a changé après leur traduction. Les mettre à jour est une bonne première contribution.

Les tests (`npm test` dans `docs/`) vérifient que chaque langue a toutes les pages et tous les textes du site, et qu’une page traduite a toujours les titres, blocs de code, tableaux, encadrés et liens de la page anglaise.
