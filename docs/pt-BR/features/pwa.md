---
icon: lucide/smartphone
---

# Instalar como app (PWA)

A interface web do Downtify é um Progressive Web App: tanto no iOS quanto no Android você pode adicioná-la à tela inicial e ela abre em tela cheia, como um app nativo, sem barra de endereço nem controles do navegador.

## iOS (Safari)

1. Abra o Downtify no Safari
2. Toque no botão **Compartilhar**
3. Toque em **Adicionar à Tela de Início**

O ícone do Downtify aparece na tela de início e abre em uma janela própria.

## Android (Chrome)

1. Abra o Downtify no Chrome
2. Toque no menu **⋮**
3. Toque em **Adicionar à tela inicial** (ou em **Instalar app**, se o Chrome oferecer direto)

## Como funciona

O `frontend/index.html` aponta para um [web app manifest](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest) (`/manifest.json`) que define `"display": "standalone"` e `start_url: "/"`, além dos ícones que o Android usa no atalho da tela inicial e no seletor de apps. É isso que o Chrome/Android lê para instalar o app em tela cheia e com ícone próprio.

O Safari do iOS não lê os campos `display` nem os de ícone do manifest ao usar "Adicionar à Tela de Início" — ele precisa das próprias tags `<meta>`/`<link>` `apple-mobile-web-app-capable` e `apple-touch-icon` no `index.html`, que são definidas junto com o manifest para que as duas plataformas tenham o mesmo comportamento em tela cheia e com o ícone do Downtify.

Não há suporte offline nem service worker — a interface do Downtify só serve enquanto consegue falar com o backend ao qual está ligada, então isto é um "app web instalável em tela cheia", não um app que funciona offline.
