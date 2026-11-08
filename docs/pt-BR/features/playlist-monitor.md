---
icon: lucide/eye
---

# Monitor de playlists

O Monitor de playlists acompanha suas playlists favoritas do Spotify, do Deezer (as públicas) e do YouTube Music — e os artistas que você segue — e baixa automaticamente as faixas e os lançamentos novos assim que aparecem, sem você mexer em nada.

Há dois tipos de monitoramento, cada um na sua aba da página Monitor (**Playlists** e **Artistas**, em `/monitor/playlists` e `/monitor/artists`):

| Monitoramento | Cole | Baixa |
|-------|-------|-----------|
| **Playlist** | O URL de uma playlist do Spotify, de uma playlist pública do Deezer ou do YouTube Music | Todas as faixas da playlist, e depois qualquer faixa acrescentada |
| **Artista** | O URL de um **artista** do Spotify, ou de um artista do YouTube Music | A discografia inteira do artista, e depois cada lançamento novo |

Cada monitoramento mostra o link que acompanha sob o nome, e um selo **Spotify**, **Deezer** ou **YouTube Music** com o serviço de onde foi adicionado.

Veja [Monitoramento de artistas](#artist-watch) para saber como eles funcionam.

Os monitoramentos pertencem a quem os criou: cada conta segue as próprias playlists e artistas (o mesmo URL monitorado duas vezes é varrido duas vezes), e uma varredura atribui seus downloads ao dono do monitoramento. Um admin vê todos.

## Como funciona

O Downtify mantém uma tarefa em segundo plano rodando a cada 60 segundos. A cada varredura, ele verifica se cada monitoramento ativo está na hora de ser inspecionado (conforme o intervalo configurado). Quando uma *playlist* está na hora, o Downtify:

1. Busca a lista completa de faixas no Spotify, no Deezer ou no YouTube Music
2. Compara com o conjunto de faixas já baixadas
3. Baixa as faixas novas pelo mesmo pipeline de um download manual
4. Atualiza o arquivo M3U da playlist (se a geração de M3U estiver ativada)

A primeira verificação, que começa assim que você adiciona o monitoramento, baixa tudo o que já está na playlist; as seguintes baixam só o que foi acrescentado desde então. "Já baixado" é registrado em um pequeno banco SQLite (`downtify_monitor.db` em `/data`), e não conferindo a pasta de downloads — então mover um arquivo baixado para outro lugar do disco (para a sua própria organização de biblioteca, outro disco, onde for) **não** faz o Downtify achar que ele sumiu e baixá-lo de novo na próxima verificação.

Uma varredura separada roda a cada hora e confere se o arquivo de cada faixa baixada ainda está lá. Arquivos realmente excluídos (e não movidos) são esquecidos nesse momento, então a faixa volta a ser elegível para download — na próxima verificação do monitoramento depois dessa varredura horária, não na hora.

Um monitoramento nunca é verificado duas vezes ao mesmo tempo. Adicionar um monitoramento inicia a primeira verificação na hora; se ela ainda estiver baixando quando a próxima varredura agendada chegar, a varredura pula o monitoramento em vez de iniciar um segundo download sobreposto das mesmas faixas.

## Adicionando uma playlist

1. Abra **Monitor** na barra lateral (no celular: **Mais → Monitor**) e fique na aba **Playlists**
2. Cole o URL de uma playlist:
    - Spotify: `https://open.spotify.com/playlist/…`
    - Playlist pública do Deezer: `https://www.deezer.com/playlist/…` (links com prefixo de idioma também funcionam)
    - YouTube Music: `https://music.youtube.com/playlist?list=…` (um link `www.youtube.com/playlist?list=…` também funciona)
3. Escolha um intervalo de verificação (de 15 minutos a uma vez por mês)
4. Clique em **Monitorar playlist**

Cada aba tem a sua caixa. Colar um link de artista na aba Playlists (ou de playlist em Artistas) não adiciona nada: a página diz que tipo de link é e se oferece para movê-lo para a aba certa.

Você também pode começar a monitorar pela página de uma playlist: cole o link dela na barra de pesquisa e use **Monitorar novas faixas** (ou **Monitorar novos lançamentos** em um artista do YouTube Music). As playlists baixadas na Biblioteca oferecem a mesma ação no menu **⋯**. Monitoramentos adicionados assim usam um intervalo de 6 horas — mude-o na página Monitor.

## Playlists do Deezer

Playlists públicas do Deezer são monitoradas como qualquer outra: cole o link na aba **Playlists**, use **Monitorar novas faixas** na página da playlist, ou escolha **Monitorar novas faixas** no menu **⋯** do card de uma playlist nas [Paradas de sucesso](charts.md). Não precisa de conta no Deezer, e todas as faixas são buscadas, por maior que seja a playlist. As músicas são baixadas pelas suas [fontes de áudio](download-settings.md) como qualquer outro link do Deezer, e a playlist ganha o arquivo M3U, a capa e a entrada na Biblioteca como uma do Spotify — mesmo com os arquivos M3U desligados, a Biblioteca guarda quais músicas pertencem a ela. Só playlists públicas podem ser monitoradas, e um link de **artista** do Deezer pode ser baixado, mas não monitorado.

## Playlists do YouTube Music

Use uma playlist do YouTube Music para músicas que não estão no Spotify: remixes, sets ao vivo, covers, uploads de canais promocionais. Cada faixa é baixada do **vídeo exato da playlist**. O Downtify não procura de novo, então o que você recebe é o que você pôs na playlist.

- **Todas as faixas são buscadas**, por maior que seja a playlist. Vídeos excluídos ou privados são pulados.
- **Músicas que o YouTube Music deixa em cinza ainda são baixadas.** Playlists feitas por conversores e importadores (Soundiiz, TuneMyMusic e similares) muitas vezes listam músicas como uploads comuns do YouTube que o YouTube Music mostra como indisponíveis e sem ID de música. O Downtify encontra o vídeo pela miniatura da entrada e o baixa como qualquer outro, então uma playlist assim não sai vazia. Um vídeo realmente excluído ou tornado privado não pode ser baixado: quando o YouTube Music o sinaliza assim, ele é pulado, e quando só dá uma miniatura, a faixa aparece como falha na fila.
- **Artista e título vêm do título do vídeo.** Muitas entradas de playlist são uploads creditados ao canal que os postou (por exemplo `MrSuicideSheep`), e o crédito real está no título, como `Bronze Whale - Patterns`. Para tudo o que não é um lançamento de catálogo, o Downtify separa `Artista - Título` no nome do arquivo e nas tags. Também remove sufixos como `(Official Video)` ou `[Lyrics]`. A parte depois do traço que nomeia uma versão (`Yellow - Live at Glastonbury`) fica no título. Faixas de catálogo (áudio oficial, ou qualquer coisa arquivada em um álbum) mantêm o artista e o título do próprio YouTube Music.
- **Nem todo link `list=` é uma playlist.** O link `OLAK5uy_…` de um álbum ainda é baixado como álbum. Um link `watch?v=…&list=…` é a única música que estava tocando. Um mix de rádio (`list=RD…`) não tem lista fixa de faixas e não pode ser monitorado.

## Monitoramento de artistas

Em vez de montar uma playlist por artista, cole o link de um artista e o Downtify segue o catálogo inteiro dele. Adicione um na aba **Artistas** da página Monitor — cole o URL, escolha um intervalo, clique em **Monitorar artista**. Os monitoramentos de artistas mostram um número de lançamentos em vez de um número de faixas.

URLs aceitos:

- Um URL de artista do Spotify (`https://open.spotify.com/artist/…`)
- Um URL de artista do YouTube Music, por canal (`https://music.youtube.com/channel/UC…`) ou por handle (`https://music.youtube.com/@HenriqueeJuliano`)

Um handle é resolvido para o canal do artista quando você adiciona o monitoramento, então o mesmo artista colado por handle e por URL de canal é reconhecido como um só monitoramento. Um handle que não pertence a um artista do YouTube Music é rejeitado.

A cada varredura, o Downtify lista a discografia do artista, compara com os lançamentos que já processou e baixa todas as faixas de qualquer coisa nova. Uma varredura em regime estável custa uma única requisição — as listas de faixas só são buscadas para lançamentos que ele ainda não viu.

::: info Por que a discografia vem do YouTube Music
O embed público do Spotify expõe o nome de um artista e uma prévia das faixas mais populares, mas **não** a discografia — lê-la exigiria credenciais da API do Spotify, que o Downtify deliberadamente não usa. Então um link de artista do Spotify é resolvido para o nome dele e associado ao mesmo artista no YouTube Music, que também é de onde o áudio é buscado. A vantagem: todo lançamento que o Downtify consegue ver é um que ele consegue de fato baixar. O custo: o link segue o artista do YouTube Music com exatamente esse nome (sem contar maiúsculas e pontuação), o melhor resultado do YouTube Music quando vários têm o mesmo nome. Com um nome comum, confira se o monitoramento é o artista que você queria e, se não for, cole direto o URL do artista no YouTube Music. Um artista do Spotify cujo nome exato nenhum artista do YouTube Music tem só pode ser adicionado assim: o Downtify não chuta.
:::

::: warning A primeira varredura baixa todo o catálogo antigo
Adicionar um artista coloca na fila **todos** os lançamentos dele, o que para um artista prolífico pode ser centenas de álbuns e singles. Defina a **[Pausa entre downloads](download-settings.md#delay-between-downloads)** antes de adicionar um lote de artistas, ou é muito provável que você tenha o ritmo limitado — ou ative **Só lançamentos novos** (abaixo) para pular de vez o catálogo antigo.
:::

### Escolhendo o que baixar

Abaixo da caixa de link na aba **Artistas** (e na janela **Editar** de um monitoramento), duas opções decidem o que um monitoramento de artista baixa:

| Opção | O que faz |
|--------|--------------|
| **Baixar: Álbuns / Singles / EPs** | Só lançamentos dos tipos marcados são baixados. Os três vêm ligados por padrão; pelo menos um precisa ficar ligado. O tipo é o próprio rótulo do YouTube Music para cada lançamento — um lançamento que ele não rotula conta como álbum. |
| **Só lançamentos novos** | Tudo o que o artista já lançou quando o monitoramento começa é pulado; só o que sair depois é baixado. Desligado por padrão. |

Como elas se comportam quando você as muda depois:

- **Ligar um tipo** baixa os lançamentos desse tipo na próxima verificação do monitoramento — inclusive o catálogo antigo, a menos que **Só lançamentos novos** esteja ligado (aí só os lançados desde que o monitoramento começou, ou desde que a opção foi ligada). Lançamentos de um tipo desligado nunca são registrados, então nada se perde ao desligar um tipo por um tempo.
- **Ligar Só lançamentos novos** em um monitoramento existente registra tudo o que já saiu até aquele ponto como pulado; lançamentos já baixados continuam como estão.
- **Desligá-la** baixa, na próxima verificação, os lançamentos que ela pulou (dos tipos marcados).
- Salvar qualquer uma das opções na janela **Editar** verifica o monitoramento na hora, em vez de esperar a próxima verificação agendada.

"Pular" os lançamentos existentes exige uma olhada bem-sucedida na discografia do artista: se o YouTube Music devolve uma lista vazia (o que costuma ser mais um soluço do que um artista sem nada lançado), nada é registrado e a próxima verificação tenta de novo, então uma resposta ruim nunca pode fazer o catálogo antigo ser baixado depois. Apontar um monitoramento de **Só lançamentos novos** para outro artista pula o catálogo antigo desse artista do mesmo jeito.

A lista do Monitor mostra os filtros de um monitoramento sob o link quando não são os padrão (por exemplo **Álbuns** · **Só novos**).

Um lançamento só é registrado como processado quando cada uma de suas faixas está resolvida, então uma faixa que falha por um erro transitório é tentada de novo na próxima varredura em vez de ser pulada para sempre. Faixas que já foram baixadas nunca são buscadas duas vezes.

Os monitoramentos de artistas não geram arquivos M3U — as faixas são organizadas pelas suas configurações de [organização de arquivos](file-organization.md) e não como uma playlist.

### Artistas sugeridos

Abaixo da lista de monitoramentos de artistas, a aba **Artistas** sugere artistas para seguir, em duas listas:

| Lista | Quem aparece |
|-------|--------------|
| **Com base no que você ouve** | Os artistas que você mais ouve: as suas próprias audições, as que o [Descobrir](discover.md) conta. Audições recentes contam mais: o peso de uma audição cai pela metade a cada 45 dias, então um artista que você ouviu muito no ano passado fica abaixo de um que você ouve todo dia agora. |
| **Com base na sua biblioteca** | Os artistas com mais faixas, depois mais álbuns, na biblioteca que você vê. |

Artistas que você já monitora (inclusive monitoramentos pausados) e nomes de coletâneas como **Various Artists** ficam de fora. Cada lista mostra 20 artistas por vez; **Mostrar mais** carrega os próximos. As listas são só suas, inclusive para um admin: as audições de outra conta nunca aparecem. Um artista que um admin escondeu dos usuários fica fora das listas de um usuário, como fica fora da Biblioteca dele.

Carregar as listas não busca nada. **Seguir** procura o nome no YouTube Music, onde um monitoramento de artista acompanha o artista:

- quando exatamente um artista de lá tem esse nome, o monitoramento é adicionado na hora, com o intervalo e as opções **Baixar** / **Só lançamentos novos** definidos na caixa acima;
- senão (homônimos, ou nenhum artista com exatamente esse nome), uma janela mostra os artistas do YouTube Music encontrados, cada um com a foto e um link para o perfil. Escolha um com **Seguir este artista**, ou use **Colar um link** para colar você mesmo o link do artista na caixa acima.

As sugestões só escolhem qual artista monitorar: as músicas continuam sendo baixadas das suas [fontes de áudio](download-settings.md) como sempre.

### Pela página de um artista na Biblioteca

A página de um artista na Biblioteca (`/library/artist`) tem um botão **Monitorar artista**, para seguir um artista que você já tem sem procurar o link dele. Ele procura o nome no YouTube Music do mesmo jeito que o **Seguir** acima:

- quando exatamente um artista de lá tem esse nome, o monitoramento é adicionado na hora. Ele é verificado diariamente e vem com **Só lançamentos novos** ligado, já que a biblioteca tem as músicas anteriores do artista;
- senão (homônimos, nenhum artista com exatamente esse nome, ou a busca falhou), uma janela mostra os artistas do YouTube Music encontrados, cada um com a foto e um link para o perfil, além de uma caixa para o link de um artista do Spotify ou do YouTube Music. As opções **Baixar** e **Só lançamentos novos** no topo valem para quem você seguir.

Depois que o servidor adiciona o monitoramento, o botão vira um link para o **Monitor**, onde você muda o intervalo e as opções; uma recusa (o artista já é monitorado, por exemplo) aparece na janela. Ele não aparece no [modo só biblioteca](library-only.md) nem na página **Various Artists**.

## Intervalos de verificação

| Rótulo | Minutos | Ideal para |
|-------|---------|----------|
| A cada 15 min | 15 | Playlists atualizadas com frequência |
| A cada 30 min | 30 | |
| A cada hora | 60 (padrão) | A maioria das playlists |
| A cada 3 horas | 180 | |
| A cada 6 horas | 360 | |
| A cada 12 horas | 720 | |
| Todo dia | 1 440 | Playlists que mudam devagar |
| Toda semana | 10 080 | Playlists atualizadas semanalmente |
| A cada 2 semanas | 20 160 | |
| Todo mês | 43 200 | Arquivo ou playlists raramente atualizadas |

Você pode mudar o intervalo de uma playlist existente a qualquer momento pelo cartão do monitor, sem removê-la e adicioná-la de novo.

## Gerenciando playlists monitoradas

Cada aba lista só o seu tipo de monitoramento. Acima da lista:

- **Filtrar** — digite parte de um nome ou do link (por exemplo o id de uma playlist) para restringir a lista
- **Tudo / Pausados** — mostra só os monitoramentos pausados
- **Verificar tudo agora** — verifica todos os monitoramentos ativos da aba atual
- Uma faixa com quantas músicas chegaram no período escolhido (**7 dias**, **30 dias** ou **90 dias**) e, somando todos os monitoramentos, quantas músicas eles têm, o espaço que ocupam (**No disco**) e quantas estão **Em mais de um monitoramento** — veja [Atividade e armazenamento por monitoramento](#activity-and-storage-per-watch)

Em cada linha:

- Interruptor **Ativo** — pausa ou retoma o monitoramento sem removê-lo
- **Verificações** — com que frequência é verificado
- **Verificar agora** (↻) — verifica na hora, fora do agendamento
- **Atividade** — músicas novas no período escolhido, a média por semana e se esse ritmo está subindo ou caindo; clique para abrir a página do monitoramento
- **Armazenamento** — o espaço das músicas que só este monitoramento tem, mais quantas ele compartilha com outros
- **Editar** (✎) — vê e muda o link, o intervalo e o estado ativo do monitoramento (veja [Editando um monitoramento](#editing-a-watch))
- **⋯** — **Atividade e músicas** (a página do monitoramento), pausar/retomar, copiar o link, abrir o original ou **Parar de monitorar** (o registro é excluído; os arquivos baixados são mantidos)

**Atividade** e **Armazenamento** são colunas como as outras: esconda ou redimensione em **Colunas**.

### Editando um monitoramento

Clique no nome de um monitoramento ou no botão **Editar** dele. A janela mostra o link completo que está sendo seguido, com **Copiar link** e **Abrir original**, além de quando o monitoramento foi adicionado, quando foi verificado pela última vez e quantas faixas ou lançamentos tem. Você pode mudar:

- **Link** — precisa ser o mesmo tipo de link (uma playlist para um monitoramento de playlist, um artista para um de artista):
    - Outro link para a **mesma** playlist ou artista (por exemplo com outro código de compartilhamento `?si=`, ou o link do YouTube Music em vez do `www.youtube.com`) só atualiza o endereço guardado. Nada mais muda.
    - Um link para uma playlist ou artista **diferente** aponta o monitoramento para ele. O monitoramento mantém o intervalo e o estado ativo, mas assume o novo nome e recomeça: o histórico de downloads ou lançamentos é apagado e, se está ativo, é verificado de imediato. Faixas que já estão na sua biblioteca não são baixadas de novo, e os arquivos do alvo anterior ficam onde estão.
    - Um link para algo que já é monitorado é recusado.
- **Verificar a cada** e **Ativo**.

Isso é útil para playlists "ao vivo" que são substituídas: abra o monitoramento para conferir qual playlist ele realmente segue e cole a nova se ela mudou.

## Ordenação

O controle **Ordenar por** acima da lista ordena a aba atual por:

| Campo | Observações |
|-------|-------|
| Data de adição | Padrão — mais novos primeiro |
| Nome | Alfabética |
| Última verificação | Verificados há menos tempo primeiro; nunca verificados por último |
| Frequência | Menos frequentes (intervalo mais longo) primeiro |
| Número de faixas / lançamentos | Mais primeiro |
| Atividade recente | Músicas novas no período escolhido |
| Ritmo médio | Músicas novas por dia no período |
| Crescimento do armazenamento | Espaço das músicas novas do período |
| Armazenamento só dele | Espaço das músicas que nenhum outro monitoramento tem |
| Músicas baixadas | Músicas no disco que o próprio monitoramento baixou |

O botão ao lado alterna entre ordem crescente e decrescente. A escolha é lembrada no navegador e só muda a lista — não a ordem de verificação nem o agendamento.

## Escolhendo um horário de sincronização diária

Por padrão, uma playlist verificada todo dia (ou semana / 2 semanas / mês) sincroniza no horário em que foi originalmente adicionada ou verificada pela última vez — não há horário do dia garantido. Para fixar as sincronizações de um dia ou mais em uma hora específica (por exemplo, rodar de madrugada às 3h em vez de a qualquer hora), defina a variável de ambiente `DOWNTIFY_MONITOR_SYNC_TIME` junto com `TZ`. Veja [Variáveis de ambiente](../getting-started/environment-variables.md#playlist-monitor) para a referência completa.

- Só afeta intervalos de um dia inteiro ou mais — intervalos menores (15 min – 12 h) não são afetados, já que ancorá-los em um único horário diário quebraria o ritmo deles.
- A primeiríssima verificação depois de adicionar uma playlist sempre roda na hora, independentemente desta configuração.

## Enriquecimento de metadados por faixa

As entradas do embed de playlist do Spotify não têm o ano de lançamento e usam a capa da playlist em vez da capa do álbum de cada faixa. O Downtify busca de novo cada faixa nova individualmente para obter a capa e o ano corretos antes de baixar — recorrendo aos dados no nível da playlist se a busca por faixa falhar. As entradas de playlist do YouTube Music pulam essa etapa: cada uma já traz os metadados do próprio vídeo.

## Integração com M3U

O M3U da playlist é reescrito **depois que cada faixa termina**, então cresce conforme a varredura baixa, em vez de aparecer só quando tudo termina. A playlist é tocável desde a primeira faixa, e um download lento ou travado mais adiante na lista nunca segura as faixas que já chegaram. Uma reescrita final no fim da varredura reavalia tudo no sistema de arquivos.

Downloads manuais de playlists/álbuns e importações por CSV se comportam da mesma forma. Veja [Exportação M3U](m3u-export.md#when-it-is-written) para detalhes.

Com [Salvar a capa da playlist](playlist-cover-art.md) ligado, a capa é buscada uma vez por varredura que tem faixas para baixar — antes da primeira delas, para que a pasta se pareça com a playlist enquanto se enche. Uma varredura que não acha nada novo não a busca de novo.

## O que acontece com músicas que saem de uma playlist

Playlists "ao vivo" (o *Top 50* do Spotify, o *Descobertas da Semana*, paradas editoriais) mudam toda semana. O Downtify trata um monitoramento como uma **fonte de música nova**, nunca como algo que governa o que você guarda:

- **Arquivos de áudio baixados nunca são excluídos por um monitoramento.** Nem quando uma faixa sai da playlist, nem quando sai de todas as playlists que você monitora, nem quando a própria playlist encolhe, nem quando você pressiona **Parar de monitorar**.
- **Só a playlist acompanha a playlist.** A cada varredura, o [arquivo M3U](m3u-export.md) é reescrito a partir das faixas atuais da playlist, na ordem atual, então uma faixa que saiu some do M3U. O arquivo dela continua na pasta e na sua biblioteca, pesquisável e tocável — inclusive pelo Navidrome, Jellyfin ou qualquer coisa apontada para a mesma pasta.
- **Uma faixa que não está em nenhuma playlist continua sendo uma faixa.** Nada varre atrás de arquivos "órfãos".

Isso faz de uma playlist de parada um feed de descobertas utilizável: músicas novas chegam automaticamente, e o que elas deixam para trás se acumula como a sua biblioteca.

```
Top 50 - USA        →  new song appears   →  Downtify downloads it
                    →  song drops out     →  M3U updated, file kept
```

As únicas coisas que excluem áudio são as que você pede explicitamente: **Excluir** numa faixa ou numa seleção na Biblioteca, excluir uma playlist pela Biblioteca (que realmente exclui as faixas dela — e pergunta antes), ou remover arquivos você mesmo do sistema de arquivos.

Para tirar da playlist uma música que você não quer, e mantê-la fora a cada verificação, oculte-a: veja [Músicas ocultas da playlist](hidden-playlist-songs.md). O arquivo dela continua na sua biblioteca.

::: info Excluir um monitoramento vs. excluir uma playlist
**Parar de monitorar** (no menu ⋯ do monitoramento) só esquece o monitoramento: nada muda no disco. **Excluir** numa playlist da página **Biblioteca** é a destrutiva — remove as faixas dessa playlist, o M3U dela e a entrada no catálogo.
:::

Se um arquivo realmente some — você o tirou da pasta de downloads, ou o excluiu à mão —, uma varredura horária percebe e esquece o registro dele no Downtify, então a próxima verificação de um monitoramento que ainda lista a faixa a baixa de novo. Um arquivo apenas *movido* dentro da pasta de downloads ainda é encontrado e não é baixado de novo.

## Armazenamento

O estado do monitor fica em um banco SQLite em `/data/downtify_monitor.db`. O banco registra:

- Cada monitoramento (tipo, ID de playlist do Spotify ou do YouTube Music ou ID de canal do YouTube Music, nome, URL, intervalo, estado ativo, hora da última verificação). Se um monitoramento é do Spotify ou do YouTube Music é lido do URL guardado, então não é preciso uma coluna extra.
- Cada faixa baixada com sucesso por monitoramento, incluindo o nome do arquivo no disco
- Para monitoramentos de artistas, os lançamentos já processados, para que uma varredura só busque listas de faixas de lançamentos realmente novos — inclusive os que **Só lançamentos novos** pulou, marcados como tal para que desligá-la possa trazê-los de volta — além dos tipos de lançamento do monitoramento e se ele é de só lançamentos novos
- Cada faixa que um monitoramento adicionou (`watch_events`): quando, o arquivo, qual provedor de áudio a buscou, se o monitoramento a baixou ou a encontrou já na biblioteca, e se veio com a primeira verificação. Essas linhas guardam o id, o nome e o dono do monitoramento como eram, e sobrevivem a ele: parar ou redirecionar um monitoramento as mantém, então as músicas dele continuam dizendo de onde vieram
- As faixas que cada monitoramento continua sem conseguir baixar (`watch_failures`), até uma dar certo, sair da playlist ou o monitoramento ser redirecionado

Bancos criados antes do Monitoramento de artistas são migrados automaticamente na inicialização; as linhas existentes continuam funcionando como monitoramentos de playlists. As faixas registradas antes de o Downtify manter o histórico acima são adicionadas a ele uma vez, na primeira inicialização, com resultado desconhecido (**Antes do registro**) — as do primeiro dia de um monitoramento contam como a primeira verificação.

## Atividade e armazenamento por monitoramento

A página Monitor e a página de cada monitoramento (**Atividade e músicas** no menu **⋯** de um monitoramento, ou um clique na **Atividade** dele) mostram quais monitoramentos fazem sua biblioteca crescer — útil com muitos monitoramentos, ou para descobrir por que um mix gerado trouxe músicas que você não esperava.

**O que conta como atividade.** Só contam as músicas que um monitoramento realmente adicionou: as que ele baixou. As que ele encontrou já na sua biblioteca (outro monitoramento, ou um download seu, já as tinha) contam à parte como **Já na biblioteca**, assim como o que veio na primeira verificação, quando ele baixa tudo o que a playlist já tinha. Assim, uma playlist estática aparece parada mesmo que a primeira verificação tenha baixado 300 músicas, e um mix que adiciona 15 músicas por semana aparece como 15 por semana. As faixas registradas antes de o Downtify manter esse histórico contam como adicionadas, e a página diz quantas são.

No período escolhido (7, 30 ou 90 dias, lembrado no navegador) um monitoramento mostra:

| Número | O que é |
|--------|------------|
| Músicas novas | Músicas que ele adicionou no período |
| Por dia / Por semana / Por mês | O ritmo médio no período — ou desde que o monitoramento começou, se isso for mais recente |
| Tendência | Se o ritmo está subindo (**Adicionando mais ultimamente**), caindo (**Adicionando menos ultimamente**) ou estável, pelas músicas novas por dia (7 dias) ou por semana (30 e 90 dias); **Ainda é cedo para dizer** enquanto houver menos de três delas para comparar |
| Crescimento do armazenamento | Espaço das músicas novas do período que ainda estão no disco |

**Armazenamento.** Um arquivo é guardado uma vez, não importa quantos monitoramentos o tenham, e os números refletem isso: **Só neste monitoramento** é o espaço das músicas que nenhum outro monitoramento tem (o que parar o monitoramento e excluir as músicas dele liberaria), **Compartilhadas** as músicas que outros monitoramentos também têm, e a faixa da página Monitor conta cada arquivo uma vez. Monitoramentos de outras contas contam para saber se um arquivo é compartilhado, mas não são nomeados.

A página de um monitoramento mostra também:

- **Músicas no disco**, **Baixadas por ele**, **Já na biblioteca** e **Com falha** — como as músicas chegaram lá, e quantas continuam falhando no download (listadas mais abaixo, com o número de tentativas e o último erro)
- **De onde veio o áudio** — YouTube Music, YouTube, Soulseek (slskd) ou Deemix, por música no disco
- **Músicas deste monitoramento** — todas as músicas que ele tem, das mais recentes para as mais antigas, incluindo as que já saíram da playlist, com filtros (**Últimos 30 dias** — ou o período escolhido —, **Baixadas por ele**, **Já na biblioteca**, **Antes do registro**). Selecione músicas para tocar, pôr na fila, adicionar a uma playlist, baixar como ZIP ou excluir — por exemplo, para limpar o que um mix trouxe na última semana
- **Abrir na Biblioteca** (a página da playlist, ou a do artista num monitoramento de artista), **Abrir original** e **Verificar agora**

O id do monitoramento (`#12`) aparece ao lado do nome, então dois monitoramentos do mesmo link — duas contas seguindo uma playlist, por exemplo — podem ser diferenciados.

## De onde veio uma música

**De onde veio** no menu de uma música (em qualquer lugar da Biblioteca) diz qual monitoramento a baixou primeiro, quando e com qual provedor — **Primeira verificação** quando veio com a primeira verificação — e lista todos os monitoramentos que a têm agora, cada um com seu id, dono (para um admin), quando recebeu a música e como: **Baixou**, **Já na biblioteca** ou **Antes do registro**. É um arquivo só: os monitoramentos que compartilham uma música apontam todos para a mesma cópia.

Dali, **Atividade e músicas** abre a página do monitoramento e **Abrir na Biblioteca** a playlist dele. Um monitoramento que foi parado, ou que agora segue outro link, continua sendo mostrado como origem das músicas que baixou. Para uma música registrada antes de esse histórico existir, aparece o primeiro monitoramento que a registrou, marcado como **Provavelmente**. Uma música que nenhum monitoramento baixou (uma que você mesmo baixou) diz isso.

Um usuário vê os próprios monitoramentos pelo nome; uma música que o monitoramento de outra conta baixou diz só isso, e quando.
