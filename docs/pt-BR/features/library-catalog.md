---
icon: lucide/library
---

# Catálogo da biblioteca e sincronização de caminhos

O Downtify mantém um pequeno **catálogo** dos arquivos em `/downloads` (a pasta do slskd, quando os [arquivos do slskd são deixados no lugar](slskd-navidrome.md#leave-files-in-place), e as [pastas extras](external-library.md) que você adiciona em Configurações) para que a página Biblioteca, o player, a exportação M3U, a sincronização com o Navidrome e a detecção de duplicatas permaneçam consistentes quando arquivos são movidos ou playlists crescem.

## O que é guardado

| Armazenamento | Local | Finalidade |
|-------|----------|---------|
| **Índice de faixas** | `/data/downtify_library.db` | Associa IDs de faixa do Spotify a caminhos da biblioteca, para que uma faixa já presente no disco seja reconhecida |
| **Catálogo de playlists** | `/data/downtify_library.db` | Quais faixas pertencem a cada playlist baixada do Spotify |
| **Downloads de playlists** | `/data/downtify_library.db` | Downloads de playlists do Spotify acompanhados e um cache das listas de faixas delas no Spotify |
| **Índice do Navidrome** | `/data/downtify_library.db` | IDs de músicas do Navidrome por arquivo |
| **Cache de metadados da biblioteca** | `/data/downtify_library.db` | Título, artista, todos os artistas creditados, álbum, artista do álbum, número da faixa, ano, duração e tamanho da capa por arquivo para `GET /tracks`, relido só quando a data de modificação ou o tamanho do arquivo muda |
| **Execuções de melhoria** | `/data/downtify_library.db` | A fila de [melhoria da biblioteca](library-upgrade.md) e quando cada faixa foi verificada pela última vez, para que uma execução sobreviva a uma reinicialização |
| **Cache de varredura de caminhos** | RAM, mais um instantâneo em `/data/downtify_library.db` | Linhas consolidadas de `GET /tracks`, listagens de playlists e pares de caminhos. As rotas da interface servem esse instantâneo sem percorrer o disco. Cada download concluído é **mesclado ao instantâneo na hora** (para que um artista novo apareça sem esperar). Uma exclusão **tira esses arquivos do instantâneo na hora** (para que um álbum suma da grade sem esperar). Uma varredura completa da árvore roda em segundo plano alguns segundos depois que a fila de downloads fica ociosa — não em um temporizador fixo. `GET /list?refresh=true` descarta o instantâneo e varre de novo agora. |
| **Itens ocultos** | `/data/downtify_library.db` | As músicas, álbuns e artistas que um admin [ocultou dos usuários](users.md#hiding-from-users) |
| **Cache de capas** | `/data/cover_cache` (opcional) | Imagens de capa extraídas para `GET /cover` |

Os arquivos são associados após movimentações por uma **chave de conteúdo** — um hash do nome e do tamanho do arquivo. Mover um arquivo para outra pasta mantém a chave dele; substituí-lo por outro arquivo dá uma nova.

## Configurações → Biblioteca

### Cache de capas

Quando ativado, o Downtify guarda as imagens de capa extraídas em `/data/cover_cache`, para que a Biblioteca e o player não releiam as tags a cada miniatura. Pode ser desligado a qualquer hora; só custa espaço em disco.

### Corrigir caminhos da biblioteca

Use depois de **mover ou renomear arquivos no disco** fora do Downtify, ou de excluí-los à mão.

1. Abra **Configurações → Biblioteca → Corrigir caminhos da biblioteca**.
2. O Downtify varre as pastas da biblioteca e:
    - **atualiza caminhos** no índice de faixas e no catálogo de playlists quando um arquivo não está mais onde estava, mas o mesmo arquivo (mesma chave de conteúdo) é encontrado em outro lugar;
    - **remove entradas obsoletas** de arquivos que não existem mais;
    - **indexa** entradas antigas que foram guardadas antes de existirem chaves de conteúdo;
    - **leva as [músicas curtidas](liked-songs.md#keeping-likes-in-step-with-the-files)** para o novo local delas.
3. Se **Gerar M3U** e/ou **Criar playlists no Navidrome** estiverem ativados, as playlists afetadas são reescritas.

Só roda quando você pressiona o botão (ou chama `POST /api/library/reconcile`) — nunca em um agendamento.

### Pastas de músicas existentes

Para tocar uma coleção que o Downtify não baixou, adicione as pastas em **Configurações → Biblioteca** e pressione **Sincronizar pastas**. Os arquivos ficam no disco; as tags são lidas e os artistas associados. Veja [Pastas de músicas existentes](external-library.md).

::: warning
Reescrever uma playlist exclui arquivos da biblioteca cujas tags claramente não correspondem à faixa do Spotify para a qual estão registrados — veja [slskd e Navidrome](slskd-navidrome.md#playlist-sync).
:::

::: info Exclusões vs. movimentações
Excluir faixas pela página **Biblioteca** já limpa o catálogo e reescreve em segundo plano os arquivos M3U e as playlists do Navidrome afetados, então não há nada a corrigir depois.
:::

## Página Biblioteca

A página Biblioteca tem quatro abas — **Álbuns**, **Artistas**, **Playlists** e **Faixas**:

- **Álbuns, artistas e playlists** aparecem como uma grade de capas ou uma lista compacta (a escolha é lembrada), com um filtro de texto e ordenação por adicionados recentemente, nome, artista, ano ou número de faixas. Álbuns e artistas são montados a partir das tags de cada arquivo (artista do álbum, álbum, ano), então não dependem de como os arquivos estão organizados no disco. Uma coletânea — artista do álbum `Various Artists`, com a marca de coletânea — fica como um álbum só em Álbuns, enquanto as faixas dela ficam nas páginas dos seus artistas. Uma faixa com `Various Artists` sem essa marca (como versões antigas marcavam qualquer música com vários artistas, inclusive uma dupla como `Zé Neto & Cristiano`) é agrupada pelo seu primeiro artista. Uma faixa sem tag de álbum aparece em Faixas e no artista dela, não em Álbuns.
- **Artistas** lista todo artista ao qual uma faixa pertence — o artista do álbum dela, ou, numa coletânea (ou num arquivo sem artista do álbum), o primeiro artista. A página desse artista também traz as faixas em que ele é convidado, marcadas com **Participação**; a aba Álbuns dele só mostra álbuns próprios (e some quando não há nenhum). Um nome que só aparece creditado ao lado de outro não ganha página própria: as tags podem nomear os integrantes de uma dupla um a um (`Henrique; Juliano`, como o YouTube Music credita algumas duplas e versões antigas do Downtify gravavam), e uma página para cada integrante seria um artista que não existe. **Various Artists** não aparece: as faixas de uma coletânea ficam nas páginas dos seus artistas, e o álbum continua em Álbuns.
- Onde quer que uma faixa mostre seus artistas — listas de faixas, a tela Tocando agora, o Finder e as linhas de músicas populares — cada nome leva à página do artista na Biblioteca, ou a uma busca por ele quando a Biblioteca não tem página dele. Nessas linhas o nome do álbum também leva ao álbum na Biblioteca, ou a uma busca por ele quando a Biblioteca não o tem. O Descobrir e o Finder dele nunca mandam você para a Busca: ali, um artista ou álbum que a Biblioteca não tem é texto simples. Os artistas vêm da tag `ARTISTS` do arquivo (veja [Vários artistas e coletâneas](file-organization.md#several-artists-and-compilations)), então um nome como *Earth, Wind & Fire* nunca é dividido na vírgula; um arquivo sem essa tag tem o texto do artista dividido em `;`, ` / ` ou `, `, a menos que esse texto também seja o artista do álbum do arquivo, ou que os nomes resultantes formem o artista do álbum (`Henrique; Juliano` num álbum de `Henrique, Juliano`) — aí é um nome só.
- **Playlists** são as playlists baixadas com um [arquivo M3U](m3u-export.md), as playlists que você cria com **Nova playlist** (editáveis), além de [downloads de playlists](slskd-navidrome.md#playlist-downloads) acompanhados que ainda não têm M3U. As playlists importadas do Spotify/YouTube ficam somente leitura até você [desvinculá-las](#detach-an-imported-playlist). As playlists que outras pessoas [compartilham com você](users.md#sharing-playlists) são listadas abaixo da grade, separadas das suas. Depois de você [curtir](liked-songs.md) uma música, *Músicas curtidas* aparece primeiro. Uma playlist criada por você usa um mosaico de até quatro capas de faixas; as importadas mantêm a arte salva com o M3U.
- **Faixas** é uma tabela ordenável (título, álbum, formato, data de adição, duração) com filtro de texto, filtro de formato e caixas de seleção — clique em uma e depois clique com Shift em outra para selecionar um intervalo. Ordene clicando no título de uma coluna, ou com o menu **Ordenar por** acima da tabela (a única forma no celular, onde os títulos ficam ocultos): adicionadas recentemente ou mais antigas primeiro, título, artista ou álbum de A–Z ou Z–A, mais longas ou mais curtas primeiro. A escolha é lembrada.

As músicas de uma playlist têm o mesmo menu **Ordenar por**, com **Ordem da playlist** (a ordem própria da playlist, que é por onde ela começa) acrescentada às opções; clicar no título de uma coluna também funciona. **Tocar** e a lista de músicas seguem a ordem que você escolheu, e a escolha é lembrada, para toda playlist.

Abrir um álbum, artista ou playlist mostra as faixas com **Tocar**, **Aleatório** e **Adicionar à fila**. **Baixar como ZIP** é um botão na página de uma playlist e fica no menu **⋯** na de um álbum. Uma playlist criada por você também tem **Adicionar músicas**, **Renomear** e **Compartilhar…** (veja [compartilhando playlists](users.md#sharing-playlists)); uma importada tem **Compartilhar…** e **Desvincular da origem** (abaixo); a página de uma playlist baixada mostra quantas faixas dela foram baixadas, lista as que faltam com **Baixar o que falta** e oferece **Monitorar novas faixas**. **Excluir playlist** fica no menu **⋯**: playlists importadas excluem o áudio; uma playlist criada por você só remove a playlist.

### Buscar numa playlist

Uma playlist longa só desenha as músicas que estão na tela, então a busca do próprio navegador (`Ctrl` + `F`) não enxerga o resto. A caixa **Buscar nesta playlist**, acima das músicas, procura em todas elas — título, artista, álbum e nome do arquivo, sem diferenciar maiúsculas nem acentos. Na página de uma playlist, `Ctrl` / `⌘` + `F` põe o cursor nela (aperte de novo dentro da caixa para a busca do navegador), e `Esc` a limpa.

Ao lado, filtros estreitam a lista. Cada um mostra quantas músicas tem e só aparece quando tem alguma:

| Filtro | Mostra |
|--------|--------|
| **Todas** | Todas as músicas baixadas da playlist |
| **Faltando** | Músicas da playlist de origem que ainda não estão na biblioteca (downloads de playlists do Spotify), com o estado do download — consultadas no Spotify quando você escolhe o filtro |
| **Falharam** | As músicas faltando cujo download falhou, cada uma com o botão de tentar de novo — depois que **Faltando** foi consultado |
| **YouTube Music**, **Soulseek (slskd)**, **Deemix**… | As músicas que essa origem baixou. O Downtify passa a lembrar disso para as músicas baixadas a partir de agora; as mais antigas contam como **Origem desconhecida**, exceto arquivos do slskd deixados no lugar e músicas das suas próprias pastas |
| **Fora do Navidrome** | Com a [sincronização com o Navidrome](slskd-navidrome.md) ligada, as músicas que o Downtify ainda não associou a uma música do Navidrome |

A busca e um filtro funcionam juntos, e o número de músicas exibidas aparece logo abaixo. Cada música mantém seu número na playlist, e ordenar, tocar e o menu de cada música valem para o que está sendo exibido.

### Desvincular uma playlist importada

Uma playlist importada de um link do Spotify ou do YouTube Music não pode ser editada, porque o Downtify a mantém em sincronia com a origem. Para arrumar uma — tirar uma música que não pertence, acrescentar uma que pertence — abra-a e escolha **Desvincular da origem**. Ela vira uma playlist como as que você cria: as músicas e o dono continuam como estão, e você ganha **Adicionar músicas**, **Renomear** e a remoção de músicas. Em troca, o vínculo com a origem é cortado: ela deixa de ser atualizada pelo Spotify ou pelo YouTube Music, o monitoramento dela no [Monitor de playlists](playlist-monitor.md) (se tinha) é removido e o acompanhamento de "músicas ausentes" some. As músicas já baixadas nunca são tocadas, e a arte dela fica até a sua primeira edição, quando um mosaico das músicas a substitui. Desvincular não pode ser desfeito pelo app; baixar o link de novo cria uma nova playlist importada.

Todas as contas veem a mesma biblioteca: o que um admin [oculta dos usuários](users.md#hiding-from-users) fica de fora para eles, e um admin vê tudo, com um olho riscado no que está oculto. Os admins ocultam e mostram pelo menu `…` de uma música, álbum ou artista, ou pela barra de seleção em **Faixas**.

**Baixar como ZIP** salva as faixas selecionadas no dispositivo de onde você navega, como um único ZIP, mantendo a estrutura de pastas — útil quando o Downtify roda num servidor doméstico e você quer um lote de faixas localmente. Combine com **Selecionar tudo** para levar tudo o que o filtro atual mostra. O arquivo é montado enquanto baixa, então nada é gravado no disco do servidor, e é limitado a 2000 faixas por download.

## API

| Método | Caminho | Descrição |
|--------|------|-------------|
| `GET` | `/list?refresh=true` | Caminhos da biblioteca, ignorando o cache de varredura de caminhos |
| `GET` | `/api/library/summary` | Contagens da página Início e álbuns recentes, sem a lista completa de faixas |
| `GET` | `/api/library/albums` | Blocos de álbuns (contagens + arquivo de capa), sem todas as faixas |
| `GET` | `/api/library/artists` | Blocos de artistas (contagens + arquivo de capa) para a Biblioteca e o Descobrir |
| `GET` `POST` | `/api/library/visibility` | Admins: o que está oculto dos usuários, e ocultar / mostrar itens |
| `POST` | `/api/library/lookup` | Linhas da biblioteca para músicas da pesquisa/links já baixadas |
| `GET` | `/tracks` | Faixas da biblioteca com tags. `?playlist=`, `?artist=`, `?album=`, `?q=` e `?limit=` devolvem um subconjunto |
| `GET` | `/media/{path}` | Serve um arquivo da biblioteca, inclusive caminhos `slskd/…` e `ext/…` |
| `GET` | `/playlist-cover?file=…` | Serve a própria [capa](playlist-cover-art.md) de uma playlist, informada como `cover` por `/playlists` |
| `POST` | `/api/library/archive` | Prepara um ZIP das faixas selecionadas (devolve um ticket de uso único) |
| `GET` | `/api/library/archive/{token}` | Transmite esse ZIP ao navegador |
| `DELETE` | `/api/library/playlist?playlist_name=…` | Exclui as faixas, o M3U e o catálogo de uma playlist importada — ou só o M3U de uma playlist que você criou |
| `POST` | `/api/library/playlists` | Cria uma playlist editável vazia |
| `POST` | `/api/library/playlists/tracks` | Adiciona ou remove arquivos da biblioteca em uma playlist que você criou |
| `POST` | `/api/library/playlists/rename` | Renomeia uma playlist que você criou |
| `PUT` | `/api/library/playlists/visibility` | [Compartilha uma playlist](users.md#sharing-playlists) sua, só para visualização |
| `POST` | `/api/library/playlists/copy` | Salva uma cópia de uma playlist que você pode abrir como uma editável sua |
| `POST` | `/api/library/playlists/detach` | Transforma uma playlist importada em uma editável |
| `POST` | `/api/library/reconcile` | Corrige os caminhos da biblioteca e depois atualiza as playlists do M3U/Navidrome |
| `POST` | `/api/library/external/sync` | Inicia uma varredura em segundo plano das pastas de música extras |
| `GET` | `/api/library/external/sync` | Sincronização de pasta extra em andamento, ou o último registro concluído |
| `POST` | `/api/library/external/unmap` | Tira uma pasta extra da biblioteca sem excluir áudio |
| `GET`/`POST` | `/api/library/upgrade…` | Varre e repara o que já foi baixado — veja [Melhorar biblioteca](library-upgrade.md#api) |

Veja a [referência da API](../api-reference.md#library) para os formatos de requisição e resposta.
