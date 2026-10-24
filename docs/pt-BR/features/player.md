---
icon: lucide/headphones
---

# Player integrado

O Downtify vem com um player web para você ouvir a música baixada sem um app separado. Pressione play em qualquer faixa, álbum, artista ou playlist da Biblioteca — ou em um download concluído na Fila — e o player começa.

## Barra do player

Enquanto uma faixa está carregada, uma barra do player flutua na parte de baixo de todas as páginas: capa, título e artista, aleatório, anterior, play/pause, próxima, repetir, tempo decorrido/total e atalhos para os painéis de letra e de a seguir (o da letra pode ser [ocultado](#hiding-the-lyrics)). Em telas largas ela também tem um controle de volume e uma barra de busca ao longo da borda superior; no celular ela encolhe ao essencial e mostra uma linha fina de progresso.

Ao lado do título há um coração para [curtir a música](liked-songs.md); o celular o deixa fora da barra para sobrar espaço ao título, e o tem em **Tocando agora** e nas listas de faixas.

Clique no título ou na capa, ou no botão de expandir, para abrir **Tocando agora**.

## Tocando agora

Uma visão em tela cheia, tingida com cores tiradas da capa do álbum atual:

- **Capa grande**, título e artista (clique no artista ou no rótulo *Tocando de* para ir ao artista, álbum ou playlist), com um coração ao lado do título para [curtir a música](liked-songs.md). A capa e a letra encolhem junto com a janela — inclusive quando você muda só a altura — para ficarem abaixo do cabeçalho.
- **Barra de busca** — clique ou arraste, ou use as setas quando ela estiver em foco. Enquanto uma faixa toca, ondas suaves deslizam sobre a parte já tocada, em cores tiradas da capa do álbum; elas ficam planas quando pausado e paradas se o seu sistema pedir movimento reduzido
- **Controles de reprodução** — aleatório, anterior, play/pause, próxima, repetir (desligado → repetir tudo → repetir uma)
- **Volume** com botão de mudo, salvo entre sessões. Oculto no celular, onde os botões físicos controlam o nível
- **Timer de desligamento** — para a reprodução em 15, 30, 45, 60 ou 90 minutos, ou no fim da faixa atual. O tempo restante aparece ao lado do botão do timer
- **Informações do arquivo** — formato e tamanho do arquivo em reprodução

Quatro painéis ficam ao lado da capa em telas largas, ou a substituem no celular:

- **Letra** — letras sincronizadas destacam a linha atual e rolam com a música; clique em uma linha para ir até ela. Letras simples são exibidas como estão. A letra vem do arquivo `.lrc` ao lado da faixa, ou da embutida nas tags dela — veja [Letras](lyrics.md). Você pode ocultar este painel — veja [Ocultando a letra](#hiding-the-lyrics).
- **A seguir** — a fila de reprodução. Arraste faixas para reordená-las, remova faixas avulsas ou limpe tudo depois da atual.
- **Detalhes** — título, artista, álbum, número da faixa, ano, duração, formato, tamanho, data de adição e caminho do arquivo.
- **Equalizador** — molde o som com dez bandas de frequência; veja [Equalizador](#equalizer).

Tocando agora faz parte do endereço da página (`?np=1`, mais `&panel=lyrics|queue|details|equalizer`), então o botão Voltar do navegador o fecha e um recarregamento o mantém aberto.

## Ocultando a letra

Prefere a capa e a fila sem as palavras? Desligue **Configurações → Geral → Player → Mostrar letras no player**. Vale na hora e tira tudo o que leva à letra no player:

- o painel **Letra** e a aba dele (no celular, o botão dele no rodapé de Tocando agora);
- o botão de letra na barra do player;
- o atalho `L`, que também sai da lista de atalhos (`?`).

Tocando agora então abre em **A seguir**. Um link para `&panel=lyrics` de antes de você desligar também cai ali, em vez de numa aba vazia. O player nem pede a letra de uma faixa enquanto ela está oculta.

::: info Ocultar não é apagar
Isso só muda o que o player mostra. Seus arquivos mantêm a letra que o Downtify embutiu neles, e os arquivos `.lrc` ao lado continuam no lugar, então servidores de mídia e outros players ainda os veem. Os downloads também continuam buscando letras — essa é a configuração separada **Baixar letras** em **Tags e letras** (veja [Letras](lyrics.md)).
:::

Como o tema e o equalizador, a escolha fica salva no navegador (`localStorage`), então vale por dispositivo e por navegador, não por servidor Downtify — você pode ocultar a letra no celular e mantê-la no computador.

## Equalizador

Um equalizador gráfico de dez bandas, no painel **Equalizador** de Tocando agora (ou pressione `E`). Está marcado como **Experimental**: ainda pode mudar e pode se comportar mal em alguns navegadores (veja [Suporte de navegadores](#browser-support)).

- **Bandas** em 31, 62, 125, 250, 500 Hz e 1, 2, 4, 8, 16 kHz, cada uma ±12 dB em passos de 0,5 dB. As bandas de 31 Hz e 16 kHz são shelves, então também elevam ou cortam tudo abaixo / acima delas. Arraste uma banda, ou foque nela e use as setas (`Page Up`/`Page Down` para 1 dB, `Home`/`End` para os limites); clique duplo a zera para 0.
- **Predefinições** — Plano, Reforço de graves, Reforço de agudos, Vocal, Rock, Eletrônica e Acústico. Mover qualquer banda depois transforma a predefinição em **Personalizado**.
- **Pré-amplificador** — ±12 dB por cima de tudo.
- **Interruptor de ligar/desligar** e **Redefinir** (volta para Plano, pré-amplificador 0, desligado). Mover uma banda ou escolher uma predefinição também liga o equalizador.
- A curva atrás dos controles é a resposta combinada de todas as bandas.

Reforçar bandas empurraria música alta além do fundo de escala e a distorceria, então o Downtify reduz o volume automaticamente pelo maior reforço da curva — o painel diz quanto. Isso mantém o pico em 0 dB, de modo que uma predefinição reforçada remodela o som em vez de só deixá-lo mais alto. Subir o pré-amplificador acima de 0 dB tira essa margem de segurança, e o painel avisa que passagens altas podem distorcer.

As configurações ficam salvas no navegador (`localStorage`) e valem para tudo o que você toca, em todas as abas, até você mudá-las. Valem por navegador, não por servidor Downtify.

### Suporte de navegadores

O equalizador usa a Web Audio API, disponível em todos os navegadores atuais. Até você ligá-lo, a reprodução nem toca no Web Audio. Depois de ligado, o áudio do resto da visita passa por ele — desligar só achata todas as bandas.

::: warning Safari no iPhone e no iPad
O iOS pode pausar o Web Audio quando a tela bloqueia ou você troca de app, o que interrompe a reprodução com o equalizador ligado. Se você ouve com a tela apagada, desligue o equalizador e recarregue a página.
:::

## Montando a fila

Tocar um álbum, artista, playlist ou a lista de faixas enfileira essas faixas em ordem, a partir da que você escolheu. **Aleatório** em uma coleção a inicia em ordem aleatória. Faixas que você não baixou tocam por inteiro direto na fila, servidas do cache de streaming do servidor: enquanto uma toca, a próxima já está sendo preparada com uma faixa de antecedência, então a reprodução atravessa linhas não baixadas sem parar — mesmo onde o próprio navegador não alcança o YouTube. Uma faixa transmitida nunca é salva, curtida nem lembrada entre recarregamentos.

O menu de cada faixa (o botão **⋯**, ou clique com o botão direito no computador) tem:

- **Tocar a seguir** — insere logo depois da faixa atual
- **Adicionar à fila** — acrescenta ao final
- **Ir para o álbum** / **Ir para o artista**
- **Salvar neste dispositivo** — baixa o arquivo pelo navegador
- **Excluir da biblioteca**

As mesmas ações valem para uma seleção de várias faixas na Biblioteca.

A fila, a faixa atual, a posição, o aleatório e a repetição são lembrados, então reabrir o Downtify retoma de onde você parou (filas com mais de 2000 faixas não são lembradas). Arquivos excluídos saem da fila automaticamente.

## Teclado e teclas de mídia

| Tecla | Ação |
|-----|--------|
| `Space` | Play / pause |
| `←` / `→` | Avançar/voltar 5 segundos |
| `Shift` + `←` / `→` | Faixa anterior / próxima |
| `↑` / `↓` | Volume |
| `M` | Mudo |
| `S` | Aleatório |
| `R` | Repetir |
| `L` | Abrir a letra (a menos que esteja [oculta](#hiding-the-lyrics)) |
| `Q` | Abrir a seguir |
| `E` | Abrir o equalizador |
| `Ctrl` / `⌘` + `K` ou `/` | Pesquisar |
| `Ctrl` / `⌘` + `F` | Buscar na playlist (na página de uma playlist) |
| `G` e depois `L` / `D` | Ir para a biblioteca / fila |
| `Esc` | Fechar Tocando agora |
| `?` | Mostrar todos os atalhos |

Os atalhos são ignorados enquanto você digita em um campo ou há uma janela aberta.

O player também informa a faixa atual ao sistema operacional (Media Session), então os controles da tela de bloqueio, os botões de fones e as teclas de mídia do teclado funcionam, com a capa exibida onde o sistema oferece suporte.

## Como funciona

As faixas vêm da listagem da biblioteca (`GET /tracks`), que lê título, artista, álbum, número da faixa, ano e duração das tags de cada arquivo. Os arquivos são servidos da montagem estática `/downloads`; downloads do slskd [deixados no lugar](slskd-navidrome.md#leave-files-in-place) são tocados por `/media/slskd/…`. A capa vem de `/cover` e a letra de `/lyrics` — veja a [referência da API](../api-reference.md#file-management).

A reprodução usa o áudio HTML5 nativo do navegador. Sem plugins, sem processos extras.

## Formatos compatíveis

O player toca qualquer formato que o mecanismo de áudio HTML5 do seu navegador suporte. Isso normalmente inclui MP3, M4A/AAC, OGG e OPUS em todos os navegadores modernos. O suporte a FLAC varia — Chrome e Edge o suportam nativamente; Firefox e Safari talvez não.
