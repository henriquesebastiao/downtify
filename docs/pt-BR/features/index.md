---
icon: lucide/sparkles
---

# Recursos

O Downtify cobre tudo de que você precisa para montar e manter uma biblioteca de músicas local a partir do Spotify.

## Visão geral

| Recurso | O que faz |
|---------|-------------|
| [Paradas de sucesso](charts.md) | Navegue pela parada global do Deezer e baixe o que está em alta |
| [Similares](similar.md) | Informe um artista ou uma faixa; o YouTube Music responde com faixas parecidas que tocam por inteiro e podem ser baixadas, sem chave |
| [Localizador](finder.md) | Pesquise no Deezer e depois navegue por um artista, seus álbuns e as faixas de qualquer álbum em colunas |
| [Configurações de download](download-settings.md) | Escolha o formato (MP3/FLAC/M4A/OGG/OPUS), a taxa de bits, os downloads simultâneos e a pausa entre downloads |
| [Fila de downloads](download-queue.md) | Pause os downloads antes de mudar configurações ou atualizar: os que estão em andamento terminam, nenhum novo começa e as músicas em espera sobrevivem a uma reinicialização |
| [Monitor de playlists](playlist-monitor.md) | Acompanhe playlists e artistas do Spotify ou YouTube Music e baixe automaticamente faixas e lançamentos novos |
| [Músicas ocultas da playlist](hidden-playlist-songs.md) | Tire de uma playlist baixada ou monitorada as músicas que você não quer e mantenha-as fora; os arquivos continuam na biblioteca |
| [Músicas mais tocadas](top-songs.md) | Cole o link de um artista e baixe suas músicas mais populares, opcionalmente como playlist |
| [Importar biblioteca (CSV)](library-import.md) | Importe uma exportação do Soundiiz, TuneMyMusic ou Exportify e coloque tudo na fila |
| [Player integrado](player.md) | Toque sua biblioteca no navegador: gerenciamento da fila, letras sincronizadas, timer de sono, teclado e teclas de mídia |
| [Normalização de volume](playback-normalization.md) | Toque todas as músicas com volume parecido, a partir de medições que um admin inicia; os arquivos de áudio nunca são alterados |
| [Músicas curtidas](liked-songs.md) | Dê um coração a uma música para curti-la; uma playlist com tudo o que você curtiu aparece sozinha |
| [Podcasts](podcasts.md) | Assine um programa por feed RSS, link do Spotify ou nome; os novos episódios são baixados e etiquetados sozinhos |
| [Usuários e login](users.md) | Login com usuário e senha (`admin` / `downtify` em um servidor novo), contas de administrador e de usuário comum, preferências por usuário e um registro de atividade com logins e o que cada um ouve |
| [Marca de conteúdo explícito](explicit-marker.md) | O "E" ao lado de músicas com letra explícita — na busca, na Biblioteca e no player — e nas tags do arquivo |
| [Substituir áudio](replace-audio.md) | Música ou versão errada? Escolha a certa no YouTube Music ou no YouTube; o arquivo mantém nome, tags e playlists |
| [Configurações do servidor](server.md) | A porta em que o Downtify escuta, alterada pelas Configurações (administradores), com reinício imediato se quiser |
| [Apps para celular](mobile-apps.md) | Pareie apps de celular por QR code e transmita a biblioteca para eles (original ou transcodificada) |
| [Descobrir](discover.md) | Artistas, álbuns e playlists que você ainda não tem, sugeridos a partir da sua biblioteca, curtidas e o que você ouve; oculte os que não quer |
| [slskd e Navidrome](slskd-navidrome.md) | Baixe do Soulseek pelo slskd, espelhe playlists no Navidrome e acompanhe os downloads de playlists |
| [Catálogo da biblioteca e sincronia de caminhos](library-catalog.md) | Como o Downtify acompanha arquivos e playlists da biblioteca, playlists que você cria na Biblioteca e a correção de caminhos depois de mover arquivos |
| [Pastas de música existentes](external-library.md) | Aponte o Downtify para pastas de áudio que você já tem; a sincronização lê as tags, associa artistas e ignora músicas que já estão na biblioteca |
| [Melhorar a biblioteca](library-upgrade.md) | Varra músicas já baixadas e corrija capas pequenas, letras ausentes e tags incompletas |
| [Armazenamento e uso](storage-usage.md) | Veja o tamanho da biblioteca e o quanto ela cresce, de que fonte veio cada parte, como terminaram os downloads e quanto ocupam duplicatas, cópias do slskd e sobras |
| [Exportação M3U](m3u-export.md) | Arquivos de playlist gerados automaticamente para Jellyfin, Navidrome, Plex e qualquer app de mídia |
| [Capa das playlists](playlist-cover-art.md) | Salve a imagem de capa da própria playlist junto ao arquivo M3U |
| [Foto, banner e bio do artista](artist-images.md) | Escolha uma foto e um banner reais para um artista no YouTube Music, Deezer, Spotify ou em um upload seu, e busque a bio, a origem e os links no Apple Music e no Deezer, automaticamente ou sob demanda |
| [Apoiar o artista](support-artists.md) | Veja onde comprar uma música, álbum ou artista: o item na iTunes Store com preço, Bandcamp e Qobuz, o site do artista |
| [Organização de arquivos](file-organization.md) | Formato plano ou subpastas por artista |
| [Letras](lyrics.md) | Baixe e incorpore letras automaticamente (simples e sincronizadas); `.lrc` ao lado do arquivo ou em uma pasta que você escolher |
| [Cookies do YouTube](youtube-cookies.md) | Envie um `cookies.txt` pela interface web para baixar faixas explícitas/com restrição de idade |
| [Internacionalização](internationalization.md) | Inglês e mais nove idiomas de fábrica, e a documentação em todos eles |
| [Avisos de atualização](updates.md) | Verificação de hora em hora nos Releases do GitHub; um aviso aparece na barra lateral quando há versão mais nova |

## Tipos de entrada

O Downtify aceita vários tipos de entrada na barra de busca:

| Entrada | Exemplo |
|-------|---------|
| URL de faixa, álbum, playlist ou artista do Spotify | `https://open.spotify.com/track/…` |
| URL do YouTube / YouTube Music | `https://www.youtube.com/watch?v=…` |
| URL de playlist ou artista do YouTube Music | `https://music.youtube.com/playlist?list=…` |
| URL de faixa, álbum, playlist ou artista do Deezer | `https://www.deezer.com/track/…` |
| Busca por texto livre | `The Night Owls Do I Still Recall` |

As buscas por texto livre vão direto para o YouTube Music — não é preciso um link do Spotify.
