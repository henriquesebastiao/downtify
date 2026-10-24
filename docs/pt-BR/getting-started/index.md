---
icon: lucide/play
---

# Primeiros passos

O Downtify é um aplicativo web auto-hospedado que baixa músicas do Spotify — sem chaves de API, sem conta, sem exigir assinatura Premium. Tudo roda dentro de um único contêiner Docker.

## O que você precisa

- **Docker** (ou Docker Compose) — o único requisito na máquina host
- Uma máquina com acesso à internet
- Um volume/diretório onde você quer guardar suas músicas

## Escolha como instalar

<div class="doc-cards">

- <DocIcon name="docker" /> **Docker run**

  O jeito mais rápido de começar. Um comando e pronto em menos de um minuto.

  [Instalação →](installation.md)

- <DocIcon name="file-code" /> **Docker Compose**

  Recomendado para instalações permanentes. Mais fácil de atualizar e gerenciar.

  [Docker Compose →](docker-compose.md)

- <DocIcon name="house" /> **Instalação com um clique**

  Usa Umbrel, CasaOS ou HomeDock OS? Instale direto pelas lojas de aplicativos deles.

  [Instalação com um clique →](one-click.md)

</div>

## Próximos passos

Com o Downtify rodando, abra [http://localhost:8000](http://localhost:8000) no navegador. Cole o endereço de uma faixa, álbum ou playlist do Spotify na barra de busca e clique em **Baixar**.

Explore o restante da documentação para conhecer as [configurações de download](../features/download-settings.md), o [monitor de playlists](../features/playlist-monitor.md), o [player integrado](../features/player.md) e mais.
