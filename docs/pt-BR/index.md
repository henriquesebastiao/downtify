---
layout: home
title: Downtify
titleTemplate: "Baixador do Spotify e player de música auto-hospedado"
description: "Baixador do Spotify auto-hospedado com player. Cole um link do Spotify, YouTube Music, Deezer ou SoundCloud e receba MP3 ou FLAC com tags. Sem chave de API."
icon: lucide/house
hero:
  eyebrow: Baixador de músicas auto-hospedado
  headline:
    - Cole um link.
    - Receba a música.
  lead: Um baixador de músicas auto-hospedado com player integrado. Cole um link do Spotify, YouTube Music, Deezer ou SoundCloud e receba uma biblioteca perfeitamente etiquetada, pronta para tocar no navegador, no celular ou no seu servidor de mídia.
  note: Sem conta do Spotify, sem chaves de API, sem Premium.
  actions:
    - text: Começar
      link: /pt-BR/getting-started/installation/
      primary: true
    - text: Código-fonte no GitHub
      link: https://github.com/henriquesebastiao/downtify
      icon: github
  shields:
    - alt: Versão
      src: https://img.shields.io/github/v/release/henriquesebastiao/downtify?color=1AD05C&label=release
      link: https://github.com/henriquesebastiao/downtify/releases
    - alt: Downloads do Docker
      src: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fghcr-badge.elias.eu.org%2Fapi%2Fhenriquesebastiao%2Fdowntify%2Fdowntify&query=downloadCount&label=docker%20pulls&color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/pkgs/container/downtify
    - alt: Estrelas no GitHub
      src: https://img.shields.io/github/stars/henriquesebastiao/downtify?style=flat&label=stars&color=1AD05C
      link: https://star-history.com/#henriquesebastiao/downtify&Date
    - alt: Licença
      src: https://img.shields.io/github/license/henriquesebastiao/downtify?color=1AD05C
      link: https://github.com/henriquesebastiao/downtify/blob/main/LICENSE
video:
  src: /assets/media/downtify-demo.mp4
  poster: /assets/media/downtify-demo-poster.webp
  label: 'O Downtify em 44 segundos: cole o link de uma playlist, baixe tudo com um clique, mantenha-a sincronizada e toque com letras sincronizadas, no computador e no celular.'
why:
  - icon: link
    title: Um link é tudo de que você precisa
    text: Cole uma música, um álbum, uma playlist inteira ou um artista do Spotify, YouTube Music, Deezer ou SoundCloud, ou simplesmente digite o que quer ouvir. O Downtify encontra o áudio e traz tudo para casa.
    link: /pt-BR/how-it-works/
  - icon: tag
    title: Arquivos que valem a pena guardar
    text: Cada arquivo leva a capa, todos os artistas creditados, o álbum, o ano, o número da faixa e a letra, sincronizada quando existe. MP3, FLAC, M4A, OGG ou Opus, ou o áudio da fonte exatamente como veio.
    link: /pt-BR/features/download-settings/
  - icon: music
    title: Seu próprio serviço de streaming
    text: Um player completo no navegador, com letras sincronizadas, karaokê, fila, músicas curtidas, playlists e podcasts. Apps para Android e iOS levam sua biblioteca com você, offline também.
    link: /pt-BR/features/player/
  - icon: radar
    title: Configure e esqueça
    text: Monitore playlists e artistas. Músicas e lançamentos novos são baixados sozinhos, na frequência que você escolher.
    link: /pt-BR/features/playlist-monitor/
  - icon: server
    title: Feito para o seu servidor
    text: Uma imagem Docker para amd64 e arm64, SQLite ou PostgreSQL, contas para todo mundo da casa com login único opcional e playlists que Jellyfin, Navidrome e Plex reconhecem.
    link: /pt-BR/getting-started/
  - icon: shield
    title: Sem amarras
    text: Sem chave de API do Spotify, sem conta de desenvolvedor, sem Premium. O app não tem anúncios, nem análise de uso, nem nada pago. É livre e de código aberto.
    link: /pt-BR/contributing/
showcase:
  - shot: now-playing
    label: Tocando agora
    caption: A letra acompanha a música, linha por linha, ao lado da capa e do que vem a seguir.
    alt: A tela cheia de Tocando agora, com a capa do álbum, a letra sincronizada com a linha atual destacada e a fila.
  - shot: karaoke
    label: Karaoke
    caption: Letras grandes que se preenchem conforme cada linha é cantada, prontas para abrir em uma segunda tela.
    alt: A tela de karaokê, com letras grandes se preenchendo sobre um fundo em movimento nas cores da capa.
  - shot: home
    label: Início
    caption: Cole um link ou procure algo novo, e continue de onde parou.
    alt: A página inicial, com uma caixa para colar um link ou pesquisar, estatísticas da biblioteca, o álbum tocando e os álbuns adicionados recentemente.
  - shot: library
    label: Biblioteca
    caption: Álbuns, artistas, playlists e faixas, ordenados e filtrados do seu jeito.
    alt: A página Biblioteca, com uma grade de capas de álbuns e abas para álbuns, artistas, playlists e faixas.
  - shot: playlist
    label: Playlists
    caption: Playlists suas, com capa própria, para tocar, compartilhar ou baixar como ZIP.
    alt: Uma página de playlist, com a capa, os botões e as músicas com álbum, formato e data de lançamento.
  - shot: phones
    label: No celular
    caption: O mesmo app no seu celular, instalável pelo navegador.
    alt: O Downtify em três celulares, mostrando a página inicial, Tocando agora e a Biblioteca.
pipeline:
  - icon: link
    title: Cole um link
    text: Spotify, YouTube Music, Deezer ou SoundCloud. Ou só digite uma música.
  - icon: search
    title: Encontra o áudio
    text: A versão mais parecida no YouTube Music, conferida pela duração. Outras fontes, se você quiser.
  - icon: download
    title: Baixa e etiqueta
    text: O yt-dlp e o ffmpeg buscam o áudio. Capa, letra e tags vão para dentro do arquivo.
  - icon: music
    title: Toque onde quiser
    text: No navegador, no celular ou no Jellyfin, Navidrome e Plex.
quickStart:
  - text: Guia de instalação
    link: /pt-BR/getting-started/installation/
    primary: true
  - text: Docker Compose
    link: /pt-BR/getting-started/docker-compose/
  - text: Instalação com um clique
    link: /pt-BR/getting-started/one-click/
apps:
  - icon: smartphone
    title: Downtify para Android
    text: O app oficial. Encontra seu servidor na rede, transmite em qualidade original no Wi-Fi e numa menor nos dados móveis, guarda músicas offline e funciona com o Android Auto. Ainda em testes, no GitHub Releases e no Obtainium.
    link: https://github.com/henriquesebastiao/downtify-android
  - icon: tablet-smartphone
    title: Downtify para iOS
    text: Feito por um membro da comunidade para iPhone e iPad (iOS 17 ou mais recente), com músicas offline e controles na tela de bloqueio. O beta público está no TestFlight.
    link: https://github.com/michaelmoskie/Downtify-IOS-Client
community:
  - text: Estrela no GitHub
    link: https://github.com/henriquesebastiao/downtify
    icon: star
    primary: true
  - text: Patrocinar
    link: https://github.com/sponsors/henriquesebastiao
    icon: heart
  - text: Traduzir
    link: /pt-BR/features/internationalization/
    icon: languages
  - text: Contribuir
    link: /pt-BR/contributing/
    icon: git-pull-request
---

## Por que o Downtify

<HomeHighlights :items="$frontmatter.why" />

## Um olhar mais de perto

<HomeShowcase :items="$frontmatter.showcase" />

## Como funciona

O Downtify não precisa de chave de API do Spotify e nunca baixa nada do Spotify. Ele descobre em fontes públicas o que um link indica, escolhe o áudio do YouTube Music cuja duração mais combina, baixa com o `yt-dlp`, converte com o `ffmpeg` e etiqueta com o `mutagen`, tudo em um só contêiner Docker. O YouTube entra quando nada combina bem, e SoundCloud, Soulseek e Deemix participam se você os ativar. [Cada etapa, em detalhes](how-it-works.md).

<HomePipeline :steps="$frontmatter.pipeline" />

## O que você pode colar

| Fonte         | O que funciona                      | Exemplo                             |
| ------------- | ----------------------------------- | ----------------------------------- |
| Spotify       | Faixas, álbuns, playlists, artistas | `open.spotify.com/playlist/…`       |
| YouTube Music | Músicas, álbuns, playlists, artistas | `music.youtube.com/playlist?list=…` |
| YouTube       | Vídeos                              | `youtube.com/watch?v=…`             |
| Deezer        | Faixas, álbuns, playlists, artistas | `deezer.com/album/…`                |
| SoundCloud    | Faixas                              | `soundcloud.com/artist/track`       |
| Busca         | O que você digitaria                | `The Night Owls Do I Still Recall`  |
| CSV           | Exportações de biblioteca           | Soundiiz, TuneMyMusic, Exportify    |

## Tudo o que ele faz

Cada recurso tem a sua página, com todas as opções explicadas. [Todos os recursos de uma vez](features/index.md).

<HomeFeatures />

## Funcionando em um minuto

```bash
docker run -d -p 8000:8000 --name downtify \
  -v /path/to/music:/downloads \
  -v downtify_data:/data \
  --restart unless-stopped \
  ghcr.io/henriquesebastiao/downtify
```

Abra [`localhost:8000`](http://localhost:8000), entre como **admin** com a senha **downtify** e cole um link. Troque essa senha em **Configurações → Geral** logo em seguida. Sua música chega em `/path/to/music`, já com as tags.

<HomeActions :actions="$frontmatter.quickStart" />

## Perguntas frequentes

::: details Preciso de conta do Spotify, Premium ou chave de API?
Não. O Downtify lê os dados de faixas, álbuns e playlists nas páginas públicas de incorporação (embed) do Spotify, então não precisa de credencial nenhuma, e o áudio nunca vem do Spotify. Veja [Como funciona](how-it-works.md).
:::

::: details De onde vem o áudio, e qual é a qualidade?
Do YouTube Music por padrão: o resultado cuja duração mais combina com a música, com o YouTube como alternativa. Escolha MP3, FLAC, M4A, OGG ou Opus na taxa de bits que quiser, ou mantenha o melhor áudio da fonte sem recodificar. Arquivos sem perdas vêm de fontes que você mesmo adiciona: seu próprio servidor [Soulseek (slskd)](features/slskd-navidrome.md), cujos arquivos mantêm o formato original, ou um servidor [Deemix](features/deemix.md). Veja [Configurações de download](features/download-settings.md).
:::

::: details Funciona com Jellyfin, Navidrome ou Plex?
Sim. Os arquivos são etiquetados como os servidores de mídia esperam, organizados em pastas `Artista/Álbum/`, e cada playlist ganha um arquivo M3U padrão que eles reconhecem. O Navidrome também pode ter as playlists sincronizadas e as avaliações definidas pelo Deezer. Veja [Organização de arquivos](features/file-organization.md) e [Exportação M3U](features/m3u-export.md).
:::

::: details Roda em um Raspberry Pi ou em um NAS?
A imagem é feita para `amd64` e `arm64`, e o Umbrel, o CasaOS e o HomeDock OS a instalam com um clique. Veja [Instalação com um clique](getting-started/one-click.md).
:::

::: details O YouTube diz "Sign in to confirm you're not a bot". E agora?
Envie um `cookies.txt` em **Configurações → Cookies do YouTube**; o Downtify mantém essa sessão conectada sozinho. Se o YouTube ainda limitar você, aumente a _Pausa entre downloads_, diminua os _Downloads simultâneos_ e depois tente `DOWNTIFY_FORCE_IPV4=1`. Veja [Solução de problemas](troubleshooting.md) e [Cookies do YouTube](features/youtube-cookies.md).
:::

## Leve com você

<HomeHighlights :items="$frontmatter.apps" />

Qualquer outro cliente pode usar a mesma API: veja o [contrato do cliente móvel](mobile-client-contract.md).

<div class="home-cta">

## Feito em comunidade

O Downtify é livre e de código aberto. Mais de 35 pessoas contribuíram com código, tradutores da comunidade o levaram a 12 idiomas, e muitos recursos começaram como uma ideia que alguém abriu em uma issue. Se ele conquistou um lugar no seu servidor, dê uma estrela no GitHub, conte para um amigo que também hospeda os próprios serviços, ou patrocine o desenvolvimento: isso ajuda a pagar o tempo que vai para cada versão.

<HomeActions :actions="$frontmatter.community" />

</div>
