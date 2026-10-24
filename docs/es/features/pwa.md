---
icon: lucide/smartphone
---

# Instalar como app (PWA)

La interfaz web de Downtify es una Progressive Web App: tanto en iOS como en Android puedes añadirla a la pantalla de inicio y se abre a pantalla completa, como una app nativa, sin barra de direcciones ni controles del navegador.

## iOS (Safari)

1. Abre Downtify en Safari
2. Pulsa el botón **Compartir**
3. Pulsa **Añadir a pantalla de inicio**

El icono de Downtify aparece en tu pantalla de inicio y se abre en su propia ventana.

## Android (Chrome)

1. Abre Downtify en Chrome
2. Pulsa el menú **⋮**
3. Pulsa **Añadir a la pantalla de inicio** (o **Instalar aplicación**, si Chrome la ofrece directamente)

## Cómo funciona

`frontend/index.html` enlaza un [web app manifest](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest) (`/manifest.json`) que establece `"display": "standalone"` y `start_url: "/"`, además de los iconos que Android usa para el acceso directo de la pantalla de inicio y el selector de apps. Es lo que Chrome/Android lee para instalar la app a pantalla completa y con su propio icono.

Safari en iOS no lee los campos `display` ni los de iconos del manifest al usar «Añadir a pantalla de inicio»: necesita sus propias etiquetas `<meta>`/`<link>` `apple-mobile-web-app-capable` y `apple-touch-icon` en `index.html`, que se definen junto al manifest para que ambas plataformas tengan el mismo comportamiento independiente, a pantalla completa y con el icono de Downtify.

No hay soporte sin conexión ni service worker: la interfaz de Downtify solo sirve mientras alcanza el backend al que está vinculada, así que esto es una «app web instalable a pantalla completa», no una que funcione sin conexión.
