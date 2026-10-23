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

Com **Configurações → Downloads e arquivos → Organizar por artista** ativado (o padrão), todas as faixas — inclusive os downloads de playlists e álbuns — são agrupadas em uma subpasta com o nome do artista principal:

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

## M3U e pastas de artista

Quando *Organizar por artista* está ativado e você baixa uma playlist do Spotify com a geração de M3U também ativada, o M3U é colocado em `<downloads>/Playlists/<nome-da-playlist>.m3u` em vez de ficar dentro da subpasta da playlist. Isso acontece porque as faixas agora ficam espalhadas por várias pastas de artistas. Os caminhos relativos dentro do M3U continuam resolvendo corretamente, não importa onde você monte a biblioteca.

## Mudando a configuração

A configuração vale imediatamente para todos os **novos** downloads. Os arquivos que já estão em disco não são movidos.

## Excluir uma faixa limpa as pastas vazias

Excluir uma faixa pela página da Biblioteca também remove a pasta de playlist, artista ou álbum dela, assim que fica vazia — e continua subindo pelas pastas-mãe que ficaram vazias (por exemplo, a pasta do artista depois que o último álbum some), parando na própria pasta de downloads, que nunca é removida. Uma pasta que ainda contém qualquer outra coisa — outra faixa, um `.m3u`, um `cover.jpg` ainda em uso — é deixada em paz.

## Selecionar e excluir várias faixas de uma vez

A lista de faixas da Biblioteca tem uma caixa de seleção em cada faixa, além de uma caixa **Selecionar tudo** que seleciona todas as faixas que correspondem ao filtro atual (veja a [página da Biblioteca](library-catalog.md#library-page)). **Excluir da biblioteca** na barra de seleção remove todas elas em uma única requisição (`DELETE /delete/batch`, veja a [Referência da API](../api-reference.md)), com a mesma limpeza por faixa (`.lrc`, `cover.jpg` órfão, pastas vazias) de excluir uma faixa de cada vez.

Para excluir um álbum ou uma playlist inteira, abra-o e escolha **Excluir** no menu **⋯**. Para tudo de um artista, digite o nome dele no filtro da lista de faixas, depois use **Selecionar tudo** e exclua.
