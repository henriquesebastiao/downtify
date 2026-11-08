---
icon: lucide/image
---

# Capa das playlists

O Downtify pode salvar a capa da própria playlist ao lado do seu [arquivo M3U](m3u-export.md), para que servidores de mídia e gerenciadores de arquivos mostrem a arte real da playlist em vez de um ícone genérico.

Ativado por padrão. Desative em **Configurações → Downloads e arquivos → Salvar a capa da playlist**.

## Onde o arquivo vai

A capa é gravada com o **mesmo nome e na mesma pasta do M3U da playlist**, com a extensão `.jpg`:

```
<downloads>/<nome-da-playlist>/<nome-da-playlist>.m3u
<downloads>/<nome-da-playlist>/<nome-da-playlist>.jpg
```

Com *Organizar por artista* ou *Organizar por álbum* ativado, as faixas ficam espalhadas por pastas de artistas e o M3U vai para um diretório central `Playlists/` (veja [Organização de arquivos](file-organization.md)) — a capa vai junto:

```
<downloads>/Playlists/<nome-da-playlist>.m3u
<downloads>/Playlists/<nome-da-playlist>.jpg
```

::: info Precisa do M3U
Com **Gerar playlists M3U** desativado, nenhuma capa é salva também: o Downtify posiciona a imagem pelo caminho do M3U, então sem ele não há onde colocá-la. A configuração fica oculta enquanto a gravação de M3U está desativada.
:::

## Fontes e resolução

| Fonte | Resolução |
|--------|-----------|
| **Spotify** | A maior imagem que a página pública de incorporação oferece para a playlist — a mesma já usada para a capa das faixas |
| **YouTube Music** | Sempre solicitada em 1200×1200, independentemente da [Resolução da capa](download-settings.md#cover-art-resolution), que afeta apenas as capas por faixa |

Os dois serviços entregam JPEG para essas URLs mesmo quando a arte original era PNG, então o arquivo é sempre salvo como `.jpg`.

## Quando é baixada

**Antes das faixas**, nos dois casos — a pasta já se parece com a playlist enquanto se enche, e um servidor de mídia que escaneie no meio do download encontra a arte em vez de uma pasta vazia:

- **Um download manual de playlist** — uma vez, assim que o nome da playlist é resolvido, antes de a primeira faixa começar.
- **[Monitor de playlists](playlist-monitor.md)** — uma vez por varredura que tenha algo para baixar, antes da primeira faixa dessa varredura. Uma varredura que não encontra nada novo não busca de novo.

Falhar em resolver ou baixar a capa (um erro de rede, uma playlist sem arte) é registrado em log e ignorado — nunca atrasa nem faz falhar o próprio download.

## Na interface do Downtify

Uma playlist que tem arte própria (baixada com uma playlist do Spotify ou do YouTube) a mostra em todo lugar onde a Biblioteca lista playlists — a grade, a página da playlist, a barra lateral e o player. Playlists sem uma, e playlists que você cria na Biblioteca, mostram um mosaico de até quatro capas de faixas distintas: duas lado a lado, três como um bloco alto à esquerda e dois empilhados à direita, quatro em uma grade 2×2. A mesma colagem é gravada como `<nome-da-playlist>.jpg` ao lado do M3U de uma playlist manual, para que o Navidrome também a veja, e é refeita sempre que você adiciona ou remove músicas.

## Navidrome

Nada a configurar: o Navidrome resolve a arte das playlists a partir de uma **imagem auxiliar** — um arquivo com o nome da playlist, na mesma pasta — que é exatamente o que o Downtify grava. Desde que a pasta de música do Navidrome inclua a sua pasta de downloads, a arte aparece na próxima varredura dele. Nenhuma chamada de API do Downtify está envolvida. Veja [slskd e Navidrome](slskd-navidrome.md#navidrome).

## Limpeza

Excluir uma playlist pela página da Biblioteca remove a capa junto com o M3U e as faixas — veja [Excluindo uma playlist](slskd-navidrome.md#deleting-a-playlist).
