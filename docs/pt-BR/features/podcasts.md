---
icon: lucide/mic
---

# Podcasts

Assine um programa e os episódios novos são baixados sozinhos — sem colar o link de novo toda semana. Podcasts são tratados de ponta a ponta de um jeito diferente da música: um episódio já é um arquivo de áudio pronto, num URL `<enclosure>` de RSS, então não há correspondência no YouTube nem transcodificação, só um download e a gravação das tags.

Abra **Podcasts** na barra lateral (no celular: **Mais → Podcasts**).

As assinaturas pertencem a quem assina: cada conta segue os próprios programas (o mesmo feed assinado duas vezes vai para duas pastas), com os próprios episódios, posições de retomada e dispensas. Um admin vê todas as assinaturas.

## Assinando

Cole um destes na caixa **Adicionar um podcast**, ou digite um nome para pesquisar:

| Entrada | O que acontece |
|-------|--------------|
| O URL do feed RSS de um podcast | Buscado e lido diretamente |
| Um link de programa do Spotify (`open.spotify.com/show/…`) | O nome do programa é lido no Spotify e depois associado ao feed RSS público dele pelo diretório de podcasts do iTunes |
| Um link de episódio do Spotify (`open.spotify.com/episode/…`) | Igual ao link de programa, e o episódio específico fica destacado se o título puder ser encontrado no feed |
| O nome de um programa (texto livre) | Pesquisado no diretório de podcasts do iTunes |

::: info Programas exclusivos do Spotify não podem ser baixados
Um programa que só existe no Spotify (sem feed público) é informado como tal — o Downtify não adivinha nem recorre a outra coisa. Pesquise o programa pelo nome para conferir antes de supor que é exclusivo.
:::

Antes de confirmar, você escolhe:

- **Manter** — veja [Quantos episódios são baixados](#how-many-episodes-are-downloaded) abaixo.
- **Intervalo** — com que frequência o feed é verificado em busca de episódios novos, de a cada 15 minutos a uma vez por mês. As assinaturas são verificadas no mesmo cronograma e pela mesma varredura em segundo plano que o [Monitor de playlists](playlist-monitor.md) — para ela, são só mais um tipo de monitoramento.

## Quantos episódios são baixados

A opção **Manter** tem dois comportamentos distintos, escolhidos uma vez por programa:

- **Todo episódio novo** — baixa só o episódio mais recente na hora (assinar não é um convite para puxar todo o catálogo antigo de um programa) e depois baixa os episódios novos que aparecerem a cada verificação. Nada é excluído automaticamente.
- **Últimos *N* episódios** — uma janela móvel. Depois de cada verificação (inclusive a primeira), os *N* episódios publicados mais recentemente são baixados, e qualquer episódio baixado mais antigo é removido para abrir espaço. Aumentar *N* depois torna esses episódios removidos baixáveis de novo; um episódio que você mesmo removeu com **Remover download** nunca volta por esse caminho — veja [Removendo episódios](#removing-episodes).

Mude **Manter** e o intervalo quando quiser, na página do programa.

## Episódios

A página de um programa lista os episódios, do mais novo ao mais antigo, cada um com a data de publicação e a duração. Um episódio fora da política de retenção continua aparecendo aqui — toque em **Baixar** para pegar só esse, por mais antigo que seja.

### Removendo episódios

O menu **⋯** de cada episódio tem **Remover download**, que exclui o arquivo mas mantém o episódio na lista. Há duas maneiras de o arquivo de um episódio sumir, com resultados diferentes:

| Como | Volta automaticamente? |
|-----|----|
| A retenção o tirou (um episódio mais antigo, fora da janela "manter os últimos N") | Sim, se você aumentar **Manter** de novo |
| Você escolheu **Remover download** | Não — baixe-o de novo à mão quando quiser |

### Marcando como reproduzido

Use o menu **⋯** de um episódio para marcá-lo como reproduzido ou não reproduzido à mão, ou simplesmente deixe-o tocar até o fim — um episódio nos últimos segundos de duração é marcado como reproduzido sozinho.

## Reproduzindo episódios

Os episódios tocam no mesmo player integrado da música, com algumas diferenças que só aparecem num episódio de podcast:

- **Voltar 15 s / avançar 30 s** no lugar de aleatório e repetir, que não se aplicam a um único episódio.
- **Velocidade de reprodução** (0,75× a 2×), ao lado do timer de soneca.
- A **posição de retomada** é salva no servidor a cada ~10 segundos de reprodução e mais uma vez quando você pausa, então fechar a aba — ou abrir o Downtify em outro dispositivo — retoma o episódio perto de onde você parou. A lista de episódios de um programa mostra uma dica "Retomar em …" para o que está pela metade.

O coração (músicas curtidas) e "ir para o álbum/artista" não se aplicam a episódios e não aparecem neles.

## Biblioteca

Os podcasts têm seu próprio lugar — nunca aparecem como faixas, álbuns ou artistas na **Biblioteca**, e uma execução de [Melhorar biblioteca](library-upgrade.md) os deixa totalmente em paz (um episódio não tem ID de faixa do Spotify de onde atualizar tags nem letra separada para procurar).

Os arquivos dos episódios continuam no mesmo volume de downloads, em `Podcasts/<Programa>/<data> - <Episódio>.<ext>`, então qualquer servidor de mídia apontado para a sua biblioteca também os vê.

## Tags

O Downtify grava o que os apps de podcast e servidores de mídia já leem de um episódio: título, o programa como álbum, o autor do programa como artista, o ano de publicação, números de episódio/temporada, a arte do próprio programa (a maior entre a imagem do feed e a do iTunes, a mesma ideia da [capa de músicas](download-settings.md#cover-art-resolution)) e a descrição do episódio como comentário. As notas do programa são guardadas como texto simples — o Downtify remove o HTML em vez de renderizá-lo.

## Bom saber

- **Sem podcasts em vídeo.** Um episódio cujo único anexo é um arquivo de vídeo é ignorado por completo; só há suporte para áudio.
- **Sem capítulos.** Feeds que incluem marcadores de capítulo ainda não os têm no Downtify.
- **Não é espelhado no Navidrome.** Diferente das playlists, as assinaturas de podcast não são enviadas para uma biblioteca do Navidrome — os episódios são arquivos comuns que o seu servidor de mídia já enxerga sozinho.
- Cancelar a assinatura (**⋯ → Cancelar inscrição**) remove os episódios baixados por padrão; escolha **Cancelar inscrição, manter episódios baixados** para deixar os arquivos no lugar.

## API

`POST /api/podcasts/resolve`, `GET /api/podcasts/search`, `POST /api/podcasts/subscribe`, `GET/PATCH/DELETE /api/podcasts/shows/{id}`, `GET /api/podcasts/shows/{id}/episodes`, `POST /api/podcasts/episodes/{id}/download`, `DELETE /api/podcasts/episodes/{id}` e `PUT /api/podcasts/episodes/{id}/playback`. Veja a [referência da API](../api-reference.md#podcasts).
