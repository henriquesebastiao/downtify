---
icon: lucide/sparkles
---

# Similares

**Similares** encontra faixas com som parecido com a que você informar, a partir do mix de rádio do próprio YouTube Music — o que o YouTube toca depois da sua faixa. Sem chave de API, sem configuração.

## Como usar

Abra **Similares** na barra lateral (abaixo de **Paradas de sucesso**, ou na folha **Mais** no celular). Digite o **Artista** ou a **Faixa** (basta um dos dois — só o artista parte do seu maior sucesso) e clique em **Buscar similares**:

Você também não precisa digitar: toda linha de faixa no app tem um botão **Similares** (o ícone de varinha ao lado do botão de baixar, preenchido como ele em Busca, Paradas de sucesso e Descobrir — em Músicas mais tocadas e em links colados é um ícone discreto, e um item do menu de contexto nas faixas da Biblioteca, de Álbuns, de Artistas e de Playlists). Ele abre esta página já buscando por aquela faixa. Os resultados também tocam por inteiro direto da linha, sem baixar nada.

- **Tocar por inteiro** — toque na capa e a faixa é transmitida deste servidor direto para o player integrado, baixada ou não.
- **Baixar** — cada linha já traz o seu vídeo e baixa na hora: o Downtify coloca o resultado na fila pelo mesmo [pipeline de correspondência](../how-it-works.md) que todos os outros downloads usam. Daí em diante a linha mostra o progresso desse download e, quando a música estiver na sua biblioteca, um visto.
- **Lista sem fim** — rolar até o fim carrega a próxima página a partir do mix da última faixa, e a reprodução além da última linha continua aumentando a fila do mesmo jeito, sem fim.

## API

Veja [`GET /api/similar/tracks`](../api-reference.md#get-apisimilartracks) na Referência da API.
