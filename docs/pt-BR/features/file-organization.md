---
icon: lucide/file-headphone
---

# Organização de arquivos

Um servidor novo organiza os arquivos por artista e álbum (`Artista/Álbum/…`): **Organizar por artista** e **Organizar por álbum** vêm ativados por padrão. Desative-os para obter o formato plano abaixo. Servidores configurados antes desse padrão mantêm a escolha que tinham.

## Formato plano (ambos desativados)

Faixas avulsas e buscas do YouTube vão direto para a raiz da pasta de downloads. As faixas de playlists e álbuns vão para uma subpasta por playlist ou por álbum:

```
downloads/
├── My Playlist/
│   ├── My Playlist.m3u
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── Tame Impala - The Less I Know The Better.mp3
└── The Night Owls - R U Awake.mp3       ← faixa avulsa
```

## Organizar por artista

Com **Configurações → Downloads e arquivos → Organizar por artista** ativado (o padrão), todas as faixas — inclusive os downloads de playlists e álbuns — são agrupadas em uma subpasta com o nome do artista do álbum (veja [Vários artistas e coletâneas](#several-artists-and-compilations)):

```
downloads/
├── The Night Owls/
│   ├── The Night Owls - Do I Still Recall.mp3
│   └── The Night Owls - R U Awake.mp3
├── Tame Impala/
│   └── Tame Impala - The Less I Know The Better.mp3
└── Playlists/
    └── My Playlist.m3u
```

Essa estrutura é compatível com servidores de mídia (Jellyfin, Navidrome, Plex) e gerenciadores de biblioteca (Beets) que esperam uma organização de pastas `Artista/Música.ext`.

## Vários artistas e coletâneas

Uma música costuma creditar vários artistas. O Downtify guarda todos na tag **Artista** do arquivo e também grava cada um separadamente numa tag **ARTISTS** (`TXXX:ARTISTS` no MP3), para que um player nunca precise dividir um nome como `Earth, Wind & Fire` na vírgula. A pasta, porém, pertence a um único artista: o **artista do álbum**, ou, numa coletânea, o primeiro artista da faixa.

- O artista do álbum é o artista que a fonte (Spotify, YouTube Music ou Deezer) credita para o **álbum**, o mesmo em todas as faixas, e é gravado na tag **Artista do álbum**. Quando a fonte não diz, é o primeiro artista da faixa.
- Uma dupla ou um grupo é um artista só. O YouTube Music credita alguns artistas pelos seus integrantes, um por entrada (`Henrique & Juliano` volta como `Henrique` e `Juliano`, no álbum e em cada faixa — às vezes na ordem inversa, `Mateus` e `Jorge` para `Jorge & Mateus`). Cada nome creditado aponta para um canal do YouTube Music; quando o link de um integrante leva a um canal com o nome do grupo inteiro, formado pelos nomes creditados ao lado dele, o Downtify junta esses nomes de volta no nome do grupo: a pasta e as tags **Artista do álbum**, **Artista** e **ARTISTS** dizem `Henrique & Juliano`. Uma colaboração de verdade (cada artista no próprio canal) mantém todos os artistas. Quando o YouTube Music não liga nenhum integrante ao canal do grupo, os nomes continuam separados; mesmo assim, a Biblioteca não dá página a um nome que só aparece creditado ao lado de outro (veja [Catálogo da biblioteca](library-catalog.md#library-page)).
- Um convidado nunca muda isso. *The Girl Is Mine*, com um convidado no *Thriller* de Michael Jackson, fica em `Michael Jackson/Thriller/`, e o single *Lady Marmalade* (Christina Aguilera, Lil' Kim, Mýa, P!nk) vai para `Christina Aguilera/`.
- Só um álbum que a própria fonte credita a **Various Artists** (uma trilha sonora, um "Now That's What I Call…") é uma coletânea — a menos que você [o marque](#marking-an-album-as-various-artists). Uma música avulsa do YouTube Music nunca é: o YouTube Music arquiva o mesmo áudio em vários lançamentos e pode mostrar qualquer um deles como álbum, muitas vezes uma coletânea, então só o download de um álbum inteiro do YouTube Music conta. As faixas dela recebem "Various Artists" como artista do álbum mais a marca de coletânea (`TCMP` no MP3, `COMPILATION` em FLAC/Ogg/Opus, `cpil` no M4A). Isso mantém o álbum inteiro no Navidrome e em outros servidores de mídia, que agrupam álbuns por essas tags e não por pasta. No disco, porém, **Organizar por artista** nunca cria uma pasta `Various Artists`: cada faixa vai para a pasta do seu primeiro artista.
- Versões antigas do Downtify gravavam **Various Artists** em qualquer música com vários artistas, sem a marca de coletânea. A Biblioteca continua listando essa música no álbum do seu primeiro artista, como antes; **Marcar como Artistas Diversos** transforma o álbum numa coletânea de verdade.

```
downloads/
├── Christina Aguilera/
│   ├── Lady Marmalade/
│   │   └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
│   └── Moulin Rouge/                  ← da trilha sonora (uma coletânea)
│       └── Christina Aguilera, Lil' Kim, Mýa, P!nk - Lady Marmalade.mp3
└── David Bowie/
    └── Moulin Rouge/                  ← mesma trilha sonora
        └── David Bowie - Nature Boy.mp3
```

*Lady Marmalade* do single e da trilha sonora de *Moulin Rouge* são dois lançamentos, cada um arquivado com o próprio álbum. As faixas da trilha sonora ficam espalhadas pelas pastas dos seus artistas, mas marcadas como uma coletânea "Various Artists", então a Biblioteca e os servidores de mídia ainda mostram *Moulin Rouge* como um álbum só.

### Marcar um álbum como Artistas Diversos

Uma fonte pode creditar um lançamento a um artista quando ele pertence a vários por igual — o Deezer lista o single *Lady Marmalade* só sob Christina Aguilera. Um admin corrige isso na página do álbum na Biblioteca, com o botão **Marcar como Artistas Diversos** ao lado de **Adicionar à fila**.

- Cada faixa do álbum recebe "Various Artists" como artista do álbum e a marca de coletânea. Nada mais nos arquivos muda, e eles ficam onde estão (as faixas de uma coletânea já ficam na pasta do seu primeiro artista). Cada arquivo é reescrito por meio de uma cópia de trabalho, mantém a data de modificação e fica intacto se a reescrita falhar.
- Na Biblioteca, o álbum passa a aparecer por **Various Artists** em **Álbuns** (cada faixa continua na página do seu artista), e a página do álbum o acompanha.
- O Downtify lembra do álbum: uma faixa dele baixada depois recebe as mesmas tags.
- Numa coletânea, o mesmo botão diz **Desmarcar como Artistas Diversos**: desfaz a marca e devolve o artista do álbum que ele tinha. Também funciona num álbum que a fonte transformou em coletânea; aí o artista do álbum passa a ser o artista que a maioria das faixas lista primeiro, e downloads posteriores desse álbum não são marcados de novo.

Só admins veem o botão. Os servidores de mídia pegam a mudança na próxima varredura da biblioteca.

## M3U e pastas de artista

Quando *Organizar por artista* está ativado e você baixa uma playlist do Spotify com a geração de M3U também ativada, o M3U é colocado em `<downloads>/Playlists/<nome-da-playlist>.m3u` em vez de ficar dentro da subpasta da playlist. Isso acontece porque as faixas agora ficam espalhadas por várias pastas de artistas. Os caminhos relativos dentro do M3U continuam resolvendo corretamente, não importa onde você monte a biblioteca.

## Mudando a configuração

A configuração vale imediatamente para todos os **novos** downloads. Os arquivos que já estão em disco não são movidos.

## Excluir uma faixa limpa as pastas vazias

Excluir uma faixa pela página da Biblioteca também remove a pasta de playlist, artista ou álbum dela, assim que fica vazia — e continua subindo pelas pastas-mãe que ficaram vazias (por exemplo, a pasta do artista depois que o último álbum some), parando na própria pasta de downloads, que nunca é removida. Uma pasta que ainda contém qualquer outra coisa — outra faixa, um `.m3u`, um `cover.jpg` ainda em uso — é deixada em paz.

## Selecionar e excluir várias faixas de uma vez

A lista de faixas da Biblioteca tem uma caixa de seleção em cada faixa, além de uma caixa **Selecionar tudo** que seleciona todas as faixas que correspondem ao filtro atual (veja a [página da Biblioteca](library-catalog.md#library-page)). **Excluir da biblioteca** na barra de seleção remove todas elas em uma única requisição (`DELETE /delete/batch`, veja a [Referência da API](../api-reference.md)), com a mesma limpeza por faixa (`.lrc`, `cover.jpg` órfão, pastas vazias) de excluir uma faixa de cada vez.

Para excluir um álbum ou uma playlist inteira, abra-o e escolha **Excluir** no menu **⋯**. Para tudo de um artista, digite o nome dele no filtro da lista de faixas, depois use **Selecionar tudo** e exclua.
