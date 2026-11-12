---
icon: lucide/cog
---

# Como funciona

O pipeline de download do Downtify tem três etapas:

```
Spotify embed  →  YouTube Music search  →  yt-dlp + ffmpeg + mutagen
  (metadata)         (audio match)          (download & tag)
```

## 1. Metadados — extração da página de incorporação do Spotify

Quando você cola uma URL do Spotify, o Downtify busca a página pública `open.spotify.com/embed` daquela faixa, álbum ou playlist. Não é preciso conta no Spotify, chave de API nem assinatura Premium — a página de incorporação é de acesso público.

Para **faixas**, a página devolve: título, artista(s), nome do álbum, ano de lançamento, duração e a URL da capa.

Para **álbuns e playlists**, ela devolve a lista de faixas. As playlists incorporadas são limitadas a cerca de 50–100 entradas, então o Downtify também pede a lista completa ao endpoint anônimo `api.spotify.com` do Spotify, com paginação, para lidar com playlists de centenas de músicas.

::: info Enriquecimento de metadados por faixa
As entradas de playlist na incorporação não trazem o ano de lançamento e usam a capa da playlist em vez da capa do álbum de cada faixa. Para o [Monitor de playlists](features/playlist-monitor.md), o Downtify busca de novo cada faixa nova individualmente para obter a capa e o ano corretos antes de baixar.
:::

## 2. Correspondência de áudio — YouTube Music e depois YouTube

O Downtify usa o [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) para buscar no YouTube Music a melhor correspondência de áudio. A consulta é montada com o título da faixa e o nome do artista.

Um resultado só é aceito se o título se parecer com o original e se compartilhar ao menos um artista. O sufixo de versão do Spotify com hífen e o do YouTube Music entre parênteses são tratados como iguais (`Tubarões - Ao Vivo` corresponde a `Tubarões (Ao Vivo)`), e um crédito de artistas que o YouTube Music reúne em uma só entrada (`A, B, and C`) é separado antes da comparação. Um "The" inicial nos nomes de artistas é ignorado (`Eden Project` corresponde a `The Eden Project`), e um título pode corresponder a uma parte do título do upload separada por ` - ` (`くちづけDiamond - Kuchizuke Diamond`, `Game OST - Song Title - Artist`), desde que as outras partes não indiquem uma versão diferente. Versões de karaokê, cover, instrumental, acelerada/desacelerada, ao vivo (incluindo `Ao Vivo`/`En Vivo`), acústica, remix e em outro idioma (por exemplo `(Spanish Version)`) são rejeitadas, a menos que a própria faixa de origem seja essa versão. Entre os resultados restantes, vence aquele cuja duração é mais próxima da do Spotify, com bônus para um nome de álbum correspondente. Se nenhum resultado se qualifica, a busca é repetida com as palavras na outra ordem (`<título> <artista>` em vez de `<artista> <título>`) — o YouTube Music ordena os resultados de forma diferente conforme a ordem das palavras, e algumas músicas só aparecem perto do topo de um jeito. Se isso também não achar nada e o álbum for conhecido, a lista de faixas do álbum é examinada diretamente.

### Alternativa: YouTube comum

Algumas músicas não estão no YouTube Music, ou só existem lá como outra gravação. Por isso o YouTube comum também é pesquisado quando:

- o YouTube Music **não tem nenhuma correspondência aceitável**, ou
- a duração da melhor correspondência dele difere **mais de 10 segundos** da do Spotify — um forte indício de que é outra gravação (por exemplo, uma versão dublada com o mesmo título).

Os resultados do YouTube comum passam pelas mesmas verificações de título, artista e versão, e nunca são aceitos com mais de 30 segundos de diferença da duração do Spotify. Um resultado do YouTube só substitui uma correspondência fraca do YouTube Music quando sua duração é estritamente mais próxima; caso contrário, a correspondência do YouTube Music é mantida, já que seus uploads de catálogo costumam ter o áudio mais limpo.

Se nenhum dos dois sites tem uma correspondência aceitável, a faixa falha com `Could not find a YouTube match for '<title>'` em vez de baixar a música errada.

Para URLs do YouTube digitadas diretamente, essa etapa é pulada — o Downtify baixa aquele vídeo específico.

::: info Links do Deezer
Um link de faixa/álbum/playlist/artista do Deezer colado (`deezer.com/track/…`) funciona como um do Spotify: a API REST pública do Deezer fornece título, artista(s), álbum e capa, cada faixa é transmitida por inteiro do YouTube antes de você baixar, e essa mesma etapa a casa no YouTube Music/YouTube. O Downtify não tem um resolvedor de discografia do Deezer próprio além do que a API do Deezer já devolve, então um link do Deezer baixa e (no caso de playlist) ganha seu próprio M3U e capa, mas não pode ser acompanhado pelo [Monitor de playlists](features/playlist-monitor.md).
:::

## 3. Download e tags — yt-dlp + ffmpeg + mutagen

### Download

O [yt-dlp](https://github.com/yt-dlp/yt-dlp) baixa o áudio do YouTube. O Downtify o configura para tentar vários clientes de player em ordem (`ios`, `android`, `web_embedded`, `mweb`, `web`, `tv`) para contornar os desafios de detecção de bots do YouTube. Veja [Variáveis de ambiente](getting-started/environment-variables.md) para opções anti-bot avançadas.

### Conversão

O [ffmpeg](https://ffmpeg.org/) converte o áudio bruto para o formato escolhido (MP3, FLAC, M4A, OGG ou OPUS) na taxa de bits escolhida.

### Etiquetagem

O [mutagen](https://mutagen.readthedocs.io/) grava os metadados no arquivo convertido:

| Tag | Gravada |
|-----|---------|
| Título | Sim |
| Artista(s) | Sim, todos os artistas creditados, e também um por valor numa tag `ARTISTS` |
| Artista do álbum | Sim, o artista do próprio álbum como a fonte o credita, senão o primeiro artista |
| Marca de coletânea | Só num álbum que a fonte credita a "Various Artists", ou que um admin marca como tal |
| Álbum | Sim |
| Ano | Sim |
| Capa do álbum (JPEG) | Sim |
| Letras (simples + sincronizadas) | Sim, se o lrclib devolver um resultado |
| Marca de explícito | Sim, quando a música é sinalizada como explícita (veja [Marca de conteúdo explícito](features/explicit-marker.md)) |

As tags ID3/Vorbis/MP4 exatas dependem do formato de saída. Veja [Letras](features/lyrics.md) para detalhes sobre como as letras são incorporadas.

## Progresso em tempo real

O Downtify transmite o progresso dos downloads ao navegador por uma conexão **WebSocket** (`/api/ws`). Conforme o yt-dlp informa o progresso, o servidor envia atualizações de porcentagem e de status a todos os clientes conectados. Assim você vê a barra de progresso andar em tempo real — sem polling, sem recarregar a página.

## Nomes de arquivo e organização

O nome do arquivo de saída é montado a partir do modelo configurado nas Configurações (padrão: `{artists} - {title}`). Caracteres inválidos em nomes de arquivo são removidos.

Quando *Organizar por artista* está ativado, o arquivo vai para uma subpasta com o nome do artista do álbum — ou, numa faixa de uma coletânea de vários artistas, do seu primeiro artista. Caso contrário, faixas avulsas vão para a raiz do diretório de downloads e as faixas de playlists/álbuns vão para uma subpasta por playlist ou álbum. Veja [Vários artistas e coletâneas](features/file-organization.md#several-artists-and-compilations).
