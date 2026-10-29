---
icon: lucide/sliders-horizontal
---

# Configurações de download

Abra **Configurações** na barra lateral (no celular: **Mais → Configurações**). A página é dividida em seções — Geral, Fontes de áudio, Downloads e arquivos, Tags e letras, Navidrome, Biblioteca e Sobre. As alterações ficam pendentes até você pressionar **Salvar alterações** na barra que aparece na parte de baixo; sair da página com alterações não salvas pergunta antes. As configurações são gravadas em disco e sobrevivem a reinícios do contêiner.

## Formato

| Formato | Extensão | Observações |
|--------|-----------|-------|
| MP3 | `.mp3` | Padrão. Compatibilidade universal. |
| FLAC | `.flac` | Sem perdas. A configuração de bitrate é ignorada. |
| M4A | `.m4a` | AAC em um contêiner MPEG-4. Bom para dispositivos Apple. |
| OGG | `.ogg` | Ogg Vorbis. Formato aberto, boa relação qualidade/tamanho. |
| OPUS | `.opus` | Melhor compressão em bitrates baixos. |

## Bitrate

Disponível para formatos com perdas (MP3, M4A, OGG, OPUS). O FLAC ignora esta configuração.

| Opção | Kbps |
|--------|------|
| Baixo | 128 |
| Médio | 192 |
| Alto | 256 |
| Máximo | **320** (padrão) |

O áudio baixado é codificado no bitrate que você escolher, em todos os formatos com perdas. Se o áudio que o YouTube entrega já tem o codec de destino em um bitrate próximo disso (por exemplo, o fluxo AAC de ~128 kbps para **M4A @ 128**), ele é mantido como está em vez de recodificado, já que recodificar só perderia qualidade.

::: info Um bitrate maior não acrescenta qualidade
O áudio do YouTube chega a no máximo **128–160 kbps** (AAC ou Opus), e o Downtify sempre baixa o melhor fluxo disponível. Codificá-lo a 256 ou 320 kbps gera arquivos maiores que preservam essa fonte fielmente, mas não recuperam detalhes que a fonte nunca teve. Escolha um bitrate menor se o tamanho dos arquivos importa mais para você.
:::

## Modelo de nome de arquivo

O modelo de nome de arquivo padrão é:

```
{artists} - {title}
```

O que produz nomes como `The Night Owls - Do I Still Recall.mp3`.

Tokens disponíveis:

| Token | Descrição |
|-------|-------------|
| `{title}` | Título da faixa |
| `{artists}` | Todos os artistas creditados, separados por vírgula (por exemplo, `Christina Aguilera, Lil' Kim, Mýa, P!nk`) |
| `{artist}` | Só o primeiro artista creditado (por exemplo, `Christina Aguilera`). Um nome com vírgula, como `Earth, Wind & Fire`, fica inteiro. |
| `{album}` | Nome do álbum |
| `{tracknumber}` | Posição da faixa no álbum, com zeros à esquerda até 2 dígitos (por exemplo, `01`, `12`). Vazio quando a fonte não tem número de faixa (por exemplo, um resultado de texto livre/busca do YouTube). |
| `{year}` | Ano de lançamento (por exemplo, `2025`). Vazio quando a fonte não tem data de lançamento (por exemplo, um resultado de texto livre/busca do YouTube). |

O modelo também pode incluir `/` para criar subpastas. Por exemplo, para organizar uma biblioteca como `Artista/Álbum (2025)/01 - Título.mp3` — útil ao baixar uma discografia completa, já que cada álbum cai na própria pasta junto com o ano de lançamento:

```
{artist}/{album} ({year})/{tracknumber} - {title}
```

Use `{artist}` em vez de `{artists}` numa pasta: com `{artists}`, uma música com convidados ganha uma pasta própria (`Christina Aguilera, Lil' Kim, Mýa, P!nk/`) em vez de ir para a do primeiro artista.

::: info
Isso é independente das opções **Organizar por artista** / **Organizar por álbum** — elas direcionam downloads de playlists/álbuns para pastas compartilhadas por artista ou por álbum em toda a sua biblioteca (veja [Organização de arquivos](file-organization.md)). `{tracknumber}` e `{year}` apenas permitem que um modelo como o acima monte esse mesmo layout manualmente, faixa por faixa, sem ativar essas opções.
:::

::: tip Coletâneas
O modelo vale para uma faixa de uma coletânea de vários artistas como para qualquer outra: `{artist}` é o primeiro artista da própria faixa, nunca "Various Artists". Veja [Vários artistas e coletâneas](file-organization.md#several-artists-and-compilations).
:::

## Downloads simultâneos

Controla quantas músicas são baixadas ao mesmo tempo. Escolha uma predefinição (1, 2, 3, 5, 8) ou digite qualquer valor personalizado de **1 a 30** no campo numérico ao lado delas.

| Valor | Comportamento |
|-------|-----------|
| **1** | Sequencial — uma música por vez (o mais seguro, menor uso de recursos) |
| **3** | Padrão. Bom equilíbrio entre velocidade e estabilidade. |
| **8** | Mais rápido para playlists grandes |
| **até 30** | Melhor para conexões muito rápidas; usa mais CPU e banda e aumenta a chance de o YouTube limitar você. |

O limite vale para todo download em lote — downloads de playlists/álbuns, o endpoint da fila em lote e [importações de biblioteca](library-import.md) por CSV — e para as consultas da sincronização das **[Pastas de músicas existentes](external-library.md)** (letras, capas, gênero). Ele **não** vale para as varreduras do Monitor de playlists, que baixam as faixas novas uma de cada vez. Mudar este valor em Configurações tem efeito imediato, sem reiniciar; o servidor limita qualquer valor fora de `1–30`.

## Pausa entre downloads

Faz o Downtify esperar um número configurável de segundos ao terminar uma música antes de começar a próxima, em vez de disparar as requisições em sequência.

| Valor | Comportamento |
|-------|-----------|
| **0** | Padrão — desligado, sem espera. |
| **5 / 15 / 30 / 60** | Predefinições, ou digite qualquer valor personalizado de **0 a 300 segundos**. |

Vale para downloads de playlists, álbuns e lotes, [importações de biblioteca](library-import.md) por CSV e varreduras automáticas do Monitor de playlists. É ignorada em um download manual de uma única faixa (não há "próxima" música para esperar) e depois da *última* faixa de qualquer lote, para que a execução não termine com uma espera inútil.

Combinada com um valor menor de **Downloads simultâneos**, é a principal ferramenta para evitar o limite de requisições do YouTube ao baixar uma playlist grande ou uma biblioteca importada sem supervisão.

## Pausa entre consultas da sincronização

A mesma ideia, mas para as **[Pastas de músicas existentes](external-library.md)** em vez de downloads. A sincronização busca letras, capas ausentes e gênero em lotes de **[Downloads simultâneos](#parallel-downloads)** faixas por vez e depois espera este número de segundos antes do próximo lote. Padrão **0** (as consultas continuam rodando em paralelo, ainda limitadas por Downloads simultâneos). Use alguns segundos em uma coleção grande para que o LRCLIB, as fontes de capas e o iTunes não sejam acionados todos de uma vez.

## Baixar capa

Controla se o Downtify incorpora a capa do álbum. Ligado por padrão. Desligue para pular totalmente a busca da capa — todas as outras tags (título, artista, álbum, ano, letra) continuam sendo incorporadas normalmente, mas os arquivos ficam menores e baixam um pouco mais rápido, já que a imagem da capa nunca é pedida nem gravada.

Desligar isto também pula a gravação do `cover.jpg` avulso que a opção *Organizar por álbum* (veja [Organização de arquivos](file-organization.md)) produz, e o [player](player.md) e a biblioteca não mostrarão capa nas faixas baixadas assim (aparece o ícone de nota musical no lugar).

Esse `cover.jpg` é compartilhado por todas as faixas da pasta do álbum. Excluir uma faixa pela página Biblioteca também o remove, mas só quando ela é a **última** faixa restante na pasta — enquanto houver outra faixa do mesmo álbum, a capa fica.

## Resolução da capa

Só importa quando **Baixar capa** (acima) está ligado. Define o tamanho desejado (largura e altura, em pixels) que o Downtify pede para a capa incorporada vinda do **YouTube Music** ou do **Deezer**. Escolha uma predefinição (300, 600, 800, 1000, 1200) ou arraste o controle deslizante de **300 a 1200**; o valor atual em pixels aparece ao lado. O padrão é 600.

É útil ao alimentar a biblioteca em um servidor de mídia como o Plex, que exibe capas em resolução maior do que a incorporada por padrão pelo Downtify.

As duas fontes aplicam a configuração de modos diferentes, já que só uma delas pode de fato ser redimensionada sob demanda:

- As miniaturas do **YouTube Music** podem ser redimensionadas editando a URL — verificado no CDN real, as predefinições mais altas devolvem de verdade mais detalhe (não apenas ampliação) na maioria das capas, até a resolução da própria imagem de origem.
- O **Deezer** só oferece quatro tamanhos fixos para a capa de qualquer faixa, álbum, artista ou playlist (56, 250, 500 e 1000 px) — não há tamanho intermediário para pedir. O Downtify escolhe o menor desses quatro que ainda seja pelo menos tão grande quanto o valor configurado (pedir 300 px dá a de 500 px, pois não existe um tamanho exato de 300 px); pedir mais de 1000 px também dá a de 1000 px, a maior do Deezer.

::: info Capas vindas do Spotify não são afetadas
O Downtify já incorpora a **maior** capa que a API de embed pública do Spotify oferece para faixas/álbuns/playlists resolvidos pelo Spotify — não há tamanho maior para pedir. Esta configuração só eleva o teto para faixas resolvidas pelo YouTube Music (busca de texto livre, URLs do YouTube e qualquer faixa do Spotify reassociada ao YouTube Music para o áudio em si) ou pelo Deezer (um link do Deezer colado, ou uma faixa das [Paradas](charts.md)).
:::

Mudar este valor em Configurações tem efeito imediato, inclusive na página de busca aberta no momento — não exige baixar de novo nada que já esteja no disco.

## Sobrescrever arquivos existentes

Ligado por padrão, como no comportamento histórico do Downtify: todo download passa pelo pipeline (busca do áudio, tags, capa, letra) e sobrescreve o que já estiver no caminho de saída calculado.

### O que "de novo" realmente significa

Ligado, um novo download é uma **execução totalmente nova**, não um reparo do arquivo existente. O Downtify não olha o que você já tem: ele pesquisa as suas [fontes de áudio](#audio-provider) na ordem configurada — então, se o slskd for o primeiro, o slskd é tentado primeiro, e não só como alternativa —, busca o áudio na fonte que responder e grava nele as tags, a capa e a letra de hoje.

Isso tem uma consequência que vale conhecer antes de baixar de novo uma biblioteca grande:

::: warning Um formato diferente deixa o arquivo antigo para trás
O novo arquivo é gravado no caminho que o [modelo de nome de arquivo](#output-filename-template) produz, com a extensão do **novo** áudio. O Downtify sobrescreve o arquivo antigo só quando os dois terminam com a mesma extensão.

Então, baixar de novo `Artista - Música.mp3` quando o slskd responde com um FLAC dá **os dois**: `Artista - Música.mp3` (o antigo, intocado) e `Artista - Música.flac`. Com [Deixar os arquivos do slskd onde estão](slskd-navidrome.md#leave-files-in-place) ligado — o padrão —, o arquivo do slskd nem é copiado para a sua pasta de downloads, então o antigo continua exatamente onde estava e o novo fica em `slskd/`.

Nada se perde, mas você ganha duplicatas. Para realmente substituir um arquivo, veja [Substituir áudio](replace-audio.md), que mantém o caminho, o formato e as tags.
:::

### A capa vem do Spotify ou do YouTube Music, não do arquivo

Qualquer arte que o áudio baixado traga — inclusive uma capa de alta resolução incorporada em um arquivo do slskd — é **descartada e substituída** durante a gravação das tags. O Downtify sempre incorpora a capa que busca para a faixa no Spotify ou no YouTube Music, na [resolução da capa](#cover-art-resolution) que você configurou (600 px por padrão). O mesmo vale para título, artistas, álbum e o resto das tags: as tags da própria fonte não são mantidas.

Se o que você quer é uma capa maior em arquivos que já tem, baixar de novo é o caminho longo. [Melhorar biblioteca](library-upgrade.md) faz exatamente isso — compara a capa incorporada de cada arquivo com a do Spotify, do iTunes e do YouTube Music, grava a maior, completa letras e tags ausentes e nunca toca no áudio.

Desligue para nunca baixar uma música que já está no disco. Isso importa mais ao baixar uma playlist, importar uma [biblioteca por CSV](library-import.md) ou deixar o [Monitor de playlists](playlist-monitor.md) sincronizar playlists que compartilham faixas entre si ou com músicas que já estão na sua biblioteca — com a opção ligada, cada uma dessas duplicatas é baixada de novo.

Desligada, o Downtify procura a música **em qualquer lugar da pasta de downloads**, não só onde o novo download iria:

- a raiz da biblioteca (downloads de faixas avulsas),
- a pasta de qualquer playlist (downloads de playlists, importações por CSV, Monitor de playlists),
- uma pasta de artista/álbum, ou o layout plano de antes de você ligar ou desligar *Organizar por artista/álbum*.

Uma música conta como já baixada quando um arquivo de áudio (`.mp3`, `.flac`, `.m4a`, `.ogg`, `.opus`) tem o nome que o [modelo de nome de arquivo](#output-filename-template) produz para ela, comparado sem diferenciar maiúsculas de minúsculas. Um arquivo `.lrc` de letra sozinho não conta. Se o modelo contém pastas (por exemplo `{artists}/{title}`), essas pastas também precisam coincidir, para que a música de outro artista com o mesmo título não seja confundida com esta. Como os arquivos não carregam o ID da faixa do Spotify/YouTube, a correspondência é pelo nome: um arquivo que você renomeou, ou salvo com outro modelo de nome de arquivo, não será reconhecido.

Quando uma música é pulada:

- Nada é buscado: nem áudio, nem capa, nem letra, nem nova gravação de tags. Para faixas do Spotify, a verificação roda antes até da busca no YouTube Music, então músicas já baixadas não custam nenhuma requisição de busca.
- A fila mostra a música como concluída, e os [arquivos M3U](m3u-export.md) das playlists apontam para o arquivo existente onde quer que ele esteja (por exemplo `../Artista - Título.mp3`), então a playlist continua tocando por inteiro.
- Se a mesma música entra na fila duas vezes ao mesmo tempo (listada duas vezes em uma playlist, ou em duas playlists baixadas em paralelo), só uma cópia é baixada. A outra espera por ela e depois é pulada.

## Faixas longas

**Configurações → Downloads e arquivos → Duração máxima** limita a duração das faixas para downloads *e* streams (padrão **10 minutos**, `0` aceita tudo). Músicas mais longas são recusadas antes de qualquer coisa ser buscada, com o erro de fila *"faixas acima de … não são baixadas"* — mixes e uploads de uma hora nunca são o que uma faixa da biblioteca deveria ser. O mesmo limite protege o streaming: uma faixa mais longa é recusada com `400` (quem conhece a duração a passa em `duration`, e o arquivo em cache é verificado de qualquer forma), então uploads longos também nunca se acumulam no cache de streaming. Arquivos já baixados e episódios de podcast (que costumam ser mais longos) não são afetados.

## Provedor de áudio

O provedor de áudio padrão é o **YouTube Music**. O Downtify usa o [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) para buscar a melhor correspondência comparando a duração da faixa. Quando o YouTube Music não tem uma correspondência aceitável, ou só uma com duração muito diferente (provavelmente outra gravação), o Downtify recorre automaticamente à busca no YouTube comum — veja [Como funciona](../how-it-works.md#fallback-to-standard-youtube).

**Configurações → Fontes de áudio** também pode usar só o **YouTube** comum, ou o **slskd** (Soulseek), como uma lista ordenada de alternativas — veja [slskd e Navidrome](slskd-navidrome.md#audio-sources-and-fallback-order).

### Forçar uma fonte de áudio específica

Se o Downtify escolher o vídeo errado do YouTube Music (por exemplo, um cover em vez do original), você pode substituí-lo por faixa:

**Opção A — cole direto uma URL do YouTube Music**

Cole `https://music.youtube.com/watch?v=…` (ou uma URL comum `youtube.com/watch?v=…`) na barra de busca e clique em baixar. O Downtify busca o áudio exatamente desse vídeo.

::: info
Ao baixar por URL do YouTube, os metadados (título, artista, capa) vêm do YouTube e não do Spotify. Para tags limpas, use a Opção B.
:::

**Opção B — forçar o áudio de uma faixa que falhou**

1. Na **Fila de downloads**, clique em **Forçar fonte de áudio** sob uma faixa que falhou.
2. Cole uma URL do YouTube ou do YouTube Music no campo que aparece.
3. Pressione **Enter** ou clique em **Aplicar**.

O Downtify baixa a faixa de novo usando exatamente esse vídeo, mantendo todos os metadados do Spotify (título, artista, álbum, capa, letra).

## Metadados incorporados

O Downtify incorpora as tags a seguir em todo arquivo baixado, qualquer que seja o formato:

| Tag | Fonte |
|-----|--------|
| Título | Embed do Spotify |
| Artista(s) | Embed do Spotify |
| Álbum | Embed do Spotify — em um download de faixa avulsa, o álbum que a página pública da faixa no Spotify indica (o embed da faixa em si não traz nenhum) |
| Ano | Embed do Spotify (busca no nível da faixa) |
| Capa do álbum | Embed do Spotify (capa no nível da faixa) para faixas resolvidas pelo Spotify; miniatura do YouTube Music ou capa do Deezer nos demais casos. Opcional — veja [Baixar capa](#download-cover-art) e [Resolução da capa](#cover-art-resolution) |
| Letra | lrclib (se ativado) |
