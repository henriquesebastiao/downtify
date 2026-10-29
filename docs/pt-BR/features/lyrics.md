---
icon: lucide/mic-vocal
---

# Letras

O Downtify procura letras enquanto uma faixa é baixada e as incorpora ao arquivo, além de um arquivo auxiliar `.lrc` quando elas são sincronizadas com o tempo.

## Ativando as letras

As letras vêm **ativadas por padrão**. Desative em **Configurações → Tags e letras → Baixar letras**.

## Provedores e ordem de tentativa

Os catálogos diferem: uma música que um provedor nunca ouviu falar costuma estar em outro. Por isso o Downtify mantém uma lista ordenada de provedores e tenta um de cada vez, parando no primeiro que tiver algo.

| Provedor | Letras | Observações |
|----------|--------|-------|
| **[LRCLIB](https://lrclib.net)** | Simples e sincronizadas | Banco de dados comunitário gratuito, sem chave. Correspondência por título, artista principal, álbum e duração. |
| **NetEase Cloud Music** | Geralmente sincronizadas | Catálogo grande, forte em lançamentos asiáticos e muitas vezes também em ocidentais. Correspondência por título, artista e duração; um resultado cujo artista é escrito de outra forma (chinês tradicional vs. simplificado, por exemplo) só é aceito quando título e duração coincidem. |

Em **Configurações → Tags e letras → Provedores** você pode arrastar os provedores para a ordem que preferir, ou usar as setas, e desligar qualquer um deles. Pelo menos um continua ligado; para parar de buscar letras de vez, use a chave **Baixar letras**.

::: info E o Genius, o Musixmatch e o AZLyrics?
Eles não estão disponíveis, e o Downtify não os oferece mais:

- O **AZLyrics** proíbe o uso de terceiros das letras em sua própria página.
- A API de desktop do **Musixmatch** responde com um token vazio, a menos que você tenha credenciais que ela não fornece a aplicativos.
- O `robots.txt` do **Genius** proíbe o endpoint de busca necessário para achar a página de uma música.

Configurações salvas que ainda citam esses nomes continuam funcionando: os nomes são ignorados, e uma lista que fica sem mais nada volta aos provedores padrão.
:::

## Pulando provedores que não tinham nada

Depois de uma busca, o Downtify registra para cada música quais provedores responderam e quais voltaram vazios, em `downtify_library.db` dentro de `/data`.

Um provedor que não tinha nada para uma música não é consultado sobre ela de novo por **30 dias**, para que novos downloads e grandes varreduras da biblioteca não repitam as mesmas buscas fracassadas. Depois disso, ele é tentado de novo, já que os catálogos crescem. Um provedor que *tinha* letra nunca é pulado, então um arquivo baixado de novo as recupera.

## Incorporação

| Formato | Tag de letra simples | Tag de letra sincronizada |
|--------|-----------------|------------------|
| MP3 | `USLT` (ID3) | `USLT` com marcações de tempo |
| FLAC | `LYRICS` (comentário Vorbis) | `LYRICS` com conteúdo LRC |
| M4A | `©lyr` | `©lyr` com conteúdo LRC |
| OGG / OPUS | `LYRICS` (comentário Vorbis) | `LYRICS` com conteúdo LRC |

## Arquivo auxiliar .lrc

Quando há letras sincronizadas, o Downtify também salva um arquivo `.lrc`. Por padrão ele fica **ao lado do áudio** com o mesmo nome base. Em **Configurações → Tags e letras** você pode desativar isso e escolher uma **pasta de letras** (padrão `/data/lyrics`). Essa pasta precisa ficar **fora** de `/downloads`, da árvore do slskd e de quaisquer pastas de música extras — o caminho relativo do áudio é recriado dentro dela (`Artista/Álbum/faixa.lrc`). Players que leem letras externas (e o [player integrado](player.md#now-playing)) ainda encontram o arquivo auxiliar. Mudar essa configuração e executar **Sincronizar** em uma pasta extra copia os `.lrc` existentes para o novo local; o arquivo de origem é removido quando essa árvore é gravável, e mantido em uma montagem somente leitura. Um arquivo auxiliar é gravado mesmo que as letras já estejam incorporadas nas tags.

Excluir a faixa pela página da Biblioteca remove o `.lrc` (ao lado do arquivo e na pasta dedicada) junto com o áudio, então as letras nunca ficam como um arquivo órfão.

## Quando nada é encontrado

Se nenhum provedor tem a música, o download continua normalmente — o arquivo de áudio é salvo sem letras, e nenhum erro é gerado.
