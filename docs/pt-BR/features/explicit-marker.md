---
icon: lucide/shield-alert
---

# Marca de conteúdo explícito

Uma música com letra explícita — linguagem que não é para crianças — traz um pequeno **E** ao lado do título, como no Spotify. Ele aparece em todo lugar onde você encontra a música, antes e depois de baixá-la, e acompanha o arquivo.

## Onde você vê

- **Resultados de busca, links colados, Paradas de sucesso e o Localizador** — em qualquer música que o serviço diga ser explícita. Você sabe antes de baixar.
- **A Biblioteca** — na aba Faixas, nas páginas de álbum, artista e playlist, e no seletor de "adicionar músicas".
- **O player** — ao lado do título na barra do player, em **Tocando agora** e em **A seguir**.

Passe o mouse sobre o **E** (ou deixe que um leitor de tela o leia) para ver "Explícito".

## De onde vem a marca

Quem decide é o serviço de onde você baixa: Spotify, YouTube Music e Deezer sinalizam, cada um, suas músicas explícitas, e o Downtify usa o que o serviço escolhido informa. Quando o Downtify baixa uma música do YouTube Music, a marca descreve o **vídeo que ele de fato baixa**: se a música é explícita no Spotify mas o Downtify casou com uma edição limpa, o arquivo não é marcado, e se o Spotify diz que é limpa mas a correspondência é explícita, ele é marcado.

Uma música que o serviço não sinaliza fica sem marca alguma — o que não é o mesmo que ser certificada como limpa, e o Downtify nunca grava uma marca de "limpa".

## No arquivo

A marca é gravada nas tags do arquivo, do jeito que o iTunes faz, para que servidores de mídia e players que a entendem também possam usá-la. O Navidrome lê exatamente essas tags como o status explícito de uma faixa.

| Formato | Tag |
|--------|-----|
| MP3 | Quadro de texto `ITUNESADVISORY` (`TXXX`), valor `1` |
| FLAC, OGG, OPUS | Comentário `ITUNESADVISORY`, valor `1` |
| M4A | Átomo `rtng`, valor `1` |

Arquivos que você já tinha são lidos do mesmo jeito: tudo o que o iTunes, o MusicBrainz Picard ou outro editor de tags marcou com `1` (ou o antigo `4`) também mostra o **E**, inclusive músicas de [pastas extras](external-library.md).

::: info Músicas baixadas antes desta versão
Arquivos que o Downtify gravou antes de a marca existir não têm nada nas tags, então não mostram o **E**, mesmo que a música seja explícita. Baixe a música de novo com [Substituir áudio](replace-audio.md) ou do zero para marcá-la. Um arquivo mantém a marca quando [Melhorar a biblioteca](library-upgrade.md) ou Substituir áudio o regrava: a marca só é adicionada, nunca removida.
:::

Na primeira vez que a Biblioteca carrega depois da atualização, o Downtify lê de novo as tags de todos os arquivos para procurar a marca, como fez quando aprendeu a mostrar codec e gênero. Em uma biblioteca grande num disco lento isso leva um momento, uma única vez.

## Para quem desenvolve apps

O [contrato do cliente móvel](../mobile-client-contract.md) e a [referência da API](../api-reference.md#get-tracks) descrevem o campo `explicit`: `true` nas faixas explícitas, ausente nas demais.
