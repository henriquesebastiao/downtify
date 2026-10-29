---
icon: lucide/smartphone
---

# Uygulama olarak yükle (PWA)

Downtify’ın web arayüzü bir Progressive Web App’tir: hem iOS’ta hem Android’de ana ekranınıza ekleyebilirsiniz; adres çubuğu ve tarayıcı denetimleri olmadan, yerel bir uygulama gibi tam ekran açılır.

## iOS (Safari)

1. Downtify’ı Safari’de açın
2. **Paylaş** düğmesine dokunun
3. **Ana Ekrana Ekle**’ye dokunun

Downtify simgesi ana ekranınızda belirir ve bağımsız bir pencerede açılır.

## Android (Chrome)

1. Downtify’ı Chrome’da açın
2. **⋮** menüsüne dokunun
3. **Ana ekrana ekle**’ye dokunun (Chrome doğrudan sunuyorsa **Uygulamayı yükle**)

## Nasıl çalışır

`frontend/index.html`, `"display": "standalone"` ve `start_url: "/"` değerlerini belirleyen bir [web app manifest](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest) dosyasına (`/manifest.json`) bağlanır; ayrıca Android’in ana ekran kısayolu ve uygulama değiştirici için kullandığı simgeleri içerir. Chrome/Android uygulamayı tam ekran ve kendi simgesiyle yüklemek için bunu okur.

iOS Safari, “Ana Ekrana Ekle” için manifest’teki `display` veya simge alanlarını hiç okumaz — `index.html` içinde kendi `apple-mobile-web-app-capable` ve `apple-touch-icon` `<meta>`/`<link>` etiketlerine ihtiyaç duyar. Bunlar manifest ile birlikte ayarlanır; böylece iki platform da Downtify simgesiyle aynı bağımsız, tam ekran davranışını alır.

Çevrimdışı destek ya da service worker yoktur — Downtify arayüzü yalnızca eşleştiği arka uca ulaşabildiği sürece işe yarar; yani bu “yüklenebilir, tam ekran bir web uygulaması”dır, çevrimdışı çalışan bir uygulama değil.
