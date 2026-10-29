---
icon: lucide/trending-up
---

# Paradas de sucesso

**Paradas de sucesso** mostra a parada global do próprio Deezer — sem filtro de gênero, o que está em alta no mundo todo agora — sem precisar de conta nem de chave de API do Deezer.

## Como usar

Abra **Paradas de sucesso** na barra lateral (ou na folha **Mais** no celular). Quatro abas leem a mesma parada: **Faixas**, **Álbuns**, **Artistas** e **Playlists**.

- **Faixas** — uma lista ranqueada. Pressione uma (ou toque na linha) para ouvi-la por inteiro do YouTube, direto no player integrado, antes de baixar. Baixar uma linha funciona como um resultado de busca: o Downtify procura no YouTube Music (e, se não achar, no YouTube comum) a melhor correspondência para título, artista e duração da faixa, pelo mesmo [pipeline de correspondência](../how-it-works.md) que todos os outros downloads usam. Depois que uma faixa é baixada, a linha toca a versão da sua biblioteca em vez de transmitir.
- **Álbuns**, **Artistas** e **Playlists** — grades de capas. Clicar em uma a resolve ([`GET /api/url/resolve`](../api-reference.md#get-apiurlresolve)) exatamente como se você tivesse colado aquele link do Deezer na caixa de busca: a lista de faixas é carregada, pronta para escolher e baixar.

## Por que as faixas baixam (e tocam por inteiro) direto daqui, mas álbuns, artistas e playlists abrem uma página antes

Uma faixa da parada não precisa de uma etapa de resolução para baixar: o Deezer já informa título, artista e nome do álbum, o que basta para buscar e casar no YouTube, como acontece com um resultado de busca por texto. Um álbum, artista ou playlist precisa dessa etapa — transformar o link em uma lista de faixas —, então o card abre a página já resolvida em vez de baixar direto da grade. Tocar uma linha de faixa transmite por inteiro do YouTube (nunca para álbuns, artistas ou playlists) — o mesmo streaming que toda linha de faixa usa, só que alimentado com o título e o artista da parada.

## API

Veja [`GET /api/discover/chart`](../api-reference.md#get-apidiscoverchart) na Referência da API.
