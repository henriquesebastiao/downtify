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
| **[LRCLIB](https://lrclib.net)** | Simples e sincronizadas | Banco de dados comunitário gratuito, sem chave. Correspondência por título, artista principal, álbum e duração. Se isso não achar nada sincronizado, a busca dele também é tentada; um resultado vale quando título, artista e duração (com poucos segundos de diferença) batem. |
| **NetEase Cloud Music** | Geralmente sincronizadas | Catálogo grande, forte em lançamentos asiáticos e muitas vezes também em ocidentais. Correspondência por título, artista e duração; um resultado cujo artista é escrito de outra forma (chinês tradicional vs. simplificado, por exemplo) só é aceito quando título e duração coincidem. |
| **Kugou Music** | Sincronizadas | Catálogo grande, forte em lançamentos chineses e com muitos ocidentais. Correspondência como no NetEase; a linha de título e os créditos de composição do início são removidos. |

Em **Configurações → Tags e letras → Provedores** você pode arrastar os provedores para a ordem que preferir, ou usar as setas, e desligar qualquer um deles. Pelo menos um continua ligado; para parar de buscar letras de vez, use a chave **Baixar letras**. Um provedor adicionado numa atualização começa desligado se você já tinha salvado sua própria lista: ligue-o lá.

### Só letras sincronizadas

**Configurações → Tags e letras → Só letras sincronizadas** (desligado por padrão) mantém só letras com marcação de tempo: um provedor que só tem letra simples para uma música conta como sem nada, e o próximo é consultado. [Melhorar biblioteca](library-upgrade.md) passa a contar como sem letra uma faixa que só tem letra simples. Letras sincronizadas que um arquivo já tem contam sempre: um arquivo `.lrc` ao lado, letras com marcação de tempo nas tags ou um quadro ID3 `SYLT` (como às vezes têm arquivos de outros apps). Com a opção ligada, a letra sincronizada que o Downtify encontra substitui a simples: no arquivo `.lrc` e na tag de letra do próprio arquivo, assim players que só leem as tags também a mostram sincronizada. A varredura também diz quantas das faixas sem letra só tinham letra simples.

### Buscar letras para faixas sem letra

**Biblioteca → Melhorar biblioteca → Escanear e buscar letras** procura na biblioteca faixas sem letra e já busca as letras, com barra de progresso. No fim, mostra quantas faixas ganharam letra, para quantas nada foi encontrado e quantas falharam. Veja [Melhorar biblioteca](library-upgrade.md#while-it-runs).

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

## Ajustando a sincronia

Letras encontradas na internet às vezes ficam um pouco adiantadas ou atrasadas em relação ao áudio baixado: outra edição da música, uma introdução mais longa. Para corrigir uma música, toque-a, abra **Tocando agora → Letra** e aperte o botão de cronômetro no canto superior direito da letra, **Ajustar sincronia da letra**:

- **−** mostra a letra antes e **+** depois, um décimo de segundo por toque, até um minuto para cada lado. A letra segue o novo tempo na hora, então dá para testar com a música tocando.
- **Salvar** grava o ajuste nos arquivos da música; **Redefinir** volta ao tempo salvo.

Salvar reescreve os próprios tempos, no `.lrc` ao lado e, quando as tags do arquivo têm letra sincronizada, nelas também (inclusive quadros `SYLT` de MP3). Assim a correção aparece também em outros players que leem o `.lrc` ou as tags, e nos apps. Um arquivo somente leitura mantém as tags; só o `.lrc` muda. Uma linha `[offset:N]` num `.lrc` é incorporada aos tempos ao salvar, e o player do Downtify já a respeita antes disso.

O botão só aparece em músicas da biblioteca com letra sincronizada. Qualquer usuário conectado pode ajustá-la; a mudança aparece no [registro de atividade](users.md#activity) como **Sincronia de letras ajustada**. O endpoint é [`POST /api/library/lyrics/offset`](../api-reference.md#post-apilibrarylyricsoffset).

## Quando nada é encontrado

Se nenhum provedor tem a música, o download continua normalmente — o arquivo de áudio é salvo sem letras, e nenhum erro é gerado.
