---
icon: lucide/wand-sparkles
---

# Melhorar biblioteca

Uma biblioteca formada ao longo do tempo carrega o que cada versão do Downtify conseguia fazer quando uma faixa foi baixada: a menor capa que uma fonte oferecia, nenhuma letra, tags sem álbum ou ano. **Melhorar biblioteca** olha o que já está no disco e repara só o que está atrasado — sem baixar de novo e sem nada para resolver à mão.

Abra em **Biblioteca → Melhorar biblioteca**.

::: info Os upgrades padrão só reescrevem tags
O modo padrão reescreve **capas, letras e tags**. A [substituição por Deemix](#deemix-recording-replacement) opcional é um modo de varredura separado, desligado por padrão. Use [Substituir áudio](replace-audio.md) para escolher manualmente outra versão.
:::

## Como funciona

1. **Análise.** O Downtify lê todas as faixas da biblioteca e informa o que está atrasado, por categoria. Nada é gravado.
2. **Escolha.** Cada categoria para a qual a análise achou algo é listada com o número de faixas e um interruptor. Desmarque o que não quiser.
3. **Melhoria.** As faixas escolhidas entram numa fila que é percorrida uma por vez. Você pode pausar, retomar ou parar, e ela sobrevive a uma reinicialização.

## O que ele repara

| Categoria | O que faz | Onde procura |
|---|---|---|
| **Melhorar capas** | Substitui uma capa menor que o tamanho desejado | Spotify, Apple Music (iTunes), YouTube Music |
| **Adicionar letras faltando** | Preenche a letra das faixas que não têm, incorporada e como arquivo `.lrc` | Seus [provedores de letras](lyrics.md), na sua ordem |
| **Atualizar tags** | Preenche álbum, artista do álbum, data de lançamento e número da faixa — inclusive o álbum que downloads antigos de faixas avulsas não têm | Spotify |

Uma faixa conta como atrasada quando:

- o lado menor da capa incorporada é **menor que o tamanho desejado** (uma faixa sem capa nenhuma também conta);
- ela não tem **nem** letra incorporada **nem** um arquivo `.lrc` (ao lado do arquivo ou na pasta de letras das Configurações);
- falta **álbum**, **artista do álbum**, **ano** ou **número da faixa** nas tags.

**Atualizar tags** só funciona para faixas de que o Downtify ainda tem o ID da faixa no Spotify — as que baixou de um link do Spotify, guardadas no [índice de faixas](library-catalog.md#what-gets-stored). As outras faixas entram na fila mas voltam como _Nada a fazer_.

## Opções

### Melhorar capas menores que

`300px` · `500px` · **`600px`** · `1000px` · `1200px`

Capas deste tamanho ou maiores são deixadas em paz. O Downtify só grava uma capa **estritamente maior** que a que já está no arquivo, então rodar uma melhoria duas vezes nunca reescreve nada à toa.

De onde vêm os tamanhos:

| Fonte | Tamanho típico |
|---|---|
| **Apple Music (iTunes)** | 1200px ou mais |
| **Spotify** | até 640px |
| **YouTube Music** | até a configuração de [resolução da capa](download-settings.md), ~1200px no máximo |

É também por isso que uma biblioteca baixada antes costuma ficar presa em 300–640px: o Spotify publica as capas em tamanhos fixos, e o maior que ele oferece é 640px.

### Origem das capas

| Escolha | Comportamento |
|---|---|
| **Maior resolução disponível** (padrão) | Pergunta a todas as fontes e fica com a maior imagem |
| **Preferir o Spotify** / **Preferir o Apple Music** / **Preferir o YouTube Music** | Usa essa fonte quando ela tem qualquer coisa; as outras só servem de alternativa para quando ela não tem nada |

### Não verificar uma música de novo por

`Sempre verificar todas as músicas` · `7 dias` · **`30 dias`** · `90 dias` · `365 dias`

Depois que uma faixa foi examinada, a próxima análise a pula por esse tempo, para que uma segunda execução sobre uma biblioteca grande não pergunte às mesmas fontes sobre as mesmas faixas de novo.

A memória é guardada **por faixa e por categoria**, o que faz as execuções parciais funcionarem: reparar só as capas de 16.000 faixas não diz nada sobre alguém ter procurado as letras delas, então uma execução de letras posterior ainda considera todas. Uma análise também registra as categorias que examinou e para as quais não achou nada a fazer — olhar e não achar nada é uma verificação como qualquer outra.

O Downtify lembra, para cada faixa e categoria: quando foi verificada, a versão do Downtify que verificou e — para capas — a maior capa encontrada e de onde veio. Quais provedores de letras já foram consultados fica guardado à parte, por música e provedor (veja [Letras](lyrics.md)).

Duas coisas sempre a anulam:

- uma **versão mais nova do Downtify** reverifica tudo, já que pode associar ou marcar melhor que a anterior;
- escolher **Sempre verificar todas as músicas** ignora a memória naquela análise.

Quando uma análise não acha mais nada a fazer _porque_ tudo foi verificado recentemente, ela diz isso e se oferece para rodar de novo sem a memória, em vez de deixar você com um "nada para melhorar" sem explicação.

## Enquanto roda

O painel de progresso mostra as faixas concluídas da fila, um valor aproximado de dados (`8.4 GB of 51.3 GB`) e quantas foram melhoradas, não tinham nada a fazer ou falharam. Cada faixa mostra o que está fazendo — _Identificando_, _Procurando capa_, _Procurando letra_, _Gravando o arquivo_ — e termina com o que mudou, por exemplo `artwork 1200px (itunes)`.

**Pausar** para depois da faixa em andamento e mantém a fila. **Parar** descarta o resto; as faixas já melhoradas continuam melhoradas. Você pode sair da página — a execução continua, e qualquer outra aba aberta acompanha.

A fila fica em `/data/downtify_library.db`, então **reiniciar o Downtify (ou o contêiner) no meio da execução a retoma** de onde parou. Uma faixa que estava em andamento quando o processo morreu volta para a fila.

## Nada se perde se uma melhoria falhar

Toda gravação vai para uma cópia de trabalho ao lado do original (`<nome>.downtify-upgrade.<ext>`). A cópia precisa abrir como áudio da mesma duração antes de ser colocada no lugar; senão é descartada e o original fica intocado. Esse arquivo nunca aparece como uma faixa própria, e some assim que a faixa termina.

A **data de modificação original é mantida**, então melhorar uma biblioteca não reembaralha _Adicionados recentemente_.

### Pastas de música somente leitura

Uma melhoria reescreve tags no lugar, então faixas em um sistema de arquivos somente leitura são **puladas**, com uma explicação, antes de buscar metadados, capas ou letras. Elas continuam tocáveis e nas playlists; seus arquivos e permissões de montagem ficam inalterados. Uma faixa somente leitura pulada não é lembrada como verificada com sucesso, então pode ser considerada de novo se a pasta ficar gravável depois. Erros inesperados de permissão, espaço em disco e E/S ainda aparecem como falhas.

Isso difere do [enriquecimento de pastas existentes](external-library.md), que pode guardar capas e letras separadamente na pasta de dados do Downtify sem reescrever arquivos de áudio protegidos.

## Por que o áudio não é substituído

Melhorias comuns de tags não substituem o áudio. O modo separado abaixo exige metadados exatos da gravação e referência de publicação; versões incertas ficam para revisão manual.

## Substituição de gravações por Deemix

Depois de ativar e testar a [fonte Deemix](deemix.md), **Melhorar biblioteca** oferece dois interruptores independentes antes de analisar:

- **Use verified Deemix recordings**: analisa os downloads originais do Downtify, inclusive cópias ocultadas por uma coleção externa preferida. Associa exatamente artista, título/versão completo e álbum; rejeita resultados ambíguos do catálogo. A duração do clipe antigo não é usada para rejeitar uma gravação correta do catálogo. Verifica as tags baixadas, a duração do catálogo, a qualidade escolhida e a decodificação completa pelo FFmpeg.
- **Remove old Downtify audio after import**: além disso, remove cada original inalterado depois da publicação. Vem desligado por padrão. Manter os originais ainda atualiza playlists e favoritos para a gravação do Deemix.

Essa análise produz uma categoria de **áudio** em vez de tarefas de capa/letra/tags. O Deemix é dono dos arquivos de saída, da capa, do layout de álbuns e das letras nativas. O Downtify os lê no lugar. Letras nativas ou incorporadas existentes são preservadas; só letras ausentes podem ser complementadas numa pasta de letras dedicada e gravável, sem reescrever o áudio. Um original sem perdas de qualidade maior é mantido quando o Deemix está configurado para MP3.

A publicação acontece uma vez por lote. Comentários do M3U, marcadores manuais e a ordem das faixas são preservados; depois, caminhos do catálogo, participações em playlists, curtidas de todos os usuários, posse e regras de faixas ocultas migram em uma única transação SQLite. Os IDs do Navidrome em cache dos arquivos antigos são invalidados para uma nova busca nativa. IDs móveis já emitidos e URLs de reprodução antigas mantêm aliases somente leitura para o substituto registrado; mutações nunca usam esses aliases de URL.

Recibos duráveis no banco da biblioteca registram os valores SHA-256 de origem/destino e o estado da publicação. As fontes permanecem até o substituto e as referências serem verificados. Uma montagem alterada ou ausente, arquivo editado, referência externa somente leitura de playlist, reprodução ativa ou falha na publicação do catálogo interrompe a limpeza com um motivo visível. Pausar/retomar e reiniciar reaproveitam os recibos. Não há varredura geral de duplicatas nem limpeza por idade: só originais verificados na pasta de downloads do Downtify são elegíveis. Downloads manuais do Deemix/slskd, originais externos, diretórios e sidecars nunca são excluídos. Depois que um original é removido, reverter o contêiner não restaura esse arquivo; restaure-o do seu backup de armazenamento, se precisar.

Para consumidores de NAS cujos nomes de montagem diferem dos caminhos do Docker, um administrador pode definir `DOWNTIFY_DEEMIX_M3U_ROOT` com um alias do contêiner que resolva para a raiz do Deemix. Caminhos relativos do M3U usam esse alias (por exemplo `/Download` mapeado para `/music/existing`). O opcional `DOWNTIFY_LIBRARY_READY_MARKERS` é um objeto JSON de caminhos de marcadores e o texto esperado, verificado antes da preparação e da limpeza. Um marcador ausente falha por segurança. Nenhuma das variáveis é necessária para o modo padrão.

A API de análise aceita `replace_audio_deemix: true`, opcionalmente `delete_replaced_audio: true`, e opcionalmente `files: ["relative/original.mp3"]` para um piloto limitado. Iniciar essa análise seleciona `categories: ["audio"]`. O estado da execução inclui contagens de substituição e um `finalization_error` quando a publicação pausa. Nenhum arquivo de origem é removido só porque um item da fila do Deemix diz concluído.

### Revisando uma gravação incerta

Uma tarefa de áudio pulada ou com falha oferece **Choose a Deezer recording**. Cole o link exato de uma faixa, veja a prévia do artista, álbum e duração, e escolha **Analyze this choice**. Isso só prepara uma nova análise de uma única faixa; confirme essa análise para iniciar a substituição. O associador automático padrão nunca chuta um álbum diferente.

Essa escolha explícita pode corrigir um rótulo de álbum antigo, mas o título/versão completo e o artista ainda precisam coincidir. Um original explícito conhecido não pode virar silenciosamente uma versão limpa. A gravação escolhida passa pelas mesmas verificações de duração, qualidade, decodificação, referência e exclusão. Uma escolha diferente não pode reaproveitar silenciosamente um recibo já preparado. O payload avançado da análise registra a escolha como `deemix_recordings: {"relative/original.mp3": "123456"}`; ela é restrita àquele arquivo e salva para reinicialização/retomada.

## API

| Método | Caminho | Descrição |
|---|---|---|
| `GET` | `/api/library/upgrade` | Estado da execução, contagens da fila e o que a análise achou |
| `GET` | `/api/library/upgrade/jobs` | Linhas por faixa (`status`, `stage`, `detail`) |
| `POST` | `/api/library/upgrade/scan` | Analisa a biblioteca; não grava nada |
| `POST` | `/api/library/upgrade/start` | Inicia a execução para as `categories` escolhidas |
| `POST` | `/api/library/upgrade/pause` | Para depois da faixa atual, mantém a fila |
| `POST` | `/api/library/upgrade/resume` | Continua uma execução pausada |
| `POST` | `/api/library/upgrade/cancel` | Descarta o resto da fila |

O progresso também é enviado pelo [WebSocket](../api-reference.md#websocket) como `{"type": "library_upgrade", "upgrade": {…}}`.

Veja a [referência da API](../api-reference.md#library) para os formatos de requisição e resposta.
