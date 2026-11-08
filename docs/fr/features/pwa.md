---
icon: lucide/smartphone
---

# Installer comme application (PWA)

L’interface web de Downtify est une Progressive Web App : sous iOS comme sous Android, vous pouvez l’ajouter à votre écran d’accueil et elle se lance en plein écran, comme une application native, sans barre d’adresse ni éléments de navigation.

## iOS (Safari)

1. Ouvrez Downtify dans Safari
2. Touchez le bouton **Partager**
3. Touchez **Sur l’écran d’accueil**

L’icône de Downtify apparaît sur votre écran d’accueil et se lance dans une fenêtre autonome.

## Android (Chrome)

1. Ouvrez Downtify dans Chrome
2. Touchez le menu **⋮**
3. Touchez **Ajouter à l’écran d’accueil** (ou **Installer l’application**, si Chrome la propose directement)

## Fonctionnement

`frontend/index.html` référence un [web app manifest](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest) (`/manifest.json`) qui définit `"display": "standalone"` et `start_url: "/"`, ainsi que les icônes qu’Android utilise pour le raccourci de l’écran d’accueil et le sélecteur d’applications. C’est ce que Chrome/Android lit pour installer l’application en plein écran, avec sa propre icône.

Safari sous iOS ne lit pas du tout les champs `display` ni les icônes du manifest pour « Sur l’écran d’accueil » : il lui faut ses propres balises `<meta>`/`<link>` `apple-mobile-web-app-capable` et `apple-touch-icon` dans `index.html`, définies à côté du manifest pour que les deux plateformes aient le même comportement autonome, en plein écran, avec l’icône de Downtify.

Il n’y a ni mode hors ligne ni service worker — l’interface de Downtify n’est utile que tant qu’elle peut joindre le backend auquel elle est associée ; c’est donc une « application web installable en plein écran », pas une application utilisable hors ligne.
