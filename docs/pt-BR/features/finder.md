---
icon: lucide/columns-3
---

# Finder

O **Finder** é um jeito de explorar o catálogo do Deezer antes de baixar. Você pesquisa no Deezer, abre um artista e navega por ele em três colunas lado a lado, como a visualização em colunas do Finder do macOS: o artista, a discografia dele e as faixas de um álbum. Não precisa de conta do Deezer nem de chave de API.

## Pesquisando

Abra **Descobrir** na barra lateral (no celular: **Mais → Descobrir**): a caixa de pesquisa do Finder fica no topo da página, com as suas pesquisas recentes do Finder ao lado. Pesquisar troca as sugestões do Descobrir pelo que foi encontrado — músicas, álbuns e artistas, com os filtros **Tudo / Músicas / Álbuns / Artistas** como na página de Pesquisa normal, mas só do Deezer. Limpe a caixa (o **×**) ou volte para ver as sugestões de novo; uma pesquisa recente roda outra vez com um clique, e **Limpar** esquece todas. As pesquisas recentes ficam guardadas só neste navegador.

**Encontrar músicas**, no menu **⋯** de um artista sugerido pelo Descobrir, mostra aqui as músicas dele como uma pesquisa: o Deezer é consultado pelo nome do artista, e só as músicas desse artista mesmo — identificadas pelo id dele no Deezer, então um homônimo ou uma música que apenas tenha esse nome ficam de fora — são listadas, até as primeiras centenas.

- **Músicas** tocam por inteiro em streaming e são baixadas como qualquer resultado de pesquisa. O Downtify encontra a música no YouTube Music (com o YouTube como alternativa) pelo título, artista e duração. Clicar no título de uma música abre o álbum dela na visualização em colunas, com a música em destaque.
- **Álbuns** abrem no artista, com aquele álbum selecionado. O botão de download na capa coloca o álbum inteiro na fila.
- **Artistas** abrem a visualização em colunas naquele artista.

## A visualização em colunas

| Coluna | O que mostra |
| --- | --- |
| **Artista** | A foto do artista e a quantidade de álbuns, a biografia no idioma da interface (expansível), as 10 faixas mais populares e "Fãs também curtem" (artistas relacionados). |
| **Discografia** | Todos os álbuns, singles, EPs e coletâneas, do mais recente ao mais antigo, com capa, título, tipo de lançamento, ano e número de faixas. Os filtros separam por tipo de lançamento. |
| **Faixas** | A capa e o título do álbum selecionado, o artista, o ano, o número de faixas e a duração. Um painel de informações lista a data de lançamento, a gravadora, os gêneros, os créditos e o UPC. Abaixo ficam as faixas do álbum: cada uma toca por inteiro em streaming até ser baixada e depois toca a partir da sua biblioteca, com um botão **Baixar álbum** para colocar todas na fila. |

Clicar numa faixa popular seleciona o álbum dela e destaca a faixa; as duas colunas rolam suavemente até aparecerem (na hora, se o sistema estiver configurado para reduzir movimento), e quando as faixas do álbum estão na tela a faixa começa a tocar por inteiro — em streaming, ou a própria música, se já estiver na sua biblioteca. Clicar nela de novo enquanto toca não a pausa; abrir a página por um link que aponta para uma faixa não inicia nada. Clicar num artista relacionado abre esse artista, e o botão de voltar do navegador retorna ao anterior. A barra de caminho acima das colunas (**Descobrir › artista › álbum**) leva de volta à pesquisa (ou ao Descobrir, quando as colunas não foram abertas a partir de uma) ou só ao artista. O que está aberto fica salvo na URL, então sobrevive a um recarregamento e pode ser guardado nos favoritos.

Em telas largas, arraste a borda entre duas colunas para deixar uma mais larga ou mais estreita, ou foque nela e use as setas do teclado. Um clique duplo restaura as larguras padrão. O botão de seta no topo das colunas de artista e de discografia recolhe a coluna só nas imagens: a foto do artista, as capas das faixas populares e as fotos dos artistas relacionados, ou as capas dos álbuns. Cada imagem continua funcionando como a linha completa, e o nome aparece ao passar o mouse. As larguras e as colunas recolhidas só duram enquanto você está na página: nunca são salvas, então recarregar ou sair do Finder as restaura.

No celular, as colunas ficam lado a lado e você desliza entre elas. Escolher um álbum leva direto às faixas dele.

::: info Por que o número de faixas aparece um instante depois
A listagem da discografia do Deezer não traz o número de faixas, então o Downtify consulta a quantidade de cada álbum separadamente, alguns álbuns por vez, ficando abaixo do limite do Deezer de 50 requisições a cada 5 segundos. Os números aparecem enquanto você olha e são lembrados até o Downtify reiniciar. Um álbum cuja quantidade não pôde ser obtida mostra `…`.
:::

## API

Veja [`GET /api/finder/search`](../api-reference.md#get-apifindersearch) e os endpoints seguintes na Referência da API.
