---
icon: lucide/import
---

# Importar biblioteca (CSV)

Já exportou sua biblioteca de outro serviço? Importe o CSV e coloque todas as faixas na fila de download de uma vez, em vez de adicionar as músicas uma a uma.

## Exportadores compatíveis

| Ferramenta | Observações |
|------|-------|
| [Soundiiz](https://soundiiz.com/) | |
| [TuneMyMusic](https://www.tunemymusic.com/) | |
| [Exportify](https://github.com/watsonbox/exportify) | |

O Downtify não fixa o esquema exato de colunas de nenhuma ferramenta. Em vez disso, compara a linha de cabeçalho do CSV, sem diferenciar maiúsculas de minúsculas, com um conjunto de apelidos conhecidos (`Title` / `Track` / `Track Title` / `Track Name` / `Song` / …, `Artist` / `Artists` / `Artist Name` / `Artist Name(s)` / … e `Album` / `Album Name` / `Album Title` / …), então exportações de qualquer uma das três — ou de um CSV feito à mão com os mesmos nomes de coluna — funcionam sem renomear nada.

Título e artista são obrigatórios. O álbum é lido quando existe e guardado como o nome do álbum da faixa (Fila, correspondência e tags do arquivo). Outras colunas que alguns exportadores incluem (ISRC, URI de faixa do Spotify, duração) são ignoradas. Cada linha é resolvida do mesmo jeito que uma busca por texto, pelo YouTube Music.

## Como importar

1. Na página inicial, clique em **Importe um CSV (Soundiiz, Exportify…)**, abaixo da caixa de busca.
2. Escolha o arquivo `.csv` exportado.

O arquivo é lido inteiramente no seu navegador e enviado ao servidor como texto simples — nunca é enviado a nenhum outro lugar. O Downtify o interpreta, coloca na fila todas as linhas reconhecidas e você cai na Fila de downloads, onde o progresso chega por WebSocket exatamente como em qualquer outro download em lote.

O lote importado recebe o nome do arquivo (o nome sem `.csv`) e, como qualquer outro download de playlist, ganha um [arquivo M3U](m3u-export.md) se essa configuração estiver ativada.

## Limites e tratamento de erros

- Até **2.000 linhas** por arquivo. Divida exportações maiores em vários arquivos.
- Linhas sem título ou artista são ignoradas em silêncio. Uma coluna de álbum ausente ou uma célula de álbum em branco não é problema — o YouTube Music ainda pode preencher o álbum depois.
- Vários artistas em uma célula (separados por `,` ou `;`) são separados em uma lista.
- Se o cabeçalho não tiver uma coluna reconhecível de título/artista, a importação inteira é recusada logo de início, com um erro que cita as colunas encontradas — nada é colocado na fila.

## Evitando limites de requisições

Importar uma biblioteca grande coloca na fila muitas buscas e downloads do YouTube Music em pouco tempo, o que facilita ser limitado. Antes de importar um arquivo grande, considere reduzir **[Downloads simultâneos](download-settings.md#parallel-downloads)** e ativar **[Pausa entre downloads](download-settings.md#delay-between-downloads)** nas Configurações.

## API

Veja [`POST /api/download/csv`](../api-reference.md#post-apidownloadcsv) na referência da API para o endpoint subjacente.
