---
icon: lucide/list-music
---

# Exportação M3U

O Downtify gera automaticamente um arquivo de playlist `EXTM3U` padrão sempre que uma playlist do Spotify é baixada — manualmente ou pelo [Monitor de playlists](playlist-monitor.md).

## Local do arquivo

| Situação | Caminho do M3U |
|-----------|---------|
| Playlist baixada normalmente | `<downloads>/<nome-da-playlist>/<nome-da-playlist>.m3u` |
| Playlist baixada com *Organizar por artista* ativado | `<downloads>/Playlists/<nome-da-playlist>.m3u` |

Com *Organizar por artista* ativado, as faixas ficam espalhadas por várias pastas de artistas, então o M3U vai para um diretório central `Playlists/` em vez da subpasta da playlist.

As [músicas curtidas](liked-songs.md) também são gravadas em `Playlists/Downtify Liked Songs.m3u`, seja qual for a organização e esteja ou não ativado *Gerar playlists M3U*.

## Caminhos relativos

Os caminhos das faixas dentro do M3U são gravados **relativos ao próprio arquivo M3U**, não como caminhos absolutos. Isso significa que o mesmo arquivo funciona tanto lido de dentro do contêiner do Downtify (`/downloads/…`) quanto de outro consumidor que monte a mesma biblioteca em outra raiz — por exemplo, o Jellyfin em `/nas/music/…`. Basta apontar seu servidor de mídia para o mesmo ponto de montagem da biblioteca e a playlist aparece como uma unidade.

## Ativando / desativando

A geração de M3U é controlada por **Configurações → Downloads e arquivos → Gerar playlists M3U** (ativada por padrão). Desativá-la pula completamente a criação do M3U; o resto do fluxo de download não muda.

## Capa

Logo abaixo dessa configuração, **Salvar a capa da playlist** (ativada por padrão) grava a imagem de capa da própria playlist ao lado do M3U, com o mesmo nome — antes das faixas, para que a pasta já se pareça com a playlist desde o início. O Downtify passa a mostrar essa arte para a playlist em vez de uma grade com as capas das faixas. Uma playlist que você cria na Biblioteca recebe um mosaico de até quatro capas de faixas, gravado do mesmo jeito. Veja [Capa das playlists](playlist-cover-art.md).

## Quando é gravado

O M3U é regravado **depois que cada faixa termina de baixar**, então o arquivo da playlist cresce conforme o download avança em vez de aparecer de uma vez no fim. Isso vale para downloads de playlists e álbuns, [importações de CSV](library-import.md) e varreduras do [Monitor de playlists](playlist-monitor.md#m3u-integration).

Isso significa que a playlist já pode ser tocada desde o momento em que a primeira faixa chega, você vê a sincronização funcionando enquanto ela acontece, e um único download lento ou travado nunca impede o M3U — nem as faixas que já terminaram — de aparecer.

Uma regravação final roda quando a execução inteira termina. Ela resolve cada faixa contra o sistema de arquivos (em vez de contra a lista em memória do que esta execução baixou), então também recolhe arquivos de execuções anteriores e corrige qualquer coisa que tenha mudado em disco durante a execução.

Toda gravação lista as faixas na **ordem da playlist**, não na ordem em que os downloads terminaram, então um M3U parcialmente gravado continua corretamente ordenado.

::: info Faixas que já estão em disco
As faixas baixadas por uma execução anterior permanecem no M3U o tempo todo — entram desde a primeira gravação, não apenas na final.
:::

## Regeneração

O M3U é regenerado do zero a cada execução — colar de novo a mesma URL de playlist produz um arquivo completo e em ordem, incluindo faixas que faltavam em execuções anteriores.

Faixas que falharam ao baixar ou que não tiveram correspondência no YouTube Music são ignoradas em silêncio.

## Compatibilidade

O arquivo gerado usa:

- Codificação UTF-8, sem BOM
- Quebras de linha LF
- O formato padrão `#EXTM3U` / `#EXTINF`

É compatível com Jellyfin, Navidrome, Plex, VLC, Kodi, Sonos e qualquer outro player ou servidor de mídia que consuma playlists M3U padrão.

## Playlists que você cria

**Biblioteca → Playlists → Nova playlist** grava o mesmo tipo de M3U em `Playlists/`, com uma linha extra `#EXTDOWNTIFY:manual` para que o Downtify a distinga de uma playlist baixada do Spotify/YouTube. Você pode renomeá-la e adicionar ou remover músicas (inclusive de [pastas extras](external-library.md)). Excluir essa playlist, excluir uma faixa ou desmapear uma pasta extra atualiza o M3U; o áudio só é excluído quando você exclui a própria faixa ou uma playlist importada.

### Adicionando músicas a uma playlist

Os administradores podem colocar músicas em uma dessas playlists, ou em uma nova, de vários lugares:

- **O menu ⋯ de uma música** (em qualquer lista de faixas) → **Adicionar à playlist**.
- **Selecione várias músicas** na Biblioteca e clique em **Adicionar à playlist**.
- **O menu ⋯ de um álbum** → **Adicionar à playlist** adiciona todas as músicas do álbum.
- **O menu ⋯ de um artista** (na página do artista) → **Adicionar à playlist** adiciona tudo o que o artista tem na sua biblioteca, álbum por álbum.

Cada menu lista suas playlists e uma entrada **Nova playlist…** que cria uma já com essas músicas. Uma música que a playlist já tem é ignorada, e a confirmação diz quantas foram realmente adicionadas (ou que todas já estavam lá). Uma playlist comporta no máximo 500 músicas.
