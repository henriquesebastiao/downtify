---
icon: lucide/compass
---

# Descobrir

Artistas que você ainda não tem, sugeridos a partir dos que você tem. Abra **Descobrir** na barra lateral (no celular: **Mais → Descobrir**). A caixa de pesquisa no topo é o [Finder](finder.md), uma pesquisa só no Deezer: pesquisar mostra os resultados no lugar das sugestões, e limpar a caixa traz as sugestões de volta.

Não precisa de conta nem de chave de API: as sugestões vêm da lista pública de "artistas semelhantes" do [Deezer](https://www.deezer.com/), que funciona sem login.

## Como as sugestões são escolhidas

1. **Seus artistas são ponderados.** Cada artista da sua biblioteca conta um pouco, e conta mais por cada um destes itens, do mais para o menos importante:
    - quantas vezes você **ouve** o artista no player do Downtify (o que você ouviu recentemente pesa mais do que o de meses atrás),
    - quantas músicas dele você **curtiu**,
    - quantas músicas dele estão **na sua biblioteca**.

    O peso se achata conforme cresce, então um artista com 400 músicas de discografia não abafa um que você toca todo dia.
2. **Os 15 primeiros são consultados no Deezer**, que devolve, para cada um, os artistas que os ouvintes dele também curtem.
3. **Cada artista sugerido ganha pontos** de cada artista seu que o sugere — mais de um artista de maior peso, e mais quanto mais alto ele aparece na lista do Deezer. Um artista para o qual vários dos seus favoritos apontam fica acima de um que só um deles menciona. Sob cada sugestão, *Porque você curte …* nomeia os artistas de onde ela veio.

Artistas que já estão na sua biblioteca e artistas que você [ocultou](#hiding-artists) nunca são sugeridos.

Clique na foto de uma sugestão para abrir o artista nas colunas do [Finder](finder.md) — perfil, discografia inteira e as faixas de qualquer álbum, tudo do Deezer. O menu **⋯** de uma sugestão também tem **Encontrar músicas** (as músicas do artista, mostradas como uma pesquisa do [Finder](finder.md)), **Abrir no Deezer** e **Não tenho interesse**. A página mostra os 12 melhores artistas; **Mostrar tudo** lista todas as sugestões (até 48).

## Álbuns e playlists

Abaixo dos artistas, construídos a partir deles:

| Seção | O que contém |
|---------|--------------|
| **Álbuns para você** | O álbum mais conhecido de cada um dos 12 principais artistas sugeridos |
| **Mais dos seus artistas** | Até dois álbuns populares de cada um dos seus 6 artistas de maior peso que ainda não estão na sua biblioteca |
| **Playlists para você** | O essencial de cada artista sugerido: a playlist **`100% <artista>`** do próprio Deezer (escolhida pelos editores do Deezer) e depois a **`This Is <artista>`** do próprio Spotify |

Elas vêm em duas etapas:

1. **Primeiro o Deezer.** A discografia de cada artista é lida no Deezer: um álbum completo vem antes de um single ou EP e, entre eles, o que tem mais fãs. Essa resposta é rápida e enche as prateleiras.
2. **Depois o Spotify.** Alguns segundos depois, as escolhas do próprio Spotify para os mesmos artistas (da busca dele) são acrescentadas **no fim** de cada prateleira — espaços reservados mostram onde elas vão aparecer enquanto carregam, e nada que já está na página se move. Um álbum escolhido pelos dois serviços aparece uma vez. Cada álbum do Spotify é procurado no Deezer por artista e título; quando o Deezer o tem, ele abre no Finder como os demais.

Um pequeno ícone no canto inferior esquerdo da capa de cada álbum e playlist diz de qual serviço ela vem:

- **Deezer** — um álbum abre nas colunas do [Finder](finder.md), com as faixas prontas para tocar por inteiro e baixar.
- **Spotify** — o Deezer não tem esse álbum, então ele abre a mesma página que um link do Spotify colado.

As playlists — tanto as do Deezer quanto as do Spotify — sempre abrem essa página, onde você pode **ouvir as músicas por inteiro** antes de baixar qualquer uma (veja [Ouvir músicas antes de baixar](top-songs.md#playing-songs-before-downloading)) e depois baixar tudo, só as músicas novas ou uma seleção.

Tudo fica guardado por uma semana, como os artistas semelhantes, e a correspondência de um álbum do Spotify no Deezer por um mês (uma semana quando o Deezer não o tinha, caso seja adicionado). Um álbum que já está na sua biblioteca (comparado por artista e título, então `Dummy (Deluxe Edition)` conta como `Dummy`) e uma playlist que você já baixou ficam de fora; ocultar um artista também tira os álbuns e playlists dele.

## O que conta como uma audição

Uma música conta uma vez por reprodução, depois que **metade dela** (ou **quatro minutos**, nas músicas longas) foi realmente tocada — pular para o meio não conta, e músicas com menos de 30 segundos nunca contam. Episódios de podcast não contam.

As audições ficam guardadas no servidor, então o que você toca no celular também molda as sugestões no computador. Para recomeçar, abra **Artistas ocultos → Limpar histórico de audição**; sua biblioteca e as músicas curtidas continuam como estão.

## Ocultando artistas

**⋯ → Não tenho interesse** em uma sugestão oculta esse artista do Descobrir para sempre (o aviso que aparece tem um **Desfazer**). Para ocultar um artista antes de ele ser sugerido — um de que você simplesmente não quer ouvir falar — abra **Artistas ocultos** e digite o nome.

A mesma lista mostra todos os artistas ocultos, com **Mostrar de novo** para recuperar um. Os nomes são comparados sem diferenciar maiúsculas de minúsculas e ignorando os caracteres que um nome de arquivo não aceita, então ocultar `AC/DC` também oculta `ACDC`.

## Bom saber

- **As sugestões ficam em cache por uma semana.** As respostas do Deezer e do Spotify para cada um dos seus artistas ficam guardadas por 7 dias, então abrir o Descobrir de novo é instantâneo e não gera uma rodada de requisições. **Atualizar** reclassifica com a sua biblioteca, curtidas e audições mais recentes; um artista cuja semana acabou é consultado de novo.
- **Se o Deezer não puder ser alcançado** (ou limitar as requisições) para alguns dos seus artistas, a página ainda mostra o que conseguiu montar e avisa que a lista está menor que o normal — tente de novo mais tarde. Uma consulta que falhou nunca é lembrada como "sem artistas semelhantes".
- **Um artista que o Deezer não conhece** simplesmente não acrescenta nada; ele não é procurado de novo até a semana dele acabar.
- Só os *nomes* de artistas e álbuns saem do seu servidor (como pesquisas no Deezer e no Spotify). Nada sobre o que você toca é enviado a lugar nenhum.

## API

Veja [Descobrir](../api-reference.md#discover) na referência da API.
