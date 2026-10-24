---
icon: lucide/smartphone
---

# Als App installieren (PWA)

Die Weboberfläche von Downtify ist eine Progressive Web App: Sowohl unter iOS als auch unter Android kannst du sie zum Home-Bildschirm hinzufügen. Sie startet dann im Vollbild wie eine native App, ohne Adressleiste und Browser-Bedienelemente.

## iOS (Safari)

1. Öffne Downtify in Safari
2. Tippe auf die Schaltfläche **Teilen**
3. Tippe auf **Zum Home-Bildschirm**

Das Downtify-Symbol erscheint auf dem Home-Bildschirm und startet in einem eigenen Fenster.

## Android (Chrome)

1. Öffne Downtify in Chrome
2. Tippe auf das Menü **⋮**
3. Tippe auf **Zum Startbildschirm hinzufügen** (oder **App installieren**, falls Chrome das direkt anbietet)

## So funktioniert es

`frontend/index.html` verweist auf ein [Web-App-Manifest](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest) (`/manifest.json`), das `"display": "standalone"` und `start_url: "/"` festlegt, dazu die Symbole, die Android für die Verknüpfung auf dem Startbildschirm und den App-Umschalter nutzt. Das liest Chrome/Android, um die App im Vollbild und mit eigenem Symbol zu installieren.

iOS-Safari liest für „Zum Home-Bildschirm“ weder das Feld `display` noch die Symbolfelder des Manifests — er braucht eigene `<meta>`-/`<link>`-Tags (`apple-mobile-web-app-capable` und `apple-touch-icon`) in `index.html`. Sie werden zusammen mit dem Manifest gesetzt, damit beide Plattformen dasselbe eigenständige Vollbildverhalten mit dem Downtify-Symbol bekommen.

Es gibt weder Offline-Unterstützung noch einen Service Worker — die Oberfläche von Downtify ist nur nützlich, solange sie das Backend erreicht, mit dem sie verbunden ist. Es ist also eine „installierbare Vollbild-Web-App“, keine offlinefähige.
