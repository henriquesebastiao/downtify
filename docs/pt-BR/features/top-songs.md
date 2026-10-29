---
icon: lucide/star
---

# Top Songs

Alguns artistas têm catálogos enormes em que só um punhado de faixas importa. Em vez de pegar links faixa por faixa, ou baixar uma playlist "This is…" de mais de 50 faixas por causa das poucas músicas que você realmente quer, cole o link do próprio artista e escolha entre as músicas mais populares dele.

## Como usar

1. Cole um link de artista na caixa de pesquisa ou na tela Início:
   - **Spotify**: `https://open.spotify.com/artist/…`
   - **YouTube Music**: `https://music.youtube.com/channel/UC…` ou `https://music.youtube.com/@handle`
   - **Deezer**: `https://www.deezer.com/artist/…`
2. A **página do artista** abre com a foto e o nome dele e lista os lançamentos (álbuns, singles, EPs e coletâneas, quando o serviço os tem), do mais novo ao mais antigo no Spotify e no Deezer; clique em um para ver as faixas ou baixá-lo. Ao lado de um botão **Top Songs**, os artistas do Spotify e do YouTube Music também têm **Monitorar novos lançamentos** — os do Deezer não, já que o [Monitor de playlists](playlist-monitor.md) não tem suporte ao Deezer.
3. **Top Songs** abre a lista das músicas mais populares dele, na ordem em que o serviço as classifica. No Spotify e no YouTube Music, um selo com um olho mostra quantas vezes cada música foi tocada, abreviado como o seu idioma faz (`1,5 bi` em português, `1.5B` em inglês) — o do Spotify é verde e o do YouTube Music é vermelho. O YouTube Music só informa um número arredondado (`1.2B plays`), então o dele é uma aproximação; o Downtify o lê da mesma requisição ao YouTube Music que lista as músicas, mais uma requisição para as contagens de reprodução. O ranking "top" do próprio Deezer não tem número público de reproduções para mostrar, então as músicas dele aparecem sem selo. As cinco primeiras já vêm marcadas; marque mais ou desmarque qualquer uma, depois pressione **Baixar selecionadas**.

### Ouvindo músicas antes de baixar

Na página Top Songs, e na página que um link de **álbum** ou **playlist** colado abre, toda música toca por inteiro: passe o mouse na linha e o número vira um botão de reproduzir (no celular o botão de reproduzir está sempre lá); pressione-o e a música é transmitida do YouTube direto para o player integrado. Pressione de novo para pausar, ou o botão de outra linha para trocar. Uma música que já está na sua biblioteca toca a partir da biblioteca, com as outras músicas baixadas da lista na fila depois dela.

O streaming sai deste servidor, nunca do navegador direto para o YouTube: a linha é resolvida para o vídeo dela no YouTube (o próprio, para uma música do YouTube Music; senão a correspondência mais próxima da busca) e o servidor baixa o áudio uma vez para o cache de streaming e depois toca o arquivo em cache (veja [`GET /api/stream/file`](../api-reference.md#get-apistreamfile)). Só o servidor precisa alcançar o YouTube, e uma faixa com restrição de idade exige cookies do YouTube (veja [Cookies do YouTube](youtube-cookies.md)) como um download.

## Fontes

| Fonte | O que "top songs" significa | Músicas listadas |
|--------|------------------------|--------------|
| Spotify | A prateleira **Popular** do próprio artista, as mesmas faixas mostradas no topo da página dele no Spotify | Até 10 |
| YouTube Music | A playlist **Top songs** do artista, classificada por popularidade | As primeiras 50 |
| Deezer | O ranking **top** do próprio artista (a mesma prateleira que o `deezer.com` mostra na página dele) | As primeiras 50 |

O embed público do Spotify não tem discografia, então o Downtify lê os lançamentos da própria consulta de discografia do web player do Spotify, a mesma API não pública que ele usa para os nomes dos álbuns. Se o Spotify a mudar, o Downtify recorre a uma lista mais curta (todos os álbuns, mas só os dez singles mais recentes) e, se isso falhar, não mostra lançamentos. As músicas do Spotify passam pelo pipeline normal de metadados e depois correspondência de áudio, com o nome do álbum anexado de antemão; o download completa o resto (número da faixa, ano) como faz com qualquer música do Spotify. As músicas do YouTube Music ficam presas ao próprio vídeo, como qualquer outro link do YouTube Music. O Deezer tem um endpoint público de discografia de verdade, então a lista de lançamentos dele não precisa de alternativa; as músicas dele passam pelo mesmo pipeline de metadados e depois correspondência de áudio que as do Spotify, com um trecho de prévia de 30 segundos anexado quando o Deezer o oferece.

## Na página do artista na Biblioteca

Um artista que o Downtify conhece no Spotify (veja [Foto, banner e biografia do artista](artist-images.md)) também ganha uma aba **Top songs** na página dele na sua Biblioteca, ao lado de Faixas e Fãs também curtem. Ela lista as primeiras **5** músicas mais populares dele no Spotify como uma lista mínima, como nos resultados de pesquisa, sob cabeçalhos de coluna (#, Título, Álbum, duração): número, capa, título, artista, álbum e duração. Uma música que não está na sua biblioteca tem um botão de **download** à direita (com o progresso enquanto baixa); depois de baixada, ele vira o rótulo **Na biblioteca**, e a música pode ser tocada como na página de um álbum: o número vira um botão de reproduzir ao passar o mouse, a capa toca, e um clique duplo ou um toque também tocam. Tocar uma enfileira as outras músicas baixadas da lista depois dela, na ordem do ranking, e a música em reprodução fica destacada. Uma música que ainda não foi baixada é **transmitida por inteiro**: passe o mouse na linha e no lugar do número aparece um botão de reproduzir; pressione-o (ou a capa) e ela toca no player integrado como uma música baixada (veja [Ouvindo músicas antes de baixar](#playing-songs-before-downloading)). Abaixo da lista, **Ver mais músicas populares** abre este artista na página Top Songs descrita acima, onde ficam a seleção, o botão **Criar playlist** e o download de várias de uma vez. A aba só aparece quando o ID do artista no Spotify é conhecido, o que acontece na primeira vez que a página dele é aberta; as músicas são pedidas nessa hora, então a contagem da aba se preenche sozinha alguns segundos depois, onde quer que você esteja na página.

Ler a capa, o álbum e a contagem de reproduções de uma música leva alguns segundos, então o Downtify guarda as cinco músicas em um arquivo por artista, `<downloads>/.metadata/ArtistTopSongs/<Artista>.topsongs.json`, criado em segundo plano na primeira vez que a página do artista é aberta. Ele é confiável por **7 dias**: abrir a aba lê o arquivo na hora e, quando ele passa dessa idade, a lista antiga é mostrada de imediato enquanto uma nova é buscada por trás — a página a troca sozinha em alguns segundos, sem atrapalhar uma música que está baixando ou tocando. O arquivo guarda só as músicas, a capa, os links dos trechos e as contagens de reproduções — nunca o áudio nem as imagens, e nunca se a música está na sua biblioteca, o que é calculado na hora. É um cache: apague quando quiser e ele é refeito.

## Criando uma playlist

O botão **Criar playlist** na página Top Songs começa **desligado** na primeira vez que você abre um artista, e começa **ligado** quando já existe na sua biblioteca uma playlist chamada **Top Songs of {artist}**, para que os downloads seguintes continuem somando a ela. Mude o botão e a sua escolha vale enquanto você estiver nessa página. Desligado, as músicas são baixadas como quaisquer outras músicas avulsas: direto para a sua pasta de downloads, ou para as suas pastas de artista/álbum quando a [Organização de arquivos](file-organization.md) está ligada, sem pasta própria, sem M3U e sem foto do artista.

Ligue e o Downtify as trata como uma playlist chamada **Top Songs of {artist}**. Onde ela vai depende da Organização de arquivos:

| Organizar por artista / álbum | Músicas | M3U e capa |
|---|---|---|
| Ambos desligados | Em uma pasta chamada `Top Songs of {artist}` | Na mesma pasta |
| Um ou ambos ligados | Arquivadas por essas configurações: `<Artista>/`, `<Álbum>/` ou `<Artista>/<Álbum>/`. Não há pasta `Top Songs of {artist}`. | Em `Playlists/`, como `Top Songs of {artist}.m3u` e `.jpg` |

Nos dois casos:

- a [playlist M3U](m3u-export.md) lista as músicas **na ordem do ranking do artista**, mesmo quando você marcou só algumas;
- a foto do artista é salva ao lado do M3U como capa dele, se **Salvar a capa da playlist** estiver ativado (veja [Capa da playlist](playlist-cover-art.md)). Não há uma configuração separada para isso.

## Limitações conhecidas

::: warning Misturando Spotify e YouTube Music para o mesmo artista
O M3U de **Top Songs of {artist}** é mantido em sincronia a partir do [catálogo de playlists](library-catalog.md), que é indexado por IDs de faixa do Spotify. Se você baixar as top songs de um artista pelo **Spotify** e depois pelo **YouTube Music** (ou o contrário), os arquivos do segundo lote são baixados corretamente, mas a próxima atualização do M3U os tira do arquivo da playlist, porque os IDs do YouTube Music não cabem nesse formato. Acrescentar mais músicas da **mesma** fonte não é afetado.
:::

::: info Nomes de álbum das músicas do Spotify
A página de artista do Spotify não diz de qual álbum uma música é. O Downtify obtém os nomes dos álbuns e as contagens de reproduções da mesma API do player do Spotify que usa para ler playlists completas: uma requisição extra por artista, mais uma para cada álbum que essa requisição não lista. Essa API não é pública, então, se o Spotify a mudar, a coluna **Álbum** fica vazia nas músicas do Spotify e o selo de contagem de reproduções some; as músicas ainda são baixadas, mas o Downtify então tem de recuperar o álbum a partir da correspondência no YouTube Music, que muitas vezes falha, deixando o arquivo sem tag de álbum e, com [Organizar por álbum](file-organization.md) ligado, numa pasta de álbum `unknown`. As top songs do YouTube Music já trazem o álbum. Se as contagens de reproduções pararem de chegar, em qualquer fonte, o selo simplesmente não aparece.
:::

## API

Veja [`GET /api/artists/top_songs/url`](../api-reference.md#get-apiartiststop_songsurl) na Referência da API.
